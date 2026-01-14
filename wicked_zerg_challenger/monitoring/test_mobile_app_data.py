#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Android 앱 데이터 전달 테스트 스크립트

서버가 Android 앱에 올바른 데이터를 전달하는지 확인합니다.
"""

import requests
import json
from typing import Dict, Any
from datetime import datetime

# Android 에뮬레이터용 URL
BASE_URL = "http://localhost:8000"  # PC에서 테스트
EMULATOR_URL = "http://10.0.2.2:8000"  # Android 에뮬레이터에서 접근

def test_api_endpoint(url: str, endpoint: str) -> Dict[str, Any]:
    """API 엔드포인트 테스트"""
    full_url = f"{url}{endpoint}"
    try:
        response = requests.get(full_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return {
            "success": True,
            "status_code": response.status_code,
            "data": data,
            "error": None
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "status_code": None,
            "data": None,
            "error": "Connection refused - 서버가 실행 중이지 않습니다"
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "status_code": None,
            "data": None,
            "error": "Timeout - 서버 응답이 없습니다"
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": None,
            "data": None,
            "error": str(e)
        }

def validate_game_state(data: Dict[str, Any]) -> Dict[str, Any]:
    """GameState 데이터 형식 검증"""
    required_fields = [
        "minerals", "vespene", "supply_used", "supply_cap",
        "units"
    ]
    # win_rate는 선택적 (없으면 0.0으로 처리)
    
    issues = []
    warnings = []
    
    # 필수 필드 확인
    for field in required_fields:
        if field not in data:
            issues.append(f"필수 필드 누락: {field}")
    
    # 필드 타입 확인
    if "minerals" in data and not isinstance(data["minerals"], (int, float)):
        issues.append(f"minerals 타입 오류: {type(data['minerals'])}")
    
    if "vespene" in data and not isinstance(data["vespene"], (int, float)):
        issues.append(f"vespene 타입 오류: {type(data['vespene'])}")
    
    if "supply_used" in data and not isinstance(data["supply_used"], (int, float)):
        issues.append(f"supply_used 타입 오류: {type(data['supply_used'])}")
    
    if "supply_cap" in data and not isinstance(data["supply_cap"], (int, float)):
        issues.append(f"supply_cap 타입 오류: {type(data['supply_cap'])}")
    
    if "units" in data:
        if not isinstance(data["units"], dict):
            issues.append(f"units 타입 오류: dict가 아님")
        else:
            # units 값이 숫자인지 확인
            for unit_name, count in data["units"].items():
                if not isinstance(count, (int, float)):
                    warnings.append(f"units.{unit_name} 타입 오류: {type(count)}")
    
    # win_rate 확인 (Android 앱에서 사용) - 선택적 필드
    if "win_rate" not in data and "winRate" not in data:
        warnings.append("win_rate 필드 없음 (기본값 0.0 사용)")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings
    }

def print_test_result(name: str, result: Dict[str, Any]):
    """테스트 결과 출력"""
    print(f"\n{'='*60}")
    print(f"테스트: {name}")
    print(f"{'='*60}")
    
    if result["success"]:
        print(f"? 상태 코드: {result['status_code']}")
        print(f"\n? 응답 데이터:")
        print(json.dumps(result["data"], indent=2, ensure_ascii=False))
        
        # 데이터 검증
        validation = validate_game_state(result["data"])
        if validation["valid"]:
            print(f"\n? 데이터 형식 검증: 통과")
        else:
            print(f"\n? 데이터 형식 검증: 실패")
            for issue in validation["issues"]:
                print(f"   - {issue}")
        
        if validation["warnings"]:
            print(f"\n?? 경고:")
            for warning in validation["warnings"]:
                print(f"   - {warning}")
    else:
        print(f"? 실패: {result['error']}")

def main():
    print("="*60)
    print("Android 앱 데이터 전달 테스트")
    print("="*60)
    print(f"\n테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 서버 상태 확인
    print("\n1. 서버 상태 확인")
    print("-"*60)
    health_result = test_api_endpoint(BASE_URL, "/health")
    if health_result["success"]:
        print("? 서버가 실행 중입니다")
    else:
        print(f"? 서버 연결 실패: {health_result['error']}")
        print("\n? 해결 방법:")
        print("   1. 서버 실행: cd monitoring && python dashboard.py")
        print("   2. 또는: cd monitoring && python dashboard_api.py")
        return
    
    # API 엔드포인트 테스트
    endpoints = [
        ("/api/game-state", "게임 상태"),
        ("/api/combat-stats", "전투 통계"),
        ("/api/learning-progress", "학습 진행도"),
    ]
    
    print("\n2. API 엔드포인트 테스트")
    print("-"*60)
    
    for endpoint, name in endpoints:
        result = test_api_endpoint(BASE_URL, endpoint)
        print_test_result(name, result)
    
    # Android 앱에서 사용하는 형식 확인
    print("\n3. Android 앱 데이터 형식 확인")
    print("-"*60)
    
    game_state_result = test_api_endpoint(BASE_URL, "/api/game-state")
    if game_state_result["success"]:
        data = game_state_result["data"]
        
        # Android 앱에서 필요한 필드 확인
        android_fields = {
            "minerals": data.get("minerals"),
            "vespene": data.get("vespene"),
            "supplyUsed": data.get("supply_used"),  # Android는 camelCase
            "supplyCap": data.get("supply_cap"),     # Android는 camelCase
            "units": data.get("units"),
            "winRate": data.get("win_rate") or data.get("winRate")
        }
        
        print("\n? Android 앱에서 사용하는 필드:")
        for field, value in android_fields.items():
            if value is not None:
                print(f"   ? {field}: {value}")
            else:
                print(f"   ? {field}: 없음")
        
        # 필드명 매핑 확인
        print("\n? 필드명 매핑 확인:")
        print("   서버 (snake_case) → Android (camelCase)")
        print(f"   supply_used → supplyUsed: {'?' if 'supply_used' in data else '?'}")
        print(f"   supply_cap → supplyCap: {'?' if 'supply_cap' in data else '?'}")
        print(f"   win_rate → winRate: {'?' if 'win_rate' in data or 'winRate' in data else '?'}")
    
    # 요약
    print("\n" + "="*60)
    print("? 테스트 요약")
    print("="*60)
    print("\n? 모든 테스트가 통과하면 Android 앱에서 데이터를 정상적으로 받을 수 있습니다.")
    print("\n?? 문제가 있다면:")
    print("   1. 서버가 실행 중인지 확인")
    print("   2. 포트 8000이 열려있는지 확인")
    print("   3. CORS 설정 확인 (dashboard_api.py)")
    print("   4. Android 앱의 BASE_URL 확인 (10.0.2.2:8000)")

if __name__ == "__main__":
    main()
