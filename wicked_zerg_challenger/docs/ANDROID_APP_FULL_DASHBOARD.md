# ? Android 앱 전체 대시보드 구현 가이드

**작성일**: 2026-01-14  
**목적**: Android 앱에 Manus 대시보드의 모든 기능 추가

---

## ? 구현 목표

Android 앱에 다음 기능을 추가:

1. **홈** - 메인 대시보드
2. **실시간 모니터링** - 게임 없을 때 "현재 진행중인 게임이 없습니다"
3. **전투분석** - 통계, 승률, 최근 20게임
4. **학습진행** - 에피소드, 보상, 승률
5. **봇설정** - 활성 설정, 빌드오더 관리
6. **AI Arena** - 경기 기록, ELO, 승률 그래프

---

## ? 구현 단계

### 1단계: 데이터 모델 생성 ?

다음 모델 클래스들이 생성되었습니다:

- `BattleStats.kt` - 전투 통계
- `GameRecord.kt` - 게임 기록
- `TrainingStats.kt` - 학습 통계
- `TrainingEpisode.kt` - 학습 에피소드
- `BotConfig.kt` - 봇 설정
- `ArenaStats.kt` - Arena 통계
- `ArenaBotInfo.kt` - Arena 봇 정보
- `ArenaMatch.kt` - Arena 경기

### 2단계: API 클라이언트 확장 ?

`ManusApiClient.kt`가 생성되었습니다:

- `getCurrentGameState()` - 현재 게임 상태 (게임 없으면 null)
- `getBattleStats()` - 전투 통계
- `getRecentGames()` - 최근 20게임
- `getTrainingStats()` - 학습 통계
- `getRecentEpisodes()` - 최근 에피소드
- `getActiveBotConfig()` - 활성 봇 설정
- `getAllBotConfigs()` - 모든 봇 설정
- `getArenaStats()` - Arena 통계
- `getArenaBotInfo()` - Arena 봇 정보
- `getRecentArenaMatches()` - 최근 20경기

### 3단계: UI 구조 변경 (필요)

현재 단일 Activity 구조를 Bottom Navigation으로 변경:

```
MainActivity (Bottom Navigation)
├── HomeFragment (홈)
├── MonitorFragment (실시간 모니터링)
├── BattlesFragment (전투분석)
├── TrainingFragment (학습진행)
├── BotConfigFragment (봇설정)
└── ArenaFragment (AI Arena)
```

### 4단계: 각 Fragment 구현 (필요)

각 페이지별 Fragment와 레이아웃 파일 생성 필요

---

## ?? 구현 방법

### 방법 1: Bottom Navigation 사용 (권장)

**장점**:
- 사용자 친화적
- 각 페이지 간 쉬운 전환
- Material Design 표준

**구현**:
1. `activity_main.xml`을 Bottom Navigation으로 변경
2. 각 페이지를 Fragment로 생성
3. ViewPager2 또는 FragmentContainerView 사용

### 방법 2: TabLayout 사용

**장점**:
- 더 많은 공간 활용
- 스와이프 제스처 지원

---

## ? 각 페이지 상세 구현

### 1. 홈 (HomeFragment)

**기능**:
- 전체 시스템 개요
- 주요 통계 요약 카드
- 빠른 액세스 링크

**레이아웃**:
- 통계 카드 (총 게임수, 승률, 현재 ELO)
- 빠른 링크 버튼

---

### 2. 실시간 모니터링 (MonitorFragment)

**기능**:
- 게임 진행 중: 실시간 게임 상태 표시
- 게임 없음: "현재 진행중인 게임이 없습니다" 메시지

**구현**:
```kotlin
val gameState = manusApiClient.getCurrentGameState()
if (gameState == null) {
    // "현재 진행중인 게임이 없습니다" 표시
    showNoGameMessage()
} else {
    // 게임 상태 표시
    updateGameState(gameState)
}
```

---

### 3. 전투분석 (BattlesFragment)

**기능**:
- 총 게임수, 승리수, 패배수, 승률
- 승률 분석 그래프
- 최근 20게임 목록

**레이아웃**:
- 통계 카드 (총 게임수, 승리, 패배, 승률)
- 승률 그래프 (MPAndroidChart 사용)
- RecyclerView (최근 20게임)

---

### 4. 학습진행 (TrainingFragment)

**기능**:
- 총 에피소드, 평균 보상, 평균 승률, 총 게임수
- 성능 개선 추이 그래프
- 최근 학습 에피소드 목록

**레이아웃**:
- 통계 카드
- 추이 그래프
- RecyclerView (최근 에피소드)

---

### 5. 봇설정 (BotConfigFragment)

**기능**:
- 활성 설정 표시 ("현재 활성설정")
- 빌드오더 설명 표시
- 설정 목록 (생성/편집/삭제)
- 특성 표시

**레이아웃**:
- 활성 설정 카드
- 설정 목록 (RecyclerView)
- FAB (새 설정 생성)

---

### 6. AI Arena (ArenaFragment)

**기능**:
- 총 경기수, 승리, 패배, 현재 ELO
- 승률 그래프 (0.0% 단위 표시)
- 봇 정보 (이름, 종족, 상태)
- 최근 20경기 목록

**레이아웃**:
- 통계 카드
- 승률 그래프 (MPAndroidChart)
- 봇 정보 카드
- RecyclerView (최근 경기)

---

## ? 필요한 라이브러리

### build.gradle.kts에 추가

```kotlin
dependencies {
    // 기존 의존성...
    
    // Navigation
    implementation("androidx.navigation:navigation-fragment-ktx:2.7.5")
    implementation("androidx.navigation:navigation-ui-ktx:2.7.5")
    
    // Material Design
    implementation("com.google.android.material:material:1.11.0")
    
    // Chart (승률 그래프)
    implementation("com.github.PhilJay:MPAndroidChart:v3.1.0")
    
    // RecyclerView (이미 포함되어 있을 수 있음)
    implementation("androidx.recyclerview:recyclerview:1.3.2")
}
```

---

## ? 데이터 동기화

### 실시간 업데이트

각 Fragment에서:
```kotlin
lifecycleScope.launch {
    while (true) {
        // 데이터 가져오기
        val data = manusApiClient.getData()
        // UI 업데이트
        updateUI(data)
        delay(5000) // 5초마다 업데이트
    }
}
```

---

## ? 다음 단계

1. **UI 구조 변경**
   - Bottom Navigation 추가
   - Fragment 생성

2. **각 Fragment 구현**
   - 레이아웃 XML 파일
   - Fragment 클래스
   - 데이터 바인딩

3. **그래프 라이브러리 통합**
   - MPAndroidChart 추가
   - 승률 그래프 구현

4. **봇 설정 관리 UI**
   - 생성/편집/삭제 다이얼로그
   - 빌드오더 편집기

---

## ? 관련 문서

- **모바일 앱 가이드**: `docs/MANUS_DASHBOARD_REQUIREMENTS.md`
- **API 명세**: `docs/MANUS_DASHBOARD_API_SPEC.md`

---

**마지막 업데이트**: 2026-01-14
