#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 키 사용 모니터링
API Key Usage Monitoring
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict


def get_log_file() -> Path:
    """로그 파일 경로 반환"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    return log_dir / "api_key_usage.json"


def log_api_key_usage(api_name: str, success: bool = True, error: Optional[str] = None):
    """
    API 키 사용 로그 기록
    
    Args:
        api_name: API 이름 (예: "gemini", "google")
        success: 성공 여부
        error: 에러 메시지 (실패 시)
    """
    log_file = get_log_file()
    
    # 기존 로그 읽기
    if log_file.exists():
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except Exception:
            logs = []
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
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[WARNING] API 키 사용 로그 저장 실패: {e}")


def load_usage_logs() -> List[Dict]:
    """사용 로그 로드"""
    log_file = get_log_file()
    
    if not log_file.exists():
        return []
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def get_usage_stats(days: int = 7) -> Dict:
    """
    사용량 통계 반환
    
    Args:
        days: 통계 기간 (일)
    
    Returns:
        통계 딕셔너리
    """
    logs = load_usage_logs()
    
    if not logs:
        return {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'success_rate': 0.0,
            'daily_usage': {}
        }
    
    # 기간 필터링
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
    recent_logs = [log for log in logs if log['timestamp'] >= cutoff_date]
    
    # 통계 계산
    total = len(recent_logs)
    successful = sum(1 for log in recent_logs if log.get('success', False))
    failed = total - successful
    success_rate = (successful / total * 100) if total > 0 else 0.0
    
    # 일일 사용량
    daily_usage = {}
    for log in recent_logs:
        date = log['timestamp'][:10]  # YYYY-MM-DD
        daily_usage[date] = daily_usage.get(date, 0) + 1
    
    return {
        'total_requests': total,
        'successful_requests': successful,
        'failed_requests': failed,
        'success_rate': success_rate,
        'daily_usage': daily_usage
    }


if __name__ == "__main__":
    from datetime import timedelta
    
    # 테스트
    log_api_key_usage("gemini", success=True)
    log_api_key_usage("gemini", success=False, error="Test error")
    
    # 통계 출력
    stats = get_usage_stats(days=7)
    print("API 키 사용 통계 (최근 7일):")
    print(f"  총 요청: {stats['total_requests']}")
    print(f"  성공: {stats['successful_requests']}")
    print(f"  실패: {stats['failed_requests']}")
    print(f"  성공률: {stats['success_rate']:.2f}%")
    print(f"  일일 사용량: {stats['daily_usage']}")
