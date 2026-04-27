# Phase 597: PEFT/LoRA
"""
sc2_strategy_lora.py — SC2 Strategy LLM Fine-Tuning with PEFT / LoRA

Fine-tunes a causal language model with Low-Rank Adaptation (LoRA) on
StarCraft II strategy instruction-response pairs.  Supports 4-bit / 8-bit
QLoRA, multiple matchup-specific adapters (ZvT, ZvP, ZvZ), adapter
hot-swapping, and memory-efficient training.

Graceful fallback to a stub implementation when transformers / peft /
bitsandbytes are absent.
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("sc2_strategy_lora")

# ---------------------------------------------------------------------------
# Optional imports
# ---------------------------------------------------------------------------
try:
    import torch
    import torch.nn as nn

    TORCH_AVAILABLE = True
    log.info("PyTorch %s available.", torch.__version__)
except ImportError:
    TORCH_AVAILABLE = False
    log.warning("PyTorch not installed.")

try:
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        TrainingArguments,
        Trainer,
        DataCollatorForLanguageModeling,
    )
    from datasets import Dataset as HFDataset

    TRANSFORMERS_AVAILABLE = True
    log.info("Transformers available.")
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    log.warning(
        "transformers not installed. Install with: pip install transformers datasets"
    )

try:
    from peft import (
        LoraConfig,
        TaskType,
        get_peft_model,
        PeftModel,
        prepare_model_for_kbit_training,
    )

    PEFT_AVAILABLE = True
    log.info("PEFT available.")
except ImportError:
    PEFT_AVAILABLE = False
    log.warning("peft not installed. Install with: pip install peft")

try:
    import bitsandbytes as bnb  # noqa: F401

    BNB_AVAILABLE = True
    log.info("bitsandbytes available.")
except ImportError:
    BNB_AVAILABLE = False
    log.warning("bitsandbytes not installed. QLoRA quantisation disabled.")

# ---------------------------------------------------------------------------
# SC2 matchup definitions
# ---------------------------------------------------------------------------
MATCHUPS = ("ZvT", "ZvP", "ZvZ")

# ---------------------------------------------------------------------------
# SC2 strategy dataset
# ---------------------------------------------------------------------------


@dataclass
class SC2StrategyExample:
    """A single instruction-response pair for strategy fine-tuning."""

    instruction: str
    response: str
    matchup: str = "ZvT"
    game_phase: str = "mid"  # early / mid / late
    tags: List[str] = field(default_factory=list)


# -- Curated dataset -------------------------------------------------------

_STRATEGY_DATA: List[Dict[str, str]] = [
    # ZvT
    {
        "matchup": "ZvT",
        "instruction": "How should I respond to a Terran 2-1-1 timing push as Zerg?",
        "response": (
            "Against a 2-1-1 timing push, prioritize Zergling-Baneling-Queen defense. "
            "Build 2 extra Queens and a Baneling Nest by 3:30. Spread creep aggressively "
            "toward the third base. When the push arrives (~5:00), use Queens for "
            "Transfuse micro on your third Hatchery while Banelings connect on the "
            "Marines. Keep Zerglings on a separate hotkey to flank. After defending, "
            "immediately drone to 66 workers and transition into Lair tech."
        ),
    },
    {
        "matchup": "ZvT",
        "instruction": "What is the optimal Roach-Ravager timing attack against mech Terran?",
        "response": (
            "The Roach-Ravager timing works best at ~6:30 before Siege Tanks reach "
            "critical mass. Build 8 Roaches and 4 Ravagers off 3 bases with +1 Missile "
            "Attack. Use Corrosive Bile to force Tank un-sieges and snipe key buildings. "
            "If mech is committed, transition to Swarm Hosts and Vipers for the late game. "
            "Keep producing Drones behind the attack — this is a harass, not an all-in."
        ),
    },
    {
        "matchup": "ZvT",
        "instruction": "How do I use Vipers effectively against Terran mech?",
        "response": (
            "Vipers are essential vs mech. Build 4-6 Vipers and keep them behind your "
            "army. Use Abduct to pull Siege Tanks and Thors into your Roach-Hydra ball. "
            "Blinding Cloud shuts down Tank siege damage. Always Consume off Overlords "
            "to maintain energy. Position Vipers on a separate control group and retreat "
            "them immediately after casting — they are fragile and expensive."
        ),
    },
    # ZvP
    {
        "matchup": "ZvP",
        "instruction": "How do I defend against Protoss cannon rush?",
        "response": (
            "Scout the Probe entering your natural at ~1:30. If you see a Forge before "
            "Gateway, immediately pull 3-4 Drones to kill the Probe and deny the first "
            "Pylon. If a cannon completes, do NOT engage it — instead take a hidden base "
            "and build a Roach Warren. 5 Roaches break any follow-up cannons. Rally "
            "Zerglings to deny Probe scouting. Most cannon rushes fail if the first "
            "cannon is denied."
        ),
    },
    {
        "matchup": "ZvP",
        "instruction": "What is the best late-game composition against Skytoss?",
        "response": (
            "Against Carrier-Tempest-Mothership, the answer is Corruptor-Viper with "
            "Infestors. Corruptors tank and deal anti-air DPS. Vipers cast Parasitic Bomb "
            "on clumped air units and Abduct high-value targets (Mothership, Carriers). "
            "Infestors use Neural Parasite on the Mothership to disable Mass Recall. "
            "Always have Spore Crawler forests at key bases. Remax on Corruptors "
            "immediately after each fight."
        ),
    },
    {
        "matchup": "ZvP",
        "instruction": "How should I play the Zergling-Baneling-Hydra style vs Protoss?",
        "response": (
            "This aggressive style works against Gateway-heavy Protoss. Get Ling speed "
            "and Baneling Nest off 3 Hatcheries. Morph 8-12 Banelings and rally Hydras "
            "from the Hydralisk Den. Attack when you hit ~60 supply with +1 Melee and "
            "+1 Missile. Banelings target Zealots, Hydras focus Stalkers. Keep "
            "reinforcement rallies short. This style falls off if the game goes past "
            "10 minutes, so commit to damage or transition."
        ),
    },
    # ZvZ
    {
        "matchup": "ZvZ",
        "instruction": "How do I win the early Zergling wars in ZvZ?",
        "response": (
            "Early ZvZ revolves around Zergling micro and economy balance. Open Hatch "
            "first only if you scout no Pool first. Get Metabolic Boost at 100 gas, then "
            "pull Drones off gas. Build 6-8 Zerglings and send them across the map. "
            "Micro tip: split Zerglings into two groups and surround from both sides. "
            "Always keep a Zergling at the opponent's natural to scout. If they commit "
            "to Drones, punish with 12 lings. If they match lings, drone behind yours."
        ),
    },
    {
        "matchup": "ZvZ",
        "instruction": "When should I transition to Roaches in ZvZ?",
        "response": (
            "Transition to Roaches when Ling-Bane becomes too volatile (~4:30 game time). "
            "Build a Roach Warren at 3:30 and produce 6 Roaches at ~4:00. Roaches counter "
            "Zerglings and survive Baneling hits. Get +1 Missile Attack and Roach Speed "
            "(Glial Reconstitution) for timing attacks. In Roach vs Roach, the player "
            "with better upgrades and Ravager support wins. Always get an Overseer for "
            "detection in case of Burrowed Roach play."
        ),
    },
    {
        "matchup": "ZvZ",
        "instruction": "How do I play the Mutalisk transition in ZvZ?",
        "response": (
            "Mutalisks in ZvZ are high-risk, high-reward. Rush Lair at ~3:30 and start "
            "the Spire immediately. While Spire builds, defend with Roaches and Zerglings. "
            "The first 7 Mutalisks arrive at ~6:00. Immediately harass mineral lines — "
            "each killed Drone is worth more than a Mutalisk. Stack Mutalisks tightly "
            "with shift-click commands. Counter: if your opponent goes Mutalisks, build "
            "4 Queens at each base plus Spore Crawlers and race to Hydralisks."
        ),
    },
    # General
    {
        "matchup": "ZvT",
        "instruction": "What are the key macro benchmarks for a Zerg player?",
        "response": (
            "Key benchmarks: 36 Drones by 4:00, 66 Drones by 6:00, 80 Drones by 7:30. "
            "Inject every Hatchery every 25 seconds. Spread creep with Queens constantly. "
            "Never bank over 1000 minerals — if you do, build Hatcheries or units. "
            "Always have at least 1 Overlord scouting the map. Supply block = lost games. "
            "Pre-make Overlords: 1 at 13 supply, 2 at 30, 3 at 44. Keep larvae under 3 "
            "per Hatchery — if larvae are capping, you are floating resources."
        ),
    },
]


def build_sc2_strategy_dataset(
    matchup_filter: Optional[str] = None,
    augment_factor: int = 1,
    seed: int = 42,
) -> List[SC2StrategyExample]:
    """Build the SC2 strategy dataset with optional matchup filtering.

    Parameters
    ----------
    matchup_filter : str, optional
        If set, only include examples for this matchup (e.g., ``"ZvT"``).
    augment_factor : int
        Repeat and slightly vary examples this many times.
    seed : int
        Random seed for augmentation.
    """
    rng = random.Random(seed)
    examples: List[SC2StrategyExample] = []

    for item in _STRATEGY_DATA:
        if matchup_filter and item["matchup"] != matchup_filter:
            continue
        for _ in range(augment_factor):
            examples.append(
                SC2StrategyExample(
                    instruction=item["instruction"],
                    response=item["response"],
                    matchup=item["matchup"],
                )
            )

    rng.shuffle(examples)
    log.info(
        "Built SC2 strategy dataset: %d examples (filter=%s, augment=%dx).",
        len(examples),
        matchup_filter or "all",
        augment_factor,
    )
    return examples


def format_prompt(example: SC2StrategyExample) -> str:
    """Format a strategy example as an instruction-following prompt."""
    return (
        f"### Matchup: {example.matchup}\n"
        f"### Instruction:\n{example.instruction}\n\n"
        f"### Response:\n{example.response}"
    )


# ---------------------------------------------------------------------------
# LoRA configuration profiles
# ---------------------------------------------------------------------------


@dataclass
class LoRAProfile:
    """Encapsulates a LoRA hyperparameter configuration."""

    name: str = "default"
    r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: List[str] = field(
        default_factory=lambda: [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ]
    )
    bias: str = "none"
    task_type: str = "CAUSAL_LM"


LORA_PROFILES: Dict[str, LoRAProfile] = {
    "default": LoRAProfile(),
    "aggressive": LoRAProfile(name="aggressive", r=32, lora_alpha=64, lora_dropout=0.1),
    "lightweight": LoRAProfile(
        name="lightweight",
        r=8,
        lora_alpha=16,
        lora_dropout=0.0,
        target_modules=["q_proj", "v_proj"],
    ),
}


# ============================================================================
# SC2StrategyLoRA — Main class
# ============================================================================

if TORCH_AVAILABLE and TRANSFORMERS_AVAILABLE and PEFT_AVAILABLE:

    class SC2StrategyLoRA:
        """Fine-tune a causal LM on SC2 strategy data using LoRA / QLoRA.

        Parameters
        ----------
        base_model_name : str
            HuggingFace model identifier (e.g. ``"meta-llama/Llama-2-7b-hf"``).
        profile : str or LoRAProfile
            LoRA hyperparameter profile name or instance.
        quantize : str or None
            ``"4bit"``, ``"8bit"``, or ``None`` for full precision.
        device : str
            Target device (``"cuda"``, ``"cpu"``).
        max_seq_len : int
            Maximum sequence length for tokenisation.
        output_dir : str
            Directory for checkpoints and adapters.
        """

        def __init__(
            self,
            base_model_name: str = "meta-llama/Llama-2-7b-hf",
            profile: str | LoRAProfile = "default",
            quantize: Optional[str] = "4bit",
            device: str = "auto",
            max_seq_len: int = 512,
            output_dir: str = "./sc2_lora_output",
        ):
            self.base_model_name = base_model_name
            self.max_seq_len = max_seq_len
            self.output_dir = Path(output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.device = device
            self.quantize = quantize

            # Resolve LoRA profile
            if isinstance(profile, str):
                self.lora_profile = LORA_PROFILES.get(profile, LORA_PROFILES["default"])
            else:
                self.lora_profile = profile

            # Loaded state (lazy)
            self._tokenizer: Optional[Any] = None
            self._base_model: Optional[Any] = None
            self._peft_model: Optional[Any] = None
            self._active_adapter: Optional[str] = None
            self._adapter_registry: Dict[str, str] = {}  # name -> path

            log.info(
                "SC2StrategyLoRA initialised  model=%s  quantize=%s  lora_r=%d  alpha=%d",
                base_model_name,
                quantize,
                self.lora_profile.r,
                self.lora_profile.lora_alpha,
            )

        # -- Model loading --------------------------------------------------

        def _get_bnb_config(self) -> Optional[Any]:
            """Build BitsAndBytesConfig for quantised loading."""
            if not BNB_AVAILABLE or self.quantize is None:
                return None

            if self.quantize == "4bit":
                return BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.bfloat16,
                    bnb_4bit_use_double_quant=True,
                )
            elif self.quantize == "8bit":
                return BitsAndBytesConfig(load_in_8bit=True)
            else:
                log.warning(
                    "Unknown quantize=%s, loading in full precision.", self.quantize
                )
                return None

        def load_base_model(self) -> None:
            """Load the base model and tokenizer (with optional quantisation)."""
            log.info("Loading tokenizer: %s", self.base_model_name)
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.base_model_name,
                trust_remote_code=True,
            )
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
                self._tokenizer.pad_token_id = self._tokenizer.eos_token_id

            bnb_config = self._get_bnb_config()
            log.info(
                "Loading base model: %s (quantize=%s)",
                self.base_model_name,
                self.quantize,
            )

            load_kwargs: Dict[str, Any] = {
                "trust_remote_code": True,
                "device_map": self.device,
            }
            if bnb_config is not None:
                load_kwargs["quantization_config"] = bnb_config

            self._base_model = AutoModelForCausalLM.from_pretrained(
                self.base_model_name,
                **load_kwargs,
            )

            # Prepare for k-bit training if quantised
            if self.quantize in ("4bit", "8bit") and BNB_AVAILABLE:
                self._base_model = prepare_model_for_kbit_training(self._base_model)

            log.info(
                "Base model loaded. Parameters: %d",
                sum(p.numel() for p in self._base_model.parameters()),
            )

        def _build_lora_config(self, adapter_name: str = "default") -> LoraConfig:
            """Create a PEFT LoraConfig from the current profile."""
            return LoraConfig(
                r=self.lora_profile.r,
                lora_alpha=self.lora_profile.lora_alpha,
                lora_dropout=self.lora_profile.lora_dropout,
                target_modules=self.lora_profile.target_modules,
                bias=self.lora_profile.bias,
                task_type=TaskType.CAUSAL_LM,
            )

        def apply_lora(self, adapter_name: str = "default") -> None:
            """Wrap the base model with a LoRA adapter."""
            if self._base_model is None:
                self.load_base_model()

            lora_config = self._build_lora_config(adapter_name)
            self._peft_model = get_peft_model(self._base_model, lora_config)
            self._active_adapter = adapter_name

            trainable = sum(
                p.numel() for p in self._peft_model.parameters() if p.requires_grad
            )
            total = sum(p.numel() for p in self._peft_model.parameters())
            pct = 100.0 * trainable / total if total > 0 else 0.0
            log.info(
                "LoRA applied (adapter=%s): trainable=%d / %d (%.2f%%)",
                adapter_name,
                trainable,
                total,
                pct,
            )

        # -- Dataset preparation --------------------------------------------

        def prepare_dataset(
            self,
            examples: List[SC2StrategyExample],
            val_split: float = 0.1,
        ) -> Tuple[HFDataset, HFDataset]:
            """Tokenise SC2 strategy examples into HuggingFace Datasets."""
            if self._tokenizer is None:
                raise RuntimeError(
                    "Tokenizer not loaded. Call load_base_model() first."
                )

            texts = [format_prompt(ex) for ex in examples]

            # Tokenise
            encodings = self._tokenizer(
                texts,
                truncation=True,
                max_length=self.max_seq_len,
                padding="max_length",
                return_tensors="np",
            )

            data_dict = {
                "input_ids": encodings["input_ids"].tolist(),
                "attention_mask": encodings["attention_mask"].tolist(),
                "labels": encodings[
                    "input_ids"
                ].tolist(),  # causal LM: labels = input_ids
            }

            dataset = HFDataset.from_dict(data_dict)
            split = dataset.train_test_split(test_size=val_split, seed=42)
            log.info(
                "Dataset prepared: train=%d  val=%d  max_len=%d",
                len(split["train"]),
                len(split["test"]),
                self.max_seq_len,
            )
            return split["train"], split["test"]

        # -- Training -------------------------------------------------------

        def train(
            self,
            train_dataset: Any,
            val_dataset: Optional[Any] = None,
            epochs: int = 3,
            batch_size: int = 4,
            gradient_accumulation_steps: int = 4,
            learning_rate: float = 2e-4,
            warmup_ratio: float = 0.03,
            weight_decay: float = 0.01,
            fp16: bool = False,
            bf16: bool = True,
            logging_steps: int = 10,
            save_steps: int = 100,
            max_grad_norm: float = 0.3,
        ) -> Dict[str, Any]:
            """Train the LoRA adapter with gradient accumulation.

            Returns training metrics.
            """
            if self._peft_model is None:
                raise RuntimeError("LoRA not applied. Call apply_lora() first.")

            run_dir = self.output_dir / f"run_{int(time.time())}"

            training_args = TrainingArguments(
                output_dir=str(run_dir),
                num_train_epochs=epochs,
                per_device_train_batch_size=batch_size,
                per_device_eval_batch_size=batch_size,
                gradient_accumulation_steps=gradient_accumulation_steps,
                learning_rate=learning_rate,
                warmup_ratio=warmup_ratio,
                weight_decay=weight_decay,
                fp16=fp16,
                bf16=bf16,
                logging_steps=logging_steps,
                save_steps=save_steps,
                save_total_limit=3,
                max_grad_norm=max_grad_norm,
                evaluation_strategy="steps" if val_dataset else "no",
                eval_steps=save_steps if val_dataset else None,
                report_to="none",
                remove_unused_columns=False,
                optim=(
                    "paged_adamw_8bit"
                    if self.quantize in ("4bit", "8bit")
                    else "adamw_torch"
                ),
                lr_scheduler_type="cosine",
                group_by_length=True,
            )

            data_collator = DataCollatorForLanguageModeling(
                tokenizer=self._tokenizer,
                mlm=False,
            )

            trainer = Trainer(
                model=self._peft_model,
                args=training_args,
                train_dataset=train_dataset,
                eval_dataset=val_dataset,
                data_collator=data_collator,
            )

            log.info(
                "Starting LoRA training: epochs=%d  lr=%.1e  grad_accum=%d",
                epochs,
                learning_rate,
                gradient_accumulation_steps,
            )
            train_result = trainer.train()
            metrics = train_result.metrics
            log.info("Training complete: %s", metrics)

            # Save adapter
            adapter_path = str(run_dir / "final_adapter")
            self._peft_model.save_pretrained(adapter_path)
            self._tokenizer.save_pretrained(adapter_path)
            self._adapter_registry[self._active_adapter or "default"] = adapter_path
            log.info("Adapter saved to %s", adapter_path)

            return metrics

        # -- Multi-adapter management (ZvT / ZvP / ZvZ) --------------------

        def train_matchup_adapters(
            self,
            all_examples: List[SC2StrategyExample],
            matchups: Sequence[str] = MATCHUPS,
            epochs: int = 3,
            **train_kwargs: Any,
        ) -> Dict[str, Dict[str, Any]]:
            """Train separate LoRA adapters for each matchup.

            Returns a dict of matchup -> training metrics.
            """
            results: Dict[str, Dict[str, Any]] = {}

            for matchup in matchups:
                log.info("=== Training adapter for %s ===", matchup)
                examples = [ex for ex in all_examples if ex.matchup == matchup]
                if not examples:
                    log.warning("No examples for matchup %s, skipping.", matchup)
                    continue

                # Re-apply fresh LoRA for each matchup
                self.apply_lora(adapter_name=matchup)
                train_ds, val_ds = self.prepare_dataset(examples)
                metrics = self.train(train_ds, val_ds, epochs=epochs, **train_kwargs)
                results[matchup] = metrics

            return results

        def load_adapter(
            self, adapter_name: str, adapter_path: Optional[str] = None
        ) -> None:
            """Load a saved LoRA adapter by name or path."""
            if self._base_model is None:
                self.load_base_model()

            path = adapter_path or self._adapter_registry.get(adapter_name)
            if path is None:
                raise FileNotFoundError(
                    f"No adapter found for '{adapter_name}'. "
                    f"Available: {list(self._adapter_registry.keys())}"
                )

            self._peft_model = PeftModel.from_pretrained(
                self._base_model,
                path,
            )
            self._active_adapter = adapter_name
            log.info("Adapter '%s' loaded from %s", adapter_name, path)

        def switch_adapter(self, adapter_name: str) -> None:
            """Switch to a different loaded adapter (hot-swap)."""
            if adapter_name in self._adapter_registry:
                self.load_adapter(adapter_name)
            else:
                raise KeyError(
                    f"Adapter '{adapter_name}' not in registry. "
                    f"Available: {list(self._adapter_registry.keys())}"
                )

        # -- Adapter merging ------------------------------------------------

        def merge_adapter(self) -> None:
            """Merge LoRA weights into the base model (irreversible)."""
            if self._peft_model is None:
                raise RuntimeError("No LoRA adapter to merge.")
            self._peft_model = self._peft_model.merge_and_unload()
            log.info("LoRA adapter merged into base model.")

        def unmerge_adapter(self) -> None:
            """Unmerge LoRA weights (only if not yet permanently merged)."""
            if self._peft_model is None:
                raise RuntimeError("No LoRA adapter loaded.")
            if hasattr(self._peft_model, "unmerge_adapter"):
                self._peft_model.unmerge_adapter()
                log.info("LoRA adapter unmerged.")
            else:
                log.warning("Cannot unmerge — model may have been permanently merged.")

        # -- Saving / Loading -----------------------------------------------

        def save_adapter(self, path: str, adapter_name: Optional[str] = None) -> None:
            """Save the current LoRA adapter weights."""
            if self._peft_model is None:
                raise RuntimeError("No LoRA model to save.")
            self._peft_model.save_pretrained(path)
            if self._tokenizer:
                self._tokenizer.save_pretrained(path)
            name = adapter_name or self._active_adapter or "default"
            self._adapter_registry[name] = path
            log.info("Adapter '%s' saved to %s", name, path)

        def save_merged_model(self, path: str) -> None:
            """Merge adapter and save the full model."""
            self.merge_adapter()
            self._peft_model.save_pretrained(path)
            if self._tokenizer:
                self._tokenizer.save_pretrained(path)
            log.info("Merged model saved to %s", path)

        # -- Inference ------------------------------------------------------

        @torch.no_grad()
        def generate(
            self,
            instruction: str,
            matchup: str = "ZvT",
            max_new_tokens: int = 256,
            temperature: float = 0.7,
            top_p: float = 0.9,
            do_sample: bool = True,
        ) -> str:
            """Generate a strategy response for a given instruction."""
            model = self._peft_model or self._base_model
            if model is None or self._tokenizer is None:
                raise RuntimeError("Model not loaded.")

            model.eval()
            prompt = (
                f"### Matchup: {matchup}\n"
                f"### Instruction:\n{instruction}\n\n"
                f"### Response:\n"
            )

            inputs = self._tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=self.max_seq_len,
            )
            input_ids = inputs["input_ids"].to(model.device)
            attention_mask = inputs["attention_mask"].to(model.device)

            outputs = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=do_sample,
                pad_token_id=self._tokenizer.eos_token_id,
            )

            generated = outputs[0][input_ids.shape[-1] :]
            response = self._tokenizer.decode(generated, skip_special_tokens=True)
            return response.strip()

        def generate_for_matchup(
            self,
            instruction: str,
            matchup: str = "ZvT",
            **gen_kwargs: Any,
        ) -> str:
            """Switch to the matchup-specific adapter and generate."""
            if matchup in self._adapter_registry and matchup != self._active_adapter:
                self.switch_adapter(matchup)
            return self.generate(instruction, matchup=matchup, **gen_kwargs)

        # -- Evaluation -----------------------------------------------------

        @torch.no_grad()
        def compute_perplexity(self, dataset: Any, batch_size: int = 4) -> float:
            """Compute perplexity on a dataset."""
            model = self._peft_model or self._base_model
            if model is None:
                raise RuntimeError("Model not loaded.")

            model.eval()
            total_loss = 0.0
            total_tokens = 0

            for i in range(0, len(dataset), batch_size):
                batch = dataset[i : i + batch_size]
                input_ids = torch.tensor(batch["input_ids"], device=model.device)
                attention_mask = torch.tensor(
                    batch["attention_mask"], device=model.device
                )
                labels = input_ids.clone()
                labels[attention_mask == 0] = -100

                outputs = model(
                    input_ids=input_ids, attention_mask=attention_mask, labels=labels
                )
                loss = outputs.loss
                n_tokens = (labels != -100).sum().item()
                total_loss += loss.item() * n_tokens
                total_tokens += n_tokens

            ppl = math.exp(total_loss / max(total_tokens, 1))
            log.info("Perplexity: %.2f (%d tokens)", ppl, total_tokens)
            return ppl

        def evaluate_sc2_metrics(
            self,
            test_examples: List[SC2StrategyExample],
            max_examples: int = 50,
        ) -> Dict[str, float]:
            """Custom SC2 evaluation metrics.

            Metrics:
            - response_length: average response token count
            - keyword_coverage: fraction of strategy keywords mentioned
            - matchup_accuracy: whether the response mentions the correct matchup units
            """
            sc2_keywords = {
                "ZvT": [
                    "marine",
                    "tank",
                    "medivac",
                    "baneling",
                    "zergling",
                    "roach",
                    "hydra",
                    "viper",
                    "queen",
                    "creep",
                    "mech",
                    "bio",
                ],
                "ZvP": [
                    "zealot",
                    "stalker",
                    "colossus",
                    "carrier",
                    "immortal",
                    "corruptor",
                    "infestor",
                    "baneling",
                    "roach",
                    "queen",
                    "cannon",
                ],
                "ZvZ": [
                    "zergling",
                    "baneling",
                    "roach",
                    "mutalisk",
                    "queen",
                    "drone",
                    "speed",
                    "spire",
                    "pool",
                ],
            }

            results: Dict[str, List[float]] = {
                "response_length": [],
                "keyword_coverage": [],
                "matchup_accuracy": [],
            }

            for ex in test_examples[:max_examples]:
                try:
                    response = self.generate(
                        ex.instruction, matchup=ex.matchup, max_new_tokens=200
                    )
                except Exception as e:
                    log.warning("Generation failed: %s", e)
                    continue

                # Response length
                tokens = self._tokenizer.encode(response)
                results["response_length"].append(len(tokens))

                # Keyword coverage
                keywords = sc2_keywords.get(ex.matchup, [])
                if keywords:
                    hits = sum(1 for kw in keywords if kw.lower() in response.lower())
                    results["keyword_coverage"].append(hits / len(keywords))

                # Matchup accuracy (does response reference correct matchup units?)
                matchup_units = {
                    "ZvT": ["terran", "marine", "tank"],
                    "ZvP": ["protoss", "zealot", "stalker"],
                    "ZvZ": ["zerg", "zergling", "roach"],
                }
                mu = matchup_units.get(ex.matchup, [])
                if mu:
                    found = any(u.lower() in response.lower() for u in mu)
                    results["matchup_accuracy"].append(1.0 if found else 0.0)

            metrics = {k: float(np.mean(v)) if v else 0.0 for k, v in results.items()}
            log.info("SC2 Metrics: %s", metrics)
            return metrics

        # -- Info -----------------------------------------------------------

        def get_adapter_info(self) -> Dict[str, Any]:
            """Return information about the current model and adapters."""
            info: Dict[str, Any] = {
                "base_model": self.base_model_name,
                "quantize": self.quantize,
                "lora_profile": {
                    "name": self.lora_profile.name,
                    "r": self.lora_profile.r,
                    "alpha": self.lora_profile.lora_alpha,
                    "dropout": self.lora_profile.lora_dropout,
                    "target_modules": self.lora_profile.target_modules,
                },
                "active_adapter": self._active_adapter,
                "registered_adapters": list(self._adapter_registry.keys()),
            }
            if self._peft_model is not None:
                trainable = sum(
                    p.numel() for p in self._peft_model.parameters() if p.requires_grad
                )
                total = sum(p.numel() for p in self._peft_model.parameters())
                info["trainable_params"] = trainable
                info["total_params"] = total
                info["trainable_pct"] = 100.0 * trainable / total if total > 0 else 0.0
            return info


# ---------------------------------------------------------------------------
# Fallback (no PEFT / transformers)
# ---------------------------------------------------------------------------


class SC2StrategyLoRAFallback:
    """Minimal stub that mirrors the SC2StrategyLoRA API without real models."""

    def __init__(self, **kwargs: Any):
        self._adapter_registry: Dict[str, str] = {}
        log.info("SC2StrategyLoRAFallback initialised (no PEFT/transformers).")

    def load_base_model(self) -> None:
        log.info("[Fallback] Base model loading simulated.")

    def apply_lora(self, adapter_name: str = "default") -> None:
        log.info("[Fallback] LoRA adapter '%s' applied (simulated).", adapter_name)

    def prepare_dataset(
        self,
        examples: List[SC2StrategyExample],
        val_split: float = 0.1,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        split_idx = max(1, int(len(examples) * (1 - val_split)))
        train = [{"text": format_prompt(ex)} for ex in examples[:split_idx]]
        val = [{"text": format_prompt(ex)} for ex in examples[split_idx:]]
        return train, val

    def train(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        log.warning("[Fallback] Training not available.")
        return {"train_loss": 0.0}

    def generate(
        self,
        instruction: str,
        matchup: str = "ZvT",
        **kwargs: Any,
    ) -> str:
        """Return a heuristic response based on keyword matching."""
        instruction_lower = instruction.lower()
        for item in _STRATEGY_DATA:
            if item["matchup"] == matchup:
                # Simple keyword overlap scoring
                words = set(instruction_lower.split())
                ref_words = set(item["instruction"].lower().split())
                overlap = len(words & ref_words)
                if overlap > 3:
                    return item["response"]
        # Default
        return (
            f"In {matchup}, focus on scouting, macro benchmarks, and proper "
            f"unit composition. Adapt to your opponent's strategy."
        )

    def save_adapter(self, path: str, **kwargs: Any) -> None:
        log.warning("[Fallback] Save not available.")

    def load_adapter(self, name: str, path: Optional[str] = None) -> None:
        log.warning("[Fallback] Load not available.")

    def compute_perplexity(self, *args: Any, **kwargs: Any) -> float:
        return 0.0

    def get_adapter_info(self) -> Dict[str, Any]:
        return {"mode": "fallback", "adapters": []}


# ---------------------------------------------------------------------------
# Main demonstration
# ---------------------------------------------------------------------------


def main() -> None:
    """End-to-end demonstration of SC2 strategy LoRA fine-tuning."""
    log.info("=== SC2 Strategy LoRA — Phase 597 Demo ===")

    # Build dataset
    examples = build_sc2_strategy_dataset(augment_factor=3)
    log.info("Total examples: %d", len(examples))

    for matchup in MATCHUPS:
        count = sum(1 for ex in examples if ex.matchup == matchup)
        log.info("  %s: %d examples", matchup, count)

    if TORCH_AVAILABLE and TRANSFORMERS_AVAILABLE and PEFT_AVAILABLE:
        log.info("--- Full PEFT/LoRA pipeline available ---")

        # Show configuration
        for name, profile in LORA_PROFILES.items():
            log.info(
                "  Profile '%s': r=%d alpha=%d dropout=%.2f targets=%s",
                name,
                profile.r,
                profile.lora_alpha,
                profile.lora_dropout,
                profile.target_modules,
            )

        # Demonstrate adapter info (without loading a real model)
        log.info("To run full training:")
        log.info(
            "  lora = SC2StrategyLoRA(base_model_name='meta-llama/Llama-2-7b-hf', quantize='4bit')"
        )
        log.info("  lora.load_base_model()")
        log.info("  lora.apply_lora('ZvT')")
        log.info("  train_ds, val_ds = lora.prepare_dataset(examples)")
        log.info("  lora.train(train_ds, val_ds, epochs=3)")
        log.info("  response = lora.generate('How to beat bio Terran?', matchup='ZvT')")
    else:
        fb = SC2StrategyLoRAFallback()
        fb.load_base_model()
        fb.apply_lora("ZvT")

        # Demonstrate fallback generation
        test_prompts = [
            ("How should I respond to a Terran 2-1-1 timing push as Zerg?", "ZvT"),
            ("How do I defend against Protoss cannon rush?", "ZvP"),
            ("How do I win the early Zergling wars in ZvZ?", "ZvZ"),
        ]
        for instruction, matchup in test_prompts:
            response = fb.generate(instruction, matchup=matchup)
            log.info("[%s] Q: %s", matchup, instruction[:60])
            log.info("       A: %s", response[:120] + "...")

    log.info("=== Phase 597 Demo Complete ===")


if __name__ == "__main__":
    main()
