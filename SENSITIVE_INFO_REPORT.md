# Sensitive Information Audit Report

The following sensitive information was detected within the `d:\Swarm-contol-in-sc2bot` workspace. These should be removed or moved to environment variables before any further push to GitHub.

## 1. Detected API Keys

| Type | Key Preview | Found In |
| :--- | :--- | :--- |
| **Google Gemini/Cloud** | `AIzaSyDNTN4yCP...` | `JARVIS_CLEAN_START.bat`, `JARVIS_RECOVERY.bat`, `JARVIS_VISIBLE_START.bat`, `run_jarvis_full_system.cmd`, `list_gemini_models.py`, `test_gemini.py`, etc. |
| **Google Gemini (Backup)** | `AIzaSyBDdPWJyX...` | `wicked_zerg_challenger\api_keys\GEMINI_API_KEY.txt`, `wicked_zerg_challenger\secrets\gemini_api.txt` |
| **Google Gemini (Tools)** | `AIzaSyC_CiEZ6C...` | `wicked_zerg_challenger\tools\cleanup_deployment_pipelines.ps1`, etc. |
| **Discord Bot Token** | *(Check `.env.jarvis`)* | Referenced in `discord_voice_chat_jarvis.js` |

## 2. High-Risk Files
These files are currently NOT ignored by Git and contain hardcoded secrets:
- `JARVIS_CLEAN_START.bat`
- `JARVIS_RECOVERY.bat`
- `JARVIS_VISIBLE_START.bat`
- `run_jarvis_full_system.cmd`
- Various `.py` and `.ps1` files in the root and `tools/` directory.

## 3. Recommended Security Lockdown Actions
1. **Move all keys to a `.env` file** (which is already in `.gitignore`).
2. **Update `.gitignore`** to explicitly block all local batch and config files.
3. **Redact keys** from the files below.
4. **Git Reset**: Once the files are clean, follow the "Clean Git History" guide to scrub previous commits.

---
*Created by JARVIS/Antigravity for Security Compliance.*
