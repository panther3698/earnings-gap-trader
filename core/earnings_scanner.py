"""
Comprehensive earnings gap scanner strategy for momentum trading
"""
import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta, date
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
import yfinance as yf

from database import get_db_session
from models.trade_models import Signal, MarketData
from core.market_data import MarketDataManager, PriceData
from utils.logging_config import get_logger
from config import get_config

logger = get_logger(__name__)
config = get_config()


class SignalType(Enum):
    """Signal types for earnings gap strategy"""
    EARNINGS_GAP_UP = "earnings_gap_up"
    EARNINGS_GAP_DOWN = "earnings_gap_down"
    
    
class SignalConfidence(Enum):
    """Signal confidence levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class EarningsAnnouncement:
    """Earnings announcement data structure"""
    symbol: str
    company_name: str
    announcement_date: date
    announcement_time: Optional[str]
    actual_eps: Optional[float]
    expected_eps: Optional[float]
    surprise_percent: Optional[float]
    revenue_actual: Optional[float]
    revenue_expected: Optional[float]
    source: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class GapData:
    """Gap analysis data structure"""
    symbol: str
    previous_close: float
    current_price: float
    gap_percent: float
    gap_amount: float
    gap_type: str  # "up" or "down"
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class VolumeData:
    """Volume analysis data structure"""
    symbol: str
    current_volume: int
    average_volume_20d: float
    volume_ratio: float
    is_surge: bool
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class EarningsGapSignal:
    """Complete earnings gap signal"""
    symbol: str
    company_name: str
    signal_type: SignalType
    confidence: SignalConfidence
    confidence_score: float
    
    # Entry details
    entry_price: float
    entry_time: datetime
    
    # Gap information
    gap_percent: float
    gap_amount: float
    previous_close: float
    
    # Volume information
    volume_ratio: float
    current_volume: int
    
    # Earnings information
    earnings_surprise: float
    actual_eps: Optional[float]
    expected_eps: Optional[float]
    
    # Risk management
    stop_loss: float
    profit_target: float
    risk_reward_ratio: float
    
    # Signal metadata
    signal_explanation: str
    created_at: datetime
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        result['signal_type'] = self.signal_type.value
        result['confidence'] = self.confidence.value
        return result


class EarningsDataCollector:
    """Collect earnings announcements from multiple sources"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.earnings_cache: Dict[str, EarningsAnnouncement] = {}
        self.cache_timeout = 3600  # 1 hour cache
        
    async def get_earnings_calendar(self, from_date: date, to_date: date) -> List[EarningsAnnouncement]:
        """Get earnings calendar for date range"""
        try:
            announcements = []
            
            # 1. Try Zerodha first (primary source if API credentials available)
            zerodha_data = await self._fetch_zerodha_earnings(from_date, to_date)
            if zerodha_data:
                announcements.extend(zerodha_data)
                logger.info(f"✅ Using Zerodha as primary earnings data source")
            else:
                logger.info("⚠️ Zerodha earnings data not available, trying fallback sources")
                
                # 2. Try MoneyControl as fallback
                moneycontrol_data = await self._scrape_moneycontrol_earnings(from_date, to_date)
                announcements.extend(moneycontrol_data)
                
                # 3. Use Yahoo Finance as last resort
                if not announcements:
                    yahoo_data = await self._fetch_yahoo_earnings(from_date, to_date)
                    announcements.extend(yahoo_data)
            
            # Remove duplicates and sort
            unique_announcements = self._deduplicate_announcements(announcements)
            return sorted(unique_announcements, key=lambda x: x.announcement_date)
            
        except Exception as e:
            logger.error(f"Error fetching earnings calendar: {e}")
            return []
    
    async def _fetch_zerodha_earnings(self, from_date: date, to_date: date) -> List[EarningsAnnouncement]:
        """Fetch earnings data using Zerodha Kite Connect API"""
        try:
            # Check if Zerodha API credentials are available
            api_key = getattr(config, 'kite_api_key', None)
            access_token = getattr(config, 'kite_access_token', None)
            
            if not api_key or not access_token:
                logger.info("🔑 Zerodha API credentials not configured, skipping Zerodha earnings fetch")
                return []
            
            # Import KiteConnect here to avoid startup issues if credentials aren't set
            from kiteconnect import KiteConnect
            
            # Initialize Kite Connect
            kite = KiteConnect(api_key=str(api_key.get_secret_value()) if hasattr(api_key, 'get_secret_value') else str(api_key))
            kite.set_access_token(str(access_token.get_secret_value()) if hasattr(access_token, 'get_secret_value') else str(access_token))
            
            announcements = []
            
            # Get instruments list
            instruments = kite.instruments("NSE")
            
            # Filter for equity instruments from major companies
            major_stocks = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'SBIN', 'BHARTIARTL', 
                          'ITC', 'LT', 'ASIANPAINT', 'AXISBANK', 'MARUTI', 'KOTAKBANK', 'HCLTECH', 
                          'WIPRO', 'ULTRACEMCO', 'ONGC', 'TECHM', 'TITAN', 'HINDUNILVR']
            
            for symbol in major_stocks:
                try:
                    # Get instrument token for the symbol
                    instrument = next((inst for inst in instruments 
                                    if inst['tradingsymbol'] == symbol and inst['instrument_type'] == 'EQ'), None)
                    
                    if not instrument:
                        continue
                    
                    # For now, we'll create earnings data based on recent price movements
                    # Note: Kite Connect doesn't provide direct earnings calendar API
                    # This is a simplified approach - in production, you might want to integrate
                    # with other data sources or use corporate actions from Kite
                    
                    # Get recent historical data to identify potential earnings dates
                    try:
                        from_date_str = from_date.strftime('%Y-%m-%d')
                        to_date_str = to_date.strftime('%Y-%m-%d')
                        
                        historical_data = kite.historical_data(
                            instrument_token=instrument['instrument_token'],
                            from_date=from_date_str,
                            to_date=to_date_str,
                            interval='day'
                        )
                        
                        # Look for significant volume/price movements that might indicate earnings
                        if historical_data and len(historical_data) > 1:
                            for data_point in historical_data:
                                date_obj = data_point['date'].date() if hasattr(data_point['date'], 'date') else data_point['date']
                                
                                # Simple heuristic: high volume compared to average
                                volumes = [d['volume'] for d in historical_data]
                                avg_volume = sum(volumes) / len(volumes)
                                
                                if data_point['volume'] > avg_volume * 2:  # Volume spike
                                    announcement = EarningsAnnouncement(
                                        symbol=symbol,
                                        company_name=instrument.get('name', f"{symbol} Limited"),
                                        announcement_date=date_obj,
                                        announcement_time="Market Hours",
                                        actual_eps=None,
                                        expected_eps=None,
                                        surprise_percent=None,
                                        revenue_actual=None,
                                        revenue_expected=None,
                                        source="Zerodha Kite Connect"
                                    )
                                    announcements.append(announcement)
                                    break  # Only one announcement per symbol
                        
                    except Exception as e:
                        logger.debug(f"Could not fetch historical data for {symbol}: {e}")
                        continue
                        
                except Exception as e:
                    logger.debug(f"Error processing {symbol} with Zerodha: {e}")
                    continue
                    
                # Add small delay to respect rate limits
                await asyncio.sleep(0.05)
            
            logger.info(f"✅ Fetched {len(announcements)} potential earnings from Zerodha")
            return announcements
            
        except Exception as e:
            logger.warning(f"⚠️ Zerodha earnings fetch failed: {e}")
            return []

    async def _scrape_moneycontrol_earnings(self, from_date: date, to_date: date) -> List[EarningsAnnouncement]:
        """Scrape MoneyControl for earnings announcements"""
        try:
            announcements = []
            
            # MoneyControl earnings calendar URL
            url = "https://www.moneycontrol.com/earnings/earnings-calendar"
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.session.get(url, timeout=10)
            )
            
            if response.status_code != 200:
                logger.warning(f"MoneyControl request failed: {response.status_code}")
                return announcements
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find earnings table
            earnings_table = soup.find('table', class_='earnings-table')
            if not earnings_table:
                logger.warning("MoneyControl earnings table not found")
                return announcements
            
            # Parse earnings rows
            rows = earnings_table.find_all('tr')[1:]  # Skip header
            
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 6:
                        continue
                    
                    # Extract data
                    company_name = cells[0].get_text(strip=True)
                    symbol = self._extract_symbol_from_name(company_name)
                    ann_date_str = cells[1].get_text(strip=True)
                    ann_time = cells[2].get_text(strip=True) if len(cells) > 2 else None
                    
                    # Parse date
                    ann_date = datetime.strptime(ann_date_str, '%d-%m-%Y').date()
                    
                    # Check if within date range
                    if from_date <= ann_date <= to_date:
                        announcement = EarningsAnnouncement(
                            symbol=symbol,
                            company_name=company_name,
                            announcement_date=ann_date,
                            announcement_time=ann_time,
                            actual_eps=None,
                            expected_eps=None,
                            surprise_percent=None,
                            revenue_actual=None,
                            revenue_expected=None,
                            source="MoneyControl"
                        )
                        announcements.append(announcement)
                        
                except Exception as e:
                    logger.warning(f"Error parsing MoneyControl row: {e}")
                    continue
            
            logger.info(f"Scraped {len(announcements)} earnings from MoneyControl")
            return announcements
            
        except Exception as e:
            logger.error(f"Error scraping MoneyControl earnings: {e}")
            return []
    
    async def _fetch_yahoo_earnings(self, from_date: date, to_date: date) -> List[EarningsAnnouncement]:
        """Fetch earnings from Yahoo Finance API"""
        try:
            announcements = []
            
            # Use major Indian stocks for Yahoo Finance earnings
            from core.market_data import StockListManager
            stock_manager = StockListManager()
            major_stocks = stock_manager.get_nifty_50()
            
            for symbol in major_stocks[:20]:  # Limit to top 20 to avoid rate limits
                try:
                    symbol_yf = f"{symbol}.NS"
                    ticker = yf.Ticker(symbol_yf)
                    
                    # Get earnings calendar
                    calendar = ticker.calendar
                    
                    if calendar is not None and not calendar.empty:
                        for idx, row in calendar.iterrows():
                            earnings_date = idx.date()
                            
                            if from_date <= earnings_date <= to_date:
                                announcement = EarningsAnnouncement(
                                    symbol=symbol,
                                    company_name=f"{symbol} Limited",
                                    announcement_date=earnings_date,
                                    announcement_time=None,
                                    actual_eps=None,
                                    expected_eps=row.get('Estimate'),
                                    surprise_percent=None,
                                    revenue_actual=None,
                                    revenue_expected=None,
                                    source="Yahoo Finance"
                                )
                                announcements.append(announcement)
                    
                    # Add delay to respect rate limits
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.warning(f"Error fetching Yahoo earnings for {symbol}: {e}")
                    continue
            
            logger.info(f"Fetched {len(announcements)} earnings from Yahoo Finance")
            return announcements
            
        except Exception as e:
            logger.error(f"Error fetching Yahoo earnings: {e}")
            return []
    
    def _extract_symbol_from_name(self, company_name: str) -> str:
        """Extract trading symbol from company name"""
        # Simple mapping for common companies
        symbol_map = {
            'Reliance Industries': 'RELIANCE',
            'Tata Consultancy Services': 'TCS',
            'Infosys': 'INFY',
            'HDFC Bank': 'HDFCBANK',
            'Hindustan Unilever': 'HINDUNILVR',
            'ICICI Bank': 'ICICIBANK',
            'State Bank of India': 'SBIN',
            'Bharti Airtel': 'BHARTIARTL',
            'ITC': 'ITC',
            'Asian Paints': 'ASIANPAINT'
        }
        
        # Check exact matches first
        if company_name in symbol_map:
            return symbol_map[company_name]
        
        # Check partial matches
        for name, symbol in symbol_map.items():
            if name.lower() in company_name.lower():
                return symbol
        
        # Default: create symbol from company name
        return company_name.replace(' ', '').upper()[:10]
    
    def _deduplicate_announcements(self, announcements: List[EarningsAnnouncement]) -> List[EarningsAnnouncement]:
        """Remove duplicate earnings announcements"""
        seen = set()
        unique_announcements = []
        
        for announcement in announcements:
            key = (announcement.symbol, announcement.announcement_date)
            if key not in seen:
                seen.add(key)
                unique_announcements.append(announcement)
        
        return unique_announcements
    
    async def get_earnings_surprise(self, symbol: str, announcement_date: date) -> Optional[float]:
        """Get earnings surprise for a specific announcement"""
        try:
            # Try to get from cache first
            cache_key = f"{symbol}_{announcement_date}"
            
            # Fetch actual vs expected EPS
            symbol_yf = f"{symbol}.NS"
            ticker = yf.Ticker(symbol_yf)
            
            # Get earnings history
            earnings = ticker.earnings_dates
            
            if earnings is not None and not earnings.empty:
                # Find earnings for the specific date
                date_earnings = earnings[earnings.index.date == announcement_date]
                
                if not date_earnings.empty:
                    actual = date_earnings['Actual'].iloc[0]
                    estimate = date_earnings['Estimate'].iloc[0]
                    
                    if actual is not None and estimate is not None and estimate != 0:
                        surprise_percent = (actual - estimate) / estimate * 100
                        return surprise_percent
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting earnings surprise for {symbol}: {e}")
            return None


class GapDetector:
    """Detect and analyze price gaps"""
    
    def __init__(self, market_data_manager: MarketDataManager):
        self.market_data_manager = market_data_manager
        self.min_gap_percent = config.min_gap_percentage
        self.max_gap_percent = config.max_gap_percentage
        
    async def detect_gap(self, symbol: str) -> Optional[GapData]:
        """Detect price gap for a symbol"""
        try:
            # Get current price
            current_price_data = await self.market_data_manager.get_real_time_price(symbol)
            if not current_price_data:
                return None
            
            # Get previous day's closing price
            previous_close = await self._get_previous_close(symbol)
            if not previous_close:
                return None
            
            current_price = current_price_data.last_price
            gap_amount = current_price - previous_close
            gap_percent = (gap_amount / previous_close) * 100
            
            # Check if gap meets minimum threshold
            if abs(gap_percent) < self.min_gap_percent * 100:
                return None
            
            # Check if gap is within maximum threshold
            if abs(gap_percent) > self.max_gap_percent * 100:
                logger.warning(f"Gap too large for {symbol}: {gap_percent:.2f}%")
                return None
            
            gap_data = GapData(
                symbol=symbol,
                previous_close=previous_close,
                current_price=current_price,
                gap_percent=gap_percent,
                gap_amount=gap_amount,
                gap_type="up" if gap_amount > 0 else "down",
                timestamp=datetime.now()
            )
            
            return gap_data
            
        except Exception as e:
            logger.error(f"Error detecting gap for {symbol}: {e}")
            return None
    
    async def _get_previous_close(self, symbol: str) -> Optional[float]:
        """Get previous trading day's closing price"""
        try:
            # Get historical data for last 5 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5)
            
            hist_data = await self.market_data_manager.get_historical_data(
                symbol, start_date, end_date, "1d"
            )
            
            if hist_data is not None and not hist_data.empty:
                # Get the last available close price
                return hist_data['Close'].iloc[-1]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting previous close for {symbol}: {e}")
            return None
    
    def validate_gap(self, gap_data: GapData, earnings_announcement: EarningsAnnouncement) -> bool:
        """Validate if gap is earnings-driven"""
        try:
            # Check if gap occurred on or after earnings announcement
            gap_date = gap_data.timestamp.date()
            earnings_date = earnings_announcement.announcement_date
            
            # Gap should occur on earnings date or next trading day
            if gap_date < earnings_date:
                return False
            
            # Check if gap is in expected direction based on earnings surprise
            if earnings_announcement.surprise_percent is not None:
                expected_direction = "up" if earnings_announcement.surprise_percent > 0 else "down"
                return gap_data.gap_type == expected_direction
            
            # If no surprise data, accept any significant gap
            return abs(gap_data.gap_percent) >= self.min_gap_percent * 100
            
        except Exception as e:
            logger.error(f"Error validating gap: {e}")
            return False


class VolumeAnalyzer:
    """Analyze trading volume patterns"""
    
    def __init__(self, market_data_manager: MarketDataManager):
        self.market_data_manager = market_data_manager
        self.volume_surge_threshold = 3.0  # 3x average volume
        
    async def analyze_volume(self, symbol: str) -> Optional[VolumeData]:
        """Analyze current volume vs historical average"""
        try:
            # Get current price data with volume
            current_data = await self.market_data_manager.get_real_time_price(symbol)
            if not current_data:
                return None
            
            # Get historical volume data
            average_volume = await self._get_average_volume(symbol)
            if not average_volume:
                return None
            
            current_volume = current_data.volume
            volume_ratio = current_volume / average_volume
            is_surge = volume_ratio >= self.volume_surge_threshold
            
            volume_data = VolumeData(
                symbol=symbol,
                current_volume=current_volume,
                average_volume_20d=average_volume,
                volume_ratio=volume_ratio,
                is_surge=is_surge,
                timestamp=datetime.now()
            )
            
            return volume_data
            
        except Exception as e:
            logger.error(f"Error analyzing volume for {symbol}: {e}")
            return None
    
    async def _get_average_volume(self, symbol: str, days: int = 20) -> Optional[float]:
        """Get average volume over specified days"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 5)  # Extra days for weekends
            
            hist_data = await self.market_data_manager.get_historical_data(
                symbol, start_date, end_date, "1d"
            )
            
            if hist_data is not None and not hist_data.empty and 'Volume' in hist_data.columns:
                # Get last 20 trading days
                recent_volume = hist_data['Volume'].tail(days)
                return recent_volume.mean()
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting average volume for {symbol}: {e}")
            return None
    
    def validate_volume_surge(self, volume_data: VolumeData, gap_data: GapData) -> bool:
        """Validate if volume surge supports the gap"""
        try:
            # Require minimum volume surge for gap validation
            min_surge = 2.0 if abs(gap_data.gap_percent) > 5 else 3.0
            
            if volume_data.volume_ratio < min_surge:
                return False
            
            # Higher volume requirements for larger gaps
            if abs(gap_data.gap_percent) > 10 and volume_data.volume_ratio < 4.0:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating volume surge: {e}")
            return False


class SignalGenerator:
    """Generate and score trading signals"""
    
    def __init__(self):
        self.min_confidence_score = 60  # Minimum confidence to generate signal
        
    def generate_signal(
        self,
        earnings_announcement: EarningsAnnouncement,
        gap_data: GapData,
        volume_data: VolumeData,
        current_price: float
    ) -> Optional[EarningsGapSignal]:
        """Generate earnings gap signal"""
        try:
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                earnings_announcement, gap_data, volume_data
            )
            
            if confidence_score < self.min_confidence_score:
                return None
            
            # Determine signal type
            signal_type = (SignalType.EARNINGS_GAP_UP if gap_data.gap_type == "up" 
                          else SignalType.EARNINGS_GAP_DOWN)
            
            # Calculate risk management levels
            stop_loss, profit_target = self._calculate_risk_levels(
                current_price, gap_data, confidence_score
            )
            
            # Generate signal explanation
            explanation = self._generate_explanation(
                earnings_announcement, gap_data, volume_data, confidence_score
            )
            
            signal = EarningsGapSignal(
                symbol=gap_data.symbol,
                company_name=earnings_announcement.company_name,
                signal_type=signal_type,
                confidence=self._get_confidence_level(confidence_score),
                confidence_score=confidence_score,
                entry_price=current_price,
                entry_time=datetime.now(),
                gap_percent=gap_data.gap_percent,
                gap_amount=gap_data.gap_amount,
                previous_close=gap_data.previous_close,
                volume_ratio=volume_data.volume_ratio,
                current_volume=volume_data.current_volume,
                earnings_surprise=earnings_announcement.surprise_percent or 0,
                actual_eps=earnings_announcement.actual_eps,
                expected_eps=earnings_announcement.expected_eps,
                stop_loss=stop_loss,
                profit_target=profit_target,
                risk_reward_ratio=abs(profit_target - current_price) / abs(current_price - stop_loss),
                signal_explanation=explanation,
                created_at=datetime.now()
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return None
    
    def _calculate_confidence_score(
        self,
        earnings_announcement: EarningsAnnouncement,
        gap_data: GapData,
        volume_data: VolumeData
    ) -> float:
        """Calculate signal confidence score (0-100)"""
        score = 0
        
        # Earnings surprise component (0-40 points)
        if earnings_announcement.surprise_percent is not None:
            surprise = abs(earnings_announcement.surprise_percent)
            if surprise >= 20:
                score += 40
            elif surprise >= 10:
                score += 30
            elif surprise >= 5:
                score += 20
            else:
                score += 10
        else:
            score += 15  # Default if no surprise data
        
        # Gap component (0-30 points)
        gap_percent = abs(gap_data.gap_percent)
        if gap_percent >= 8:
            score += 30
        elif gap_percent >= 5:
            score += 25
        elif gap_percent >= 3:
            score += 20
        else:
            score += 10
        
        # Volume component (0-30 points)
        volume_ratio = volume_data.volume_ratio
        if volume_ratio >= 5:
            score += 30
        elif volume_ratio >= 4:
            score += 25
        elif volume_ratio >= 3:
            score += 20
        else:
            score += 10
        
        return min(score, 100)
    
    def _get_confidence_level(self, score: float) -> SignalConfidence:
        """Convert score to confidence level"""
        if score >= 85:
            return SignalConfidence.VERY_HIGH
        elif score >= 75:
            return SignalConfidence.HIGH
        elif score >= 65:
            return SignalConfidence.MEDIUM
        else:
            return SignalConfidence.LOW
    
    def _calculate_risk_levels(
        self, current_price: float, gap_data: GapData, confidence_score: float
    ) -> Tuple[float, float]:
        """Calculate stop loss and profit target levels"""
        
        # Base stop loss: 3% for gap up, 2% for gap down
        if gap_data.gap_type == "up":
            stop_loss_percent = 0.03
            profit_target_percent = 0.08  # 8% profit target
        else:
            stop_loss_percent = 0.02
            profit_target_percent = 0.06  # 6% profit target
        
        # Adjust based on confidence
        if confidence_score >= 85:
            profit_target_percent *= 1.5  # Higher targets for high confidence
        elif confidence_score < 65:
            stop_loss_percent *= 0.8  # Tighter stops for low confidence
        
        # Calculate levels
        if gap_data.gap_type == "up":
            stop_loss = current_price * (1 - stop_loss_percent)
            profit_target = current_price * (1 + profit_target_percent)
        else:
            stop_loss = current_price * (1 + stop_loss_percent)
            profit_target = current_price * (1 - profit_target_percent)
        
        return stop_loss, profit_target
    
    def _generate_explanation(
        self,
        earnings_announcement: EarningsAnnouncement,
        gap_data: GapData,
        volume_data: VolumeData,
        confidence_score: float
    ) -> str:
        """Generate human-readable explanation for the signal"""
        
        surprise_text = ""
        if earnings_announcement.surprise_percent is not None:
            surprise_text = f"earnings surprise of {earnings_announcement.surprise_percent:.1f}%"
        else:
            surprise_text = "earnings announcement"
        
        gap_text = f"{gap_data.gap_percent:.1f}% gap {gap_data.gap_type}"
        volume_text = f"{volume_data.volume_ratio:.1f}x volume surge"
        
        explanation = (
            f"{earnings_announcement.company_name} shows strong momentum with "
            f"{surprise_text}, {gap_text}, and {volume_text}. "
            f"Signal confidence: {confidence_score:.0f}/100"
        )
        
        return explanation


class EarningsGapScanner:
    """Main earnings gap scanner orchestrating the entire strategy"""
    
    def __init__(self, market_data_manager: MarketDataManager):
        self.market_data_manager = market_data_manager
        self.earnings_collector = EarningsDataCollector()
        self.gap_detector = GapDetector(market_data_manager)
        self.volume_analyzer = VolumeAnalyzer(market_data_manager)
        self.signal_generator = SignalGenerator()
        
        self.db_session = get_db_session()
        self.daily_signal_count = 0
        self.max_signals_per_day = 1
        self.last_signal_date = None
        
        # Scanner state
        self.is_scanning = False
        self.scan_interval = 300  # 5 minutes
        self._scan_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> bool:
        """Initialize the scanner"""
        try:
            logger.info("Initializing earnings gap scanner...")
            
            # Check market data manager
            if not await self.market_data_manager.initialize():
                logger.error("Failed to initialize market data manager")
                return False
            
            # Reset daily counters
            self._reset_daily_counters()
            
            logger.info("Earnings gap scanner initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize earnings gap scanner: {e}")
            return False
    
    async def scan_for_signals(self) -> List[EarningsGapSignal]:
        """Scan for earnings gap signals"""
        try:
            # Check if we've reached daily signal limit
            if self._is_daily_limit_reached():
                logger.info("Daily signal limit reached, skipping scan")
                return []
            
            # Check if market is open
            market_status = await self.market_data_manager.get_market_status()
            if not market_status['is_open']:
                logger.info("Market closed, skipping scan")
                return []
            
            # Get today's earnings announcements
            today = date.today()
            yesterday = today - timedelta(days=1)
            
            earnings_announcements = await self.earnings_collector.get_earnings_calendar(
                yesterday, today
            )
            
            if not earnings_announcements:
                logger.info("No earnings announcements found for today")
                return []
            
            logger.info(f"Found {len(earnings_announcements)} earnings announcements")
            
            signals = []
            
            # Analyze each earnings announcement
            for announcement in earnings_announcements:
                try:
                    signal = await self._analyze_earnings_announcement(announcement)
                    if signal:
                        signals.append(signal)
                        
                        # Check if we've reached the daily limit
                        if len(signals) >= self.max_signals_per_day:
                            logger.info("Reached maximum signals per day")
                            break
                    
                except Exception as e:
                    logger.error(f"Error analyzing {announcement.symbol}: {e}")
                    continue
            
            # Update daily signal count
            self.daily_signal_count += len(signals)
            
            # Store signals in database
            for signal in signals:
                await self._store_signal(signal)
            
            logger.info(f"Generated {len(signals)} earnings gap signals")
            return signals
            
        except Exception as e:
            logger.error(f"Error scanning for signals: {e}")
            return []
    
    async def _analyze_earnings_announcement(self, announcement: EarningsAnnouncement) -> Optional[EarningsGapSignal]:
        """Analyze a single earnings announcement for trading signals"""
        try:
            symbol = announcement.symbol
            
            # Step 1: Detect gap
            gap_data = await self.gap_detector.detect_gap(symbol)
            if not gap_data:
                return None
            
            # Step 2: Validate gap against earnings
            if not self.gap_detector.validate_gap(gap_data, announcement):
                return None
            
            # Step 3: Analyze volume
            volume_data = await self.volume_analyzer.analyze_volume(symbol)
            if not volume_data or not volume_data.is_surge:
                return None
            
            # Step 4: Validate volume surge
            if not self.volume_analyzer.validate_volume_surge(volume_data, gap_data):
                return None
            
            # Step 5: Get earnings surprise if not available
            if announcement.surprise_percent is None:
                surprise = await self.earnings_collector.get_earnings_surprise(
                    symbol, announcement.announcement_date
                )
                announcement.surprise_percent = surprise
            
            # Step 6: Check entry criteria
            if not self._check_entry_criteria(announcement, gap_data, volume_data):
                return None
            
            # Step 7: Generate signal
            current_price = gap_data.current_price
            signal = self.signal_generator.generate_signal(
                announcement, gap_data, volume_data, current_price
            )
            
            if signal:
                logger.info(f"Generated signal for {symbol}: {signal.confidence.value} confidence")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error analyzing earnings announcement for {announcement.symbol}: {e}")
            return None
    
    def _check_entry_criteria(
        self, 
        announcement: EarningsAnnouncement, 
        gap_data: GapData, 
        volume_data: VolumeData
    ) -> bool:
        """Check if all entry criteria are met"""
        
        # Criteria 1: Earnings surprise > 5% (or significant gap if no surprise data)
        if announcement.surprise_percent is not None:
            if abs(announcement.surprise_percent) < 5:
                return False
        else:
            # If no surprise data, require larger gap
            if abs(gap_data.gap_percent) < 4:
                return False
        
        # Criteria 2: Gap > 2%
        if abs(gap_data.gap_percent) < 2:
            return False
        
        # Criteria 3: Volume > 3x average
        if volume_data.volume_ratio < 3:
            return False
        
        # Criteria 4: Within announcement timeframe (same day or next day)
        gap_date = gap_data.timestamp.date()
        announcement_date = announcement.announcement_date
        
        if gap_date < announcement_date or gap_date > announcement_date + timedelta(days=1):
            return False
        
        # Criteria 5: Market hours only (9:15 AM - 3:00 PM)
        current_time = datetime.now().time()
        market_start = datetime.strptime("09:15", "%H:%M").time()
        market_end = datetime.strptime("15:00", "%H:%M").time()
        
        if not (market_start <= current_time <= market_end):
            return False
        
        return True
    
    def _is_daily_limit_reached(self) -> bool:
        """Check if daily signal limit is reached"""
        today = date.today()
        
        # Reset counter if new day
        if self.last_signal_date != today:
            self.daily_signal_count = 0
            self.last_signal_date = today
        
        return self.daily_signal_count >= self.max_signals_per_day
    
    def _reset_daily_counters(self) -> None:
        """Reset daily counters"""
        self.daily_signal_count = 0
        self.last_signal_date = date.today()
    
    async def _store_signal(self, signal: EarningsGapSignal) -> None:
        """Store signal in database"""
        try:
            db_signal = Signal(
                symbol=signal.symbol,
                signal_type=signal.signal_type.value,
                confidence_score=signal.confidence_score,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                profit_target=signal.profit_target,
                metadata=json.dumps(signal.to_dict()),
                created_at=signal.created_at
            )
            
            self.db_session.add(db_signal)
            self.db_session.commit()
            
            logger.info(f"Stored signal for {signal.symbol} in database")
            
        except Exception as e:
            logger.error(f"Error storing signal: {e}")
            self.db_session.rollback()
    
    async def start_real_time_scanning(self) -> None:
        """Start real-time scanning"""
        if self.is_scanning:
            logger.warning("Real-time scanning already active")
            return
        
        self.is_scanning = True
        logger.info(f"Starting real-time earnings gap scanning (interval: {self.scan_interval}s)")
        
        async def scanning_loop():
            while self.is_scanning:
                try:
                    signals = await self.scan_for_signals()
                    if signals:
                        logger.info(f"Found {len(signals)} new signals")
                        
                        # Notify about new signals (can be extended for notifications)
                        for signal in signals:
                            logger.info(f"NEW SIGNAL: {signal.symbol} - {signal.signal_explanation}")
                    
                    await asyncio.sleep(self.scan_interval)
                    
                except Exception as e:
                    logger.error(f"Error in scanning loop: {e}")
                    await asyncio.sleep(60)  # Wait 1 minute before retrying
        
        self._scan_task = asyncio.create_task(scanning_loop())
    
    async def stop_real_time_scanning(self) -> None:
        """Stop real-time scanning"""
        self.is_scanning = False
        if self._scan_task:
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Real-time earnings gap scanning stopped")
    
    async def get_scan_status(self) -> Dict[str, Any]:
        """Get current scanning status"""
        return {
            "is_scanning": self.is_scanning,
            "daily_signal_count": self.daily_signal_count,
            "max_signals_per_day": self.max_signals_per_day,
            "last_signal_date": self.last_signal_date.isoformat() if self.last_signal_date else None,
            "scan_interval": self.scan_interval
        }
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            await self.stop_real_time_scanning()
            
            # Close database session
            if self.db_session:
                self.db_session.close()
            
            logger.info("Earnings gap scanner cleaned up")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# Global earnings gap scanner instance
earnings_gap_scanner = None

async def get_earnings_gap_scanner() -> EarningsGapScanner:
    """Get global earnings gap scanner instance"""
    global earnings_gap_scanner
    
    if earnings_gap_scanner is None:
        from core.market_data import market_data_manager
        earnings_gap_scanner = EarningsGapScanner(market_data_manager)
        await earnings_gap_scanner.initialize()
    
    return earnings_gap_scanner