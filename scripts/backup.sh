#!/bin/bash
# Comprehensive backup script for Earnings Gap Trading System
# Performs database, configuration, and application data backups

set -euo pipefail

# Configuration
BACKUP_BASE_DIR="/opt/backups/earnings_gap_trader"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="${BACKUP_BASE_DIR}/${TIMESTAMP}"
LOG_FILE="/var/log/earnings_gap_trader/backup.log"

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

# Retention settings
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Notification settings
ALERT_EMAIL="${ALERT_EMAIL:-}"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_IDS="${TELEGRAM_CHAT_IDS:-}"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
handle_error() {
    local exit_code=$?
    log "ERROR: Backup failed with exit code $exit_code"
    send_alert "CRITICAL" "Backup failed" "Backup process failed with exit code $exit_code at $(date)"
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
        echo "$message" | mail -s "[$level] Trading System Backup: $subject" "$ALERT_EMAIL" 2>/dev/null || true
    fi
    
    # Telegram alert
    if [[ -n "$TELEGRAM_BOT_TOKEN" && -n "$TELEGRAM_CHAT_IDS" ]]; then
        local telegram_message="🔄 *Trading System Backup*\n\n*Level:* $level\n*Subject:* $subject\n*Message:* $message"
        
        IFS=',' read -ra CHAT_IDS <<< "$TELEGRAM_CHAT_IDS"
        for chat_id in "${CHAT_IDS[@]}"; do
            curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
                -d "chat_id=$chat_id" \
                -d "text=$telegram_message" \
                -d "parse_mode=Markdown" > /dev/null 2>&1 || true
        done
    fi
}

# Create backup directory
create_backup_dir() {
    log "Creating backup directory: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"/{database,redis,config,logs,data}
    chmod 750 "$BACKUP_DIR"
}

# Backup PostgreSQL database
backup_database() {
    log "Starting database backup..."
    
    local db_backup_file="${BACKUP_DIR}/database/earnings_gap_trader_${TIMESTAMP}.sql.gz"
    
    # Set password for pg_dump
    export PGPASSWORD="$DB_PASSWORD"
    
    # Create database dump with compression
    pg_dump \
        --host="$DB_HOST" \
        --port="$DB_PORT" \
        --username="$DB_USER" \
        --dbname="$DB_NAME" \
        --verbose \
        --clean \
        --if-exists \
        --create \
        --format=custom \
        --compress=9 \
        --file="${db_backup_file%.gz}" 2>> "$LOG_FILE"
    
    # Compress the dump
    gzip "${db_backup_file%.gz}"
    
    # Verify backup
    if [[ -f "$db_backup_file" ]]; then
        local backup_size=$(du -h "$db_backup_file" | cut -f1)
        log "Database backup completed: $db_backup_file ($backup_size)"
    else
        log "ERROR: Database backup file not created"
        return 1
    fi
    
    unset PGPASSWORD
}

# Backup Redis data
backup_redis() {
    log "Starting Redis backup..."
    
    local redis_backup_file="${BACKUP_DIR}/redis/redis_${TIMESTAMP}.rdb"
    
    # Trigger Redis BGSAVE
    if [[ -n "$REDIS_PASSWORD" ]]; then
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" BGSAVE >> "$LOG_FILE" 2>&1
    else
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" BGSAVE >> "$LOG_FILE" 2>&1
    fi
    
    # Wait for background save to complete
    log "Waiting for Redis background save to complete..."
    while true; do
        if [[ -n "$REDIS_PASSWORD" ]]; then
            last_save=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" LASTSAVE)
        else
            last_save=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" LASTSAVE)
        fi
        
        if [[ "$last_save" != "$prev_save" ]]; then
            break
        fi
        sleep 2
    done
    
    # Copy Redis dump file
    local redis_data_dir="/var/lib/redis"
    if [[ -f "$redis_data_dir/dump.rdb" ]]; then
        cp "$redis_data_dir/dump.rdb" "$redis_backup_file"
        gzip "$redis_backup_file"
        log "Redis backup completed: ${redis_backup_file}.gz"
    else
        log "WARNING: Redis dump file not found"
    fi
}

# Backup configuration files
backup_config() {
    log "Starting configuration backup..."
    
    local config_backup_file="${BACKUP_DIR}/config/config_${TIMESTAMP}.tar.gz"
    
    # Backup configuration directories
    tar -czf "$config_backup_file" \
        -C /opt/earnings_gap_trader \
        config/ \
        systemd/ \
        docker-compose.yml \
        requirements*.txt \
        .env.production.example \
        2>> "$LOG_FILE"
    
    if [[ -f "$config_backup_file" ]]; then
        local backup_size=$(du -h "$config_backup_file" | cut -f1)
        log "Configuration backup completed: $config_backup_file ($backup_size)"
    else
        log "ERROR: Configuration backup failed"
        return 1
    fi
}

# Backup log files
backup_logs() {
    log "Starting log backup..."
    
    local logs_backup_file="${BACKUP_DIR}/logs/logs_${TIMESTAMP}.tar.gz"
    local log_dir="/var/log/earnings_gap_trader"
    
    if [[ -d "$log_dir" ]]; then
        tar -czf "$logs_backup_file" \
            -C "$(dirname "$log_dir")" \
            "$(basename "$log_dir")" \
            2>> "$LOG_FILE"
        
        if [[ -f "$logs_backup_file" ]]; then
            local backup_size=$(du -h "$logs_backup_file" | cut -f1)
            log "Log backup completed: $logs_backup_file ($backup_size)"
        else
            log "WARNING: Log backup failed"
        fi
    else
        log "WARNING: Log directory not found: $log_dir"
    fi
}

# Backup application data
backup_app_data() {
    log "Starting application data backup..."
    
    local data_backup_file="${BACKUP_DIR}/data/app_data_${TIMESTAMP}.tar.gz"
    local app_dir="/opt/earnings_gap_trader"
    
    # Backup critical application files (excluding venv and __pycache__)
    tar -czf "$data_backup_file" \
        -C "$app_dir" \
        --exclude="venv" \
        --exclude="__pycache__" \
        --exclude="*.pyc" \
        --exclude="*.pyo" \
        --exclude=".git" \
        --exclude="node_modules" \
        app/ \
        scripts/ \
        2>> "$LOG_FILE"
    
    if [[ -f "$data_backup_file" ]]; then
        local backup_size=$(du -h "$data_backup_file" | cut -f1)
        log "Application data backup completed: $data_backup_file ($backup_size)"
    else
        log "ERROR: Application data backup failed"
        return 1
    fi
}

# Create backup manifest
create_manifest() {
    log "Creating backup manifest..."
    
    local manifest_file="${BACKUP_DIR}/MANIFEST.json"
    
    cat > "$manifest_file" << EOF
{
    "backup_timestamp": "$TIMESTAMP",
    "backup_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "backup_type": "full",
    "version": "1.0",
    "components": {
        "database": {
            "type": "postgresql",
            "host": "$DB_HOST",
            "database": "$DB_NAME",
            "backup_method": "pg_dump"
        },
        "redis": {
            "type": "redis",
            "host": "$REDIS_HOST",
            "backup_method": "rdb_copy"
        },
        "configuration": {
            "type": "files",
            "backup_method": "tar_gz"
        },
        "logs": {
            "type": "files",
            "backup_method": "tar_gz"
        },
        "application_data": {
            "type": "files",
            "backup_method": "tar_gz"
        }
    },
    "system_info": {
        "hostname": "$(hostname)",
        "os": "$(uname -s)",
        "kernel": "$(uname -r)",
        "backup_script_version": "1.0"
    },
    "checksums": {
$(find "$BACKUP_DIR" -type f -name "*.gz" -o -name "*.sql" | while read -r file; do
    echo "        \"$(basename "$file")\": \"$(sha256sum "$file" | cut -d' ' -f1)\","
done | sed '$ s/,$//')
    }
}
EOF
    
    log "Backup manifest created: $manifest_file"
}

# Upload to S3 (optional)
upload_to_s3() {
    if [[ -z "$S3_BUCKET" ]]; then
        log "S3 upload skipped (no bucket configured)"
        return 0
    fi
    
    log "Starting S3 upload..."
    
    # Create tarball of entire backup
    local backup_archive="${BACKUP_BASE_DIR}/backup_${TIMESTAMP}.tar.gz"
    tar -czf "$backup_archive" -C "$BACKUP_BASE_DIR" "$TIMESTAMP"
    
    # Upload to S3
    if command -v aws &> /dev/null; then
        aws s3 cp "$backup_archive" "s3://$S3_BUCKET/backups/" \
            --region "$AWS_REGION" \
            --storage-class STANDARD_IA >> "$LOG_FILE" 2>&1
        
        if [[ $? -eq 0 ]]; then
            log "S3 upload completed: s3://$S3_BUCKET/backups/$(basename "$backup_archive")"
            rm -f "$backup_archive"
        else
            log "ERROR: S3 upload failed"
            return 1
        fi
    else
        log "WARNING: AWS CLI not found, skipping S3 upload"
    fi
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    
    # Local cleanup
    find "$BACKUP_BASE_DIR" -type d -name "20*" -mtime +$RETENTION_DAYS -exec rm -rf {} \; 2>/dev/null || true
    
    # S3 cleanup (if configured)
    if [[ -n "$S3_BUCKET" ]] && command -v aws &> /dev/null; then
        local cutoff_date=$(date -d "$RETENTION_DAYS days ago" +%Y%m%d)
        aws s3 ls "s3://$S3_BUCKET/backups/" --region "$AWS_REGION" | \
        awk '{print $4}' | \
        grep "^backup_[0-9]" | \
        while read -r backup_file; do
            local backup_date=$(echo "$backup_file" | sed 's/backup_\([0-9]\{8\}\).*/\1/')
            if [[ "$backup_date" < "$cutoff_date" ]]; then
                aws s3 rm "s3://$S3_BUCKET/backups/$backup_file" --region "$AWS_REGION" >> "$LOG_FILE" 2>&1
                log "Deleted old S3 backup: $backup_file"
            fi
        done
    fi
    
    log "Cleanup completed"
}

# Verify backup integrity
verify_backup() {
    log "Verifying backup integrity..."
    
    local verification_failed=false
    
    # Check if all expected files exist
    local expected_files=(
        "${BACKUP_DIR}/database/earnings_gap_trader_${TIMESTAMP}.sql.gz"
        "${BACKUP_DIR}/config/config_${TIMESTAMP}.tar.gz"
        "${BACKUP_DIR}/data/app_data_${TIMESTAMP}.tar.gz"
        "${BACKUP_DIR}/MANIFEST.json"
    )
    
    for file in "${expected_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log "ERROR: Expected backup file missing: $file"
            verification_failed=true
        fi
    done
    
    # Verify file sizes (should be > 0)
    find "$BACKUP_DIR" -type f -size 0 | while read -r empty_file; do
        log "ERROR: Empty backup file: $empty_file"
        verification_failed=true
    done
    
    if [[ "$verification_failed" == "true" ]]; then
        log "ERROR: Backup verification failed"
        return 1
    else
        log "Backup verification completed successfully"
    fi
}

# Main backup function
main() {
    log "Starting backup process..."
    
    # Check if backup is already running
    local lock_file="/var/run/earnings_gap_trader_backup.lock"
    if [[ -f "$lock_file" ]]; then
        log "ERROR: Backup already running (lock file exists)"
        exit 1
    fi
    
    # Create lock file
    echo $$ > "$lock_file"
    trap "rm -f $lock_file" EXIT
    
    # Check dependencies
    command -v pg_dump >/dev/null 2>&1 || { log "ERROR: pg_dump not found"; exit 1; }
    command -v redis-cli >/dev/null 2>&1 || { log "ERROR: redis-cli not found"; exit 1; }
    
    # Create backup directory
    create_backup_dir
    
    # Perform backups
    backup_database
    backup_redis
    backup_config
    backup_logs
    backup_app_data
    
    # Create manifest
    create_manifest
    
    # Verify backup
    verify_backup
    
    # Upload to S3
    upload_to_s3
    
    # Cleanup old backups
    cleanup_old_backups
    
    # Calculate total backup size
    local total_size=$(du -sh "$BACKUP_DIR" | cut -f1)
    log "Backup process completed successfully. Total size: $total_size"
    
    # Send success notification
    send_alert "INFO" "Backup completed" "Backup process completed successfully at $(date). Total size: $total_size"
}

# Check if script is run as root or with appropriate permissions
if [[ $EUID -eq 0 ]]; then
    log "WARNING: Running as root. Consider using a dedicated backup user."
fi

# Source environment file if it exists
if [[ -f "/opt/earnings_gap_trader/config/.env" ]]; then
    set -a
    source "/opt/earnings_gap_trader/config/.env"
    set +a
fi

# Run main function
main "$@"