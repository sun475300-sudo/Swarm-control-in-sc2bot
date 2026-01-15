# API 키 사용량 제한 설정
import time
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
import json

class ApiKeyUsageLimiter:
    '''API 키 사용량 제한 클래스'''
 
 def __init__(self, daily_limit: int = 1000, hourly_limit: int = 100):
 self.daily_limit = daily_limit
 self.hourly_limit = hourly_limit
        self.usage_file = Path('logs') / 'api_key_usage_limits.json'
 self._load_usage()
 
 def _load_usage(self):
        '''사용량 로드'''
 if self.usage_file.exists():
            with open(self.usage_file, 'r', encoding='utf-8') as f:
 self.usage = json.load(f)
 else:
 self.usage = defaultdict(int)
 
 def _save_usage(self):
        '''사용량 저장'''
 self.usage_file.parent.mkdir(exist_ok=True)
        with open(self.usage_file, 'w', encoding='utf-8') as f:
 json.dump(dict(self.usage), f, indent=2)
 
 def can_make_request(self) -> tuple[bool, str]:
        '''요청 가능한지 확인'''
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
        '''요청 기록'''
 now = datetime.now()
        date_key = now.strftime('%Y-%m-%d')
        hour_key = now.strftime('%Y-%m-%d-%H')
 
 self.usage[date_key] = self.usage.get(date_key, 0) + 1
 self.usage[hour_key] = self.usage.get(hour_key, 0) + 1
 
 # 오래된 데이터 정리 (30일 이상)
        cutoff_date = (now - timedelta(days=30)).strftime('%Y-%m-%d')
 self.usage = {k: v for k, v in self.usage.items() if k >= cutoff_date}
 
 self._save_usage()