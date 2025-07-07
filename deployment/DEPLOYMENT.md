# Deployment Guide - Earnings Gap Trading System

This document provides comprehensive deployment instructions for the Earnings Gap Trading System in production environments.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Pre-deployment Checklist](#pre-deployment-checklist)
- [Deployment Options](#deployment-options)
- [Docker Deployment](#docker-deployment)
- [Manual Deployment](#manual-deployment)
- [Post-deployment Setup](#post-deployment-setup)
- [Monitoring Setup](#monitoring-setup)
- [Backup Configuration](#backup-configuration)
- [Security Hardening](#security-hardening)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- **Operating System**: Ubuntu 20.04+ LTS or CentOS 8+
- **CPU**: Minimum 2 cores, Recommended 4+ cores
- **Memory**: Minimum 4GB RAM, Recommended 8GB+
- **Storage**: Minimum 50GB SSD, Recommended 100GB+ SSD
- **Network**: Stable internet connection with low latency

### Software Dependencies
- Docker 20.10+ and Docker Compose 2.0+
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Nginx 1.18+
- Git
- Systemd (for service management)

### Trading Requirements
- Active Zerodha trading account
- Kite Connect API credentials
- Telegram bot token
- Valid email account for alerts
- SSL certificates (for HTTPS)

## Pre-deployment Checklist

### Security Checklist
- [ ] Generate strong passwords for all services
- [ ] Obtain SSL certificates for HTTPS
- [ ] Configure firewall rules
- [ ] Set up SSH key authentication
- [ ] Create dedicated user accounts
- [ ] Configure SELinux/AppArmor (if applicable)

### Infrastructure Checklist
- [ ] Provision server with adequate resources
- [ ] Configure DNS records
- [ ] Set up monitoring infrastructure
- [ ] Configure backup storage
- [ ] Test network connectivity
- [ ] Install required software dependencies

### Application Checklist
- [ ] Clone repository to server
- [ ] Configure environment variables
- [ ] Test database connectivity
- [ ] Validate API credentials
- [ ] Run application tests
- [ ] Configure logging

## Deployment Options

### Option 1: Docker Deployment (Recommended)
Best for most use cases, provides isolation and easy management.

### Option 2: Manual Deployment
For custom setups or when Docker is not available.

### Option 3: Cloud Deployment
Using cloud providers like AWS, GCP, or Azure.

## Docker Deployment

### Step 1: Prepare Environment
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.12.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Log out and back in for group changes to take effect
```

### Step 2: Clone and Configure
```bash
# Clone repository
git clone https://github.com/your-org/earnings-gap-trader.git
cd earnings-gap-trader

# Create production environment file
cp .env.production.example .env.production

# Edit configuration
nano .env.production
```

### Step 3: Configure SSL (Production)
```bash
# Create SSL directory
sudo mkdir -p /etc/ssl/earnings-gap-trader

# Copy your SSL certificates
sudo cp your-cert.pem /etc/ssl/earnings-gap-trader/cert.pem
sudo cp your-key.pem /etc/ssl/earnings-gap-trader/key.pem
sudo chmod 600 /etc/ssl/earnings-gap-trader/key.pem
```

### Step 4: Deploy with Docker Compose
```bash
# Pull latest images
docker-compose -f docker-compose.prod.yml pull

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Check service status
docker-compose -f docker-compose.prod.yml ps
```

### Step 5: Initialize Database
```bash
# Run database migrations
docker-compose -f docker-compose.prod.yml exec app python -m alembic upgrade head

# Create initial admin user (if required)
docker-compose -f docker-compose.prod.yml exec app python scripts/create_admin_user.py
```

### Step 6: Verify Deployment
```bash
# Check application health
curl -k https://localhost:8000/health

# Check logs
docker-compose -f docker-compose.prod.yml logs -f app
```

## Manual Deployment

### Step 1: System Preparation
```bash
# Create dedicated user
sudo useradd -m -s /bin/bash trader
sudo usermod -aG sudo trader

# Switch to trader user
sudo su - trader

# Create directory structure
mkdir -p /opt/earnings_gap_trader/{app,config,logs,backups}
```

### Step 2: Install Dependencies
```bash
# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Install Redis
sudo apt install -y redis-server

# Install Nginx
sudo apt install -y nginx

# Install additional tools
sudo apt install -y git curl wget htop
```

### Step 3: Setup Application
```bash
# Clone repository
cd /opt/earnings_gap_trader
git clone https://github.com/your-org/earnings-gap-trader.git app
cd app

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements-production.txt
```

### Step 4: Configure Database
```bash
# Setup PostgreSQL
sudo -u postgres createuser trader
sudo -u postgres createdb earnings_gap_trader -O trader
sudo -u postgres psql -c "ALTER USER trader PASSWORD 'secure_password';"

# Configure PostgreSQL for performance
sudo nano /etc/postgresql/14/main/postgresql.conf
# Add recommended settings for trading workload

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Step 5: Configure Services
```bash
# Copy systemd service files
sudo cp systemd/*.service /etc/systemd/system/

# Reload systemd and enable services
sudo systemctl daemon-reload
sudo systemctl enable earnings-gap-trader
sudo systemctl enable earnings-gap-trader-worker
sudo systemctl enable earnings-gap-trader-scheduler
```

### Step 6: Run Deployment Script
```bash
# Make deployment script executable
chmod +x deploy.sh

# Run deployment script
sudo ./deploy.sh
```

## Post-deployment Setup

### Verify Service Status
```bash
# Check all services
sudo systemctl status earnings-gap-trader
sudo systemctl status earnings-gap-trader-worker
sudo systemctl status earnings-gap-trader-scheduler

# Check application health
curl https://your-domain.com/health
```

### Configure Monitoring
```bash
# Start monitoring services
sudo systemctl start prometheus
sudo systemctl start grafana-server

# Enable monitoring services
sudo systemctl enable prometheus
sudo systemctl enable grafana-server
```

### Setup Backup Automation
```bash
# Add backup cron job
sudo crontab -e

# Add this line for daily backups at 2 AM
0 2 * * * /opt/earnings_gap_trader/scripts/backup.sh >> /var/log/earnings_gap_trader/backup_cron.log 2>&1
```

### Configure Log Rotation
```bash
# Create logrotate configuration
sudo nano /etc/logrotate.d/earnings-gap-trader

# Add logrotate configuration
```

## Monitoring Setup

### Prometheus Configuration
```yaml
# /etc/prometheus/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'earnings-gap-trader'
    static_configs:
      - targets: ['localhost:9000']
    scrape_interval: 5s
    metrics_path: /metrics
```

### Grafana Dashboard Setup
```bash
# Import pre-built dashboards
curl -X POST \
  http://admin:admin@localhost:3000/api/dashboards/import \
  -H 'Content-Type: application/json' \
  -d @monitoring/grafana/dashboard.json
```

### Health Monitoring
```bash
# Start health monitoring
sudo systemctl start earnings-gap-trader-health-monitor
sudo systemctl enable earnings-gap-trader-health-monitor

# Check health monitor status
sudo systemctl status earnings-gap-trader-health-monitor
```

## Backup Configuration

### Automated Backup Setup
```bash
# Test backup script
sudo /opt/earnings_gap_trader/scripts/backup.sh

# Configure S3 backup (optional)
aws configure set aws_access_key_id YOUR_ACCESS_KEY
aws configure set aws_secret_access_key YOUR_SECRET_KEY
aws configure set default.region us-east-1
```

### Backup Verification
```bash
# Test restore procedure
sudo /opt/earnings_gap_trader/scripts/restore.sh --dry-run latest

# Verify backup integrity
sudo /opt/earnings_gap_trader/scripts/backup_verify.sh
```

## Security Hardening

### Firewall Configuration
```bash
# Configure UFW firewall
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow required ports
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS

# Allow monitoring (if needed)
sudo ufw allow from trusted_ip to any port 3000  # Grafana
sudo ufw allow from trusted_ip to any port 9090  # Prometheus
```

### SSL Configuration
```bash
# Configure Nginx with SSL
sudo nano /etc/nginx/sites-available/earnings-gap-trader

# Test Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### Service Security
```bash
# Set file permissions
sudo chown -R trader:trader /opt/earnings_gap_trader
sudo chmod 640 /opt/earnings_gap_trader/config/.env*
sudo chmod +x /opt/earnings_gap_trader/scripts/*.sh

# Configure service security
sudo systemctl edit earnings-gap-trader
# Add security restrictions in override.conf
```

## Environment-Specific Configurations

### Development Environment
```bash
# Use development compose file
docker-compose -f docker-compose.dev.yml up -d

# Enable debug mode
export DEBUG=True
export LOG_LEVEL=DEBUG
```

### Staging Environment
```bash
# Use staging configuration
cp .env.staging.example .env.staging

# Deploy to staging
docker-compose -f docker-compose.staging.yml up -d
```

### Production Environment
```bash
# Use production configuration with security hardening
cp .env.production.example .env.production

# Deploy with full monitoring and backup
docker-compose -f docker-compose.prod.yml up -d
```

## Load Balancing and High Availability

### Nginx Load Balancer
```nginx
# /etc/nginx/sites-available/earnings-gap-trader-lb
upstream earnings_gap_trader {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/ssl/earnings-gap-trader/cert.pem;
    ssl_certificate_key /etc/ssl/earnings-gap-trader/key.pem;
    
    location / {
        proxy_pass http://earnings_gap_trader;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Database Replication
```bash
# Configure PostgreSQL streaming replication
# Primary server configuration
sudo nano /etc/postgresql/14/main/postgresql.conf

# Replica server configuration
sudo nano /etc/postgresql/14/main/recovery.conf
```

## Performance Optimization

### Database Optimization
```sql
-- PostgreSQL performance tuning
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Reload configuration
SELECT pg_reload_conf();
```

### Application Optimization
```bash
# Configure worker processes
export WORKERS=4
export WORKER_CLASS=uvicorn.workers.UvicornWorker
export WORKER_CONNECTIONS=1000

# Configure memory limits
export WORKER_MEMORY_LIMIT=1GB
export MAX_CONNECTIONS=100
```

### Redis Optimization
```bash
# Configure Redis for performance
sudo nano /etc/redis/redis.conf

# Key settings:
# maxmemory 512mb
# maxmemory-policy allkeys-lru
# save 900 1
# save 300 10
# save 60 10000
```

## Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check service status
sudo systemctl status earnings-gap-trader

# Check logs
sudo journalctl -u earnings-gap-trader -f

# Check application logs
tail -f /var/log/earnings_gap_trader/app.log
```

#### Database Connection Issues
```bash
# Test database connectivity
psql -h localhost -U trader -d earnings_gap_trader -c "SELECT 1;"

# Check PostgreSQL status
sudo systemctl status postgresql

# Check database logs
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

#### High Memory Usage
```bash
# Check memory usage
free -h
htop

# Check application memory usage
ps aux | grep earnings
docker stats

# Optimize memory settings
export WORKER_MEMORY_LIMIT=512MB
```

#### Slow Performance
```bash
# Check system resources
iostat -x 1
vmstat 1

# Check database performance
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"

# Check application metrics
curl http://localhost:9000/metrics
```

### Log Analysis
```bash
# Application logs
tail -f /var/log/earnings_gap_trader/app.log

# System logs
sudo journalctl -f

# Docker logs
docker-compose logs -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Performance Monitoring
```bash
# System performance
htop
iotop
nethogs

# Application performance
curl http://localhost:8000/metrics
curl http://localhost:8000/health

# Database performance
sudo -u postgres psql -c "SELECT * FROM pg_stat_database;"
```

## Maintenance Procedures

### Regular Maintenance Tasks
```bash
# Weekly tasks
- Update system packages
- Review logs for errors
- Check backup integrity
- Monitor disk space
- Review performance metrics

# Monthly tasks
- Update application dependencies
- Review security settings
- Test disaster recovery procedures
- Update documentation
- Performance optimization review
```

### Update Procedures
```bash
# Application updates
git pull origin main
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# System updates
sudo apt update && sudo apt upgrade -y
sudo systemctl restart earnings-gap-trader
```

### Scaling Procedures
```bash
# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale worker=4

# Add new server
# Configure load balancer
# Update DNS records
# Test failover procedures
```

## Support and Documentation

### Getting Help
- Check application logs first
- Review this deployment guide
- Check system resource usage
- Test network connectivity
- Review configuration files

### Documentation Updates
This deployment guide should be updated when:
- New features are added
- Infrastructure changes are made
- Security requirements change
- Performance optimizations are implemented

### Emergency Contacts
- System Administrator: admin@trading-system.com
- Technical Support: support@trading-system.com
- Emergency Hotline: +1-555-EMERGENCY

---

**Last Updated**: January 2024  
**Version**: 1.0  
**Next Review**: July 2024