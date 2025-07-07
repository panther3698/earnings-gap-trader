# Earnings Gap Trader - Setup Guide

This guide will help you set up and configure the Earnings Gap Trader system for automated trading of earnings gap opportunities in the Indian stock market.

## Prerequisites

### System Requirements
- Python 3.9 or higher
- 4GB RAM minimum (8GB recommended)
- 10GB free disk space
- Stable internet connection
- Windows, macOS, or Linux

### Trading Account Requirements
- Zerodha trading account with Kite Connect API access
- Sufficient trading capital (minimum ₹50,000 recommended)
- Basic understanding of stock trading and risks

### API Access Requirements
- Zerodha Kite Connect API subscription
- Telegram Bot API token (for notifications)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/earnings_gap_trader.git
cd earnings_gap_trader
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit the `.env` file with your configuration:

```env
# Application Configuration
DEBUG=False
HOST=0.0.0.0
PORT=8000
SECRET_KEY=your-secret-key-change-in-production

# Database Configuration
DATABASE_URL=sqlite:///./earnings_gap_trader.db

# Zerodha Kite Connect API
KITE_API_KEY=your_kite_api_key
KITE_API_SECRET=your_kite_api_secret
KITE_ACCESS_TOKEN=your_kite_access_token

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Trading Configuration
MAX_POSITION_SIZE=10000
RISK_PER_TRADE=0.02
STOP_LOSS_PERCENTAGE=0.05
TARGET_PERCENTAGE=0.10

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=earnings_gap_trader.log

# Security Configuration
ENCRYPTION_KEY=your_encryption_key_32_chars_long
```

## API Setup

### 1. Zerodha Kite Connect Setup

1. **Subscribe to Kite Connect**:
   - Login to your Zerodha account
   - Go to [console.zerodha.com](https://console.zerodha.com)
   - Subscribe to Kite Connect (₹2000/month)

2. **Create App**:
   - Click "Create new app"
   - Choose app type: "Connect"
   - Enter app name and description
   - Set redirect URL to: `http://localhost:8000/auth/callback`

3. **Get API Credentials**:
   - Note down the `API Key` and `API Secret`
   - Add these to your `.env` file

4. **Generate Access Token**:
   ```bash
   python scripts/generate_access_token.py
   ```
   - Follow the authentication flow
   - Copy the access token to your `.env` file

### 2. Telegram Bot Setup

1. **Create Bot**:
   - Message @BotFather on Telegram
   - Send `/newbot` and follow instructions
   - Note down the bot token

2. **Get Chat ID**:
   - Message your bot
   - Visit: `https://api.telegram.org/bot{BOT_TOKEN}/getUpdates`
   - Find your chat ID in the response

3. **Configure**:
   - Add bot token and chat ID to `.env` file

## Database Setup

### 1. Initialize Database

```bash
python -c "
from database import init_db
import asyncio
asyncio.run(init_db())
"
```

### 2. Verify Database Tables

```bash
python -c "
from sqlalchemy import inspect
from database import engine
inspector = inspect(engine)
print('Tables:', inspector.get_table_names())
"
```

## Configuration

### 1. Trading Parameters

Edit your trading configuration through the web interface at `http://localhost:8000/config` or modify the `.env` file:

```env
# Risk Management
MAX_POSITION_SIZE=10000        # Maximum ₹ per position
RISK_PER_TRADE=0.02           # 2% of account per trade
STOP_LOSS_PERCENTAGE=0.05     # 5% stop loss
TARGET_PERCENTAGE=0.10        # 10% target
MAX_DAILY_LOSS=5000          # Maximum daily loss limit
MAX_OPEN_POSITIONS=5         # Maximum simultaneous positions

# Strategy Parameters
MIN_GAP_PERCENTAGE=0.03       # Minimum 3% gap to trade
MAX_GAP_PERCENTAGE=0.15       # Maximum 15% gap to avoid
MIN_VOLUME_RATIO=1.5         # Minimum volume vs average
EARNINGS_WINDOW_DAYS=2        # Days around earnings to monitor
MARKET_OPEN_DELAY=15         # Minutes to wait after market open
POSITION_TIMEOUT=60          # Minutes before auto-exit
```

### 2. Security Configuration

Generate a secure encryption key:

```python
from utils.encryption import generate_key
print(generate_key())
```

Add this key to your `.env` file as `ENCRYPTION_KEY`.

## Running the System

### 1. Start the Application

```bash
python main.py
```

The system will start and be available at `http://localhost:8000`

### 2. Access the Dashboard

Open your browser and navigate to:
- Main Dashboard: `http://localhost:8000`
- Configuration: `http://localhost:8000/config`

### 3. Enable Trading

**Important**: The system starts in **Paper Trading** mode by default for safety.

To enable live trading:
1. Go to Settings page
2. Disable "Paper Trading Mode"
3. Ensure all API credentials are correct
4. Start with small position sizes

## Testing

### 1. Run Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_strategy.py

# Run with coverage
pytest --cov=.
```

### 2. Test API Connections

```bash
python scripts/test_connections.py
```

### 3. Paper Trading Test

1. Enable paper trading mode
2. Start the system
3. Monitor for earnings gaps
4. Verify orders are placed and managed correctly

## Monitoring

### 1. Log Files

Monitor the application logs:

```bash
# Follow main log
tail -f earnings_gap_trader.log

# Follow trade-specific log
tail -f trades.log

# Follow performance log
tail -f performance.log
```

### 2. Telegram Notifications

Verify Telegram notifications are working:
- Gap detection alerts
- Trade entry/exit notifications
- System status updates
- Risk management alerts

### 3. Dashboard Monitoring

Monitor real-time data on the dashboard:
- Current positions
- P&L tracking
- Gap detection status
- System health

## Security Best Practices

### 1. Environment Security

- Never commit `.env` file to version control
- Use strong, unique passwords
- Regularly rotate API keys
- Enable 2FA on all accounts

### 2. System Security

- Run on a secure server
- Use HTTPS in production
- Regularly update dependencies
- Monitor for unauthorized access

### 3. Trading Security

- Start with paper trading
- Use position limits
- Monitor daily loss limits
- Have manual override capabilities

## Troubleshooting

### Common Issues

1. **API Connection Errors**:
   ```
   Error: Invalid API credentials
   Solution: Verify API key, secret, and access token
   ```

2. **Database Errors**:
   ```
   Error: Database not found
   Solution: Run database initialization script
   ```

3. **Telegram Bot Not Working**:
   ```
   Error: Unauthorized
   Solution: Verify bot token and chat ID
   ```

4. **No Gaps Detected**:
   ```
   Issue: Scanner not finding gaps
   Solution: Check market hours and scanner configuration
   ```

### Debug Mode

Enable debug mode for detailed logging:

```env
DEBUG=True
LOG_LEVEL=DEBUG
```

### Performance Issues

If experiencing performance issues:

1. **Database Optimization**:
   ```bash
   python scripts/optimize_database.py
   ```

2. **Memory Usage**:
   - Monitor RAM usage
   - Adjust scanning frequency
   - Clear old log files

3. **Network Issues**:
   - Check internet connection
   - Verify API rate limits
   - Monitor API response times

## Production Deployment

### 1. Server Setup

For production deployment:

```bash
# Install production dependencies
pip install gunicorn supervisor

# Create systemd service
sudo cp scripts/earnings_gap_trader.service /etc/systemd/system/
sudo systemctl enable earnings_gap_trader
sudo systemctl start earnings_gap_trader
```

### 2. Reverse Proxy (Optional)

Set up Nginx for production:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. SSL Certificate

Set up SSL certificate:

```bash
sudo certbot --nginx -d your-domain.com
```

## Backup and Recovery

### 1. Database Backup

```bash
# Create backup
python scripts/backup_database.py

# Restore backup
python scripts/restore_database.py backup_file.sql
```

### 2. Configuration Backup

```bash
# Backup configuration
cp .env .env.backup.$(date +%Y%m%d)

# Backup trading data
tar -czf trading_data_backup.tar.gz *.log *.db
```

### 3. Automated Backups

Set up daily backups with cron:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /path/to/earnings_gap_trader/scripts/daily_backup.sh
```

## Support

### Getting Help

1. **Documentation**: Check this guide and API documentation
2. **Logs**: Review application logs for error details
3. **Community**: Join our Discord/Telegram community
4. **Issues**: Report bugs on GitHub

### Emergency Procedures

1. **Stop All Trading**:
   ```bash
   python scripts/emergency_stop.py
   ```

2. **Close All Positions**:
   ```bash
   python scripts/close_all_positions.py
   ```

3. **System Shutdown**:
   ```bash
   sudo systemctl stop earnings_gap_trader
   ```

---

**⚠️ Risk Disclaimer**: Trading involves substantial risk of loss. Never trade with money you cannot afford to lose. Start with paper trading and small position sizes. The developers are not responsible for any financial losses.

For additional support, please refer to the [API Guide](API_GUIDE.md) or contact support.