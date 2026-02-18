#!/bin/bash
# ═══════════════════════════════════════════════════
#  JARVIS 서비스 시작 스크립트 (#165)
#  - 모든 서비스 순차 시작 (crypto -> proxy -> mcp)
#  - PID 파일 관리
#  - 이미 실행 중인 서비스 체크
# ═══════════════════════════════════════════════════

set -e

# 프로젝트 루트 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

# PID 디렉토리
PID_DIR="$PROJECT_DIR/pids"
LOG_DIR="$PROJECT_DIR/logs"

# 환경변수 파일
ENV_FILE="$PROJECT_DIR/.env.jarvis"

# 서비스 정보
CRYPTO_HTTP_PORT=8766
CLAUDE_PROXY_PORT=8765
SC2_MCP_PORT=8767

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ── 유틸리티 함수 ──

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo ""
    echo -e "${BLUE}══════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}══════════════════════════════════════════${NC}"
}

# 디렉토리 초기화
init_dirs() {
    mkdir -p "$PID_DIR"
    mkdir -p "$LOG_DIR"
}

# PID 파일에서 프로세스 ID 읽기
read_pid() {
    local pid_file="$1"
    if [ -f "$pid_file" ]; then
        cat "$pid_file" 2>/dev/null
    else
        echo "0"
    fi
}

# 프로세스가 실행 중인지 확인
is_running() {
    local pid="$1"
    if [ "$pid" -le 0 ] 2>/dev/null; then
        return 1
    fi
    if kill -0 "$pid" 2>/dev/null; then
        return 0
    fi
    return 1
}

# 포트가 사용 중인지 확인
is_port_in_use() {
    local port="$1"
    if command -v ss &>/dev/null; then
        ss -tuln 2>/dev/null | grep -q ":${port} "
    elif command -v netstat &>/dev/null; then
        netstat -tuln 2>/dev/null | grep -q ":${port} "
    elif command -v lsof &>/dev/null; then
        lsof -i ":${port}" &>/dev/null
    else
        # 포트 체크 불가 - 실행 시도
        return 1
    fi
}

# 서비스 시작 함수
start_service() {
    local name="$1"
    local pid_file="$2"
    local log_file="$3"
    local port="$4"
    shift 4
    local cmd=("$@")

    log_info "[$name] 시작 중..."

    # 이미 실행 중인지 PID 파일로 확인
    local old_pid
    old_pid=$(read_pid "$pid_file")
    if is_running "$old_pid"; then
        log_warn "[$name] 이미 실행 중 (PID: $old_pid) - 건너뜀"
        return 0
    fi

    # 포트가 사용 중인지 확인
    if is_port_in_use "$port"; then
        log_warn "[$name] 포트 $port 이미 사용 중 - 다른 프로세스가 점유하고 있을 수 있음"
        log_warn "  기존 프로세스를 종료하려면: lsof -i :$port 또는 netstat -tulnp | grep $port"
        return 1
    fi

    # 서비스 시작 (백그라운드)
    "${cmd[@]}" >> "$log_file" 2>&1 &
    local pid=$!

    # PID 파일에 기록
    echo "$pid" > "$pid_file"

    # 시작 대기 (최대 10초)
    local wait_time=0
    local max_wait=10
    while [ $wait_time -lt $max_wait ]; do
        sleep 1
        wait_time=$((wait_time + 1))

        # 프로세스가 종료되었는지 확인
        if ! is_running "$pid"; then
            log_error "[$name] 시작 실패 (프로세스가 즉시 종료됨)"
            log_error "  로그 확인: tail -20 $log_file"
            rm -f "$pid_file"
            return 1
        fi

        # 포트가 열렸는지 확인
        if is_port_in_use "$port"; then
            log_info "[$name] 시작 완료 (PID: $pid, 포트: $port, ${wait_time}초 소요)"
            return 0
        fi
    done

    # 타임아웃이지만 프로세스는 살아있음 - 경고만 출력
    if is_running "$pid"; then
        log_warn "[$name] 포트 $port 대기 타임아웃, 프로세스는 실행 중 (PID: $pid)"
        return 0
    else
        log_error "[$name] 시작 실패"
        rm -f "$pid_file"
        return 1
    fi
}

# 환경변수 파일 로드
load_env() {
    if [ -f "$ENV_FILE" ]; then
        log_info ".env.jarvis 환경변수 로드"
        set -a
        # 주석과 빈 줄 무시하며 로드
        while IFS='=' read -r key value; do
            # 주석, 빈 줄 건너뛰기
            [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
            key=$(echo "$key" | xargs)
            value=$(echo "$value" | xargs)
            export "$key=$value" 2>/dev/null || true
        done < "$ENV_FILE"
        set +a
    else
        log_warn ".env.jarvis 파일 없음 - 환경변수 없이 시작"
    fi
}

# 환경변수 검증 (validate_env.py 호출)
validate_env() {
    local validate_script="$PROJECT_DIR/validate_env.py"
    if [ -f "$validate_script" ]; then
        log_info "환경변수 검증 중..."
        if python3 "$validate_script" 2>/dev/null || python "$validate_script" 2>/dev/null; then
            log_info "환경변수 검증 통과"
        else
            log_warn "환경변수 검증에 실패가 있음 - 계속 진행"
        fi
    fi
}

# ── 서비스별 시작 함수 ──

start_crypto_http() {
    local python_cmd
    if command -v python3 &>/dev/null; then
        python_cmd="python3"
    else
        python_cmd="python"
    fi

    start_service \
        "Crypto HTTP" \
        "$PID_DIR/crypto_http.pid" \
        "$LOG_DIR/crypto_http.log" \
        "$CRYPTO_HTTP_PORT" \
        "$python_cmd" "$PROJECT_DIR/crypto_trading/crypto_http_service.py"
}

start_claude_proxy() {
    if ! command -v node &>/dev/null; then
        log_error "[Claude Proxy] Node.js가 설치되지 않음"
        return 1
    fi

    start_service \
        "Claude Proxy" \
        "$PID_DIR/claude_proxy.pid" \
        "$LOG_DIR/claude_proxy.log" \
        "$CLAUDE_PROXY_PORT" \
        node "$PROJECT_DIR/claude_proxy.js"
}

start_sc2_mcp() {
    local python_cmd
    if command -v python3 &>/dev/null; then
        python_cmd="python3"
    else
        python_cmd="python"
    fi

    start_service \
        "SC2 MCP" \
        "$PID_DIR/sc2_mcp.pid" \
        "$LOG_DIR/sc2_mcp.log" \
        "$SC2_MCP_PORT" \
        "$python_cmd" "$PROJECT_DIR/sc2_mcp_server.py"
}

# ── 전체 서비스 상태 표시 ──

show_status() {
    log_header "JARVIS 서비스 상태"

    local services=("crypto_http:Crypto HTTP:$CRYPTO_HTTP_PORT"
                    "claude_proxy:Claude Proxy:$CLAUDE_PROXY_PORT"
                    "sc2_mcp:SC2 MCP:$SC2_MCP_PORT")

    for entry in "${services[@]}"; do
        IFS=':' read -r id name port <<< "$entry"
        local pid_file="$PID_DIR/${id}.pid"
        local pid
        pid=$(read_pid "$pid_file")
        local status

        if is_running "$pid"; then
            status="${GREEN}실행 중${NC} (PID: $pid, 포트: $port)"
        elif is_port_in_use "$port"; then
            status="${YELLOW}포트 사용 중${NC} (포트: $port, PID 파일 없음)"
        else
            status="${RED}중지됨${NC}"
        fi

        echo -e "  [$name] $status"
    done
    echo ""
}

# ── 전체 서비스 중지 ──

stop_all() {
    log_header "JARVIS 서비스 중지"

    local services=("sc2_mcp:SC2 MCP" "claude_proxy:Claude Proxy" "crypto_http:Crypto HTTP")

    for entry in "${services[@]}"; do
        IFS=':' read -r id name <<< "$entry"
        local pid_file="$PID_DIR/${id}.pid"
        local pid
        pid=$(read_pid "$pid_file")

        if is_running "$pid"; then
            log_info "[$name] 종료 중 (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 2
            if is_running "$pid"; then
                log_warn "[$name] 강제 종료"
                kill -9 "$pid" 2>/dev/null || true
            fi
            rm -f "$pid_file"
            log_info "[$name] 종료 완료"
        else
            log_info "[$name] 이미 중지됨"
            rm -f "$pid_file"
        fi
    done
}

# ── 메인 ──

main() {
    local action="${1:-start}"

    log_header "JARVIS 서비스 관리자"

    case "$action" in
        start)
            init_dirs
            load_env
            validate_env

            log_header "서비스 순차 시작"

            # 1. Crypto HTTP 서비스 (다른 서비스가 의존)
            start_crypto_http
            sleep 2

            # 2. Claude Proxy (Crypto HTTP에 의존)
            start_claude_proxy
            sleep 2

            # 3. SC2 MCP 서버
            start_sc2_mcp

            # 최종 상태 표시
            sleep 2
            show_status
            log_info "JARVIS 서비스 시작 완료"
            ;;

        stop)
            stop_all
            log_info "JARVIS 서비스 중지 완료"
            ;;

        restart)
            stop_all
            sleep 3
            main "start"
            ;;

        status)
            show_status
            ;;

        *)
            echo "사용법: $0 {start|stop|restart|status}"
            echo ""
            echo "  start   - 모든 서비스 순차 시작"
            echo "  stop    - 모든 서비스 중지"
            echo "  restart - 모든 서비스 재시작"
            echo "  status  - 서비스 상태 확인"
            exit 1
            ;;
    esac
}

main "$@"
