# Swarm-Net 프레젠테이션 발표 대본 & 시각 자료 가이드

> 총 8장 슬라이드 | 예상 발표 시간: 10~15분

---

## Slide 1: 타이틀 (Title)

### 화면 구성
- **헤드라인:** 하늘의 새로운 질서를 구축하다
- **프로젝트명:** 군집 드론 기반 다이내믹 공역 통제 시스템 (Swarm-Net)
- **서브 카피:** StarCraft II 군단 제어 AI 기반 Sim-to-Real 관제(ATC) 솔루션
- **시각:** 3D 시뮬레이터의 정면 샷 — 군집 드론이 파란색 육각형 결계를 형성한 모습

### 발표 대본 (~30초)
> "안녕하십니까, 군집 드론을 활용한 실시간 동적 공역 통제 시스템, **'Swarm-Net'** 프로젝트의 발표를 시작하겠습니다. 저희는 게임 AI에서 검증된 군집 제어 알고리즘을, **실제 드론 공역 관제 시스템**으로 전이하는 프로젝트를 진행했습니다."

### 전환 큐
→ "먼저, 왜 이 시스템이 필요한지 말씀드리겠습니다."

### AI 이미지 생성 프롬프트 (Midjourney / DALL-E 3)
```
A cinematic wide-angle shot of six autonomous military-grade drones hovering in a perfect hexagonal formation at dusk, connected by glowing cyan laser mesh lines forming a translucent dome-shaped barrier in the sky. Dark navy blue atmosphere with subtle orange sunset glow on the horizon. Each drone emits a soft blue holographic radar pulse. The scene has a cyberpunk aesthetic with volumetric fog, depth of field, and lens flare. Professional tech presentation style, 16:9 aspect ratio, ultra-detailed, 8K resolution. --ar 16:9 --v 6
```

---

## Slide 2: 문제 제기 (Background & Problem)

### 화면 구성
- **핵심 문구:** 고정형 지상 레이더의 사각지대와 혼잡해지는 하늘
- **시각:** 도심 상공에 무분별하게 날아다니는 미확인 드론들 일러스트
- **3가지 한계점:**
  1. 산악/빌딩 지형의 **사각지대** 발생
  2. 특정 지역에 **신속 전개 불가**
  3. 저고도 소형 드론 **탐지 한계**

### 발표 대본 (~1분)
> "드론 배송과 UAM의 시대로 접어들면서 공역은 점차 혼잡해지고 있습니다. 2025년 기준 국내 등록 드론은 **약 90만 대**를 돌파했으며, 산업용 드론 비행은 매년 30% 이상 증가하고 있습니다."
>
> "하지만 기존의 지상 기반 고정형 레이더는 세 가지 근본적 한계가 있습니다. **첫째**, 산악 지형이나 빌딩 숲에서 사각지대가 발생합니다. **둘째**, 긴급 상황에 특정 지역으로 신속하게 관제망을 전개하기 어렵습니다. **셋째**, 저고도에서 운용되는 소형 드론은 기존 레이더의 탐지 범위 밖에 있습니다."

### 전환 큐
→ "그래서 저희는 **발상을 전환**했습니다."

### AI 이미지 생성 프롬프트
```
A dramatic split-view infographic showing the limitations of traditional ground-based radar systems. Left side: a static radar tower on the ground with red dashed lines showing blind spots behind mountains and skyscrapers, small commercial drones flying undetected in gaps. Right side: a chaotic urban sky filled with dozens of delivery drones, survey drones, and recreational drones flying without coordination, some nearly colliding. Dark moody atmosphere with warning red and orange accent colors. Technical diagram style with clean labels, professional presentation aesthetic. --ar 16:9 --v 6
```

---

## Slide 3: 핵심 솔루션 (Our Solution: Swarm-Net)

### 화면 구성
- **핵심 문구:** "드론이 직접 하늘의 관제탑이 되다"
- **시각:** 군집 드론이 하늘로 솟아올라 Mesh Network를 연결하는 인포그래픽
- **핵심 3요소:**
  - Swarm Fleet: 6~12대 다각형 대형
  - Mesh Radar: LiDAR + RF 통신망
  - Timer Control: 체공 시간 자동 관리

### 발표 대본 (~1분)
> "이에 대한 해결책으로, **여러 대의 통제용 군집 드론을 공중에 직접 띄워** 실시간 통신망을 형성하는 방식을 제안합니다."
>
> "이 군집 드론들은 지정된 공역에서 스스로 다각형의 **레이더 결계**를 치고, 내부로 진입하는 모든 민간 드론을 감지하고 통제하는 **'움직이는 관제탑'** 역할을 수행합니다."
>
> "핵심은 세 가지입니다. 6~12대의 드론이 **다각형 대형**을 이루고, 상호 간 LiDAR와 RF 통신으로 **Mesh Radar**를 구축하며, 탐지된 드론에 **체공 시간을 자동 할당**합니다."

### 전환 큐
→ "그렇다면 이 군집 제어 알고리즘은 어디서 온 것일까요?"

### AI 이미지 생성 프롬프트
```
A futuristic concept illustration of six autonomous drones ascending from a mobile command vehicle into the sky, forming an expanding hexagonal mesh network. Bright cyan holographic connection lines link each drone to its neighbors, creating a translucent protective dome over a designated airspace zone. Inside the dome, small civilian drones are visible with green status indicators. The scene is viewed from a dramatic low angle with a dark blue gradient sky, subtle grid lines on the ground below, and glowing HUD-style labels. Clean, professional infographic style suitable for a tech presentation. --ar 16:9 --v 6
```

---

## Slide 4: 핵심 기술 — Sim-to-Real

### 화면 구성
- **핵심 문구:** 가상의 강화학습 알고리즘을 현실의 드론 공역 관제로 이식하다
- **시각:** 좌우 분할 비교
  - [좌] SC2 저그 봇의 군집 이동 화면
  - [우] Swarm-Net 3D 시뮬레이터의 드론 통제 화면
  - [중앙] 화살표 + "Sim → Real" 텍스트
- **기술 전이 테이블:**

| SC2 컴포넌트 | Drone ATC 매핑 | 전이도 |
|---|---|---|
| Boids Algorithm | Formation Flight | ★★★★★ |
| Blackboard | Flight Data Hub | ★★★★★ |
| Authority Mode | ATC Priority | ★★★★★ |
| IntelManager | Sensor Fusion | ★★★★☆ |
| RL Agent | Adaptive AI | ★★★★☆ |

### 발표 대본 (~1분 30초)
> "이 시스템의 핵심은 **'Sim-to-Real'** 기술입니다. 강화학습을 기반으로 수많은 유닛이 자율적으로 진형을 유지하고 의사결정을 내리는 **스타크래프트 2 군단 제어 알고리즘**을, 실제 드론 비행 제어 및 관제 로직으로 이식했습니다."
>
> "게임 속에서 **10,000판 이상의 시뮬레이션**으로 검증된 정교한 군집 이동 로직 — 분리(Separation), 정렬(Alignment), 응집(Cohesion)의 **Boids 알고리즘** — 이 현실의 완벽한 다이내믹 레이더망으로 재탄생한 것입니다."
>
> "SC2의 2D 알고리즘에 **고도(Altitude) 차원만 추가**하면, 드론 편대 비행의 핵심 제어 로직으로 **직접 전이가 가능**합니다."

### 전환 큐
→ "이제 실제 시스템이 어떻게 동작하는지 시뮬레이션으로 보여드리겠습니다."

### AI 이미지 생성 프롬프트
```
A striking side-by-side comparison image for a tech presentation. LEFT SIDE: A top-down view of a StarCraft 2 battle scene with Zerg zergling units moving in a coordinated swarm formation with visible Boids algorithm vectors (separation, alignment, cohesion arrows in cyan). RIGHT SIDE: The same formation pattern but now with real-world autonomous drones flying in 3D hexagonal formation with glowing mesh network connections. CENTER: A large glowing arrow labeled "Sim → Real" bridging both worlds with a digital transformation effect (pixels dissolving into reality). Dark background with blue-to-purple gradient. Professional, cinematic, highly detailed. --ar 16:9 --v 6
```

---

## Slide 5: 시스템 아키텍처 — 3D 라이브 시뮬레이션

### 화면 구성
- **핵심 문구:** 사각지대 없는 3D 입체 스캔 및 실시간 좌표 추적
- **시각:** `swarm_3d_simulator.html` 라이브 데모 또는 화면 녹화
- **4단계 운용 플로우 요약:**
  1. Mesh Network 형성 → 2. 드론 탐지 → 3. 타이머 추적 → 4. 경고/퇴각

### 발표 대본 (~1분 30초)
> "시스템의 **3D 아키텍처 시뮬레이션**입니다. 보시는 것처럼 6대의 군집 드론이 **육각형 대형**을 이루며 공중에 레이더 돔을 형성하고 있습니다."
>
> "결계 내부로 진입한 사용자 드론은 즉각적으로 **고유 ID가 부여**되고, **X, Y, Z 좌표가 실시간**으로 스캔됩니다. 각 드론 머리 위의 라벨에서 **잔여 비행 시간**이 카운트다운되고 있는 것을 확인하실 수 있습니다."
>
> "초록색은 정상, 노란색은 시간 임박, 빨간색으로 깜빡이는 드론은 **시간이 초과**되어 즉시 복귀 명령이 발령된 상태입니다."

### 전환 큐
→ "이 데이터가 관제관에게 어떻게 보이는지, 대시보드를 보여드리겠습니다."

### AI 이미지 생성 프롬프트
```
A detailed 3D isometric view of an airspace control system simulation. Six blue sentinel drones form a hexagonal perimeter at altitude, connected by glowing cyan mesh lines creating a translucent dome. Inside the dome, seven civilian drones fly at various altitudes — three with green holographic timer labels showing "08:32", two with yellow warning labels showing "01:45", and two with red blinking alert labels showing "00:00" with warning triangles. Expanding cyan radar pulse rings emanate from the center of the dome along the ground. Dark navy background with subtle grid, professional 3D render quality, sci-fi command center aesthetic. --ar 16:9 --v 6
```

---

## Slide 6: 실시간 관제 대시보드

### 화면 구성
- **핵심 문구:** 타이머 기반의 자동화된 체공 시간 관리 및 퇴각 통제
- **시각:** `swarm_dashboard.html` 캡처본
  - 좌측 레이더 맵의 펄스 스캔 효과 강조
  - 우측 Fleet Management 리스트의 초록/노랑/빨강 색상 변화
- **강조 포인트:**
  - 🟢 정상 비행 (잔여 > 3분)
  - 🟡 시간 임박 경고 (잔여 < 2분) → 자동 Push 알림
  - 🔴 시간 초과 (0초) → 강제 복귀 명령 + 깜빡임

### 발표 대본 (~1분)
> "레이더망에 감지된 드론은 **실시간 관제 대시보드**에 등록되며, 사전에 허가된 비행시간 타이머가 부여됩니다."
>
> "좌측의 레이더 맵에서는 군집 드론이 육각형 결계를 치고 스캔 파동을 발산하는 모습이 실시간으로 표시됩니다. 우측의 Fleet Management 패널에서는 각 드론의 **잔여 시간과 상태**가 한눈에 파악됩니다."
>
> "관리자의 개입 없이도, 시간이 임박하면 **주황색 주의 알림**이, 제한 시간이 초과되면 즉각적인 **붉은색 경고**와 함께 해당 드론의 조종자에게 **강제 복귀 명령**이 자동으로 푸시 전송됩니다."

### 전환 큐
→ "이 시스템이 실제로 어디에 쓰일 수 있을까요?"

### AI 이미지 생성 프롬프트
```
A sleek futuristic command center dashboard UI screenshot on a dark background (#060a13). Left panel: an SVG hexagonal radar map with six sentinel drone nodes connected by animated cyan mesh lines, radar pulse rings expanding from center, and colored drone icons inside (green, yellow, red). Right panel: a fleet management list showing drone cards with countdown timers — green cards with "08:56" normal status, yellow cards with "01:26" warning status, and red blinking cards with "00:00" expired alert status with warning icons. Top bar shows system stats (SWARM: 6, TRACKED: 7, WARNINGS: 3, ALERTS: 1). Bottom bar shows communication flow animation. Cybernetic dark theme with neon cyan and green accents, JetBrains Mono font. --ar 16:9 --v 6
```

---

## Slide 7: 기대 효과 및 활용 분야

### 화면 구성
- **핵심 문구:** 지형지물에 구애받지 않는 최적의 이동식 관제 및 보안 인프라
- **비교표:**

| 항목 | 기존 방식 | Swarm-Net |
|---|---|---|
| 탐지 범위 | 고정 반경 | 동적 공역 커버 |
| 배치 시간 | 수 개월 설치 | 수 분 내 전개 |
| 비용 | 수억 원 레이더 | Fleet 운영비 |
| 유연성 | 고정 위치 | 실시간 재구성 |
| 확장성 | 기지국 추가 | 드론 추가 투입 |

- **6대 활용 분야** (아이콘 그리드):
  - 군사 야전 작전 | 불법 드론 차단 | 재난 현장 통제
  - 드론 쇼 안전 | UAM 공역 관리 | 농업 방제 구역

### 발표 대본 (~1분)
> "이 시스템은 기존 고정형 레이더 대비 **5가지 핵심 우위**를 가집니다. 특히 배치 시간이 수 개월에서 **수 분으로** 단축되고, 필요에 따라 공역을 **실시간으로 재구성**할 수 있다는 점이 가장 큰 차별점입니다."
>
> "활용 분야는 다양합니다. 고정 기지국 설치가 불가능한 **군사 야전 작전 구역**에서의 신속한 방어망 구축, 주요 시설물의 **불법 드론 접근 차단**, 대형 **드론 쇼에서의 충돌 방지**, 그리고 재난 현장에서의 **긴급 공역 통제**까지 — 기동성과 통신망 운용 효율성을 극대화한 **실전형 솔루션**입니다."

### 전환 큐
→ "마지막으로 이 프로젝트의 미래 비전을 공유드리겠습니다."

### AI 이미지 생성 프롬프트
```
A professional infographic showing six application scenarios for a drone swarm airspace control system, arranged in a 3x2 grid on a dark background. Each cell contains a minimalist isometric illustration: (1) Military field operations with camouflaged drones forming a perimeter, (2) Airport security with drones blocking unauthorized aircraft, (3) Disaster response with emergency drones cordoning off a fire scene, (4) Drone show safety with formation drones creating a safe boundary, (5) Urban air mobility with layered flight corridors, (6) Agricultural zone management with drones over farmland. Each illustration uses cyan, green, and orange accent colors on dark navy backgrounds with subtle glow effects. Clean modern presentation style. --ar 16:9 --v 6
```

---

## Slide 8: 결론 및 Q&A

### 화면 구성
- **헤드라인:** "안전하고 체계적인 하늘의 미래, Swarm-Net이 만들어갑니다"
- **로드맵 타임라인:**
  - Stage 1: SC2 시뮬레이션 (10,000+ 게임 검증) ✅
  - Stage 2: 3D 시뮬레이터 (파라미터 적응) ✅
  - Stage 3: 실 드론 테스트 (5대 편대 비행) 🔜
  - Stage 4: 도시 스케일 ATC (100+ 드론 관제) 🎯
- **시각:** 3D 시뮬레이터 + 대시보드 이미지가 조화롭게 배치된 와이드 이미지
- **"Thank You & Q&A"** 텍스트

### 발표 대본 (~30초)
> "하늘은 이제 단순한 비행 공간을 넘어, **안전하고 효율적으로 관리되어야 할 새로운 인프라**입니다."
>
> "저희는 현재 Stage 2까지 완료했으며, 다음 단계로 **실제 드론 5대를 활용한 편대 비행 테스트**를 준비하고 있습니다. Swarm-Net이 만들어갈 **체계적인 공역의 미래**에 많은 기대 부탁드립니다."
>
> "감사합니다. **질문 받겠습니다.**"

### AI 이미지 생성 프롬프트
```
A grand cinematic conclusion slide image showing a panoramic futuristic cityscape at twilight with multiple drone swarm formations creating overlapping translucent cyan hexagonal dome barriers across the sky at different altitudes. Autonomous delivery drones fly safely through designated corridors between the barriers. A central holographic command interface floats in the foreground showing a miniature version of the monitoring dashboard. The scene conveys order, safety, and technological advancement. Warm orange sunset merging with cool blue technology tones. Text overlay area at top: clean space for "Thank You & Q&A". Ultra-wide cinematic composition, volumetric lighting, highly detailed. --ar 16:9 --v 6
```

---

## 📋 발표 타이밍 가이드

| 슬라이드 | 예상 시간 | 누적 시간 | 비고 |
|---|---|---|---|
| 1. 타이틀 | 0:30 | 0:30 | 인사 + 한줄 소개 |
| 2. 문제 제기 | 1:00 | 1:30 | 공감 유도 |
| 3. 핵심 솔루션 | 1:00 | 2:30 | **핵심 아이디어 전달** |
| 4. Sim-to-Real | 1:30 | 4:00 | 기술적 차별점 |
| 5. 3D 시뮬레이션 | 1:30 | 5:30 | **라이브 데모** |
| 6. 관제 대시보드 | 1:00 | 6:30 | 실용성 어필 |
| 7. 기대 효과 | 1:00 | 7:30 | 비즈니스 가치 |
| 8. 결론 & Q&A | 0:30 | 8:00 | 마무리 |
| Q&A 시간 | 2:00~7:00 | 10~15분 | 자유 질의응답 |

## 💡 발표 팁

1. **Slide 5에서 라이브 데모**: 3D 시뮬레이터를 실제로 브라우저에서 열어 마우스 드래그로 회전하며 보여주면 임팩트 극대화
2. **Slide 6에서 실시간 카운트다운**: 대시보드를 열어 실제 타이머가 줄어드는 것을 보여주면 직관적 이해에 효과적
3. **Slide 4의 비교**: "왼쪽이 게임이고, 오른쪽이 실제 드론입니다. 알고리즘은 동일합니다" — 이 한마디가 핵심
4. **시선 유도**: 빨간 깜빡임이 나오는 순간 "저 드론이 바로 시간 초과된 드론입니다"라고 포인팅