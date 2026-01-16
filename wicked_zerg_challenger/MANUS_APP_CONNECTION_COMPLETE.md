# Manus App Connection Setup Complete

## Date: 2026-01-16

## ? Setup Completed

### Environment Variables Set

1. **MANUS_DASHBOARD_URL**: `https://manus.im/app/3RkAdZMhHugbLDuJwVpTpr`
2. **MANUS_DASHBOARD_ENABLED**: `1` (enabled)
3. **MANUS_SYNC_INTERVAL**: `5` (seconds)

### Files Created

1. **`bat/setup_manus_app_connection.bat`**: Automated setup script
2. **`MANUS_APP_CONNECTION_SETUP.md`**: Detailed setup guide

## ? Manus App URL

**App URL**: `https://manus.im/app/3RkAdZMhHugbLDuJwVpTpr`  
**Browser Setup**: `https://manus.im/app/3RkAdZMhHugbLDuJwVpTpr?redirectUrl=%252Fmy-browser%253Fstep%253Dget-started%2526enable`

## ? Next Steps

### 1. Complete Browser Setup in Manus App

1. Open the Manus app:
   ```
   https://manus.im/app/3RkAdZMhHugbLDuJwVpTpr?redirectUrl=%252Fmy-browser%253Fstep%253Dget-started%2526enable
   ```

2. Follow the setup wizard:
   - Enable browser connection
   - Grant necessary permissions
   - Complete the setup steps

### 2. Verify Connection

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

### 3. Start Training with Monitoring

```batch
cd wicked_zerg_challenger
python run_with_training.py
```

### 4. Monitor in Manus App

- Open: `https://manus.im/app/3RkAdZMhHugbLDuJwVpTpr`
- View real-time game statistics
- Monitor training progress
- Check performance metrics

## ?? Configuration

### Environment Variables (Set Permanently)

The following environment variables have been set in your user profile:

- `MANUS_DASHBOARD_URL=https://manus.im/app/3RkAdZMhHugbLDuJwVpTpr`
- `MANUS_DASHBOARD_ENABLED=1`
- `MANUS_SYNC_INTERVAL=5`

### Verify Environment Variables

```powershell
$env:MANUS_DASHBOARD_URL
$env:MANUS_DASHBOARD_ENABLED
$env:MANUS_SYNC_INTERVAL
```

## ? Notes

- The Manus app URL format: `https://manus.im/app/{APP_ID}`
- Browser setup URL includes redirect parameters for setup wizard
- Environment variables are set permanently in your user profile
- API keys are optional but may be required for some features
- Data syncs every 5 seconds (configurable via `MANUS_SYNC_INTERVAL`)

## ? Troubleshooting

### Connection Issues

1. Verify environment variables:
   ```powershell
   $env:MANUS_DASHBOARD_URL
   ```

2. Test connection:
   ```batch
   python monitoring\manus_dashboard_client.py
   ```

3. Check Manus app is accessible in browser

4. Verify browser connection is enabled in Manus app

### Data Not Syncing

1. Check `MANUS_DASHBOARD_ENABLED=1`
2. Verify sync interval: `MANUS_SYNC_INTERVAL=5`
3. Review logs for error messages
4. Ensure browser connection is enabled in Manus app

## ? Related Files

- `bat/setup_manus_app_connection.bat`: Setup script
- `MANUS_APP_CONNECTION_SETUP.md`: Detailed guide
- `monitoring/manus_dashboard_client.py`: Client implementation
- `monitoring/manus_sync.py`: Sync service
