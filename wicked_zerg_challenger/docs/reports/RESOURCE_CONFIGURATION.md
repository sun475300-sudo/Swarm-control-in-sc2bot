# Resource Configuration - Single Instance with Full GPU/CPU Utilization

## Configuration Summary

The project has been configured to run with **1 instance** using **full GPU and CPU utilization**.

### Changes Applied

#### 1. Instance Count
- **File**: `local_training/scripts/parallel_train_integrated.py`
- **Change**: `NUM_INSTANCES` default changed from `2` to `1`
- **Result**: Only 1 game instance will run at a time

#### 2. CPU Full Utilization
- **File**: `zerg_net.py`
- **Change**: Added CPU thread configuration in `ReinforcementLearner.__init__()`
  - `torch.set_num_threads(cpu_count)` - Uses all CPU cores for PyTorch
  - `OMP_NUM_THREADS` - OpenMP thread count
  - `MKL_NUM_THREADS` - Intel MKL thread count
- **Result**: All available CPU cores are used for maximum performance

#### 3. GPU Full Utilization
- **File**: `zerg_net.py`
- **Status**: Already configured
  - Automatic GPU detection (`_get_device()`)
  - Model and tensors moved to GPU automatically
  - All operations run on GPU when available
- **Result**: GPU is fully utilized for neural network operations

#### 4. Main Training Script
- **File**: `local_training/main_integrated.py`
- **Change**: Added CPU configuration at module level and in `__main__`
- **Result**: CPU threads configured before training starts

### Performance Benefits

1. **Single Instance**: 
   - All GPU memory dedicated to one game instance
   - No resource contention between instances
   - Maximum performance per game

2. **Full CPU Utilization**:
   - All CPU cores used for data processing
   - Faster tensor operations
   - Better parallel processing

3. **Full GPU Utilization**:
   - All GPU memory available for model
   - No memory fragmentation
   - Maximum inference speed

### Usage

The configuration is automatic. Simply run:

```bash
python local_training/main_integrated.py
```

Or use the parallel training script (which will use 1 instance):

```bash
python local_training/scripts/parallel_train_integrated.py
```

### Environment Variables

You can override the instance count if needed:

```bash
# Force 1 instance (default)
$env:NUM_INSTANCES=1; python parallel_train_integrated.py

# Or use more instances if you have high-end GPU
$env:NUM_INSTANCES=2; python parallel_train_integrated.py
```

### Monitoring

- **GPU Usage**: Check with `nvidia-smi` (if NVIDIA GPU)
- **CPU Usage**: Check with Task Manager (Windows) or `htop` (Linux)
- **Memory**: Monitor with system tools

---

**Configuration Date**: 2026-01-14
**Status**: Active
