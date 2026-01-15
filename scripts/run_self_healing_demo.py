"""
Demonstrate self-healing pipeline.
"""

from pathlib import Path
from src.self_healing.pipeline import SelfHealingPipeline


def main() -> None:
    """Run self-healing demo."""
    print("="*70)
    print("Self-Healing Pipeline Demo")
    print("="*70)
    print()
    
    # Create sample error log
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    error_log = log_dir / "error.log"
    error_log.write_text("""
ModuleNotFoundError: No module named 'nonexistent_module'
Traceback (most recent call last):
  File "test.py", line 1, in <module>
    import nonexistent_module
""", encoding="utf-8")
    
    print("[INFO] Created sample error log at logs/error.log")
    print()
    
    # Run pipeline
    pipeline = SelfHealingPipeline()
    result = pipeline.run_once()
    
    if result:
        print("[SUCCESS] Issue detected and suggestion generated!")
        print("[INFO] Check patch_suggestions.txt for details")
    else:
        print("[INFO] No issues detected")
    
    print()
    print("="*70)


if __name__ == "__main__":
    main()
