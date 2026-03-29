# P101: PowerShell - Windows Automation
# SC2 Bot deployment and management automation

param(
    [string]$Action = "deploy",
    [string]$Map = "AbyssalReefLE",
    [int]$Games = 5
)

$ErrorActionPreference = "Stop"

function Install-SC2Bot {
    Write-Host "Installing SC2 Bot dependencies..." -ForegroundColor Cyan
    pip install -r requirements.txt
    Write-Host "Installing Rust extensions..." -ForegroundColor Cyan
    cargo build --release
}

function Run-Game {
    param([string]$MapName, [string]$EnemyRace = "Random")
    
    Write-Host "Starting game on $MapName vs $EnemyRace..." -ForegroundColor Green
    python run_single_game.py --map $MapName --enemy-race $EnemyRace
}

function Get-GameStats {
    $replays = Get-ChildItem -Path "replays" -Filter "*.SC2Replay"
    Write-Host "Total Replays: $($replays.Count)"
    
    $latest = $replays | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latest) {
        Write-Host "Latest: $($latest.Name) - $($latest.LastWriteTime)"
    }
}

function Start-TrainingLoop {
    Write-Host "Starting automated training loop..." -ForegroundColor Yellow
    for ($i = 0; $i -lt $Games; $i++) {
        Run-Game -MapName $Map
    }
    Get-GameStats
}

switch ($Action) {
    "install" { Install-SC2Bot }
    "run" { Run-Game -MapName $Map }
    "train" { Start-TrainingLoop }
    "stats" { Get-GameStats }
    default { Write-Host "Usage: .\automation.ps1 -Action [install|run|train|stats]" }
}
