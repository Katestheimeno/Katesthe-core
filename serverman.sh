#!/bin/bash
# =========================================
# Server Deployment Manager
# =========================================
# A flexible deployment automation tool for containerized applications
#
# Usage:
#   serverman [command] [options]
#
# First run requires configuration setup
# =========================================

set -eo pipefail  # Exit on error, fail on pipe errors
IFS=$'\n\t'       # Better word splitting

# Script metadata
SCRIPT_VERSION="2.1.0"
SCRIPT_NAME="ServerMan"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration paths
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/serverman"
CONFIG_FILE="$CONFIG_DIR/serverman.conf"
LOCK_FILE="/tmp/serverman.lock"

# Default configuration values
DEFAULT_COMPOSE_FILE="docker-compose.prod.yml"
DEFAULT_ENV_FILE="service/.env.prod"
DEFAULT_PROJECT_NAME="production"
DEFAULT_BACKUP_DIR="backups"
DEFAULT_BACKUP_RETENTION=10
DEFAULT_HEALTH_CHECK_TIMEOUT=30
DEFAULT_SERVICE_READY_WAIT=15

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly MAGENTA='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color
readonly BOLD='\033[1m'

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  [INFO]${NC} $*" >&2
}

log_success() {
    echo -e "${GREEN}✅ [SUCCESS]${NC} $*" >&2
}

log_warning() {
    echo -e "${YELLOW}⚠️  [WARNING]${NC} $*" >&2
}

log_error() {
    echo -e "${RED}❌ [ERROR]${NC} $*" >&2
}

log_debug() {
    if [[ "${DEBUG:-0}" == "1" ]]; then
        echo -e "${MAGENTA}🔍 [DEBUG]${NC} $*" >&2
    fi
}

log_step() {
    echo -e "${CYAN}${BOLD}▶ $*${NC}" >&2
}

# Error handler
error_exit() {
    log_error "$1"
    cleanup
    exit "${2:-1}"
}

# Cleanup function
cleanup() {
    if [[ -f "$LOCK_FILE" ]]; then
        rm -f "$LOCK_FILE"
    fi
}

# Trap errors and interrupts
trap 'error_exit "Script interrupted" 130' INT TERM
trap 'cleanup' EXIT

# Lock mechanism to prevent concurrent runs
acquire_lock() {
    if [[ -f "$LOCK_FILE" ]]; then
        local pid
        pid=$(cat "$LOCK_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            error_exit "Another instance is already running (PID: $pid)"
        else
            log_warning "Removing stale lock file"
            rm -f "$LOCK_FILE"
        fi
    fi
    echo $$ > "$LOCK_FILE"
}

# Check if configuration exists
require_config() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Configuration file not found!"
        echo ""
        log_info "ServerMan requires initial setup before use."
        log_info "Please run: ${BOLD}serverman setup${NC}"
        echo ""
        exit 1
    fi
}

# Configuration management
create_default_config() {
    mkdir -p "$CONFIG_DIR"
    
    local project_root compose_file env_file project_name backup_dir
    
    # Prompt for project root directory
    echo ""
    log_step "ServerMan Configuration Setup"
    echo ""
    log_info "This will create a configuration file at: $CONFIG_FILE"
    echo ""
    
    while true; do
        read -rp "Enter the absolute path to your project root directory: " project_root
        
        # Expand tilde and resolve path
        project_root="${project_root/#\~/$HOME}"
        project_root="$(cd "$project_root" 2>/dev/null && pwd)" || {
            log_error "Directory does not exist or is not accessible: $project_root"
            continue
        }
        
        if [[ ! -d "$project_root" ]]; then
            log_error "Directory does not exist: $project_root"
            continue
        fi
        
        log_success "Project root: $project_root"
        break
    done
    
    echo ""
    log_info "The following paths are relative to the project root"
    echo ""
    
    read -rp "Docker Compose file (relative path) [$DEFAULT_COMPOSE_FILE]: " compose_file
    compose_file="${compose_file:-$DEFAULT_COMPOSE_FILE}"
    
    read -rp "Environment file (relative path) [$DEFAULT_ENV_FILE]: " env_file
    env_file="${env_file:-$DEFAULT_ENV_FILE}"
    
    read -rp "Project name [$DEFAULT_PROJECT_NAME]: " project_name
    project_name="${project_name:-$DEFAULT_PROJECT_NAME}"
    
    read -rp "Backup directory (relative path) [$DEFAULT_BACKUP_DIR]: " backup_dir
    backup_dir="${backup_dir:-$DEFAULT_BACKUP_DIR}"
    
    # Validate that compose file exists
    if [[ ! -f "$project_root/$compose_file" ]]; then
        log_warning "Docker Compose file not found at: $project_root/$compose_file"
        read -rp "Continue anyway? (yes/no): " continue_setup
        if [[ "$continue_setup" != "yes" ]]; then
            log_error "Setup cancelled"
            exit 1
        fi
    fi
    
    cat > "$CONFIG_FILE" << EOF
# ServerMan Configuration File
# Created: $(date)

# CRITICAL: Absolute path to project root directory
PROJECT_ROOT="$project_root"

# Docker Compose settings (relative to PROJECT_ROOT)
COMPOSE_FILE="$compose_file"
ENV_FILE="$env_file"
PROJECT_NAME="$project_name"

# Backup settings (relative to PROJECT_ROOT)
BACKUP_DIR="$backup_dir"
BACKUP_RETENTION=$DEFAULT_BACKUP_RETENTION
BACKUP_BEFORE_UPDATE=true

# Timing settings (seconds)
SERVICE_READY_WAIT=$DEFAULT_SERVICE_READY_WAIT
HEALTH_CHECK_TIMEOUT=$DEFAULT_HEALTH_CHECK_TIMEOUT
MIGRATION_TIMEOUT=300

# Service-specific settings
WEB_SERVICE="web"
WORKER_SERVICE="celery_worker"
SCHEDULER_SERVICE="celery_beat"
DB_SERVICE="db"
CACHE_SERVICE="redis"

# Monitoring settings
MONITORING_ENABLED=false
FLOWER_PORT=5555

# Email notification settings (optional)
EMAIL_NOTIFICATIONS=false
EMAIL_TO=""
EMAIL_FROM=""
EMAIL_SMTP_HOST=""
EMAIL_SMTP_PORT="587"
EMAIL_SMTP_USER=""
EMAIL_SMTP_PASSWORD=""
EMAIL_USE_TLS=true

# Advanced settings
AUTO_CLEANUP_IMAGES=true
ZERO_DOWNTIME_DEPLOY=true
VERBOSE_LOGGING=false
DEBUG=0
EOF
    
    chmod 600 "$CONFIG_FILE"
    log_success "Configuration saved to: $CONFIG_FILE"
    echo ""
    log_info "You can edit this file anytime with: serverman edit-config"
    log_info "ServerMan will always operate in: $project_root"
}

load_config() {
    require_config
    
    # Source the configuration
    # shellcheck source=/dev/null
    source "$CONFIG_FILE"
    
    # Validate PROJECT_ROOT exists
    if [[ -z "${PROJECT_ROOT:-}" ]]; then
        error_exit "PROJECT_ROOT not defined in configuration file"
    fi
    
    if [[ ! -d "$PROJECT_ROOT" ]]; then
        error_exit "PROJECT_ROOT directory does not exist: $PROJECT_ROOT"
    fi
    
    log_debug "Configuration loaded from: $CONFIG_FILE"
    log_debug "Working in project root: $PROJECT_ROOT"
    
    # Change to project root directory
    cd "$PROJECT_ROOT" || error_exit "Failed to change to project root: $PROJECT_ROOT"
    
    # Validate required files
    validate_environment
}

validate_environment() {
    local errors=0
    
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "Docker Compose file not found: $PROJECT_ROOT/$COMPOSE_FILE"
        errors=$((errors + 1))
    fi
    
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "Environment file not found: $PROJECT_ROOT/$ENV_FILE"
        log_info "Create it from template: cp $PROJECT_ROOT/${ENV_FILE}.example $PROJECT_ROOT/${ENV_FILE}"
        errors=$((errors + 1))
    fi
    
    if [[ $errors -gt 0 ]]; then
        error_exit "Environment validation failed with $errors error(s)"
    fi
    
    log_debug "Environment validation passed"
}

# Interactive configuration setup
interactive_setup() {
    if [[ -f "$CONFIG_FILE" ]]; then
        log_warning "Configuration file already exists: $CONFIG_FILE"
        read -rp "Do you want to reconfigure? This will overwrite existing config (yes/no): " reconfigure
        if [[ "$reconfigure" != "yes" ]]; then
            log_info "Setup cancelled"
            exit 0
        fi
    fi
    
    create_default_config
    
    echo ""
    log_success "Setup complete! You can now use serverman from anywhere."
    echo ""
    log_info "Try: serverman status"
}

# Docker Compose wrapper with common options
dc() {
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" "$@"
}

# Build Docker images
cmd_build() {
    log_step "Building Docker images"
    
    local build_args=()
    
    if [[ "${1:-}" == "--no-cache" ]]; then
        build_args+=("--no-cache")
        log_info "Building without cache"
    fi
    
    dc build "${build_args[@]}"
    log_success "Docker images built successfully"
    
    if [[ "${AUTO_CLEANUP_IMAGES:-true}" == "true" ]]; then
        log_info "Cleaning up dangling images..."
        docker image prune -f
    fi
}

# Start all services
cmd_start() {
    log_step "Starting services"
    
    dc up -d
    
    log_info "Waiting for services to be ready (${SERVICE_READY_WAIT}s)..."
    sleep "$SERVICE_READY_WAIT"
    
    log_success "Services started successfully"
    cmd_status
}

# Stop all services
cmd_stop() {
    log_step "Stopping services"
    
    dc down
    
    log_success "Services stopped successfully"
}

# Restart services
cmd_restart() {
    log_step "Restarting services"
    
    if [[ -n "${1:-}" ]]; then
        log_info "Restarting service: $1"
        dc restart "$1"
    else
        dc restart
    fi
    
    log_success "Services restarted successfully"
    cmd_status
}

# View logs
cmd_logs() {
    local service="${1:-}"
    local follow_flag="-f"
    local tail_lines="100"
    
    if [[ "$service" == "--no-follow" ]]; then
        follow_flag=""
        service="${2:-}"
    fi
    
    log_info "Viewing logs (Ctrl+C to exit)"
    
    if [[ -n "$service" ]]; then
        dc logs $follow_flag --tail="$tail_lines" "$service"
    else
        dc logs $follow_flag --tail="$tail_lines"
    fi
}

# Check service status
cmd_status() {
    log_step "Service Status"
    echo ""
    log_info "Project: $PROJECT_ROOT"
    echo ""
    dc ps
    
    echo ""
    log_info "Quick health summary:"
    
    # Count running vs total services
    local total running
    total=$(dc ps -q 2>/dev/null | wc -l)
    running=$(dc ps --filter "status=running" -q 2>/dev/null | wc -l)
    
    if [[ $running -eq $total ]] && [[ $total -gt 0 ]]; then
        echo -e "${GREEN}● All services running ($running/$total)${NC}"
    elif [[ $running -gt 0 ]]; then
        echo -e "${YELLOW}◐ Partially running ($running/$total)${NC}"
    else
        echo -e "${RED}○ No services running${NC}"
    fi
}

# Run database migrations
cmd_migrate() {
    log_step "Running database migrations"
    
    if ! dc ps "$WEB_SERVICE" 2>/dev/null | grep -q "Up"; then
        error_exit "Web service is not running. Start services first."
    fi
    
    dc exec -T "$WEB_SERVICE" python service/manage.py migrate --noinput
    
    log_success "Migrations completed successfully"
}

# Collect static files
cmd_collect_static() {
    log_step "Collecting static files"
    
    dc exec -T "$WEB_SERVICE" python service/manage.py collectstatic --noinput --clear
    
    log_success "Static files collected successfully"
}

# Create backup
cmd_backup() {
    log_step "Creating database backup"
    
    local backup_name="${1:-backup_$(date +%Y%m%d_%H%M%S)}"
    local backup_script="$PROJECT_ROOT/scripts/backup-database.sh"
    
    if [[ -x "$backup_script" ]]; then
        "$backup_script" "$backup_name"
    else
        log_warning "Backup script not found or not executable: $backup_script"
        
        # Fallback: simple pg_dump
        mkdir -p "$BACKUP_DIR"
        local backup_file="$BACKUP_DIR/${backup_name}.sql.gz"
        
        log_info "Creating backup: $backup_file"
        dc exec -T "$DB_SERVICE" pg_dump -U postgres 2>/dev/null | gzip > "$backup_file"
        
        log_success "Backup created: $backup_file"
    fi
    
    # Cleanup old backups
    cleanup_old_backups
}

cleanup_old_backups() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        return
    fi
    
    local backup_count
    backup_count=$(find "$BACKUP_DIR" -name "*.sql.gz" -type f 2>/dev/null | wc -l)
    
    if [[ $backup_count -gt ${BACKUP_RETENTION:-10} ]]; then
        log_info "Cleaning up old backups (keeping last ${BACKUP_RETENTION:-10})"
        find "$BACKUP_DIR" -name "*.sql.gz" -type f -printf '%T@ %p\n' 2>/dev/null | \
            sort -n | head -n -"${BACKUP_RETENTION:-10}" | cut -d' ' -f2- | \
            xargs -r rm -v
    fi
}

# Full deployment
cmd_deploy() {
    log_step "Starting Full Deployment"
    log_info "Target: $PROJECT_ROOT"
    echo ""
    
    acquire_lock
    
    cmd_build
    
    log_info "Starting services..."
    dc up -d
    
    log_info "Waiting for services to be ready (${SERVICE_READY_WAIT}s)..."
    sleep "$SERVICE_READY_WAIT"
    
    cmd_migrate
    cmd_collect_static
    
    log_info "Restarting web service..."
    dc restart "$WEB_SERVICE"
    
    sleep 5
    
    log_success "Full deployment completed successfully!"
    cmd_status
    
    echo ""
    log_info "Next steps:"
    echo "  • Create superuser: serverman superuser"
    echo "  • Check health: serverman health"
    echo "  • View logs: serverman logs"
    echo "  • Monitor services: serverman monitor"
    
    send_notification "✅ Deployment completed successfully for $PROJECT_NAME"
}

# Update deployment with zero downtime
cmd_update() {
    log_step "Starting Deployment Update"
    log_info "Target: $PROJECT_ROOT"
    echo ""
    
    acquire_lock
    
    # Create pre-update backup
    if [[ "${BACKUP_BEFORE_UPDATE:-true}" == "true" ]]; then
        log_info "Creating pre-update backup..."
        cmd_backup "pre_update_$(date +%Y%m%d_%H%M%S)" || {
            log_error "Backup failed!"
            read -rp "Continue without backup? (yes/no): " continue_anyway
            if [[ "$continue_anyway" != "yes" ]]; then
                error_exit "Update cancelled by user"
            fi
        }
    fi
    
    # Pull latest changes if in git repo
    if [[ -d "$PROJECT_ROOT/.git" ]]; then
        log_info "Pulling latest changes..."
        git pull origin main || log_warning "Git pull failed or not on main branch"
    fi
    
    cmd_build
    
    if [[ "${ZERO_DOWNTIME_DEPLOY:-true}" == "true" ]]; then
        log_info "Performing zero-downtime deployment..."
        dc up -d --no-deps --build "$WEB_SERVICE"
    else
        log_info "Restarting all services..."
        dc up -d --build
    fi
    
    log_info "Waiting for new containers (${SERVICE_READY_WAIT}s)..."
    sleep "$SERVICE_READY_WAIT"
    
    cmd_migrate
    cmd_collect_static
    
    log_info "Restarting worker services..."
    dc restart "$WORKER_SERVICE" "$SCHEDULER_SERVICE" 2>/dev/null || true
    
    log_success "Deployment update completed successfully!"
    cmd_status
    
    send_notification "✅ Deployment update completed successfully for $PROJECT_NAME"
}

# Start with monitoring
cmd_monitor() {
    log_step "Starting services with monitoring"
    
    if [[ "${MONITORING_ENABLED:-false}" != "true" ]]; then
        log_warning "Monitoring not enabled in config. Enabling temporarily..."
    fi
    
    dc --profile monitoring up -d
    
    log_success "Services started with monitoring"
    log_info "Flower dashboard: http://localhost:${FLOWER_PORT:-5555}"
    
    cmd_status
}

# Create superuser
cmd_superuser() {
    log_step "Creating Django superuser"
    
    dc exec "$WEB_SERVICE" python service/manage.py createsuperuser
}

# Health checks
cmd_health() {
    log_step "Running Health Checks"
    log_info "Project: $PROJECT_ROOT"
    
    local health_ok=true
    
    # Check if services are running
    echo ""
    log_info "Checking service status..."
    if ! dc ps --filter "status=running" 2>/dev/null | grep -q "$WEB_SERVICE"; then
        log_error "Web service is not running"
        health_ok=false
    else
        log_success "Web service is running"
    fi
    
    # Django system check
    echo ""
    log_info "Running Django system checks..."
    if dc exec -T "$WEB_SERVICE" python service/manage.py check --deploy 2>&1 | grep -q "no issues"; then
        log_success "Django system check passed"
    else
        log_warning "Django system check reported issues"
        health_ok=false
    fi
    
    # Database connectivity
    echo ""
    log_info "Checking database connection..."
    if dc exec -T "$WEB_SERVICE" python -c "
import django
django.setup()
from django.db import connection
connection.ensure_connection()
print('OK')
" 2>/dev/null | grep -q "OK"; then
        log_success "Database connection successful"
    else
        log_error "Database connection failed"
        health_ok=false
    fi
    
    # Check Celery workers
    echo ""
    log_info "Checking Celery workers..."
    if dc exec -T "$WORKER_SERVICE" python -m celery -A config inspect ping 2>/dev/null | grep -q "pong"; then
        log_success "Celery workers responding"
    else
        log_warning "Celery workers not responding"
    fi
    
    echo ""
    if [[ "$health_ok" == "true" ]]; then
        log_success "All critical health checks passed"
        return 0
    else
        log_error "Some health checks failed"
        return 1
    fi
}

# Show migration status
cmd_migrations() {
    log_step "Migration Status"
    
    dc exec -T "$WEB_SERVICE" python service/manage.py showmigrations --list
}

# Shell access
cmd_shell() {
    local service="${1:-$WEB_SERVICE}"
    local shell_type="${2:-bash}"
    
    log_info "Opening shell in $service container..."
    
    dc exec "$service" "$shell_type"
}

# Django shell
cmd_django_shell() {
    log_info "Opening Django shell..."
    
    dc exec "$WEB_SERVICE" python service/manage.py shell
}

# Show configuration
cmd_config() {
    log_step "Current Configuration"
    echo ""
    
    if [[ -f "$CONFIG_FILE" ]]; then
        cat "$CONFIG_FILE"
    else
        log_warning "No configuration file found"
    fi
}

# Edit configuration
cmd_edit_config() {
    require_config
    
    local editor="${EDITOR:-nano}"
    
    log_info "Opening configuration file in $editor"
    "$editor" "$CONFIG_FILE"
    
    log_success "Configuration file closed"
    log_warning "Changes will take effect on next serverman command"
}

# Send email notification
send_notification() {
    local message="$1"
    
    # Check if email notifications are enabled
    if [[ "${EMAIL_NOTIFICATIONS:-false}" != "true" ]]; then
        return 0
    fi
    
    if [[ -z "${EMAIL_TO:-}" ]] || [[ -z "${EMAIL_FROM:-}" ]]; then
        log_debug "Email notifications enabled but not fully configured"
        return 0
    fi
    
    local subject="[$SCRIPT_NAME] $PROJECT_NAME"
    local body="$message\n\nProject: $PROJECT_ROOT\nTimestamp: $(date)\nHost: $(hostname)"
    
    # Try to send email using different methods
    if command -v sendmail &> /dev/null; then
        # Using sendmail
        echo -e "To: $EMAIL_TO\nFrom: $EMAIL_FROM\nSubject: $subject\n\n$body" | sendmail -t
        log_debug "Notification sent via sendmail"
    elif command -v mail &> /dev/null; then
        # Using mail command
        echo -e "$body" | mail -s "$subject" -r "$EMAIL_FROM" "$EMAIL_TO"
        log_debug "Notification sent via mail"
    elif [[ -n "${EMAIL_SMTP_HOST:-}" ]]; then
        # Using curl with SMTP
        local smtp_url="smtp://${EMAIL_SMTP_HOST}:${EMAIL_SMTP_PORT:-587}"
        
        curl --url "$smtp_url" \
            --mail-from "$EMAIL_FROM" \
            --mail-rcpt "$EMAIL_TO" \
            --user "${EMAIL_SMTP_USER}:${EMAIL_SMTP_PASSWORD}" \
            --upload-file - <<EOF
From: $EMAIL_FROM
To: $EMAIL_TO
Subject: $subject

$body
EOF
        log_debug "Notification sent via SMTP"
    else
        log_debug "No email sending method available"
    fi
}

# Clean up Docker resources
cmd_cleanup() {
    log_step "Cleaning up Docker resources"
    log_info "Project: $PROJECT_ROOT"
    echo ""
    
    log_info "Removing stopped containers..."
    docker container prune -f
    
    log_info "Removing unused images..."
    docker image prune -f
    
    log_info "Removing unused networks..."
    docker network prune -f
    
    log_info "Removing unused volumes (be careful!)..."
    read -rp "Remove unused volumes? (yes/no): " remove_volumes
    if [[ "$remove_volumes" == "yes" ]]; then
        docker volume prune -f
    fi
    
    log_success "Cleanup completed"
}

# Show help
show_help() {
    cat << EOF
${BOLD}$SCRIPT_NAME v$SCRIPT_VERSION${NC} - Server Deployment Manager

${BOLD}Usage:${NC}
  serverman [command] [options]

${BOLD}Commands:${NC}
  ${CYAN}setup${NC}           Interactive configuration setup (required first time)
  ${CYAN}build${NC}           Build Docker images (--no-cache for clean build)
  ${CYAN}start${NC}           Start all services
  ${CYAN}stop${NC}            Stop all services
  ${CYAN}restart${NC}         Restart services [service_name]
  ${CYAN}logs${NC}            View logs [service_name] (--no-follow for static)
  ${CYAN}status${NC}          Check service status
  ${CYAN}ps${NC}              Alias for status
  
  ${CYAN}migrate${NC}         Run database migrations
  ${CYAN}migrations${NC}      Show migration status
  ${CYAN}collect${NC}         Collect static files
  ${CYAN}backup${NC}          Create database backup [backup_name]
  
  ${CYAN}deploy${NC}          Full deployment (build + migrate + start)
  ${CYAN}update${NC}          Update deployment (pull + build + migrate)
  
  ${CYAN}monitor${NC}         Start with Celery Flower monitoring
  ${CYAN}superuser${NC}       Create Django superuser
  ${CYAN}health${NC}          Run health checks
  
  ${CYAN}shell${NC}           Open shell in container [service] [shell_type]
  ${CYAN}django-shell${NC}    Open Django shell
  
  ${CYAN}config${NC}          Show current configuration
  ${CYAN}edit-config${NC}     Edit configuration file
  ${CYAN}cleanup${NC}         Clean up Docker resources
  
  ${CYAN}version${NC}         Show script version
  ${CYAN}help${NC}            Show this help message

${BOLD}Examples:${NC}
  serverman setup              # Initial setup (run this first!)
  serverman deploy             # Initial deployment
  serverman update             # Update existing deployment
  serverman logs web           # View web service logs
  serverman shell celery_worker  # Shell into worker
  serverman backup pre_upgrade # Create named backup
  serverman health             # Check system health

${BOLD}Installation:${NC}
  sudo cp serverman.sh /usr/local/bin/serverman
  sudo chmod +x /usr/local/bin/serverman
  serverman setup              # Run setup to configure

${BOLD}Configuration:${NC}
  Config file: $CONFIG_FILE
  Edit config: serverman edit-config
  
  The script works from the project root defined during setup.
  You can run serverman from anywhere on the system.

${BOLD}Environment:${NC}
  DEBUG=1 serverman [command]  # Enable debug logging

For more information, visit the documentation.
EOF
}

# Main command router
main() {
    local command="${1:-help}"
    shift || true
    
    # Handle help and version flags globally (no config needed)
    case "$command" in
        -h|--help|help)
            show_help
            exit 0
            ;;
        version|--version|-v)
            echo "$SCRIPT_NAME v$SCRIPT_VERSION"
            exit 0
            ;;
        setup)
            interactive_setup
            exit 0
            ;;
    esac
    
    # All other commands require configuration
    load_config
    
    # Route to command
    case "$command" in
        build)
            cmd_build "$@"
            ;;
        start)
            cmd_start "$@"
            ;;
        stop)
            cmd_stop "$@"
            ;;
        restart)
            cmd_restart "$@"
            ;;
        logs)
            cmd_logs "$@"
            ;;
        status|ps)
            cmd_status "$@"
            ;;
        migrate)
            cmd_migrate "$@"
            ;;
        migrations)
            cmd_migrations "$@"
            ;;
        collect)
            cmd_collect_static "$@"
            ;;
        backup)
            cmd_backup "$@"
            ;;
        deploy)
            cmd_deploy "$@"
            ;;
        update)
            cmd_update "$@"
            ;;
        monitor)
            cmd_monitor "$@"
            ;;
        superuser)
            cmd_superuser "$@"
            ;;
        health)
            cmd_health "$@"
            ;;
        shell)
            cmd_shell "$@"
            ;;
        django-shell|djshell)
            cmd_django_shell "$@"
            ;;
        config)
            cmd_config "$@"
            ;;
        edit-config)
            cmd_edit_config "$@"
            ;;
        cleanup)
            cmd_cleanup "$@"
            ;;
        *)
            log_error "Unknown command: $command"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
