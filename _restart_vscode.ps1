# Kill PS Language Server first
Stop-Process -Name language_server_windows_x64 -Force -ErrorAction SilentlyContinue

# Kill all Antigravity (VSCode) processes
Stop-Process -Name Antigravity -Force -ErrorAction SilentlyContinue
Write-Host "All Antigravity processes killed."

Start-Sleep 3

# Restart with workspace
Start-Process "C:\Users\sun47\AppData\Local\Programs\Antigravity\Antigravity.exe" -ArgumentList "D:\Swarm-contol-in-sc2bot"
Write-Host "Antigravity restarting..."

Start-Sleep 12

# Verify PS LSP is dead
$ps = Get-Process language_server_windows_x64 -ErrorAction SilentlyContinue
if ($ps) { Write-Host "PS LSP: STILL ALIVE $([math]::Round($ps.WorkingSet64/1MB,0))MB" -ForegroundColor Red }
else { Write-Host "PS LSP: GONE!" -ForegroundColor Green }

# Final memory
$os = Get-CimInstance Win32_OperatingSystem
$usedGB = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/1MB, 1)
$freeGB = [math]::Round($os.FreePhysicalMemory/1MB, 1)
$pct = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / $os.TotalVisibleMemorySize * 100, 1)
Write-Host "Memory: ${usedGB}GB / 15.8GB (${pct}%) | Free: ${freeGB}GB"
