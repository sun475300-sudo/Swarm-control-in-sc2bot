# Phase 596: PyTorch Geometric (PyG)
"""
sc2_battle_gnn.py — StarCraft II Battle Prediction with Graph Neural Networks

Models SC2 combat as a graph: units are nodes, interactions (attack range,
proximity) are edges.  Supports GCN, GAT, GraphSAGE, and full MPNN
architectures with global pooling for graph-level battle-outcome prediction.

Graceful fallback to a pure-NumPy stub when PyTorch / PyG is absent.
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("sc2_battle_gnn")

# ---------------------------------------------------------------------------
# Optional imports — PyTorch & PyG
# ---------------------------------------------------------------------------
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.optim import Adam
    from torch.optim.lr_scheduler import CosineAnnealingLR

    TORCH_AVAILABLE = True
    log.info("PyTorch %s available.", torch.__version__)
except ImportError:
    TORCH_AVAILABLE = False
    log.warning(
        "PyTorch not installed. Running pure-NumPy fallback. "
        "Install with: pip install torch"
    )

try:
    import torch_geometric  # noqa: F811
    from torch_geometric.data import Batch, Data
    from torch_geometric.loader import DataLoader as PyGDataLoader
    from torch_geometric.nn import (
        GATConv,
        GCNConv,
        NNConv,
        SAGEConv,
        global_add_pool,
        global_max_pool,
        global_mean_pool,
    )
    from torch_geometric.utils import to_networkx

    PYG_AVAILABLE = True
    log.info("PyTorch Geometric %s available.", torch_geometric.__version__)
except ImportError:
    PYG_AVAILABLE = False
    if TORCH_AVAILABLE:
        log.warning(
            "torch_geometric not installed. "
            "Install with: pip install torch-geometric"
        )

# ---------------------------------------------------------------------------
# SC2 unit-type catalogue (Zerg-centric, extensible)
# ---------------------------------------------------------------------------
UNIT_TYPES: Dict[str, int] = {
    "Zergling": 0,
    "Baneling": 1,
    "Roach": 2,
    "Ravager": 3,
    "Hydralisk": 4,
    "Lurker": 5,
    "Mutalisk": 6,
    "Corruptor": 7,
    "BroodLord": 8,
    "Viper": 9,
    "Infestor": 10,
    "SwarmHost": 11,
    "Ultralisk": 12,
    "Queen": 13,
    "Overlord": 14,
    "Overseer": 15,
    "Drone": 16,
    "SpineCrawler": 17,
    "SporeCrawler": 18,
    # Terran
    "Marine": 19,
    "Marauder": 20,
    "Reaper": 21,
    "Hellion": 22,
    "SiegeTank": 23,
    "Thor": 24,
    "Viking": 25,
    "Medivac": 26,
    "Banshee": 27,
    "Raven": 28,
    "Battlecruiser": 29,
    "Liberator": 30,
    "Ghost": 31,
    "Cyclone": 32,
    "WidowMine": 33,
    # Protoss
    "Zealot": 34,
    "Stalker": 35,
    "Adept": 36,
    "Sentry": 37,
    "Immortal": 38,
    "Colossus": 39,
    "Disruptor": 40,
    "Phoenix": 41,
    "VoidRay": 42,
    "Oracle": 43,
    "Tempest": 44,
    "Carrier": 45,
    "HighTemplar": 46,
    "DarkTemplar": 47,
    "Archon": 48,
    "WarpPrism": 49,
    "Observer": 50,
    "Mothership": 51,
}
NUM_UNIT_TYPES = len(UNIT_TYPES)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class UnitState:
    """Snapshot of a single unit on the battlefield."""

    unit_id: int
    unit_type: str
    hp: float
    max_hp: float
    dps: float
    attack_range: float
    speed: float
    is_flying: bool
    x: float
    y: float
    player_id: int  # 1 = friendly, 2 = enemy


@dataclass
class BattleSnapshot:
    """All units visible in a single game-tick battle frame."""

    units: List[UnitState]
    outcome: Optional[float] = None  # 1.0 win, 0.0 loss, 0.5 draw
    tick: int = 0


# ---------------------------------------------------------------------------
# Feature engineering helpers
# ---------------------------------------------------------------------------


def _unit_features(unit: UnitState, embed_dim: int = 16) -> np.ndarray:
    """Return a feature vector for a single unit node.

    Features (7 scalar + embed_dim embedding):
        hp_ratio, hp, max_hp, dps, range, speed, is_flying,
        <unit_type_embedding via learned lookup or one-hot placeholder>
    """
    hp_ratio = unit.hp / max(unit.max_hp, 1.0)
    scalars = np.array(
        [
            hp_ratio,
            unit.hp / 500.0,  # rough normalisation
            unit.max_hp / 500.0,
            unit.dps / 50.0,
            unit.attack_range / 15.0,
            unit.speed / 6.0,
            float(unit.is_flying),
        ],
        dtype=np.float32,
    )

    # One-hot placeholder for unit type (will be replaced by learnable
    # embedding inside the model, but we keep a sparse cue here).
    type_idx = UNIT_TYPES.get(unit.unit_type, 0)
    type_vec = np.zeros(embed_dim, dtype=np.float32)
    type_vec[type_idx % embed_dim] = 1.0

    return np.concatenate([scalars, type_vec])


NODE_FEAT_DIM = 7 + 16  # 23


def _edge_features(u1: UnitState, u2: UnitState) -> np.ndarray:
    """Edge features between two units.

    [distance_norm, can_attack, is_friendly]
    """
    dx = u1.x - u2.x
    dy = u1.y - u2.y
    dist = math.sqrt(dx * dx + dy * dy)
    dist_norm = min(dist / 30.0, 1.0)

    can_attack = (
        1.0
        if ((not u2.is_flying or u1.attack_range > 0) and dist <= u1.attack_range + 1.0)
        else 0.0
    )

    is_friendly = 1.0 if u1.player_id == u2.player_id else 0.0

    return np.array([dist_norm, can_attack, is_friendly], dtype=np.float32)


EDGE_FEAT_DIM = 3


# ---------------------------------------------------------------------------
# Graph construction from game state
# ---------------------------------------------------------------------------


def build_graph_from_snapshot(
    snapshot: BattleSnapshot,
    max_edge_dist: float = 20.0,
) -> Optional[Any]:
    """Convert a BattleSnapshot into a PyG Data object.

    Edges are created between units within *max_edge_dist* distance.
    """
    units = snapshot.units
    if not units:
        return None

    # Node features
    node_feats = np.stack([_unit_features(u) for u in units], axis=0)

    # Edges (fully connected within distance threshold)
    src_list: List[int] = []
    dst_list: List[int] = []
    edge_attr_list: List[np.ndarray] = []

    for i, u1 in enumerate(units):
        for j, u2 in enumerate(units):
            if i == j:
                continue
            dx = u1.x - u2.x
            dy = u1.y - u2.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist <= max_edge_dist:
                src_list.append(i)
                dst_list.append(j)
                edge_attr_list.append(_edge_features(u1, u2))

    if not src_list:
        # Add self-loops so the graph is non-empty
        for i in range(len(units)):
            src_list.append(i)
            dst_list.append(i)
            edge_attr_list.append(np.zeros(EDGE_FEAT_DIM, dtype=np.float32))

    if not PYG_AVAILABLE:
        return {
            "x": node_feats,
            "edge_index": np.array([src_list, dst_list]),
            "edge_attr": np.stack(edge_attr_list),
            "y": snapshot.outcome,
        }

    edge_index = torch.tensor([src_list, dst_list], dtype=torch.long)
    x = torch.tensor(node_feats, dtype=torch.float)
    edge_attr = torch.tensor(np.stack(edge_attr_list), dtype=torch.float)
    y = torch.tensor(
        [snapshot.outcome if snapshot.outcome is not None else 0.5],
        dtype=torch.float,
    )

    unit_type_ids = torch.tensor(
        [UNIT_TYPES.get(u.unit_type, 0) for u in units],
        dtype=torch.long,
    )

    return Data(
        x=x,
        edge_index=edge_index,
        edge_attr=edge_attr,
        y=y,
        unit_type_ids=unit_type_ids,
    )


def build_dataset(
    snapshots: Sequence[BattleSnapshot],
    max_edge_dist: float = 20.0,
) -> List[Any]:
    """Build a list of PyG Data objects from battle snapshots."""
    graphs: List[Any] = []
    for snap in snapshots:
        g = build_graph_from_snapshot(snap, max_edge_dist)
        if g is not None:
            graphs.append(g)
    log.info("Built %d graphs from %d snapshots.", len(graphs), len(snapshots))
    return graphs


# ============================================================================
# GNN MODEL IMPLEMENTATIONS
# ============================================================================

if TORCH_AVAILABLE and PYG_AVAILABLE:

    # -----------------------------------------------------------------------
    # Unit-type embedding module (shared across architectures)
    # -----------------------------------------------------------------------
    class UnitTypeEmbedding(nn.Module):
        """Learnable embedding for SC2 unit types, concatenated to raw features."""

        def __init__(self, num_types: int = NUM_UNIT_TYPES, embed_dim: int = 16):
            super().__init__()
            self.embed = nn.Embedding(num_types, embed_dim)

        def forward(self, x: torch.Tensor, unit_type_ids: torch.Tensor) -> torch.Tensor:
            emb = self.embed(unit_type_ids)
            # Replace the placeholder one-hot section with the learned embedding
            return torch.cat([x[:, :7], emb], dim=-1)

    # -----------------------------------------------------------------------
    # 1. GCN-based battle predictor
    # -----------------------------------------------------------------------
    class GCNBattlePredictor(nn.Module):
        """Graph Convolutional Network stack for battle outcome prediction."""

        def __init__(
            self,
            in_channels: int = NODE_FEAT_DIM,
            hidden: int = 128,
            num_layers: int = 4,
            dropout: float = 0.2,
        ):
            super().__init__()
            self.type_embed = UnitTypeEmbedding()
            in_dim = 7 + 16  # scalar features + learned embedding

            self.convs = nn.ModuleList()
            self.bns = nn.ModuleList()
            self.convs.append(GCNConv(in_dim, hidden))
            self.bns.append(nn.BatchNorm1d(hidden))
            for _ in range(num_layers - 1):
                self.convs.append(GCNConv(hidden, hidden))
                self.bns.append(nn.BatchNorm1d(hidden))

            self.dropout = dropout
            self.head = nn.Sequential(
                nn.Linear(hidden * 2, hidden),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden, 1),
                nn.Sigmoid(),
            )

        def forward(self, data: Data) -> torch.Tensor:
            x = self.type_embed(data.x, data.unit_type_ids)
            edge_index = data.edge_index
            batch = (
                data.batch
                if hasattr(data, "batch") and data.batch is not None
                else torch.zeros(x.size(0), dtype=torch.long, device=x.device)
            )

            for conv, bn in zip(self.convs, self.bns):
                x = conv(x, edge_index)
                x = bn(x)
                x = F.relu(x)
                x = F.dropout(x, p=self.dropout, training=self.training)

            # Dual global pooling
            xm = global_mean_pool(x, batch)
            xa = global_max_pool(x, batch)
            out = self.head(torch.cat([xm, xa], dim=-1))
            return out.squeeze(-1)

    # -----------------------------------------------------------------------
    # 2. GAT-based battle predictor (attention over unit interactions)
    # -----------------------------------------------------------------------
    class GATBattlePredictor(nn.Module):
        """Graph Attention Network for battle outcome prediction.

        Stores attention weights for visualisation.
        """

        def __init__(
            self,
            in_channels: int = NODE_FEAT_DIM,
            hidden: int = 64,
            heads: int = 4,
            num_layers: int = 3,
            dropout: float = 0.2,
        ):
            super().__init__()
            self.type_embed = UnitTypeEmbedding()
            in_dim = 7 + 16

            self.convs = nn.ModuleList()
            self.bns = nn.ModuleList()
            self.convs.append(GATConv(in_dim, hidden, heads=heads, dropout=dropout))
            self.bns.append(nn.BatchNorm1d(hidden * heads))
            for _ in range(num_layers - 2):
                self.convs.append(
                    GATConv(hidden * heads, hidden, heads=heads, dropout=dropout)
                )
                self.bns.append(nn.BatchNorm1d(hidden * heads))
            # Final layer: single head
            self.convs.append(
                GATConv(hidden * heads, hidden, heads=1, concat=False, dropout=dropout)
            )
            self.bns.append(nn.BatchNorm1d(hidden))

            self.dropout = dropout
            self._attention_weights: List[Tuple[torch.Tensor, torch.Tensor]] = []

            self.head = nn.Sequential(
                nn.Linear(hidden * 2, hidden),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden, 1),
                nn.Sigmoid(),
            )

        def forward(self, data: Data, return_attention: bool = False) -> torch.Tensor:
            x = self.type_embed(data.x, data.unit_type_ids)
            edge_index = data.edge_index
            batch = (
                data.batch
                if hasattr(data, "batch") and data.batch is not None
                else torch.zeros(x.size(0), dtype=torch.long, device=x.device)
            )

            self._attention_weights.clear()

            for i, (conv, bn) in enumerate(zip(self.convs, self.bns)):
                x, (edge_idx_out, alpha) = conv(
                    x, edge_index, return_attention_weights=True
                )
                if return_attention:
                    self._attention_weights.append(
                        (edge_idx_out.detach().cpu(), alpha.detach().cpu())
                    )
                x = bn(x)
                x = F.elu(x)
                x = F.dropout(x, p=self.dropout, training=self.training)

            xm = global_mean_pool(x, batch)
            xa = global_max_pool(x, batch)
            out = self.head(torch.cat([xm, xa], dim=-1))
            return out.squeeze(-1)

        def get_attention_weights(self) -> List[Tuple[torch.Tensor, torch.Tensor]]:
            """Return cached attention weights from the last forward pass."""
            return self._attention_weights

    # -----------------------------------------------------------------------
    # 3. GraphSAGE for inductive learning (new unit compositions)
    # -----------------------------------------------------------------------
    class SAGEBattlePredictor(nn.Module):
        """GraphSAGE model — inductive learning for unseen unit compositions."""

        def __init__(
            self,
            in_channels: int = NODE_FEAT_DIM,
            hidden: int = 128,
            num_layers: int = 3,
            dropout: float = 0.2,
        ):
            super().__init__()
            self.type_embed = UnitTypeEmbedding()
            in_dim = 7 + 16

            self.convs = nn.ModuleList()
            self.bns = nn.ModuleList()
            self.convs.append(SAGEConv(in_dim, hidden))
            self.bns.append(nn.BatchNorm1d(hidden))
            for _ in range(num_layers - 1):
                self.convs.append(SAGEConv(hidden, hidden))
                self.bns.append(nn.BatchNorm1d(hidden))

            self.dropout = dropout
            self.head = nn.Sequential(
                nn.Linear(hidden * 3, hidden),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden, 1),
                nn.Sigmoid(),
            )

        def forward(self, data: Data) -> torch.Tensor:
            x = self.type_embed(data.x, data.unit_type_ids)
            edge_index = data.edge_index
            batch = (
                data.batch
                if hasattr(data, "batch") and data.batch is not None
                else torch.zeros(x.size(0), dtype=torch.long, device=x.device)
            )

            for conv, bn in zip(self.convs, self.bns):
                x = conv(x, edge_index)
                x = bn(x)
                x = F.relu(x)
                x = F.dropout(x, p=self.dropout, training=self.training)

            # Triple global pooling (mean + max + sum)
            xm = global_mean_pool(x, batch)
            xa = global_max_pool(x, batch)
            xs = global_add_pool(x, batch)
            out = self.head(torch.cat([xm, xa, xs], dim=-1))
            return out.squeeze(-1)

    # -----------------------------------------------------------------------
    # 4. Message Passing Neural Network (MPNN) — uses edge features
    # -----------------------------------------------------------------------
    class MPNNBattlePredictor(nn.Module):
        """Full MPNN using NNConv to incorporate edge features (distance,
        can_attack, is_friendly) into message passing."""

        def __init__(
            self,
            in_channels: int = NODE_FEAT_DIM,
            hidden: int = 128,
            edge_dim: int = EDGE_FEAT_DIM,
            num_layers: int = 3,
            dropout: float = 0.2,
        ):
            super().__init__()
            self.type_embed = UnitTypeEmbedding()
            in_dim = 7 + 16

            self.lin_in = nn.Linear(in_dim, hidden)

            self.convs = nn.ModuleList()
            self.bns = nn.ModuleList()
            for _ in range(num_layers):
                edge_nn = nn.Sequential(
                    nn.Linear(edge_dim, hidden),
                    nn.ReLU(),
                    nn.Linear(hidden, hidden * hidden),
                )
                self.convs.append(NNConv(hidden, hidden, edge_nn, aggr="mean"))
                self.bns.append(nn.BatchNorm1d(hidden))

            self.dropout = dropout
            self.head = nn.Sequential(
                nn.Linear(hidden * 2, hidden),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden, 1),
                nn.Sigmoid(),
            )

        def forward(self, data: Data) -> torch.Tensor:
            x = self.type_embed(data.x, data.unit_type_ids)
            x = F.relu(self.lin_in(x))
            edge_index = data.edge_index
            edge_attr = data.edge_attr
            batch = (
                data.batch
                if hasattr(data, "batch") and data.batch is not None
                else torch.zeros(x.size(0), dtype=torch.long, device=x.device)
            )

            for conv, bn in zip(self.convs, self.bns):
                x = conv(x, edge_index, edge_attr)
                x = bn(x)
                x = F.relu(x)
                x = F.dropout(x, p=self.dropout, training=self.training)

            xm = global_mean_pool(x, batch)
            xa = global_max_pool(x, batch)
            out = self.head(torch.cat([xm, xa], dim=-1))
            return out.squeeze(-1)

    # -----------------------------------------------------------------------
    # Unified wrapper
    # -----------------------------------------------------------------------
    class SC2BattleGNN:
        """High-level API for training and evaluating GNN battle predictors.

        Parameters
        ----------
        arch : str
            One of ``"gcn"``, ``"gat"``, ``"sage"``, ``"mpnn"``.
        hidden : int
            Hidden dimension for all layers.
        num_layers : int
            Number of message-passing layers.
        lr : float
            Learning rate.
        dropout : float
            Dropout probability.
        device : str
            ``"cuda"`` or ``"cpu"``.
        """

        ARCH_MAP = {
            "gcn": GCNBattlePredictor,
            "gat": GATBattlePredictor,
            "sage": SAGEBattlePredictor,
            "mpnn": MPNNBattlePredictor,
        }

        def __init__(
            self,
            arch: str = "gat",
            hidden: int = 128,
            num_layers: int = 3,
            lr: float = 1e-3,
            dropout: float = 0.2,
            device: str = "cpu",
        ):
            if arch not in self.ARCH_MAP:
                raise ValueError(
                    f"Unknown architecture '{arch}'. Choose from {list(self.ARCH_MAP)}"
                )

            self.arch_name = arch
            self.device = torch.device(device)

            model_cls = self.ARCH_MAP[arch]
            kwargs: Dict[str, Any] = {
                "hidden": hidden,
                "num_layers": num_layers,
                "dropout": dropout,
            }
            if arch == "gat":
                kwargs["heads"] = 4
            self.model = model_cls(**kwargs).to(self.device)

            self.optimizer = Adam(self.model.parameters(), lr=lr, weight_decay=1e-5)
            self.scheduler = CosineAnnealingLR(self.optimizer, T_max=50, eta_min=1e-6)
            self.criterion = nn.BCELoss()

            self._train_losses: List[float] = []
            self._val_losses: List[float] = []
            log.info(
                "SC2BattleGNN initialised  arch=%s  params=%d  device=%s",
                arch,
                sum(p.numel() for p in self.model.parameters()),
                self.device,
            )

        # -- Training -------------------------------------------------------

        def train_epoch(
            self,
            loader: PyGDataLoader,
            clip_grad: float = 1.0,
        ) -> float:
            """Run one training epoch; return mean loss."""
            self.model.train()
            total_loss = 0.0
            n = 0
            for batch in loader:
                batch = batch.to(self.device)
                self.optimizer.zero_grad()
                pred = self.model(batch)
                loss = self.criterion(pred, batch.y)
                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), clip_grad)
                self.optimizer.step()
                total_loss += loss.item() * batch.num_graphs
                n += batch.num_graphs
            avg = total_loss / max(n, 1)
            self._train_losses.append(avg)
            return avg

        @torch.no_grad()
        def evaluate(self, loader: PyGDataLoader) -> Dict[str, float]:
            """Evaluate on a data loader; return loss, accuracy, AUC."""
            self.model.eval()
            total_loss = 0.0
            correct = 0
            n = 0
            all_preds: List[float] = []
            all_labels: List[float] = []

            for batch in loader:
                batch = batch.to(self.device)
                pred = self.model(batch)
                loss = self.criterion(pred, batch.y)
                total_loss += loss.item() * batch.num_graphs
                binary_pred = (pred > 0.5).float()
                correct += (binary_pred == batch.y).sum().item()
                n += batch.num_graphs
                all_preds.extend(pred.cpu().tolist())
                all_labels.extend(batch.y.cpu().tolist())

            avg_loss = total_loss / max(n, 1)
            accuracy = correct / max(n, 1)
            self._val_losses.append(avg_loss)

            # Simple AUC approximation (rank-based)
            auc = self._approx_auc(all_labels, all_preds)

            return {"loss": avg_loss, "accuracy": accuracy, "auc": auc}

        def fit(
            self,
            train_graphs: List[Data],
            val_graphs: Optional[List[Data]] = None,
            epochs: int = 50,
            batch_size: int = 32,
            patience: int = 10,
        ) -> Dict[str, Any]:
            """Full training loop with early stopping."""
            train_loader = PyGDataLoader(
                train_graphs, batch_size=batch_size, shuffle=True
            )
            val_loader = (
                PyGDataLoader(val_graphs, batch_size=batch_size) if val_graphs else None
            )

            best_val_loss = float("inf")
            best_state = None
            wait = 0

            for epoch in range(1, epochs + 1):
                train_loss = self.train_epoch(train_loader)
                self.scheduler.step()

                msg = f"Epoch {epoch:3d} | train_loss={train_loss:.4f}"
                if val_loader:
                    metrics = self.evaluate(val_loader)
                    msg += f" | val_loss={metrics['loss']:.4f} acc={metrics['accuracy']:.3f} auc={metrics['auc']:.3f}"
                    if metrics["loss"] < best_val_loss:
                        best_val_loss = metrics["loss"]
                        best_state = {
                            k: v.cpu().clone()
                            for k, v in self.model.state_dict().items()
                        }
                        wait = 0
                    else:
                        wait += 1
                log.info(msg)

                if wait >= patience:
                    log.info("Early stopping at epoch %d.", epoch)
                    break

            if best_state is not None:
                self.model.load_state_dict(best_state)

            return {
                "epochs_trained": epoch,
                "best_val_loss": best_val_loss,
                "train_losses": self._train_losses.copy(),
                "val_losses": self._val_losses.copy(),
            }

        # -- Prediction -----------------------------------------------------

        @torch.no_grad()
        def predict(self, snapshot: BattleSnapshot) -> float:
            """Predict win probability for a single battle snapshot."""
            self.model.eval()
            graph = build_graph_from_snapshot(snapshot)
            if graph is None:
                return 0.5
            graph = graph.to(self.device)
            # Add batch vector for single graph
            graph.batch = torch.zeros(
                graph.x.size(0), dtype=torch.long, device=self.device
            )
            return self.model(graph).item()

        @torch.no_grad()
        def predict_batch(self, snapshots: Sequence[BattleSnapshot]) -> List[float]:
            """Predict win probabilities for a batch of snapshots."""
            self.model.eval()
            graphs = [build_graph_from_snapshot(s) for s in snapshots]
            graphs = [g for g in graphs if g is not None]
            if not graphs:
                return [0.5] * len(snapshots)
            loader = PyGDataLoader(graphs, batch_size=len(graphs))
            batch = next(iter(loader)).to(self.device)
            preds = self.model(batch)
            return preds.cpu().tolist()

        # -- Attention visualisation ----------------------------------------

        @torch.no_grad()
        def get_attention_map(
            self,
            snapshot: BattleSnapshot,
        ) -> Optional[Dict[str, Any]]:
            """Return attention weights for a GAT model on a single snapshot.

            Returns None if the architecture is not GAT.
            """
            if self.arch_name != "gat":
                log.warning("Attention map only available for GAT architecture.")
                return None

            self.model.eval()
            graph = build_graph_from_snapshot(snapshot)
            if graph is None:
                return None
            graph = graph.to(self.device)
            graph.batch = torch.zeros(
                graph.x.size(0), dtype=torch.long, device=self.device
            )

            _ = self.model(graph, return_attention=True)
            attn = self.model.get_attention_weights()

            unit_names = [u.unit_type for u in snapshot.units]
            return {
                "unit_names": unit_names,
                "layers": [
                    {"edge_index": ei.numpy(), "alpha": al.numpy()} for ei, al in attn
                ],
            }

        def visualize_attention(
            self,
            snapshot: BattleSnapshot,
            layer: int = -1,
            save_path: Optional[str] = None,
        ) -> None:
            """Plot attention weights using matplotlib / networkx."""
            attn_data = self.get_attention_map(snapshot)
            if attn_data is None:
                return

            try:
                import matplotlib.pyplot as plt
                import networkx as nx
            except ImportError:
                log.warning("matplotlib/networkx required for visualisation.")
                return

            layer_data = attn_data["layers"][layer]
            edge_index = layer_data["edge_index"]  # (2, E)
            alpha = layer_data["alpha"]  # (E, heads) or (E,)

            if alpha.ndim == 2:
                alpha = alpha.mean(axis=1)  # average over heads

            G = nx.DiGraph()
            names = attn_data["unit_names"]
            for i, name in enumerate(names):
                G.add_node(i, label=name)

            for idx in range(edge_index.shape[1]):
                src, dst = int(edge_index[0, idx]), int(edge_index[1, idx])
                G.add_edge(src, dst, weight=float(alpha[idx]))

            pos = nx.spring_layout(G, seed=42)
            labels = {i: names[i] for i in range(len(names))}
            weights = [G[u][v]["weight"] * 3.0 for u, v in G.edges()]

            plt.figure(figsize=(12, 8))
            nx.draw_networkx_nodes(G, pos, node_size=600, node_color="lightblue")
            nx.draw_networkx_labels(G, pos, labels, font_size=8)
            nx.draw_networkx_edges(
                G,
                pos,
                width=weights,
                alpha=0.6,
                edge_color="red",
                arrows=True,
                arrowsize=15,
            )
            plt.title(f"GAT Attention Weights (Layer {layer})")
            plt.axis("off")
            plt.tight_layout()

            if save_path:
                plt.savefig(save_path, dpi=150)
                log.info("Attention plot saved to %s", save_path)
            else:
                plt.show()
            plt.close()

        # -- Persistence ----------------------------------------------------

        def save(self, path: str) -> None:
            torch.save(
                {
                    "arch": self.arch_name,
                    "state_dict": self.model.state_dict(),
                    "train_losses": self._train_losses,
                    "val_losses": self._val_losses,
                },
                path,
            )
            log.info("Model saved to %s", path)

        def load(self, path: str) -> None:
            ckpt = torch.load(path, map_location=self.device)
            self.model.load_state_dict(ckpt["state_dict"])
            self._train_losses = ckpt.get("train_losses", [])
            self._val_losses = ckpt.get("val_losses", [])
            log.info("Model loaded from %s", path)

        # -- Helpers --------------------------------------------------------

        @staticmethod
        def _approx_auc(labels: List[float], preds: List[float]) -> float:
            """Wilcoxon-Mann-Whitney AUC approximation."""
            if not labels or len(set(labels)) < 2:
                return 0.5
            pairs = sorted(zip(preds, labels), reverse=True)
            n_pos = sum(1 for _, l in pairs if l > 0.5)
            n_neg = len(pairs) - n_pos
            if n_pos == 0 or n_neg == 0:
                return 0.5
            rank_sum = 0.0
            for rank, (_, l) in enumerate(pairs, 1):
                if l > 0.5:
                    rank_sum += rank
            auc = (rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
            return 1.0 - auc  # flip because higher pred = higher rank


# ---------------------------------------------------------------------------
# NumPy fallback (no PyTorch / PyG)
# ---------------------------------------------------------------------------


class SC2BattleGNNFallback:
    """Minimal pure-NumPy fallback that mirrors the SC2BattleGNN API.

    Uses a simple heuristic: total_dps * total_hp ratio between sides.
    """

    def __init__(self, **kwargs: Any):
        log.info("SC2BattleGNNFallback initialised (no PyTorch).")

    def predict(self, snapshot: BattleSnapshot) -> float:
        friendly_power = 0.0
        enemy_power = 0.0
        for u in snapshot.units:
            power = (u.hp / max(u.max_hp, 1)) * u.dps * (1 + u.attack_range / 10)
            if u.player_id == 1:
                friendly_power += power
            else:
                enemy_power += power
        total = friendly_power + enemy_power
        if total < 1e-9:
            return 0.5
        return friendly_power / total

    def predict_batch(self, snapshots: Sequence[BattleSnapshot]) -> List[float]:
        return [self.predict(s) for s in snapshots]

    def fit(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        log.warning("Training not available in fallback mode.")
        return {"epochs_trained": 0}

    def save(self, path: str) -> None:
        log.warning("Save not available in fallback mode.")

    def load(self, path: str) -> None:
        log.warning("Load not available in fallback mode.")


# ---------------------------------------------------------------------------
# Synthetic data generator (for testing and demonstration)
# ---------------------------------------------------------------------------


def generate_synthetic_battle(
    min_units: int = 4,
    max_units: int = 20,
    rng: Optional[random.Random] = None,
) -> BattleSnapshot:
    """Generate a synthetic battle snapshot for testing."""
    if rng is None:
        rng = random.Random()

    unit_pool = list(UNIT_TYPES.keys())
    n_friendly = rng.randint(min_units // 2, max_units // 2)
    n_enemy = rng.randint(min_units // 2, max_units // 2)

    units: List[UnitState] = []
    uid = 0

    for player_id, count in [(1, n_friendly), (2, n_enemy)]:
        cx = rng.uniform(10, 50) if player_id == 1 else rng.uniform(50, 90)
        cy = rng.uniform(10, 90)
        for _ in range(count):
            utype = rng.choice(unit_pool)
            max_hp = rng.uniform(35, 500)
            units.append(
                UnitState(
                    unit_id=uid,
                    unit_type=utype,
                    hp=rng.uniform(max_hp * 0.3, max_hp),
                    max_hp=max_hp,
                    dps=rng.uniform(5, 40),
                    attack_range=rng.uniform(1, 13),
                    speed=rng.uniform(1.5, 5.5),
                    is_flying=rng.random() < 0.15,
                    x=cx + rng.gauss(0, 5),
                    y=cy + rng.gauss(0, 5),
                    player_id=player_id,
                )
            )
            uid += 1

    # Heuristic outcome (for synthetic data)
    fp = sum(u.hp * u.dps for u in units if u.player_id == 1)
    ep = sum(u.hp * u.dps for u in units if u.player_id == 2)
    outcome = 1.0 if fp > ep else 0.0

    return BattleSnapshot(units=units, outcome=outcome, tick=rng.randint(0, 10000))


def generate_synthetic_dataset(
    n: int = 500,
    seed: int = 42,
) -> List[BattleSnapshot]:
    """Generate *n* synthetic battle snapshots."""
    rng = random.Random(seed)
    return [generate_synthetic_battle(rng=rng) for _ in range(n)]


# ---------------------------------------------------------------------------
# Main demonstration
# ---------------------------------------------------------------------------


def main() -> None:
    """End-to-end demonstration: generate data, train, evaluate."""
    log.info("=== SC2 Battle GNN — Phase 596 Demo ===")

    snapshots = generate_synthetic_dataset(600, seed=123)
    log.info("Generated %d synthetic battles.", len(snapshots))

    if PYG_AVAILABLE and TORCH_AVAILABLE:
        graphs = build_dataset(snapshots)
        split = int(len(graphs) * 0.8)
        train_graphs = graphs[:split]
        val_graphs = graphs[split:]

        for arch in ("gcn", "gat", "sage", "mpnn"):
            log.info("--- Training %s ---", arch.upper())
            gnn = SC2BattleGNN(arch=arch, hidden=64, num_layers=3, lr=1e-3)
            results = gnn.fit(
                train_graphs, val_graphs, epochs=15, batch_size=32, patience=5
            )
            log.info(
                "%s: epochs=%d  best_val_loss=%.4f",
                arch.upper(),
                results["epochs_trained"],
                results["best_val_loss"],
            )

            # Single prediction
            prob = gnn.predict(snapshots[0])
            log.info(
                "  Sample prediction: %.3f  (actual: %.1f)", prob, snapshots[0].outcome
            )

        # Attention visualisation demo
        log.info("--- GAT Attention Demo ---")
        gat_model = SC2BattleGNN(arch="gat", hidden=64, num_layers=3)
        gat_model.fit(train_graphs, val_graphs, epochs=5, batch_size=32)
        attn = gat_model.get_attention_map(snapshots[0])
        if attn:
            log.info(
                "Attention map: %d units, %d layers captured.",
                len(attn["unit_names"]),
                len(attn["layers"]),
            )
    else:
        fb = SC2BattleGNNFallback()
        for snap in snapshots[:5]:
            p = fb.predict(snap)
            log.info("Fallback prediction: %.3f  (actual: %.1f)", p, snap.outcome)

    log.info("=== Phase 596 Demo Complete ===")


if __name__ == "__main__":
    main()
