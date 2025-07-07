# 🚀 Installation Guide - Earnings Gap Trading System

Complete installation guide with multiple setup options to get your trading system running quickly and reliably.

## 📋 Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Setup Options](#quick-setup-options)
- [Automated Setup Wizard](#automated-setup-wizard)
- [Manual Installation](#manual-installation)
- [Validation & Testing](#validation--testing)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

## 📋 Prerequisites

### System Requirements
- **Operating System**: Windows 10+, macOS 10.14+, or Linux
- **Python**: Version 3.9 or higher ([Download Python](https://python.org/downloads/))
- **Memory**: Minimum 4GB RAM (8GB+ recommended)
- **Storage**: At least 2GB free disk space
- **Internet**: Stable connection for downloading dependencies and trading APIs

### Trading Account Requirements
- **Zerodha Demat Account** with Kite Connect API access
- **API Credentials**: API Key, API Secret, User ID
- **Access Token**: Generated daily for live trading
- **Telegram Account** (optional, for notifications)

### Required Credentials Checklist
Before starting installation, gather these credentials:

#### Zerodha API (Required)
- [ ] **API Key**: Get from [Kite Connect](https://kite.trade/)
- [ ] **API Secret**: Provided with API Key
- [ ] **User ID**: Your Zerodha client ID
- [ ] **Access Token**: Generate daily for live trading

#### Telegram Bot (Optional)
- [ ] **Bot Token**: Get from [@BotFather](https://t.me/BotFather)
- [ ] **Chat ID**: Your personal chat ID or group chat ID

## 🎯 Quick Setup Options

Choose the setup method that works best for you:

### Option 1: One-Click Automated Setup (Recommended)
**Easiest and fastest way to get started**

#### Windows Users:
```batch
# Double-click setup.bat file OR run in Command Prompt:
setup.bat
```

#### macOS/Linux Users:
```bash
# Run in terminal:
chmod +x setup.sh
./setup.sh
```

#### Python Users (Any Platform):
```bash
python setup_trading_system.py
```

### Option 2: Manual Installation
For users who prefer control over each step - see [Manual Installation](#manual-installation) section.

### Option 3: Docker Installation
For containerized deployment - see [Docker Setup](#docker-setup) section.

## 🧙‍♂️ Automated Setup Wizard

The automated wizard provides a guided, interactive setup experience with beautiful terminal interface.

### What the Wizard Does

#### Step 1: System Validation ✅
- Checks Python version compatibility
- Verifies internet connectivity
- Confirms sufficient disk space
- Validates operating system

#### Step 2: Environment Setup 🏗️
- Creates isolated virtual environment
- Downloads and installs all dependencies
- Sets up proper Python paths
- Configures development environment

#### Step 3: Credential Collection 🔐
- Securely prompts for API credentials
- Validates credential formats
- Tests API connections
- Encrypts and stores credentials safely

#### Step 4: System Configuration ⚙️
- Generates comprehensive .env file
- Sets safe trading defaults
- Configures logging and monitoring
- Creates backup configurations

#### Step 5: Database Setup 🗄️
- Creates SQLite database
- Initializes trading tables
- Sets up performance indexes
- Validates database connectivity

#### Step 6: System Testing ✅
- Tests all API connections
- Validates file permissions
- Checks port availability
- Runs comprehensive health checks

#### Step 7: First Launch 🚀
- Starts the trading system
- Opens web dashboard
- Sends test notifications
- Confirms system ready

### Running the Wizard

The wizard provides beautiful, colored output:

```
🚀 EARNINGS GAP TRADING SYSTEM SETUP
================================================================
          AUTOMATED SETUP WIZARD
================================================================

[1/9] STEP 1: System Requirements Check
✅ Python 3.11.2 detected
✅ Internet connection active
✅ 15.3GB disk space available

[2/9] STEP 2: Virtual Environment Setup
Creating virtual environment...
✅ Virtual environment created successfully

[3/9] STEP 3: Installing Dependencies
Installing fastapi... ✅
Installing kiteconnect... ✅
[████████████████████████████████] 100%

[4/9] STEP 4: Zerodha API Configuration
Enter your Zerodha API Key: [user input]
Enter your Zerodha API Secret: [hidden]
✅ API credentials validated successfully

[5/9] STEP 5: Telegram Bot Setup (Optional)
Do you want to setup Telegram notifications? (y/n): y
✅ Bot connection successful: TradingBot

[6/9] STEP 6: System Configuration
Generating secure configuration...
✅ .env file created successfully

[7/9] STEP 7: Database Setup
Creating trading database...
✅ Database initialized successfully

[8/9] STEP 8: System Validation
Testing Zerodha API connection... ✅
Testing Telegram bot... ✅
Testing database connection... ✅

[9/9] STEP 9: First Startup
Starting trading system...
✅ System started successfully
🌐 Dashboard available at: http://localhost:8000

🎉 SETUP COMPLETE! Your trading system is ready.
```

## 🔧 Manual Installation

For users who prefer step-by-step manual installation:

### Step 1: Download and Extract
```bash
# Clone or download the project
git clone https://github.com/your-repo/earnings-gap-trader.git
cd earnings-gap-trader

# OR extract downloaded ZIP file
```

### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
# Upgrade pip first
pip install --upgrade pip

# Install all requirements
pip install -r requirements.txt
```

### Step 4: Create Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials (use any text editor)
nano .env    # Linux/Mac
notepad .env # Windows
```

**Required .env Variables:**
```bash
# API Credentials
KITE_API_KEY=your_zerodha_api_key
KITE_API_SECRET=your_zerodha_api_secret
KITE_USER_ID=your_zerodha_user_id
KITE_ACCESS_TOKEN=your_daily_access_token

# Optional Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Step 5: Initialize Database
```bash
python -c "from database import init_db; import asyncio; asyncio.run(init_db())"
```

### Step 6: Validate Setup
```bash
python scripts/validate_setup.py
```

### Step 7: Start System
```bash
python main.py
```

## 🐳 Docker Setup

For containerized deployment:

### Quick Docker Start
```bash
# Using docker-compose (recommended)
docker-compose up -d

# Or build and run manually
docker build -t earnings-gap-trader .
docker run -p 8000:8000 earnings-gap-trader
```

### Docker with Custom Configuration
```bash
# Copy and edit environment file
cp .env.production.example .env.production
# Edit .env.production with your credentials

# Start with production configuration
docker-compose -f docker-compose.prod.yml up -d
```

## ✅ Validation & Testing

### Automatic Validation
```bash
# Run comprehensive validation
python scripts/validate_setup.py

# Expected output:
# ✅ Python Version: Python 3.11.2
# ✅ Project Structure: All files present
# ✅ Dependencies: All packages installed
# ✅ Configuration: .env file properly formatted
# ✅ Database: Database with 5 tables
# ✅ File Permissions: Read/write permissions OK
# 🎉 VALIDATION PASSED! System is ready.
```

### Manual Testing
```bash
# Test database connection
python -c "import sqlite3; print('✅ DB OK' if sqlite3.connect('trading_system.db').execute('SELECT 1').fetchone() else '❌ DB FAIL')"

# Test imports
python -c "import config, database; print('✅ Imports OK')"

# Test web server
python main.py
# Open http://localhost:8000 in browser
```

### Paper Trading Test
```bash
# Ensure paper trading is enabled
grep "PAPER_TRADING=True" .env

# Start system and test signal generation
python main.py
# Monitor dashboard for signal detection
```

## 🚨 Troubleshooting

### Common Installation Issues

#### Python Not Found
**Error**: `'python' is not recognized as an internal or external command`

**Solutions**:
- Install Python from [python.org](https://python.org/downloads/)
- Check "Add Python to PATH" during installation
- Restart terminal after installation
- Try `python3` instead of `python`

#### Permission Denied
**Error**: `Permission denied` when creating files

**Solutions**:
```bash
# Windows: Run Command Prompt as Administrator
# macOS/Linux: Fix permissions
sudo chown -R $USER:$USER .
chmod +x setup.sh
```

#### Virtual Environment Issues
**Error**: Virtual environment creation fails

**Solutions**:
```bash
# Install venv module
pip install virtualenv

# Or use alternative
python -m pip install virtualenv
python -m virtualenv venv
```

#### Dependency Installation Fails
**Error**: Package installation errors

**Solutions**:
```bash
# Update pip
pip install --upgrade pip

# Use specific Python version
python3.9 -m pip install -r requirements.txt

# Install with user flag
pip install --user -r requirements.txt

# Clear pip cache
pip cache purge
```

#### API Connection Issues
**Error**: Cannot connect to Zerodha API

**Solutions**:
- Verify API credentials are correct
- Check if access token is fresh (daily update required)
- Ensure API permissions are enabled in Kite Connect
- Test network connectivity
- Disable VPN temporarily

#### Port 8000 In Use
**Error**: `Port 8000 is already in use`

**Solutions**:
```bash
# Find process using port
lsof -ti:8000    # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>    # macOS/Linux
taskkill /PID <PID> /F  # Windows

# Or use different port in .env
PORT=8001
```

#### Database Initialization Fails
**Error**: Cannot create database

**Solutions**:
- Check disk space availability
- Verify write permissions in project directory
- Delete existing database file: `rm trading_system.db`
- Run initialization again

### Debug Mode

Run setup with debug information:
```bash
python setup_trading_system.py --debug
```

### Log Files
Check these log files for detailed error information:
- **Setup Log**: `setup.log`
- **Application Log**: `trading_system.log`
- **System Error**: Console output

### Getting Help

#### Self-Help Resources
1. **Validation Tool**: `python scripts/validate_setup.py`
2. **Quick Start Guide**: `QUICK_START.md`
3. **User Manual**: `USER_GUIDE.md`
4. **Deployment Guide**: `DEPLOYMENT.md`

#### Support Channels
- **GitHub Issues**: Report bugs and get help
- **Documentation**: Complete guides and references
- **Community Forums**: Connect with other users
- **Email Support**: For urgent technical issues

## 🎯 Next Steps

After successful installation:

### 1. Explore the Dashboard 📊
- Open `http://localhost:8000`
- Review system status
- Check configuration settings
- Familiarize with interface

### 2. Test Paper Trading 🧪
- Verify paper trading mode is enabled
- Monitor signal detection
- Test risk management
- Review trade execution logs

### 3. Configure Notifications 📱
- Test Telegram bot functionality
- Set up email alerts (optional)
- Configure alert preferences
- Test emergency notifications

### 4. Review Risk Settings ⚠️
- Check position limits
- Adjust risk parameters
- Set daily loss limits
- Configure circuit breakers

### 5. Prepare for Live Trading 💰
- **IMPORTANT**: Only after thorough testing
- Update access token daily
- Set `PAPER_TRADING=False`
- Start with small positions
- Monitor system closely

## 🔐 Security Considerations

### Credential Security
- Never share your `.env` file
- Keep API credentials private
- Rotate access tokens daily
- Use strong passwords
- Enable 2FA where possible

### System Security
- Run on secure networks
- Keep system updated
- Monitor access logs
- Use firewall protection
- Regular security audits

### Trading Security
- Always start with paper trading
- Use conservative risk limits
- Never risk more than you can afford to lose
- Have emergency stop procedures
- Monitor system performance regularly

## 📚 Additional Resources

### Documentation
- **README.md**: Project overview and features
- **USER_GUIDE.md**: Complete user manual
- **DEPLOYMENT.md**: Production deployment guide
- **API_GUIDE.md**: API reference and integration

### Video Tutorials
- **Installation Walkthrough**: Step-by-step video guide
- **Configuration Tutorial**: Setting up credentials
- **Dashboard Overview**: Interface explanation
- **Paper Trading Demo**: Safe testing procedures

### Community Resources
- **Discord Server**: Real-time chat and support
- **Reddit Community**: r/AlgoTrading discussions
- **YouTube Channel**: Video tutorials and updates
- **Blog**: Trading strategies and system updates

---

## 🎉 Welcome to Algorithmic Trading!

You're now ready to start your automated trading journey. Remember to:

- **Start small** and test thoroughly
- **Monitor regularly** and adjust as needed
- **Stay informed** about market conditions
- **Trade responsibly** within your limits

**Happy Trading! 📈🚀**

---

**Installation Guide Version**: 1.0  
**Last Updated**: July 2024  
**Compatible Platforms**: Windows, macOS, Linux  
**Python Requirements**: 3.9+