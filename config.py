"""
Configuration settings for Earnings Gap Trader
"""
import os
from typing import Optional, List
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings
from pydantic.types import SecretStr
from dotenv import load_dotenv

load_dotenv()


class TradingConfig(BaseSettings):
    """Trading configuration with Pydantic BaseSettings"""
    
    # Application Settings
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    secret_key: SecretStr = Field(..., env="SECRET_KEY")
    
    # Database Settings
    database_url: str = Field(default="sqlite:///./earnings_gap_trader.db", env="DATABASE_URL")
    
    # Zerodha Kite Connect Settings
    kite_api_key: Optional[SecretStr] = Field(None, env="KITE_API_KEY")
    kite_api_secret: Optional[SecretStr] = Field(None, env="KITE_API_SECRET")
    kite_access_token: Optional[SecretStr] = Field(None, env="KITE_ACCESS_TOKEN")
    kite_request_token: Optional[SecretStr] = Field(None, env="KITE_REQUEST_TOKEN")
    
    # Telegram Bot Settings
    telegram_bot_token: Optional[SecretStr] = Field(None, env="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = Field(None, env="TELEGRAM_CHAT_ID")
    telegram_enabled: bool = Field(default=True, env="TELEGRAM_ENABLED")
    
    # Trading Parameters
    max_position_size: float = Field(default=10000.0, gt=0, env="MAX_POSITION_SIZE")
    risk_per_trade: float = Field(default=0.02, gt=0, le=0.1, env="RISK_PER_TRADE")
    stop_loss_percentage: float = Field(default=0.05, gt=0, le=0.2, env="STOP_LOSS_PERCENTAGE")
    target_percentage: float = Field(default=0.10, gt=0, le=0.5, env="TARGET_PERCENTAGE")
    max_daily_loss: float = Field(default=5000.0, gt=0, env="MAX_DAILY_LOSS")
    max_open_positions: int = Field(default=5, gt=0, le=20, env="MAX_OPEN_POSITIONS")
    min_gap_percentage: float = Field(default=2.0, gt=0, env="MIN_GAP_PERCENTAGE")
    max_gap_percentage: float = Field(default=15.0, gt=0, env="MAX_GAP_PERCENTAGE")
    
    # Position Sizing
    position_sizing_method: str = Field(default="fixed_amount", env="POSITION_SIZING_METHOD")
    capital_allocation: float = Field(default=0.8, gt=0, le=1.0, env="CAPITAL_ALLOCATION")
    
    # Market Data Settings
    market_data_provider: str = Field(default="kite", env="MARKET_DATA_PROVIDER")
    update_interval: int = Field(default=5, gt=0, env="UPDATE_INTERVAL")
    market_start_time: str = Field(default="09:15", env="MARKET_START_TIME")
    market_end_time: str = Field(default="15:30", env="MARKET_END_TIME")
    pre_market_start: str = Field(default="09:00", env="PRE_MARKET_START")
    
    # Trading Hours
    trading_enabled: bool = Field(default=True, env="TRADING_ENABLED")
    auto_square_off: bool = Field(default=True, env="AUTO_SQUARE_OFF")
    square_off_time: str = Field(default="15:20", env="SQUARE_OFF_TIME")
    
    # Risk Management
    daily_loss_limit: float = Field(default=5000.0, gt=0, env="DAILY_LOSS_LIMIT")
    max_drawdown_percentage: float = Field(default=10.0, gt=0, le=50, env="MAX_DRAWDOWN_PERCENTAGE")
    portfolio_heat: float = Field(default=6.0, gt=0, le=20, env="PORTFOLIO_HEAT")
    
    # Logging Settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="earnings_gap_trader.log", env="LOG_FILE")
    log_rotation_size: int = Field(default=10485760, env="LOG_ROTATION_SIZE")  # 10MB
    log_backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    
    # Security Settings
    encryption_key: Optional[SecretStr] = Field(None, env="ENCRYPTION_KEY")
    session_timeout: int = Field(default=3600, gt=0, env="SESSION_TIMEOUT")  # 1 hour
    
    # Email Settings (Optional)
    email_enabled: bool = Field(default=False, env="EMAIL_ENABLED")
    smtp_server: Optional[str] = Field(None, env="SMTP_SERVER")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    email_username: Optional[str] = Field(None, env="EMAIL_USERNAME")
    email_password: Optional[SecretStr] = Field(None, env="EMAIL_PASSWORD")
    recipient_email: Optional[str] = Field(None, env="RECIPIENT_EMAIL")
    
    # Watchlist Settings
    default_watchlist: List[str] = Field(default=["RELIANCE", "TCS", "INFY", "HDFC", "ICICIBANK"], env="DEFAULT_WATCHLIST")
    max_watchlist_size: int = Field(default=50, gt=0, env="MAX_WATCHLIST_SIZE")
    
    # API Rate Limiting
    api_rate_limit: int = Field(default=3, gt=0, env="API_RATE_LIMIT")  # requests per second
    api_timeout: int = Field(default=30, gt=0, env="API_TIMEOUT")
    
    # Performance Settings
    enable_performance_logging: bool = Field(default=True, env="ENABLE_PERFORMANCE_LOGGING")
    enable_trade_analytics: bool = Field(default=True, env="ENABLE_TRADE_ANALYTICS")
    
    # Trading Mode Settings
    paper_trading: bool = Field(default=False, env="PAPER_TRADING")
    mock_trading: bool = Field(default=False, env="MOCK_TRADING")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        validate_assignment = True
        case_sensitive = False
        
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()
    
    @field_validator("position_sizing_method")
    @classmethod
    def validate_position_sizing_method(cls, v):
        valid_methods = ["fixed_amount", "percentage", "volatility_based", "kelly"]
        if v not in valid_methods:
            raise ValueError(f"position_sizing_method must be one of {valid_methods}")
        return v
    
    @field_validator("market_data_provider")
    @classmethod
    def validate_market_data_provider(cls, v):
        valid_providers = ["kite", "yfinance", "alpha_vantage"]
        if v not in valid_providers:
            raise ValueError(f"market_data_provider must be one of {valid_providers}")
        return v
    
    @field_validator("default_watchlist", mode="before")
    @classmethod
    def parse_watchlist(cls, v):
        if isinstance(v, str):
            return [symbol.strip().upper() for symbol in v.split(",") if symbol.strip()]
        return v
    
    @model_validator(mode="after")
    def validate_trading_parameters(self):
        """Validate logical relationships between trading parameters"""
        if self.target_percentage <= self.stop_loss_percentage:
            raise ValueError("target_percentage must be greater than stop_loss_percentage")
        
        if self.max_gap_percentage <= self.min_gap_percentage:
            raise ValueError("max_gap_percentage must be greater than min_gap_percentage")
        
        return self
    
    @model_validator(mode="after")
    def validate_required_credentials(self):
        """Validate required credentials based on enabled features"""
        if not self.debug:
            # Check required API credentials
            if not self.kite_api_key:
                raise ValueError("KITE_API_KEY is required in production mode")
            if not self.kite_api_secret:
                raise ValueError("KITE_API_SECRET is required in production mode")
            
            # Check Telegram settings if enabled
            if self.telegram_enabled and not self.telegram_bot_token:
                raise ValueError("TELEGRAM_BOT_TOKEN is required when Telegram is enabled")
            
            # Check email settings if enabled
            if self.email_enabled:
                required_fields = [
                    (self.smtp_server, "SMTP_SERVER"),
                    (self.email_username, "EMAIL_USERNAME"), 
                    (self.email_password, "EMAIL_PASSWORD"),
                    (self.recipient_email, "RECIPIENT_EMAIL")
                ]
                for field_value, field_name in required_fields:
                    if not field_value:
                        raise ValueError(f"{field_name} is required when email is enabled")
        
        return self
    
    def get_secret_value(self, field_name: str) -> Optional[str]:
        """Safely get secret value"""
        field_value = getattr(self, field_name, None)
        if field_value and hasattr(field_value, 'get_secret_value'):
            return field_value.get_secret_value()
        return field_value
    
    def mask_secrets(self) -> dict:
        """Return config dict with masked secret values"""
        config_dict = self.dict()
        secret_fields = [field for field, field_info in self.__fields__.items() 
                        if field_info.type_ == SecretStr or "password" in field.lower() or "token" in field.lower() or "key" in field.lower()]
        
        for field in secret_fields:
            if config_dict.get(field):
                config_dict[field] = "***MASKED***"
        
        return config_dict


# Global configuration instance
settings = TradingConfig()

# Legacy support - maintain backward compatibility
DEBUG = settings.debug
HOST = settings.host
PORT = settings.port
SECRET_KEY = settings.get_secret_value("secret_key")
DATABASE_URL = settings.database_url
KITE_API_KEY = settings.get_secret_value("kite_api_key")
KITE_API_SECRET = settings.get_secret_value("kite_api_secret")
KITE_ACCESS_TOKEN = settings.get_secret_value("kite_access_token")
TELEGRAM_BOT_TOKEN = settings.get_secret_value("telegram_bot_token")
TELEGRAM_CHAT_ID = settings.telegram_chat_id
MAX_POSITION_SIZE = settings.max_position_size
RISK_PER_TRADE = settings.risk_per_trade
STOP_LOSS_PERCENTAGE = settings.stop_loss_percentage
TARGET_PERCENTAGE = settings.target_percentage
MARKET_DATA_PROVIDER = settings.market_data_provider
UPDATE_INTERVAL = settings.update_interval
LOG_LEVEL = settings.log_level
LOG_FILE = settings.log_file
ENCRYPTION_KEY = settings.get_secret_value("encryption_key")


def validate_config():
    """Validate configuration (for backward compatibility)"""
    try:
        TradingConfig()
        return True
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {str(e)}")


def get_config() -> TradingConfig:
    """Get the global configuration instance"""
    return settings


def reload_config() -> TradingConfig:
    """Reload configuration from environment"""
    global settings
    settings = TradingConfig()
    return settings