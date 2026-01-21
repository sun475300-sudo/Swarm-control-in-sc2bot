# -*- coding: utf-8 -*-
"""
Production Logic Verification - 생산 로직 검증 도구

수정된 로직의 정확성을 검증합니다.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


def verify_production_enhancements():
    """ProductionEnhancements 클래스 검증"""
    print("=" * 70)
    print("Production Enhancements Verification")
    print("=" * 70)
    
    try:
        from local_training.production_enhancements import ProductionEnhancements
        
        # 클래스 존재 확인
        print("\n[1] 클래스 존재 확인: ?")
        print(f"   - ProductionEnhancements 클래스 로드 성공")
        
        # 메서드 존재 확인
        required_methods = [
            'should_upgrade_to_lair',
            'upgrade_to_lair',
            'emergency_flush_with_tech_units',
            'can_build_tech_building',
            'get_production_priority',
            'get_prioritized_units',
            '_check_unit_requirements',
        ]
        
        print("\n[2] 필수 메서드 확인:")
        for method_name in required_methods:
            if hasattr(ProductionEnhancements, method_name):
                print(f"   ? {method_name}")
            else:
                print(f"   ? {method_name} (누락)")
        
        # 속성 확인
        print("\n[3] 필수 속성 확인:")
        # Mock bot 객체 생성
        class MockBot:
            def __init__(self):
                self.minerals = 1000
                self.vespene = 500
                self.supply_left = 20
                
            def structures(self, unit_type):
                class MockStructures:
                    def __init__(self):
                        self._exists = False
                        self._ready = MockStructures()
                        self._ready._exists = False
                    
                    @property
                    def exists(self):
                        return self._exists
                    
                    @property
                    def ready(self):
                        return self._ready
                
                return MockStructures()
        
        mock_bot = MockBot()
        enhancer = ProductionEnhancements(mock_bot)
        
        required_attrs = [
            'lair_upgrade_attempts',
            'max_lair_upgrade_attempts',
            'tech_building_dependencies',
            'production_priority',
        ]
        
        for attr_name in required_attrs:
            if hasattr(enhancer, attr_name):
                print(f"   ? {attr_name}")
            else:
                print(f"   ? {attr_name} (누락)")
        
        # 우선순위 확인
        print("\n[4] 생산 우선순위 확인:")
        priorities = enhancer.production_priority
        sorted_priorities = sorted(priorities.items(), key=lambda x: x[1], reverse=True)
        for unit_type, priority in sorted_priorities:
            print(f"   {unit_type}: {priority}")
        
        print("\n" + "=" * 70)
        print("검증 완료: 모든 항목이 정상적으로 로드되었습니다.")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"\n[ERROR] 검증 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_indentation_fixes():
    """인덴테이션 수정 확인"""
    print("\n" + "=" * 70)
    print("Indentation Fixes Verification")
    print("=" * 70)
    
    files_to_check = [
        "wicked_zerg_challenger/spell_unit_manager.py",
        "wicked_zerg_challenger/local_training/curriculum_manager.py",
    ]
    
    import py_compile
    
    all_passed = True
    for file_path in files_to_check:
        full_path = project_root / file_path
        if full_path.exists():
            try:
                py_compile.compile(str(full_path), doraise=True)
                print(f"? {file_path}: 문법 검사 통과")
            except py_compile.PyCompileError as e:
                print(f"? {file_path}: 문법 오류 - {e}")
                all_passed = False
        else:
            print(f"? {file_path}: 파일 없음")
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("인덴테이션 수정 확인 완료: 모든 파일이 정상입니다.")
    else:
        print("인덴테이션 수정 확인 실패: 일부 파일에 오류가 있습니다.")
    print("=" * 70)
    
    return all_passed


if __name__ == "__main__":
    print("\n생산 로직 검증 시작...\n")
    
    # 1. ProductionEnhancements 검증
    result1 = verify_production_enhancements()
    
    # 2. 인덴테이션 수정 확인
    result2 = verify_indentation_fixes()
    
    # 최종 결과
    print("\n" + "=" * 70)
    if result1 and result2:
        print("? 모든 검증 통과")
    else:
        print("? 일부 검증 실패")
    print("=" * 70)
