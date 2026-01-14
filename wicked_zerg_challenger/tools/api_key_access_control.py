#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 키 접근 제어
API Key Access Control
"""

import os
from pathlib import Path
from typing import Optional, List


class ApiKeyAccessControl:
    """API 키 접근 제어 클래스"""
    
    def __init__(self):
        """초기화"""
        self.allowed_ips = self._load_allowed_ips()
        self.allowed_domains = self._load_allowed_domains()
    
    def _load_allowed_ips(self) -> List[str]:
        """허용된 IP 주소 목록 로드"""
        config_file = Path("config") / "allowed_ips.txt"
        
        # 예제 파일이 있으면 사용
        if not config_file.exists():
            example_file = Path("config") / "allowed_ips.txt.example"
            if example_file.exists():
                return []  # 예제 파일은 무시
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    ips = []
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            ips.append(line)
                    return ips
            except Exception:
                return []
        
        return []
    
    def _load_allowed_domains(self) -> List[str]:
        """허용된 도메인 목록 로드"""
        config_file = Path("config") / "allowed_domains.txt"
        
        # 예제 파일이 있으면 사용
        if not config_file.exists():
            example_file = Path("config") / "allowed_domains.txt.example"
            if example_file.exists():
                return []  # 예제 파일은 무시
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    domains = []
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            domains.append(line)
                    return domains
            except Exception:
                return []
        
        return []
    
    def is_allowed(self, ip: Optional[str] = None, domain: Optional[str] = None) -> bool:
        """
        접근이 허용되었는지 확인
        
        Args:
            ip: 클라이언트 IP 주소
            domain: 클라이언트 도메인
        
        Returns:
            허용 여부
        """
        # 제한이 없으면 허용
        if not self.allowed_ips and not self.allowed_domains:
            return True
        
        # IP 확인
        if ip and self.allowed_ips:
            # 정확한 IP 매칭
            if ip in self.allowed_ips:
                return True
            
            # CIDR 표기법 지원 (간단한 구현)
            for allowed_ip in self.allowed_ips:
                if '/' in allowed_ip:
                    # CIDR 표기법 (예: 192.168.1.0/24)
                    # 간단한 구현: 정확한 매칭만
                    if ip == allowed_ip.split('/')[0]:
                        return True
                elif ip == allowed_ip:
                    return True
        
        # 도메인 확인
        if domain and self.allowed_domains:
            for allowed_domain in self.allowed_domains:
                if allowed_domain.startswith('*.'):
                    # 와일드카드 도메인 (예: *.example.com)
                    base_domain = allowed_domain[2:]
                    if domain.endswith('.' + base_domain) or domain == base_domain:
                        return True
                elif domain == allowed_domain:
                    return True
        
        # IP나 도메인이 제공되지 않았고 제한이 있으면 거부
        if self.allowed_ips or self.allowed_domains:
            return False
        
        return True


if __name__ == "__main__":
    # 테스트
    access_control = ApiKeyAccessControl()
    
    print("접근 제어 설정:")
    print(f"  허용된 IP: {access_control.allowed_ips}")
    print(f"  허용된 도메인: {access_control.allowed_domains}")
    
    # 테스트
    test_ip = "192.168.1.100"
    test_domain = "example.com"
    
    print(f"\n테스트:")
    print(f"  IP {test_ip}: {'허용' if access_control.is_allowed(ip=test_ip) else '거부'}")
    print(f"  도메인 {test_domain}: {'허용' if access_control.is_allowed(domain=test_domain) else '거부'}")
