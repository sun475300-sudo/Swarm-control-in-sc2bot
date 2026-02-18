/**
 * JARVIS Claude AI Proxy Server (v2.0)
 * - 공식 Anthropic SDK (Claude Opus 4.6 / Sonnet 4.6 / Haiku 4.5)
 * - 모델 라우팅 (복잡도 기반 자동 선택)
 * - MCP 도구 연동 (암호화폐, 시스템, SC2)
 * - 기존 Discord 봇 인터페이스 호환 (POST /chat → {reply})
 * - 웹 세션 폴백 (API 키 없을 경우)
 */
const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const fetch = require('node-fetch');
const crypto = require('crypto');
const path = require('path');
const { execSync } = require('child_process');
const fs = require('fs');

require('dotenv').config({ path: path.join(__dirname, '.env.jarvis') });

const Anthropic = require('@anthropic-ai/sdk').default || require('@anthropic-ai/sdk');

const app = express();
const PORT = 8765;

app.use(cors());
app.use(bodyParser.json({ limit: '10mb' }));
app.use((req, res, next) => {
    res.header('Content-Type', 'application/json; charset=utf-8');
    next();
});

// ═══════════════════════════════════════════════
//  설정
// ═══════════════════════════════════════════════

const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY || '';
const SESSION_KEY = process.env.CLAUDE_SESSION_KEY || '';
const CRYPTO_SERVICE = 'http://127.0.0.1:8766';
const SC2_DIR = path.join(__dirname);

// 모델 라우팅
const MODELS = {
    haiku:  'claude-haiku-4-5-20251001',
    sonnet: 'claude-sonnet-4-6',
    opus:   'claude-opus-4-6',
};
const DEFAULT_MODEL = process.env.JARVIS_DEFAULT_MODEL || 'sonnet';

// Anthropic 클라이언트 (API 키가 있을 때만)
let anthropic = null;
if (ANTHROPIC_API_KEY) {
    anthropic = new Anthropic({ apiKey: ANTHROPIC_API_KEY });
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
- 시스템 모니터링 (스크린샷, 인터넷 속도)
- 스타크래프트2 봇 상태 확인 및 제어

도구를 사용할 때는 결과를 자연스러운 한국어로 요약해서 전달해.
절대 구글, OpenAI, Anthropic 등 다른 회사가 만들었다고 말하지 마.`;

// ═══════════════════════════════════════════════
//  모델 라우팅
// ═══════════════════════════════════════════════

function selectModel(message, requestedModel) {
    // 명시적 모델 요청
    if (requestedModel && MODELS[requestedModel]) {
        return MODELS[requestedModel];
    }

    const msg = message.toLowerCase();

    // Opus: 복잡한 분석, 코딩, 전략
    const complexKeywords = [
        '분석해', '코드', '전략', '설계', '비교해', '왜', '원인',
        '리팩토링', '최적화', '아키텍처', '깊이', '상세히', '논리',
        'analyze', 'code', 'strategy', 'debug', 'explain why',
    ];
    if (complexKeywords.some(k => msg.includes(k)) || msg.length > 500) {
        return MODELS.opus;
    }

    // Haiku: 간단한 질문, 인사, 단답형
    const simpleKeywords = [
        '안녕', '뭐해', '고마워', '시간', '날씨', '몇시', 'ㅎㅎ', 'ㅋㅋ',
        '응', '네', '아니', 'ok', 'yes', 'no', 'hi', 'hello',
    ];
    if (simpleKeywords.some(k => msg.includes(k)) && msg.length < 50) {
        return MODELS.haiku;
    }

    // 기본: Sonnet (성능/비용 균형)
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
                amount_krw: { type: 'number', description: "매수 금액 (원)" }
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
//  도구 실행기
// ═══════════════════════════════════════════════

async function executeTool(name, input) {
    try {
        switch (name) {
            // ── 암호화폐 도구 (HTTP → :8766) ──
            case 'coin_price': {
                const symbol = (input.symbol || 'BTC').toUpperCase();
                const res = await fetch(`${CRYPTO_SERVICE}/market/price/${symbol}`, { timeout: 10000 });
                const data = await res.json();
                if (data.error) return data.error;
                const chg = data.signed_change_rate ? (data.signed_change_rate * 100).toFixed(2) : '?';
                return `${data.ticker} 현재가: ${data.trade_price?.toLocaleString()}원 (${chg}%)`;
            }
            case 'coin_prices': {
                const res = await fetch(`${CRYPTO_SERVICE}/market/prices?limit=10`, { timeout: 10000 });
                const data = await res.json();
                return data.prices?.map(p =>
                    `${p.ticker.replace('KRW-','')}: ${p.price?.toLocaleString()}원`
                ).join('\n') || '시세 조회 실패';
            }
            case 'my_balance': {
                const res = await fetch(`${CRYPTO_SERVICE}/portfolio/balance`, { timeout: 10000 });
                const data = await res.json();
                if (data.error) return data.error;
                let lines = [`총 자산: ${data.total_krw?.toLocaleString()}원`];
                for (const a of (data.assets || [])) {
                    if (a.currency === 'KRW') {
                        lines.push(`  KRW: ${a.balance?.toLocaleString()}원`);
                    } else {
                        const pnl = a.pnl_pct ? ` (${a.pnl_pct > 0 ? '+' : ''}${a.pnl_pct}%)` : '';
                        lines.push(`  ${a.currency}: ${a.balance?.toFixed(4)}개 = ${a.value_krw?.toLocaleString()}원${pnl}`);
                    }
                }
                return lines.join('\n');
            }
            case 'buy_coin': {
                const symbol = (input.symbol || 'BTC').toUpperCase();
                const market = symbol.startsWith('KRW-') ? symbol : `KRW-${symbol}`;
                const res = await fetch(`${CRYPTO_SERVICE}/trade/buy`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ market, amount_krw: input.amount_krw }),
                    timeout: 15000,
                });
                const data = await res.json();
                if (data.error) return `매수 실패: ${data.error}`;
                const dry = data.dry_run ? '[모의매매] ' : '';
                return `${dry}${market} 매수 완료: ${data.amount_krw?.toLocaleString()}원 (단가 ${data.price?.toLocaleString()}원)`;
            }
            case 'sell_coin': {
                const symbol = (input.symbol || 'BTC').toUpperCase();
                const market = symbol.startsWith('KRW-') ? symbol : `KRW-${symbol}`;
                const percent = input.percent || 100;
                const res = await fetch(`${CRYPTO_SERVICE}/trade/sell`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ market, percent }),
                    timeout: 15000,
                });
                const data = await res.json();
                if (data.error) return `매도 실패: ${data.error}`;
                const dry = data.dry_run ? '[모의매매] ' : '';
                return `${dry}${market} 매도 완료: ${data.volume?.toFixed(4)}개 (${data.value_krw?.toLocaleString()}원)`;
            }
            case 'analyze_market': {
                const res = await fetch(`${CRYPTO_SERVICE}/chart/analysis`, { timeout: 30000 });
                const data = await res.json();
                if (!data.summary) return '분석 실패';
                return data.summary.map(s =>
                    `${s.coin}: ${s.recommendation} (점수:${s.score > 0 ? '+' : ''}${s.score}, RSI:${s.rsi}, 24h:${s.change_24h > 0 ? '+' : ''}${s.change_24h}%)`
                ).join('\n');
            }
            case 'analyze_coin_detail': {
                const symbol = (input.symbol || 'BTC').toUpperCase();
                const ticker = symbol.startsWith('KRW-') ? symbol : `KRW-${symbol}`;
                const res = await fetch(`${CRYPTO_SERVICE}/chart/analysis?tickers=${ticker}`, { timeout: 20000 });
                const data = await res.json();
                if (!data.summary || data.summary.length === 0) return '분석 실패';
                const s = data.summary[0];
                return `${s.coin} 상세 분석:\n  현재가: ${s.price?.toLocaleString()}원\n  추천: ${s.recommendation} (점수: ${s.score > 0 ? '+' : ''}${s.score}/100)\n  RSI: ${s.rsi}\n  24h 변동: ${s.change_24h > 0 ? '+' : ''}${s.change_24h}%`;
            }
            case 'auto_trade_status': {
                const res = await fetch(`${CRYPTO_SERVICE}/auto/status`, { timeout: 10000 });
                const data = await res.json();
                const running = data.is_running ? '실행 중' : '중지됨';
                const dry = data.dry_run ? '모의매매' : '실전매매';
                let lines = [`자동매매: ${running} (${dry})`, `사이클: ${data.cycle_count}회`];
                if (data.last_analysis) {
                    for (const a of data.last_analysis) {
                        lines.push(`  ${a.market?.replace('KRW-','')}: ${a.recommendation} (${a.score > 0 ? '+' : ''}${a.score}점)`);
                    }
                }
                return lines.join('\n');
            }
            case 'start_auto_trade': {
                const body = {};
                if (input.strategy) body.strategy = input.strategy;
                const res = await fetch(`${CRYPTO_SERVICE}/auto/start`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                    timeout: 10000,
                });
                const data = await res.json();
                return data.message || '자동매매 시작';
            }
            case 'stop_auto_trade': {
                const res = await fetch(`${CRYPTO_SERVICE}/auto/stop`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    timeout: 10000,
                });
                const data = await res.json();
                return data.message || '자동매매 중지';
            }
            case 'portfolio_summary': {
                const res = await fetch(`${CRYPTO_SERVICE}/portfolio/summary`, { timeout: 10000 });
                const data = await res.json();
                if (data.status === 'no_data') return data.message;
                const sign = data.pnl_krw >= 0 ? '+' : '';
                return `포트폴리오 요약:\n  총 자산: ${data.total_value_krw?.toLocaleString()}원\n  수익: ${sign}${data.pnl_krw?.toLocaleString()}원 (${sign}${data.pnl_pct}%)\n  거래 횟수: ${data.trades_count}회`;
            }
            case 'recent_trades': {
                const count = input.count || 10;
                const res = await fetch(`${CRYPTO_SERVICE}/trade/history?limit=${count}`, { timeout: 10000 });
                const data = await res.json();
                if (!data.trades || data.trades.length === 0) return '거래 내역 없음';
                return data.trades.map(t => {
                    const side = t.side === 'buy' ? '매수' : '매도';
                    const dry = t.dry_run ? '[모의]' : '';
                    return `${dry}${t.timestamp?.substring(0,16)} ${side} ${t.ticker} ${t.amount?.toLocaleString()}원`;
                }).join('\n');
            }

            // ── 시스템 도구 ──
            case 'capture_screenshot': {
                try {
                    const result = execSync(
                        'python -c "import pyautogui,base64,io;s=pyautogui.screenshot();b=io.BytesIO();s.save(b,format=\'JPEG\',quality=50);print(\'captured:\'+str(len(b.getvalue()))+\' bytes\')"',
                        { timeout: 10000, encoding: 'utf-8' }
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
                        { timeout: 120000, encoding: 'utf-8' }
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
                const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
                if (Array.isArray(data)) {
                    const counts = {};
                    data.forEach(e => { counts[e.unit_type || 'UNKNOWN'] = (counts[e.unit_type || 'UNKNOWN'] || 0) + 1; });
                    return `현재 유닛: ${JSON.stringify(counts)}`;
                }
                return `게임 상태: ${JSON.stringify(data)}`;
            }
            case 'sc2_set_aggression': {
                const level = input.level || 'balanced';
                const valid = ['passive', 'balanced', 'aggressive', 'all_in'];
                if (!valid.includes(level)) return `유효하지 않은 레벨. 선택: ${valid.join(', ')}`;
                const cmdFile = path.join(SC2_DIR, 'jarvis_command.json');
                fs.writeFileSync(cmdFile, JSON.stringify({ aggression_level: level }), 'utf-8');
                return `공격성 레벨을 ${level}로 설정했어. 봇이 곧 반영할 거야.`;
            }
            case 'sc2_bot_logs': {
                const logDir = path.join(SC2_DIR, 'logs');
                if (!fs.existsSync(logDir)) return '로그 디렉토리 없음';
                const logFiles = fs.readdirSync(logDir).filter(f => f.endsWith('.log')).sort().reverse();
                if (logFiles.length === 0) return '로그 파일 없음';
                const logPath = path.join(logDir, logFiles[0]);
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
//  공식 Anthropic API 호출 (Tool Use 포함)
// ═══════════════════════════════════════════════

async function queryClaudeAPI(userMessage, requestedModel) {
    if (!anthropic) return null;

    const model = selectModel(userMessage, requestedModel);
    console.log(`🧠 모델 선택: ${model}`);

    let messages = [{ role: 'user', content: userMessage }];
    const maxToolRounds = 5; // 도구 호출 최대 반복 횟수

    for (let round = 0; round < maxToolRounds; round++) {
        const response = await anthropic.messages.create({
            model,
            max_tokens: 4096,
            system: SYSTEM_PROMPT,
            tools: TOOLS,
            messages,
        });

        // 텍스트 응답 수집
        let textParts = [];
        let toolUses = [];

        for (const block of response.content) {
            if (block.type === 'text') {
                textParts.push(block.text);
            } else if (block.type === 'tool_use') {
                toolUses.push(block);
            }
        }

        // 도구 호출이 없으면 텍스트 반환
        if (toolUses.length === 0) {
            return textParts.join('\n');
        }

        // 도구 실행 및 결과 수집
        console.log(`🔧 도구 호출 ${toolUses.length}개: ${toolUses.map(t => t.name).join(', ')}`);

        // assistant 메시지 추가 (tool_use 포함)
        messages.push({ role: 'assistant', content: response.content });

        // tool_result 메시지 추가
        const toolResults = [];
        for (const tu of toolUses) {
            const result = await executeTool(tu.name, tu.input);
            console.log(`  ✓ ${tu.name}: ${result.substring(0, 80)}...`);
            toolResults.push({
                type: 'tool_result',
                tool_use_id: tu.id,
                content: result,
            });
        }
        messages.push({ role: 'user', content: toolResults });
    }

    return '도구 호출 제한에 도달했어. 잠시 후 다시 시도해줘.';
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
                } catch (e) { }
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

async function queryJarvis(message, requestedModel) {
    // 1차: 공식 API (Tool Use 지원)
    if (anthropic) {
        try {
            const result = await queryClaudeAPI(message, requestedModel);
            if (result) return result;
        } catch (e) {
            console.error('API 오류, 웹 세션 폴백:', e.message);
        }
    }

    // 2차: 웹 세션 폴백 (Tool Use 미지원)
    const webResult = await queryClaudeWeb(message);
    if (webResult) return sanitizeResponse(webResult);

    return '죄송해요, 현재 AI 서비스에 연결할 수 없어요. API 키나 세션을 확인해주세요.';
}

// ═══════════════════════════════════════════════
//  HTTP 엔드포인트
// ═══════════════════════════════════════════════

// JARVIS 커스텀 엔드포인트 (Discord 봇 호환)
app.post('/chat', async (req, res) => {
    const start = Date.now();
    try {
        const userMessage = req.body.message;
        const userId = req.body.user;
        const requestedModel = req.body.model; // 'haiku', 'sonnet', 'opus'

        if (!userMessage) {
            return res.status(400).json({ error: 'Message is required' });
        }

        console.log(`📨 [${userId}] ${userMessage.substring(0, 100)}`);

        const reply = await queryJarvis(userMessage, requestedModel);

        const elapsed = ((Date.now() - start) / 1000).toFixed(1);
        console.log(`🤖 [${elapsed}s] ${reply.substring(0, 80)}...`);

        res.json({ reply });
    } catch (e) {
        console.error('Chat Error:', e);
        res.status(500).json({
            error: 'Internal Server Error',
            reply: '죄송해요, 처리 중에 문제가 발생했어요.'
        });
    }
});

// OpenAI 호환 엔드포인트
app.post('/v1/chat/completions', async (req, res) => {
    try {
        const messages = req.body.messages;
        const lastMessage = messages[messages.length - 1].content;

        const reply = await queryJarvis(lastMessage);

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
        res.status(500).json({ error: e.message });
    }
});

// 상태 확인 엔드포인트
app.get('/status', (req, res) => {
    res.json({
        service: 'JARVIS Claude Proxy v2.0',
        mode: anthropic ? 'official_api' : 'web_session_fallback',
        models: MODELS,
        default_model: DEFAULT_MODEL,
        tools_count: TOOLS.length,
        uptime: process.uptime(),
    });
});

// ═══════════════════════════════════════════════
//  서버 시작
// ═══════════════════════════════════════════════

app.listen(PORT, () => {
    console.log('');
    console.log('╔══════════════════════════════════════════╗');
    console.log('║   JARVIS Claude Proxy v2.0               ║');
    console.log('╠══════════════════════════════════════════╣');
    console.log(`║  Port: ${PORT}                              ║`);
    console.log(`║  Mode: ${anthropic ? 'Official API (SDK)    ' : 'Web Session (Fallback)'}       ║`);
    console.log(`║  Models:                                 ║`);
    console.log(`║    Haiku:  ${MODELS.haiku}  ║`);
    console.log(`║    Sonnet: ${MODELS.sonnet}              ║`);
    console.log(`║    Opus:   ${MODELS.opus}                ║`);
    console.log(`║  Tools: ${TOOLS.length} MCP tools registered         ║`);
    console.log('╚══════════════════════════════════════════╝');
    console.log('');
});
