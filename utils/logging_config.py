"""
Logging configuration for Earnings Gap Trader
"""
import logging
import logging.handlers
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
import structlog
import config


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    enable_structured_logging: bool = True
) -> None:
    """
    Set up comprehensive logging for the application
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Log file path (optional)
        enable_structured_logging: Whether to use structured logging
    """
    # Use config values if not provided
    log_level = log_level or config.LOG_LEVEL
    log_file = log_file or config.LOG_FILE
    
    # Create logs directory if it doesn't exist
    if log_file:
        log_dir = Path(log_file).parent
        log_dir.mkdir(exist_ok=True)
    
    # Configure Python standard logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[]
    )
    
    # Remove default handlers
    logging.getLogger().handlers.clear()
    
    # Create formatters
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)-20s - %(levelname)-8s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)-20s - %(levelname)-8s - %(funcName)-15s:%(lineno)-4d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # File handler with rotation
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        
        # Add handlers to root logger
        logging.getLogger().addHandler(file_handler)
    
    # Add console handler
    logging.getLogger().addHandler(console_handler)
    
    # Configure structured logging if enabled
    if enable_structured_logging:
        setup_structured_logging()
    
    # Set specific logger levels
    configure_third_party_loggers()
    
    # Log startup message
    logger = get_logger(__name__)
    logger.info(f"Logging initialized - Level: {log_level}, File: {log_file or 'None'}")


def setup_structured_logging() -> None:
    """Set up structured logging with structlog"""
    try:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    except ImportError:
        # structlog not available, skip structured logging
        pass


def configure_third_party_loggers() -> None:
    """Configure log levels for third-party libraries"""
    # Reduce verbosity of third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('websockets').setLevel(logging.WARNING)
    
    # Kite Connect library
    logging.getLogger('kiteconnect').setLevel(logging.INFO)
    
    # SQLAlchemy - only show warnings and errors
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    
    # FastAPI
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('fastapi').setLevel(logging.INFO)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for better readability"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}"
                f"{self.COLORS['RESET']}"
            )
        
        return super().format(record)


class TradingLogger:
    """Specialized logger for trading operations"""
    
    def __init__(self, name: str):
        self.logger = get_logger(name)
        self.trade_file = "trades.log"
        
        # Create separate handler for trade-specific logs
        if config.LOG_FILE:
            trade_log_path = Path(config.LOG_FILE).parent / self.trade_file
            self.trade_handler = logging.handlers.RotatingFileHandler(
                trade_log_path,
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=10,
                encoding='utf-8'
            )
            
            trade_formatter = logging.Formatter(
                '%(asctime)s - TRADE - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            self.trade_handler.setFormatter(trade_formatter)
            self.trade_handler.setLevel(logging.INFO)
    
    def log_trade_entry(self, symbol: str, quantity: int, price: float, strategy: str) -> None:
        """Log trade entry"""
        message = f"ENTRY - {symbol} - Qty: {quantity} - Price: ₹{price:.2f} - Strategy: {strategy}"
        self.logger.info(message)
        
        if hasattr(self, 'trade_handler'):
            trade_logger = logging.getLogger('trades')
            trade_logger.addHandler(self.trade_handler)
            trade_logger.info(message)
    
    def log_trade_exit(self, symbol: str, quantity: int, entry_price: float, exit_price: float, pnl: float) -> None:
        """Log trade exit"""
        message = (f"EXIT - {symbol} - Qty: {quantity} - Entry: ₹{entry_price:.2f} - "
                  f"Exit: ₹{exit_price:.2f} - P&L: ₹{pnl:.2f}")
        self.logger.info(message)
        
        if hasattr(self, 'trade_handler'):
            trade_logger = logging.getLogger('trades')
            trade_logger.addHandler(self.trade_handler)
            trade_logger.info(message)
    
    def log_gap_detection(self, symbol: str, gap_percent: float, price: float) -> None:
        """Log gap detection"""
        message = f"GAP_DETECTED - {symbol} - Gap: {gap_percent:+.2f}% - Price: ₹{price:.2f}"
        self.logger.info(message)
    
    def log_risk_alert(self, alert_type: str, message: str) -> None:
        """Log risk management alerts"""
        log_message = f"RISK_ALERT - {alert_type} - {message}"
        self.logger.warning(log_message)
    
    def log_system_event(self, event_type: str, details: str) -> None:
        """Log system events"""
        message = f"SYSTEM - {event_type} - {details}"
        self.logger.info(message)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def get_trading_logger(name: str) -> TradingLogger:
    """
    Get a specialized trading logger
    
    Args:
        name: Logger name
        
    Returns:
        TradingLogger instance
    """
    return TradingLogger(name)


class LogContext:
    """Context manager for adding context to logs"""
    
    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        self.old_factory = None
    
    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)


def log_with_context(logger: logging.Logger, **context):
    """
    Decorator for adding context to all logs in a function
    
    Usage:
        @log_with_context(logger, trade_id=123, symbol="RELIANCE")
        def some_function():
            logger.info("This will include trade_id and symbol in the log")
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with LogContext(logger, **context):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def setup_performance_logging() -> None:
    """Set up performance monitoring logs"""
    perf_logger = get_logger('performance')
    
    if config.LOG_FILE:
        perf_log_path = Path(config.LOG_FILE).parent / "performance.log"
        perf_handler = logging.handlers.RotatingFileHandler(
            perf_log_path,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        
        perf_formatter = logging.Formatter(
            '%(asctime)s - PERF - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        perf_handler.setFormatter(perf_formatter)
        perf_logger.addHandler(perf_handler)
        perf_logger.setLevel(logging.INFO)


def log_execution_time(func):
    """Decorator to log function execution time"""
    def wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        
        logger = get_logger('performance')
        logger.info(f"{func.__name__} executed in {execution_time:.4f} seconds")
        
        return result
    return wrapper


class AsyncLogHandler(logging.handlers.RotatingFileHandler):
    """Asynchronous log handler to avoid blocking the main thread"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = None
        try:
            import asyncio
            import queue
            self.queue = queue.Queue(maxsize=1000)
            self.loop = asyncio.new_event_loop()
        except ImportError:
            pass
    
    def emit(self, record):
        if self.queue:
            try:
                self.queue.put_nowait(record)
            except:
                # Queue is full, drop the log
                pass
        else:
            super().emit(record)
    
    async def flush_logs(self):
        """Flush queued logs asynchronously"""
        if not self.queue:
            return
        
        while not self.queue.empty():
            try:
                record = self.queue.get_nowait()
                super().emit(record)
            except:
                break


# Export commonly used functions
__all__ = [
    'setup_logging',
    'get_logger',
    'get_trading_logger',
    'TradingLogger',
    'LogContext',
    'log_with_context',
    'log_execution_time',
    'setup_performance_logging'
]