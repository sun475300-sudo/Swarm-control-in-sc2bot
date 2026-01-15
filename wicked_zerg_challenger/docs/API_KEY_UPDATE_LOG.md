# ? API 키 업데이트 로그

**작성일**: 2026-01-14

---

## ? 업데이트 내역

### Google Cloud API 키 업데이트

**날짜**: 2026-01-14  
**키**: `AIzaSyD-c6...UZrc`

**저장 위치**:
- ? `secrets/gemini_api.txt` (권장)
- ? `api_keys/GOOGLE_API_KEY.txt` (하위 호환성)
- ? `api_keys/GEMINI_API_KEY.txt` (하위 호환성)

**사용 위치**:
- `genai_self_healing.py` - Gemini Self-Healing 시스템
- `local_training/strategy_audit.py` - Build-Order Gap Analyzer
- `wicked_zerg_bot_pro.py` - 봇 초기화 시

---

## ? 확인 사항

### 키 로드 확인

다음 명령으로 키가 올바르게 로드되는지 확인:

```bash
python -c "from tools.load_api_key import get_google_api_key; print(get_google_api_key()[:20] + '...')"
```

**예상 출력**: `AIzaSyD-c6nmOLolncI...`

---

## ? 보안 주의사항

1. **Git에 커밋하지 마세요!**
   - `.gitignore`에 `secrets/`와 `api_keys/` 폴더가 이미 추가되어 있습니다
   - 실수로 커밋했다면 즉시 키를 재생성하세요

2. **파일 권한 설정** (Linux/Mac):
   ```bash
   chmod 600 secrets/gemini_api.txt
   chmod 600 api_keys/GOOGLE_API_KEY.txt
   chmod 600 api_keys/GEMINI_API_KEY.txt
   ```

3. **키 공유 금지**:
   - API 키는 개인용으로만 사용하세요
   - 팀 공유가 필요하면 환경 변수나 보안 저장소 사용

---

## ? 관련 문서

- **API 키 관리 가이드**: `docs/API_KEYS_MANAGEMENT.md`
- **보안 설정**: `docs/SECURITY_SETUP_COMPLETE.md`
- **빠른 설정**: `api_keys/SETUP_INSTRUCTIONS.md`

---

**마지막 업데이트**: 2026-01-14
