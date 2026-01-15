# API 키 접근 제어 설정
import os
from pathlib import Path
from typing import Optional

class ApiKeyAccessControl:
    '''API 키 접근 제어 클래스'''
 
 def __init__(self):
 self.allowed_ips = self._load_allowed_ips()
 self.allowed_domains = self._load_allowed_domains()
 
 def _load_allowed_ips(self) -> list:
        '''허용된 IP 주소 목록 로드'''
        config_file = Path('config') / 'allowed_ips.txt'
 if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip() and not line.startswith('#')]
 return []
 
 def _load_allowed_domains(self) -> list:
        '''허용된 도메인 목록 로드'''
        config_file = Path('config') / 'allowed_domains.txt'
 if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip() and not line.startswith('#')]
 return []
 
 def is_allowed(self, ip: Optional[str] = None, domain: Optional[str] = None) -> bool:
        '''접근이 허용되었는지 확인'''
 if ip and self.allowed_ips:
 return ip in self.allowed_ips
 if domain and self.allowed_domains:
 return domain in self.allowed_domains
 return True # 제한이 없으면 허용