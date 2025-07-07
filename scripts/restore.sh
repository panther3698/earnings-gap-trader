#!/bin/bash
# Comprehensive restore script for Earnings Gap Trading System
# Restores database, configuration, and application data from backups

set -euo pipefail

# Configuration
BACKUP_BASE_DIR="/opt/backups/earnings_gap_trader"
LOG_FILE="/var/log/earnings_gap_trader/restore.log"
RESTORE_TIMESTAMP=""
BACKUP_DIR=""

# Database configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-earnings_gap_trader}"
DB_USER="${DB_USER:-trader}"
DB_PASSWORD="${DB_PASSWORD:-}"

# Redis configuration
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"

# AWS S3 configuration (optional)
S3_BUCKET="${BACKUP_S3_BUCKET:-}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Notification settings
ALERT_EMAIL="${ALERT_EMAIL:-}"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_IDS="${TELEGRAM_CHAT_IDS:-}"

# Restore options
RESTORE_DATABASE=true
RESTORE_REDIS=true
RESTORE_CONFIG=true
RESTORE_LOGS=false
RESTORE_APP_DATA=true
FORCE_RESTORE=false
DRY_RUN=false

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
handle_error() {
    local exit_code=$?
    log "ERROR: Restore failed with exit code $exit_code"
    send_alert "CRITICAL" "Restore failed" "Restore process failed with exit code $exit_code at $(date)"
    exit $exit_code
}

trap handle_error ERR

# Send alert function
send_alert() {
    local level="$1"
    local subject="$2"
    local message="$3"
    
    # Email alert
    if [[ -n "$ALERT_EMAIL" ]]; then
        echo "$message" | mail -s "[$level] Trading System Restore: $subject" "$ALERT_EMAIL" 2>/dev/null || true
    fi
    
    # Telegram alert
    if [[ -n "$TELEGRAM_BOT_TOKEN" && -n "$TELEGRAM_CHAT_IDS" ]]; then
        local telegram_message="🔄 *Trading System Restore*\n\n*Level:* $level\n*Subject:* $subject\n*Message:* $message"
        
        IFS=',' read -ra CHAT_IDS <<< "$TELEGRAM_CHAT_IDS"
        for chat_id in "${CHAT_IDS[@]}"; do
            curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
                -d "chat_id=$chat_id" \
                -d "text=$telegram_message" \
                -d "parse_mode=Markdown" > /dev/null 2>&1 || true
        done
    fi
}

# Show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS] BACKUP_TIMESTAMP

Restore Earnings Gap Trading System from backup

ARGUMENTS:
    BACKUP_TIMESTAMP    Timestamp of backup to restore (YYYYMMDD_HHMMSS)
                       Use 'latest' to restore from the most recent backup
                       Use 'list' to show available backups

OPTIONS:
    -h, --help         Show this help message
    -d, --database     Restore database only
    -r, --redis        Restore Redis only
    -c, --config       Restore configuration only
    -l, --logs         Restore logs only
    -a, --app-data     Restore application data only
    --no-database      Skip database restore
    --no-redis         Skip Redis restore
    --no-config        Skip configuration restore
    --no-app-data      Skip application data restore
    -f, --force        Force restore without confirmation
    --dry-run          Show what would be restored without actually doing it
    --from-s3          Download backup from S3 before restoring

EXAMPLES:
    $0 20240115_143022                    # Restore specific backup
    $0 latest                             # Restore latest backup
    $0 --database latest                  # Restore only database from latest backup
    $0 --dry-run latest                   # Show what would be restored
    $0 --from-s3 --force 20240115_143022  # Download from S3 and restore without confirmation

EOF
}

# List available backups
list_backups() {
    log "Available backups:"
    
    # Local backups
    echo "Local backups:"
    find "$BACKUP_BASE_DIR" -maxdepth 1 -type d -name "20*" | sort -r | head -10 | while read -r backup_path; do
        local timestamp=$(basename "$backup_path")
        local backup_date=$(date -d "${timestamp:0:8} ${timestamp:9:2}:${timestamp:11:2}:${timestamp:13:2}" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "Invalid date")
        local size=$(du -sh "$backup_path" 2>/dev/null | cut -f1 || echo "Unknown")
        echo "  $timestamp - $backup_date ($size)"
    done
    
    # S3 backups (if configured)
    if [[ -n "$S3_BUCKET" ]] && command -v aws &> /dev/null; then
        echo ""
        echo "S3 backups:"
        aws s3 ls "s3://$S3_BUCKET/backups/" --region "$AWS_REGION" 2>/dev/null | \
        grep "backup_[0-9]" | sort -r | head -10 | while read -r line; do
            local backup_file=$(echo "$line" | awk '{print $4}')
            local timestamp=$(echo "$backup_file" | sed 's/backup_\([0-9]\{8\}_[0-9]\{6\}\).*/\1/')
            local size=$(echo "$line" | awk '{print $3}')
            local backup_date=$(date -d "${timestamp:0:8} ${timestamp:9:2}:${timestamp:11:2}:${timestamp:13:2}" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "Invalid date")
            echo "  $timestamp - $backup_date ($(numfmt --to=iec $size))"
        done
    fi
}

# Download backup from S3
download_from_s3() {
    local timestamp="$1"
    
    if [[ -z "$S3_BUCKET" ]]; then
        log "ERROR: S3 bucket not configured"
        exit 1
    fi
    
    if ! command -v aws &> /dev/null; then
        log "ERROR: AWS CLI not found"
        exit 1
    fi
    
    log "Downloading backup from S3..."
    
    local backup_archive="${BACKUP_BASE_DIR}/backup_${timestamp}.tar.gz"
    local s3_path="s3://$S3_BUCKET/backups/backup_${timestamp}.tar.gz"
    
    aws s3 cp "$s3_path" "$backup_archive" --region "$AWS_REGION" >> "$LOG_FILE" 2>&1
    
    if [[ $? -eq 0 ]]; then
        log "Download completed: $backup_archive"
        
        # Extract the backup
        log "Extracting backup archive..."
        tar -xzf "$backup_archive" -C "$BACKUP_BASE_DIR"
        
        # Remove the archive
        rm -f "$backup_archive"
        
        log "Backup extracted successfully"
    else
        log "ERROR: Failed to download backup from S3"
        exit 1
    fi
}

# Get latest backup timestamp
get_latest_backup() {
    local latest_backup
    latest_backup=$(find "$BACKUP_BASE_DIR" -maxdepth 1 -type d -name "20*" | sort -r | head -1)
    
    if [[ -n "$latest_backup" ]]; then
        basename "$latest_backup"
    else
        log "ERROR: No backups found"
        exit 1
    fi
}

# Verify backup integrity
verify_backup() {
    local backup_dir="$1"
    
    log "Verifying backup integrity..."
    
    # Check if manifest exists
    local manifest_file="${backup_dir}/MANIFEST.json"
    if [[ ! -f "$manifest_file" ]]; then
        log "WARNING: Backup manifest not found"
        return 0
    fi
    
    # Verify checksums if available
    if command -v jq &> /dev/null; then
        local checksums
        checksums=$(jq -r '.checksums | to_entries[] | "\(.key) \(.value)"' "$manifest_file" 2>/dev/null || echo "")
        
        if [[ -n "$checksums" ]]; then
            log "Verifying file checksums..."
            echo "$checksums" | while read -r filename expected_checksum; do
                local file_path
                file_path=$(find "$backup_dir" -name "$filename" -type f | head -1)
                
                if [[ -f "$file_path" ]]; then
                    local actual_checksum
                    actual_checksum=$(sha256sum "$file_path" | cut -d' ' -f1)
                    
                    if [[ "$actual_checksum" == "$expected_checksum" ]]; then
                        log "✓ Checksum verified: $filename"
                    else
                        log "✗ Checksum mismatch: $filename"
                        return 1
                    fi
                else
                    log "✗ File not found: $filename"
                    return 1
                fi
            done
        fi
    fi
    
    log "Backup verification completed"
}

# Stop services
stop_services() {
    log "Stopping services..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would stop trading system services"
        return 0
    fi
    
    # Stop trading system services
    systemctl stop earnings-gap-trader.service 2>/dev/null || true
    systemctl stop earnings-gap-trader-worker.service 2>/dev/null || true
    systemctl stop earnings-gap-trader-scheduler.service 2>/dev/null || true
    
    log "Services stopped"
}

# Start services
start_services() {
    log "Starting services..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would start trading system services"
        return 0
    fi
    
    # Start trading system services
    systemctl start earnings-gap-trader.service
    systemctl start earnings-gap-trader-worker.service
    systemctl start earnings-gap-trader-scheduler.service
    
    # Wait for services to be ready
    sleep 10
    
    # Check service status
    if systemctl is-active --quiet earnings-gap-trader.service; then
        log "✓ Main service started successfully"
    else
        log "✗ Main service failed to start"
        return 1
    fi
    
    log "Services started successfully"
}

# Restore database
restore_database() {
    local backup_dir="$1"
    
    log "Starting database restore..."
    
    local db_backup_file
    db_backup_file=$(find "$backup_dir/database" -name "*.sql.gz" -type f | head -1)
    
    if [[ -z "$db_backup_file" ]]; then
        log "ERROR: Database backup file not found"
        return 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would restore database from: $db_backup_file"
        return 0
    fi
    
    # Set password for psql
    export PGPASSWORD="$DB_PASSWORD"
    
    # Drop existing database (if exists) and recreate
    log "Recreating database..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres << EOF >> "$LOG_FILE" 2>&1
DROP DATABASE IF EXISTS $DB_NAME;
CREATE DATABASE $DB_NAME OWNER $DB_USER;
EOF
    
    # Restore database
    log "Restoring database from backup..."
    zcat "$db_backup_file" | pg_restore \
        --host="$DB_HOST" \
        --port="$DB_PORT" \
        --username="$DB_USER" \
        --dbname="$DB_NAME" \
        --verbose \
        --clean \
        --if-exists \
        --no-owner \
        --no-privileges >> "$LOG_FILE" 2>&1
    
    unset PGPASSWORD
    
    log "Database restore completed"
}

# Restore Redis data
restore_redis() {
    local backup_dir="$1"
    
    log "Starting Redis restore..."
    
    local redis_backup_file
    redis_backup_file=$(find "$backup_dir/redis" -name "*.rdb.gz" -type f | head -1)
    
    if [[ -z "$redis_backup_file" ]]; then
        log "WARNING: Redis backup file not found"
        return 0
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would restore Redis from: $redis_backup_file"
        return 0
    fi
    
    # Stop Redis service
    log "Stopping Redis service..."
    systemctl stop redis-server 2>/dev/null || systemctl stop redis 2>/dev/null || true
    
    # Backup current Redis data
    local redis_data_dir="/var/lib/redis"
    if [[ -f "$redis_data_dir/dump.rdb" ]]; then
        mv "$redis_data_dir/dump.rdb" "$redis_data_dir/dump.rdb.backup.$(date +%s)"
    fi
    
    # Restore Redis dump file
    log "Restoring Redis data..."
    zcat "$redis_backup_file" > "$redis_data_dir/dump.rdb"
    chown redis:redis "$redis_data_dir/dump.rdb" 2>/dev/null || true
    
    # Start Redis service
    log "Starting Redis service..."
    systemctl start redis-server 2>/dev/null || systemctl start redis 2>/dev/null
    
    # Wait for Redis to be ready
    sleep 5
    
    # Verify Redis is working
    if [[ -n "$REDIS_PASSWORD" ]]; then
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" ping >> "$LOG_FILE" 2>&1
    else
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >> "$LOG_FILE" 2>&1
    fi
    
    log "Redis restore completed"
}

# Restore configuration
restore_config() {
    local backup_dir="$1"
    
    log "Starting configuration restore..."
    
    local config_backup_file
    config_backup_file=$(find "$backup_dir/config" -name "*.tar.gz" -type f | head -1)
    
    if [[ -z "$config_backup_file" ]]; then
        log "ERROR: Configuration backup file not found"
        return 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would restore configuration from: $config_backup_file"
        return 0
    fi
    
    # Backup current configuration
    local config_backup_current="/opt/earnings_gap_trader/config_backup_$(date +%s).tar.gz"
    log "Backing up current configuration to: $config_backup_current"
    tar -czf "$config_backup_current" -C /opt/earnings_gap_trader config/ systemd/ 2>/dev/null || true
    
    # Restore configuration
    log "Restoring configuration..."
    tar -xzf "$config_backup_file" -C /opt/earnings_gap_trader --overwrite >> "$LOG_FILE" 2>&1
    
    # Set proper permissions
    chown -R trader:trader /opt/earnings_gap_trader/config/ 2>/dev/null || true
    chmod 640 /opt/earnings_gap_trader/config/.env* 2>/dev/null || true
    
    log "Configuration restore completed"
}

# Restore logs
restore_logs() {
    local backup_dir="$1"
    
    log "Starting log restore..."
    
    local logs_backup_file
    logs_backup_file=$(find "$backup_dir/logs" -name "*.tar.gz" -type f | head -1)
    
    if [[ -z "$logs_backup_file" ]]; then
        log "WARNING: Log backup file not found"
        return 0
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would restore logs from: $logs_backup_file"
        return 0
    fi
    
    # Create logs directory if it doesn't exist
    mkdir -p /var/log/earnings_gap_trader_restored
    
    # Restore logs to a separate directory to avoid conflicts
    log "Restoring logs to /var/log/earnings_gap_trader_restored..."
    tar -xzf "$logs_backup_file" -C /var/log/earnings_gap_trader_restored --strip-components=1 >> "$LOG_FILE" 2>&1
    
    log "Log restore completed"
}

# Restore application data
restore_app_data() {
    local backup_dir="$1"
    
    log "Starting application data restore..."
    
    local data_backup_file
    data_backup_file=$(find "$backup_dir/data" -name "*.tar.gz" -type f | head -1)
    
    if [[ -z "$data_backup_file" ]]; then
        log "ERROR: Application data backup file not found"
        return 1
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would restore application data from: $data_backup_file"
        return 0
    fi
    
    # Backup current application data
    local app_backup_current="/opt/earnings_gap_trader/app_backup_$(date +%s).tar.gz"
    log "Backing up current application data to: $app_backup_current"
    tar -czf "$app_backup_current" -C /opt/earnings_gap_trader app/ scripts/ 2>/dev/null || true
    
    # Restore application data
    log "Restoring application data..."
    tar -xzf "$data_backup_file" -C /opt/earnings_gap_trader --overwrite >> "$LOG_FILE" 2>&1
    
    # Set proper permissions
    chown -R trader:trader /opt/earnings_gap_trader/app/ /opt/earnings_gap_trader/scripts/ 2>/dev/null || true
    chmod +x /opt/earnings_gap_trader/scripts/*.sh 2>/dev/null || true
    
    log "Application data restore completed"
}

# Confirm restore
confirm_restore() {
    if [[ "$FORCE_RESTORE" == "true" ]]; then
        return 0
    fi
    
    echo ""
    echo "=========================================="
    echo "RESTORE CONFIRMATION"
    echo "=========================================="
    echo "Backup to restore: $RESTORE_TIMESTAMP"
    echo "Backup directory: $BACKUP_DIR"
    echo ""
    echo "Components to restore:"
    [[ "$RESTORE_DATABASE" == "true" ]] && echo "  ✓ Database"
    [[ "$RESTORE_REDIS" == "true" ]] && echo "  ✓ Redis"
    [[ "$RESTORE_CONFIG" == "true" ]] && echo "  ✓ Configuration"
    [[ "$RESTORE_LOGS" == "true" ]] && echo "  ✓ Logs"
    [[ "$RESTORE_APP_DATA" == "true" ]] && echo "  ✓ Application Data"
    echo ""
    echo "WARNING: This will overwrite existing data!"
    echo ""
    read -p "Are you sure you want to proceed? (yes/no): " -r
    
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log "Restore cancelled by user"
        exit 0
    fi
}

# Main restore function
main() {
    local timestamp="$1"
    
    log "Starting restore process for backup: $timestamp"
    
    # Check if restore is already running
    local lock_file="/var/run/earnings_gap_trader_restore.lock"
    if [[ -f "$lock_file" ]]; then
        log "ERROR: Restore already running (lock file exists)"
        exit 1
    fi
    
    # Create lock file
    echo $$ > "$lock_file"
    trap "rm -f $lock_file" EXIT
    
    # Handle special timestamps
    if [[ "$timestamp" == "latest" ]]; then
        timestamp=$(get_latest_backup)
        log "Using latest backup: $timestamp"
    fi
    
    RESTORE_TIMESTAMP="$timestamp"
    BACKUP_DIR="${BACKUP_BASE_DIR}/${timestamp}"
    
    # Check if backup exists locally
    if [[ ! -d "$BACKUP_DIR" ]]; then
        if [[ "$DOWNLOAD_FROM_S3" == "true" ]]; then
            download_from_s3 "$timestamp"
        else
            log "ERROR: Backup directory not found: $BACKUP_DIR"
            log "Use --from-s3 to download from S3 or check available backups with 'list'"
            exit 1
        fi
    fi
    
    # Verify backup
    verify_backup "$BACKUP_DIR"
    
    # Confirm restore
    confirm_restore
    
    # Send start notification
    send_alert "INFO" "Restore started" "Restore process started for backup $timestamp at $(date)"
    
    # Stop services before restore
    stop_services
    
    # Perform restores based on options
    if [[ "$RESTORE_DATABASE" == "true" ]]; then
        restore_database "$BACKUP_DIR"
    fi
    
    if [[ "$RESTORE_REDIS" == "true" ]]; then
        restore_redis "$BACKUP_DIR"
    fi
    
    if [[ "$RESTORE_CONFIG" == "true" ]]; then
        restore_config "$BACKUP_DIR"
    fi
    
    if [[ "$RESTORE_LOGS" == "true" ]]; then
        restore_logs "$BACKUP_DIR"
    fi
    
    if [[ "$RESTORE_APP_DATA" == "true" ]]; then
        restore_app_data "$BACKUP_DIR"
    fi
    
    # Start services after restore
    if [[ "$DRY_RUN" != "true" ]]; then
        start_services
    fi
    
    log "Restore process completed successfully"
    
    # Send success notification
    send_alert "INFO" "Restore completed" "Restore process completed successfully for backup $timestamp at $(date)"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -d|--database)
            RESTORE_DATABASE=true
            RESTORE_REDIS=false
            RESTORE_CONFIG=false
            RESTORE_LOGS=false
            RESTORE_APP_DATA=false
            shift
            ;;
        -r|--redis)
            RESTORE_DATABASE=false
            RESTORE_REDIS=true
            RESTORE_CONFIG=false
            RESTORE_LOGS=false
            RESTORE_APP_DATA=false
            shift
            ;;
        -c|--config)
            RESTORE_DATABASE=false
            RESTORE_REDIS=false
            RESTORE_CONFIG=true
            RESTORE_LOGS=false
            RESTORE_APP_DATA=false
            shift
            ;;
        -l|--logs)
            RESTORE_DATABASE=false
            RESTORE_REDIS=false
            RESTORE_CONFIG=false
            RESTORE_LOGS=true
            RESTORE_APP_DATA=false
            shift
            ;;
        -a|--app-data)
            RESTORE_DATABASE=false
            RESTORE_REDIS=false
            RESTORE_CONFIG=false
            RESTORE_LOGS=false
            RESTORE_APP_DATA=true
            shift
            ;;
        --no-database)
            RESTORE_DATABASE=false
            shift
            ;;
        --no-redis)
            RESTORE_REDIS=false
            shift
            ;;
        --no-config)
            RESTORE_CONFIG=false
            shift
            ;;
        --no-app-data)
            RESTORE_APP_DATA=false
            shift
            ;;
        -f|--force)
            FORCE_RESTORE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --from-s3)
            DOWNLOAD_FROM_S3=true
            shift
            ;;
        *)
            if [[ "$1" == "list" ]]; then
                list_backups
                exit 0
            elif [[ -n "$1" && ! "$1" =~ ^- ]]; then
                RESTORE_TIMESTAMP="$1"
                shift
            else
                log "ERROR: Unknown option: $1"
                usage
                exit 1
            fi
            ;;
    esac
done

# Check if timestamp is provided
if [[ -z "$RESTORE_TIMESTAMP" ]]; then
    log "ERROR: Backup timestamp not provided"
    usage
    exit 1
fi

# Source environment file if it exists
if [[ -f "/opt/earnings_gap_trader/config/.env" ]]; then
    set -a
    source "/opt/earnings_gap_trader/config/.env"
    set +a
fi

# Run main function
main "$RESTORE_TIMESTAMP"