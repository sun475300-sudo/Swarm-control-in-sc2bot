# API 키 사용 모니터링 스크립트
import os
import json
from datetime import datetime
from pathlib import Path

def log_api_key_usage(api_name, success=True, error=None):
    '''API 키 사용 로그 기록'''
    log_dir = Path('logs')
 log_dir.mkdir(exist_ok=True)
 
    log_file = log_dir / 'api_key_usage.json'
 
 # 기존 로그 읽기
 if log_file.exists():
        with open(log_file, 'r', encoding='utf-8') as f:
 logs = json.load(f)
 else:
 logs = []
 
 # 새 로그 추가
 log_entry = {
        'timestamp': datetime.now().isoformat(),
        'api': api_name,
        'success': success,
        'error': str(error) if error else None
 }
 
 logs.append(log_entry)
 
 # 최근 1000개만 유지
 if len(logs) > 1000:
 logs = logs[-1000:]
 
 # 로그 저장
    with open(log_file, 'w', encoding='utf-8') as f:
 json.dump(logs, f, indent=2, ensure_ascii=False)