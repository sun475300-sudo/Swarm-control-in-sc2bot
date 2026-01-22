# -*- coding: utf-8 -*-
"""
Production Logic Verification - Production logic verification tool

Verifies the correctness of modified production logic.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


def verify_production_enhancements():
    """ProductionEnhancements Ŭ���� ����"""
    print("=" * 70)
    print("Production Enhancements Verification")
    print("=" * 70)
    
    try:
        from local_training.production_enhancements import ProductionEnhancements
        
        # Ŭ���� ���� Ȯ��
        print("\n[1] Ŭ���� ���� Ȯ��: ?")
        print(f"   - ProductionEnhancements Ŭ���� �ε� ����")
        
        # �޼��� ���� Ȯ��
        required_methods = [
            'should_upgrade_to_lair',
            'upgrade_to_lair',
            'emergency_flush_with_tech_units',
            'can_build_tech_building',
            'get_production_priority',
            'get_prioritized_units',
            '_check_unit_requirements',
        ]
        
        print("\n[2] �ʼ� �޼��� Ȯ��:")
        for method_name in required_methods:
            if hasattr(ProductionEnhancements, method_name):
                print(f"   ? {method_name}")
            else:
                print(f"   ? {method_name} (����)")
        
        # �Ӽ� Ȯ��
        print("\n[3] �ʼ� �Ӽ� Ȯ��:")
        # Mock bot ��ü ����
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
                print(f"   ? {attr_name} (����)")
        
        # �켱���� Ȯ��
        print("\n[4] ���� �켱���� Ȯ��:")
        priorities = enhancer.production_priority
        sorted_priorities = sorted(priorities.items(), key=lambda x: x[1], reverse=True)
        for unit_type, priority in sorted_priorities:
            print(f"   {unit_type}: {priority}")
        
        print("\n" + "=" * 70)
        print("���� �Ϸ�: ��� �׸��� ���������� �ε�Ǿ����ϴ�.")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"\n[ERROR] ���� ����: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_indentation_fixes():
    """�ε����̼� ���� Ȯ��"""
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
                print(f"? {file_path}: ���� �˻� ���")
            except py_compile.PyCompileError as e:
                print(f"? {file_path}: ���� ���� - {e}")
                all_passed = False
        else:
            print(f"? {file_path}: ���� ����")
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("�ε����̼� ���� Ȯ�� �Ϸ�: ��� ������ �����Դϴ�.")
    else:
        print("�ε����̼� ���� Ȯ�� ����: �Ϻ� ���Ͽ� ������ �ֽ��ϴ�.")
    print("=" * 70)
    
    return all_passed


if __name__ == "__main__":
    print("\n���� ���� ���� ����...\n")
    
    # 1. ProductionEnhancements ����
    result1 = verify_production_enhancements()
    
    # 2. �ε����̼� ���� Ȯ��
    result2 = verify_indentation_fixes()
    
    # ���� ���
    print("\n" + "=" * 70)
    if result1 and result2:
        print("? ��� ���� ���")
    else:
        print("? �Ϻ� ���� ����")
    print("=" * 70)
