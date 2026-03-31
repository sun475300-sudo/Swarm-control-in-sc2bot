# Phase 562: PowerShell Automation
# SC2 Bot management on Windows with PowerShell

#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

$Script:Config = @{
    BotName     = "SC2ZergBot"
    Version     = "560.0"
    BotDir      = $PSScriptRoot
    PythonExe   = "python"
    LogDir      = Join-Path $PSScriptRoot "logs"
    ModelDir    = Join-Path $PSScriptRoot "models"
    PidFile     = Join-Path $PSScriptRoot ".bot.pid"
    MaxLogSizeMB = 100
}

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────

function Write-BotLog {
    param(
        [string]$Message,
        [ValidateSet("Info","OK","Warn","Error")]
        [string]$Level = "Info"
    )
    $colors = @{
        Info  = "Cyan"
        OK    = "Green"
        Warn  = "Yellow"
        Error = "Red"
    }
    $prefix = "[$Level]".PadRight(8)
    Write-Host "$prefix $Message" -ForegroundColor $colors[$Level]
}

# ─────────────────────────────────────────────
# Game state simulation
# ─────────────────────────────────────────────

class SC2GameState {
    [int]$Minerals   = 50
    [int]$Gas        = 0
    [int]$Supply     = 12
    [int]$MaxSupply  = 14
    [int]$Workers    = 12
    [int]$Army       = 0
    [int]$Frame      = 0
    [int]$Hatcheries = 1
    [double]$Threat  = 0.0

    [bool] CanAfford([int]$m, [int]$g) {
        return ($this.Minerals -ge $m -and $this.Gas -ge $g)
    }

    [bool] SupplyFull() {
        return ($this.Supply -ge $this.MaxSupply - 1)
    }

    [string] Phase() {
        if ($this.Frame -lt 1344) { return "Opening" }
        if ($this.Frame -lt 3360) { return "EarlyGame" }
        if ($this.Frame -lt 6720) { return "MidGame" }
        return "LateGame"
    }

    [SC2GameState] Clone() {
        $c = [SC2GameState]::new()
        $c.Minerals   = $this.Minerals
        $c.Gas        = $this.Gas
        $c.Supply     = $this.Supply
        $c.MaxSupply  = $this.MaxSupply
        $c.Workers    = $this.Workers
        $c.Army       = $this.Army
        $c.Frame      = $this.Frame
        $c.Hatcheries = $this.Hatcheries
        $c.Threat     = $this.Threat
        return $c
    }
}

$Script:UnitCosts = @{
    drone     = @{ Minerals = 50;  Gas = 0;  Supply = 1 }
    zergling  = @{ Minerals = 25;  Gas = 0;  Supply = 1 }
    roach     = @{ Minerals = 75;  Gas = 25; Supply = 2 }
    hydralisk = @{ Minerals = 100; Gas = 50; Supply = 2 }
    overlord  = @{ Minerals = 100; Gas = 0;  Supply = 0 }
}

function Get-Decision {
    param([SC2GameState]$State)

    if ($State.Threat -gt 0.6)                          { return "defend"   }
    if ($State.SupplyFull() -and $State.CanAfford(100,0)) { return "overlord" }
    if ($State.Workers -lt 22 -and $State.CanAfford(50,0)) { return "drone"  }
    if ($State.Minerals -ge 300 -and $State.Hatcheries -lt 3) { return "expand" }
    if ($State.CanAfford(75, 25))                       { return "roach"    }
    if ($State.CanAfford(25, 0))                        { return "zergling" }
    return "wait"
}

function Invoke-Action {
    param([SC2GameState]$State, [string]$Action)
    $s = $State.Clone()

    switch ($Action) {
        { $_ -in $Script:UnitCosts.Keys } {
            $cost = $Script:UnitCosts[$_]
            if (-not $s.CanAfford($cost.Minerals, $cost.Gas)) { break }
            $s.Minerals -= $cost.Minerals
            $s.Gas      -= $cost.Gas
            $s.Supply   += $cost.Supply
            switch ($_) {
                "drone"    { $s.Workers++; break }
                "overlord" { $s.MaxSupply += 8; break }
                default    { $s.Army += $cost.Supply }
            }
        }
        "expand" {
            if ($s.Minerals -lt 300) { break }
            $s.Minerals   -= 300
            $s.Hatcheries++
            $s.Workers    += 4
        }
    }
    return $s
}

function Step-GameState {
    param([SC2GameState]$State)
    $s = $State.Clone()
    $income = [math]::Floor($s.Workers * 8 / 10)
    $s.Minerals += $income
    $s.Frame++
    $s.Threat = [math]::Min(1.0, $s.Threat + 0.0001)
    $action = Get-Decision -State $s
    return Invoke-Action -State $s -Action $action
}

function Invoke-Simulation {
    param([int]$Frames = 2000, [string]$EnemyRace = "Terran")
    $state   = [SC2GameState]::new()
    $history = [System.Collections.Generic.List[SC2GameState]]::new()

    for ($i = 0; $i -lt $Frames; $i++) {
        $state = Step-GameState -State $state
        $history.Add($state.Clone())
    }
    return @{ State = $state; History = $history }
}

# ─────────────────────────────────────────────
# Bot process management
# ─────────────────────────────────────────────

function Start-BotProcess {
    $cfg = $Script:Config
    Write-BotLog "Starting $($cfg.BotName) v$($cfg.Version)..." -Level Info

    if (Test-Path $cfg.PidFile) {
        $oldPid = Get-Content $cfg.PidFile
        if (Get-Process -Id $oldPid -ErrorAction SilentlyContinue) {
            Write-BotLog "Bot already running (PID $oldPid)" -Level Warn
            return
        }
        Remove-Item $cfg.PidFile -Force
    }

    New-Item -ItemType Directory -Path $cfg.LogDir   -Force | Out-Null
    New-Item -ItemType Directory -Path $cfg.ModelDir -Force | Out-Null

    $logFile = Join-Path $cfg.LogDir "$($cfg.BotName)_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
    $proc = Start-Process -FilePath $cfg.PythonExe `
        -ArgumentList "main.py", "--bot-name", $cfg.BotName `
        -WorkingDirectory $cfg.BotDir `
        -RedirectStandardOutput $logFile `
        -PassThru -NoNewWindow

    $proc.Id | Out-File $cfg.PidFile -Encoding ASCII
    Write-BotLog "Bot started (PID $($proc.Id))" -Level OK
}

function Stop-BotProcess {
    $pidFile = $Script:Config.PidFile
    if (-not (Test-Path $pidFile)) {
        Write-BotLog "Bot not running (no PID file)" -Level Warn
        return
    }
    $pid = [int](Get-Content $pidFile)
    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($proc) {
        $proc | Stop-Process -Force
        Write-BotLog "Stopped PID $pid" -Level OK
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

function Get-BotStatus {
    $pidFile = $Script:Config.PidFile
    if (-not (Test-Path $pidFile)) {
        return [PSCustomObject]@{ Status = "STOPPED"; PID = $null }
    }
    $pid = [int](Get-Content $pidFile)
    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($proc) {
        return [PSCustomObject]@{
            Status  = "RUNNING"
            PID     = $pid
            CPU     = $proc.CPU
            Memory  = [math]::Round($proc.WorkingSet64 / 1MB, 1)
        }
    }
    return [PSCustomObject]@{ Status = "DEAD (stale PID $pid)"; PID = $pid }
}

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

Write-Host "`nPhase 562: PowerShell Automation — SC2 Bot Manager`n" -ForegroundColor Cyan

# Run simulation
Write-BotLog "Running economy simulation (2000 frames)..." -Level Info
$result = Invoke-Simulation -Frames 2000 -EnemyRace "Terran"
$final  = $result.State

Write-Host ""
Write-Host "Final State:" -ForegroundColor Yellow
Write-Host "  Frame:     $($final.Frame)"
Write-Host "  Minerals:  $($final.Minerals)"
Write-Host "  Workers:   $($final.Workers)"
Write-Host "  Army:      $($final.Army)"
Write-Host "  Supply:    $($final.Supply)/$($final.MaxSupply)"
Write-Host "  Phase:     $($final.Phase())"

# Analytics using LINQ-style pipeline
$history = $result.History
$avgMin  = ($history | Measure-Object -Property Minerals -Average).Average
$maxWork = ($history | Measure-Object -Property Workers  -Maximum).Maximum
$maxArmy = ($history | Measure-Object -Property Army     -Maximum).Maximum

Write-Host ""
Write-Host "Analytics:" -ForegroundColor Yellow
Write-Host "  Avg Minerals: $([math]::Round($avgMin, 1))"
Write-Host "  Max Workers:  $maxWork"
Write-Host "  Max Army:     $maxArmy"

# Status check
$status = Get-BotStatus
Write-Host ""
Write-BotLog "Bot status: $($status.Status)" -Level Info
