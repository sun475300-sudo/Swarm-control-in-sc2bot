# -*- coding: utf-8 -*-
"""
Phase 15 Integration Test Script

This script runs validation tests for the integrated systems:
- OpponentModeling
- AdvancedMicroControllerV3

Usage:
    python test_integration.py --games 10 --race Terran
    python test_integration.py --quick-test
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


class IntegrationTester:
    """Test runner for Phase 15 integrated systems"""

    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.data_dir = self.base_dir / "data" / "opponent_models"
        self.results = {
            "test_date": datetime.now().isoformat(),
            "opponent_modeling": {},
            "micro_v3": {},
            "performance": {},
            "errors": []
        }

    def check_file_structure(self) -> bool:
        """Verify all required files exist"""
        print("[VALIDATION] Checking file structure...")

        required_files = [
            "opponent_modeling.py",
            "advanced_micro_controller_v3.py",
            "wicked_zerg_bot_pro_impl.py",
            "bot_step_integration.py"
        ]

        missing_files = []
        for file_name in required_files:
            file_path = self.base_dir / file_name
            if not file_path.exists():
                missing_files.append(file_name)
                print(f"  [X] Missing: {file_name}")
            else:
                print(f"  [OK] Found: {file_name}")

        if missing_files:
            self.results["errors"].append(f"Missing files: {missing_files}")
            return False

        return True

    def check_imports(self) -> bool:
        """Test if all modules can be imported"""
        print("\n[VALIDATION] Checking imports...")

        try:
            from opponent_modeling import OpponentModeling
            print("  [OK] OpponentModeling imported successfully")
            self.results["opponent_modeling"]["import"] = "success"
        except Exception as e:
            print(f"  [X] Failed to import OpponentModeling: {e}")
            self.results["opponent_modeling"]["import"] = f"failed: {e}"
            self.results["errors"].append(f"OpponentModeling import error: {e}")
            return False

        try:
            from advanced_micro_controller_v3 import AdvancedMicroControllerV3
            print("  [OK] AdvancedMicroControllerV3 imported successfully")
            self.results["micro_v3"]["import"] = "success"
        except Exception as e:
            print(f"  [X] Failed to import AdvancedMicroControllerV3: {e}")
            self.results["micro_v3"]["import"] = f"failed: {e}"
            self.results["errors"].append(f"AdvancedMicroControllerV3 import error: {e}")
            return False

        return True

    def check_data_directory(self) -> bool:
        """Ensure data directory exists for opponent models"""
        print("\n[VALIDATION] Checking data directory...")

        if not self.data_dir.exists():
            print(f"  [\!]  Creating data directory: {self.data_dir}")
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.results["opponent_modeling"]["data_dir"] = "created"
        else:
            print(f"  [OK] Data directory exists: {self.data_dir}")
            self.results["opponent_modeling"]["data_dir"] = "exists"

            # Check for existing opponent models
            json_files = list(self.data_dir.glob("*.json"))
            if json_files:
                print(f"  [STATS] Found {len(json_files)} existing opponent models:")
                for json_file in json_files:
                    print(f"     - {json_file.name}")
                self.results["opponent_modeling"]["existing_models"] = len(json_files)
            else:
                print("  [i]  No existing opponent models (this is normal for first run)")
                self.results["opponent_modeling"]["existing_models"] = 0

        return True

    def test_opponent_modeling_initialization(self) -> bool:
        """Test OpponentModeling can be initialized"""
        print("\n[VALIDATION] Testing OpponentModeling initialization...")

        try:
            from opponent_modeling import OpponentModeling

            # Initialize system
            om = OpponentModeling()
            print("  [OK] OpponentModeling initialized successfully")

            # Test opponent tracking
            om.on_game_start("TestOpponent", None)
            print("  [OK] Opponent tracking started")

            # Test strategy prediction (should return None for new opponent)
            strategy, confidence = om.get_predicted_strategy()
            print(f"  [OK] Strategy prediction: {strategy} (confidence: {confidence:.2%})")

            # Test counter recommendations
            counters = om.get_counter_recommendations()
            print(f"  [OK] Counter recommendations: {counters}")

            self.results["opponent_modeling"]["initialization"] = "success"
            return True

        except Exception as e:
            print(f"  [X] OpponentModeling initialization failed: {e}")
            self.results["opponent_modeling"]["initialization"] = f"failed: {e}"
            self.results["errors"].append(f"OpponentModeling init error: {e}")
            return False

    def test_micro_v3_initialization(self) -> bool:
        """Test AdvancedMicroControllerV3 can be initialized"""
        print("\n[VALIDATION] Testing AdvancedMicroControllerV3 initialization...")

        try:
            from advanced_micro_controller_v3 import AdvancedMicroControllerV3
            from unittest.mock import Mock

            # Create mock bot
            mock_bot = Mock()
            mock_bot.time = 0.0
            mock_bot.units = Mock()
            mock_bot.units.return_value = []

            # Initialize system
            micro_v3 = AdvancedMicroControllerV3(mock_bot)
            print("  [OK] AdvancedMicroControllerV3 initialized successfully")

            # Test status retrieval
            status = micro_v3.get_status()
            print(f"  [OK] Status retrieved: {len(status)} fields")
            print(f"     - Ravager cooldowns: {len(status.get('ravager_cooldowns', {}))}")
            print(f"     - Lurker burrowed: {len(status.get('lurker_burrowed', {}))}")
            print(f"     - Focus fire assignments: {len(status.get('focus_fire_assignments', {}))}")

            self.results["micro_v3"]["initialization"] = "success"
            return True

        except Exception as e:
            print(f"  [X] AdvancedMicroControllerV3 initialization failed: {e}")
            self.results["micro_v3"]["initialization"] = f"failed: {e}"
            self.results["errors"].append(f"AdvancedMicroControllerV3 init error: {e}")
            return False

    def run_unit_tests(self) -> bool:
        """Run all unit tests"""
        print("\n[VALIDATION] Running unit tests...")

        import subprocess

        try:
            result = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                timeout=120
            )

            # Parse output
            output_lines = result.stdout.split('\n') + result.stderr.split('\n')

            # Find test result line
            for line in output_lines:
                if line.startswith("Ran "):
                    print(f"  [OK] {line}")
                if line.startswith("OK"):
                    print(f"  [OK] All tests passed!")
                    self.results["performance"]["unit_tests"] = "all_passed"
                    return True
                if "FAILED" in line:
                    print(f"  [X] {line}")
                    self.results["performance"]["unit_tests"] = "some_failed"
                    self.results["errors"].append(f"Unit tests failed: {line}")
                    return False

            return True

        except subprocess.TimeoutExpired:
            print("  [X] Unit tests timed out (>120s)")
            self.results["performance"]["unit_tests"] = "timeout"
            self.results["errors"].append("Unit tests timeout")
            return False
        except Exception as e:
            print(f"  [X] Failed to run unit tests: {e}")
            self.results["performance"]["unit_tests"] = f"error: {e}"
            self.results["errors"].append(f"Unit test execution error: {e}")
            return False

    def check_integration_points(self) -> bool:
        """Verify integration points in main bot files"""
        print("\n[VALIDATION] Checking integration points...")

        # Check wicked_zerg_bot_pro_impl.py
        impl_file = self.base_dir / "wicked_zerg_bot_pro_impl.py"
        with open(impl_file, 'r', encoding='utf-8') as f:
            impl_content = f.read()

        integration_checks = {
            "OpponentModeling import": "from opponent_modeling import OpponentModeling" in impl_content,
            "AdvancedMicroV3 import": "from advanced_micro_controller_v3 import AdvancedMicroControllerV3" in impl_content,
            "OpponentModeling init": "self.opponent_modeling = OpponentModeling()" in impl_content,
            "AdvancedMicroV3 init": "self.micro_v3 = AdvancedMicroControllerV3(self)" in impl_content,
            "OpponentModeling on_game_start": "self.opponent_modeling.on_game_start" in impl_content,
            "OpponentModeling on_game_end": "self.opponent_modeling.on_game_end" in impl_content,
        }

        all_passed = True
        for check_name, check_result in integration_checks.items():
            if check_result:
                print(f"  [OK] {check_name}")
            else:
                print(f"  [X] {check_name}")
                all_passed = False
                self.results["errors"].append(f"Missing integration: {check_name}")

        self.results["opponent_modeling"]["integration_points"] = all_passed

        # Check bot_step_integration.py
        step_file = self.base_dir / "bot_step_integration.py"
        with open(step_file, 'r', encoding='utf-8') as f:
            step_content = f.read()

        step_checks = {
            "OpponentModeling on_step": "opponent_modeling.on_step" in step_content,
            "AdvancedMicroV3 on_step": "micro_v3.on_step" in step_content,
        }

        for check_name, check_result in step_checks.items():
            if check_result:
                print(f"  [OK] {check_name}")
            else:
                print(f"  [X] {check_name}")
                all_passed = False
                self.results["errors"].append(f"Missing step integration: {check_name}")

        self.results["micro_v3"]["integration_points"] = all_passed

        return all_passed

    def generate_report(self):
        """Generate and save test report"""
        print("\n" + "=" * 70)
        print("INTEGRATION TEST REPORT")
        print("=" * 70)

        # Summary
        total_checks = 0
        passed_checks = 0

        for category in ["opponent_modeling", "micro_v3", "performance"]:
            if category in self.results:
                for key, value in self.results[category].items():
                    total_checks += 1
                    if "success" in str(value).lower() or "passed" in str(value).lower() or value is True:
                        passed_checks += 1

        success_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0

        print(f"\n[OK] Passed: {passed_checks}/{total_checks} ({success_rate:.1f}%)")

        if self.results["errors"]:
            print(f"\n[X] Errors found: {len(self.results['errors'])}")
            for i, error in enumerate(self.results["errors"], 1):
                print(f"   {i}. {error}")
        else:
            print("\n[OK] No errors found!")

        # Save report to file
        report_file = self.base_dir / "integration_test_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n[STATS] Full report saved to: {report_file}")

        print("=" * 70)

        return len(self.results["errors"]) == 0

    def run_all_tests(self) -> bool:
        """Run all validation tests"""
        print("\n" + "=" * 70)
        print("PHASE 15 INTEGRATION VALIDATION")
        print("=" * 70 + "\n")

        tests = [
            ("File Structure", self.check_file_structure),
            ("Imports", self.check_imports),
            ("Data Directory", self.check_data_directory),
            ("OpponentModeling Init", self.test_opponent_modeling_initialization),
            ("AdvancedMicroV3 Init", self.test_micro_v3_initialization),
            ("Integration Points", self.check_integration_points),
            ("Unit Tests", self.run_unit_tests),
        ]

        all_passed = True
        for test_name, test_func in tests:
            try:
                if not test_func():
                    all_passed = False
                    print(f"\n[\!]  Test '{test_name}' failed!")
            except Exception as e:
                all_passed = False
                print(f"\n[X] Test '{test_name}' crashed: {e}")
                self.results["errors"].append(f"{test_name} crashed: {e}")

        # Generate report
        self.generate_report()

        return all_passed


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Phase 15 Integration Test Script"
    )
    parser.add_argument(
        "--quick-test",
        action="store_true",
        help="Run quick validation tests only (no unit tests)"
    )

    args = parser.parse_args()

    tester = IntegrationTester()

    if args.quick_test:
        print("[INFO] Running quick validation tests...\n")
        tests = [
            ("File Structure", tester.check_file_structure),
            ("Imports", tester.check_imports),
            ("Data Directory", tester.check_data_directory),
            ("Integration Points", tester.check_integration_points),
        ]

        all_passed = True
        for test_name, test_func in tests:
            try:
                if not test_func():
                    all_passed = False
            except Exception as e:
                all_passed = False
                print(f"\n[X] Test '{test_name}' crashed: {e}")

        tester.generate_report()
    else:
        all_passed = tester.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
