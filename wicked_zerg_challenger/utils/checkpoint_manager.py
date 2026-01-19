# -*- coding: utf-8 -*-
"""
Checkpoint Manager - Auto-resume for training crashes

Provides checkpoint saving/loading for automatic resume after crashes.
Integrates with replay_crash_handler for comprehensive crash recovery.
"""

import json
import pickle
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import shutil


class CheckpointManager:
    """
    Manages training checkpoints for auto-resume functionality.
    
    Saves:
    - Model weights/state
    - Training progress (game count, win/loss stats)
    - Bot configuration
    - Learning parameters
    
    Usage:
        manager = CheckpointManager(checkpoint_dir)
        manager.save_checkpoint(iteration, model_state, training_stats)
        latest = manager.load_latest_checkpoint()  # Returns (iteration, state, stats)
    """
    
    def __init__(self, checkpoint_dir: Path, max_checkpoints: int = 10):
        """
        Initialize checkpoint manager.
        
        Args:
            checkpoint_dir: Directory to store checkpoints
            max_checkpoints: Maximum number of checkpoints to keep (oldest deleted)
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.max_checkpoints = max_checkpoints
        self.checkpoint_info_file = self.checkpoint_dir / "checkpoint_info.json"
    
    def save_checkpoint(
        self,
        iteration: int,
        model_state: Optional[Dict[str, Any]] = None,
        training_stats: Optional[Dict[str, Any]] = None,
        bot_config: Optional[Dict[str, Any]] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Save a checkpoint.
        
        Args:
            iteration: Training iteration/game number
            model_state: Model weights/state dict
            training_stats: Training statistics (wins, losses, etc.)
            bot_config: Bot configuration
            additional_data: Any additional data to save
        
        Returns:
            Path to saved checkpoint
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_name = f"checkpoint_{iteration:06d}_{timestamp}"
        checkpoint_path = self.checkpoint_dir / checkpoint_name
        checkpoint_path.mkdir(exist_ok=True)
        
        # Save model state
        if model_state is not None:
            model_file = checkpoint_path / "model_state.pkl"
            with open(model_file, 'wb') as f:
                pickle.dump(model_state, f)
        
        # Save training stats
        if training_stats is not None:
            stats_file = checkpoint_path / "training_stats.json"
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(training_stats, f, indent=2, ensure_ascii=False)
        
        # Save bot config
        if bot_config is not None:
            config_file = checkpoint_path / "bot_config.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(bot_config, f, indent=2, ensure_ascii=False)
        
        # Save additional data
        if additional_data is not None:
            data_file = checkpoint_path / "additional_data.json"
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(additional_data, f, indent=2, ensure_ascii=False)
        
        # Update checkpoint info
        checkpoint_info = {
            "iteration": iteration,
            "timestamp": timestamp,
            "path": str(checkpoint_path),
            "has_model": model_state is not None,
            "has_stats": training_stats is not None,
            "has_config": bot_config is not None
        }
        
        # Load existing checkpoints
        all_checkpoints = self._load_checkpoint_info()
        all_checkpoints[checkpoint_name] = checkpoint_info
        
        # Keep only latest N checkpoints
        if len(all_checkpoints) > self.max_checkpoints:
            self._cleanup_old_checkpoints(all_checkpoints)
        
        # Save updated info
        self._save_checkpoint_info(all_checkpoints)
        
        return checkpoint_path
    
    def load_latest_checkpoint(self) -> Optional[Dict[str, Any]]:
        """
        Load the latest checkpoint.
        
        Returns:
            Dict with keys: iteration, model_state, training_stats, bot_config, path
            Returns None if no checkpoint found
        """
        all_checkpoints = self._load_checkpoint_info()
        if not all_checkpoints:
            return None
        
        # Find latest checkpoint by iteration
        latest = max(all_checkpoints.values(), key=lambda x: x["iteration"])
        checkpoint_path = Path(latest["path"])
        
        if not checkpoint_path.exists():
            return None
        
        result = {
            "iteration": latest["iteration"],
            "timestamp": latest["timestamp"],
            "path": checkpoint_path,
            "model_state": None,
            "training_stats": None,
            "bot_config": None,
            "additional_data": None
        }
        
        # Load model state
        model_file = checkpoint_path / "model_state.pkl"
        if model_file.exists():
            with open(model_file, 'rb') as f:
                result["model_state"] = pickle.load(f)
        
        # Load training stats
        stats_file = checkpoint_path / "training_stats.json"
        if stats_file.exists():
            with open(stats_file, 'r', encoding='utf-8') as f:
                result["training_stats"] = json.load(f)
        
        # Load bot config
        config_file = checkpoint_path / "bot_config.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                result["bot_config"] = json.load(f)
        
        # Load additional data
        data_file = checkpoint_path / "additional_data.json"
        if data_file.exists():
            with open(data_file, 'r', encoding='utf-8') as f:
                result["additional_data"] = json.load(f)
        
        return result
    
    def _load_checkpoint_info(self) -> Dict[str, Dict[str, Any]]:
        """Load checkpoint info from JSON file."""
        if not self.checkpoint_info_file.exists():
            return {}
        
        try:
            with open(self.checkpoint_info_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _save_checkpoint_info(self, checkpoints: Dict[str, Dict[str, Any]]):
        """Save checkpoint info to JSON file."""
        with open(self.checkpoint_info_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoints, f, indent=2, ensure_ascii=False)
    
    def _cleanup_old_checkpoints(self, all_checkpoints: Dict[str, Dict[str, Any]]):
        """Remove oldest checkpoints, keeping only max_checkpoints."""
        # Sort by iteration
        sorted_checkpoints = sorted(
            all_checkpoints.items(),
            key=lambda x: x[1]["iteration"]
        )
        
        # Remove oldest
        to_remove = sorted_checkpoints[:-self.max_checkpoints]
        for checkpoint_name, checkpoint_info in to_remove:
            checkpoint_path = Path(checkpoint_info["path"])
            if checkpoint_path.exists():
                try:
                    shutil.rmtree(checkpoint_path)
                except Exception:
                    pass  # Ignore deletion errors
            
            del all_checkpoints[checkpoint_name]
    
    def get_latest_iteration(self) -> int:
        """Get iteration number of latest checkpoint."""
        checkpoint = self.load_latest_checkpoint()
        if checkpoint:
            return checkpoint["iteration"]
        return 0
