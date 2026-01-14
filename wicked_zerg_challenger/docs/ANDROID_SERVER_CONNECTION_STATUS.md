# ? Android 앱 서버 연결 상태 표시 기능

**작성일**: 2026-01-14

---

## ? 구현 완료

모든 Fragment에 서버 연결 상태 감지 및 표시 기능이 추가되었습니다.

---

## ? 구현 내용

### 1. 연결 상태 감지

각 Fragment에서 다음 예외를 구분하여 처리합니다:

- **`ConnectException`**: 서버에 연결할 수 없음
- **`SocketTimeoutException`**: 서버 응답 시간 초과
- **기타 Exception**: 알 수 없는 오류

### 2. 상태 표시

#### 연결됨
- 상태 텍스트: "Server Connected" (또는 "서버 연결됨")
- 색상: 녹색 (`#00ff00`)
- 표시: 연결되면 숨김 (기본적으로 표시하지 않음)

#### 연결 끊김
- 상태 텍스트: "Server Disconnected: [오류 메시지]"
- 색상: 빨간색 (`#ff0000`)
- 표시: 항상 표시

---

## ? 각 Fragment별 구현

### MonitorFragment
- **상태 표시 위치**: 헤더 아래
- **메시지**:
  - 연결됨 + 게임 진행 중: "서버 연결됨 - 게임 진행 중"
  - 연결됨 + 게임 없음: "서버 연결됨 - 게임 없음"
  - 연결 끊김: "서버 연결 끊김 - [오류 메시지]"

### HomeFragment
- **상태 표시 위치**: 헤더 아래
- **기능**: 연결 끊김 시 모든 통계를 "-"로 표시

### BattlesFragment
- **상태 표시 위치**: 헤더 아래
- **기능**: 연결 끊김 시 모든 통계를 "-"로 표시하고 게임 목록 초기화

### TrainingFragment
- **상태 표시 위치**: 헤더 아래
- **기능**: 연결 끊김 시 모든 통계를 "-"로 표시하고 에피소드 목록 초기화

### BotConfigFragment
- **상태 표시 위치**: 헤더 아래
- **기능**: 연결 끊김 시 설정 목록 초기화

### ArenaFragment
- **상태 표시 위치**: 헤더 아래
- **기능**: 연결 끊김 시 모든 통계를 "-"로 표시하고 경기 목록 초기화

---

## ? 기술적 구현

### 예외 처리

```kotlin
try {
    // API 호출
    val data = apiClient.getData()
    // 데이터 표시
} catch (e: java.net.ConnectException) {
    // 서버 연결 실패
    showServerDisconnected("서버에 연결할 수 없습니다")
} catch (e: java.net.SocketTimeoutException) {
    // 타임아웃
    showServerDisconnected("서버 응답 시간 초과")
} catch (e: Exception) {
    // 기타 오류
    showServerDisconnected("서버 연결 오류: ${e.message}")
}
```

### 상태 표시 함수

```kotlin
private fun showServerDisconnected(message: String) {
    statusText.text = "Server Disconnected: $message"
    statusText.setTextColor(requireContext().getColor(R.color.red))
    statusText.visibility = View.VISIBLE
    
    // 데이터 초기화
    // ...
}
```

---

## ? 레이아웃 구조

모든 Fragment 레이아웃에 다음 구조가 추가되었습니다:

```xml
<!-- Status Indicator -->
<TextView
    android:id="@+id/statusText"
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:text="Connecting..."
    android:textColor="#00ff00"
    android:textSize="14sp"
    android:gravity="center"
    android:padding="8dp"
    android:visibility="gone" />
```

---

## ? 사용자 경험

### 연결 상태 표시
- **연결됨**: 상태 텍스트가 자동으로 숨겨짐 (깔끔한 UI)
- **연결 끊김**: 빨간색 텍스트로 명확하게 표시

### 데이터 초기화
- 연결이 끊기면 모든 데이터가 "-" 또는 빈 목록으로 표시
- 사용자가 오래된 데이터를 보지 않도록 보장

---

## ? 체크리스트

- [x] MonitorFragment - 연결 상태 표시
- [x] HomeFragment - 연결 상태 표시
- [x] BattlesFragment - 연결 상태 표시
- [x] TrainingFragment - 연결 상태 표시
- [x] BotConfigFragment - 연결 상태 표시
- [x] ArenaFragment - 연결 상태 표시
- [x] 모든 레이아웃에 statusText 추가
- [x] 예외 처리 (ConnectException, SocketTimeoutException)
- [x] 데이터 초기화 로직

---

**마지막 업데이트**: 2026-01-14
