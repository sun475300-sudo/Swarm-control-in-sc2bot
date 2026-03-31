#!/usr/bin/env bash
# Phase 561: Bash Scripting Advanced
# SC2 Bot deployment, monitoring, and automation scripts

set -euo pipefail
IFS=$'\n\t'

# ─────────────────────────────────────────────
# Color output
# ─────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

log_info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

BOT_NAME="sc2_zerg_bot"
BOT_VERSION="560.0"
BOT_DIR="${BOT_DIR:-$(dirname "$(readlink -f "$0")")}"
VENV_DIR="${BOT_DIR}/.venv"
LOG_DIR="${BOT_DIR}/logs"
MODEL_DIR="${BOT_DIR}/models"
PID_FILE="${BOT_DIR}/.bot.pid"
MAX_LOG_SIZE_MB=100
MAX_LOG_FILES=10

# ─────────────────────────────────────────────
# Functions
# ─────────────────────────────────────────────

check_deps() {
    log_info "Checking dependencies..."
    local missing=()
    local deps=(python3 git curl jq)
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &>/dev/null; then
            missing+=("$dep")
        fi
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing: ${missing[*]}"
        return 1
    fi
    log_ok "All dependencies found"
}

setup_venv() {
    log_info "Setting up Python venv..."
    if [[ ! -d "$VENV_DIR" ]]; then
        python3 -m venv "$VENV_DIR"
    fi
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    pip install --quiet --upgrade pip
    if [[ -f "${BOT_DIR}/requirements.txt" ]]; then
        pip install --quiet -r "${BOT_DIR}/requirements.txt"
    fi
    log_ok "Venv ready: $VENV_DIR"
}

start_bot() {
    log_info "Starting $BOT_NAME v$BOT_VERSION..."
    mkdir -p "$LOG_DIR" "$MODEL_DIR"

    if [[ -f "$PID_FILE" ]]; then
        local old_pid
        old_pid=$(cat "$PID_FILE")
        if kill -0 "$old_pid" 2>/dev/null; then
            log_warn "Bot already running (PID $old_pid)"
            return 0
        fi
        rm -f "$PID_FILE"
    fi

    local log_file="${LOG_DIR}/${BOT_NAME}_$(date +%Y%m%d_%H%M%S).log"
    nohup python3 -u "${BOT_DIR}/main.py" \
        --bot-name "$BOT_NAME" \
        --version "$BOT_VERSION" \
        >> "$log_file" 2>&1 &
    echo $! > "$PID_FILE"
    log_ok "Bot started (PID $(cat "$PID_FILE")) → $log_file"
}

stop_bot() {
    if [[ ! -f "$PID_FILE" ]]; then
        log_warn "Bot not running (no PID file)"
        return 0
    fi
    local pid
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
        kill -SIGTERM "$pid"
        local timeout=10
        while kill -0 "$pid" 2>/dev/null && (( timeout-- > 0 )); do
            sleep 1
        done
        if kill -0 "$pid" 2>/dev/null; then
            kill -SIGKILL "$pid"
            log_warn "Sent SIGKILL to PID $pid"
        else
            log_ok "Bot stopped (PID $pid)"
        fi
    else
        log_warn "Process $pid not found"
    fi
    rm -f "$PID_FILE"
}

status_bot() {
    if [[ ! -f "$PID_FILE" ]]; then
        echo "Status: STOPPED"
        return 1
    fi
    local pid
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
        local uptime_s elapsed
        uptime_s=$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d ' ' || echo 0)
        printf "Status: RUNNING\nPID: %s\nUptime: %ss\n" "$pid" "$uptime_s"
    else
        echo "Status: DEAD (stale PID $pid)"
        rm -f "$PID_FILE"
        return 1
    fi
}

rotate_logs() {
    log_info "Rotating logs in $LOG_DIR..."
    local count=0
    while IFS= read -r -d '' f; do
        local size_mb
        size_mb=$(du -m "$f" | cut -f1)
        if (( size_mb > MAX_LOG_SIZE_MB )); then
            gzip "$f" && (( count++ ))
        fi
    done < <(find "$LOG_DIR" -name "*.log" -print0 2>/dev/null)

    # Keep only recent compressed logs
    local n_compressed
    n_compressed=$(find "$LOG_DIR" -name "*.log.gz" | wc -l)
    if (( n_compressed > MAX_LOG_FILES )); then
        find "$LOG_DIR" -name "*.log.gz" -print0 \
            | xargs -0 ls -t \
            | tail -n "+$((MAX_LOG_FILES+1))" \
            | xargs rm -f
    fi
    log_ok "Rotated $count logs"
}

health_check() {
    log_info "Running health check..."
    local checks_passed=0
    local checks_total=4

    # 1. Python version
    local py_ver
    py_ver=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
    if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)"; then
        log_ok "Python $py_ver ✓"
        (( checks_passed++ ))
    else
        log_error "Python $py_ver too old (need 3.9+)"
    fi

    # 2. Required Python packages
    if python3 -c "import sc2, numpy" 2>/dev/null; then
        log_ok "Core packages ✓"
        (( checks_passed++ ))
    else
        log_warn "Some packages missing (non-fatal)"
        (( checks_passed++ ))
    fi

    # 3. Disk space
    local free_mb
    free_mb=$(df -m "$BOT_DIR" | awk 'NR==2 {print $4}')
    if (( free_mb > 500 )); then
        log_ok "Disk: ${free_mb}MB free ✓"
        (( checks_passed++ ))
    else
        log_warn "Low disk: ${free_mb}MB"
    fi

    # 4. Models directory
    if [[ -d "$MODEL_DIR" ]]; then
        local n_models
        n_models=$(find "$MODEL_DIR" -name "*.pt" -o -name "*.pkl" 2>/dev/null | wc -l)
        log_ok "Models: $n_models files ✓"
        (( checks_passed++ ))
    else
        log_warn "No models directory"
    fi

    printf "\nHealth: %d/%d checks passed\n" "$checks_passed" "$checks_total"
    [[ $checks_passed -ge $((checks_total - 1)) ]]
}

show_stats() {
    log_info "Bot Statistics"
    echo "───────────────────────────────"
    printf "%-20s %s\n" "Name:"     "$BOT_NAME"
    printf "%-20s %s\n" "Version:"  "$BOT_VERSION"
    printf "%-20s %s\n" "Bot Dir:"  "$BOT_DIR"
    printf "%-20s %s\n" "Venv:"     "$VENV_DIR"
    printf "%-20s %s\n" "Logs:"     "$LOG_DIR"
    printf "%-20s %s\n" "Models:"   "$MODEL_DIR"

    local n_py=0
    n_py=$(find "$BOT_DIR" -name "*.py" 2>/dev/null | wc -l)
    printf "%-20s %s\n" "Python files:" "$n_py"

    local last_log=""
    last_log=$(find "$LOG_DIR" -name "*.log" -newer "$BOT_DIR" 2>/dev/null \
               | sort -t_ -k2 | tail -1) || true
    printf "%-20s %s\n" "Latest log:" "${last_log:-none}"
    echo "───────────────────────────────"
}

# ─────────────────────────────────────────────
# CI/CD helpers
# ─────────────────────────────────────────────

run_tests() {
    log_info "Running tests..."
    local failed=0
    if python3 -m pytest tests/ -x -q \
        --tb=short \
        -p no:warnings \
        2>&1 | tail -5; then
        log_ok "Tests passed"
    else
        log_error "Tests failed"
        failed=1
    fi
    return $failed
}

build_docker() {
    log_info "Building Docker image..."
    docker build -t "${BOT_NAME}:${BOT_VERSION}" -t "${BOT_NAME}:latest" \
        --build-arg VERSION="$BOT_VERSION" \
        "$BOT_DIR"
    log_ok "Image built: ${BOT_NAME}:${BOT_VERSION}"
}

# ─────────────────────────────────────────────
# Main dispatch
# ─────────────────────────────────────────────

usage() {
    cat <<EOF
Usage: $0 <command>

Commands:
  start        Start the bot
  stop         Stop the bot
  restart      Restart the bot
  status       Show bot status
  health       Run health check
  stats        Show statistics
  rotate-logs  Rotate log files
  test         Run test suite
  build        Build Docker image
  check-deps   Check system dependencies
EOF
}

main() {
    local cmd="${1:-help}"
    case "$cmd" in
        start)       check_deps && start_bot ;;
        stop)        stop_bot ;;
        restart)     stop_bot; sleep 1; start_bot ;;
        status)      status_bot ;;
        health)      health_check ;;
        stats)       show_stats ;;
        rotate-logs) rotate_logs ;;
        test)        run_tests ;;
        build)       build_docker ;;
        check-deps)  check_deps ;;
        help|--help|-h) usage ;;
        *)
            log_error "Unknown command: $cmd"
            usage; exit 1 ;;
    esac
}

echo "Phase 561: Bash Scripting — SC2 Bot Deployment"
main "${1:-stats}"
