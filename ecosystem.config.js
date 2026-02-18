/**
 * PM2 프로세스 관리 설정 (#167)
 *
 * 사용법:
 *   pm2 start ecosystem.config.js
 *   pm2 start ecosystem.config.js --only claude-proxy
 *   pm2 start ecosystem.config.js --env production
 *
 * 정의된 앱:
 *   1. claude-proxy      — Claude AI 프록시 서버 (Node.js, 포트 3456)
 *   2. crypto-http        — 암호화폐 HTTP 서비스 (Python, 포트 8766)
 *   3. sc2-mcp-server     — StarCraft II MCP 서버 (Python)
 */
module.exports = {
  apps: [
    // ───────────────────────────────────────────
    // 1) Claude Proxy (Node.js)
    // ───────────────────────────────────────────
    {
      name: 'claude-proxy',
      script: 'claude_proxy.js',
      interpreter: 'node',
      // 클러스터 모드: Node.js 앱에서 CPU 코어 활용
      instances: process.env.PROXY_INSTANCES || 1,
      exec_mode: 'cluster',
      watch: false,
      max_memory_restart: '512M',
      // 로그 설정
      log_file: './logs/pm2-claude-proxy-combined.log',
      out_file: './logs/pm2-claude-proxy-out.log',
      error_file: './logs/pm2-claude-proxy-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      // 재시작 정책
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      // 환경변수 (기본)
      env: {
        NODE_ENV: 'development',
        PORT: 3456,
        LOG_LEVEL: 'debug',
      },
      // 환경변수 (프로덕션: --env production)
      env_production: {
        NODE_ENV: 'production',
        PORT: 3456,
        LOG_LEVEL: 'info',
      },
    },

    // ───────────────────────────────────────────
    // 2) 암호화폐 HTTP 서비스 (Python)
    // ───────────────────────────────────────────
    {
      name: 'crypto-http',
      script: 'crypto_trading/crypto_http_service.py',
      interpreter: 'python',
      interpreter_args: '-u', // 파이썬 버퍼 없이 출력
      instances: 1,
      exec_mode: 'fork', // Python은 fork 모드 사용
      watch: false,
      max_memory_restart: '256M',
      // 로그 설정
      log_file: './logs/pm2-crypto-http-combined.log',
      out_file: './logs/pm2-crypto-http-out.log',
      error_file: './logs/pm2-crypto-http-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      // 재시작 정책
      autorestart: true,
      max_restarts: 5,
      restart_delay: 5000,
      // 환경변수
      env: {
        PYTHONPATH: '.',
        CRYPTO_PORT: 8766,
        LOG_LEVEL: 'DEBUG',
        DRY_RUN: 'true',
      },
      env_production: {
        PYTHONPATH: '.',
        CRYPTO_PORT: 8766,
        LOG_LEVEL: 'INFO',
        DRY_RUN: 'false',
      },
    },

    // ───────────────────────────────────────────
    // 3) SC2 MCP 서버 (Python)
    // ───────────────────────────────────────────
    {
      name: 'sc2-mcp-server',
      script: 'sc2_mcp_server.py',
      interpreter: 'python',
      interpreter_args: '-u',
      instances: 1,
      exec_mode: 'fork',
      watch: false,
      max_memory_restart: '512M',
      // 로그 설정
      log_file: './logs/pm2-sc2-mcp-combined.log',
      out_file: './logs/pm2-sc2-mcp-out.log',
      error_file: './logs/pm2-sc2-mcp-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      // 재시작 정책
      autorestart: true,
      max_restarts: 5,
      restart_delay: 5000,
      // 환경변수
      env: {
        PYTHONPATH: '.',
        LOG_LEVEL: 'DEBUG',
        SC2_DIR: 'd:\\Swarm-contol-in-sc2bot',
      },
      env_production: {
        PYTHONPATH: '.',
        LOG_LEVEL: 'INFO',
        SC2_DIR: '/opt/jarvis/sc2bot',
      },
    },
  ],
};
