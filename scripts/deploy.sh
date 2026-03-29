#!/bin/bash
#================================================================================
# 🎮 StarCraft II AI Bot - Production Deployment Script
# P79: Production Deployment Scripts
#================================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOY_ENV="${DEPLOY_ENV:-production}"
LOG_DIR="${PROJECT_ROOT}/logs"
BACKUP_DIR="${PROJECT_ROOT}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
VERSION_FILE="${PROJECT_ROOT}/VERSION"

# Colors
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Initialize directories
init_dirs() {
    mkdir -p "$LOG_DIR" "$BACKUP_DIR"
    log_info "Directories initialized"
}

# Get current version
get_version() {
    if [[ -f "$VERSION_FILE" ]]; then
        cat "$VERSION_FILE"
    else
        echo "0.0.0"
    fi
}

# Update version
update_version() {
    local bump_type="${1:-patch}"
    local current_version
    current_version=$(get_version)
    
    IFS='.' read -r major minor patch <<< "$current_version"
    
    case "$bump_type" in
        major)
            ((major++))
            minor=0
            patch=0
            ;;
        minor)
            ((minor++))
            patch=0
            ;;
        patch)
            ((patch++))
            ;;
    esac
    
    local new_version="${major}.${minor}.${patch}"
    echo "$new_version" > "$VERSION_FILE"
    echo "$new_version"
}

# Docker commands
docker_build() {
    local image_name="${1:-sc2_wicked_bot}"
    local tag="${2:-latest}"
    
    log_info "Building Docker image: ${image_name}:${tag}"
    docker build \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        --cache-from "${image_name}:builder" \
        -t "${image_name}:${tag}" \
        -t "${image_name}:latest" \
        "$PROJECT_ROOT"
    
    log_success "Docker image built successfully"
}

docker_push() {
    local image_name="${1:-sc2_wicked_bot}"
    local registry="${2:-}"
    local tag="${3:-latest}"
    
    if [[ -n "$registry" ]]; then
        local full_image="${registry}/${image_name}:${tag}"
        docker tag "${image_name}:${tag}" "$full_image"
        docker push "$full_image"
        log_success "Image pushed to registry: $full_image"
    else
        log_warn "No registry specified, skipping push"
    fi
}

# Backup functions
backup_database() {
    local db_name="${POSTGRES_DB:-sc2_analytics}"
    local db_user="${POSTGRES_USER:-postgres}"
    local backup_file="${BACKUP_DIR}/db_backup_${TIMESTAMP}.sql.gz"
    
    if command -v pg_dump &> /dev/null; then
        log_info "Backing up database..."
        PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump -h "${POSTGRES_HOST:-localhost}" \
            -U "$db_user" "$db_name" | gzip > "$backup_file"
        log_success "Database backed up to: $backup_file"
    else
        log_warn "pg_dump not found, skipping database backup"
    fi
}

backup_configs() {
    local backup_file="${BACKUP_DIR}/configs_${TIMESTAMP}.tar.gz"
    
    tar -czf "$backup_file" \
        -C "$PROJECT_ROOT" \
        --exclude='*.pyc' \
        --exclude='__pycache__' \
        --exclude='node_modules' \
        --exclude='.git' \
        .env \
        config/ \
        scripts/
    
    log_success "Configs backed up to: $backup_file"
}

# Deployment functions
deploy_docker_compose() {
    local compose_file="${1:-docker-compose.yml}"
    
    log_info "Deploying with Docker Compose..."
    
    docker-compose -f "$compose_file" down || true
    docker-compose -f "$compose_file" pull
    docker-compose -f "$compose_file" up -d
    
    sleep 5
    
    if docker-compose -f "$compose_file" ps | grep -q "Up"; then
        log_success "Deployment successful"
    else
        log_error "Deployment failed"
        return 1
    fi
}

deploy_kubernetes() {
    local namespace="${1:-sc2-bot}"
    local kubeconfig="${KUBECONFIG:-~/.kube/config}"
    
    log_info "Deploying to Kubernetes..."
    
    if [[ ! -f "$kubeconfig" ]]; then
        log_error "Kubeconfig not found: $kubeconfig"
        return 1
    fi
    
    kubectl --kubeconfig="$kubeconfig" apply -f "$PROJECT_ROOT/k8s/" -n "$namespace"
    kubectl --kubeconfig="$kubeconfig" rollout status deployment/sc2-bot -n "$namespace"
    
    log_success "Kubernetes deployment complete"
}

# Health checks
health_check() {
    local url="${1:-http://localhost:5000/health}"
    local max_attempts="${2:-30}"
    local attempt=1
    
    log_info "Running health check..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            log_success "Health check passed"
            return 0
        fi
        
        echo -ne "${YELLOW}Attempt $attempt/$max_attempts...${NC}\r"
        sleep 2
        ((attempt++))
    done
    
    log_error "Health check failed after $max_attempts attempts"
    return 1
}

check_dependencies() {
    local missing_deps=()
    
    for dep in docker docker-compose curl; do
        if ! command -v "$dep" &> /dev/null; then
            missing_deps+=("$dep")
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        return 1
    fi
    
    log_info "All dependencies available"
}

# Rollback functions
rollback_docker() {
    local compose_file="${1:-docker-compose.yml}"
    local backup_tag="${2:-previous}"
    
    log_warn "Rolling back to: $backup_tag"
    docker-compose -f "$compose_file" pull "$backup_tag"
    docker-compose -f "$compose_file" up -d
}

# Monitoring
show_logs() {
    local service="${1:-}"
    local lines="${2:-100}"
    
    if [[ -n "$service" ]]; then
        docker-compose logs --tail="$lines" "$service"
    else
        docker-compose logs --tail="$lines"
    fi
}

show_stats() {
    log_info "Container Stats:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
    
    log_info "Disk Usage:"
    df -h "$PROJECT_ROOT" | tail -1
    
    log_info "Memory Usage:"
    free -h | grep Mem
}

# Cleanup
cleanup_old_backups() {
    local days="${1:-7}"
    log_info "Cleaning up backups older than $days days..."
    find "$BACKUP_DIR" -name "*.gz" -mtime "+$days" -delete
    find "$LOG_DIR" -name "*.log" -mtime "+$days" -delete
    log_success "Cleanup complete"
}

cleanup_docker() {
    log_info "Cleaning up Docker resources..."
    docker system prune -f
    docker image prune -f
    log_success "Docker cleanup complete"
}

# Build matrix
build_all_platforms() {
    log_info "Building for all platforms..."
    
    docker buildx create --name sc2-builder || true
    docker buildx use sc2-builder
    
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        -t "sc2_wicked_bot:multi" \
        --push \
        "$PROJECT_ROOT"
    
    log_success "Multi-platform build complete"
}

# CI/CD helpers
ci_build() {
    log_info "Running CI build..."
    
    check_dependencies
    docker_build "sc2_wicked_bot" "${GIT_COMMIT:-latest}"
    
    log_success "CI build complete"
}

ci_test() {
    log_info "Running tests..."
    
    docker-compose -f docker-compose.test.yml up --abort-on-container-exit
    
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        log_success "Tests passed"
    else
        log_error "Tests failed"
    fi
    
    return $exit_code
}

ci_deploy() {
    log_info "CI deployment..."
    
    local version
    version=$(update_version patch)
    
    backup_configs
    backup_database
    
    deploy_docker_compose
    health_check
    
    log_success "Deployed version: $version"
}

# Help
show_help() {
    cat << EOF
🎮 StarCraft II AI Bot - Deployment Script

Usage: $0 <command> [options]

Commands:
    build           Build Docker image
    push            Push image to registry
    deploy          Deploy to production
    rollback        Rollback to previous version
    backup          Create backups
    health          Run health check
    logs            Show container logs
    stats           Show container stats
    cleanup         Clean up old backups and Docker resources
    test            Run tests
    ci-build        CI build
    ci-deploy       CI deployment
    build-multi     Build for multiple platforms

Options:
    -e, --env       Environment (production/staging)
    -v, --version   Bump version (major/minor/patch)
    -h, --help      Show this help

Examples:
    $0 build
    $0 deploy -e production
    $0 ci-deploy
    $0 rollback

EOF
}

# Main
main() {
    init_dirs
    
    if [[ $# -eq 0 ]]; then
        show_help
        exit 0
    fi
    
    case "$1" in
        build)
            docker_build "${2:-sc2_wicked_bot}" "${3:-latest}"
            ;;
        push)
            docker_push "${2:-sc2_wicked_bot}" "${3:-}" "${4:-latest}"
            ;;
        deploy)
            deploy_docker_compose "${2:-docker-compose.yml}"
            health_check
            ;;
        rollback)
            rollback_docker "${2:-docker-compose.yml}" "${3:-previous}"
            ;;
        backup)
            backup_configs
            backup_database
            ;;
        health)
            health_check "${2:-http://localhost:5000/health}"
            ;;
        logs)
            show_logs "${2:-}" "${3:-100}"
            ;;
        stats)
            show_stats
            ;;
        cleanup)
            cleanup_old_backups "${2:-7}"
            cleanup_docker
            ;;
        test)
            ci_test
            ;;
        ci-build)
            ci_build
            ;;
        ci-deploy)
            ci_deploy
            ;;
        build-multi)
            build_all_platforms
            ;;
        version)
            get_version
            ;;
        bump)
            update_version "${2:-patch}"
            ;;
        -h|--help)
            show_help
            ;;
        *)
            log_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
