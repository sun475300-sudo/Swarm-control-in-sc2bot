# Game Training Started

## Date: 2026-01-16

## Status: ? Training Started

### Command Executed
```batch
python run_with_training.py
```

### Training Configuration
- **Mode**: Single game mode (1 game at a time)
- **Visual**: Game window visible
- **Monitoring**: http://localhost:8001
- **Neural Network**: Enabled
- **Manus Monitoring**: Enabled (if configured)

### Learned Parameters Applied
The following parameters learned from replay comparison are being used:

```json
{
  "gas_supply": 17.0,
  "hive_supply": 12.0,
  "hydralisk_den_supply": 122.0,
  "lair_supply": 12.0,
  "natural_expansion_supply": 30.0,
  "roach_warren_supply": 55.0,
  "spawning_pool_supply": 17.0
}
```

### Monitoring

#### Local Monitoring Server
- **URL**: http://localhost:8001
- **Features**:
  - Real-time game statistics
  - Training progress
  - Performance metrics
  - Build order execution

#### Manus App Monitoring (if configured)
- **URL**: https://manus.im/app/3RkAdZMhHugbLDuJwVpTpr
- **Features**:
  - Remote monitoring
  - Historical data
  - Performance analysis

### Training Features

1. **Adaptive Difficulty**: Automatically adjusts based on performance
2. **Error Recovery**: Handles connection errors and retries
3. **Background Learning**: Replay analysis and model training in background
4. **Session Management**: Tracks training statistics and progress

### How to Stop Training

- **Press Ctrl+C** in the terminal to stop training gracefully
- Training will:
  - Complete current game
  - Save model checkpoint
  - Stop background learners
  - Stop monitoring servers
  - Generate training summary

### Expected Output

Training will show:
- Game initialization
- Map selection
- Game execution
- Result logging
- Statistics updates
- Model saving

### Next Steps After Training

1. **Post-Training Analysis**: Run comparison analysis
2. **Replay Learning**: Learn from training replays
3. **Parameter Update**: Apply new learned parameters
4. **Next Training Cycle**: Start next training session

### Notes

- Training runs continuously until stopped
- Games are saved as replays
- Model is saved after each game
- Statistics are logged to `training_stats.json`
- Monitoring data is available in real-time
