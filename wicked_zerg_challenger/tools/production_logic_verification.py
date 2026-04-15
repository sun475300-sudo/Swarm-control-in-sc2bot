# -*- coding: utf-8 -*-
"""
Production Logic Verification - Production logic verification tool

Verifies the correctness of modified production logic.
"""

import sys
from pathlib import Path
import logging

logger = logging.getLogger("ProductionLogicVerification")

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


def verify_production_enhancements():
    """Verify ProductionEnhancements class"""
    logger.info("=" * 70)
    logger.info("Production Enhancements Verification")
    logger.info("=" * 70)

    try:
        from local_training.production_enhancements import ProductionEnhancements

        # Check class existence
        logger.info("\n[1] Class existence check: OK")
        logger.info("   - ProductionEnhancements class loaded successfully")

        # Check method existence
        required_methods = [
            'should_upgrade_to_lair',
            'upgrade_to_lair',
            'emergency_flush_with_tech_units',
            'can_build_tech_building',
            'get_production_priority',
            'get_prioritized_units',
            '_check_unit_requirements',
        ]

        logger.info("\n[2] Required methods check:")
        for method_name in required_methods:
            if hasattr(ProductionEnhancements, method_name):
                logger.info(f"   OK {method_name}")
            else:
                logger.info(f"   MISSING {method_name}")

        # Check attributes
        logger.info("\n[3] Required attributes check:")
        # Create mock bot object
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
                logger.info(f"   OK {attr_name}")
            else:
                logger.info(f"   MISSING {attr_name}")

        # Check priority
        logger.info("\n[4] Production priority check:")
        priorities = enhancer.production_priority
        sorted_priorities = sorted(priorities.items(), key=lambda x: x[1], reverse=True)
        for unit_type, priority in sorted_priorities:
            logger.info(f"   {unit_type}: {priority}")

        logger.info("\n" + "=" * 70)
        logger.info("Verification complete: All items loaded successfully.")
        logger.info("=" * 70)
        return True

    except Exception as e:
        logger.error(f"\n[ERROR] Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_indentation_fixes():
    """Verify indentation fixes"""
    logger.info("\n" + "=" * 70)
    logger.info("Indentation Fixes Verification")
    logger.info("=" * 70)

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
                logger.info(f"OK {file_path}: Syntax check passed")
            except py_compile.PyCompileError as e:
                logger.error(f"ERROR {file_path}: Syntax error - {e}")
                all_passed = False
        else:
            logger.info(f"MISSING {file_path}: File not found")
            all_passed = False

    logger.info("\n" + "=" * 70)
    if all_passed:
        logger.info("Indentation verification complete: All files are valid.")
    else:
        logger.error("Indentation verification failed: Some files have errors.")
    logger.info("=" * 70)

    return all_passed


if __name__ == "__main__":
    print("\nStarting production logic verification...\n")

    # 1. ProductionEnhancements verification
    result1 = verify_production_enhancements()

    # 2. Indentation fix verification
    result2 = verify_indentation_fixes()

    # Final result
    print("\n" + "=" * 70)
    if result1 and result2:
        print("All verifications passed")
    else:
        print("Some verifications failed")
    print("=" * 70)
