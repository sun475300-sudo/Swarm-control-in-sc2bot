# -*- coding: utf-8 -*-
"""
Run game training 5 times

This script executes run_with_training.py 5 times sequentially.
"""

import subprocess
import sys
from pathlib import Path

def main():
    project_root = Path(__file__).parent.parent
    training_script = project_root / "run_with_training.py"
    
    if not training_script.exists():
        print(f"[ERROR] Training script not found: {training_script}")
        sys.exit(1)
    
    print("=" * 70)
    print("? GAME TRAINING - 5 GAMES")
    print("=" * 70)
    
    for i in range(1, 6):
        print(f"\n{'='*70}")
        print(f"? GAME #{i} / 5")
        print(f"{'='*70}\n")
        
        try:
            # Run training script
            result = subprocess.run(
                [sys.executable, str(training_script)],
                cwd=str(project_root),
                check=False
            )
            
            if result.returncode == 0:
                print(f"\n? Game #{i} completed successfully")
            else:
                print(f"\n??  Game #{i} completed with exit code: {result.returncode}")
        
        except KeyboardInterrupt:
            print(f"\n\n??  Training interrupted by user at Game #{i}")
            sys.exit(1)
        except Exception as e:
            print(f"\n? Error running Game #{i}: {e}")
            continue
    
    print(f"\n{'='*70}")
    print("? ALL 5 GAMES COMPLETED")
    print("=" * 70)

if __name__ == "__main__":
    main()
