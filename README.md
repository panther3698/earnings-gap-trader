# Earnings Gap Trading System

A comprehensive automated trading system designed to identify and capitalize on earnings-related gap opportunities in the Indian stock market using Zerodha Kite Connect API.

![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-production--ready-green.svg)
![Testing](https://img.shields.io/badge/tests-passing-brightgreen.svg)
![Deployment](https://img.shields.io/badge/deployment-docker--ready-blue.svg)

## 🚀 Features

### Core Trading Features
- **Automated Earnings Gap Detection**: Real-time scanning for pre/post earnings price gaps
- **Intelligent Risk Management**: Position sizing, stop-loss, and profit targets
- **Multi-Strategy Support**: Customizable trading strategies and parameters
- **Paper Trading Mode**: Safe testing environment before live trading
- **Real-time Order Management**: Automated order placement and execution monitoring

### Technology Stack
- **Backend**: FastAPI with async/await support
- **Database**: SQLAlchemy with SQLite (PostgreSQL ready)
- **Market Data**: Zerodha Kite Connect + Yahoo Finance fallback
- **Frontend**: Modern responsive web dashboard with real-time updates
- **Notifications**: Telegram bot integration for alerts
- **Security**: End-to-end encryption for sensitive data

### Advanced Features
- **WebSocket Real-time Updates**: Live price feeds and trade notifications
- **Professional Dashboard**: Comprehensive trading interface with charts
- **Comprehensive Logging**: Detailed audit trails and performance monitoring
- **Backup & Recovery**: Automated data backup and disaster recovery
- **API Integration**: RESTful API for external integrations

## 📁 Project Structure

```
earnings_gap_trader/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration management
├── database.py            # Database setup and connections
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
├── README.md             # This file
│
├── models/               # Data models and schemas
│   ├── __init__.py
│   ├── trade_models.py   # Trading-related database models
│   └── config_models.py  # Configuration models
│
├── core/                 # Core trading system components
│   ├── __init__.py
│   ├── earnings_scanner.py    # Earnings events and gap detection
│   ├── risk_manager.py        # Risk management and position sizing
│   ├── market_data.py         # Real-time market data provider
│   ├── order_engine.py        # Order execution and management
│   └── telegram_service.py    # Telegram notifications
│
├── frontend/             # Web interface
│   ├── static/          # Static assets (CSS, JS, images)
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   └── templates/       # HTML templates
│       ├── base.html
│       ├── dashboard.html
│       └── config.html
│
├── utils/               # Utility modules
│   ├── __init__.py
│   ├── encryption.py    # Data encryption utilities
│   ├── validators.py    # Input validation functions
│   └── logging_config.py # Logging configuration
│
├── tests/               # Test suite
│   ├── __init__.py
│   ├── test_strategy.py # Strategy and scanner tests
│   └── test_execution.py # Execution and integration tests
│
└── docs/                # Documentation
    ├── SETUP.md         # Detailed setup instructions
    └── API_GUIDE.md     # API documentation
```

## 🚀 Quick Start

### One-Command Setup (Recommended)

Get your trading system running in minutes with our automated setup wizard:

**Windows:**
```batch
setup.bat
```

**macOS/Linux:**
```bash
./setup.sh
```

**Any Platform:**
```bash
python scripts/setup_trading_system.py
```

The interactive wizard will guide you through:
- ✅ System requirements validation
- 🔧 Automatic dependency installation  
- 🔐 Secure credential collection
- ⚙️ System configuration
- 🗄️ Database initialization
- 🚀 First startup

### Manual Installation (Alternative)

For step-by-step manual setup, see [INSTALLATION.md](docs/INSTALLATION.md)

### Prerequisites
- **Python 3.9+** ([Download](https://python.org/downloads/))
- **Zerodha account** with API access ([Get API](https://kite.trade/))
- **Telegram Bot** (optional, for notifications)
- **4GB+ RAM, 2GB+ disk space**

### Setup Options
- 📋 **[GET_STARTED.md](docs/GET_STARTED.md)** - Choose your setup method
- 🚀 **[QUICK_START.md](docs/QUICK_START.md)** - Quick setup guide  
- 🔧 **[INSTALLATION.md](docs/INSTALLATION.md)** - Detailed installation
- 📖 **[USER_GUIDE.md](deployment/USER_GUIDE.md)** - Complete user manual

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following configuration:

```env
# Application Settings
DEBUG=False
HOST=0.0.0.0
PORT=8000
SECRET_KEY=your-secret-key-change-in-production

# Database
DATABASE_URL=sqlite:///./earnings_gap_trader.db

# Zerodha Kite Connect API
KITE_API_KEY=your_kite_api_key
KITE_API_SECRET=your_kite_api_secret  
KITE_ACCESS_TOKEN=your_kite_access_token

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Trading Parameters
MAX_POSITION_SIZE=10000        # Maximum ₹ per position
RISK_PER_TRADE=0.02           # 2% of account per trade
STOP_LOSS_PERCENTAGE=0.05     # 5% stop loss
TARGET_PERCENTAGE=0.10        # 10% profit target
MAX_DAILY_LOSS=5000          # Maximum daily loss limit
MAX_OPEN_POSITIONS=5         # Maximum simultaneous positions

# Strategy Parameters  
MIN_GAP_PERCENTAGE=0.03       # Minimum 3% gap to trade
MAX_GAP_PERCENTAGE=0.15       # Maximum 15% gap limit
MIN_VOLUME_RATIO=1.5         # Minimum volume vs average
EARNINGS_WINDOW_DAYS=2        # Days around earnings to monitor

# Security
ENCRYPTION_KEY=your_encryption_key_32_chars_long

# Logging
LOG_LEVEL=INFO
LOG_FILE=earnings_gap_trader.log
```

### Trading Configuration

The system supports extensive configuration through both the web interface and environment variables:

- **Risk Management**: Position sizing, stop-loss levels, daily loss limits
- **Strategy Parameters**: Gap thresholds, volume requirements, timing settings
- **Market Data**: Update intervals, data sources, fallback options
- **Notifications**: Telegram alerts, email notifications, webhook integrations

## 📊 Dashboard Features

### Real-time Trading Dashboard
- **Live P&L Tracking**: Real-time profit/loss monitoring with charts
- **Position Management**: Current positions with unrealized P&L
- **Gap Detection Scanner**: Live earnings gap detection with alerts
- **Risk Monitoring**: Real-time risk metrics and limit tracking
- **Order Management**: Order status tracking and execution monitoring

### Key Dashboard Sections
1. **Portfolio Overview**: Account balance, margin usage, daily P&L
2. **Active Positions**: Current holdings with real-time prices
3. **Gap Scanner**: Live earnings gap detection results
4. **Recent Trades**: Trade history with performance metrics
5. **System Status**: Trading system health and connectivity
6. **Risk Dashboard**: Position limits and risk utilization

## 🔧 API Integration

### REST API Endpoints

The system provides a comprehensive REST API for external integrations:

```python
# Get system status
GET /api/system/status

# Portfolio information
GET /api/portfolio/summary
GET /api/portfolio/positions

# Trading operations
GET /api/trades
POST /api/trades
POST /api/trades/{id}/close

# Gap detection
GET /api/gaps
POST /api/gaps/scan

# Configuration
GET /api/config/trading
PUT /api/config/trading
```

### WebSocket Real-time Updates

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

// Subscribe to real-time updates
ws.send(JSON.stringify({
    type: 'subscribe',
    payload: {
        subscriptions: ['price_updates', 'gap_alerts', 'trade_updates']
    }
}));
```

## 🤖 Telegram Integration

The system includes comprehensive Telegram bot integration for:

- **Gap Detection Alerts**: Instant notifications when earnings gaps are detected
- **Trade Notifications**: Entry/exit alerts with P&L information
- **Risk Alerts**: Warnings when approaching risk limits
- **System Status**: Health monitoring and connectivity updates
- **Remote Control**: Basic trading controls via Telegram commands

### Available Telegram Commands
- `/status` - Get system status
- `/positions` - View current positions
- `/pnl` - Daily P&L summary
- `/stop` - Stop automated trading
- `/resume` - Resume automated trading
- `/balance` - Account balance information

## 🛡️ Security Features

### Data Protection
- **End-to-end Encryption**: All sensitive data encrypted using Fernet symmetric encryption
- **Secure API Communication**: HTTPS/WSS protocols for all external communications
- **Credential Management**: Encrypted storage of API keys and tokens
- **Access Control**: Session-based authentication and authorization

### Risk Management
- **Position Limits**: Maximum position size and concurrent position limits
- **Daily Loss Limits**: Automatic trading suspension on excessive losses
- **Drawdown Protection**: Real-time monitoring of account drawdowns
- **Paper Trading Mode**: Safe testing environment with simulated trading

## 📈 Trading Strategy

### Earnings Gap Strategy

The system implements a sophisticated earnings gap trading strategy:

1. **Gap Detection**: Identifies significant price gaps after earnings announcements
2. **Volume Confirmation**: Validates gaps with above-average trading volume
3. **Technical Analysis**: Incorporates RSI, moving averages, and support/resistance
4. **Risk Assessment**: Calculates position size based on account risk parameters
5. **Execution**: Automated order placement with stop-loss and profit targets

### Strategy Parameters
- **Gap Threshold**: Minimum gap percentage (default: 3%)
- **Volume Ratio**: Minimum volume vs average (default: 1.5x)
- **Time Window**: Earnings announcement window (default: 2 days)
- **Position Timeout**: Maximum holding period (default: 60 minutes)

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_strategy.py
pytest tests/test_execution.py

# Run with coverage report
pytest --cov=. --cov-report=html
```

### Test Categories
- **Strategy Tests**: Earnings detection, gap calculation, technical analysis
- **Execution Tests**: Order placement, risk management, portfolio tracking
- **Integration Tests**: API endpoints, WebSocket connections, database operations
- **Performance Tests**: Load testing, memory usage, execution speed

## 📚 Documentation

Comprehensive documentation is available:

- **[Setup Guide](docs/SETUP.md)**: Detailed installation and configuration instructions
- **[API Guide](docs/API_GUIDE.md)**: Complete API reference and integration examples
- **Code Documentation**: Inline docstrings and type hints throughout codebase

## 🔄 Production Deployment

### Docker Deployment (Recommended)

```bash
# Build Docker image
docker build -t earnings-gap-trader .

# Run with Docker Compose
docker-compose up -d
```

### Traditional Deployment

```bash
# Install production dependencies
pip install gunicorn supervisor

# Start with Gunicorn
gunicorn main:app --bind 0.0.0.0:8000 --workers 4

# Set up systemd service
sudo cp scripts/earnings_gap_trader.service /etc/systemd/system/
sudo systemctl enable earnings_gap_trader
sudo systemctl start earnings_gap_trader
```

### Production Checklist
- [ ] Configure HTTPS/SSL certificates
- [ ] Set up database backups
- [ ] Configure log rotation
- [ ] Set up monitoring and alerting
- [ ] Implement firewall rules
- [ ] Configure reverse proxy (Nginx/Apache)

## 📊 Performance & Monitoring

### System Monitoring
- **Application Performance**: Response times, memory usage, CPU utilization
- **Trading Performance**: Win rate, profit factor, Sharpe ratio, maximum drawdown
- **System Health**: Database connections, API connectivity, error rates

### Logging & Audit Trails
- **Trade Logs**: Detailed records of all trading activities
- **System Logs**: Application events, errors, and performance metrics
- **Audit Logs**: Configuration changes and administrative actions

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/new-feature`
3. **Make changes and add tests**
4. **Run the test suite**: `pytest`
5. **Submit a pull request**

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run code formatting
black .
flake8 .
mypy .
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Risk Disclaimer

**IMPORTANT RISK WARNING**: Trading involves substantial risk of loss and is not suitable for all investors. Past performance is not indicative of future results. Never trade with money you cannot afford to lose.

- This software is provided for educational and research purposes
- The developers are not responsible for any financial losses
- Always start with paper trading to test strategies
- Understand the risks before enabling live trading
- Consider consulting with a financial advisor

## 🆘 Support & Community

### Getting Help
- **Documentation**: Check the [Setup Guide](docs/SETUP.md) and [API Guide](docs/API_GUIDE.md)
- **Issues**: Report bugs and feature requests on [GitHub Issues](https://github.com/your-username/earnings_gap_trader/issues)
- **Discussions**: Join our [GitHub Discussions](https://github.com/your-username/earnings_gap_trader/discussions)

### Community Links
- **Discord**: [Join our Discord community](https://discord.gg/your-invite)
- **Telegram**: [Trading discussions group](https://t.me/your-group)
- **YouTube**: [Video tutorials and updates](https://youtube.com/your-channel)

### Commercial Support
For commercial deployments and custom development, contact: support@yourdomain.com

## 🎯 Roadmap

### Upcoming Features
- [ ] **Multi-Exchange Support**: BSE, NSE F&O integration
- [ ] **Advanced Strategies**: Mean reversion, momentum trading
- [ ] **Machine Learning**: AI-powered gap prediction models
- [ ] **Options Trading**: Options strategies for earnings plays
- [ ] **Mobile App**: React Native mobile application
- [ ] **Cloud Deployment**: AWS/GCP deployment templates
- [ ] **Portfolio Analytics**: Advanced performance analytics
- [ ] **Social Trading**: Copy trading and strategy sharing

### Long-term Vision
- Multi-asset class support (commodities, forex, crypto)
- Institutional-grade risk management
- Regulatory compliance tools
- Advanced backtesting engine
- Strategy marketplace

---

## 📞 Contact

- **Email**: contact@yourdomain.com
- **Website**: https://yourdomain.com
- **GitHub**: https://github.com/your-username/earnings_gap_trader

---

**Built with ❤️ for the Indian trading community**

*"Successful trading is about risk management, not predictions."*