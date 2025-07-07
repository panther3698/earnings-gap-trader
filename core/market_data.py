"""
Comprehensive market data service with Zerodha Kite Connect and Yahoo Finance backup
"""
import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any, Union, Tuple
from datetime import datetime, timedelta, time as dt_time
from enum import Enum
from dataclasses import dataclass, asdict
from threading import Thread, Event
import pandas as pd
import yfinance as yf
from kiteconnect import KiteConnect, KiteTicker
from sqlalchemy.orm import Session
import numpy as np
from typing import Set

from database import get_db_session
from models.trade_models import MarketData
from utils.logging_config import get_logger
from config import get_config

logger = get_logger(__name__)
config = get_config()


class DataSource(Enum):
    """Data source types"""
    ZERODHA = "zerodha"
    YAHOO = "yahoo"
    CACHE = "cache"


class MarketStatus(Enum):
    """Market status enum"""
    OPEN = "open"
    CLOSED = "closed"
    PRE_MARKET = "pre_market"
    POST_MARKET = "post_market"
    HOLIDAY = "holiday"


@dataclass
class TickData:
    """Real-time tick data structure"""
    symbol: str
    exchange: str
    instrument_token: int
    last_price: float
    last_quantity: int
    average_price: float
    volume: int
    buy_quantity: int
    sell_quantity: int
    ohlc: Dict[str, float]
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PriceData:
    """Standardized price data structure"""
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    last_price: float
    timestamp: datetime
    source: str
    bid: Optional[float] = None
    ask: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class DataSourceInterface(ABC):
    """Abstract base class for data sources"""
    
    @abstractmethod
    async def get_real_time_price(self, symbol: str) -> Optional[PriceData]:
        pass
    
    @abstractmethod
    async def get_historical_data(self, symbol: str, from_date: datetime, to_date: datetime, interval: str) -> Optional[pd.DataFrame]:
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        pass
    
    @abstractmethod
    async def connect(self) -> bool:
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        pass


class ZerodhaDataSource(DataSourceInterface):
    """Zerodha Kite Connect data source"""
    
    def __init__(self):
        self.kite: Optional[KiteConnect] = None
        self.kws: Optional[KiteTicker] = None
        self.connected = False
        self.last_api_call = 0
        self.api_call_count = 0
        self.rate_limit_reset = 0
        self.subscribed_tokens: Set[int] = set()
        self.token_symbol_map: Dict[int, str] = {}
        self.symbol_token_map: Dict[str, int] = {}
        self.tick_callbacks: List[Callable] = []
        
    async def connect(self) -> bool:
        """Connect to Zerodha Kite Connect"""
        try:
            api_key = getattr(config, 'kite_api_key', None)
            access_token = getattr(config, 'kite_access_token', None)
            
            # Handle SecretStr types
            if hasattr(api_key, 'get_secret_value'):
                api_key = api_key.get_secret_value()
            if hasattr(access_token, 'get_secret_value'):
                access_token = access_token.get_secret_value()
            
            if not api_key or not access_token:
                logger.warning("Zerodha credentials not configured")
                return False
            
            self.kite = KiteConnect(api_key=api_key)
            self.kite.set_access_token(access_token)
            
            # Test connection
            try:
                profile = self.kite.profile()
                if profile:
                    logger.info(f"✅ Connected to Zerodha as {profile.get('user_name', 'Unknown')}")
                    
                    # Initialize WebSocket
                    await self._initialize_websocket()
                    
                    self.connected = True
                    return True
                else:
                    logger.error("❌ Zerodha profile() returned empty response")
                    return False
            except Exception as profile_error:
                logger.error(f"❌ Zerodha profile test failed: {profile_error}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to connect to Zerodha: {e}")
            self.connected = False
            return False
    
    async def _initialize_websocket(self) -> None:
        """Initialize Zerodha WebSocket for real-time data"""
        try:
            if not self.kite:
                return
            
            api_key = getattr(config, 'kite_api_key', None)
            access_token = getattr(config, 'kite_access_token', None)
            
            # Handle SecretStr types
            if hasattr(api_key, 'get_secret_value'):
                api_key = api_key.get_secret_value()
            if hasattr(access_token, 'get_secret_value'):
                access_token = access_token.get_secret_value()
            
            self.kws = KiteTicker(api_key, access_token)
            
            def on_ticks(ws, ticks):
                """Handle incoming tick data"""
                asyncio.create_task(self._process_ticks(ticks))
            
            def on_connect(ws, response):
                logger.info("Zerodha WebSocket connected")
            
            def on_close(ws, code, reason):
                logger.warning(f"Zerodha WebSocket closed: {code} - {reason}")
            
            def on_error(ws, code, reason):
                logger.error(f"Zerodha WebSocket error: {code} - {reason}")
            
            self.kws.on_ticks = on_ticks
            self.kws.on_connect = on_connect
            self.kws.on_close = on_close
            self.kws.on_error = on_error
            
            # Start WebSocket in separate thread - disable signal handlers for twisted
            def safe_connect():
                import twisted.internet._signals
                # Patch the actual signal handling classes
                if hasattr(twisted.internet._signals, '_WithSignalHandling'):
                    twisted.internet._signals._WithSignalHandling.install = lambda self: None
                if hasattr(twisted.internet._signals, '_ChildSignalHandling'):
                    twisted.internet._signals._ChildSignalHandling.install = lambda self: None
                if hasattr(twisted.internet._signals, '_MultiSignalHandling'):
                    twisted.internet._signals._MultiSignalHandling.install = lambda self: None
                self.kws.connect()
            
            ws_thread = Thread(target=safe_connect, daemon=True)
            ws_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to initialize Zerodha WebSocket: {e}")
    
    async def _process_ticks(self, ticks: List[Dict]) -> None:
        """Process incoming tick data"""
        try:
            for tick in ticks:
                symbol = self.token_symbol_map.get(tick['instrument_token'])
                if symbol:
                    tick_data = TickData(
                        symbol=symbol,
                        exchange=tick.get('exchange', 'NSE'),
                        instrument_token=tick['instrument_token'],
                        last_price=tick['last_price'],
                        last_quantity=tick.get('last_quantity', 0),
                        average_price=tick.get('average_price', tick['last_price']),
                        volume=tick.get('volume', 0),
                        buy_quantity=tick.get('buy_quantity', 0),
                        sell_quantity=tick.get('sell_quantity', 0),
                        ohlc=tick.get('ohlc', {}),
                        timestamp=datetime.now()
                    )
                    
                    # Notify callbacks
                    for callback in self.tick_callbacks:
                        try:
                            await callback(tick_data)
                        except Exception as e:
                            logger.error(f"Error in tick callback: {e}")
        
        except Exception as e:
            logger.error(f"Error processing ticks: {e}")
    
    async def _rate_limited_call(self, func, *args, **kwargs):
        """Make rate-limited API calls"""
        current_time = time.time()
        
        # Reset counter every minute
        if current_time - self.rate_limit_reset > 60:
            self.api_call_count = 0
            self.rate_limit_reset = current_time
        
        # Check rate limit (3 calls per second, 200 per minute)
        if self.api_call_count >= 180:  # Conservative limit
            wait_time = 60 - (current_time - self.rate_limit_reset)
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
                self.api_call_count = 0
                self.rate_limit_reset = time.time()
        
        # Ensure minimum 0.33s between calls
        if current_time - self.last_api_call < 0.33:
            await asyncio.sleep(0.33 - (current_time - self.last_api_call))
        
        try:
            self.api_call_count += 1
            self.last_api_call = time.time()
            
            # Run sync function in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: func(*args, **kwargs))
            return result
            
        except Exception as e:
            logger.error(f"API call failed: {e}")
            return None
    
    async def get_real_time_price(self, symbol: str) -> Optional[PriceData]:
        """Get real-time price from Zerodha"""
        try:
            if not self.kite or not self.connected:
                return None
            
            kite_symbol = f"NSE:{symbol}"
            quote = await self._rate_limited_call(self.kite.quote, [kite_symbol])
            
            if not quote or kite_symbol not in quote:
                return None
            
            data = quote[kite_symbol]
            ohlc = data.get('ohlc', {})
            
            price_data = PriceData(
                symbol=symbol,
                open=ohlc.get('open', 0),
                high=ohlc.get('high', 0),
                low=ohlc.get('low', 0),
                close=ohlc.get('close', 0),
                volume=data.get('volume', 0),
                last_price=data.get('last_price', 0),
                timestamp=datetime.now(),
                source=DataSource.ZERODHA.value,
                bid=data.get('depth', {}).get('buy', [{}])[0].get('price') if data.get('depth') else None,
                ask=data.get('depth', {}).get('sell', [{}])[0].get('price') if data.get('depth') else None,
                change=data.get('net_change'),
                change_percent=data.get('last_price', 0) / ohlc.get('close', 1) - 1 if ohlc.get('close') else None
            )
            
            return price_data
            
        except Exception as e:
            logger.error(f"Error fetching Zerodha price for {symbol}: {e}")
            return None
    
    async def get_historical_data(self, symbol: str, from_date: datetime, to_date: datetime, interval: str) -> Optional[pd.DataFrame]:
        """Get historical data from Zerodha"""
        try:
            if not self.kite or not self.connected:
                return None
            
            # Get instrument token
            instrument_token = self.symbol_token_map.get(symbol)
            if not instrument_token:
                # Try to get instruments list
                instruments = await self._rate_limited_call(self.kite.instruments, "NSE")
                if instruments:
                    for inst in instruments:
                        if inst['tradingsymbol'] == symbol:
                            instrument_token = inst['instrument_token']
                            self.symbol_token_map[symbol] = instrument_token
                            self.token_symbol_map[instrument_token] = symbol
                            break
            
            if not instrument_token:
                logger.warning(f"Instrument token not found for {symbol}")
                return None
            
            # Convert interval format
            kite_interval_map = {
                "1m": "minute",
                "5m": "5minute",
                "15m": "15minute",
                "1h": "60minute",
                "1d": "day"
            }
            
            kite_interval = kite_interval_map.get(interval, "day")
            
            # Fetch historical data
            historical_data = await self._rate_limited_call(
                self.kite.historical_data,
                instrument_token,
                from_date,
                to_date,
                kite_interval
            )
            
            if historical_data:
                df = pd.DataFrame(historical_data)
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                df.columns = [col.title() for col in df.columns]  # Standardize column names
                return df
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching Zerodha historical data for {symbol}: {e}")
            return None
    
    async def subscribe_to_ticks(self, symbol: str) -> bool:
        """Subscribe to real-time ticks for a symbol"""
        try:
            if not self.kws or symbol in self.symbol_token_map:
                return False
            
            # Get instrument token
            instrument_token = self.symbol_token_map.get(symbol)
            if not instrument_token:
                return False
            
            self.kws.subscribe([instrument_token])
            self.kws.set_mode(self.kws.MODE_FULL, [instrument_token])
            self.subscribed_tokens.add(instrument_token)
            
            logger.info(f"Subscribed to ticks for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing to ticks for {symbol}: {e}")
            return False
    
    async def is_connected(self) -> bool:
        return self.connected
    
    async def disconnect(self) -> None:
        """Disconnect from Zerodha"""
        try:
            if self.kws:
                self.kws.close()
            self.connected = False
            logger.info("Disconnected from Zerodha")
        except Exception as e:
            logger.error(f"Error disconnecting from Zerodha: {e}")


class YahooDataSource(DataSourceInterface):
    """Yahoo Finance data source as backup"""
    
    def __init__(self):
        self.connected = False
        self.cache: Dict[str, Tuple[PriceData, datetime]] = {}
        self.cache_timeout = 60  # Cache for 1 minute
    
    async def connect(self) -> bool:
        """Connect to Yahoo Finance (always available)"""
        self.connected = True
        logger.info("Yahoo Finance data source ready")
        return True
    
    async def get_real_time_price(self, symbol: str) -> Optional[PriceData]:
        """Get price from Yahoo Finance"""
        try:
            # Check cache first
            cache_key = symbol
            if cache_key in self.cache:
                cached_data, cache_time = self.cache[cache_key]
                if (datetime.now() - cache_time).seconds < self.cache_timeout:
                    return cached_data
            
            symbol_yf = f"{symbol}.NS"
            ticker = yf.Ticker(symbol_yf)
            
            # Get current info and recent history
            info = ticker.info
            hist = ticker.history(period="1d", interval="1m")
            
            if hist.empty:
                return None
            
            latest = hist.iloc[-1]
            previous_close = info.get('previousClose', latest['Close'])
            
            price_data = PriceData(
                symbol=symbol,
                open=info.get('open', latest['Open']),
                high=latest['High'],
                low=latest['Low'],
                close=previous_close,
                volume=int(latest['Volume']),
                last_price=latest['Close'],
                timestamp=datetime.now(),
                source=DataSource.YAHOO.value,
                change=latest['Close'] - previous_close,
                change_percent=(latest['Close'] - previous_close) / previous_close if previous_close else None
            )
            
            # Cache the data
            self.cache[cache_key] = (price_data, datetime.now())
            
            return price_data
            
        except Exception as e:
            logger.error(f"Error fetching Yahoo price for {symbol}: {e}")
            return None
    
    async def get_historical_data(self, symbol: str, from_date: datetime, to_date: datetime, interval: str) -> Optional[pd.DataFrame]:
        """Get historical data from Yahoo Finance"""
        try:
            symbol_yf = f"{symbol}.NS"
            ticker = yf.Ticker(symbol_yf)
            
            # Convert interval format
            yahoo_interval_map = {
                "1m": "1m",
                "5m": "5m", 
                "15m": "15m",
                "1h": "1h",
                "1d": "1d"
            }
            
            yahoo_interval = yahoo_interval_map.get(interval, "1d")
            
            # Calculate period or use dates
            if (to_date - from_date).days <= 7 and interval in ["1m", "5m", "15m"]:
                # For intraday data, use period
                hist = ticker.history(period="7d", interval=yahoo_interval)
                hist = hist[hist.index >= from_date]
                hist = hist[hist.index <= to_date]
            else:
                hist = ticker.history(start=from_date, end=to_date, interval=yahoo_interval)
            
            if not hist.empty:
                # Standardize column names to match Zerodha format
                hist.columns = [col.title() for col in hist.columns]
                return hist
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching Yahoo historical data for {symbol}: {e}")
            return None
    
    async def is_connected(self) -> bool:
        return self.connected
    
    async def disconnect(self) -> None:
        self.connected = False


class DataValidator:
    """Data quality validation and cleaning"""
    
    def __init__(self):
        self.price_deviation_threshold = 0.2  # 20% price deviation
        self.volume_spike_threshold = 5.0     # 5x volume spike
    
    def validate_price_data(self, price_data: PriceData, previous_data: Optional[PriceData] = None) -> Tuple[bool, List[str]]:
        """Validate price data quality"""
        issues = []
        
        # Basic validation
        if price_data.last_price <= 0:
            issues.append("Invalid last price (non-positive)")
        
        if price_data.volume < 0:
            issues.append("Invalid volume (negative)")
        
        if price_data.high < price_data.low:
            issues.append("High price less than low price")
        
        if not (price_data.low <= price_data.last_price <= price_data.high):
            issues.append("Last price outside high-low range")
        
        # Validate against previous data if available
        if previous_data:
            price_change = abs(price_data.last_price - previous_data.last_price) / previous_data.last_price
            if price_change > self.price_deviation_threshold:
                issues.append(f"Large price deviation: {price_change:.2%}")
            
            if previous_data.volume > 0:
                volume_ratio = price_data.volume / previous_data.volume
                if volume_ratio > self.volume_spike_threshold:
                    issues.append(f"Volume spike detected: {volume_ratio:.1f}x")
        
        return len(issues) == 0, issues
    
    def clean_historical_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate historical data"""
        if df is None or df.empty:
            return df
        
        # Remove rows with missing critical data
        df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
        
        # Remove rows where high < low
        df = df[df['High'] >= df['Low']]
        
        # Remove rows with zero or negative prices
        for col in ['Open', 'High', 'Low', 'Close']:
            df = df[df[col] > 0]
        
        # Remove volume outliers
        if 'Volume' in df.columns:
            volume_median = df['Volume'].median()
            volume_threshold = volume_median * 20  # 20x median volume
            df = df[df['Volume'] <= volume_threshold]
        
        # Forward fill small gaps (max 3 consecutive)
        df = df.fillna(method='ffill', limit=3)
        
        return df
    
    def detect_corporate_actions(self, df: pd.DataFrame) -> List[Dict]:
        """Detect potential corporate actions in historical data"""
        actions = []
        
        if df is None or len(df) < 2:
            return actions
        
        # Calculate day-to-day returns
        df['return'] = df['Close'].pct_change()
        
        # Detect large gaps (potential splits/bonuses)
        large_gaps = df[abs(df['return']) > 0.15]  # 15% threshold
        
        for idx, row in large_gaps.iterrows():
            action_type = "split" if row['return'] < -0.15 else "bonus"
            actions.append({
                "date": idx,
                "type": action_type,
                "return": row['return'],
                "severity": "high" if abs(row['return']) > 0.3 else "medium"
            })
        
        return actions


class TickDataProcessor:
    """Process and manage real-time tick data"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.tick_buffer: Dict[str, List[TickData]] = {}
        self.last_prices: Dict[str, float] = {}
        self.callbacks: List[Callable] = []
        self.buffer_size = 100  # Keep last 100 ticks per symbol
        
    async def process_tick(self, tick_data: TickData) -> None:
        """Process incoming tick data"""
        try:
            symbol = tick_data.symbol
            
            # Update buffer
            if symbol not in self.tick_buffer:
                self.tick_buffer[symbol] = []
            
            self.tick_buffer[symbol].append(tick_data)
            
            # Maintain buffer size
            if len(self.tick_buffer[symbol]) > self.buffer_size:
                self.tick_buffer[symbol] = self.tick_buffer[symbol][-self.buffer_size:]
            
            # Update last price
            self.last_prices[symbol] = tick_data.last_price
            
            # Store to database (sample every 10th tick to avoid overload)
            if len(self.tick_buffer[symbol]) % 10 == 0:
                await self._store_tick_to_db(tick_data)
            
            # Notify callbacks
            for callback in self.callbacks:
                try:
                    await callback(tick_data)
                except Exception as e:
                    logger.error(f"Error in tick callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing tick for {tick_data.symbol}: {e}")
    
    async def _store_tick_to_db(self, tick_data: TickData) -> None:
        """Store tick data to database"""
        try:
            market_data = MarketData(
                symbol=tick_data.symbol,
                timestamp=tick_data.timestamp,
                open_price=tick_data.ohlc.get('open', 0),
                high_price=tick_data.ohlc.get('high', 0),
                low_price=tick_data.ohlc.get('low', 0),
                close_price=tick_data.last_price,
                volume=tick_data.volume,
                last_trade_price=tick_data.last_price,
                last_trade_quantity=tick_data.last_quantity
            )
            
            self.db.add(market_data)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error storing tick to database: {e}")
            self.db.rollback()
    
    def get_latest_ticks(self, symbol: str, count: int = 10) -> List[TickData]:
        """Get latest ticks for a symbol"""
        if symbol in self.tick_buffer:
            return self.tick_buffer[symbol][-count:]
        return []
    
    def get_last_price(self, symbol: str) -> Optional[float]:
        """Get last known price for a symbol"""
        return self.last_prices.get(symbol)
    
    def add_callback(self, callback: Callable) -> None:
        """Add callback for tick processing"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable) -> None:
        """Remove callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)


class MarketHoursManager:
    """Manage market hours and holidays"""
    
    def __init__(self):
        self.market_open_time = dt_time(9, 15)  # 9:15 AM
        self.market_close_time = dt_time(15, 30)  # 3:30 PM
        self.pre_market_start = dt_time(9, 0)   # 9:00 AM
        self.post_market_end = dt_time(16, 0)   # 4:00 PM
        
        # Indian stock market holidays (sample - you'd load from a comprehensive source)
        self.holidays_2024 = [
            datetime(2024, 1, 26),  # Republic Day
            datetime(2024, 3, 8),   # Holi
            datetime(2024, 3, 29),  # Good Friday
            datetime(2024, 8, 15),  # Independence Day
            datetime(2024, 10, 2),  # Gandhi Jayanti
            datetime(2024, 11, 1),  # Diwali
            datetime(2024, 12, 25), # Christmas
        ]
    
    def get_market_status(self, timestamp: Optional[datetime] = None) -> MarketStatus:
        """Get current market status"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Check if it's a holiday
        if timestamp.date() in [h.date() for h in self.holidays_2024]:
            return MarketStatus.HOLIDAY
        
        # Check if it's a weekend
        if timestamp.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return MarketStatus.CLOSED
        
        current_time = timestamp.time()
        
        # Check market hours
        if current_time < self.pre_market_start:
            return MarketStatus.CLOSED
        elif current_time < self.market_open_time:
            return MarketStatus.PRE_MARKET
        elif current_time <= self.market_close_time:
            return MarketStatus.OPEN
        elif current_time <= self.post_market_end:
            return MarketStatus.POST_MARKET
        else:
            return MarketStatus.CLOSED
    
    def is_market_open(self, timestamp: Optional[datetime] = None) -> bool:
        """Check if market is currently open"""
        return self.get_market_status(timestamp) == MarketStatus.OPEN
    
    def get_next_market_open(self, timestamp: Optional[datetime] = None) -> datetime:
        """Get next market opening time"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # If market is currently open, return current time
        if self.is_market_open(timestamp):
            return timestamp
        
        # Calculate next market open
        next_open = timestamp.replace(
            hour=self.market_open_time.hour,
            minute=self.market_open_time.minute,
            second=0,
            microsecond=0
        )
        
        # If we're past market close, move to next day
        if timestamp.time() > self.market_close_time:
            next_open += timedelta(days=1)
        
        # Skip weekends and holidays
        while (next_open.weekday() >= 5 or 
               next_open.date() in [h.date() for h in self.holidays_2024]):
            next_open += timedelta(days=1)
        
        return next_open
    
    def get_market_hours_today(self, timestamp: Optional[datetime] = None) -> Dict[str, datetime]:
        """Get market hours for today"""
        if timestamp is None:
            timestamp = datetime.now()
        
        today = timestamp.date()
        
        return {
            "pre_market_start": datetime.combine(today, self.pre_market_start),
            "market_open": datetime.combine(today, self.market_open_time),
            "market_close": datetime.combine(today, self.market_close_time),
            "post_market_end": datetime.combine(today, self.post_market_end)
        }


class StockListManager:
    """Manage stock lists (Nifty 50, etc.)"""
    
    def __init__(self):
        self.nifty_50_symbols = [
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "HINDUNILVR",
            "ICICIBANK", "SBIN", "BHARTIARTL", "ITC", "ASIANPAINT",
            "LT", "AXISBANK", "MARUTI", "KOTAKBANK", "HCLTECH",
            "WIPRO", "ULTRACEMCO", "ONGC", "TECHM", "TITAN",
            "SUNPHARMA", "POWERGRID", "NESTLEIND", "TATAMOTORS", "TATASTEEL",
            "BAJFINANCE", "M&M", "NTPC", "JSWSTEEL", "DRREDDY",
            "EICHERMOT", "ADANIPORTS", "HEROMOTOCO", "CIPLA", "COALINDIA",
            "GRASIM", "BRITANNIA", "BPCL", "HINDALCO", "DIVISLAB",
            "SHREECEM", "BAJAJFINSV", "INDUSINDBK", "UPL", "APOLLOHOSP",
            "TATACONSUM", "BAJAJ-AUTO", "HDFCLIFE", "SBILIFE", "ADANIENT"
        ]
        
        self.nifty_next_50_symbols = [
            "ADANIGREEN", "ADANITRANS", "AMBUJACEM", "BANDHANBNK", "BERGEPAINT",
            "BIOCON", "BOSCHLTD", "CANFINHOME", "CHOLAFIN", "COLPAL",
            "CONCOR", "COFORGE", "DABUR", "DALBHARAT", "DELTACORP",
            "DMART", "ESCORTS", "GODREJCP", "GODREJPROP", "GRANULES",
            "HAVELLS", "ICICIPRULI", "IDFCFIRSTB", "INDIGO", "INDUSTOWER",
            "JINDALSTEL", "JUBLFOOD", "LALPATHLAB", "LICHSGFIN", "LUPIN",
            "MARICO", "MCDOWELL-N", "MFSL", "MOTHERSON", "MPHASIS",
            "MRF", "NAUKRI", "NMDC", "PAGEIND", "PEL",
            "PIDILITIND", "PIIND", "PNB", "SAIL", "SIEMENS",
            "TORNTPHARM", "TORNTPOWER", "TRENT", "VOLTAS", "ZEEL"
        ]
    
    def get_nifty_50(self) -> List[str]:
        """Get Nifty 50 stock symbols"""
        return self.nifty_50_symbols.copy()
    
    def get_nifty_next_50(self) -> List[str]:
        """Get Nifty Next 50 stock symbols"""
        return self.nifty_next_50_symbols.copy()
    
    def get_all_major_stocks(self) -> List[str]:
        """Get all major stocks (Nifty 100)"""
        return self.nifty_50_symbols + self.nifty_next_50_symbols
    
    def is_major_stock(self, symbol: str) -> bool:
        """Check if symbol is a major stock"""
        return symbol in self.get_all_major_stocks()


class MarketDataManager:
    """Main market data manager coordinating all sources and services"""
    
    def __init__(self):
        self.zerodha_source = ZerodhaDataSource()
        self.yahoo_source = YahooDataSource()
        self.data_validator = DataValidator()
        self.tick_processor = TickDataProcessor(get_db_session())
        self.market_hours = MarketHoursManager()
        self.stock_list = StockListManager()
        
        self.primary_source: DataSourceInterface = self.zerodha_source
        self.backup_source: DataSourceInterface = self.yahoo_source
        
        self.price_cache: Dict[str, Tuple[PriceData, datetime]] = {}
        self.cache_timeout = 30  # 30 seconds cache
        
        self.subscribers: Dict[str, List[Callable]] = {}
        self.is_streaming = False
        self._streaming_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> bool:
        """Initialize market data manager"""
        try:
            logger.info("Initializing market data manager...")
            
            # Try to connect to primary source (Zerodha)
            zerodha_connected = await self.zerodha_source.connect()
            
            # Always connect to backup source
            yahoo_connected = await self.yahoo_source.connect()
            
            if zerodha_connected:
                logger.info("Using Zerodha as primary data source")
                self.primary_source = self.zerodha_source
                self.backup_source = self.yahoo_source
            else:
                logger.warning("Zerodha connection failed, using Yahoo Finance as primary")
                self.primary_source = self.yahoo_source
                self.backup_source = None
            
            # Setup tick processor callback
            if isinstance(self.primary_source, ZerodhaDataSource):
                self.primary_source.tick_callbacks.append(self.tick_processor.process_tick)
            
            logger.info("Market data manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize market data manager: {e}")
            return False
    
    async def get_real_time_price(self, symbol: str, use_cache: bool = True) -> Optional[PriceData]:
        """Get real-time price with automatic failover"""
        try:
            # Check cache first
            if use_cache and symbol in self.price_cache:
                cached_data, cache_time = self.price_cache[symbol]
                if (datetime.now() - cache_time).seconds < self.cache_timeout:
                    return cached_data
            
            # Try primary source first
            price_data = await self.primary_source.get_real_time_price(symbol)
            
            # Validate data quality
            if price_data:
                is_valid, issues = self.data_validator.validate_price_data(price_data)
                if not is_valid:
                    logger.warning(f"Data quality issues for {symbol}: {issues}")
                    # Try backup source if data quality is poor
                    if self.backup_source:
                        backup_data = await self.backup_source.get_real_time_price(symbol)
                        if backup_data:
                            is_backup_valid, _ = self.data_validator.validate_price_data(backup_data)
                            if is_backup_valid:
                                price_data = backup_data
            
            # If primary source failed, try backup
            if not price_data and self.backup_source:
                logger.warning(f"Primary source failed for {symbol}, trying backup")
                price_data = await self.backup_source.get_real_time_price(symbol)
            
            # Cache valid data
            if price_data:
                self.price_cache[symbol] = (price_data, datetime.now())
                
                # Notify subscribers
                await self._notify_subscribers(symbol, price_data)
            
            return price_data
            
        except Exception as e:
            logger.error(f"Error getting real-time price for {symbol}: {e}")
            return None
    
    async def get_historical_data(
        self, 
        symbol: str, 
        from_date: datetime, 
        to_date: datetime, 
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """Get historical data with automatic failover"""
        try:
            # Try primary source first
            data = await self.primary_source.get_historical_data(symbol, from_date, to_date, interval)
            
            # Clean and validate data
            if data is not None and not data.empty:
                data = self.data_validator.clean_historical_data(data)
                
                # Detect corporate actions
                corporate_actions = self.data_validator.detect_corporate_actions(data)
                if corporate_actions:
                    logger.info(f"Detected {len(corporate_actions)} potential corporate actions for {symbol}")
            
            # If primary source failed or returned poor data, try backup
            if (data is None or data.empty) and self.backup_source:
                logger.warning(f"Primary source failed for historical data {symbol}, trying backup")
                data = await self.backup_source.get_historical_data(symbol, from_date, to_date, interval)
                
                if data is not None and not data.empty:
                    data = self.data_validator.clean_historical_data(data)
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return None
    
    async def subscribe_to_price_updates(self, symbol: str, callback: Callable) -> bool:
        """Subscribe to real-time price updates"""
        try:
            if symbol not in self.subscribers:
                self.subscribers[symbol] = []
            
            self.subscribers[symbol].append(callback)
            
            # If using Zerodha, subscribe to ticks
            if isinstance(self.primary_source, ZerodhaDataSource):
                await self.primary_source.subscribe_to_ticks(symbol)
            
            logger.info(f"Added price subscription for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing to price updates for {symbol}: {e}")
            return False
    
    async def unsubscribe_from_price_updates(self, symbol: str, callback: Callable) -> bool:
        """Unsubscribe from price updates"""
        try:
            if symbol in self.subscribers and callback in self.subscribers[symbol]:
                self.subscribers[symbol].remove(callback)
                
                # Remove symbol if no more subscribers
                if not self.subscribers[symbol]:
                    del self.subscribers[symbol]
                
                logger.info(f"Removed price subscription for {symbol}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error unsubscribing from price updates for {symbol}: {e}")
            return False
    
    async def _notify_subscribers(self, symbol: str, price_data: PriceData) -> None:
        """Notify all subscribers of price updates"""
        if symbol in self.subscribers:
            for callback in self.subscribers[symbol]:
                try:
                    await callback(price_data)
                except Exception as e:
                    logger.error(f"Error in price update callback for {symbol}: {e}")
    
    async def start_price_streaming(self, update_interval: int = 5) -> None:
        """Start price streaming for all subscribed symbols"""
        if self.is_streaming:
            logger.warning("Price streaming already active")
            return
        
        self.is_streaming = True
        logger.info(f"Starting price streaming with {update_interval}s interval")
        
        async def streaming_loop():
            while self.is_streaming:
                try:
                    # Update prices for all subscribed symbols
                    for symbol in list(self.subscribers.keys()):
                        price_data = await self.get_real_time_price(symbol, use_cache=False)
                        if price_data:
                            await self._notify_subscribers(symbol, price_data)
                    
                    await asyncio.sleep(update_interval)
                    
                except Exception as e:
                    logger.error(f"Error in price streaming loop: {e}")
                    await asyncio.sleep(10)
        
        self._streaming_task = asyncio.create_task(streaming_loop())
    
    async def stop_price_streaming(self) -> None:
        """Stop price streaming"""
        self.is_streaming = False
        if self._streaming_task:
            self._streaming_task.cancel()
            try:
                await self._streaming_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Price streaming stopped")
    
    async def get_market_status(self) -> Dict[str, Any]:
        """Get comprehensive market status"""
        status = self.market_hours.get_market_status()
        market_hours_today = self.market_hours.get_market_hours_today()
        
        return {
            "status": status.value,
            "is_open": status == MarketStatus.OPEN,
            "market_hours": {
                "pre_market_start": market_hours_today["pre_market_start"].isoformat(),
                "market_open": market_hours_today["market_open"].isoformat(),
                "market_close": market_hours_today["market_close"].isoformat(),
                "post_market_end": market_hours_today["post_market_end"].isoformat()
            },
            "next_market_open": self.market_hours.get_next_market_open().isoformat(),
            "data_sources": {
                "primary": self.primary_source.__class__.__name__,
                "primary_connected": await self.primary_source.is_connected(),
                "backup": self.backup_source.__class__.__name__ if self.backup_source else None,
                "backup_connected": await self.backup_source.is_connected() if self.backup_source else False
            },
            "subscriptions": len(self.subscribers),
            "cache_size": len(self.price_cache),
            "streaming_active": self.is_streaming
        }
    
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, Optional[PriceData]]:
        """Get prices for multiple symbols efficiently"""
        tasks = [self.get_real_time_price(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            symbol: result if not isinstance(result, Exception) else None
            for symbol, result in zip(symbols, results)
        }
    
    async def warmup_cache(self, symbols: Optional[List[str]] = None) -> None:
        """Warm up cache with commonly used symbols"""
        if symbols is None:
            symbols = self.stock_list.get_nifty_50()[:20]  # Top 20 Nifty stocks
        
        logger.info(f"Warming up cache for {len(symbols)} symbols")
        await self.get_multiple_prices(symbols)
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            await self.stop_price_streaming()
            await self.primary_source.disconnect()
            if self.backup_source:
                await self.backup_source.disconnect()
            
            logger.info("Market data manager cleaned up")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# Global market data manager instance
market_data_manager = MarketDataManager()