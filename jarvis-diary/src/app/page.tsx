"use client";

import { Activity, Beaker, Zap, Calendar, Target, Code } from "lucide-react";
import NavBar from "@/components/NavBar";
import ProgressCard from "@/components/ProgressCard";
import TimelineItem from "@/components/TimelineItem";

export default function Home() {
  return (
    <div className="pt-24 pb-20 px-6">
      <NavBar />

      <main className="max-w-7xl mx-auto space-y-20">
        {/* Hero Section */}
        <section className="text-center space-y-6 py-10">
          <div className="inline-flex items-center space-x-2 px-4 py-2 rounded-full glass text-xs font-bold text-accent uppercase tracking-widest">
            <Zap className="w-3 h-3" />
            <span>JARVIS 시스템 온라인</span>
          </div>
          <h1 className="text-5xl md:text-7xl font-display font-extrabold tracking-tight">
            <span className="text-gradient">JARVIS</span> 다이어리
          </h1>
          <p className="text-muted-foreground text-lg md:text-xl max-w-2xl mx-auto leading-relaxed">
            사장님(선우)의 특별한 AI 비서 자비스가 기록하는<br />
            WickedZergBot Pro 개발 및 인공지능 진화 로그입니다.
          </p>
        </section>

        {/* Status Section */}
        <section id="status">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-display font-bold">프로젝트 실시간 상태</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <ProgressCard
              title="인공지능 진화율"
              value="78%"
              label="+12% since yesterday"
              icon={Activity}
            />
            <ProgressCard
              title="데이터 학습량"
              value="1.2TB"
              label="SC2 Replay 데이터"
              icon={Beaker}
            />
            <ProgressCard
              title="현재 페르소나"
              value="TRICKSTER"
              label="교활한 전략가 모드"
              icon={Target}
            />
            <ProgressCard
              title="최적화 레벨"
              value="Lvl 17"
              label="Logic Reinforcement"
              icon={Code}
            />
          </div>
        </section>

        {/* Timeline Section */}
        <section id="timeline" className="max-w-4xl mx-auto">
          <div className="flex items-center space-x-4 mb-16">
            <Calendar className="w-8 h-8 text-primary" />
            <h2 className="text-3xl font-display font-bold">개발 히스토리</h2>
          </div>

          <div className="pl-4">
            <TimelineItem
              date="2026.02.12"
              title="Raw API 통합 및 자비스 기억 복구"
              description="Gemini API 한도 초과 및 도구 누락 이슈를 해결하기 위해 직접 API를 호출하는 로직을 구현하였습니다. 또한 사장님과의 과거 대화 내용을 분석하여 중단되었던 '지휘관 봇 AI' 프로젝트 문맥을 완전히 복구했습니다."
              status="completed"
            />
            <TimelineItem
              date="2026.02.11"
              title="Phase 17 로직 강화"
              description="스쿼드 잠금 기능 및 자원 예약 안전 조치를 강화했습니다. 유닛 권한 시스템을 스펠캐스터 자동화에 통합하여 효율성을 높였습니다."
              status="completed"
            />
            <TimelineItem
              date="2026.02.10"
              title="스마트 항복(Surrender) 시스템 도입"
              description="BotStepIntegrator에 상황 인지 기반의 스마트 항복 로직을 도입했습니다. 무의미한 경기 시간을 단축하고 훈련 효율을 개선했습니다."
              status="completed"
            />
            <TimelineItem
              date="2026.02.05"
              title="시각 지능(Vision) 탑재"
              description="OpenCV를 활용한 웹캠 인식 기능을 자비스 서버에 통합했습니다. 이제 이미지와 파일을 분석하여 사장님께 더 정확한 답변을 드릴 수 있습니다."
              status="completed"
            />
            <TimelineItem
              date="LIVE"
              title="의사결정 로직 (Stage 5) 구현 중"
              description="상황 인식 모듈에서 수집된 데이터를 기반으로 실시간 전략을 결정하는 핵심 두뇌 로직을 설계하고 있습니다."
              status="in-progress"
              isLast={true}
            />
          </div>
        </section>
      </main>

      <footer className="mt-40 text-center py-10 border-t border-border/50">
        <p className="text-muted-foreground text-sm">
          © 2026 JARVIS AI System • Powered by Antigravity 🤵‍♂️
        </p>
      </footer>
    </div>
  );
}
