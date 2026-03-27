# Swarm-Net Airspace Manager — 시각화 패키지

## 파일 목록

| 파일 | 설명 | 실행 방법 |
|------|------|-----------|
| `swarm_dashboard.html` | 2D 관제 대시보드 (React + SVG) | 브라우저에서 더블클릭 |
| `swarm_3d_simulator.html` | 3D 시뮬레이터 (Three.js) | 브라우저에서 더블클릭 |
| `PRESENTATION_VISUALS.md` | Mermaid 알고리즘 구조도 | GitHub / VSCode Mermaid Preview |
| `SWARM_NET_PROJECT.md` | 프로젝트 설명서 | 아무 Markdown 뷰어 |

## 실행 요구사항

- **브라우저**: Chrome, Edge, Firefox 최신 버전 (CDN에서 라이브러리 로드)
- **인터넷 연결 필요** (React, Three.js, Tailwind CSS를 CDN으로 로드)
- 별도 설치/빌드 불필요 — HTML 파일을 그대로 더블클릭하면 됩니다

## 주요 기능

### 2D 대시보드 (`swarm_dashboard.html`)
- 육각형 레이더 맵 + 스캔 펄스 애니메이션
- 사용자 드론 실시간 카운트다운 타이머
- 상태별 색상 전환 (초록→노랑→빨강)
- 시간 초과 드론 깜빡임 경고
- 드론 클릭 시 상세 정보 표시

### 3D 시뮬레이터 (`swarm_3d_simulator.html`)
- 3D 공간에서 군집 드론 육각형 대형 비행
- 사용자 드론이 레이더 돔 내부에서 자율 비행
- 드론 머리 위 실시간 타이머 라벨
- 마우스 드래그: 회전 / 스크롤: 줌

### Mermaid 다이어그램 (`PRESENTATION_VISUALS.md`)
- 4-7: 4단계 알고리즘 시퀀스 다이어그램
- 4-8: 통신 흐름도 (Swarm → Server → User)
- 렌더링: [mermaid.live](https://mermaid.live) 또는 GitHub에서 자동 렌더링
