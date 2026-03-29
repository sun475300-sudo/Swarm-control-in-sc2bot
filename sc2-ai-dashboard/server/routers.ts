import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, protectedProcedure, router } from "./_core/trpc";
import { z } from "zod";
import * as db from "./db";
import * as fs from "fs";
import * as path from "path";

// ★ Phase 43: 실시간 로그/버그 추적 — appRouter보다 먼저 정의 ★
const LOG_PATHS_EARLY = [
  path.join(process.cwd(), "..", "wicked_zerg_challenger", "logs", "bot.log"),
  path.join(process.cwd(), "..", "logs", "bot.log"),
  path.join(process.cwd(), "logs", "bot.log"),
];
function findLogFileEarly(): string | null {
  for (const p of LOG_PATHS_EARLY) {
    if (fs.existsSync(p)) return p;
  }
  return null;
}
interface LogEntry {
  timestamp: string;
  level: "ERROR" | "WARNING" | "INFO" | "DEBUG";
  source: string;
  message: string;
  line: number;
}
function parseLogLine(raw: string, lineNum: number): LogEntry | null {
  const m = raw.match(/^(\d{2}:\d{2}:\d{2})\s+-\s+([\w]+)\s+-\s+(ERROR|WARNING|INFO|DEBUG)\s+-\s+(.+)$/);
  if (!m) return null;
  return { timestamp: m[1], level: m[3] as LogEntry["level"], source: m[2], message: m[4].trim(), line: lineNum };
}
const logsRouter = router({
  getRecentErrors: publicProcedure
    .input(z.object({ limit: z.number().min(1).max(200).default(50), level: z.enum(["ERROR", "WARNING", "ALL"]).default("ALL") }))
    .query(({ input }) => {
      const logPath = findLogFileEarly();
      if (!logPath) return { entries: [], logPath: null, error: "로그 파일 없음", errorCount: 0, warnCount: 0, totalLines: 0 };
      try {
        const lines = fs.readFileSync(logPath, "utf-8").split("\n");
        const all: LogEntry[] = [];
        lines.forEach((l, i) => { const e = parseLogLine(l, i + 1); if (e) all.push(e); });
        const filtered = all.filter(e =>
          input.level === "ALL" ? true :
          input.level === "ERROR" ? e.level === "ERROR" :
          ["ERROR", "WARNING"].includes(e.level)
        );
        return {
          entries: filtered.slice(-input.limit).reverse(),
          logPath,
          totalLines: lines.length,
          errorCount: all.filter(e => e.level === "ERROR").length,
          warnCount: all.filter(e => e.level === "WARNING").length,
          error: null,
        };
      } catch (e) { return { entries: [], logPath, error: String(e), errorCount: 0, warnCount: 0, totalLines: 0 }; }
    }),
  getLogStatus: publicProcedure.query(() => {
    const logPath = findLogFileEarly();
    if (!logPath) return { exists: false, path: null, sizeKb: 0 };
    try { const s = fs.statSync(logPath); return { exists: true, path: logPath, sizeKb: Math.round(s.size / 1024) }; }
    catch { return { exists: false, path: logPath, sizeKb: 0 }; }
  }),
});

const REPLAY_FEEDBACK_PATHS = [
  path.join(process.cwd(), "..", "data", "replay_feedback", "latest_feedback.json"),
  path.join(process.cwd(), "data", "replay_feedback", "latest_feedback.json"),
];

function findReplayFeedbackFile(): string | null {
  for (const p of REPLAY_FEEDBACK_PATHS) {
    if (fs.existsSync(p)) return p;
  }
  return null;
}

const replayRouter = router({
  getLatest: publicProcedure
    .input(z.object({ limit: z.number().min(1).max(50).default(10) }))
    .query(({ input }) => {
      const feedbackPath = findReplayFeedbackFile();
      if (!feedbackPath) {
        return {
          found: false,
          path: null,
          generatedAt: null,
          count: 0,
          items: [] as Array<Record<string, unknown>>,
          error: "replay feedback artifact not found",
        };
      }

      try {
        const raw = JSON.parse(fs.readFileSync(feedbackPath, "utf-8")) as {
          generated_at?: string;
          count?: number;
          items?: Array<Record<string, unknown>>;
        };
        const allItems = Array.isArray(raw.items) ? raw.items : [];
        const sorted = [...allItems].sort((a, b) => {
          const ap = typeof a.priority_score === "number" ? a.priority_score : 0;
          const bp = typeof b.priority_score === "number" ? b.priority_score : 0;
          return bp - ap;
        });

        return {
          found: true,
          path: feedbackPath,
          generatedAt: raw.generated_at ?? null,
          count: typeof raw.count === "number" ? raw.count : allItems.length,
          items: sorted.slice(0, input.limit),
          error: null,
        };
      } catch (e) {
        return {
          found: false,
          path: feedbackPath,
          generatedAt: null,
          count: 0,
          items: [] as Array<Record<string, unknown>>,
          error: String(e),
        };
      }
    }),
});

export const appRouter = router({
  system: systemRouter,
  logs: logsRouter,  // ★ Phase 43: 실시간 로그 추적
  replay: replayRouter,
  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return {
        success: true,
      } as const;
    }),
  }),

  // Game Sessions
  game: router({
    // 현재 진행 중인 게임 세션 가져오기
    getCurrentSession: protectedProcedure.query(async ({ ctx }) => {
      return await db.getLatestGameSession(ctx.user.id);
    }),

    // 게임 세션 목록
    getSessions: protectedProcedure
      .input(z.object({ limit: z.number().optional() }))
      .query(async ({ ctx, input }) => {
        return await db.getGameSessions(ctx.user.id, input.limit);
      }),

    // 게임 세션 생성
    createSession: protectedProcedure
      .input(z.object({
        mapName: z.string(),
        enemyRace: z.enum(["Terran", "Protoss", "Zerg", "Random"]),
        difficulty: z.string(),
      }))
      .mutation(async ({ ctx, input }) => {
        return await db.createGameSession({
          userId: ctx.user.id,
          ...input,
        });
      }),

    // 게임 세션 업데이트
    updateSession: protectedProcedure
      .input(z.object({
        id: z.number(),
        result: z.enum(["Victory", "Defeat", "InProgress"]).optional(),
        gamePhase: z.string().optional(),
        duration: z.number().optional(),
        finalSupply: z.number().optional(),
        finalMinerals: z.number().optional(),
        finalGas: z.number().optional(),
        unitsKilled: z.number().optional(),
        unitsLost: z.number().optional(),
      }))
      .mutation(async ({ input }) => {
        const { id, ...data } = input;
        return await db.updateGameSession(id, data);
      }),

    // 게임 통계
    getStats: protectedProcedure.query(async ({ ctx }) => {
      return await db.getGameStats(ctx.user.id);
    }),
  }),

  // Battles
  battle: router({
    // 세션별 전투 기록
    getBySession: protectedProcedure
      .input(z.object({ sessionId: z.number() }))
      .query(async ({ input }) => {
        return await db.getBattlesBySession(input.sessionId);
      }),

    // 전투 기록 생성
    create: protectedProcedure
      .input(z.object({
        sessionId: z.number(),
        battleTime: z.number(),
        location: z.string().optional(),
        unitsEngaged: z.number().optional(),
        unitsKilled: z.number().optional(),
        unitsLost: z.number().optional(),
        damageDealt: z.number().optional(),
        damageTaken: z.number().optional(),
        result: z.enum(["Win", "Loss", "Retreat"]),
      }))
      .mutation(async ({ input }) => {
        return await db.createBattle(input);
      }),
  }),

  // Training Episodes
  training: router({
    // 학습 에피소드 목록
    getEpisodes: protectedProcedure
      .input(z.object({ limit: z.number().optional() }))
      .query(async ({ ctx, input }) => {
        return await db.getTrainingEpisodes(ctx.user.id, input.limit);
      }),

    // 학습 통계
    getStats: protectedProcedure.query(async ({ ctx }) => {
      return await db.getTrainingStats(ctx.user.id);
    }),

    // 학습 에피소드 생성
    createEpisode: protectedProcedure
      .input(z.object({
        episodeNumber: z.number(),
        totalReward: z.number(),
        averageReward: z.number().optional(),
        winRate: z.number().optional(),
        gamesPlayed: z.number(),
        learningRate: z.number().optional(),
        epsilon: z.number().optional(),
        loss: z.number().optional(),
        notes: z.string().optional(),
      }))
      .mutation(async ({ ctx, input }) => {
        return await db.createTrainingEpisode({
          userId: ctx.user.id,
          ...input,
        });
      }),
  }),

  // Bot Configurations
  bot: router({
    // 봇 설정 목록
    getConfigs: protectedProcedure.query(async ({ ctx }) => {
      return await db.getBotConfigs(ctx.user.id);
    }),

    // 활성 봇 설정
    getActiveConfig: protectedProcedure.query(async ({ ctx }) => {
      return await db.getActiveBotConfig(ctx.user.id);
    }),

    // 봇 설정 생성
    createConfig: protectedProcedure
      .input(z.object({
        name: z.string(),
        strategy: z.enum(["Aggressive", "Defensive", "Balanced", "Economic", "Rush"]),
        buildOrder: z.string().optional(),
        isActive: z.boolean().optional(),
        description: z.string().optional(),
      }))
      .mutation(async ({ ctx, input }) => {
        return await db.createBotConfig({
          userId: ctx.user.id,
          ...input,
        });
      }),

    // 봇 설정 업데이트
    updateConfig: protectedProcedure
      .input(z.object({
        id: z.number(),
        name: z.string().optional(),
        strategy: z.enum(["Aggressive", "Defensive", "Balanced", "Economic", "Rush"]).optional(),
        buildOrder: z.string().optional(),
        isActive: z.boolean().optional(),
        description: z.string().optional(),
      }))
      .mutation(async ({ ctx, input }) => {
        const { id, ...data } = input;
        return await db.updateBotConfig(id, ctx.user.id, data);
      }),

    // 봇 설정 삭제
    deleteConfig: protectedProcedure
      .input(z.object({ id: z.number() }))
      .mutation(async ({ ctx, input }) => {
        return await db.deleteBotConfig(input.id, ctx.user.id);
      }),
  }),

  // AI Arena
  arena: router({
    // 경기 목록
    getMatches: protectedProcedure
      .input(z.object({ limit: z.number().optional() }))
      .query(async ({ ctx, input }) => {
        return await db.getArenaMatches(ctx.user.id, input.limit);
      }),

    // Arena 통계
    getStats: protectedProcedure.query(async ({ ctx }) => {
      return await db.getArenaStats(ctx.user.id);
    }),

    // 경기 기록 생성
    createMatch: protectedProcedure
      .input(z.object({
        matchId: z.string().optional(),
        opponentName: z.string().optional(),
        opponentRace: z.enum(["Terran", "Protoss", "Zerg"]).optional(),
        mapName: z.string().optional(),
        result: z.enum(["Win", "Loss", "Tie"]),
        ranking: z.number().optional(),
        elo: z.number().optional(),
        replayUrl: z.string().optional(),
      }))
      .mutation(async ({ ctx, input }) => {
        return await db.createArenaMatch({
          userId: ctx.user.id,
          ...input,
        });
      }),
  }),
});

export type AppRouter = typeof appRouter;
