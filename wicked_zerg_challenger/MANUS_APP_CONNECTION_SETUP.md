# Manus App Monitoring Connection Setup

## Date: 2026-01-16

## Manus App URL
**App URL**: `https://manus.im/app/3RkAdZMhHugbLDuJwVpTpr`  
**App ID**: `3RkAdZMhHugbLDuJwVpTpr`  
**Browser Setup**: `https://manus.im/app/3RkAdZMhHugbLDuJwVpTpr?redirectUrl=%252Fmy-browser%253Fstep%253Dget-started%2526enable`

## Quick Setup

### Option 1: Automated Setup (Recommended)
```batch
bat\setup_manus_app_connection.bat
```

This script will:
1. Set environment variables for current session
2. Set permanent environment variables
3. Test the connection

### Option 2: Manual Setup

#### PowerShell (Current Session)
```powershell
$env:MANUS_DASHBOARD_URL = "https://manus.im/app/3RkAdZMhHugbLDuJwVpTpr"
$env:MANUS_DASHBOARD_ENABLED = "1"
$env:MANUS_SYNC_INTERVAL = "5"
```

#### Permanent Setup (User Environment)
```powershell
[System.Environment]::SetEnvironmentVariable("MANUS_DASHBOARD_URL", "https://manus.im/app/3RkAdZMhHugbLDuJwVpTpr", "User")
[System.Environment]::SetEnvironmentVariable("MANUS_DASHBOARD_ENABLED", "1", "User")
[System.Environment]::SetEnvironmentVariable("MANUS_SYNC_INTERVAL", "5", "User")
```

## Verification

### Check Environment Variables
```powershell
$env:MANUS_DASHBOARD_URL
$env:MANUS_DASHBOARD_ENABLED
$env:MANUS_SYNC_INTERVAL
```

### Test Connection
```batch
cd wicked_zerg_challenger\monitoring
python manus_dashboard_client.py
```

Expected output:
```
[MANUS] 클라이언트 초기화: https://manus.im/app/3RkAdZMhHugbLDuJwVpTpr (활성화: True)
Manus 대시보드 연결 확인 중...
? 연결 테스트 성공
```

## Browser Connection Setup

1. **Open Manus App**: 
   - URL: `https://manus.im/app/3RkAdZMhHugbLDuJwVpTpr?redirectUrl=%252Fmy-browser%253Fstep%253Dget-started%2526enable`
   - Or use the app directly: `https://manus.im/app/3RkAdZMhHugbLDuJwVpTpr`

2. **Complete Browser Setup**:
   - Follow the setup wizard in the app
   - Enable browser connection
   - Grant necessary permissions

3. **Verify Connection**:
   - Check that the app shows "Connected" status
   - Test data synchronization

## Usage

### Start Training with Manus Monitoring
```batch
cd wicked_zerg_challenger
python run_with_training.py
```

### Monitor in Manus App
- Open: `https://manus.im/app/3RkAdZMhHugbLDuJwVpTpr`
- View real-time game statistics
- Monitor training progress
- Check performance metrics

## Configuration Files

The Manus client will use:
- **Environment Variables** (priority 1)
- **API Key Files** (if needed):
  - `monitoring/api_keys/manus_api_key.txt`
  - `api_keys/manus_api_key.txt`
  - `secrets/manus_api_key.txt`

## Troubleshooting

### Connection Issues
1. Verify environment variables are set
2. Check Manus app is accessible
3. Test connection: `python monitoring\manus_dashboard_client.py`
4. Check firewall/network settings

### Data Not Syncing
1. Verify `MANUS_DASHBOARD_ENABLED=1`
2. Check sync interval: `MANUS_SYNC_INTERVAL=5`
3. Review logs for error messages
4. Ensure browser connection is enabled in Manus app

## Notes

- The Manus app URL format: `https://manus.im/app/{APP_ID}`
- Browser setup URL includes redirect parameters for setup wizard
- Environment variables take precedence over default values
- API keys are optional but may be required for some features
