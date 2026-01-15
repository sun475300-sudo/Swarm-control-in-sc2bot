# -*- coding: utf-8 -*-
"""
Hybrid Architecture Configuration

Controls whether services run locally (monolithic) or distributed (hybrid).
"""

import os
from typing import Optional
from pathlib import Path


@dataclass
class HybridConfig:
    """
 Configuration for hybrid architecture mode.
 
 When enabled, external services (monitoring, learning, telemetry) 
 can run as separate processes/servers.
    """
 
    # Service mode: "local" (monolithic) or "hybrid" (distributed)
    mode: str = "local"
 
 # Telemetry service configuration
 telemetry_service_enabled: bool = False
    telemetry_service_url: Optional[str] = None  # e.g., "http://localhost:8001"
 
 # Learning service configuration
 learning_service_enabled: bool = False
    learning_service_url: Optional[str] = None  # e.g., "http://localhost:8002"
 
 # Monitoring service configuration (already separate)
    monitoring_service_url: Optional[str] = None  # e.g., "http://localhost:8000"
 
 # Service discovery
    service_registry_url: Optional[str] = None  # e.g., "http://localhost:8003"
 
 # Connection settings
 connection_timeout: int = 5 # seconds
 retry_attempts: int = 3
 retry_delay: float = 1.0 # seconds
 
 # Fallback to local if service unavailable
 fallback_to_local: bool = True
 
 @classmethod
    def from_env(cls) -> "HybridConfig":
        """
 Load configuration from environment variables.
 
 Environment variables:
        - HYBRID_MODE: "local" or "hybrid" (default: "local")
 - TELEMETRY_SERVICE_URL: Telemetry service URL
 - LEARNING_SERVICE_URL: Learning service URL
 - MONITORING_SERVICE_URL: Monitoring service URL
 - SERVICE_REGISTRY_URL: Service registry URL
        """
        mode = os.environ.get("HYBRID_MODE", "local").lower()
 
 return cls(
 mode=mode,
            telemetry_service_enabled=os.environ.get("TELEMETRY_SERVICE_ENABLED", "false").lower() == "true",
            telemetry_service_url=os.environ.get("TELEMETRY_SERVICE_URL"),
            learning_service_enabled=os.environ.get("LEARNING_SERVICE_ENABLED", "false").lower() == "true",
            learning_service_url=os.environ.get("LEARNING_SERVICE_URL"),
            monitoring_service_url=os.environ.get("MONITORING_SERVICE_URL", "http://localhost:8000"),
            service_registry_url=os.environ.get("SERVICE_REGISTRY_URL"),
            connection_timeout=int(os.environ.get("SERVICE_CONNECTION_TIMEOUT", "5")),
            retry_attempts=int(os.environ.get("SERVICE_RETRY_ATTEMPTS", "3")),
            retry_delay=float(os.environ.get("SERVICE_RETRY_DELAY", "1.0")),
            fallback_to_local=os.environ.get("SERVICE_FALLBACK_TO_LOCAL", "true").lower() == "true",
 )
 
 @classmethod
    def from_file(cls, config_path: Path) -> "HybridConfig":
        """
 Load configuration from JSON file.
 
 Args:
 config_path: Path to JSON configuration file
        """
 import json
 
 if not config_path.exists():
 return cls.from_env() # Fallback to environment variables
 
        with open(config_path, 'r', encoding='utf-8') as f:
 data = json.load(f)
 
 return cls(**data)
 
 def is_hybrid_mode(self) -> bool:
        """Check if hybrid mode is enabled."""
        return self.mode == "hybrid"
 
 def is_local_mode(self) -> bool:
        """Check if local (monolithic) mode is enabled."""
        return self.mode == "local"


# Global configuration instance
_config: Optional[HybridConfig] = None


def get_config() -> HybridConfig:
    """Get global hybrid configuration instance."""
 global _config
 if _config is None:
 # Try to load from file first, then environment
        config_file = Path(__file__).parent.parent / "hybrid_config.json"
 _config = HybridConfig.from_file(config_file) if config_file.exists() else HybridConfig.from_env()
 return _config


def set_config(config: HybridConfig) -> None:
    """Set global hybrid configuration instance."""
 global _config
 _config = config