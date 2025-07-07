#!/bin/bash
set -e

# Earnings Gap Trading System - Production Deployment Script
# Version: 1.0.0
# Description: Automated deployment script for production environment

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="earnings_gap_trader"
APP_DIR="/opt/${APP_NAME}"
SERVICE_USER="trader"
PYTHON_VERSION="3.11"
VENV_DIR="${APP_DIR}/venv"
LOG_DIR="/var/log/${APP_NAME}"
BACKUP_DIR="/opt/backups/${APP_NAME}"
NGINX_CONFIG="/etc/nginx/sites-available/${APP_NAME}"
SYSTEMD_SERVICE="/etc/systemd/system/${APP_NAME}.service"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_os() {
    if [ -f /etc/debian_version ]; then
        OS="debian"
        log_info "Detected Debian/Ubuntu system"
    elif [ -f /etc/redhat-release ]; then
        OS="redhat"
        log_info "Detected RedHat/CentOS system"
    else
        log_error "Unsupported operating system"
        exit 1
    fi
}

install_system_dependencies() {
    log_info "Installing system dependencies..."
    
    if [ "$OS" = "debian" ]; then
        apt-get update
        apt-get install -y \
            python${PYTHON_VERSION} \
            python${PYTHON_VERSION}-dev \
            python${PYTHON_VERSION}-venv \
            python3-pip \
            nginx \
            postgresql-14 \
            postgresql-contrib \
            redis-server \
            git \
            curl \
            wget \
            unzip \
            supervisor \
            htop \
            vim \
            certbot \
            python3-certbot-nginx
    elif [ "$OS" = "redhat" ]; then
        yum update -y
        yum install -y \
            python${PYTHON_VERSION} \
            python${PYTHON_VERSION}-devel \
            python3-pip \
            nginx \
            postgresql-server \
            postgresql-contrib \
            redis \
            git \
            curl \
            wget \
            unzip \
            supervisor \
            htop \
            vim \
            certbot \
            python3-certbot-nginx
    fi
    
    log_success "System dependencies installed"
}

create_user() {
    log_info "Creating service user..."
    
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd -r -s /bin/bash -d "$APP_DIR" "$SERVICE_USER"
        log_success "Created user: $SERVICE_USER"
    else
        log_warning "User $SERVICE_USER already exists"
    fi
}

setup_directories() {
    log_info "Setting up directories..."
    
    # Create application directory
    mkdir -p "$APP_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$BACKUP_DIR"
    mkdir -p "${APP_DIR}/config"
    mkdir -p "${APP_DIR}/static"
    mkdir -p "${APP_DIR}/logs"
    
    # Set permissions
    chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$LOG_DIR"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$BACKUP_DIR"
    
    log_success "Directories created and configured"
}

setup_python_environment() {
    log_info "Setting up Python virtual environment..."
    
    # Create virtual environment
    sudo -u "$SERVICE_USER" python${PYTHON_VERSION} -m venv "$VENV_DIR"
    
    # Upgrade pip
    sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel
    
    log_success "Python virtual environment created"
}

install_application() {
    log_info "Installing application..."
    
    # Copy application files
    cp -r . "$APP_DIR/app/"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR/app/"
    
    # Install Python dependencies
    log_info "Installing Python dependencies..."
    sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install -r "${APP_DIR}/app/requirements-production.txt"
    
    log_success "Application installed"
}

setup_database() {
    log_info "Setting up PostgreSQL database..."
    
    # Initialize PostgreSQL (if needed)
    if [ "$OS" = "redhat" ]; then
        postgresql-setup initdb
    fi
    
    # Start PostgreSQL
    systemctl start postgresql
    systemctl enable postgresql
    
    # Create database and user
    sudo -u postgres psql << EOF
CREATE DATABASE ${APP_NAME}_prod;
CREATE USER ${APP_NAME}_user WITH PASSWORD '$(openssl rand -base64 32)';
GRANT ALL PRIVILEGES ON DATABASE ${APP_NAME}_prod TO ${APP_NAME}_user;
ALTER USER ${APP_NAME}_user CREATEDB;
\q
EOF
    
    # Initialize database schema
    sudo -u "$SERVICE_USER" bash -c "
        cd $APP_DIR/app && 
        $VENV_DIR/bin/python -c 'from database import init_database; init_database()'
    "
    
    log_success "Database configured"
}

setup_redis() {
    log_info "Setting up Redis..."
    
    # Start Redis
    systemctl start redis
    systemctl enable redis
    
    # Configure Redis for production
    cat > /etc/redis/redis.conf.d/trading.conf << 'EOF'
# Trading system specific Redis configuration
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
EOF
    
    systemctl restart redis
    
    log_success "Redis configured"
}

create_environment_file() {
    log_info "Creating environment configuration..."
    
    cat > "${APP_DIR}/config/.env" << 'EOF'
# Production Environment Configuration
ENVIRONMENT=production
DEBUG=False
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=earnings_gap_trader_prod
DB_USER=earnings_gap_trader_user
DB_PASSWORD=CHANGE_THIS_PASSWORD

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Security
SECRET_KEY=CHANGE_THIS_SECRET_KEY
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# API Keys (to be filled by user)
ZERODHA_API_KEY=your_zerodha_api_key
ZERODHA_ACCESS_TOKEN=your_zerodha_access_token
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_IDS=your_chat_id_1,your_chat_id_2

# Trading Configuration
PAPER_TRADING=True
MAX_DAILY_LOSS=50000
MAX_POSITIONS=5
POSITION_SIZE_PERCENT=5.0
STOP_LOSS_PERCENT=3.0

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/earnings_gap_trader/app.log
EOF
    
    # Set secure permissions
    chmod 600 "${APP_DIR}/config/.env"
    chown "$SERVICE_USER:$SERVICE_USER" "${APP_DIR}/config/.env"
    
    log_warning "Please update the .env file with your actual configuration values"
    log_success "Environment file created"
}

create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > "$SYSTEMD_SERVICE" << EOF
[Unit]
Description=Earnings Gap Trading System
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=exec
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$APP_DIR/app
Environment=PATH=$VENV_DIR/bin
EnvironmentFile=$APP_DIR/config/.env
ExecStart=$VENV_DIR/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$APP_NAME

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

# Security measures
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR $LOG_DIR $BACKUP_DIR

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable "$APP_NAME"
    
    log_success "Systemd service created"
}

setup_nginx() {
    log_info "Setting up Nginx reverse proxy..."
    
    cat > "$NGINX_CONFIG" << 'EOF'
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=trading:10m rate=10r/m;
    limit_req zone=trading burst=20 nodelay;
    
    # Static files
    location /static {
        alias /opt/earnings_gap_trader/app/frontend/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # WebSocket support
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
    
    # Application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
    
    # Security
    location ~ /\. {
        deny all;
    }
    
    location ~ ^/(admin|api/admin) {
        deny all;
    }
}
EOF
    
    # Enable site
    ln -sf "$NGINX_CONFIG" /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Test nginx configuration
    nginx -t
    
    # Start nginx
    systemctl restart nginx
    systemctl enable nginx
    
    log_success "Nginx configured"
}

setup_ssl() {
    log_info "Setting up SSL certificate..."
    
    # Note: This requires manual intervention for domain verification
    log_warning "SSL setup requires manual domain verification"
    log_info "Run the following command after updating your domain in nginx config:"
    log_info "certbot --nginx -d your-domain.com -d www.your-domain.com"
    
    # Set up auto-renewal
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
    
    log_success "SSL auto-renewal configured"
}

setup_monitoring() {
    log_info "Setting up monitoring scripts..."
    
    # Create monitoring script
    cat > "${APP_DIR}/scripts/health_check.sh" << 'EOF'
#!/bin/bash
# Health check script for earnings gap trading system

LOG_FILE="/var/log/earnings_gap_trader/health_check.log"
APP_URL="http://localhost:8000/health"

# Check application health
if curl -f -s "$APP_URL" > /dev/null; then
    echo "$(date): Application is healthy" >> "$LOG_FILE"
else
    echo "$(date): Application health check failed" >> "$LOG_FILE"
    systemctl restart earnings_gap_trader
fi

# Check disk space
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "$(date): WARNING - Disk usage is ${DISK_USAGE}%" >> "$LOG_FILE"
fi

# Check memory usage
MEM_USAGE=$(free | awk 'NR==2{printf "%.2f%%", $3*100/$2 }' | sed 's/%//')
if [ "$(echo "$MEM_USAGE > 90" | bc -l)" -eq 1 ]; then
    echo "$(date): WARNING - Memory usage is ${MEM_USAGE}%" >> "$LOG_FILE"
fi
EOF
    
    chmod +x "${APP_DIR}/scripts/health_check.sh"
    
    # Set up cron job for health checks
    (crontab -u "$SERVICE_USER" -l 2>/dev/null; echo "*/5 * * * * ${APP_DIR}/scripts/health_check.sh") | crontab -u "$SERVICE_USER" -
    
    log_success "Monitoring configured"
}

setup_backup() {
    log_info "Setting up backup procedures..."
    
    # Create backup script
    cat > "${APP_DIR}/scripts/backup.sh" << 'EOF'
#!/bin/bash
# Backup script for earnings gap trading system

BACKUP_DIR="/opt/backups/earnings_gap_trader"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="earnings_gap_trader_prod"
DB_USER="earnings_gap_trader_user"

# Create backup directory
mkdir -p "$BACKUP_DIR/db"
mkdir -p "$BACKUP_DIR/config"
mkdir -p "$BACKUP_DIR/logs"

# Database backup
pg_dump -U "$DB_USER" -h localhost "$DB_NAME" | gzip > "$BACKUP_DIR/db/db_backup_$DATE.sql.gz"

# Configuration backup
cp -r /opt/earnings_gap_trader/config "$BACKUP_DIR/config/config_$DATE"

# Log backup (last 7 days)
find /var/log/earnings_gap_trader -name "*.log" -mtime -7 -exec cp {} "$BACKUP_DIR/logs/" \;

# Clean old backups (keep 30 days)
find "$BACKUP_DIR" -type f -mtime +30 -delete
find "$BACKUP_DIR" -type d -empty -delete

echo "$(date): Backup completed - $DATE"
EOF
    
    chmod +x "${APP_DIR}/scripts/backup.sh"
    
    # Set up daily backup cron job
    (crontab -u "$SERVICE_USER" -l 2>/dev/null; echo "0 2 * * * ${APP_DIR}/scripts/backup.sh") | crontab -u "$SERVICE_USER" -
    
    log_success "Backup procedures configured"
}

setup_logrotate() {
    log_info "Setting up log rotation..."
    
    cat > "/etc/logrotate.d/${APP_NAME}" << 'EOF'
/var/log/earnings_gap_trader/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 trader trader
    postrotate
        systemctl reload earnings_gap_trader
    endscript
}
EOF
    
    log_success "Log rotation configured"
}

run_health_checks() {
    log_info "Running health checks..."
    
    # Check if services are running
    services=("postgresql" "redis" "nginx" "$APP_NAME")
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            log_success "$service is running"
        else
            log_error "$service is not running"
        fi
    done
    
    # Check application health endpoint
    sleep 5  # Give app time to start
    if curl -f -s "http://localhost:8000/health" > /dev/null; then
        log_success "Application health check passed"
    else
        log_warning "Application health check failed - check logs"
    fi
}

display_next_steps() {
    log_info "Deployment completed! Next steps:"
    echo ""
    echo "1. Update configuration file: ${APP_DIR}/config/.env"
    echo "   - Add your actual API keys"
    echo "   - Update database password"
    echo "   - Set your domain name"
    echo ""
    echo "2. Update Nginx configuration: $NGINX_CONFIG"
    echo "   - Replace 'your-domain.com' with your actual domain"
    echo ""
    echo "3. Set up SSL certificate:"
    echo "   sudo certbot --nginx -d your-domain.com"
    echo ""
    echo "4. Start the application:"
    echo "   sudo systemctl start $APP_NAME"
    echo ""
    echo "5. Check application status:"
    echo "   sudo systemctl status $APP_NAME"
    echo "   sudo journalctl -u $APP_NAME -f"
    echo ""
    echo "6. Application will be available at:"
    echo "   http://your-domain.com (after SSL: https://)"
    echo ""
    echo "7. Monitor logs:"
    echo "   tail -f $LOG_DIR/app.log"
    echo ""
    log_success "Deployment script completed successfully!"
}

# Main deployment process
main() {
    log_info "Starting deployment of Earnings Gap Trading System..."
    
    check_root
    check_os
    
    # Create backup directory for rollback
    mkdir -p "$BACKUP_DIR/pre-deployment"
    
    install_system_dependencies
    create_user
    setup_directories
    setup_python_environment
    install_application
    setup_database
    setup_redis
    create_environment_file
    create_systemd_service
    setup_nginx
    setup_ssl
    setup_monitoring
    setup_backup
    setup_logrotate
    
    # Don't auto-start in production - let user configure first
    log_info "Services configured but not started - configure environment first"
    
    run_health_checks
    display_next_steps
}

# Script options
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "update")
        log_info "Updating application..."
        systemctl stop "$APP_NAME"
        install_application
        systemctl start "$APP_NAME"
        log_success "Application updated"
        ;;
    "rollback")
        log_info "Rolling back deployment..."
        systemctl stop "$APP_NAME"
        # Restore from backup (implementation depends on backup strategy)
        log_warning "Rollback functionality requires manual implementation"
        ;;
    "status")
        systemctl status "$APP_NAME"
        ;;
    "logs")
        journalctl -u "$APP_NAME" -f
        ;;
    *)
        echo "Usage: $0 {deploy|update|rollback|status|logs}"
        exit 1
        ;;
esac