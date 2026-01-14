# ? Android 앱 데이터 전달 테스트 - 빠른 시작

**작성일**: 2026-01-14

---

## ? 빠른 테스트 (3단계)

### 1단계: 서버 실행

```powershell
cd wicked_zerg_challenger\monitoring
python dashboard_api.py
```

또는:

```powershell
python dashboard.py
```

**확인**: 브라우저에서 `http://localhost:8000/health` 접속 → 응답 확인

---

### 2단계: API 테스트

```powershell
cd wicked_zerg_challenger\monitoring
python test_mobile_app_data.py
```

**또는 브라우저에서 직접 확인**:
- `http://localhost:8000/api/game-state`
- `http://localhost:8000/api/combat-stats`
- `http://localhost:8000/api/learning-progress`

---

### 3단계: Android 앱 확인

1. **Android Studio에서 앱 실행**
2. **Logcat 열기** (하단 탭)
3. **필터**: `ApiClient` 또는 `WickedZerg`
4. **확인 사항**:
   - ? "Connected" 메시지
   - ? UI에 데이터 표시 (Minerals, Vespene, Supply 등)

---

## ? 체크리스트

### 서버 측
- [ ] 서버가 `http://localhost:8000`에서 실행 중
- [ ] `/api/game-state` 엔드포인트 응답 확인
- [ ] CORS 설정 확인 (Android 에뮬레이터 허용)

### Android 앱 측
- [ ] `BASE_URL`이 `http://10.0.2.2:8000`로 설정됨
- [ ] 인터넷 권한이 `AndroidManifest.xml`에 있음
- [ ] 로그에서 "Connected" 메시지 확인
- [ ] UI에 데이터 표시됨

---

## ? 문제 해결

### "Connection refused"
→ 서버가 실행되지 않음. `python dashboard_api.py` 실행

### "Timeout"
→ 포트 8000이 다른 프로그램에서 사용 중. 포트 변경 또는 다른 프로그램 종료

### 데이터가 표시되지 않음
→ 필드명 매핑 확인 (snake_case → camelCase)

---

## ? 상세 가이드

전체 가이드는 `docs/ANDROID_DATA_TRANSFER_TEST.md` 참고

---

**마지막 업데이트**: 2026-01-14
