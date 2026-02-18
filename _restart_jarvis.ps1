# JARVIS Full System Restart
$ErrorActionPreference = 'SilentlyContinue'

# 1. CLIProxy (port 8317)
Start-Process python -ArgumentList "C:\Users\sun47\.openclaw\run_proxy.py" -WindowStyle Hidden
Start-Sleep -Seconds 2

# 2. Gateway (port 18789)
$env:ANTHROPIC_BASE_URL = "http://127.0.0.1:8317"
$env:ANTHROPIC_API_KEY = "dummy"
Start-Process node -ArgumentList "C:\Users\sun47\AppData\Roaming\npm\node_modules\openclaw\dist\index.js gateway --port 18789" -WindowStyle Hidden
Start-Sleep -Seconds 1

# 3. Voice Bridge (port 8765)
Start-Process python -ArgumentList "C:\Users\sun47\.openclaw\mcp_gateway_proxy.py" -WindowStyle Hidden
Start-Sleep -Seconds 1

# 4. Discord Bot
Start-Process node -ArgumentList "C:\Users\sun47\.openclaw\workspace\discord_voice_chat_jarvis.js" -WindowStyle Hidden -WorkingDirectory "D:\Swarm-contol-in-sc2bot"
Start-Sleep -Seconds 1

# 5. Crypto HTTP Service (port 8766)
Start-Process python -ArgumentList "D:\Swarm-contol-in-sc2bot\crypto_trading\crypto_http_service.py" -WindowStyle Hidden -WorkingDirectory "D:\Swarm-contol-in-sc2bot"
Start-Sleep -Seconds 3

# Verify
$ports = @(
    @{Name="CLIProxy"; Port=8317},
    @{Name="Gateway"; Port=18789},
    @{Name="VoiceBridge"; Port=8765},
    @{Name="DiscordBot"; Port=19999},
    @{Name="CryptoService"; Port=8766}
)
$ok = 0
foreach ($svc in $ports) {
    $conn = netstat -ano | Select-String "LISTENING" | Select-String ":$($svc.Port)\s"
    if ($conn) {
        Write-Host "[OK] $($svc.Name) :$($svc.Port)" -ForegroundColor Green
        $ok++
    } else {
        Write-Host "[FAIL] $($svc.Name) :$($svc.Port)" -ForegroundColor Red
    }
}
Write-Host "`n$ok/5 services running"