$ErrorActionPreference = "SilentlyContinue"

# 1. Define Archive Path
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$archiveDir = "d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\local_training\archived_sessions\$timestamp"
New-Item -ItemType Directory -Force -Path $archiveDir | Out-Null

Write-Host "[INFO] reset_training: Archiving previous session to $archiveDir"

# 2. Archive Metadata Files
$statsFile = "d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\training_stats.json"
if (Test-Path $statsFile) {
    Move-Item -Path $statsFile -Destination $archiveDir
}

# 3. Archive & Reset Data Directories
$dataDirs = @(
    "d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\local_training\data",
    "d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\local_training\models",
    "d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\local_training\extracted_data",
    "d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\local_training\logs",
    "d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\local_training\checkpoints",
    "d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\local_training\output"
)

foreach ($dir in $dataDirs) {
    if (Test-Path $dir) {
        $dirName = Split-Path $dir -Leaf
        $dest = Join-Path $archiveDir $dirName
        Move-Item -Path $dir -Destination $dest
    }
    # Re-create empty directory
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

# 4. Clear/Re-initialize Stats File
New-Item -ItemType File -Force -Path $statsFile | Out-Null

Write-Host "[SUCCESS] Training session reset complete."
Write-Host "[ACTION] Please run 'python run_training.py' (or your start script) to begin a fresh session."
