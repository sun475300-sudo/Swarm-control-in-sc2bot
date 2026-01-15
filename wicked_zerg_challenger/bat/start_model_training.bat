@echo off
REM Neural Network Model Training - Start Game with Training Enabled
REM 게임 실행하여 신경망 모델 생성 시작

REM CRITICAL: Ensure script runs from project root regardless of current directory
cd /d "%~dp0.."

echo.
echo ================================
echo NEURAL NETWORK MODEL TRAINING
echo ================================
echo.
echo This will start a StarCraft II game and train the neural network model.
echo Model will be saved to: local_training/models/zerg_net_model.pt
echo.

REM Check if StarCraft II is available
python -c "import sys; sys.path.insert(0, '.'); from sc2 import run_game, maps, Race, Difficulty; print('[OK] StarCraft II API available')" 2>nul || (
    echo [WARNING] StarCraft II API may not be available
    echo [INFO] Continuing anyway...
)

echo.
echo [INFO] Training Configuration:
echo   - 15-dimensional state vector (Self 5 + Enemy 10)
echo   - REINFORCE algorithm for policy learning
echo   - Model auto-saves after each game
echo   - Training enabled: train_mode=True
echo.

pause

echo.
echo [STEP 1] Starting game with neural network training...
echo [INFO] Game window will open - you can watch the training in real-time!
echo.

python run_with_training.py

echo.
echo ================================
echo TRAINING COMPLETE
echo ================================
echo.
echo Model saved to: local_training/models/zerg_net_model.pt
echo You can now use this trained model in future games!
echo.

pause
