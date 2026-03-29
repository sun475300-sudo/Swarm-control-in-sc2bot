import DashboardLayout from "@/components/DashboardLayout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { trpc } from "@/lib/trpc";
import { Activity, AlertCircle, AlertTriangle, Coins, Droplet, FileText, Shield, Swords, Users } from "lucide-react";
import { useEffect, useState } from "react";

export default function Monitor() {
  const { data: currentSession, refetch } = trpc.game.getCurrentSession.useQuery();
  const [logLevel, setLogLevel] = useState<"ALL" | "WARNING" | "ERROR">("WARNING");
  const { data: logData, refetch: refetchLogs } = trpc.logs.getRecentErrors.useQuery(
    { limit: 30, level: logLevel },
    { refetchInterval: 5000 }  // 5초 자동 새로고침
  );
  const { data: replayData, refetch: refetchReplay } = trpc.replay.getLatest.useQuery(
    { limit: 6 },
    { refetchInterval: 15000 }
  );

  // 5초마다 자동 새로고침
  useEffect(() => {
    const interval = setInterval(() => {
      refetch();
      refetchLogs();
      refetchReplay();
    }, 5000);
    return () => clearInterval(interval);
  }, [refetch, refetchLogs, refetchReplay]);

  if (!currentSession) {
    return (
      <DashboardLayout>
        <div className="space-y-8">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight glow-text">
              실시간 모니터링
            </h1>
            <p className="text-muted-foreground text-lg">
              현재 진행 중인 게임이 없습니다
            </p>
          </div>

          <Card className="glass-card">
            <CardHeader>
              <CardTitle>게임 시작 대기 중</CardTitle>
              <CardDescription>
                새로운 게임이 시작되면 여기에 실시간 정보가 표시됩니다
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-center py-12">
                <div className="text-center space-y-4">
                  <Activity className="w-16 h-16 text-muted-foreground mx-auto animate-pulse" />
                  <p className="text-muted-foreground">
                    게임 세션을 시작하면 실시간 모니터링이 활성화됩니다
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    );
  }

  const supplyPercent = currentSession.finalSupply
    ? (currentSession.finalSupply / 200) * 100
    : 0;

  const resourceCards = [
    {
      title: "미네랄",
      value: currentSession.finalMinerals || 0,
      icon: Coins,
      color: "text-blue-400",
      bgColor: "bg-blue-400/10",
    },
    {
      title: "가스",
      value: currentSession.finalGas || 0,
      icon: Droplet,
      color: "text-green-400",
      bgColor: "bg-green-400/10",
    },
    {
      title: "인구수",
      value: `${currentSession.finalSupply || 0}/200`,
      icon: Users,
      color: "text-purple-400",
      bgColor: "bg-purple-400/10",
    },
  ];

  const combatStats = [
    {
      title: "처치한 유닛",
      value: currentSession.unitsKilled || 0,
      icon: Swords,
      color: "text-chart-1",
    },
    {
      title: "잃은 유닛",
      value: currentSession.unitsLost || 0,
      icon: Shield,
      color: "text-chart-2",
    },
  ];

  return (
    <DashboardLayout>
      <div className="space-y-8 animate-slide-up">
        {/* 헤더 */}
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <h1 className="text-4xl font-bold tracking-tight glow-text">
              실시간 모니터링
            </h1>
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-primary/20 border border-primary/30">
              <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
              <span className="text-sm font-medium text-primary">LIVE</span>
            </div>
          </div>
          <p className="text-muted-foreground text-lg">
            현재 게임 상태를 실시간으로 모니터링합니다
          </p>
        </div>

        {/* 게임 정보 */}
        <Card className="glass-card border-primary/20 animate-pulse-glow">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary" />
              게임 정보
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div>
                <p className="text-sm text-muted-foreground mb-1">맵</p>
                <p className="font-semibold text-lg">{currentSession.mapName}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">상대 종족</p>
                <p className="font-semibold text-lg">{currentSession.enemyRace}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">난이도</p>
                <p className="font-semibold text-lg">{currentSession.difficulty}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">게임 단계</p>
                <p className="font-semibold text-lg text-primary">
                  {currentSession.gamePhase || "진행 중"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 자원 현황 */}
        <div>
          <h2 className="text-2xl font-bold mb-4">자원 현황</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {resourceCards.map((resource, index) => {
              const Icon = resource.icon;
              return (
                <Card key={index} className="glass-card hover:glow-effect transition-all">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">
                      {resource.title}
                    </CardTitle>
                    <div className={`p-2 rounded-lg ${resource.bgColor}`}>
                      <Icon className={`w-4 h-4 ${resource.color}`} />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className={`text-3xl font-bold ${resource.color}`}>
                      {resource.value}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>

        {/* 인구수 게이지 */}
        <Card className="glass-card">
          <CardHeader>
            <CardTitle>인구수 사용률</CardTitle>
            <CardDescription>
              현재 {currentSession.finalSupply || 0} / 200 (
              {supplyPercent.toFixed(0)}%)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Progress value={supplyPercent} className="h-4" />
          </CardContent>
        </Card>

        {/* 전투 통계 */}
        <div>
          <h2 className="text-2xl font-bold mb-4">전투 통계</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {combatStats.map((stat, index) => {
              const Icon = stat.icon;
              return (
                <Card key={index} className="glass-card">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Icon className={`w-5 h-5 ${stat.color}`} />
                      {stat.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className={`text-4xl font-bold ${stat.color}`}>
                      {stat.value}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>

        {/* ★ Phase 42: 전투력 비율 분석 위젯 */}
        <Card className="glass-card border-yellow-500/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Swords className="w-5 h-5 text-yellow-400" />
              전투력 비율 분석
            </CardTitle>
            <CardDescription>
              아군 vs 적군 전투력 비교 (HP 가중 공급 기준)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {(() => {
              const ourKDA = currentSession.unitsKilled && currentSession.unitsLost
                ? (currentSession.unitsKilled / Math.max(currentSession.unitsLost, 1))
                : 1;
              const kdaColor = ourKDA >= 1.5 ? "text-green-400" : ourKDA >= 0.8 ? "text-yellow-400" : "text-red-400";
              const kdaLabel = ourKDA >= 1.5 ? "우세" : ourKDA >= 0.8 ? "균형" : "열세";
              const supply = currentSession.finalSupply || 0;
              const killPct = currentSession.unitsKilled
                ? Math.min(100, (currentSession.unitsKilled / Math.max(currentSession.unitsKilled + (currentSession.unitsLost || 0), 1)) * 100)
                : 50;

              return (
                <div className="space-y-4">
                  {/* KDA 뱃지 */}
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">전투 효율 (KDA)</span>
                    <div className="flex items-center gap-2">
                      <span className={`text-2xl font-bold ${kdaColor}`}>
                        {ourKDA.toFixed(2)}
                      </span>
                      <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                        kdaColor === "text-green-400" ? "bg-green-400/20 text-green-400" :
                        kdaColor === "text-yellow-400" ? "bg-yellow-400/20 text-yellow-400" :
                        "bg-red-400/20 text-red-400"
                      }`}>{kdaLabel}</span>
                    </div>
                  </div>

                  {/* 처치/피해 비율 바 */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>처치 비율</span>
                      <span>{killPct.toFixed(0)}%</span>
                    </div>
                    <div className="h-3 rounded-full bg-muted overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          killPct >= 60 ? "bg-green-500" : killPct >= 40 ? "bg-yellow-500" : "bg-red-500"
                        }`}
                        style={{ width: `${killPct}%` }}
                      />
                    </div>
                  </div>

                  {/* 인구수 전투 효율 */}
                  <div className="grid grid-cols-3 gap-3 pt-2 border-t border-border">
                    <div className="text-center">
                      <p className="text-xs text-muted-foreground mb-1">현재 병력</p>
                      <p className="text-lg font-bold text-purple-400">{supply}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-xs text-muted-foreground mb-1">처치</p>
                      <p className="text-lg font-bold text-green-400">
                        {currentSession.unitsKilled || 0}
                      </p>
                    </div>
                    <div className="text-center">
                      <p className="text-xs text-muted-foreground mb-1">손실</p>
                      <p className="text-lg font-bold text-red-400">
                        {currentSession.unitsLost || 0}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })()}
          </CardContent>
        </Card>

        {/* 게임 시간 */}
        {currentSession.duration && (
          <Card className="glass-card">
            <CardHeader>
              <CardTitle>게임 시간</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-primary">
                {Math.floor(currentSession.duration / 60)}분{" "}
                {currentSession.duration % 60}초
              </div>
            </CardContent>
          </Card>
        )}

        {/* ★ Phase 43: 실시간 로그/버그 추적 위젯 */}
        <Card className="glass-card border-red-500/20">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-red-400" />
                실시간 로그 추적
                {logData && (logData.errorCount > 0 || logData.warnCount > 0) && (
                  <span className="ml-2 flex items-center gap-1">
                    {logData.errorCount > 0 && (
                      <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full font-medium">
                        ERR {logData.errorCount}
                      </span>
                    )}
                    {logData.warnCount > 0 && (
                      <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded-full font-medium">
                        WARN {logData.warnCount}
                      </span>
                    )}
                  </span>
                )}
              </CardTitle>
              {/* 레벨 필터 버튼 */}
              <div className="flex gap-1">
                {(["ALL", "WARNING", "ERROR"] as const).map(lvl => (
                  <button
                    key={lvl}
                    onClick={() => setLogLevel(lvl)}
                    className={`text-xs px-2 py-1 rounded font-medium transition-colors ${
                      logLevel === lvl
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground hover:bg-muted/80"
                    }`}
                  >
                    {lvl}
                  </button>
                ))}
              </div>
            </div>
            <CardDescription>
              bot.log 실시간 모니터링 — 5초마다 자동 갱신
              {logData?.totalLines && ` (총 ${logData.totalLines.toLocaleString()}줄)`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {logData?.error ? (
              <div className="flex items-center gap-2 text-muted-foreground py-4">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm">{logData.error}</span>
              </div>
            ) : logData?.entries && logData.entries.length > 0 ? (
              <div className="space-y-1 max-h-64 overflow-y-auto font-mono text-xs">
                {logData.entries.map((entry, i) => (
                  <div
                    key={i}
                    className={`flex items-start gap-2 px-2 py-1 rounded ${
                      entry.level === "ERROR"
                        ? "bg-red-500/10 border-l-2 border-red-500"
                        : entry.level === "WARNING"
                        ? "bg-yellow-500/10 border-l-2 border-yellow-500"
                        : "bg-muted/30"
                    }`}
                  >
                    {entry.level === "ERROR" ? (
                      <AlertCircle className="w-3 h-3 text-red-400 mt-0.5 shrink-0" />
                    ) : entry.level === "WARNING" ? (
                      <AlertTriangle className="w-3 h-3 text-yellow-400 mt-0.5 shrink-0" />
                    ) : (
                      <Activity className="w-3 h-3 text-muted-foreground mt-0.5 shrink-0" />
                    )}
                    <span className={`shrink-0 ${entry.level === "ERROR" ? "text-red-400" : entry.level === "WARNING" ? "text-yellow-400" : "text-muted-foreground"}`}>
                      {entry.timestamp}
                    </span>
                    <span className="text-blue-400 shrink-0">[{entry.source}]</span>
                    <span className="text-foreground/80 break-all">{entry.message}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center py-8 text-muted-foreground">
                <Activity className="w-4 h-4 mr-2 animate-pulse" />
                <span className="text-sm">로그 없음 — 게임 실행 시 자동 표시</span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* ★ Phase 53: 리플레이 피드백 우선순위 위젯 */}
        <Card className="glass-card border-cyan-500/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-cyan-400" />
              Replay Feedback Priority
            </CardTitle>
            <CardDescription>
              Rust 우선순위 점수 기반 학습 대상 리플레이 추천
              {replayData?.generatedAt && ` · ${new Date(replayData.generatedAt).toLocaleTimeString()}`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {replayData?.error ? (
              <div className="flex items-center gap-2 text-muted-foreground py-3">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm">{replayData.error}</span>
              </div>
            ) : replayData?.items && replayData.items.length > 0 ? (
              <div className="space-y-2">
                {replayData.items.map((item, i) => {
                  const fileName = typeof item.file_name === "string" ? item.file_name : "Unknown";
                  const mapName = typeof item.map_name === "string" && item.map_name ? item.map_name : "Unknown";
                  const length = typeof item.game_length === "string" && item.game_length ? item.game_length : "Unknown";
                  const score = typeof item.priority_score === "number" ? item.priority_score : 0;
                  const scoreColor = score >= 2.2 ? "text-green-400" : score >= 1.5 ? "text-yellow-400" : "text-red-400";

                  return (
                    <div
                      key={`${fileName}-${i}`}
                      className="rounded-lg border border-cyan-500/20 bg-cyan-500/5 px-3 py-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-semibold truncate">{fileName}</p>
                        <span className={`text-sm font-bold ${scoreColor}`}>{score.toFixed(3)}</span>
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground flex items-center gap-2">
                        <span>{mapName}</span>
                        <span>•</span>
                        <span>{length}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="flex items-center justify-center py-6 text-muted-foreground">
                <Activity className="w-4 h-4 mr-2 animate-pulse" />
                <span className="text-sm">피드백 데이터 없음 - 스크립트 실행 후 자동 표시</span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
