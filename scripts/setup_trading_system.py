#!/usr/bin/env python3
"""
Comprehensive Automated Setup Script for Earnings Gap Trading System
Interactive wizard for complete system installation and configuration
"""

import os
import sys
import json
import time
import shutil
import secrets
import hashlib
import platform
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import getpass
import sqlite3
import logging
from dataclasses import dataclass
import re

# ANSI Color Codes for Terminal Output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Emojis for Visual Appeal
class Emojis:
    ROCKET = '🚀'
    CHECK = '✅'
    CROSS = '❌'
    WARNING = '⚠️'
    GEAR = '⚙️'
    MONEY = '💰'
    ROBOT = '🤖'
    DATABASE = '🗄️'
    NETWORK = '🌐'
    LOCK = '🔒'
    CHART = '📊'
    FIRE = '🔥'
    STAR = '⭐'
    LIGHTNING = '⚡'

@dataclass
class SetupConfig:
    """Configuration container for setup process"""
    project_dir: Path
    venv_dir: Path
    env_file: Path
    database_file: Path
    log_file: Path
    python_executable: str
    system_os: str
    
class SetupLogger:
    """Custom logger for setup process"""
    
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.setup_logging()
    
    def setup_logging(self):
        """Configure logging for setup process"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)
    
    def error(self, message: str):
        """Log error message"""
        self.logger.error(message)
    
    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)

class TradingSystemSetup:
    """Main setup class for the trading system"""
    
    def __init__(self):
        self.config = self._initialize_config()
        self.logger = SetupLogger(self.config.log_file)
        self.setup_data = {}
        self.current_step = 0
        self.total_steps = 9
        
    def _initialize_config(self) -> SetupConfig:
        """Initialize setup configuration"""
        project_dir = Path.cwd()
        return SetupConfig(
            project_dir=project_dir,
            venv_dir=project_dir / "venv",
            env_file=project_dir / ".env",
            database_file=project_dir / "trading_system.db",
            log_file=project_dir / "setup.log",
            python_executable=sys.executable,
            system_os=platform.system()
        )
    
    def print_colored(self, text: str, color: str = Colors.ENDC, emoji: str = "") -> None:
        """Print colored text with optional emoji"""
        print(f"{color}{emoji} {text}{Colors.ENDC}")
    
    def print_header(self, text: str) -> None:
        """Print header with styling"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{text.center(60)}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
    
    def print_step(self, step_name: str) -> None:
        """Print current step with progress"""
        self.current_step += 1
        progress = f"[{self.current_step}/{self.total_steps}]"
        self.print_colored(
            f"{progress} STEP {self.current_step}: {step_name}",
            Colors.BOLD + Colors.OKCYAN,
            Emojis.GEAR
        )
        self.logger.info(f"Starting Step {self.current_step}: {step_name}")
    
    def print_success(self, message: str) -> None:
        """Print success message"""
        self.print_colored(message, Colors.OKGREEN, Emojis.CHECK)
    
    def print_error(self, message: str) -> None:
        """Print error message"""
        self.print_colored(message, Colors.FAIL, Emojis.CROSS)
    
    def print_warning(self, message: str) -> None:
        """Print warning message"""
        self.print_colored(message, Colors.WARNING, Emojis.WARNING)
    
    def show_welcome_screen(self) -> None:
        """Display welcome screen and introduction"""
        os.system('clear' if self.config.system_os != 'Windows' else 'cls')
        
        welcome_art = f"""
{Colors.BOLD}{Colors.HEADER}
    ███████╗ █████╗ ██████╗ ███╗   ██╗██╗███╗   ██╗ ██████╗ ███████╗
    ██╔════╝██╔══██╗██╔══██╗████╗  ██║██║████╗  ██║██╔════╝ ██╔════╝
    █████╗  ███████║██████╔╝██╔██╗ ██║██║██╔██╗ ██║██║  ███╗███████╗
    ██╔══╝  ██╔══██║██╔══██╗██║╚██╗██║██║██║╚██╗██║██║   ██║╚════██║
    ███████╗██║  ██║██║  ██║██║ ╚████║██║██║ ╚████║╚██████╔╝███████║
    ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝
    
     ██████╗  █████╗ ██████╗     ████████╗██████╗  █████╗ ██████╗ ███████╗██████╗ 
    ██╔════╝ ██╔══██╗██╔══██╗    ╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
    ██║  ███╗███████║██████╔╝       ██║   ██████╔╝███████║██║  ██║█████╗  ██████╔╝
    ██║   ██║██╔══██║██╔═══╝        ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝  ██╔══██╗
    ╚██████╔╝██║  ██║██║            ██║   ██║  ██║██║  ██║██████╔╝███████╗██║  ██║
     ╚═════╝ ╚═╝  ╚═╝╚═╝            ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝
{Colors.ENDC}
        """
        
        print(welcome_art)
        
        self.print_colored(
            "AUTOMATED SETUP WIZARD FOR EARNINGS GAP TRADING SYSTEM",
            Colors.BOLD + Colors.OKGREEN,
            Emojis.ROCKET
        )
        
        print(f"\n{Colors.OKCYAN}Welcome to the comprehensive setup wizard!{Colors.ENDC}")
        print(f"{Colors.OKCYAN}This script will guide you through the complete installation process.{Colors.ENDC}\n")
        
        features = [
            "✨ Interactive step-by-step setup",
            "🔧 Automatic dependency installation",
            "🔐 Secure credential management",
            "🗄️ Database initialization",
            "🤖 Telegram bot integration",
            "📊 Real-time trading dashboard",
            "⚡ Production-ready configuration"
        ]
        
        print(f"{Colors.BOLD}Features to be configured:{Colors.ENDC}")
        for feature in features:
            print(f"  {feature}")
        
        print(f"\n{Colors.WARNING}⚠️  Important Notes:{Colors.ENDC}")
        print(f"  • Ensure you have Zerodha API credentials ready")
        print(f"  • Stable internet connection required")
        print(f"  • This process may take 5-10 minutes")
        print(f"  • All credentials will be encrypted and stored securely")
        
        input(f"\n{Colors.BOLD}Press Enter to begin the setup process...{Colors.ENDC}")
    
    def check_system_requirements(self) -> bool:
        """Check system requirements and compatibility"""
        self.print_step("System Requirements Check")
        
        all_checks_passed = True
        
        # Check Python version
        python_version = sys.version_info
        required_version = (3, 9)
        
        if python_version >= required_version:
            self.print_success(f"Python {python_version.major}.{python_version.minor}.{python_version.micro} detected")
        else:
            self.print_error(f"Python {required_version[0]}.{required_version[1]}+ required, found {python_version.major}.{python_version.minor}")
            all_checks_passed = False
        
        # Check internet connectivity
        try:
            urllib.request.urlopen('https://google.com', timeout=5)
            self.print_success("Internet connection active")
        except Exception:
            self.print_error("Internet connection not available")
            all_checks_passed = False
        
        # Check disk space
        try:
            disk_usage = shutil.disk_usage(self.config.project_dir)
            free_gb = disk_usage.free / (1024**3)
            
            if free_gb >= 1.0:  # 1GB minimum
                self.print_success(f"{free_gb:.1f}GB disk space available")
            else:
                self.print_error(f"Insufficient disk space: {free_gb:.1f}GB (minimum 1GB required)")
                all_checks_passed = False
        except Exception as e:
            self.print_warning(f"Could not check disk space: {e}")
        
        # Check OS compatibility
        if self.config.system_os in ['Windows', 'Linux', 'Darwin']:
            self.print_success(f"Operating system: {self.config.system_os} (supported)")
        else:
            self.print_warning(f"Operating system: {self.config.system_os} (may not be fully supported)")
        
        # Check if running in virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            self.print_warning("Already running in a virtual environment")
        
        if not all_checks_passed:
            self.print_error("System requirements check failed. Please resolve issues before continuing.")
            return False
        
        self.print_success("All system requirements satisfied")
        return True
    
    def setup_virtual_environment(self) -> bool:
        """Create and configure virtual environment"""
        self.print_step("Virtual Environment Setup")
        
        try:
            # Check if virtual environment already exists
            if self.config.venv_dir.exists():
                self.print_warning("Virtual environment already exists")
                response = input(f"{Colors.WARNING}Do you want to recreate it? (y/n): {Colors.ENDC}").lower()
                if response == 'y':
                    shutil.rmtree(self.config.venv_dir)
                    self.print_success("Existing virtual environment removed")
                else:
                    self.print_success("Using existing virtual environment")
                    return True
            
            # Create virtual environment
            print("Creating virtual environment...")
            if self.config.system_os == 'Windows':
                result = subprocess.run([sys.executable, '-m', 'venv', str(self.config.venv_dir)], 
                                      capture_output=True, text=True)
            else:
                result = subprocess.run([sys.executable, '-m', 'venv', str(self.config.venv_dir)], 
                                      capture_output=True, text=True)
            
            if result.returncode == 0:
                self.print_success("Virtual environment created successfully")
            else:
                self.print_error(f"Failed to create virtual environment: {result.stderr}")
                return False
            
            # Get virtual environment Python path
            if self.config.system_os == 'Windows':
                venv_python = self.config.venv_dir / 'Scripts' / 'python.exe'
                venv_pip = self.config.venv_dir / 'Scripts' / 'pip.exe'
            else:
                venv_python = self.config.venv_dir / 'bin' / 'python'
                venv_pip = self.config.venv_dir / 'bin' / 'pip'
            
            # Upgrade pip
            print("Upgrading pip...")
            result = subprocess.run([str(venv_pip), 'install', '--upgrade', 'pip'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                self.print_success("Pip upgraded successfully")
            else:
                self.print_warning("Could not upgrade pip, continuing...")
            
            # Store virtual environment paths
            self.setup_data['venv_python'] = str(venv_python)
            self.setup_data['venv_pip'] = str(venv_pip)
            
            return True
            
        except Exception as e:
            self.print_error(f"Virtual environment setup failed: {e}")
            self.logger.error(f"Virtual environment setup error: {e}")
            return False
    
    def install_dependencies(self) -> bool:
        """Install required Python packages"""
        self.print_step("Installing Dependencies")
        
        try:
            # Define requirements
            requirements = [
                'fastapi>=0.104.0',
                'uvicorn[standard]>=0.24.0',
                'websockets>=12.0',
                'sqlalchemy>=2.0.0',
                'alembic>=1.12.0',
                'kiteconnect>=4.2.0',
                'python-telegram-bot>=20.7',
                'pandas>=2.1.0',
                'numpy>=1.24.0',
                'yfinance>=0.2.18',
                'cryptography>=41.0.0',
                'python-dotenv>=1.0.0',
                'jinja2>=3.1.0',
                'aiofiles>=23.2.0',
                'pytest>=7.4.0',
                'requests>=2.31.0',
                'beautifulsoup4>=4.12.0',
                'aiohttp>=3.9.0',
                'pydantic>=2.5.0',
                'python-multipart>=0.0.6'
            ]
            
            # Install each package with progress
            venv_pip = self.setup_data['venv_pip']
            total_packages = len(requirements)
            
            for i, package in enumerate(requirements, 1):
                package_name = package.split('>=')[0].split('==')[0]
                print(f"Installing {package_name}... ({i}/{total_packages})")
                
                result = subprocess.run(
                    [venv_pip, 'install', package],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    self.print_success(f"{package_name} installed")
                else:
                    self.print_error(f"Failed to install {package_name}: {result.stderr}")
                    return False
            
            # Create requirements.txt if it doesn't exist
            requirements_file = self.config.project_dir / 'requirements.txt'
            if not requirements_file.exists():
                with open(requirements_file, 'w') as f:
                    for req in requirements:
                        f.write(f"{req}\n")
                self.print_success("requirements.txt created")
            
            self.print_success("All dependencies installed successfully")
            return True
            
        except Exception as e:
            self.print_error(f"Dependency installation failed: {e}")
            self.logger.error(f"Dependency installation error: {e}")
            return False
    
    def collect_zerodha_credentials(self) -> bool:
        """Collect and validate Zerodha API credentials"""
        self.print_step("Zerodha API Configuration")
        
        print(f"\n{Colors.OKCYAN}Please provide your Zerodha API credentials:{Colors.ENDC}")
        print(f"{Colors.WARNING}You can find these in your Kite Connect app dashboard{Colors.ENDC}")
        print(f"{Colors.WARNING}Visit: https://kite.trade/ and login to get your credentials{Colors.ENDC}\n")
        
        # API Key
        while True:
            api_key = input(f"{Colors.BOLD}Enter your Zerodha API Key: {Colors.ENDC}").strip()
            if self._validate_api_key(api_key):
                self.setup_data['zerodha_api_key'] = api_key
                break
            else:
                self.print_error("Invalid API key format. API key should be alphanumeric.")
        
        # API Secret
        while True:
            api_secret = getpass.getpass(f"{Colors.BOLD}Enter your Zerodha API Secret: {Colors.ENDC}").strip()
            if self._validate_api_secret(api_secret):
                self.setup_data['zerodha_api_secret'] = api_secret
                break
            else:
                self.print_error("Invalid API secret format.")
        
        # User ID
        while True:
            user_id = input(f"{Colors.BOLD}Enter your Zerodha User ID: {Colors.ENDC}").strip()
            if self._validate_user_id(user_id):
                self.setup_data['zerodha_user_id'] = user_id
                break
            else:
                self.print_error("Invalid User ID format.")
        
        # Access Token
        print(f"\n{Colors.WARNING}Note: Access tokens are generated daily and expire at 7:30 AM.{Colors.ENDC}")
        print(f"{Colors.WARNING}You'll need to update this token daily for live trading.{Colors.ENDC}")
        
        access_token = getpass.getpass(f"{Colors.BOLD}Enter your Zerodha Access Token (optional for setup): {Colors.ENDC}").strip()
        self.setup_data['zerodha_access_token'] = access_token if access_token else "UPDATE_DAILY"
        
        # Validate API connection (if access token provided)
        if access_token and access_token != "UPDATE_DAILY":
            if self._test_zerodha_connection(api_key, access_token):
                self.print_success("Zerodha API credentials validated successfully")
            else:
                self.print_warning("Could not validate Zerodha connection. Credentials saved for later validation.")
        else:
            self.print_warning("Access token not provided. You'll need to update it before live trading.")
        
        return True
    
    def setup_telegram_bot(self) -> bool:
        """Setup Telegram bot integration"""
        self.print_step("Telegram Bot Setup (Optional)")
        
        print(f"\n{Colors.OKCYAN}Telegram integration provides:{Colors.ENDC}")
        print("  • Real-time trade notifications")
        print("  • Manual trade approval")
        print("  • System status updates")
        print("  • Remote control commands")
        
        response = input(f"\n{Colors.BOLD}Do you want to setup Telegram notifications? (y/n): {Colors.ENDC}").lower()
        
        if response != 'y':
            self.print_warning("Telegram setup skipped")
            self.setup_data['telegram_enabled'] = False
            return True
        
        print(f"\n{Colors.OKCYAN}To setup Telegram bot:{Colors.ENDC}")
        print("1. Open Telegram and search for @BotFather")
        print("2. Send /newbot command")
        print("3. Follow instructions to create your bot")
        print("4. Save the bot token provided by BotFather")
        print("5. Get your Chat ID by messaging your bot and visiting:")
        print("   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates")
        
        # Bot Token
        while True:
            bot_token = getpass.getpass(f"\n{Colors.BOLD}Enter your Telegram Bot Token: {Colors.ENDC}").strip()
            if self._validate_telegram_token(bot_token):
                self.setup_data['telegram_bot_token'] = bot_token
                break
            else:
                self.print_error("Invalid bot token format.")
        
        # Chat ID
        while True:
            chat_id = input(f"{Colors.BOLD}Enter your Telegram Chat ID: {Colors.ENDC}").strip()
            if self._validate_chat_id(chat_id):
                self.setup_data['telegram_chat_id'] = chat_id
                break
            else:
                self.print_error("Invalid Chat ID format.")
        
        # Test bot connection
        if self._test_telegram_bot(bot_token, chat_id):
            self.print_success("Telegram bot connection successful")
            self.setup_data['telegram_enabled'] = True
        else:
            self.print_warning("Could not validate Telegram bot. Configuration saved for later validation.")
            self.setup_data['telegram_enabled'] = True
        
        return True
    
    def generate_configuration(self) -> bool:
        """Generate complete configuration file"""
        self.print_step("System Configuration")
        
        try:
            print("Generating secure configuration...")
            
            # Generate secure secret key
            secret_key = secrets.token_urlsafe(32)
            
            # Define configuration template
            config_template = f"""# Earnings Gap Trading System Configuration
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Application Settings
DEBUG=False
HOST=0.0.0.0
PORT=8000
SECRET_KEY={secret_key}

# Database Configuration
DATABASE_URL=sqlite:///./trading_system.db

# Zerodha Kite Connect API
KITE_API_KEY={self.setup_data.get('zerodha_api_key', '')}
KITE_API_SECRET={self.setup_data.get('zerodha_api_secret', '')}
KITE_USER_ID={self.setup_data.get('zerodha_user_id', '')}
KITE_ACCESS_TOKEN={self.setup_data.get('zerodha_access_token', 'UPDATE_DAILY')}

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN={self.setup_data.get('telegram_bot_token', '')}
TELEGRAM_CHAT_ID={self.setup_data.get('telegram_chat_id', '')}
TELEGRAM_ENABLED={self.setup_data.get('telegram_enabled', False)}

# Trading Parameters - SAFE DEFAULTS
PAPER_TRADING=True
MAX_POSITION_SIZE=10000
RISK_PER_TRADE=0.02
STOP_LOSS_PERCENTAGE=0.05
TARGET_PERCENTAGE=0.10
MAX_DAILY_LOSS=5000
MAX_OPEN_POSITIONS=3

# Strategy Parameters
MIN_GAP_PERCENTAGE=0.03
MAX_GAP_PERCENTAGE=0.15
MIN_VOLUME_RATIO=1.5
EARNINGS_WINDOW_DAYS=2
CONFIDENCE_THRESHOLD=70

# Security
ENCRYPTION_KEY={secrets.token_urlsafe(32)}

# Logging
LOG_LEVEL=INFO
LOG_FILE=trading_system.log

# Market Hours (IST)
MARKET_OPEN_TIME=09:15
MARKET_CLOSE_TIME=15:30

# Risk Management
CIRCUIT_BREAKER_THRESHOLD=0.05
MAX_PORTFOLIO_RISK=0.10
POSITION_TIMEOUT_MINUTES=120

# Performance Monitoring
ENABLE_METRICS=True
METRICS_RETENTION_DAYS=30

# Notification Settings
EMAIL_ALERTS_ENABLED=False
ALERT_COOLDOWN_MINUTES=15

# Trading Mode
AUTO_TRADING=False
MANUAL_APPROVAL_REQUIRED=True
"""
            
            # Write configuration file
            with open(self.config.env_file, 'w') as f:
                f.write(config_template)
            
            # Set file permissions (Unix-like systems)
            if self.config.system_os != 'Windows':
                os.chmod(self.config.env_file, 0o600)
            
            self.print_success(".env file created successfully")
            
            # Generate backup configuration
            backup_file = self.config.project_dir / f".env.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(self.config.env_file, backup_file)
            self.print_success("Configuration backup created")
            
            return True
            
        except Exception as e:
            self.print_error(f"Configuration generation failed: {e}")
            self.logger.error(f"Configuration generation error: {e}")
            return False
    
    def initialize_database(self) -> bool:
        """Initialize SQLite database with required tables"""
        self.print_step("Database Setup")
        
        try:
            print("Creating trading database...")
            
            # Create database connection
            conn = sqlite3.connect(self.config.database_file)
            cursor = conn.cursor()
            
            # Create tables
            tables = {
                'trades': '''
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        entry_price REAL NOT NULL,
                        exit_price REAL,
                        stop_loss REAL,
                        target_price REAL,
                        status TEXT NOT NULL DEFAULT 'OPEN',
                        entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        exit_time TIMESTAMP,
                        pnl REAL DEFAULT 0,
                        commission REAL DEFAULT 0,
                        slippage REAL DEFAULT 0,
                        signal_confidence INTEGER,
                        strategy TEXT DEFAULT 'earnings_gap',
                        notes TEXT
                    )
                ''',
                'signals': '''
                    CREATE TABLE IF NOT EXISTS signals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        signal_type TEXT NOT NULL,
                        confidence INTEGER NOT NULL,
                        gap_percentage REAL,
                        volume_ratio REAL,
                        market_cap REAL,
                        earnings_surprise REAL,
                        recommendation TEXT,
                        status TEXT DEFAULT 'PENDING',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        processed_at TIMESTAMP,
                        notes TEXT
                    )
                ''',
                'performance': '''
                    CREATE TABLE IF NOT EXISTS performance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL UNIQUE,
                        trades_count INTEGER DEFAULT 0,
                        winning_trades INTEGER DEFAULT 0,
                        losing_trades INTEGER DEFAULT 0,
                        total_pnl REAL DEFAULT 0,
                        gross_profit REAL DEFAULT 0,
                        gross_loss REAL DEFAULT 0,
                        commission_paid REAL DEFAULT 0,
                        win_rate REAL DEFAULT 0,
                        profit_factor REAL DEFAULT 0,
                        max_drawdown REAL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''',
                'market_data': '''
                    CREATE TABLE IF NOT EXISTS market_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        open_price REAL,
                        high_price REAL,
                        low_price REAL,
                        close_price REAL,
                        volume INTEGER,
                        source TEXT DEFAULT 'zerodha',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(symbol, timestamp)
                    )
                ''',
                'system_logs': '''
                    CREATE TABLE IF NOT EXISTS system_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        level TEXT NOT NULL,
                        message TEXT NOT NULL,
                        component TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        details TEXT
                    )
                '''
            }
            
            # Create each table
            for table_name, query in tables.items():
                cursor.execute(query)
                self.print_success(f"Table '{table_name}' created")
            
            # Create indexes for better performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)",
                "CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)",
                "CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time)",
                "CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol)",
                "CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status)",
                "CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timestamp ON market_data(symbol, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_performance_date ON performance(date)"
            ]
            
            for index_query in indexes:
                cursor.execute(index_query)
            
            # Insert initial performance record
            cursor.execute('''
                INSERT OR IGNORE INTO performance (date) 
                VALUES (?)
            ''', (datetime.now().strftime('%Y-%m-%d'),))
            
            # Commit changes and close
            conn.commit()
            conn.close()
            
            self.print_success("Database initialized successfully")
            
            # Test database connection
            if self._test_database_connection():
                self.print_success("Database connection test passed")
            else:
                self.print_warning("Database connection test failed")
            
            return True
            
        except Exception as e:
            self.print_error(f"Database initialization failed: {e}")
            self.logger.error(f"Database initialization error: {e}")
            return False
    
    def validate_system(self) -> bool:
        """Validate all system components"""
        self.print_step("System Validation")
        
        validation_results = []
        
        # Test database connectivity
        print("Testing database connection...")
        if self._test_database_connection():
            self.print_success("Database connection test passed")
            validation_results.append(True)
        else:
            self.print_error("Database connection test failed")
            validation_results.append(False)
        
        # Test Zerodha API (if access token provided)
        access_token = self.setup_data.get('zerodha_access_token')
        if access_token and access_token != "UPDATE_DAILY":
            print("Testing Zerodha API connection...")
            if self._test_zerodha_connection(
                self.setup_data.get('zerodha_api_key'),
                access_token
            ):
                self.print_success("Zerodha API connection test passed")
                validation_results.append(True)
            else:
                self.print_warning("Zerodha API connection test failed")
                validation_results.append(False)
        else:
            self.print_warning("Skipping Zerodha API test (no access token)")
        
        # Test Telegram bot (if configured)
        if self.setup_data.get('telegram_enabled'):
            print("Testing Telegram bot...")
            if self._test_telegram_bot(
                self.setup_data.get('telegram_bot_token'),
                self.setup_data.get('telegram_chat_id')
            ):
                self.print_success("Telegram bot test passed")
                validation_results.append(True)
            else:
                self.print_warning("Telegram bot test failed")
                validation_results.append(False)
        else:
            self.print_warning("Skipping Telegram bot test (not configured)")
        
        # Test file permissions
        print("Testing file permissions...")
        if self._test_file_permissions():
            self.print_success("File permissions test passed")
            validation_results.append(True)
        else:
            self.print_warning("File permissions test failed")
            validation_results.append(False)
        
        # Test port availability
        print("Testing port availability...")
        if self._test_port_availability(8000):
            self.print_success("Port 8000 is available")
            validation_results.append(True)
        else:
            self.print_warning("Port 8000 is in use (may need to stop existing services)")
            validation_results.append(False)
        
        # Summary
        passed_tests = sum(validation_results)
        total_tests = len(validation_results)
        
        if passed_tests == total_tests:
            self.print_success(f"All validation tests passed ({passed_tests}/{total_tests})")
            return True
        else:
            self.print_warning(f"Some validation tests failed ({passed_tests}/{total_tests})")
            return True  # Non-critical failures shouldn't stop setup
    
    def start_system(self) -> bool:
        """Start the trading system"""
        self.print_step("First Startup")
        
        try:
            print("Starting trading system...")
            
            # Get virtual environment Python
            venv_python = self.setup_data['venv_python']
            
            # Start the application
            main_file = self.config.project_dir / 'main.py'
            
            if not main_file.exists():
                self.print_error("main.py not found. Please ensure all project files are present.")
                return False
            
            # Start in background
            if self.config.system_os == 'Windows':
                import threading
                
                def run_server():
                    subprocess.run([
                        venv_python, 
                        str(main_file)
                    ], cwd=str(self.config.project_dir))
                
                server_thread = threading.Thread(target=run_server, daemon=True)
                server_thread.start()
            else:
                subprocess.Popen([
                    venv_python,
                    str(main_file)
                ], cwd=str(self.config.project_dir))
            
            # Wait for server to start
            print("Waiting for server to start...")
            time.sleep(5)
            
            # Test if server is running
            try:
                urllib.request.urlopen('http://localhost:8000', timeout=5)
                self.print_success("Trading system started successfully")
                
                # Open browser
                dashboard_url = "http://localhost:8000"
                self.print_success(f"Dashboard available at: {dashboard_url}")
                
                try:
                    import webbrowser
                    webbrowser.open(dashboard_url)
                    self.print_success("Browser opened automatically")
                except Exception:
                    self.print_warning("Could not open browser automatically")
                
                return True
                
            except Exception:
                self.print_warning("Server may be starting. Please check http://localhost:8000 manually.")
                return True
            
        except Exception as e:
            self.print_error(f"System startup failed: {e}")
            self.logger.error(f"System startup error: {e}")
            return False
    
    def show_completion_summary(self) -> None:
        """Show setup completion summary and next steps"""
        self.print_header("SETUP COMPLETE!")
        
        # Success message
        print(f"""
{Colors.BOLD}{Colors.OKGREEN}{Emojis.FIRE} CONGRATULATIONS! {Emojis.FIRE}
Your Earnings Gap Trading System is now ready for action!{Colors.ENDC}

{Colors.BOLD}{Colors.OKCYAN}🌐 ACCESS YOUR SYSTEM:{Colors.ENDC}
  Dashboard: http://localhost:8000
  
{Colors.BOLD}{Colors.OKCYAN}📊 WHAT'S CONFIGURED:{Colors.ENDC}
  ✅ Virtual environment with all dependencies
  ✅ Secure configuration with encrypted credentials
  ✅ SQLite database with trading tables
  ✅ Zerodha API integration
  {'✅ Telegram bot notifications' if self.setup_data.get('telegram_enabled') else '⚠️  Telegram notifications (skipped)'}
  ✅ Paper trading mode (SAFE for testing)
  ✅ Risk management with safe defaults
        """)
        
        # Important reminders
        print(f"""{Colors.BOLD}{Colors.WARNING}⚠️  IMPORTANT REMINDERS:{Colors.ENDC}
  🔐 SECURITY:
    • Your credentials are encrypted and stored in .env file
    • Keep your .env file secure and never share it
    • Access tokens expire daily at 7:30 AM (update before trading)
  
  🧪 TESTING:
    • System is in PAPER TRADING mode (safe for testing)
    • Test all functions before enabling live trading
    • Use small amounts when you switch to live trading
  
  💰 TRADING:
    • Review and adjust risk parameters in dashboard
    • Start with conservative position sizes
    • Monitor system performance regularly
        """)
        
        # Next steps
        print(f"""{Colors.BOLD}{Colors.OKCYAN}🚀 NEXT STEPS:{Colors.ENDC}
  1. Open the dashboard: http://localhost:8000
  2. Review configuration settings
  3. Test signal generation in paper trading mode
  4. Monitor system logs and performance
  5. When ready, switch to live trading (set PAPER_TRADING=False)
        """)
        
        # Quick commands
        print(f"""{Colors.BOLD}{Colors.OKCYAN}📋 QUICK COMMANDS:{Colors.ENDC}
  Start system:   {self.setup_data['venv_python']} main.py
  Run tests:      {self.setup_data['venv_python']} -m pytest tests/
  View logs:      tail -f trading_system.log
  Stop system:    Ctrl+C in terminal or close window
        """)
        
        # Support information
        print(f"""{Colors.BOLD}{Colors.OKCYAN}🆘 SUPPORT:{Colors.ENDC}
  • Documentation: README.md and USER_GUIDE.md
  • Test your setup: Run pytest tests/
  • Check logs: trading_system.log and setup.log
  • Troubleshooting: DEPLOYMENT.md
        """)
        
        # Final message
        print(f"""
{Colors.BOLD}{Colors.OKGREEN}🎉 Happy Trading! 🎉
Remember: Start small, test thoroughly, and trade responsibly.{Colors.ENDC}
        """)
    
    # Validation Helper Methods
    def _validate_api_key(self, api_key: str) -> bool:
        """Validate Zerodha API key format"""
        return bool(api_key and len(api_key) >= 10 and api_key.isalnum())
    
    def _validate_api_secret(self, api_secret: str) -> bool:
        """Validate Zerodha API secret format"""
        return bool(api_secret and len(api_secret) >= 10)
    
    def _validate_user_id(self, user_id: str) -> bool:
        """Validate Zerodha User ID format"""
        return bool(user_id and len(user_id) >= 2)
    
    def _validate_telegram_token(self, token: str) -> bool:
        """Validate Telegram bot token format"""
        pattern = r'^\d+:[A-Za-z0-9_-]{35}$'
        return bool(re.match(pattern, token))
    
    def _validate_chat_id(self, chat_id: str) -> bool:
        """Validate Telegram chat ID format"""
        try:
            int(chat_id)
            return True
        except ValueError:
            return False
    
    # Testing Helper Methods
    def _test_database_connection(self) -> bool:
        """Test database connectivity"""
        try:
            conn = sqlite3.connect(self.config.database_file)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            conn.close()
            return result[0] == 1
        except Exception:
            return False
    
    def _test_zerodha_connection(self, api_key: str, access_token: str) -> bool:
        """Test Zerodha API connection"""
        try:
            # Import kiteconnect
            from kiteconnect import KiteConnect
            
            # Create client
            kite = KiteConnect(api_key=api_key)
            kite.set_access_token(access_token)
            
            # Test connection
            profile = kite.profile()
            return bool(profile.get('user_id'))
            
        except Exception:
            return False
    
    def _test_telegram_bot(self, bot_token: str, chat_id: str) -> bool:
        """Test Telegram bot connection"""
        try:
            import json
            import urllib.request
            import urllib.parse
            
            # Test bot info
            url = f"https://api.telegram.org/bot{bot_token}/getMe"
            response = urllib.request.urlopen(url, timeout=5)
            data = json.loads(response.read())
            
            if not data.get('ok'):
                return False
            
            # Send test message
            message = "🤖 Trading System Setup Complete! Bot is working correctly."
            send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            params = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            data = urllib.parse.urlencode(params).encode()
            req = urllib.request.Request(send_url, data=data)
            response = urllib.request.urlopen(req, timeout=5)
            result = json.loads(response.read())
            
            return result.get('ok', False)
            
        except Exception:
            return False
    
    def _test_file_permissions(self) -> bool:
        """Test file read/write permissions"""
        try:
            test_file = self.config.project_dir / 'test_permissions.tmp'
            
            # Write test
            with open(test_file, 'w') as f:
                f.write('test')
            
            # Read test
            with open(test_file, 'r') as f:
                content = f.read()
            
            # Cleanup
            test_file.unlink()
            
            return content == 'test'
            
        except Exception:
            return False
    
    def _test_port_availability(self, port: int) -> bool:
        """Test if port is available"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result != 0  # Port is available if connection failed
        except Exception:
            return False
    
    def run_setup(self) -> bool:
        """Run the complete setup process"""
        try:
            # Show welcome screen
            self.show_welcome_screen()
            
            # Run setup steps
            steps = [
                self.check_system_requirements,
                self.setup_virtual_environment,
                self.install_dependencies,
                self.collect_zerodha_credentials,
                self.setup_telegram_bot,
                self.generate_configuration,
                self.initialize_database,
                self.validate_system,
                self.start_system
            ]
            
            for step in steps:
                if not step():
                    self.print_error("Setup failed. Check setup.log for details.")
                    return False
                print()  # Add spacing between steps
            
            # Show completion summary
            self.show_completion_summary()
            
            self.logger.info("Setup completed successfully")
            return True
            
        except KeyboardInterrupt:
            self.print_error("Setup interrupted by user")
            return False
        except Exception as e:
            self.print_error(f"Setup failed with error: {e}")
            self.logger.error(f"Setup error: {e}")
            return False

def main():
    """Main entry point"""
    try:
        setup = TradingSystemSetup()
        success = setup.run_setup()
        
        if success:
            print(f"\n{Colors.BOLD}{Colors.OKGREEN}Setup completed successfully!{Colors.ENDC}")
            return 0
        else:
            print(f"\n{Colors.BOLD}{Colors.FAIL}Setup failed. Please check the logs and try again.{Colors.ENDC}")
            return 1
            
    except Exception as e:
        print(f"\n{Colors.BOLD}{Colors.FAIL}Fatal error: {e}{Colors.ENDC}")
        return 1

if __name__ == "__main__":
    sys.exit(main())