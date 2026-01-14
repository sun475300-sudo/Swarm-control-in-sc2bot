#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 키 사용량 제한
API Key Usage Limiter
"""

import json
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from typing import Tuple


class ApiKeyUsageLimiter:
    """API 키 사용량 제한 클래스"""
    
    def __init__(self, daily_limit: int = 1000, hourly_limit: int = 100):
        """
        초기화
        
        Args:
            daily_limit: 일일 사용량 제한
            hourly_limit: 시간당 사용량 제한
        """
        self.daily_limit = daily_limit
        self.hourly_limit = hourly_limit
        self.usage_file = Path("logs") / "api_key_usage_limits.json"
        self.usage = defaultdict(int)
        self._load_usage()
    
    def _load_usage(self):
        """사용량 로드"""
        if self.usage_file.exists():
            try:
                with open(self.usage_file, 'r', encoding='utf-8') as f:
                    self.usage = defaultdict(int, json.load(f))
            except Exception:
                self.usage = defaultdict(int)
        else:
            self.usage = defaultdict(int)
    
    def _save_usage(self):
        """사용량 저장"""
        self.usage_file.parent.mkdir(exist_ok=True)
        try:
            with open(self.usage_file, 'w', encoding='utf-8') as f:
                json.dump(dict(self.usage), f, indent=2)
        except Exception as e:
            print(f"[WARNING] 사용량 저장 실패: {e}")
    
    def can_make_request(self) -> Tuple[bool, str]:
        """
        요청 가능한지 확인
        
        Returns:
            (가능 여부, 메시지)
        """
        now = datetime.now()
        date_key = now.strftime('%Y-%m-%d')
        hour_key = now.strftime('%Y-%m-%d-%H')
        
        daily_count = self.usage.get(date_key, 0)
        hourly_count = self.usage.get(hour_key, 0)
        
        if daily_count >= self.daily_limit:
            return False, f"일일 사용량 제한 초과 ({daily_count}/{self.daily_limit})"
        
        if hourly_count >= self.hourly_limit:
            return False, f"시간당 사용량 제한 초과 ({hourly_count}/{self.hourly_limit})"
        
        return True, ""
    
    def record_request(self):
        """요청 기록"""
        now = datetime.now()
        date_key = now.strftime('%Y-%m-%d')
        hour_key = now.strftime('%Y-%m-%d-%H')
        
        self.usage[date_key] = self.usage.get(date_key, 0) + 1
        self.usage[hour_key] = self.usage.get(hour_key, 0) + 1
        
        # 오래된 데이터 정리 (30일 이상)
        cutoff_date = (now - timedelta(days=30)).strftime('%Y-%m-%d')
        self.usage = defaultdict(int, {k: v for k, v in self.usage.items() if k >= cutoff_date})
        
        self._save_usage()
    
    def get_current_usage(self) -> dict:
        """현재 사용량 반환"""
        now = datetime.now()
        date_key = now.strftime('%Y-%m-%d')
        hour_key = now.strftime('%Y-%m-%d-%H')
        
        return {
            'daily': self.usage.get(date_key, 0),
            'daily_limit': self.daily_limit,
            'hourly': self.usage.get(hour_key, 0),
            'hourly_limit': self.hourly_limit
        }


if __name__ == "__main__":
    # 테스트
    limiter = ApiKeyUsageLimiter(daily_limit=1000, hourly_limit=100)
    
    can_request, message = limiter.can_make_request()
    print(f"요청 가능: {can_request}")
    if not can_request:
        print(f"  이유: {message}")
    else:
        limiter.record_request()
        usage = limiter.get_current_usage()
        print(f"현재 사용량:")
        print(f"  일일: {usage['daily']}/{usage['daily_limit']}")
        print(f"  시간당: {usage['hourly']}/{usage['hourly_limit']}")
