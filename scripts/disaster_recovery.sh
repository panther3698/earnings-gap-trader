#!/bin/bash
# Disaster Recovery Script for Earnings Gap Trading System
# Comprehensive disaster recovery procedures with automated failover capabilities

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/earnings_gap_trader/disaster_recovery.log"
CONFIG_FILE="/opt/earnings_gap_trader/config/disaster_recovery.conf"

# Default configuration
DR_MODE="${DR_MODE:-restore}"
PRIMARY_SITE="${PRIMARY_SITE:-primary}"
SECONDARY_SITE="${SECONDARY_SITE:-secondary}"
CURRENT_SITE="${CURRENT_SITE:-primary}"
BACKUP_BASE_DIR="/opt/backups/earnings_gap_trader"
DR_BACKUP_DIR="/opt/dr_backups/earnings_gap_trader"

# Services to manage
SERVICES=(
    "earnings-gap-trader"
    "earnings-gap-trader-worker"
    "earnings-gap-trader-scheduler"
    "postgresql"
    "redis-server"
    "nginx"
)

# Notification settings
ALERT_EMAIL="${ALERT_EMAIL:-}"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_IDS="${TELEGRAM_CHAT_IDS:-}"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"

# Health check settings
HEALTH_CHECK_URL="${HEALTH_CHECK_URL:-http://localhost:8000/health}"
HEALTH_CHECK_TIMEOUT=30
MAX_HEALTH_CHECK_RETRIES=3

# Recovery settings
AUTO_RECOVERY="${AUTO_RECOVERY:-false}"
RECOVERY_TIMEOUT=3600
FAILOVER_THRESHOLD=3

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
handle_error() {
    local exit_code=$?
    log "ERROR: Disaster recovery failed with exit code $exit_code"
    send_alert "CRITICAL" "DR Operation Failed" "Disaster recovery operation failed with exit code $exit_code at $(date)"
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
        echo "$message" | mail -s "[$level] Trading System DR: $subject" "$ALERT_EMAIL" 2>/dev/null || true
    fi
    
    # Telegram alert
    if [[ -n "$TELEGRAM_BOT_TOKEN" && -n "$TELEGRAM_CHAT_IDS" ]]; then
        local telegram_message="🚨 *Trading System DR Alert*\n\n*Level:* $level\n*Subject:* $subject\n*Message:* $message"
        
        IFS=',' read -ra CHAT_IDS <<< "$TELEGRAM_CHAT_IDS"
        for chat_id in "${CHAT_IDS[@]}"; do
            curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
                -d "chat_id=$chat_id" \
                -d "text=$telegram_message" \
                -d "parse_mode=Markdown" > /dev/null 2>&1 || true
        done
    fi
    
    # Slack notification
    if [[ -n "$SLACK_WEBHOOK" ]]; then
        local slack_payload="{\"text\":\"[$level] Trading System DR: $subject\n$message\"}"
        curl -s -X POST -H 'Content-type: application/json' \
            --data "$slack_payload" "$SLACK_WEBHOOK" > /dev/null 2>&1 || true
    fi
}

# Load configuration
load_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        source "$CONFIG_FILE"
        log "Configuration loaded from: $CONFIG_FILE"
    else
        log "Warning: Configuration file not found: $CONFIG_FILE"
    fi
}

# Health check function
check_system_health() {
    local retry_count=0
    
    while [[ $retry_count -lt $MAX_HEALTH_CHECK_RETRIES ]]; do
        if curl -s --max-time "$HEALTH_CHECK_TIMEOUT" "$HEALTH_CHECK_URL" > /dev/null 2>&1; then
            log "✓ System health check passed"
            return 0
        else
            retry_count=$((retry_count + 1))
            log "✗ Health check failed (attempt $retry_count/$MAX_HEALTH_CHECK_RETRIES)"
            sleep 10
        fi
    done
    
    log "✗ System health check failed after $MAX_HEALTH_CHECK_RETRIES attempts"
    return 1
}

# Check service status
check_service_status() {
    local failed_services=()
    
    for service in "${SERVICES[@]}"; do
        if systemctl is-active --quiet "$service"; then
            log "✓ Service $service is active"
        else
            log "✗ Service $service is not active"
            failed_services+=("$service")
        fi
    done
    
    if [[ ${#failed_services[@]} -eq 0 ]]; then
        return 0
    else
        log "Failed services: ${failed_services[*]}"
        return 1
    fi
}

# Stop all services
stop_all_services() {
    log "Stopping all trading system services..."
    
    for service in "${SERVICES[@]}"; do
        if systemctl is-active --quiet "$service"; then
            log "Stopping service: $service"
            systemctl stop "$service" || log "Warning: Failed to stop $service"
        fi
    done
    
    # Wait for services to stop
    sleep 10
    
    log "All services stopped"
}

# Start all services
start_all_services() {
    log "Starting all trading system services..."
    
    # Start services in specific order
    local start_order=(
        "postgresql"
        "redis-server"
        "nginx"
        "earnings-gap-trader"
        "earnings-gap-trader-worker"
        "earnings-gap-trader-scheduler"
    )
    
    for service in "${start_order[@]}"; do
        log "Starting service: $service"
        systemctl start "$service" || log "Warning: Failed to start $service"
        sleep 5
    done
    
    # Wait for services to start
    sleep 15
    
    log "All services started"
}

# Create emergency backup
create_emergency_backup() {
    log "Creating emergency backup..."
    
    local emergency_timestamp=$(date +"%Y%m%d_%H%M%S_emergency")
    local emergency_backup_dir="${DR_BACKUP_DIR}/${emergency_timestamp}"
    
    mkdir -p "$emergency_backup_dir"
    
    # Quick database backup
    if systemctl is-active --quiet postgresql; then
        log "Creating emergency database backup..."
        pg_dumpall -U postgres > "${emergency_backup_dir}/emergency_db_backup.sql" 2>/dev/null || true
    fi
    
    # Configuration backup
    log "Creating emergency configuration backup..."
    tar -czf "${emergency_backup_dir}/emergency_config.tar.gz" \
        -C /opt/earnings_gap_trader \
        config/ systemd/ docker-compose.yml 2>/dev/null || true
    
    # Application state backup
    log "Creating emergency application state backup..."
    tar -czf "${emergency_backup_dir}/emergency_app_state.tar.gz" \
        -C /opt/earnings_gap_trader/app \
        logs/ data/ cache/ 2>/dev/null || true
    
    log "Emergency backup created: $emergency_backup_dir"
    echo "$emergency_backup_dir"
}

# Restore from latest backup
restore_from_backup() {
    local backup_timestamp="$1"
    
    log "Initiating restore from backup: $backup_timestamp"
    
    # Stop services before restore
    stop_all_services
    
    # Run restore script
    if [[ -x "$SCRIPT_DIR/restore.sh" ]]; then
        log "Running restore script..."
        "$SCRIPT_DIR/restore.sh" --force "$backup_timestamp"
    else
        log "ERROR: Restore script not found or not executable"
        return 1
    fi
    
    # Start services after restore
    start_all_services
    
    # Verify system health
    sleep 30
    if check_system_health; then
        log "✓ System restored and healthy"
        return 0
    else
        log "✗ System restored but health check failed"
        return 1
    fi
}

# Failover to secondary site
failover_to_secondary() {
    log "Initiating failover to secondary site..."
    
    # Create emergency backup before failover
    local emergency_backup
    emergency_backup=$(create_emergency_backup)
    
    # Stop services on primary
    stop_all_services
    
    # Update DNS or load balancer configuration (placeholder)
    log "Updating DNS/Load Balancer configuration..."
    # This would typically involve API calls to your DNS provider or load balancer
    # update_dns_to_secondary() || log "Warning: DNS update failed"
    
    # Sync data to secondary site (if configured)
    if [[ -n "${SECONDARY_SITE_HOST:-}" ]]; then
        log "Syncing emergency backup to secondary site..."
        rsync -avz "$emergency_backup/" "${SECONDARY_SITE_HOST}:${DR_BACKUP_DIR}/" || log "Warning: Sync to secondary failed"
    fi
    
    log "Failover to secondary site initiated"
    send_alert "CRITICAL" "Failover Initiated" "Failover to secondary site initiated at $(date). Emergency backup: $emergency_backup"
}

# Automated recovery attempt
attempt_auto_recovery() {
    log "Attempting automated recovery..."
    
    local recovery_attempts=0
    local max_attempts=3
    
    while [[ $recovery_attempts -lt $max_attempts ]]; do
        recovery_attempts=$((recovery_attempts + 1))
        log "Recovery attempt $recovery_attempts/$max_attempts"
        
        # Try restarting services
        log "Attempting service restart..."
        stop_all_services
        sleep 30
        start_all_services
        sleep 60
        
        # Check if recovery was successful
        if check_system_health && check_service_status; then
            log "✓ Automated recovery successful"
            send_alert "INFO" "Recovery Successful" "Automated recovery completed successfully after $recovery_attempts attempts at $(date)"
            return 0
        fi
        
        # Try restoring from latest backup
        log "Service restart failed, attempting restore from latest backup..."
        local latest_backup
        latest_backup=$(find "$BACKUP_BASE_DIR" -maxdepth 1 -type d -name "20*" | sort -r | head -1 | xargs basename 2>/dev/null || echo "")
        
        if [[ -n "$latest_backup" ]]; then
            if restore_from_backup "$latest_backup"; then
                log "✓ Recovery from backup successful"
                send_alert "WARNING" "Recovery from Backup" "Recovery completed using backup $latest_backup after $recovery_attempts attempts at $(date)"
                return 0
            fi
        fi
        
        log "✗ Recovery attempt $recovery_attempts failed"
        sleep 60
    done
    
    log "✗ All automated recovery attempts failed"
    send_alert "CRITICAL" "Recovery Failed" "All automated recovery attempts failed after $max_attempts attempts at $(date)"
    return 1
}

# Disaster detection
detect_disaster() {
    log "Running disaster detection checks..."
    
    local disaster_detected=false
    local failure_count=0
    
    # Check system health
    if ! check_system_health; then
        log "✗ System health check failed"
        failure_count=$((failure_count + 1))
    fi
    
    # Check service status
    if ! check_service_status; then
        log "✗ Service status check failed"
        failure_count=$((failure_count + 1))
    fi
    
    # Check disk space
    local disk_usage
    disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ $disk_usage -gt 95 ]]; then
        log "✗ Critical disk space: ${disk_usage}%"
        failure_count=$((failure_count + 1))
    fi
    
    # Check memory usage
    local memory_usage
    memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [[ $memory_usage -gt 95 ]]; then
        log "✗ Critical memory usage: ${memory_usage}%"
        failure_count=$((failure_count + 1))
    fi
    
    # Check database connectivity
    if ! sudo -u postgres psql -c "SELECT 1;" > /dev/null 2>&1; then
        log "✗ Database connectivity failed"
        failure_count=$((failure_count + 1))
    fi
    
    # Determine if disaster detected
    if [[ $failure_count -ge $FAILOVER_THRESHOLD ]]; then
        disaster_detected=true
        log "✗ DISASTER DETECTED: $failure_count critical failures detected"
        send_alert "CRITICAL" "Disaster Detected" "Disaster detected with $failure_count critical failures at $(date)"
    else
        log "✓ No disaster detected ($failure_count failures, threshold: $FAILOVER_THRESHOLD)"
    fi
    
    echo "$disaster_detected"
}

# Monitor and react
monitor_and_react() {
    log "Starting continuous monitoring mode..."
    
    local consecutive_failures=0
    local monitoring=true
    
    while [[ "$monitoring" == "true" ]]; do
        if [[ "$(detect_disaster)" == "true" ]]; then
            consecutive_failures=$((consecutive_failures + 1))
            log "Consecutive failures: $consecutive_failures"
            
            if [[ $consecutive_failures -ge $FAILOVER_THRESHOLD ]]; then
                log "CRITICAL: Disaster threshold reached"
                
                if [[ "$AUTO_RECOVERY" == "true" ]]; then
                    if attempt_auto_recovery; then
                        consecutive_failures=0
                        log "Recovery successful, resetting failure count"
                    else
                        log "Auto recovery failed, initiating manual procedures"
                        monitoring=false
                    fi
                else
                    log "Auto recovery disabled, manual intervention required"
                    monitoring=false
                fi
            fi
        else
            if [[ $consecutive_failures -gt 0 ]]; then
                log "System health restored, resetting failure count"
                consecutive_failures=0
            fi
        fi
        
        sleep 60  # Check every minute
    done
}

# Generate disaster recovery report
generate_dr_report() {
    local report_file="/opt/earnings_gap_trader/reports/dr_report_$(date +%Y%m%d_%H%M%S).txt"
    
    mkdir -p "$(dirname "$report_file")"
    
    cat > "$report_file" << EOF
================================================================================
DISASTER RECOVERY SYSTEM STATUS REPORT
Generated: $(date)
================================================================================

SYSTEM INFORMATION:
- Hostname: $(hostname)
- Current Site: $CURRENT_SITE
- DR Mode: $DR_MODE
- Auto Recovery: $AUTO_RECOVERY

SERVICE STATUS:
$(for service in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$service"; then
        echo "  ✓ $service: ACTIVE"
    else
        echo "  ✗ $service: INACTIVE"
    fi
done)

SYSTEM RESOURCES:
- Disk Usage: $(df / | awk 'NR==2 {print $5}')
- Memory Usage: $(free | awk 'NR==2{printf "%.1f%%", $3*100/$2}')
- CPU Load: $(uptime | awk -F'load average:' '{print $2}')
- Uptime: $(uptime | awk '{print $3,$4}' | sed 's/,//')

BACKUP STATUS:
- Latest Backup: $(find "$BACKUP_BASE_DIR" -maxdepth 1 -type d -name "20*" | sort -r | head -1 | xargs basename 2>/dev/null || echo "None found")
- Backup Directory Size: $(du -sh "$BACKUP_BASE_DIR" 2>/dev/null | cut -f1 || echo "Unknown")
- Emergency Backups: $(find "$DR_BACKUP_DIR" -maxdepth 1 -type d -name "*emergency*" | wc -l 2>/dev/null || echo "0")

HEALTH CHECK RESULTS:
$(if check_system_health > /dev/null 2>&1; then
    echo "  ✓ Application Health: HEALTHY"
else
    echo "  ✗ Application Health: UNHEALTHY"
fi)

CONNECTIVITY:
$(if curl -s --max-time 5 http://localhost:8000/health > /dev/null 2>&1; then
    echo "  ✓ Local API: ACCESSIBLE"
else
    echo "  ✗ Local API: NOT ACCESSIBLE"
fi)

RECENT LOG ENTRIES:
$(tail -10 "$LOG_FILE" 2>/dev/null || echo "No recent log entries")

================================================================================
END OF REPORT
================================================================================
EOF
    
    log "DR report generated: $report_file"
    echo "$report_file"
}

# Show usage
usage() {
    cat << EOF
Usage: $0 [COMMAND] [OPTIONS]

Disaster Recovery Management for Earnings Gap Trading System

COMMANDS:
    monitor         Start continuous monitoring mode
    detect          Run disaster detection checks
    recover         Attempt automated recovery
    restore         Restore from specific backup
    failover        Initiate failover to secondary site
    backup          Create emergency backup
    report          Generate DR status report
    test            Run DR system tests
    status          Show current DR status

OPTIONS:
    -h, --help      Show this help message
    -c, --config    Specify configuration file
    --auto          Enable auto recovery mode
    --no-auto       Disable auto recovery mode
    --force         Force operation without confirmation

EXAMPLES:
    $0 monitor                      # Start monitoring mode
    $0 detect                       # Run disaster detection
    $0 recover                      # Attempt recovery
    $0 restore 20240115_143022      # Restore from specific backup
    $0 backup                       # Create emergency backup
    $0 report                       # Generate status report

EOF
}

# Test DR procedures
test_dr_procedures() {
    log "Running DR system tests..."
    
    local test_results=()
    
    # Test 1: Backup creation
    log "Test 1: Emergency backup creation"
    if backup_dir=$(create_emergency_backup); then
        test_results+=("✓ Emergency backup: PASS")
        rm -rf "$backup_dir"  # Cleanup test backup
    else
        test_results+=("✗ Emergency backup: FAIL")
    fi
    
    # Test 2: Service management
    log "Test 2: Service management"
    if systemctl list-units --type=service --state=active | grep -q earnings-gap-trader; then
        test_results+=("✓ Service management: PASS")
    else
        test_results+=("✗ Service management: FAIL")
    fi
    
    # Test 3: Health checks
    log "Test 3: Health check functionality"
    if check_system_health > /dev/null 2>&1; then
        test_results+=("✓ Health checks: PASS")
    else
        test_results+=("✗ Health checks: FAIL")
    fi
    
    # Test 4: Notification system
    log "Test 4: Notification system"
    send_alert "INFO" "DR Test" "This is a test notification from the DR system"
    test_results+=("✓ Notifications: SENT (check your alerts)")
    
    # Display results
    log "DR Test Results:"
    for result in "${test_results[@]}"; do
        log "  $result"
    done
}

# Main function
main() {
    local command="${1:-status}"
    
    # Create lock file
    local lock_file="/var/run/earnings_gap_trader_dr.lock"
    if [[ -f "$lock_file" ]] && [[ "$command" != "status" ]]; then
        log "ERROR: DR operation already running (lock file exists)"
        exit 1
    fi
    
    if [[ "$command" != "status" ]]; then
        echo $$ > "$lock_file"
        trap "rm -f $lock_file" EXIT
    fi
    
    # Load configuration
    load_config
    
    case "$command" in
        monitor)
            monitor_and_react
            ;;
        detect)
            if [[ "$(detect_disaster)" == "true" ]]; then
                exit 1
            else
                exit 0
            fi
            ;;
        recover)
            attempt_auto_recovery
            ;;
        restore)
            local backup_timestamp="${2:-}"
            if [[ -z "$backup_timestamp" ]]; then
                log "ERROR: Backup timestamp required for restore"
                exit 1
            fi
            restore_from_backup "$backup_timestamp"
            ;;
        failover)
            failover_to_secondary
            ;;
        backup)
            create_emergency_backup
            ;;
        report)
            generate_dr_report
            ;;
        test)
            test_dr_procedures
            ;;
        status)
            echo "Disaster Recovery System Status:"
            echo "Current Site: $CURRENT_SITE"
            echo "Auto Recovery: $AUTO_RECOVERY"
            if check_system_health > /dev/null 2>&1; then
                echo "System Health: ✓ HEALTHY"
            else
                echo "System Health: ✗ UNHEALTHY"
            fi
            ;;
        *)
            log "ERROR: Unknown command: $command"
            usage
            exit 1
            ;;
    esac
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --auto)
            AUTO_RECOVERY=true
            shift
            ;;
        --no-auto)
            AUTO_RECOVERY=false
            shift
            ;;
        --force)
            # Handle force option if needed
            shift
            ;;
        *)
            break
            ;;
    esac
done

# Run main function with remaining arguments
main "$@"