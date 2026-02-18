# ═══════════════════════════════════════════════════════════
# JARVIS Discord Bot - Auto Start Script (Safe Launcher Wrapper)
# ═══════════════════════════════════════════════════════════

$WorkDir = "d:\Swarm-contol-in-sc2bot"
$SafeLauncher = "start_jarvis_safe.py"
$LogFile = "$WorkDir\logs\jarvis_autostart.log"
$Python = "python"

# 로그 디렉토리 생성
if (-not (Test-Path "$WorkDir\logs")) { New-Item -ItemType Directory -Path "$WorkDir\logs" | Out-Null }

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $LogFile -Value "[$timestamp] Executing $SafeLauncher..."

Set-Location $WorkDir

try {
    # start_jarvis_safe.py 실행 (백그라운드)
    # Python 스크립트 내에서 subprocess.Popen으로 봇을 실행하므로 여기선 wait 없이 실행해도 됨
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Python
    $psi.Arguments = $SafeLauncher
    $psi.WorkingDirectory = $WorkDir
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    
    $proc = [System.Diagnostics.Process]::Start($psi)
    Add-Content -Path $LogFile -Value "[$timestamp] Launcher started (PID: $($proc.Id))"
} catch {
    Add-Content -Path $LogFile -Value "[$timestamp] Failed to start launcher: $_"
}


