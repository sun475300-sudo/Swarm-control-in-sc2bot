# -*- coding: utf-8 -*-
"""
Learning Service Client

Sends learning data to a remote learning service for distributed training.
Falls back to local training if service is unavailable.
"""

import json
import time
import requests
from typing import Any
from typing import Dict
from typing import Optional
from pathlib import Path
import logging


logger = logging.getLogger(__name__)


class LearningServiceClient:
    """
 Client for sending learning data to a remote learning service.

 When hybrid mode is enabled, sends training data to remote service.
 When local mode or service unavailable, falls back to local training.
    """

def __init__(self, service_url: Optional[str] = None):
    """
 Initialize LearningServiceClient.

 Args:
 service_url: Learning service URL (optional, uses config if not provided)
     """
 self.config = get_config()
 self.service_url = service_url or self.config.learning_service_url

 # Local fallback
     self.local_models_dir = Path(__file__).parent.parent / "local_training" / "models"
 self.local_models_dir.mkdir(parents=True, exist_ok=True)

 # Connection status
 self.service_available = False
 self._check_service_availability()

def _check_service_availability(self) -> bool:
    """
 Check if learning service is available.

 Returns:
 bool: True if service is available
     """
 if not self.config.is_hybrid_mode() or not self.service_url:
     self.service_available = False
 return False

 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     response = requests.get(
     f"{self.service_url}/health",
 timeout=self.config.connection_timeout
 )
 self.service_available = response.status_code == 200
 return self.service_available
 except Exception as e:
     logger.warning(f"Learning service not available: {e}")
 self.service_available = False
 return False

def send_training_data(
 self,
 game_result: str,
 game_time: float,
 build_order_score: Optional[float] = None,
 loss_reason: Optional[str] = None,
 parameters_updated: int = 0
 ) -> bool:
     """
 Send training data to remote learning service.

 Args:
     game_result: Game result ("Victory" or "Defeat")
 game_time: Game duration in seconds
 build_order_score: Build order comparison score
 loss_reason: Reason for loss (if defeat)
 parameters_updated: Number of parameters updated

 Returns:
 bool: True if sent successfully (or saved locally)
     """
 training_data = {
     "game_result": game_result,
     "game_time": game_time,
     "build_order_score": build_order_score,
     "loss_reason": loss_reason,
     "parameters_updated": parameters_updated,
     "timestamp": time.time()
 }

 # Try remote service first (if hybrid mode and available)
 if self.config.is_hybrid_mode() and self.service_available and self.service_url:
     if self._send_to_service(training_data):
         return True

        # Fallback to local (already handled by bot's on_end method)
 if self.config.fallback_to_local:
     logger.debug("Learning service unavailable, using local training")
 return True

 return False

def _send_to_service(self, data: Dict[str, Any]) -> bool:
    """
 Send training data to remote service.

 Args:
 data: Training data dictionary

 Returns:
 bool: True if sent successfully
     """
 if not self.service_url:
     return False

 for attempt in range(self.config.retry_attempts):
     try:
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         response = requests.post(
         f"{self.service_url}/api/training",
 json=data,
 timeout=self.config.connection_timeout,
     headers={"Content-Type": "application/json"}
 )

 if response.status_code == 200:
     logger.debug("Sent training data to learning service")
 return True
 else:
     logger.warning(f"Learning service returned status {response.status_code}")

 except requests.exceptions.RequestException as e:
     logger.warning(f"Failed to send training data (attempt {attempt + 1}/{self.config.retry_attempts}): {e}")
 if attempt < self.config.retry_attempts - 1:
     time.sleep(self.config.retry_delay)
 else:
 # Service unavailable, mark as unavailable
 self.service_available = False

 return False

def get_model_update(self, model_path: str) -> Optional[bytes]:
    """
 Get updated model from remote learning service.

 Args:
 model_path: Local model path

 Returns:
 bytes: Model data if available, None otherwise
     """
 if not self.config.is_hybrid_mode() or not self.service_available or not self.service_url:
     return None

 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     response = requests.get(
     f"{self.service_url}/api/model/latest",
 timeout=self.config.connection_timeout
 )

 if response.status_code == 200:
     return response.content
 else:
     logger.warning(f"Learning service returned status {response.status_code}")
 return None

 except requests.exceptions.RequestException as e:
     logger.warning(f"Failed to get model update: {e}")
 return None
