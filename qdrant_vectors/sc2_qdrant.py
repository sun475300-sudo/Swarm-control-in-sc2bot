# SC2 Bot - Qdrant Vector Database
# Strategy embeddings with payload filtering and recommendation API

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition,
    MatchValue, Range, ScoredPoint, RecommendRequest,
    CreateCollection, OptimizersConfigDiff, HnswConfigDiff,
    UpdateResult, SearchRequest, SearchParams,
)
from typing import List, Optional, Dict, Any
import uuid

# --- Client Setup ---
client = QdrantClient(host="localhost", port=6333)

# --- Collection: sc2_strategies ---
COLLECTION_NAME = "sc2_strategies"
VECTOR_DIM = 1536  # OpenAI text-embedding-3-small

def create_collection():
    """Create sc2_strategies collection with HNSW index."""
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_DIM,
            distance=Distance.COSINE,
            on_disk=False,
        ),
        hnsw_config=HnswConfigDiff(
            m=16,
            ef_construct=200,
            full_scan_threshold=10_000,
        ),
        optimizers_config=OptimizersConfigDiff(
            indexing_threshold=20_000,
            memmap_threshold=50_000,
        ),
        on_disk_payload=False,
    )
    # Create payload indexes for fast filtering
    client.create_payload_index(COLLECTION_NAME, "race",      models.PayloadSchemaType.KEYWORD)
    client.create_payload_index(COLLECTION_NAME, "map",       models.PayloadSchemaType.KEYWORD)
    client.create_payload_index(COLLECTION_NAME, "win_rate",  models.PayloadSchemaType.FLOAT)
    client.create_payload_index(COLLECTION_NAME, "matchup",   models.PayloadSchemaType.KEYWORD)
    print(f"[Qdrant] Created collection: {COLLECTION_NAME}")

# --- Upsert Strategies ---
def upsert_strategies(strategies: List[dict], vectors: List[List[float]]):
    """Upsert strategy points with payload and embedding vectors."""
    points = [
        PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, s["strategy_name"])),
            vector=v,
            payload={
                "strategy_name": s["strategy_name"],
                "race":          s["race"],
                "matchup":       s["matchup"],
                "map":           s.get("map", "any"),
                "win_rate":      s["win_rate"],
                "difficulty":    s.get("difficulty", "medium"),
                "tags":          s.get("tags", []),
                "description":   s.get("description", ""),
            },
        )
        for s, v in zip(strategies, vectors)
    ]
    result: UpdateResult = client.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)
    print(f"[Qdrant] Upserted {len(points)} strategies: status={result.status}")

# --- Search with Payload Filtering ---
def search_strategies(
    query_vector: List[float],
    race: Optional[str] = None,
    min_win_rate: float = 0.0,
    map_name: Optional[str] = None,
    top_k: int = 10,
) -> List[ScoredPoint]:
    """Search for similar strategies with payload filters."""
    must_conditions = [
        FieldCondition(key="win_rate", range=Range(gte=min_win_rate))
    ]
    if race:
        must_conditions.append(FieldCondition(key="race", match=MatchValue(value=race)))
    if map_name:
        must_conditions.append(FieldCondition(key="map", match=MatchValue(value=map_name)))

    query_filter = Filter(must=must_conditions) if must_conditions else None

    return client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        query_filter=query_filter,
        limit=top_k,
        with_payload=True,
        with_vectors=False,
        search_params=SearchParams(hnsw_ef=128, exact=False),
    )

# --- Recommendation API ---
def recommend_similar_strategies(
    positive_ids: List[str],
    negative_ids: Optional[List[str]] = None,
    race: Optional[str] = None,
    top_k: int = 5,
) -> List[ScoredPoint]:
    """Find strategies similar to positives and dissimilar to negatives."""
    must_conditions = []
    if race:
        must_conditions.append(FieldCondition(key="race", match=MatchValue(value=race)))

    return client.recommend(
        collection_name=COLLECTION_NAME,
        positive=positive_ids,
        negative=negative_ids or [],
        query_filter=Filter(must=must_conditions) if must_conditions else None,
        limit=top_k,
        with_payload=True,
    )

# --- Scroll: Browse all strategies ---
def scroll_all_strategies(race: Optional[str] = None, limit: int = 100) -> List[dict]:
    """Scroll through all strategies in the collection."""
    scroll_filter = None
    if race:
        scroll_filter = Filter(must=[FieldCondition(key="race", match=MatchValue(value=race))])
    records, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=scroll_filter,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )
    return [r.payload for r in records]

if __name__ == "__main__":
    create_collection()
    import random
    dummy_vector = [random.random() for _ in range(VECTOR_DIM)]
    upsert_strategies(
        [{"strategy_name": "Ling Flood", "race": "Zerg", "matchup": "ZvT",
          "win_rate": 0.60, "tags": ["rush"], "description": "Fast ling flood pressure"}],
        [dummy_vector],
    )
    results = search_strategies(dummy_vector, race="Zerg", min_win_rate=0.5)
    for r in results:
        print(f"[Qdrant] {r.payload['strategy_name']} score={r.score:.4f}")
