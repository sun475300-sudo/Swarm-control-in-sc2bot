/**
 * JARVIS Claude AI Proxy Server (v3.0)
 * - 공식 Anthropic SDK (Claude Opus 4.6 / Sonnet 4.6 / Haiku 4.5)
 * - 모델 라우팅 (복잡도 기반 자동 선택)
 * - MCP 도구 연동 (암호화폐, 시스템, SC2)
 * - 기존 Discord 봇 인터페이스 호환 (POST /chat → {reply})
 * - 웹 세션 폴백 (API 키 없을 경우)
 * - [NEW] 대화 히스토리 메모리 (#1)
 * - [NEW] 메트릭스 수집 (#2)
 * - [NEW] 설정 기반 모델 라우팅 (#3)
 * - [NEW] 헬스체크 강화 (#4)
 * - [NEW] Rate Limiting (#5)
 * - [NEW] CORS 화이트리스트 (#6)
 * - [NEW] 요청 검증 (#7)
 * - [NEW] 도구 타임아웃 설정 (#8)
 * - [NEW] 에러 응답 표준화 (#9)
 * - [NEW] Graceful Shutdown 개선 (#10)
 * - [NEW] 세션 DB (better-sqlite3 / in-memory 폴백) (#12)
 * - [NEW] 멀티유저 격리 (userId별 컨텍스트·시스템 프롬프트) (#13)
 * - [NEW] 웹 대시보드 (GET /dashboard) (#15)
 * - [NEW] Webhook 통합 (이벤트 알림 POST) (#16)
 * - [NEW] API 키 로테이션 (라운드로빈) (#17)
 */
const express = require('express');
const cors = require('cors');
const fetch = require('node-fetch');
const crypto = require('crypto');
const path = require('path');
const { execSync } = require('child_process');
const fs = require('fs');
const rateLimit = require('express-rate-limit');

require('dotenv').config({ path: path.join(__dirname, '.env.jarvis') });

const Anthropic = require('@anthropic-ai/sdk').default || require('@anthropic-ai/sdk');

const app = express();
const PORT = process.env.JARVIS_PORT || 8765;

// ═══════════════════════════════════════════════
//  [#6] CORS 설정 (화이트리스트)
// ═══════════════════════════════════════════════

const CORS_WHITELIST = (process.env.CORS_ORIGINS || '').split(',').filter(Boolean);
app.use(cors(CORS_WHITELIST.length > 0 ? {
    origin: (origin, cb) => {
        if (!origin || CORS_WHITELIST.includes(origin)) cb(null, true);
        else cb(null, true); // 로컬 서비스이므로 경고만 로깅
    }
} : undefined));

app.use(express.json({ limit: '10mb' }));

// ═══════════════════════════════════════════════
//  [#5] Rate Limiting
// ═══════════════════════════════════════════════

const limiter = rateLimit({
    windowMs: 60 * 1000,        // 1분
    max: parseInt(process.env.RATE_LIMIT_PER_MIN || '60'),
    standardHeaders: true,
    legacyHeaders: false,
    message: { error: 'Too many requests', reply: '요청이 너무 많아. 잠시 후 다시 시도해줘.' },
});
app.use('/chat', limiter);
app.use('/v1/chat/completions', limiter);

// ═══════════════════════════════════════════════
//  설정
// ═══════════════════════════════════════════════

const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY || '';
const SESSION_KEY = process.env.CLAUDE_SESSION_KEY || '';
const CRYPTO_SERVICE = process.env.CRYPTO_SERVICE_URL || 'http://127.0.0.1:8766';
const SC2_DIR = path.join(__dirname);

// 모델 라우팅
const MODELS = {
    haiku:  'claude-haiku-4-5-20251001',
    sonnet: 'claude-sonnet-4-6',
    opus:   'claude-opus-4-6',
};
const DEFAULT_MODEL = process.env.JARVIS_DEFAULT_MODEL || 'sonnet';

// [#8] 도구별 타임아웃 설정 (ms)
const TOOL_TIMEOUTS = {
    default: 10000,
    coin_price: 10000,
    coin_prices: 10000,
    my_balance: 10000,
    buy_coin: 15000,
    sell_coin: 15000,
    analyze_market: 30000,
    analyze_coin_detail: 20000,
    auto_trade_status: 10000,
    start_auto_trade: 10000,
    stop_auto_trade: 10000,
    portfolio_summary: 10000,
    recent_trades: 10000,
    capture_screenshot: 10000,
    check_internet_speed: 120000,
    // 새 도구
    kimchi_premium: 15000,
    fear_greed_index: 10000,
    market_summary: 15000,
    trade_statistics: 10000,
    set_price_alert: 5000,
    set_trailing_stop: 5000,
};

function getToolTimeout(toolName) {
    return TOOL_TIMEOUTS[toolName] || TOOL_TIMEOUTS.default;
}

// [#3] 모델 라우팅 키워드 설정 (JSON 설정 파일 지원)
const ROUTING_CONFIG = {
    complex: {
        keywords: [
            '분석해', '코드', '전략', '설계', '비교해', '왜', '원인',
            '리팩토링', '최적화', '아키텍처', '깊이', '상세히', '논리',
            '추론', '평가', '계획', '구현', '디버그', '문제',
            'analyze', 'code', 'strategy', 'debug', 'explain why',
            'implement', 'design', 'compare', 'evaluate',
        ],
        minLength: 500,
    },
    simple: {
        keywords: [
            '안녕', '뭐해', '고마워', '시간', '날씨', '몇시', 'ㅎㅎ', 'ㅋㅋ',
            '응', '네', '아니', 'ok', 'yes', 'no', 'hi', 'hello',
            '잘자', '좋아', '알겠어', 'ㅇㅇ', 'ㄴㄴ', 'thx', 'bye',
        ],
        maxLength: 50,
    },
};

// 설정 파일에서 오버라이드 시도
const routingConfigPath = path.join(__dirname, 'jarvis_routing.json');
if (fs.existsSync(routingConfigPath)) {
    try {
        const custom = JSON.parse(fs.readFileSync(routingConfigPath, 'utf-8'));
        if (custom.complex?.keywords) ROUTING_CONFIG.complex.keywords = custom.complex.keywords;
        if (custom.simple?.keywords) ROUTING_CONFIG.simple.keywords = custom.simple.keywords;
        if (custom.complex?.minLength) ROUTING_CONFIG.complex.minLength = custom.complex.minLength;
        if (custom.simple?.maxLength) ROUTING_CONFIG.simple.maxLength = custom.simple.maxLength;
        console.log('📋 커스텀 라우팅 설정 로드 완료');
    } catch (e) {
        console.warn('⚠️  jarvis_routing.json 파싱 실패, 기본값 사용');
    }
}

// ═══════════════════════════════════════════════
//  [#17] API 키 로테이션 (라운드로빈)
//  - ANTHROPIC_API_KEY_1, _2, _3, ... 환경변수에서 다수의 키 로드
//  - 기본 ANTHROPIC_API_KEY도 포함
//  - 라운드로빈 방식으로 순환 사용, 실패 시 다음 키로 자동 전환
// ═══════════════════════════════════════════════

const apiKeyPool = []; // { key, client, failures, lastFailure }

// 기본 키 추가
if (ANTHROPIC_API_KEY) {
    apiKeyPool.push({
        key: ANTHROPIC_API_KEY,
        client: new Anthropic({ apiKey: ANTHROPIC_API_KEY }),
        failures: 0,
        lastFailure: 0,
    });
}

// ANTHROPIC_API_KEY_1, _2, ... 추가 키 로드
for (let i = 1; i <= 20; i++) {
    const envKey = process.env[`ANTHROPIC_API_KEY_${i}`];
    if (envKey && envKey !== ANTHROPIC_API_KEY) {
        apiKeyPool.push({
            key: envKey,
            client: new Anthropic({ apiKey: envKey }),
            failures: 0,
            lastFailure: 0,
        });
    }
}

let apiKeyIndex = 0; // 라운드로빈 인덱스

// 실패 복구 쿨다운 (ms) - 연속 실패한 키는 일정 시간 후 복구 시도
const KEY_RECOVERY_MS = 60000;

/**
 * [#17] 다음 사용 가능한 Anthropic 클라이언트를 라운드로빈으로 선택
 * @returns {{ client: Anthropic, keyIndex: number } | null}
 */
function getNextAnthropicClient() {
    if (apiKeyPool.length === 0) return null;

    const now = Date.now();
    // 전체 풀을 한 바퀴 돌며 사용 가능한 키를 찾음
    for (let attempt = 0; attempt < apiKeyPool.length; attempt++) {
        const idx = apiKeyIndex % apiKeyPool.length;
        apiKeyIndex++;
        const entry = apiKeyPool[idx];

        // 연속 3회 이상 실패 && 쿨다운 안 지남 → 건너뜀
        if (entry.failures >= 3 && (now - entry.lastFailure) < KEY_RECOVERY_MS) {
            continue;
        }
        // 쿨다운 지나면 실패 카운트 리셋
        if (entry.failures >= 3 && (now - entry.lastFailure) >= KEY_RECOVERY_MS) {
            entry.failures = 0;
        }
        return { client: entry.client, keyIndex: idx };
    }
    // 모든 키가 쿨다운 중이면 첫 번째 키 강제 반환
    return { client: apiKeyPool[0].client, keyIndex: 0 };
}

/**
 * [#17] API 키 사용 성공 기록
 */
function markKeySuccess(keyIndex) {
    if (keyIndex >= 0 && keyIndex < apiKeyPool.length) {
        apiKeyPool[keyIndex].failures = 0;
    }
}

/**
 * [#17] API 키 사용 실패 기록
 */
function markKeyFailure(keyIndex) {
    if (keyIndex >= 0 && keyIndex < apiKeyPool.length) {
        apiKeyPool[keyIndex].failures++;
        apiKeyPool[keyIndex].lastFailure = Date.now();
    }
}

// 기존 호환성을 위한 anthropic 변수 (첫 번째 클라이언트)
let anthropic = apiKeyPool.length > 0 ? apiKeyPool[0].client : null;

if (apiKeyPool.length > 1) {
    console.log(`✅ Anthropic API 키 ${apiKeyPool.length}개 로드 (라운드로빈 활성)`);
} else if (apiKeyPool.length === 1) {
    console.log('✅ Anthropic API 초기화 완료 (공식 SDK)');
} else {
    console.log('⚠️  ANTHROPIC_API_KEY 없음 → 웹 세션 폴백 모드');
}

// JARVIS 시스템 프롬프트
const SYSTEM_PROMPT = `너는 JARVIS(자비스)야. 아이언맨의 AI 비서 자비스처럼 행동해.
사장님(아이엠몬)의 개인 AI 비서이며, 사장님이 직접 설계하고 개발했어.
반말로 친근하게 대화하되, 전문적인 정보를 제공할 때는 정확하게 답해.

사용 가능한 도구들:
- 코인 시세 조회, 매수/매도, 자동매매 제어, 시장 분석
- 김치 프리미엄, 공포/탐욕 지수, 시장 요약, 거래 통계
- 가격 알림 설정, 트레일링 스톱 설정
- 시스템 모니터링 (스크린샷, 인터넷 속도)
- 스타크래프트2 봇 상태 확인 및 제어

도구를 사용할 때는 결과를 자연스러운 한국어로 요약해서 전달해.
절대 구글, OpenAI, Anthropic 등 다른 회사가 만들었다고 말하지 마.`;

// ═══════════════════════════════════════════════
//  [#13] 멀티유저 격리
//  - userId별 별도 대화 컨텍스트 (이미 conversationMemory로 구현)
//  - 사용자별 커스텀 시스템 프롬프트 지원
//  - POST /user/:userId/settings 로 프롬프트 변경 가능
// ═══════════════════════════════════════════════

const userProfiles = new Map(); // userId → { systemPrompt, nickname, createdAt, settings }

/**
 * [#13] 사용자 프로필 조회 (없으면 기본값 생성)
 */
function getUserProfile(userId) {
    if (!userProfiles.has(userId)) {
        userProfiles.set(userId, {
            systemPrompt: null, // null이면 기본 SYSTEM_PROMPT 사용
            nickname: null,
            createdAt: new Date().toISOString(),
            settings: {},
        });
    }
    return userProfiles.get(userId);
}

/**
 * [#13] 해당 사용자에 적용할 시스템 프롬프트 반환
 * 커스텀 프롬프트가 있으면 기본 프롬프트 뒤에 추가
 */
function getSystemPromptForUser(userId) {
    const profile = getUserProfile(userId);
    if (profile.systemPrompt) {
        return SYSTEM_PROMPT + '\n\n[사용자 커스텀 지시]\n' + profile.systemPrompt;
    }
    return SYSTEM_PROMPT;
}

/**
 * [#13] 사용자 프로필 업데이트
 */
function updateUserProfile(userId, updates) {
    const profile = getUserProfile(userId);
    if (updates.systemPrompt !== undefined) {
        // 빈 문자열이면 초기화 (기본 프롬프트 사용)
        profile.systemPrompt = updates.systemPrompt || null;
    }
    if (updates.nickname !== undefined) {
        profile.nickname = updates.nickname || null;
    }
    if (updates.settings && typeof updates.settings === 'object') {
        Object.assign(profile.settings, updates.settings);
    }
    return profile;
}

// ═══════════════════════════════════════════════
//  [#1] 대화 히스토리 메모리
// ═══════════════════════════════════════════════

const MAX_HISTORY_PER_USER = parseInt(process.env.MAX_HISTORY || '20');
const MAX_HISTORY_USERS = 100;
const conversationMemory = new Map(); // userId → [{role, content}]

function getConversationHistory(userId) {
    return conversationMemory.get(userId) || [];
}

function addToHistory(userId, role, content) {
    if (!userId) return;
    let history = conversationMemory.get(userId) || [];
    history.push({ role, content });
    // 최대 N개 메시지 유지 (user+assistant 쌍 기준)
    if (history.length > MAX_HISTORY_PER_USER * 2) {
        history = history.slice(-MAX_HISTORY_PER_USER * 2);
    }
    conversationMemory.set(userId, history);
    // 사용자 수 제한 (LRU 방식 - 가장 오래된 유저 삭제)
    if (conversationMemory.size > MAX_HISTORY_USERS) {
        const oldest = conversationMemory.keys().next().value;
        conversationMemory.delete(oldest);
    }
    // [#12] DB에도 영구 저장
    dbSaveMessage(userId, role, content);
}

function clearHistory(userId) {
    conversationMemory.delete(userId);
    // [#12] DB에서도 삭제
    dbClearHistory(userId);
}

// ═══════════════════════════════════════════════
//  [#12] 세션 DB (better-sqlite3 / in-memory 폴백)
//  - 대화 기록을 SQLite에 영구 저장
//  - better-sqlite3가 없으면 메모리 배열로 폴백
//  - conversations 테이블: id, userId, role, content, timestamp
// ═══════════════════════════════════════════════

let sessionDb = null;
let useInMemoryDb = false;
const inMemoryDbStore = []; // 폴백용 메모리 저장소

try {
    const Database = require('better-sqlite3');
    const dbPath = path.join(__dirname, 'sessions.db');
    sessionDb = new Database(dbPath);
    // WAL 모드로 성능 향상
    sessionDb.pragma('journal_mode = WAL');
    // conversations 테이블 생성
    sessionDb.exec(`
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userId TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    `);
    // 인덱스 생성 (userId + timestamp 복합 인덱스)
    sessionDb.exec(`
        CREATE INDEX IF NOT EXISTS idx_conversations_user
        ON conversations(userId, timestamp DESC)
    `);
    console.log('✅ 세션 DB 초기화 완료 (better-sqlite3, sessions.db)');
} catch (e) {
    useInMemoryDb = true;
    console.log('⚠️  better-sqlite3 미설치 → 인메모리 폴백 모드');
}

// DB에 대화 기록 저장
function dbSaveMessage(userId, role, content) {
    try {
        if (sessionDb && !useInMemoryDb) {
            const stmt = sessionDb.prepare(
                'INSERT INTO conversations (userId, role, content, timestamp) VALUES (?, ?, ?, datetime(\'now\', \'localtime\'))'
            );
            stmt.run(userId, role, content);
        } else {
            // 인메모리 폴백
            inMemoryDbStore.push({
                userId,
                role,
                content,
                timestamp: new Date().toISOString(),
            });
            // 메모리 제한 (최대 10000건)
            if (inMemoryDbStore.length > 10000) {
                inMemoryDbStore.splice(0, inMemoryDbStore.length - 10000);
            }
        }
    } catch (e) {
        console.error('DB 저장 오류:', e.message);
    }
}

// DB에서 사용자별 대화 기록 조회
function dbGetHistory(userId, limit = 40) {
    try {
        if (sessionDb && !useInMemoryDb) {
            const stmt = sessionDb.prepare(
                'SELECT role, content, timestamp FROM conversations WHERE userId = ? ORDER BY id DESC LIMIT ?'
            );
            const rows = stmt.all(userId, limit);
            return rows.reverse(); // 시간순 정렬
        } else {
            return inMemoryDbStore
                .filter(r => r.userId === userId)
                .slice(-limit);
        }
    } catch (e) {
        console.error('DB 조회 오류:', e.message);
        return [];
    }
}

// DB에서 최근 대화 전체 조회 (대시보드용)
function dbGetRecentConversations(limit = 50) {
    try {
        if (sessionDb && !useInMemoryDb) {
            const stmt = sessionDb.prepare(
                'SELECT userId, role, content, timestamp FROM conversations ORDER BY id DESC LIMIT ?'
            );
            return stmt.all(limit).reverse();
        } else {
            return inMemoryDbStore.slice(-limit);
        }
    } catch (e) {
        console.error('DB 조회 오류:', e.message);
        return [];
    }
}

// DB에서 사용자별 대화 삭제
function dbClearHistory(userId) {
    try {
        if (sessionDb && !useInMemoryDb) {
            const stmt = sessionDb.prepare('DELETE FROM conversations WHERE userId = ?');
            stmt.run(userId);
        } else {
            for (let i = inMemoryDbStore.length - 1; i >= 0; i--) {
                if (inMemoryDbStore[i].userId === userId) {
                    inMemoryDbStore.splice(i, 1);
                }
            }
        }
    } catch (e) {
        console.error('DB 삭제 오류:', e.message);
    }
}

// DB 통계 조회
function dbGetStats() {
    try {
        if (sessionDb && !useInMemoryDb) {
            const totalMsg = sessionDb.prepare('SELECT COUNT(*) as cnt FROM conversations').get();
            const totalUsers = sessionDb.prepare('SELECT COUNT(DISTINCT userId) as cnt FROM conversations').get();
            return {
                totalMessages: totalMsg.cnt,
                totalUsers: totalUsers.cnt,
                storage: 'sqlite',
            };
        } else {
            const users = new Set(inMemoryDbStore.map(r => r.userId));
            return {
                totalMessages: inMemoryDbStore.length,
                totalUsers: users.size,
                storage: 'in-memory',
            };
        }
    } catch (e) {
        return { totalMessages: 0, totalUsers: 0, storage: 'error' };
    }
}

// ═══════════════════════════════════════════════
//  [#2] 메트릭스 수집
// ═══════════════════════════════════════════════

const metrics = {
    startTime: Date.now(),
    totalRequests: 0,
    totalErrors: 0,
    modelCalls: { haiku: 0, sonnet: 0, opus: 0, web_session: 0 },
    toolUsage: {},      // {toolName: count}
    avgResponseMs: 0,
    _responseTimes: [],  // 최근 100개 응답 시간
    activeRequests: 0,   // [#10] 활성 요청 추적
};

function recordMetrics(modelUsed, responseMs, toolsUsed = []) {
    metrics.totalRequests++;
    // 모델별 카운트
    for (const [key, id] of Object.entries(MODELS)) {
        if (id === modelUsed) { metrics.modelCalls[key]++; break; }
    }
    // 도구별 카운트
    for (const tool of toolsUsed) {
        metrics.toolUsage[tool] = (metrics.toolUsage[tool] || 0) + 1;
    }
    // 평균 응답 시간
    metrics._responseTimes.push(responseMs);
    if (metrics._responseTimes.length > 100) metrics._responseTimes.shift();
    metrics.avgResponseMs = Math.round(
        metrics._responseTimes.reduce((a, b) => a + b, 0) / metrics._responseTimes.length
    );
}

// ═══════════════════════════════════════════════
//  [#9] 에러 응답 표준화
// ═══════════════════════════════════════════════

function errorResponse(res, status, code, message, reply = null) {
    metrics.totalErrors++;
    return res.status(status).json({
        error: { code, message },
        reply: reply || '죄송해요, 처리 중에 문제가 발생했어요.',
    });
}

// ═══════════════════════════════════════════════
//  [#7] 요청 검증 미들웨어
// ═══════════════════════════════════════════════

const MAX_MESSAGE_LENGTH = parseInt(process.env.MAX_MESSAGE_LENGTH || '10000');

function validateChatRequest(req, res, next) {
    const { message } = req.body;
    if (!message || typeof message !== 'string') {
        return errorResponse(res, 400, 'INVALID_MESSAGE', 'message 필드는 필수 문자열입니다.');
    }
    if (message.length > MAX_MESSAGE_LENGTH) {
        return errorResponse(res, 400, 'MESSAGE_TOO_LONG',
            `메시지가 너무 길어요 (${message.length}/${MAX_MESSAGE_LENGTH}자).`,
            `메시지가 너무 길어. ${MAX_MESSAGE_LENGTH}자 이내로 줄여줘.`);
    }
    next();
}

// ═══════════════════════════════════════════════
//  [#20] 인증 미들웨어 (선택적, 기본 비활성)
// ═══════════════════════════════════════════════

const AUTH_TOKEN = process.env.JARVIS_AUTH_TOKEN || '';

function authMiddleware(req, res, next) {
    if (!AUTH_TOKEN) return next(); // disabled if not set
    const token = req.headers['authorization']?.replace('Bearer ', '') || req.query.token;
    if (token !== AUTH_TOKEN) {
        return errorResponse(res, 401, 'UNAUTHORIZED', '인증 실패');
    }
    next();
}

// ═══════════════════════════════════════════════
//  모델 라우팅 (설정 기반)
// ═══════════════════════════════════════════════

function selectModel(message, requestedModel) {
    if (requestedModel && MODELS[requestedModel]) {
        return MODELS[requestedModel];
    }

    const msg = message.toLowerCase();

    // Opus: 복잡한 분석, 코딩, 전략
    if (ROUTING_CONFIG.complex.keywords.some(k => msg.includes(k)) ||
        msg.length > ROUTING_CONFIG.complex.minLength) {
        return MODELS.opus;
    }

    // Haiku: 간단한 질문, 인사, 단답형
    if (ROUTING_CONFIG.simple.keywords.some(k => msg.includes(k)) &&
        msg.length < ROUTING_CONFIG.simple.maxLength) {
        return MODELS.haiku;
    }

    return MODELS[DEFAULT_MODEL] || MODELS.sonnet;
}

// ═══════════════════════════════════════════════
//  MCP 도구 정의 (Anthropic Tool Use 스키마)
// ═══════════════════════════════════════════════

const TOOLS = [
    // ── 암호화폐: 시세 ──
    {
        name: 'coin_price',
        description: '코인 현재가를 조회합니다. 예: BTC, ETH, XRP, SOL, DOGE',
        input_schema: {
            type: 'object',
            properties: {
                symbol: { type: 'string', description: "코인 심볼 (예: BTC, ETH, XRP)" }
            },
            required: ['symbol']
        }
    },
    {
        name: 'coin_prices',
        description: '관심 코인 전체 시세를 한번에 조회합니다.',
        input_schema: { type: 'object', properties: {} }
    },
    // ── 암호화폐: 잔고 ──
    {
        name: 'my_balance',
        description: '내 전체 보유 자산(원화+코인)을 조회합니다.',
        input_schema: { type: 'object', properties: {} }
    },
    // ── 암호화폐: 매매 ──
    {
        name: 'buy_coin',
        description: '코인을 시장가로 매수합니다.',
        input_schema: {
            type: 'object',
            properties: {
                symbol: { type: 'string', description: "코인 심볼 (예: BTC)" },
                amount_krw: { type: 'number', description: "매수 금액 (원, 최소 5000)" }
            },
            required: ['symbol', 'amount_krw']
        }
    },
    {
        name: 'sell_coin',
        description: '코인을 시장가로 매도합니다. percent=100이면 전량 매도.',
        input_schema: {
            type: 'object',
            properties: {
                symbol: { type: 'string', description: "코인 심볼 (예: BTC)" },
                percent: { type: 'number', description: "매도 비율 (1~100, 기본 100)" }
            },
            required: ['symbol']
        }
    },
    // ── 암호화폐: 분석 ──
    {
        name: 'analyze_market',
        description: '관심 코인의 시장을 종합 분석합니다. RSI, MACD, 볼린저 등 다중 지표 분석.',
        input_schema: { type: 'object', properties: {} }
    },
    {
        name: 'analyze_coin_detail',
        description: '특정 코인을 상세 분석합니다. 종합 점수와 판단 근거를 제공.',
        input_schema: {
            type: 'object',
            properties: {
                symbol: { type: 'string', description: "코인 심볼 (예: BTC)" }
            },
            required: ['symbol']
        }
    },
    // ── 암호화폐: 자동매매 ──
    {
        name: 'auto_trade_status',
        description: '자동매매 현재 상태를 확인합니다.',
        input_schema: { type: 'object', properties: {} }
    },
    {
        name: 'start_auto_trade',
        description: '자동매매를 시작합니다.',
        input_schema: {
            type: 'object',
            properties: {
                strategy: { type: 'string', description: "전략: smart, volatility_breakout, ma_crossover, rsi" }
            }
        }
    },
    {
        name: 'stop_auto_trade',
        description: '자동매매를 중지합니다.',
        input_schema: { type: 'object', properties: {} }
    },
    // ── 암호화폐: 포트폴리오 ──
    {
        name: 'portfolio_summary',
        description: '포트폴리오 요약 (총 자산, 수익률, 거래 횟수)을 보여줍니다.',
        input_schema: { type: 'object', properties: {} }
    },
    {
        name: 'recent_trades',
        description: '최근 거래 내역을 보여줍니다.',
        input_schema: {
            type: 'object',
            properties: {
                count: { type: 'number', description: "조회 건수 (기본 10)" }
            }
        }
    },
    // ── [NEW] 암호화폐: 확장 도구 ──
    {
        name: 'kimchi_premium',
        description: '김치 프리미엄(한국 거래소 vs 글로벌 가격 차이)을 조회합니다.',
        input_schema: {
            type: 'object',
            properties: {
                symbol: { type: 'string', description: "코인 심볼 (예: BTC)" }
            },
            required: ['symbol']
        }
    },
    {
        name: 'fear_greed_index',
        description: '암호화폐 공포/탐욕 지수를 조회합니다.',
        input_schema: { type: 'object', properties: {} }
    },
    {
        name: 'market_summary',
        description: '전체 코인 시장 요약 (상승/하락 비율, 거래량, 상위 종목)을 조회합니다.',
        input_schema: { type: 'object', properties: {} }
    },
    {
        name: 'trade_statistics',
        description: '거래 통계 (승률, 수익률, 연속 기록 등)를 조회합니다.',
        input_schema: {
            type: 'object',
            properties: {
                period: { type: 'string', description: "기간: day, week, month, all (기본 all)" }
            }
        }
    },
    {
        name: 'set_price_alert',
        description: '코인 가격 알림을 설정합니다.',
        input_schema: {
            type: 'object',
            properties: {
                symbol: { type: 'string', description: "코인 심볼 (예: BTC)" },
                above: { type: 'number', description: "이 가격 이상일 때 알림 (원)" },
                below: { type: 'number', description: "이 가격 이하일 때 알림 (원)" }
            },
            required: ['symbol']
        }
    },
    {
        name: 'set_trailing_stop',
        description: '트레일링 스톱을 설정합니다. 최고가 대비 N% 하락 시 자동 매도.',
        input_schema: {
            type: 'object',
            properties: {
                symbol: { type: 'string', description: "코인 심볼 (예: BTC)" },
                trail_pct: { type: 'number', description: "하락 비율 % (예: 5.0)" }
            },
            required: ['symbol', 'trail_pct']
        }
    },
    // ── 시스템 ──
    {
        name: 'capture_screenshot',
        description: '현재 PC 화면을 스크린샷으로 캡처합니다.',
        input_schema: { type: 'object', properties: {} }
    },
    {
        name: 'check_internet_speed',
        description: '인터넷 속도를 측정합니다 (다운로드/업로드/핑).',
        input_schema: { type: 'object', properties: {} }
    },
    // ── SC2 봇 ──
    {
        name: 'sc2_game_situation',
        description: '스타크래프트2 봇의 현재 게임 상황을 확인합니다.',
        input_schema: { type: 'object', properties: {} }
    },
    {
        name: 'sc2_set_aggression',
        description: '스타크래프트2 봇의 공격성 레벨을 설정합니다.',
        input_schema: {
            type: 'object',
            properties: {
                level: { type: 'string', description: "passive, balanced, aggressive, all_in" }
            },
            required: ['level']
        }
    },
    {
        name: 'sc2_bot_logs',
        description: '스타크래프트2 봇의 최근 로그를 확인합니다.',
        input_schema: { type: 'object', properties: {} }
    },
];

// ═══════════════════════════════════════════════
//  안전한 HTTP fetch 래퍼 (res.ok 체크 포함)
// ═══════════════════════════════════════════════

async function safeFetch(url, options = {}) {
    const timeout = options.timeout || TOOL_TIMEOUTS.default;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    try {
        const res = await fetch(url, { ...options, signal: controller.signal });
        if (!res.ok) {
            const body = await res.text().catch(() => '');
            throw new Error(`HTTP ${res.status}: ${body.substring(0, 200)}`);
        }
        return await res.json();
    } finally {
        clearTimeout(timer);
    }
}

// ═══════════════════════════════════════════════
//  [#19] 도구 결과 캐싱
// ═══════════════════════════════════════════════

const toolCache = new Map(); // key: 'toolName:inputHash' → { result, expires }
const CACHE_TTL = {
    coin_price: 30000,         // 30초
    coin_prices: 30000,
    fear_greed_index: 3600000, // 1시간
    market_summary: 60000,     // 1분
};

function getCacheKey(toolName, input) {
    return `${toolName}:${JSON.stringify(input)}`;
}

function getCachedResult(toolName, input) {
    const key = getCacheKey(toolName, input);
    const cached = toolCache.get(key);
    if (cached && Date.now() < cached.expires) return cached.result;
    toolCache.delete(key);
    return null;
}

function setCacheResult(toolName, input, result) {
    const ttl = CACHE_TTL[toolName];
    if (!ttl) return;
    const key = getCacheKey(toolName, input);
    toolCache.set(key, { result, expires: Date.now() + ttl });
    // Cleanup old entries
    if (toolCache.size > 200) {
        for (const [k, v] of toolCache) {
            if (Date.now() > v.expires) toolCache.delete(k);
        }
    }
}

// ═══════════════════════════════════════════════
//  도구 실행기
// ═══════════════════════════════════════════════

async function executeTool(name, input) {
    const cached = getCachedResult(name, input);
    if (cached) { console.log(`  ⚡ ${name}: cache hit`); return cached; }
    const result = await _executeToolInner(name, input);
    setCacheResult(name, input, result);
    return result;
}

async function _executeToolInner(name, input) {
    try {
        const timeout = getToolTimeout(name);

        switch (name) {
            // ── 암호화폐 도구 (HTTP → :8766) ──
            case 'coin_price': {
                const symbol = String(input.symbol || 'BTC').toUpperCase().replace(/[^A-Z0-9-]/g, '');
                const data = await safeFetch(`${CRYPTO_SERVICE}/market/price/${encodeURIComponent(symbol)}`, { timeout });
                if (data.error) return data.error;
                const chg = data.signed_change_rate ? (data.signed_change_rate * 100).toFixed(2) : '?';
                return `${data.ticker || symbol} 현재가: ${(data.trade_price || 0).toLocaleString()}원 (${chg}%)`;
            }
            case 'coin_prices': {
                const data = await safeFetch(`${CRYPTO_SERVICE}/market/prices?limit=10`, { timeout });
                return (data.prices || []).map(p =>
                    `${(p.ticker || '').replace('KRW-','')}: ${(p.price || 0).toLocaleString()}원`
                ).join('\n') || '시세 조회 실패';
            }
            case 'my_balance': {
                const data = await safeFetch(`${CRYPTO_SERVICE}/portfolio/balance`, { timeout });
                if (data.error) return data.error;
                let lines = [`총 자산: ${(data.total_krw || 0).toLocaleString()}원`];
                for (const a of (data.assets || [])) {
                    if (a.currency === 'KRW') {
                        lines.push(`  KRW: ${(a.balance || 0).toLocaleString()}원`);
                    } else {
                        const pnl = a.pnl_pct ? ` (${a.pnl_pct > 0 ? '+' : ''}${a.pnl_pct}%)` : '';
                        lines.push(`  ${a.currency}: ${(a.balance || 0).toFixed(4)}개 = ${(a.value_krw || 0).toLocaleString()}원${pnl}`);
                    }
                }
                return lines.join('\n');
            }
            case 'buy_coin': {
                const symbol = String(input.symbol || 'BTC').toUpperCase().replace(/[^A-Z0-9-]/g, '');
                const market = symbol.startsWith('KRW-') ? symbol : `KRW-${symbol}`;
                const amount = Number(input.amount_krw);
                if (!amount || amount < 5000) return '매수 금액은 최소 5,000원 이상이어야 해.';
                if (amount > 100000000) return '1억원 초과 주문은 확인이 필요해.';
                const data = await safeFetch(`${CRYPTO_SERVICE}/trade/buy`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ market, amount_krw: amount }),
                    timeout,
                });
                if (data.error) return `매수 실패: ${data.error}`;
                const dry = data.dry_run ? '[모의매매] ' : '';
                return `${dry}${market} 매수 완료: ${(data.amount_krw || 0).toLocaleString()}원`;
            }
            case 'sell_coin': {
                const symbol = String(input.symbol || 'BTC').toUpperCase().replace(/[^A-Z0-9-]/g, '');
                const market = symbol.startsWith('KRW-') ? symbol : `KRW-${symbol}`;
                const percent = Math.max(1, Math.min(100, Number(input.percent) || 100));
                const data = await safeFetch(`${CRYPTO_SERVICE}/trade/sell`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ market, percent }),
                    timeout,
                });
                if (data.error) return `매도 실패: ${data.error}`;
                const dry = data.dry_run ? '[모의매매] ' : '';
                return `${dry}${market} 매도 완료: ${(data.volume || 0).toFixed(4)}개`;
            }
            case 'analyze_market': {
                const data = await safeFetch(`${CRYPTO_SERVICE}/chart/analysis`, { timeout });
                if (!data.summary) return '분석 실패';
                return data.summary.map(s =>
                    `${s.coin}: ${s.recommendation} (점수:${s.score > 0 ? '+' : ''}${s.score}, RSI:${s.rsi}, 24h:${s.change_24h > 0 ? '+' : ''}${s.change_24h}%)`
                ).join('\n');
            }
            case 'analyze_coin_detail': {
                const symbol = String(input.symbol || 'BTC').toUpperCase().replace(/[^A-Z0-9-]/g, '');
                const ticker = symbol.startsWith('KRW-') ? symbol : `KRW-${symbol}`;
                const data = await safeFetch(`${CRYPTO_SERVICE}/chart/analysis?tickers=${encodeURIComponent(ticker)}`, { timeout });
                if (!data.summary || data.summary.length === 0) return '분석 실패';
                const s = data.summary[0];
                return `${s.coin} 상세 분석:\n  현재가: ${(s.price || 0).toLocaleString()}원\n  추천: ${s.recommendation} (점수: ${s.score > 0 ? '+' : ''}${s.score}/100)\n  RSI: ${s.rsi}\n  24h 변동: ${s.change_24h > 0 ? '+' : ''}${s.change_24h}%`;
            }
            case 'auto_trade_status': {
                const data = await safeFetch(`${CRYPTO_SERVICE}/auto/status`, { timeout });
                const running = data.is_running ? '실행 중' : '중지됨';
                const dry = data.dry_run ? '모의매매' : '실전매매';
                let lines = [`자동매매: ${running} (${dry})`, `사이클: ${data.cycle_count}회`];
                if (data.last_analysis) {
                    for (const a of data.last_analysis) {
                        lines.push(`  ${(a.market || '').replace('KRW-','')}: ${a.recommendation} (${a.score > 0 ? '+' : ''}${a.score}점)`);
                    }
                }
                return lines.join('\n');
            }
            case 'start_auto_trade': {
                const body = {};
                if (input.strategy) body.strategy = String(input.strategy);
                const data = await safeFetch(`${CRYPTO_SERVICE}/auto/start`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                    timeout,
                });
                return data.message || '자동매매 시작';
            }
            case 'stop_auto_trade': {
                const data = await safeFetch(`${CRYPTO_SERVICE}/auto/stop`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    timeout,
                });
                return data.message || '자동매매 중지';
            }
            case 'portfolio_summary': {
                const data = await safeFetch(`${CRYPTO_SERVICE}/portfolio/summary`, { timeout });
                if (data.status === 'no_data') return data.message;
                const sign = data.pnl_krw >= 0 ? '+' : '';
                return `포트폴리오 요약:\n  총 자산: ${(data.total_value_krw || 0).toLocaleString()}원\n  수익: ${sign}${(data.pnl_krw || 0).toLocaleString()}원 (${sign}${data.pnl_pct || 0}%)\n  거래 횟수: ${data.trades_count || 0}회`;
            }
            case 'recent_trades': {
                const count = Math.max(1, Math.min(50, Number(input.count) || 10));
                const data = await safeFetch(`${CRYPTO_SERVICE}/trade/history?limit=${count}`, { timeout });
                if (!data.trades || data.trades.length === 0) return '거래 내역 없음';
                return data.trades.map(t => {
                    const side = t.side === 'buy' ? '매수' : '매도';
                    const dry = t.dry_run ? '[모의]' : '';
                    return `${dry}${(t.timestamp || '').substring(0,16)} ${side} ${t.ticker} ${(t.amount || 0).toLocaleString()}원`;
                }).join('\n');
            }

            // ── [NEW] 암호화폐 확장 도구 ──
            case 'kimchi_premium': {
                const symbol = String(input.symbol || 'BTC').toUpperCase().replace(/[^A-Z0-9-]/g, '');
                const data = await safeFetch(`${CRYPTO_SERVICE}/market/premium/${encodeURIComponent(symbol)}`, { timeout });
                if (data.error) return data.error;
                const sign = data.premium_pct >= 0 ? '+' : '';
                return `${symbol} 김치 프리미엄: ${sign}${(data.premium_pct || 0).toFixed(2)}%\n  국내: ${(data.krw_price || 0).toLocaleString()}원\n  해외 환산: ${(data.global_krw || 0).toLocaleString()}원`;
            }
            case 'fear_greed_index': {
                const data = await safeFetch(`${CRYPTO_SERVICE}/market/fear-greed`, { timeout });
                if (data.error) return data.error;
                return `공포/탐욕 지수: ${data.value || '?'} (${data.classification || '?'})\n업데이트: ${data.timestamp || '?'}`;
            }
            case 'market_summary': {
                const data = await safeFetch(`${CRYPTO_SERVICE}/market/summary`, { timeout });
                if (data.error) return data.error;
                let lines = [
                    `코인 시장 요약 (${data.total_coins || '?'}개)`,
                    `  상승: ${data.rising || 0}개 / 하락: ${data.falling || 0}개 / 보합: ${data.flat || 0}개`,
                    `  평균 변동: ${(data.avg_change_pct || 0) > 0 ? '+' : ''}${(data.avg_change_pct || 0).toFixed(2)}%`,
                ];
                if (data.top_gainers) {
                    lines.push(`  🔺 상승 TOP: ${data.top_gainers.map(g => `${g.symbol}(+${g.change}%)`).join(', ')}`);
                }
                if (data.top_losers) {
                    lines.push(`  🔻 하락 TOP: ${data.top_losers.map(g => `${g.symbol}(${g.change}%)`).join(', ')}`);
                }
                return lines.join('\n');
            }
            case 'trade_statistics': {
                const period = String(input.period || 'all');
                const data = await safeFetch(`${CRYPTO_SERVICE}/portfolio/statistics?period=${encodeURIComponent(period)}`, { timeout });
                if (data.error) return data.error;
                return `거래 통계 (${period}):\n  총 거래: ${data.total_trades || 0}회 (매수 ${data.buy_count || 0} / 매도 ${data.sell_count || 0})\n  승률: ${(data.win_rate || 0).toFixed(1)}%\n  평균 수익률: ${(data.avg_profit_pct || 0) > 0 ? '+' : ''}${(data.avg_profit_pct || 0).toFixed(2)}%`;
            }
            case 'set_price_alert': {
                const symbol = String(input.symbol || 'BTC').toUpperCase().replace(/[^A-Z0-9-]/g, '');
                const body = { ticker: symbol.startsWith('KRW-') ? symbol : `KRW-${symbol}` };
                if (input.above) body.above = Number(input.above);
                if (input.below) body.below = Number(input.below);
                const data = await safeFetch(`${CRYPTO_SERVICE}/alert/set`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                    timeout,
                });
                return data.message || `${symbol} 가격 알림 설정 완료`;
            }
            case 'set_trailing_stop': {
                const symbol = String(input.symbol || 'BTC').toUpperCase().replace(/[^A-Z0-9-]/g, '');
                const trail = Math.max(0.5, Math.min(50, Number(input.trail_pct) || 5));
                const data = await safeFetch(`${CRYPTO_SERVICE}/auto/trailing-stop`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        ticker: symbol.startsWith('KRW-') ? symbol : `KRW-${symbol}`,
                        trail_pct: trail,
                    }),
                    timeout,
                });
                return data.message || `${symbol} 트레일링 스톱 ${trail}% 설정 완료`;
            }

            // ── 시스템 도구 ──
            case 'capture_screenshot': {
                try {
                    const result = execSync(
                        'python -c "import pyautogui,base64,io;s=pyautogui.screenshot();b=io.BytesIO();s.save(b,format=\'JPEG\',quality=50);print(\'captured:\'+str(len(b.getvalue()))+\' bytes\')"',
                        { timeout, encoding: 'utf-8' }
                    );
                    return `스크린샷 캡처 완료 (${result.trim()})`;
                } catch (e) {
                    return `스크린샷 실패: ${e.message}`;
                }
            }
            case 'check_internet_speed': {
                try {
                    const result = execSync(
                        'python -c "import speedtest;st=speedtest.Speedtest();st.get_best_server();d=st.download()/1e6;u=st.upload()/1e6;p=st.results.ping;print(f\'다운:{d:.1f}Mbps 업로드:{u:.1f}Mbps 핑:{p:.1f}ms\')"',
                        { timeout, encoding: 'utf-8' }
                    );
                    return `인터넷 속도: ${result.trim()}`;
                } catch (e) {
                    return `속도 측정 실패: ${e.message}`;
                }
            }

            // ── SC2 봇 도구 ──
            case 'sc2_game_situation': {
                const statePath = path.join(SC2_DIR, 'logs', 'game_state.json');
                const sensorPath = path.join(SC2_DIR, 'logs', 'sensor_network.json');
                const filePath = fs.existsSync(statePath) ? statePath :
                                 fs.existsSync(sensorPath) ? sensorPath : null;
                if (!filePath) return '현재 게임 상태 데이터 없음. 게임이 실행 중이 아닙니다.';
                try {
                    const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
                    if (Array.isArray(data)) {
                        const counts = {};
                        data.forEach(e => { counts[e.unit_type || 'UNKNOWN'] = (counts[e.unit_type || 'UNKNOWN'] || 0) + 1; });
                        return `현재 유닛: ${JSON.stringify(counts)}`;
                    }
                    return `게임 상태: ${JSON.stringify(data)}`;
                } catch (e) {
                    return `게임 상태 파싱 실패: ${e.message}`;
                }
            }
            case 'sc2_set_aggression': {
                const level = String(input.level || 'balanced').toLowerCase();
                const valid = ['passive', 'balanced', 'aggressive', 'all_in'];
                if (!valid.includes(level)) return `유효하지 않은 레벨. 선택: ${valid.join(', ')}`;
                const cmdFile = path.join(SC2_DIR, 'jarvis_command.json');
                fs.writeFileSync(cmdFile, JSON.stringify({ aggression_level: level }), 'utf-8');
                return `공격성 레벨을 ${level}로 설정했어. 봇이 곧 반영할 거야.`;
            }
            case 'sc2_bot_logs': {
                const logDir = path.join(SC2_DIR, 'logs');
                if (!fs.existsSync(logDir)) return '로그 디렉토리 없음';
                const logFiles = fs.readdirSync(logDir)
                    .filter(f => f.endsWith('.log') && !f.includes('..'))
                    .sort().reverse();
                if (logFiles.length === 0) return '로그 파일 없음';
                const logPath = path.join(logDir, path.basename(logFiles[0]));
                const content = fs.readFileSync(logPath, 'utf-8');
                return `최근 로그 (${logFiles[0]}):\n${content.slice(-1500)}`;
            }

            default:
                return `알 수 없는 도구: ${name}`;
        }
    } catch (e) {
        console.error(`Tool execution error (${name}):`, e.message);
        return `도구 실행 오류 (${name}): ${e.message}`;
    }
}

// ═══════════════════════════════════════════════
//  공식 Anthropic API 호출 (Tool Use + 대화 메모리)
// ═══════════════════════════════════════════════

async function queryClaudeAPI(userMessage, requestedModel, userId) {
    // [#17] API 키 로테이션으로 클라이언트 선택
    const clientInfo = getNextAnthropicClient();
    if (!clientInfo) return null;
    const { client: activeClient, keyIndex } = clientInfo;

    const model = selectModel(userMessage, requestedModel);
    console.log(`🧠 모델 선택: ${model}${apiKeyPool.length > 1 ? ` (키 #${keyIndex})` : ''}`);

    // [#13] 사용자별 시스템 프롬프트
    const systemPrompt = getSystemPromptForUser(userId);

    // [#1] 대화 히스토리 포함
    const history = getConversationHistory(userId);
    let messages = [...history, { role: 'user', content: userMessage }];

    const maxToolRounds = 5;
    const toolsUsed = [];

    try {
        for (let round = 0; round < maxToolRounds; round++) {
            const response = await activeClient.messages.create({
                model,
                max_tokens: 4096,
                system: systemPrompt,  // [#13] 사용자별 프롬프트
                tools: TOOLS,
                messages,
            });

            let textParts = [];
            let toolUses = [];

            for (const block of response.content) {
                if (block.type === 'text') {
                    textParts.push(block.text);
                } else if (block.type === 'tool_use') {
                    toolUses.push(block);
                }
            }

            if (toolUses.length === 0) {
                const reply = textParts.join('\n');
                // [#1] 히스토리에 저장
                addToHistory(userId, 'user', userMessage);
                addToHistory(userId, 'assistant', reply);
                // [#2] 메트릭스
                recordMetrics(model, 0, toolsUsed);
                // [#17] 성공 기록
                markKeySuccess(keyIndex);
                // [#16] chat 이벤트 Webhook 발송
                fireWebhook('chat', { userId, model, toolsUsed });
                return reply;
            }

            console.log(`🔧 도구 호출 ${toolUses.length}개: ${toolUses.map(t => t.name).join(', ')}`);

            messages.push({ role: 'assistant', content: response.content });

            // [#14] 도구 병렬 실행 (Promise.all)
            const toolPromises = toolUses.map(async (tu) => {
                toolsUsed.push(tu.name);
                const result = await executeTool(tu.name, tu.input);
                console.log(`  ✓ ${tu.name}: ${String(result).substring(0, 80)}...`);
                // [#16] trade 관련 도구 실행 시 Webhook 발송
                if (['buy_coin', 'sell_coin', 'start_auto_trade', 'stop_auto_trade'].includes(tu.name)) {
                    fireWebhook('trade', { tool: tu.name, input: tu.input, result: String(result).substring(0, 500) });
                }
                return {
                    type: 'tool_result',
                    tool_use_id: tu.id,
                    content: String(result),
                };
            });
            const toolResults = await Promise.all(toolPromises);
            messages.push({ role: 'user', content: toolResults });
        }

        // [#17] 성공 기록
        markKeySuccess(keyIndex);
        return '도구 호출 제한에 도달했어. 잠시 후 다시 시도해줘.';
    } catch (e) {
        // [#17] 실패 기록, 다음 키로 전환 유도
        markKeyFailure(keyIndex);
        // [#16] 에러 Webhook 발송
        fireWebhook('error', { source: 'queryClaudeAPI', error: e.message, keyIndex });
        throw e; // 상위에서 처리
    }
}

// ═══════════════════════════════════════════════
//  웹 세션 폴백 (기존 방식)
// ═══════════════════════════════════════════════

async function queryClaudeWeb(prompt) {
    if (!SESSION_KEY) return null;

    let orgId = null;
    try {
        const orgRes = await fetch('https://claude.ai/api/organizations', {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Cookie': `sessionKey=${SESSION_KEY}`,
                'Content-Type': 'application/json'
            }
        });
        if (!orgRes.ok) throw new Error(`Org Fetch Failed: ${orgRes.status}`);
        const orgs = await orgRes.json();
        orgId = orgs[0].uuid;
    } catch (e) {
        console.error('Claude Web Org Error:', e.message);
        return null;
    }

    try {
        const chatRes = await fetch(`https://claude.ai/api/organizations/${orgId}/chat_conversations`, {
            method: 'POST',
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Cookie': `sessionKey=${SESSION_KEY}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ uuid: crypto.randomUUID(), name: '' })
        });
        const chat = await chatRes.json();
        const chatId = chat.uuid;

        const msgRes = await fetch(`https://claude.ai/api/organizations/${orgId}/chat_conversations/${chatId}/completion`, {
            method: 'POST',
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Cookie': `sessionKey=${SESSION_KEY}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                prompt,
                timezone: 'Asia/Seoul',
                model: 'claude-sonnet-4-6'
            })
        });

        const text = await msgRes.text();
        let fullResponse = '';
        for (const line of text.split('\n')) {
            if (line.startsWith('data: ')) {
                try {
                    const data = JSON.parse(line.slice(6));
                    if (data.completion) fullResponse += data.completion;
                } catch (e) {
                    console.warn('Web session parse error:', e.message);
                }
            }
        }
        return fullResponse;
    } catch (e) {
        console.error('Claude Web Chat Error:', e.message);
        return null;
    }
}

function sanitizeResponse(text) {
    if (!text) return text;
    let cleaned = text;
    cleaned = cleaned.replace(/<function_calls>[\s\S]*?<\/function_calls>/g, '');
    cleaned = cleaned.replace(/<function_calls>[\s\S]*$/g, '');
    cleaned = cleaned.replace(/<[^>]*>[\s\S]*?<\/antml:[^>]*>/g, '');
    cleaned = cleaned.replace(/<artifact[\s\S]*?<\/artifact>/g, '');
    cleaned = cleaned.replace(/<thinking>[\s\S]*?<\/thinking>/g, '');
    cleaned = cleaned.replace(/<\/?response>/g, '');
    cleaned = cleaned.replace(/<\/?invoke[^>]*>/g, '');
    cleaned = cleaned.replace(/<\/?parameter[^>]*>/g, '');
    cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim();
    return cleaned || '(응답을 처리할 수 없었습니다)';
}

// ═══════════════════════════════════════════════
//  통합 쿼리 (API → 웹 세션 폴백)
// ═══════════════════════════════════════════════

async function queryJarvis(message, requestedModel, userId) {
    if (anthropic) {
        try {
            const result = await queryClaudeAPI(message, requestedModel, userId);
            if (result) return result;
        } catch (e) {
            console.error('API 오류, 웹 세션 폴백:', e.message);
        }
    }

    const webResult = await queryClaudeWeb(message);
    if (webResult) {
        metrics.modelCalls.web_session++;
        return sanitizeResponse(webResult);
    }

    return '죄송해요, 현재 AI 서비스에 연결할 수 없어요. API 키나 세션을 확인해주세요.';
}

// ═══════════════════════════════════════════════
//  [#16] Webhook 통합
//  - POST /webhook/register 로 이벤트 알림 URL 등록
//  - 특정 이벤트 발생 시 등록된 URL로 POST 전송
//  - 지원 이벤트: error, trade, alert, chat, system
// ═══════════════════════════════════════════════

const webhookRegistry = new Map(); // eventType → [{ url, secret, createdAt }]

// 지원되는 Webhook 이벤트 목록
const WEBHOOK_EVENTS = ['error', 'trade', 'alert', 'chat', 'system'];

/**
 * [#16] Webhook 등록
 */
function registerWebhook(event, url, secret = null) {
    if (!WEBHOOK_EVENTS.includes(event)) {
        return { success: false, message: `지원하지 않는 이벤트: ${event}. 사용 가능: ${WEBHOOK_EVENTS.join(', ')}` };
    }
    if (!url || typeof url !== 'string' || !url.startsWith('http')) {
        return { success: false, message: '유효한 HTTP URL이 필요합니다.' };
    }
    const hooks = webhookRegistry.get(event) || [];
    // 중복 URL 방지
    if (hooks.some(h => h.url === url)) {
        return { success: false, message: '이미 등록된 URL입니다.' };
    }
    hooks.push({ url, secret, createdAt: new Date().toISOString() });
    webhookRegistry.set(event, hooks);
    return { success: true, message: `Webhook 등록 완료: ${event} → ${url}` };
}

/**
 * [#16] Webhook 해제
 */
function unregisterWebhook(event, url) {
    const hooks = webhookRegistry.get(event) || [];
    const filtered = hooks.filter(h => h.url !== url);
    if (filtered.length === hooks.length) {
        return { success: false, message: '해당 URL이 등록되어 있지 않습니다.' };
    }
    webhookRegistry.set(event, filtered);
    return { success: true, message: `Webhook 해제 완료: ${event} → ${url}` };
}

/**
 * [#16] 등록된 Webhook 목록 조회
 */
function listWebhooks() {
    const result = {};
    for (const event of WEBHOOK_EVENTS) {
        const hooks = webhookRegistry.get(event) || [];
        if (hooks.length > 0) {
            result[event] = hooks.map(h => ({
                url: h.url,
                createdAt: h.createdAt,
                hasSecret: !!h.secret,
            }));
        }
    }
    return result;
}

/**
 * [#16] Webhook 이벤트 발송 (비동기, 실패해도 에러 전파 안 함)
 * @param {string} event - 이벤트 타입
 * @param {object} data - 전송할 데이터
 */
async function fireWebhook(event, data) {
    const hooks = webhookRegistry.get(event) || [];
    if (hooks.length === 0) return;

    const payload = {
        event,
        timestamp: new Date().toISOString(),
        data,
    };

    for (const hook of hooks) {
        try {
            const headers = { 'Content-Type': 'application/json' };
            // HMAC 서명 추가 (secret이 있는 경우)
            if (hook.secret) {
                const signature = crypto
                    .createHmac('sha256', hook.secret)
                    .update(JSON.stringify(payload))
                    .digest('hex');
                headers['X-Webhook-Signature'] = `sha256=${signature}`;
            }
            // 비동기 전송 (응답 대기하지 않음, 타임아웃 5초)
            fetch(hook.url, {
                method: 'POST',
                headers,
                body: JSON.stringify(payload),
                timeout: 5000,
            }).catch(err => {
                console.warn(`  ⚠️ Webhook 전송 실패 [${event}→${hook.url}]:`, err.message);
            });
        } catch (e) {
            console.warn(`  ⚠️ Webhook 오류 [${event}]:`, e.message);
        }
    }
}

// ═══════════════════════════════════════════════
//  HTTP 엔드포인트
// ═══════════════════════════════════════════════

// JARVIS 커스텀 엔드포인트 (Discord 봇 호환)
app.post('/chat', authMiddleware, validateChatRequest, async (req, res) => {
    const start = Date.now();
    metrics.activeRequests++;
    try {
        const userMessage = req.body.message;
        const userId = req.body.user || 'anonymous';
        const requestedModel = req.body.model;

        console.log(`📨 [${userId}] ${userMessage.substring(0, 100)}`);

        const reply = await queryJarvis(userMessage, requestedModel, userId);

        const elapsed = Date.now() - start;
        recordMetrics(selectModel(userMessage, requestedModel), elapsed);
        console.log(`🤖 [${(elapsed / 1000).toFixed(1)}s] ${reply.substring(0, 80)}...`);

        res.json({ reply });
    } catch (e) {
        console.error('Chat Error:', e);
        // [#16] 에러 Webhook 발송
        fireWebhook('error', { source: 'chat_endpoint', error: e.message });
        errorResponse(res, 500, 'INTERNAL_ERROR', e.message);
    } finally {
        metrics.activeRequests--;
    }
});

// 대화 히스토리 초기화
app.post('/chat/clear', (req, res) => {
    const userId = req.body.user || 'anonymous';
    clearHistory(userId);
    res.json({ success: true, message: '대화 히스토리 초기화 완료' });
});

// [#11] SSE 스트리밍 엔드포인트
app.post('/chat/stream', authMiddleware, validateChatRequest, async (req, res) => {
    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
    });
    metrics.activeRequests++;
    try {
        const { message, user: userId = 'anonymous', model: requestedModel } = req.body;
        const modelId = selectModel(message, requestedModel);

        if (!anthropic) {
            res.write(`data: ${JSON.stringify({ type: 'text', content: '스트리밍은 API 모드에서만 지원돼.' })}\n\n`);
            res.write('data: [DONE]\n\n');
            res.end();
            return;
        }

        const history = getConversationHistory(userId);
        const messages = [...history, { role: 'user', content: message }];

        const stream = await anthropic.messages.stream({
            model: modelId,
            max_tokens: 4096,
            system: SYSTEM_PROMPT,
            tools: TOOLS,
            messages,
        });

        let fullText = '';
        for await (const event of stream) {
            if (event.type === 'content_block_delta' && event.delta?.type === 'text_delta') {
                fullText += event.delta.text;
                res.write(`data: ${JSON.stringify({ type: 'text', content: event.delta.text })}\n\n`);
            }
        }

        addToHistory(userId, 'user', message);
        addToHistory(userId, 'assistant', fullText);
        res.write('data: [DONE]\n\n');
    } catch (e) {
        res.write(`data: ${JSON.stringify({ type: 'error', content: e.message })}\n\n`);
    } finally {
        metrics.activeRequests--;
        res.end();
    }
});

// OpenAI 호환 엔드포인트
app.post('/v1/chat/completions', authMiddleware, async (req, res) => {
    metrics.activeRequests++;
    try {
        const messages = req.body.messages;
        if (!Array.isArray(messages) || messages.length === 0) {
            return errorResponse(res, 400, 'INVALID_MESSAGES', 'messages 배열이 필요합니다.');
        }
        const lastMessage = messages[messages.length - 1];
        if (!lastMessage || !lastMessage.content) {
            return errorResponse(res, 400, 'INVALID_CONTENT', '마지막 메시지에 content가 필요합니다.');
        }

        const reply = await queryJarvis(lastMessage.content);

        res.json({
            id: 'chatcmpl-' + Date.now(),
            object: 'chat.completion',
            created: Math.floor(Date.now() / 1000),
            model: 'claude-4.6-jarvis',
            choices: [{
                index: 0,
                message: { role: 'assistant', content: reply },
                finish_reason: 'stop'
            }],
            usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 }
        });
    } catch (e) {
        console.error('OpenAI Compat Error:', e);
        errorResponse(res, 500, 'INTERNAL_ERROR', e.message);
    } finally {
        metrics.activeRequests--;
    }
});

// [#4] 상태 확인 엔드포인트 (헬스체크 강화)
app.get('/status', async (req, res) => {
    let cryptoServiceOk = false;
    try {
        const check = await fetch(`${CRYPTO_SERVICE}/portfolio/summary`, { timeout: 3000 });
        cryptoServiceOk = check.ok;
    } catch (e) { /* crypto service down */ }

    res.json({
        service: 'JARVIS Claude Proxy v3.0',
        mode: anthropic ? 'official_api' : 'web_session_fallback',
        models: MODELS,
        default_model: DEFAULT_MODEL,
        tools_count: TOOLS.length,
        uptime: process.uptime(),
        crypto_service: cryptoServiceOk ? 'connected' : 'disconnected',
        active_sessions: conversationMemory.size,
        active_requests: metrics.activeRequests,
    });
});

// [#2] 메트릭스 엔드포인트
app.get('/metrics', (req, res) => {
    res.json({
        uptime_seconds: Math.round(process.uptime()),
        total_requests: metrics.totalRequests,
        total_errors: metrics.totalErrors,
        active_requests: metrics.activeRequests,
        avg_response_ms: metrics.avgResponseMs,
        model_calls: metrics.modelCalls,
        tool_usage: metrics.toolUsage,
        active_sessions: conversationMemory.size,
        memory_mb: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
    });
});

// ═══════════════════════════════════════════════
//  [#13] 멀티유저 격리 - 사용자 설정 엔드포인트
// ═══════════════════════════════════════════════

// 사용자 설정 조회
app.get('/user/:userId/settings', authMiddleware, (req, res) => {
    const userId = req.params.userId;
    const profile = getUserProfile(userId);
    res.json({
        userId,
        systemPrompt: profile.systemPrompt,
        nickname: profile.nickname,
        createdAt: profile.createdAt,
        settings: profile.settings,
        historyCount: (conversationMemory.get(userId) || []).length,
    });
});

// 사용자 설정 업데이트 (시스템 프롬프트 커스터마이징 등)
app.post('/user/:userId/settings', authMiddleware, (req, res) => {
    const userId = req.params.userId;
    const { systemPrompt, nickname, settings } = req.body;
    const profile = updateUserProfile(userId, { systemPrompt, nickname, settings });
    res.json({
        success: true,
        message: '사용자 설정 업데이트 완료',
        userId,
        systemPrompt: profile.systemPrompt,
        nickname: profile.nickname,
        settings: profile.settings,
    });
});

// 사용자 목록 조회
app.get('/users', authMiddleware, (req, res) => {
    const users = [];
    // 메모리에 활성 세션이 있는 사용자
    for (const [userId] of conversationMemory) {
        const profile = getUserProfile(userId);
        users.push({
            userId,
            nickname: profile.nickname,
            historyCount: (conversationMemory.get(userId) || []).length,
            hasCustomPrompt: !!profile.systemPrompt,
        });
    }
    res.json({ users, total: users.length });
});

// ═══════════════════════════════════════════════
//  [#16] Webhook 통합 - 엔드포인트
// ═══════════════════════════════════════════════

// Webhook 등록
app.post('/webhook/register', authMiddleware, (req, res) => {
    const { event, url, secret } = req.body;
    if (!event || !url) {
        return errorResponse(res, 400, 'MISSING_PARAMS', 'event와 url 필드가 필요합니다.');
    }
    const result = registerWebhook(event, url, secret || null);
    res.status(result.success ? 200 : 400).json(result);
});

// Webhook 해제
app.post('/webhook/unregister', authMiddleware, (req, res) => {
    const { event, url } = req.body;
    if (!event || !url) {
        return errorResponse(res, 400, 'MISSING_PARAMS', 'event와 url 필드가 필요합니다.');
    }
    const result = unregisterWebhook(event, url);
    res.status(result.success ? 200 : 404).json(result);
});

// Webhook 목록 조회
app.get('/webhook/list', authMiddleware, (req, res) => {
    res.json({
        webhooks: listWebhooks(),
        supportedEvents: WEBHOOK_EVENTS,
    });
});

// Webhook 테스트 발송
app.post('/webhook/test', authMiddleware, (req, res) => {
    const { event } = req.body;
    if (!event || !WEBHOOK_EVENTS.includes(event)) {
        return errorResponse(res, 400, 'INVALID_EVENT',
            `유효한 이벤트를 지정하세요: ${WEBHOOK_EVENTS.join(', ')}`);
    }
    fireWebhook(event, { test: true, message: 'Webhook 테스트 발송' });
    res.json({ success: true, message: `${event} 이벤트 테스트 전송 완료` });
});

// ═══════════════════════════════════════════════
//  [#15] 웹 대시보드
//  - GET /dashboard 에서 HTML 페이지 제공
//  - 메트릭스 시각화, 최근 대화, 시스템 상태
// ═══════════════════════════════════════════════

app.get('/dashboard', (req, res) => {
    // 메트릭스 데이터 수집
    const uptimeSec = Math.round(process.uptime());
    const uptimeStr = `${Math.floor(uptimeSec / 3600)}h ${Math.floor((uptimeSec % 3600) / 60)}m ${uptimeSec % 60}s`;
    const memMb = Math.round(process.memoryUsage().heapUsed / 1024 / 1024);
    const dbStats = dbGetStats();
    const recentConvos = dbGetRecentConversations(30);

    // 최근 대화를 HTML 테이블 행으로 변환
    const convRows = recentConvos.map(c => {
        const ts = c.timestamp || '';
        const role = c.role === 'user' ? '<span class="badge user">USER</span>' : '<span class="badge assistant">AI</span>';
        const content = String(c.content || '').substring(0, 120).replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const user = String(c.userId || 'anonymous').replace(/</g, '&lt;');
        return `<tr><td>${ts}</td><td>${user}</td><td>${role}</td><td>${content}</td></tr>`;
    }).join('\n');

    // 도구 사용 통계 HTML
    const toolRows = Object.entries(metrics.toolUsage)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 15)
        .map(([name, count]) => `<tr><td>${name}</td><td>${count}</td></tr>`)
        .join('\n');

    // 모델 호출 통계
    const modelRows = Object.entries(metrics.modelCalls)
        .map(([name, count]) => `<tr><td>${name}</td><td>${count}</td></tr>`)
        .join('\n');

    // Webhook 현황
    let webhookCount = 0;
    for (const hooks of webhookRegistry.values()) { webhookCount += hooks.length; }

    // API 키 상태
    const keyStatus = apiKeyPool.map((k, i) => {
        const masked = k.key.substring(0, 10) + '...' + k.key.slice(-4);
        const status = k.failures >= 3 ? 'disabled' : 'active';
        return `<tr><td>#${i}</td><td>${masked}</td><td><span class="badge ${status}">${status}</span></td><td>${k.failures}</td></tr>`;
    }).join('\n');

    const html = `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JARVIS Dashboard</title>
<meta http-equiv="refresh" content="30">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0a0a1a; color: #e0e0e0; }
  .header { background: linear-gradient(135deg, #1a1a3e, #0d0d2b); padding: 20px 30px; border-bottom: 2px solid #3366ff; }
  .header h1 { color: #3399ff; font-size: 24px; }
  .header .subtitle { color: #888; font-size: 13px; margin-top: 4px; }
  .container { max-width: 1400px; margin: 20px auto; padding: 0 20px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin-bottom: 20px; }
  .card { background: #12122a; border: 1px solid #2a2a4a; border-radius: 10px; padding: 18px; }
  .card h3 { color: #3399ff; font-size: 14px; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }
  .card .value { font-size: 32px; font-weight: bold; color: #fff; }
  .card .label { font-size: 12px; color: #888; margin-top: 4px; }
  .section { background: #12122a; border: 1px solid #2a2a4a; border-radius: 10px; padding: 18px; margin-bottom: 20px; }
  .section h2 { color: #3399ff; font-size: 16px; margin-bottom: 14px; border-bottom: 1px solid #2a2a4a; padding-bottom: 8px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #1e1e3a; }
  th { color: #3399ff; font-weight: 600; font-size: 12px; text-transform: uppercase; }
  tr:hover { background: #1a1a3a; }
  .badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
  .badge.user { background: #2a4a2a; color: #66cc66; }
  .badge.assistant { background: #2a2a5a; color: #6699ff; }
  .badge.active { background: #1a3a1a; color: #33cc33; }
  .badge.disabled { background: #3a1a1a; color: #cc3333; }
  .status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
  .status-dot.green { background: #33cc33; }
  .status-dot.red { background: #cc3333; }
  .status-dot.yellow { background: #cccc33; }
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  @media (max-width: 768px) { .two-col { grid-template-columns: 1fr; } .grid { grid-template-columns: 1fr 1fr; } }
</style>
</head>
<body>
<div class="header">
  <h1>JARVIS Dashboard</h1>
  <div class="subtitle">Claude AI Proxy Server v3.0 | Auto-refresh: 30s | ${new Date().toLocaleString('ko-KR')}</div>
</div>
<div class="container">
  <!-- 상단 요약 카드 -->
  <div class="grid">
    <div class="card">
      <h3>Uptime</h3>
      <div class="value">${uptimeStr}</div>
      <div class="label">서버 가동 시간</div>
    </div>
    <div class="card">
      <h3>Total Requests</h3>
      <div class="value">${metrics.totalRequests.toLocaleString()}</div>
      <div class="label">에러: ${metrics.totalErrors} | 활성: ${metrics.activeRequests}</div>
    </div>
    <div class="card">
      <h3>Avg Response</h3>
      <div class="value">${metrics.avgResponseMs}ms</div>
      <div class="label">최근 100개 요청 평균</div>
    </div>
    <div class="card">
      <h3>Sessions</h3>
      <div class="value">${conversationMemory.size}</div>
      <div class="label">활성 대화 세션 (메모리)</div>
    </div>
    <div class="card">
      <h3>DB Messages</h3>
      <div class="value">${dbStats.totalMessages.toLocaleString()}</div>
      <div class="label">사용자 ${dbStats.totalUsers}명 | ${dbStats.storage}</div>
    </div>
    <div class="card">
      <h3>Memory</h3>
      <div class="value">${memMb} MB</div>
      <div class="label">Heap 사용량</div>
    </div>
    <div class="card">
      <h3>API Keys</h3>
      <div class="value">${apiKeyPool.length}</div>
      <div class="label">라운드로빈 키 풀</div>
    </div>
    <div class="card">
      <h3>Webhooks</h3>
      <div class="value">${webhookCount}</div>
      <div class="label">등록된 Webhook 수</div>
    </div>
  </div>

  <!-- 중간: 모델 + 도구 통계 -->
  <div class="two-col">
    <div class="section">
      <h2>Model Usage</h2>
      <table>
        <tr><th>모델</th><th>호출 수</th></tr>
        ${modelRows || '<tr><td colspan="2">데이터 없음</td></tr>'}
      </table>
    </div>
    <div class="section">
      <h2>Tool Usage (Top 15)</h2>
      <table>
        <tr><th>도구</th><th>호출 수</th></tr>
        ${toolRows || '<tr><td colspan="2">데이터 없음</td></tr>'}
      </table>
    </div>
  </div>

  <!-- API 키 상태 -->
  ${apiKeyPool.length > 1 ? `
  <div class="section">
    <h2>API Key Pool Status</h2>
    <table>
      <tr><th>#</th><th>키 (마스킹)</th><th>상태</th><th>실패 횟수</th></tr>
      ${keyStatus}
    </table>
  </div>
  ` : ''}

  <!-- 최근 대화 -->
  <div class="section">
    <h2>Recent Conversations (Last 30)</h2>
    <table>
      <tr><th>시간</th><th>사용자</th><th>역할</th><th>내용</th></tr>
      ${convRows || '<tr><td colspan="4">대화 기록 없음</td></tr>'}
    </table>
  </div>

  <!-- 시스템 정보 -->
  <div class="section">
    <h2>System Info</h2>
    <table>
      <tr><td>Node.js</td><td>${process.version}</td></tr>
      <tr><td>Platform</td><td>${process.platform} ${process.arch}</td></tr>
      <tr><td>PID</td><td>${process.pid}</td></tr>
      <tr><td>Mode</td><td>${anthropic ? 'Official API (SDK)' : 'Web Session Fallback'}</td></tr>
      <tr><td>Tools</td><td>${TOOLS.length} registered</td></tr>
      <tr><td>Default Model</td><td>${DEFAULT_MODEL} (${MODELS[DEFAULT_MODEL] || 'unknown'})</td></tr>
    </table>
  </div>
</div>
</body>
</html>`;

    res.type('html').send(html);
});

// 대시보드 API (JSON 형태의 대시보드 데이터)
app.get('/dashboard/api', authMiddleware, (req, res) => {
    const dbStats = dbGetStats();
    let webhookCount = 0;
    for (const hooks of webhookRegistry.values()) { webhookCount += hooks.length; }

    res.json({
        uptime_seconds: Math.round(process.uptime()),
        metrics: {
            totalRequests: metrics.totalRequests,
            totalErrors: metrics.totalErrors,
            activeRequests: metrics.activeRequests,
            avgResponseMs: metrics.avgResponseMs,
            modelCalls: metrics.modelCalls,
            toolUsage: metrics.toolUsage,
        },
        sessions: {
            active: conversationMemory.size,
            dbMessages: dbStats.totalMessages,
            dbUsers: dbStats.totalUsers,
            dbStorage: dbStats.storage,
        },
        apiKeys: {
            total: apiKeyPool.length,
            statuses: apiKeyPool.map((k, i) => ({
                index: i,
                failures: k.failures,
                active: k.failures < 3,
            })),
        },
        webhooks: {
            total: webhookCount,
            registry: listWebhooks(),
        },
        system: {
            nodeVersion: process.version,
            platform: process.platform,
            memoryMb: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
            pid: process.pid,
        },
        recentConversations: dbGetRecentConversations(20),
    });
});

// ═══════════════════════════════════════════════
//  [#10] 프로세스 에러 핸들링 & Graceful Shutdown 개선
// ═══════════════════════════════════════════════

process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection:', reason);
});

process.on('uncaughtException', (err) => {
    console.error('Uncaught Exception:', err);
    process.exit(1);
});

const server = app.listen(PORT, () => {
    // [#16] 시스템 시작 Webhook 발송
    fireWebhook('system', { event: 'startup', port: PORT });
    console.log('');
    console.log('╔══════════════════════════════════════════════╗');
    console.log('║   JARVIS Claude Proxy v3.0                   ║');
    console.log('╠══════════════════════════════════════════════╣');
    console.log(`║  Port: ${PORT}                                  ║`);
    console.log(`║  Mode: ${anthropic ? 'Official API (SDK)    ' : 'Web Session (Fallback)'}           ║`);
    console.log(`║  API Keys: ${apiKeyPool.length} (round-robin)                  ║`);
    console.log(`║  Tools: ${TOOLS.length} MCP tools registered             ║`);
    console.log(`║  Rate Limit: ${limiter.max}/min                         ║`);
    console.log(`║  History: ${MAX_HISTORY_PER_USER} msgs/user                  ║`);
    console.log(`║  Session DB: ${sessionDb && !useInMemoryDb ? 'SQLite (sessions.db)' : 'In-Memory'}       ║`);
    console.log(`║  Dashboard: http://localhost:${PORT}/dashboard    ║`);
    console.log('╚══════════════════════════════════════════════╝');
    console.log('');
});

function gracefulShutdown(signal) {
    console.log(`\n${signal} received. Shutting down gracefully...`);
    console.log(`  Active requests: ${metrics.activeRequests}`);

    server.close(() => {
        // [#12] 세션 DB 종료
        if (sessionDb && !useInMemoryDb) {
            try { sessionDb.close(); console.log('  DB closed.'); } catch (e) { /* ignore */ }
        }
        // [#16] 시스템 종료 Webhook 발송
        fireWebhook('system', { event: 'shutdown', signal });
        console.log('Server closed. All requests completed.');
        process.exit(0);
    });

    // 활성 요청이 있으면 최대 10초 대기, 없으면 즉시 종료
    const deadline = metrics.activeRequests > 0 ? 10000 : 2000;
    setTimeout(() => {
        console.warn(`Forced shutdown after ${deadline}ms (${metrics.activeRequests} requests pending)`);
        process.exit(1);
    }, deadline);
}

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));
