# ? Android 앱 전체 대시보드 구현 가이드

**작성일**: 2026-01-14  
**목적**: Android 앱에 Manus 대시보드의 모든 기능 구현

---

## ? 완료된 작업

### 1. 데이터 모델 생성 ?

다음 모델 클래스들이 생성되었습니다:

- `models/BattleStats.kt` - 전투 통계
- `models/GameRecord.kt` - 게임 기록
- `models/TrainingStats.kt` - 학습 통계
- `models/TrainingEpisode.kt` - 학습 에피소드
- `models/BotConfig.kt` - 봇 설정
- `models/ArenaStats.kt` - Arena 통계
- `models/ArenaBotInfo.kt` - Arena 봇 정보
- `models/ArenaMatch.kt` - Arena 경기

### 2. API 클라이언트 확장 ?

`api/ManusApiClient.kt`가 생성되었습니다:

- 모든 대시보드 기능을 위한 API 메서드 포함

### 3. UI 구조 변경 ?

- `activity_main_with_nav.xml` - Bottom Navigation 레이아웃
- `menu/bottom_navigation_menu.xml` - 네비게이션 메뉴
- `navigation/nav_graph.xml` - 네비게이션 그래프

### 4. MonitorFragment 구현 ?

- 실시간 모니터링 Fragment
- 게임 없을 때 "현재 진행중인 게임이 없습니다" 메시지 표시

---

## ? 다음 단계: 나머지 Fragment 구현

### 1. MainActivity 수정

`MainActivity.kt`를 Bottom Navigation을 사용하도록 수정:

```kotlin
class MainActivity : AppCompatActivity() {
    
    private lateinit var navController: NavController
    private lateinit var bottomNavigation: BottomNavigationView
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main_with_nav)
        
        // Navigation 설정
        val navHostFragment = supportFragmentManager
            .findFragmentById(R.id.nav_host_fragment) as NavHostFragment
        navController = navHostFragment.navController
        
        bottomNavigation = findViewById(R.id.bottom_navigation)
        bottomNavigation.setupWithNavController(navController)
    }
}
```

### 2. 나머지 Fragment 생성

다음 Fragment들을 생성해야 합니다:

1. **HomeFragment** - 홈 화면
2. **BattlesFragment** - 전투분석
3. **TrainingFragment** - 학습진행
4. **BotConfigFragment** - 봇설정
5. **ArenaFragment** - AI Arena

### 3. 레이아웃 파일 생성

각 Fragment에 대한 레이아웃 XML 파일:

- `fragment_home.xml`
- `fragment_battles.xml`
- `fragment_training.xml`
- `fragment_bot_config.xml`
- `fragment_arena.xml`

---

## ? 각 Fragment 상세 구현

### HomeFragment

**기능**:
- 전체 시스템 개요
- 주요 통계 요약 카드
- 빠른 액세스 링크

**레이아웃 요소**:
- 통계 카드 (총 게임수, 승률, 현재 ELO)
- 빠른 링크 버튼

---

### BattlesFragment

**기능**:
- 총 게임수, 승리수, 패배수, 승률
- 승률 분석 그래프
- 최근 20게임 목록 (RecyclerView)

**레이아웃 요소**:
- 통계 카드
- 승률 그래프 (MPAndroidChart)
- RecyclerView (최근 20게임)

---

### TrainingFragment

**기능**:
- 총 에피소드, 평균 보상, 평균 승률, 총 게임수
- 성능 개선 추이 그래프
- 최근 학습 에피소드 목록

**레이아웃 요소**:
- 통계 카드
- 추이 그래프
- RecyclerView (최근 에피소드)

---

### BotConfigFragment

**기능**:
- 활성 설정 표시 ("현재 활성설정")
- 빌드오더 설명 표시
- 설정 목록 (생성/편집/삭제)
- 특성 표시

**레이아웃 요소**:
- 활성 설정 카드
- 설정 목록 (RecyclerView)
- FAB (새 설정 생성)

---

### ArenaFragment

**기능**:
- 총 경기수, 승리, 패배, 현재 ELO
- 승률 그래프 (0.0% 단위 표시)
- 봇 정보 (이름, 종족, 상태)
- 최근 20경기 목록

**레이아웃 요소**:
- 통계 카드
- 승률 그래프 (MPAndroidChart)
- 봇 정보 카드
- RecyclerView (최근 경기)

---

## ? 필요한 추가 작업

### 1. build.gradle.kts 업데이트 ?

Navigation과 Chart 라이브러리가 추가되었습니다.

### 2. MainActivity 수정 (필요)

Bottom Navigation을 사용하도록 변경

### 3. Fragment 구현 (필요)

나머지 5개 Fragment 생성

### 4. 레이아웃 파일 생성 (필요)

각 Fragment의 레이아웃 XML 생성

### 5. RecyclerView Adapter 생성 (필요)

- GameRecordAdapter
- TrainingEpisodeAdapter
- BotConfigAdapter
- ArenaMatchAdapter

---

## ? 참고 자료

- **Android Navigation**: https://developer.android.com/guide/navigation
- **MPAndroidChart**: https://github.com/PhilJay/MPAndroidChart
- **Material Design**: https://material.io/design

---

## ? 체크리스트

### 완료
- [x] 데이터 모델 생성
- [x] API 클라이언트 확장
- [x] UI 구조 변경 (Bottom Navigation)
- [x] MonitorFragment 구현

### 진행 중
- [ ] MainActivity 수정
- [ ] HomeFragment 구현
- [ ] BattlesFragment 구현
- [ ] TrainingFragment 구현
- [ ] BotConfigFragment 구현
- [ ] ArenaFragment 구현

---

**마지막 업데이트**: 2026-01-14
