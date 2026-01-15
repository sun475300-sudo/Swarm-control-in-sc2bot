# -*- coding: utf-8 -*-
"""
Telemetry Service Client

Sends telemetry data to a remote telemetry service via HTTP API.
Falls back to local file logging if service is unavailable.
"""

import json
import time
import requests
from typing import Any, Dict, List, Optional
from pathlib import Path
import logging


logger = logging.getLogger(__name__)


class TelemetryServiceClient:
    """
 Client for sending telemetry data to a remote service.
 
 When hybrid mode is enabled, sends data to remote service.
 When local mode or service unavailable, falls back to local file logging.
    """
 
 def __init__(self, service_url: Optional[str] = None):
        """
 Initialize TelemetryServiceClient.
 
 Args:
 service_url: Telemetry service URL (optional, uses config if not provided)
        """
 self.config = get_config()
 self.service_url = service_url or self.config.telemetry_service_url
 
 # Local fallback
        self.local_log_dir = Path(__file__).parent.parent / "data"
 self.local_log_dir.mkdir(parents=True, exist_ok=True)
        self.local_telemetry_file = self.local_log_dir / "telemetry_local.json"
 
 # Telemetry buffer (for batch sending)
 self.telemetry_buffer: List[Dict[str, Any]] = []
 self.buffer_size = 10 # Send in batches of 10
 
 # Connection status
 self.service_available = False
 self._check_service_availability()
 
 def _check_service_availability(self) -> bool:
        """
 Check if telemetry service is available.
 
 Returns:
 bool: True if service is available
        """
 if not self.config.is_hybrid_mode() or not self.service_url:
 self.service_available = False
 return False
 
 try:
 response = requests.get(
                f"{self.service_url}/health",
 timeout=self.config.connection_timeout
 )
 self.service_available = response.status_code == 200
 return self.service_available
 except Exception as e:
            logger.warning(f"Telemetry service not available: {e}")
 self.service_available = False
 return False
 
 def send_telemetry(self, telemetry_data: Dict[str, Any]) -> bool:
        """
 Send telemetry data to remote service or save locally.
 
 Args:
 telemetry_data: Telemetry data dictionary
 
 Returns:
 bool: True if sent successfully (or saved locally)
        """
 # Add to buffer
 self.telemetry_buffer.append(telemetry_data)
 
 # Send batch if buffer is full
 if len(self.telemetry_buffer) >= self.buffer_size:
 return self._flush_buffer()
 
 return True
 
 def _flush_buffer(self) -> bool:
        """
 Flush telemetry buffer to service or local file.
 
 Returns:
 bool: True if flushed successfully
        """
 if not self.telemetry_buffer:
 return True
 
 # Try remote service first (if hybrid mode and available)
 if self.config.is_hybrid_mode() and self.service_available and self.service_url:
 if self._send_to_service(self.telemetry_buffer):
 self.telemetry_buffer.clear()
 return True
 
 # Fallback to local file
 if self.config.fallback_to_local:
 self._save_to_local(self.telemetry_buffer)
 self.telemetry_buffer.clear()
 return True
 
 return False
 
 def _send_to_service(self, data: List[Dict[str, Any]]) -> bool:
        """
 Send telemetry data to remote service.
 
 Args:
 data: List of telemetry data dictionaries
 
 Returns:
 bool: True if sent successfully
        """
 if not self.service_url:
 return False
 
 for attempt in range(self.config.retry_attempts):
 try:
 response = requests.post(
                    f"{self.service_url}/api/telemetry",
                    json={"telemetry": data},
 timeout=self.config.connection_timeout,
                    headers={"Content-Type": "application/json"}
 )
 
 if response.status_code == 200:
                    logger.debug(f"Sent {len(data)} telemetry entries to service")
 return True
 else:
                    logger.warning(f"Telemetry service returned status {response.status_code}")
 
 except requests.exceptions.RequestException as e:
                logger.warning(f"Failed to send telemetry (attempt {attempt + 1}/{self.config.retry_attempts}): {e}")
 if attempt < self.config.retry_attempts - 1:
 time.sleep(self.config.retry_delay)
 else:
 # Service unavailable, mark as unavailable
 self.service_available = False
 
 return False
 
 def _save_to_local(self, data: List[Dict[str, Any]]) -> None:
        """
 Save telemetry data to local file (fallback).
 
 Args:
 data: List of telemetry data dictionaries
        """
 try:
 # Load existing data
 existing_data = []
 if self.local_telemetry_file.exists():
 try:
                    with open(self.local_telemetry_file, 'r', encoding='utf-8') as f:
 existing_data = json.load(f)
 except (json.JSONDecodeError, IOError):
 existing_data = []
 
 # Append new data
 existing_data.extend(data)
 
 # Save to file (atomic write)
            temp_file = self.local_telemetry_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
 json.dump(existing_data, f, indent=2, ensure_ascii=False)
 
 # Atomic replace
 temp_file.replace(self.local_telemetry_file)
 
            logger.debug(f"Saved {len(data)} telemetry entries to local file")
 
 except Exception as e:
            logger.error(f"Failed to save telemetry to local file: {e}")
 
 def flush(self) -> bool:
        """
 Force flush remaining buffer.
 
 Returns:
 bool: True if flushed successfully
        """
 return self._flush_buffer()
 
 def close(self) -> None:
        """Close client and flush remaining data."""
 self.flush()