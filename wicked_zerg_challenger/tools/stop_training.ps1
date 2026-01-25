# Force Stop Training Script (PowerShell)
Write-Host "========================================" -ForegroundColor Red
Write-Host "  FORCE STOPPING ALL TRAINING" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Red

# 1. Stop Python Training Scripts
$trainingScripts = @("run_with_training", "background_parallel_learner", "wicked_zerg_bot_pro")
Write-Host "`n[1] Check/Stop Training Scripts..." -ForegroundColor Yellow

$pythonProcs = Get-Process python -ErrorAction SilentlyContinue
foreach ($proc in $pythonProcs) {
    try {
        $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)").CommandLine
        foreach ($script in $trainingScripts) {
            if ($cmdLine -match $script) {
                Write-Host "   Killing Process: $($proc.Id) ($script)" -ForegroundColor Red
                Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
                break
            }
        }
    }
    catch {}
}

# 2. Stop StarCraft II (Optional - only if it looks like a bot instance)
# For safety, we won't kill SC2 blindly unless we are sure, but "Force Stop All Training" implies stopping the game too.
Write-Host "`n[2] Check/Stop StarCraft II..." -ForegroundColor Yellow
$sc2Procs = Get-Process SC2_x64 -ErrorAction SilentlyContinue
if ($sc2Procs) {
    Write-Host "   Found StarCraft II running. Killing to stop training loop." -ForegroundColor Red
    Stop-Process -Name SC2_x64 -Force -ErrorAction SilentlyContinue
}
else {
    Write-Host "   StarCraft II not running." -ForegroundColor Green
}

# 3. Stop Monitoring Servers
Write-Host "`n[3] Stopping Monitoring Servers..." -ForegroundColor Yellow
$monitorScript = Join-Path (Get-Location) "monitoring\stop_all_servers.ps1"
if (Test-Path $monitorScript) {
    & $monitorScript
}
else {
    Write-Host "   Monitoring stop script not found." -ForegroundColor Gray
}

Write-Host "`n[DONE] All training processes should be stopped." -ForegroundColor Green
