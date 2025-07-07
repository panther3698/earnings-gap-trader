"""
Configuration models for user settings and trading parameters
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from database import Base


class TradingConfig(Base):
    """Model for trading configuration settings"""
    __tablename__ = "trading_config"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    
    # Risk Management
    max_position_size = Column(Float, default=10000.0)
    risk_per_trade = Column(Float, default=0.02)
    stop_loss_percentage = Column(Float, default=0.05)
    target_percentage = Column(Float, default=0.10)
    max_daily_loss = Column(Float, default=5000.0)
    max_open_positions = Column(Integer, default=5)
    
    # Strategy Parameters
    min_gap_percentage = Column(Float, default=0.03)
    max_gap_percentage = Column(Float, default=0.15)
    min_volume_ratio = Column(Float, default=1.5)
    earnings_window_days = Column(Integer, default=2)
    
    # Timing Settings
    market_open_delay = Column(Integer, default=15)  # minutes
    position_timeout = Column(Integer, default=60)   # minutes
    
    # Active/Inactive
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class UserSettings(Base):
    """Model for user application settings"""
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, unique=True, default="default_user")
    
    # API Settings
    kite_api_key = Column(String(100))
    kite_api_secret = Column(String(100))
    kite_access_token = Column(String(200))
    
    # Telegram Settings
    telegram_bot_token = Column(String(200))
    telegram_chat_id = Column(String(50))
    telegram_enabled = Column(Boolean, default=True)
    
    # Notification Preferences
    email_enabled = Column(Boolean, default=False)
    email_address = Column(String(100))
    sms_enabled = Column(Boolean, default=False)
    sms_number = Column(String(20))
    
    # UI Preferences
    theme = Column(String(20), default="light")
    timezone = Column(String(50), default="Asia/Kolkata")
    language = Column(String(10), default="en")
    
    # Trading Preferences
    auto_trading_enabled = Column(Boolean, default=False)
    paper_trading_mode = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class AlertConfig(Base):
    """Model for alert configuration"""
    __tablename__ = "alert_config"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    alert_type = Column(String(50), nullable=False)  # EARNINGS_GAP, STOP_LOSS, TARGET_HIT
    
    # Conditions
    conditions = Column(JSON)  # Store complex conditions as JSON
    
    # Notification Settings
    notify_telegram = Column(Boolean, default=True)
    notify_email = Column(Boolean, default=False)
    notify_sms = Column(Boolean, default=False)
    
    # Alert Settings
    is_active = Column(Boolean, default=True)
    cooldown_minutes = Column(Integer, default=5)
    max_alerts_per_day = Column(Integer, default=50)
    
    # Tracking
    alerts_sent_today = Column(Integer, default=0)
    last_alert_sent = Column(DateTime)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())