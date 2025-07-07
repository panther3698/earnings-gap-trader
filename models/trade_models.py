"""
Database models for trading operations
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class EarningsEvent(Base):
    """Model for tracking earnings events"""
    __tablename__ = "earnings_events"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    company_name = Column(String(200), nullable=False)
    earnings_date = Column(DateTime, nullable=False)
    expected_eps = Column(Float)
    actual_eps = Column(Float)
    surprise_percent = Column(Float)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    trades = relationship("Trade", back_populates="earnings_event")


class Trade(Base):
    """Model for individual trades"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    trade_type = Column(String(10), nullable=False)  # BUY/SELL
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    stop_loss = Column(Float)
    target_price = Column(Float)
    status = Column(String(20), default="OPEN")  # OPEN/CLOSED/CANCELLED
    strategy = Column(String(50), default="earnings_gap")
    pnl = Column(Float, default=0.0)
    fees = Column(Float, default=0.0)
    entry_time = Column(DateTime, default=func.now())
    exit_time = Column(DateTime)
    notes = Column(Text)
    
    # Foreign Keys
    earnings_event_id = Column(Integer, ForeignKey("earnings_events.id"))
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    
    # Relationships
    earnings_event = relationship("EarningsEvent", back_populates="trades")
    portfolio = relationship("Portfolio", back_populates="trades")
    orders = relationship("Order", back_populates="trade")


class Order(Base):
    """Model for order management"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=False)
    order_id = Column(String(50), unique=True, index=True)  # Broker order ID
    symbol = Column(String(20), nullable=False)
    order_type = Column(String(20), nullable=False)  # MARKET/LIMIT/SL/SL-M
    transaction_type = Column(String(10), nullable=False)  # BUY/SELL
    quantity = Column(Integer, nullable=False)
    price = Column(Float)
    trigger_price = Column(Float)
    status = Column(String(20), default="PENDING")  # PENDING/COMPLETE/CANCELLED/REJECTED
    placed_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    filled_quantity = Column(Integer, default=0)
    average_price = Column(Float)
    
    # Relationships
    trade = relationship("Trade", back_populates="orders")


class Position(Base):
    """Model for current positions"""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, unique=True, index=True)
    quantity = Column(Integer, nullable=False)
    average_price = Column(Float, nullable=False)
    current_price = Column(Float)
    pnl = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    position_type = Column(String(10), nullable=False)  # LONG/SHORT
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Portfolio(Base):
    """Model for portfolio tracking"""
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, default="Default Portfolio")
    balance = Column(Float, nullable=False, default=0.0)
    equity = Column(Float, default=0.0)
    margin_available = Column(Float, default=0.0)
    margin_used = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    day_pnl = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    trades = relationship("Trade", back_populates="portfolio")


class Signal(Base):
    """Model for trading signals"""
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    signal_type = Column(String(20), nullable=False)  # BUY/SELL/HOLD
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    source = Column(String(50), nullable=False)  # earnings_gap, technical, etc.
    price_at_signal = Column(Float, nullable=False)
    target_price = Column(Float)
    stop_loss_price = Column(Float)
    quantity_suggested = Column(Integer)
    risk_reward_ratio = Column(Float)
    
    # Signal parameters (JSON stored as text)
    parameters = Column(Text)  # JSON string of signal parameters
    
    # Metadata
    status = Column(String(20), default="ACTIVE")  # ACTIVE/EXECUTED/EXPIRED/CANCELLED
    priority = Column(String(10), default="MEDIUM")  # HIGH/MEDIUM/LOW
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Execution tracking
    executed_at = Column(DateTime)
    execution_price = Column(Float)
    execution_quantity = Column(Integer)
    
    # Foreign Keys
    earnings_event_id = Column(Integer, ForeignKey("earnings_events.id"))
    trade_id = Column(Integer, ForeignKey("trades.id"))
    
    # Relationships
    earnings_event = relationship("EarningsEvent")
    trade = relationship("Trade")


class Performance(Base):
    """Model for daily performance tracking"""
    __tablename__ = "performance"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, index=True)
    
    # Daily P&L metrics
    daily_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    
    # Trade metrics
    trades_count = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)  # Percentage
    
    # Position metrics
    positions_opened = Column(Integer, default=0)
    positions_closed = Column(Integer, default=0)
    positions_held = Column(Integer, default=0)
    
    # Portfolio metrics
    portfolio_value = Column(Float, default=0.0)
    cash_balance = Column(Float, default=0.0)
    margin_used = Column(Float, default=0.0)
    drawdown = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    
    # Risk metrics
    var_95 = Column(Float, default=0.0)  # Value at Risk
    sharpe_ratio = Column(Float, default=0.0)
    sortino_ratio = Column(Float, default=0.0)
    
    # Trading metrics
    average_win = Column(Float, default=0.0)
    average_loss = Column(Float, default=0.0)
    largest_win = Column(Float, default=0.0)
    largest_loss = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    
    # Fees and costs
    total_fees = Column(Float, default=0.0)
    total_taxes = Column(Float, default=0.0)
    
    # Benchmark comparison
    benchmark_return = Column(Float, default=0.0)
    alpha = Column(Float, default=0.0)
    beta = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class MarketData(Base):
    """Model for storing market data snapshots"""
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # OHLCV data
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Integer, default=0)
    
    # Additional market data
    bid_price = Column(Float)
    ask_price = Column(Float)
    bid_quantity = Column(Integer)
    ask_quantity = Column(Integer)
    last_trade_price = Column(Float)
    last_trade_quantity = Column(Integer)
    
    # Derived indicators
    sma_20 = Column(Float)
    ema_20 = Column(Float)
    rsi_14 = Column(Float)
    volatility = Column(Float)
    
    # Gap information
    gap_percentage = Column(Float)
    gap_type = Column(String(10))  # UP/DOWN/NONE
    
    created_at = Column(DateTime, default=func.now())


class RiskMetrics(Base):
    """Model for risk management metrics"""
    __tablename__ = "risk_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, index=True)
    
    # Portfolio risk metrics
    portfolio_value = Column(Float, nullable=False)
    total_exposure = Column(Float, default=0.0)
    net_exposure = Column(Float, default=0.0)
    gross_exposure = Column(Float, default=0.0)
    
    # Position concentration
    max_position_weight = Column(Float, default=0.0)
    sector_concentration = Column(Text)  # JSON of sector weights
    
    # Risk limits
    daily_loss = Column(Float, default=0.0)
    max_daily_loss_limit = Column(Float, nullable=False)
    portfolio_heat = Column(Float, default=0.0)
    max_portfolio_heat = Column(Float, default=6.0)
    
    # Volatility metrics
    portfolio_volatility = Column(Float, default=0.0)
    beta_to_market = Column(Float, default=0.0)
    correlation_to_market = Column(Float, default=0.0)
    
    # Risk warnings
    risk_warnings = Column(Text)  # JSON array of active warnings
    margin_call_risk = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())