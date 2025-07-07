"""
Comprehensive risk management system with intelligent position sizing and circuit breakers
"""
import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta, time as dt_time
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from database import get_db_session
from models.trade_models import Trade, Performance, RiskMetrics
from core.market_data import MarketDataManager, PriceData
from utils.logging_config import get_logger
from config import get_config

logger = get_logger(__name__)
config = get_config()


class RiskLevel(Enum):
    """Risk level classifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MarketRegime(Enum):
    """Market regime types"""
    TRENDING = "trending"
    CHOPPY = "choppy"
    VOLATILE = "volatile"
    CALM = "calm"


class AlertType(Enum):
    """Risk alert types"""
    POSITION_SIZE_LIMIT = "position_size_limit"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    DRAWDOWN_LIMIT = "drawdown_limit"
    VOLATILITY_SPIKE = "volatility_spike"
    EMERGENCY_STOP = "emergency_stop"
    CORRELATION_BREACH = "correlation_breach"


@dataclass
class PositionSize:
    """Position sizing calculation result"""
    symbol: str
    base_size: float
    volatility_adjusted_size: float
    performance_adjusted_size: float
    final_size: float
    max_allowed_size: float
    size_percentage: float
    risk_amount: float
    rationale: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RiskMetrics:
    """Current risk metrics snapshot"""
    timestamp: datetime
    total_capital: float
    available_capital: float
    portfolio_value: float
    daily_pnl: float
    daily_pnl_percent: float
    max_drawdown: float
    current_drawdown: float
    portfolio_heat: float
    open_positions: int
    total_risk_amount: float
    risk_utilization: float
    volatility_percentile: float
    market_regime: MarketRegime
    risk_level: RiskLevel
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        result['market_regime'] = self.market_regime.value
        result['risk_level'] = self.risk_level.value
        return result


@dataclass
class RiskAlert:
    """Risk management alert"""
    alert_type: AlertType
    severity: RiskLevel
    message: str
    current_value: float
    limit_value: float
    timestamp: datetime
    requires_action: bool
    suggested_action: str
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        result['alert_type'] = self.alert_type.value
        result['severity'] = self.severity.value
        return result


class VolatilityAnalyzer:
    """Analyze market volatility and regime detection"""
    
    def __init__(self, market_data_manager: MarketDataManager):
        self.market_data_manager = market_data_manager
        self.atr_period = 14
        self.volatility_lookback = 60  # Days for volatility percentile
        
    async def calculate_atr(self, symbol: str, period: int = None) -> Optional[float]:
        """Calculate Average True Range"""
        try:
            if period is None:
                period = self.atr_period
            
            # Get historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period + 10)  # Extra days for weekends
            
            hist_data = await self.market_data_manager.get_historical_data(
                symbol, start_date, end_date, "1d"
            )
            
            if hist_data is None or len(hist_data) < period:
                return None
            
            # Calculate True Range
            hist_data['H-L'] = hist_data['High'] - hist_data['Low']
            hist_data['H-PC'] = abs(hist_data['High'] - hist_data['Close'].shift(1))
            hist_data['L-PC'] = abs(hist_data['Low'] - hist_data['Close'].shift(1))
            
            hist_data['TR'] = hist_data[['H-L', 'H-PC', 'L-PC']].max(axis=1)
            
            # Calculate ATR using exponential moving average
            atr = hist_data['TR'].ewm(span=period).mean().iloc[-1]
            
            return atr
            
        except Exception as e:
            logger.error(f"Error calculating ATR for {symbol}: {e}")
            return None
    
    async def get_volatility_percentile(self, symbol: str) -> Optional[float]:
        """Get current volatility percentile compared to historical"""
        try:
            # Get longer historical data for percentile calculation
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.volatility_lookback + 30)
            
            hist_data = await self.market_data_manager.get_historical_data(
                symbol, start_date, end_date, "1d"
            )
            
            if hist_data is None or len(hist_data) < 30:
                return None
            
            # Calculate daily returns
            hist_data['returns'] = hist_data['Close'].pct_change()
            
            # Calculate rolling volatility (20-day)
            hist_data['volatility'] = hist_data['returns'].rolling(window=20).std() * np.sqrt(252)
            
            # Get current volatility
            current_vol = hist_data['volatility'].iloc[-1]
            
            # Calculate percentile
            vol_series = hist_data['volatility'].dropna()
            percentile = (vol_series <= current_vol).mean() * 100
            
            return percentile
            
        except Exception as e:
            logger.error(f"Error calculating volatility percentile for {symbol}: {e}")
            return None
    
    async def detect_market_regime(self, symbol: str) -> MarketRegime:
        """Detect current market regime"""
        try:
            # Get recent price data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            hist_data = await self.market_data_manager.get_historical_data(
                symbol, start_date, end_date, "1d"
            )
            
            if hist_data is None or len(hist_data) < 20:
                return MarketRegime.CALM  # Default
            
            # Calculate various metrics
            returns = hist_data['Close'].pct_change().dropna()
            
            # Volatility
            volatility = returns.std() * np.sqrt(252)
            
            # Trend strength (using linear regression slope)
            prices = hist_data['Close'].values
            x = np.arange(len(prices))
            slope = np.polyfit(x, prices, 1)[0]
            trend_strength = abs(slope / prices.mean())
            
            # Choppiness (price oscillation)
            high_low_ratio = (hist_data['High'] - hist_data['Low']).mean() / hist_data['Close'].mean()
            
            # Market regime classification
            if volatility > 0.3:  # High volatility
                return MarketRegime.VOLATILE
            elif trend_strength > 0.02:  # Strong trend
                return MarketRegime.TRENDING
            elif high_low_ratio > 0.03:  # High intraday movement
                return MarketRegime.CHOPPY
            else:
                return MarketRegime.CALM
            
        except Exception as e:
            logger.error(f"Error detecting market regime for {symbol}: {e}")
            return MarketRegime.CALM


class PositionSizer:
    """Dynamic position sizing with volatility and performance adjustment"""
    
    def __init__(self, volatility_analyzer: VolatilityAnalyzer):
        self.volatility_analyzer = volatility_analyzer
        self.base_risk_percent = config.risk_per_trade  # 2% default
        self.max_position_size = config.max_position_size
        self.volatility_adjustment_factor = 2.0
        
    async def calculate_position_size(
        self, 
        symbol: str, 
        entry_price: float, 
        stop_loss: float, 
        account_balance: float,
        recent_performance: Optional[Dict] = None
    ) -> PositionSize:
        """Calculate optimal position size"""
        try:
            # Base position size (2% of capital)
            base_risk_amount = account_balance * self.base_risk_percent
            
            # Calculate base position size
            risk_per_share = abs(entry_price - stop_loss)
            if risk_per_share == 0:
                risk_per_share = entry_price * 0.02  # Default 2% stop
            
            base_shares = base_risk_amount / risk_per_share
            base_size = base_shares * entry_price
            
            # Volatility adjustment
            volatility_adjusted_size = await self._apply_volatility_adjustment(
                symbol, base_size, account_balance
            )
            
            # Performance adjustment
            performance_adjusted_size = self._apply_performance_adjustment(
                volatility_adjusted_size, recent_performance
            )
            
            # Apply maximum limits
            max_allowed = min(
                account_balance * 0.1,  # Max 10% of capital per position
                self.max_position_size   # Absolute max from config
            )
            
            final_size = min(performance_adjusted_size, max_allowed)
            
            # Calculate metrics
            size_percentage = (final_size / account_balance) * 100
            risk_amount = (final_size / entry_price) * risk_per_share
            
            # Generate rationale
            rationale = self._generate_sizing_rationale(
                base_size, volatility_adjusted_size, performance_adjusted_size, 
                final_size, max_allowed
            )
            
            return PositionSize(
                symbol=symbol,
                base_size=base_size,
                volatility_adjusted_size=volatility_adjusted_size,
                performance_adjusted_size=performance_adjusted_size,
                final_size=final_size,
                max_allowed_size=max_allowed,
                size_percentage=size_percentage,
                risk_amount=risk_amount,
                rationale=rationale
            )
            
        except Exception as e:
            logger.error(f"Error calculating position size for {symbol}: {e}")
            # Return minimal safe position
            safe_size = min(account_balance * 0.01, 1000)  # 1% or ₹1000
            return PositionSize(
                symbol=symbol,
                base_size=safe_size,
                volatility_adjusted_size=safe_size,
                performance_adjusted_size=safe_size,
                final_size=safe_size,
                max_allowed_size=safe_size,
                size_percentage=1.0,
                risk_amount=safe_size * 0.02,
                rationale="Error in calculation - using safe minimal size"
            )
    
    async def _apply_volatility_adjustment(
        self, symbol: str, base_size: float, account_balance: float
    ) -> float:
        """Adjust position size based on volatility"""
        try:
            # Get volatility metrics
            atr = await self.volatility_analyzer.calculate_atr(symbol)
            vol_percentile = await self.volatility_analyzer.get_volatility_percentile(symbol)
            regime = await self.volatility_analyzer.detect_market_regime(symbol)
            
            adjustment_factor = 1.0
            
            # ATR-based adjustment
            if atr is not None:
                # Get current price for ATR percentage
                current_price_data = await self.volatility_analyzer.market_data_manager.get_real_time_price(symbol)
                if current_price_data:
                    atr_percent = (atr / current_price_data.last_price) * 100
                    
                    if atr_percent > 5:  # High ATR
                        adjustment_factor *= 0.7
                    elif atr_percent < 2:  # Low ATR
                        adjustment_factor *= 1.2
            
            # Volatility percentile adjustment
            if vol_percentile is not None:
                if vol_percentile > 80:  # High volatility
                    adjustment_factor *= 0.6
                elif vol_percentile < 20:  # Low volatility
                    adjustment_factor *= 1.3
            
            # Market regime adjustment
            regime_adjustments = {
                MarketRegime.VOLATILE: 0.5,
                MarketRegime.CHOPPY: 0.7,
                MarketRegime.TRENDING: 1.2,
                MarketRegime.CALM: 1.1
            }
            adjustment_factor *= regime_adjustments.get(regime, 1.0)
            
            # Apply adjustment with bounds
            adjustment_factor = max(0.3, min(2.0, adjustment_factor))
            adjusted_size = base_size * adjustment_factor
            
            return adjusted_size
            
        except Exception as e:
            logger.error(f"Error applying volatility adjustment: {e}")
            return base_size
    
    def _apply_performance_adjustment(
        self, base_size: float, recent_performance: Optional[Dict]
    ) -> float:
        """Adjust position size based on recent performance"""
        try:
            if recent_performance is None:
                return base_size
            
            # Get performance metrics
            win_rate = recent_performance.get('win_rate', 0.5)
            avg_return = recent_performance.get('avg_return', 0.0)
            consecutive_losses = recent_performance.get('consecutive_losses', 0)
            trades_count = recent_performance.get('trades_count', 0)
            
            adjustment_factor = 1.0
            
            # Win rate adjustment
            if trades_count >= 5:  # Enough trades for statistical significance
                if win_rate > 0.7:  # High win rate
                    adjustment_factor *= 1.2
                elif win_rate < 0.3:  # Low win rate
                    adjustment_factor *= 0.7
            
            # Average return adjustment
            if avg_return > 0.05:  # Positive 5%+ average
                adjustment_factor *= 1.1
            elif avg_return < -0.03:  # Negative 3%+ average
                adjustment_factor *= 0.8
            
            # Consecutive losses penalty
            if consecutive_losses >= 3:
                adjustment_factor *= 0.5
            elif consecutive_losses >= 2:
                adjustment_factor *= 0.8
            
            # Apply bounds
            adjustment_factor = max(0.2, min(1.5, adjustment_factor))
            
            return base_size * adjustment_factor
            
        except Exception as e:
            logger.error(f"Error applying performance adjustment: {e}")
            return base_size
    
    def _generate_sizing_rationale(
        self, 
        base_size: float, 
        vol_adjusted: float, 
        perf_adjusted: float, 
        final_size: float, 
        max_allowed: float
    ) -> str:
        """Generate human-readable rationale for position sizing"""
        
        rationale_parts = []
        
        # Base size
        rationale_parts.append(f"Base: ₹{base_size:,.0f}")
        
        # Volatility adjustment
        vol_change = (vol_adjusted / base_size - 1) * 100
        if abs(vol_change) > 5:
            direction = "reduced" if vol_change < 0 else "increased"
            rationale_parts.append(f"Volatility {direction} by {abs(vol_change):.0f}%")
        
        # Performance adjustment
        perf_change = (perf_adjusted / vol_adjusted - 1) * 100
        if abs(perf_change) > 5:
            direction = "reduced" if perf_change < 0 else "increased"
            rationale_parts.append(f"Performance {direction} by {abs(perf_change):.0f}%")
        
        # Maximum limit check
        if final_size < perf_adjusted:
            limit_reduction = (1 - final_size / perf_adjusted) * 100
            rationale_parts.append(f"Limited by max size (-{limit_reduction:.0f}%)")
        
        return ", ".join(rationale_parts)


class CircuitBreaker:
    """Monitor risk limits and implement circuit breakers"""
    
    def __init__(self):
        self.daily_loss_limit = config.max_daily_loss
        self.max_drawdown_limit = 0.10  # 10%
        self.max_portfolio_heat = 0.15  # 15%
        self.max_open_positions = config.max_open_positions
        
        self.is_trading_halted = False
        self.halt_reason = None
        self.halt_timestamp = None
        
    def check_daily_loss_limit(self, daily_pnl: float, account_balance: float) -> Optional[RiskAlert]:
        """Check daily loss limit"""
        daily_loss_percent = abs(daily_pnl) / account_balance
        
        if daily_pnl < 0 and daily_loss_percent >= 0.03:  # 3% daily loss limit
            return RiskAlert(
                alert_type=AlertType.DAILY_LOSS_LIMIT,
                severity=RiskLevel.CRITICAL,
                message=f"Daily loss limit breached: {daily_loss_percent:.1%}",
                current_value=daily_loss_percent,
                limit_value=0.03,
                timestamp=datetime.now(),
                requires_action=True,
                suggested_action="Halt trading for the day"
            )
        elif daily_pnl < 0 and daily_loss_percent >= 0.02:  # Warning at 2%
            return RiskAlert(
                alert_type=AlertType.DAILY_LOSS_LIMIT,
                severity=RiskLevel.HIGH,
                message=f"Approaching daily loss limit: {daily_loss_percent:.1%}",
                current_value=daily_loss_percent,
                limit_value=0.03,
                timestamp=datetime.now(),
                requires_action=False,
                suggested_action="Consider reducing position sizes"
            )
        
        return None
    
    def check_drawdown_limit(self, current_drawdown: float) -> Optional[RiskAlert]:
        """Check maximum drawdown limit"""
        if current_drawdown >= self.max_drawdown_limit:
            return RiskAlert(
                alert_type=AlertType.DRAWDOWN_LIMIT,
                severity=RiskLevel.CRITICAL,
                message=f"Maximum drawdown breached: {current_drawdown:.1%}",
                current_value=current_drawdown,
                limit_value=self.max_drawdown_limit,
                timestamp=datetime.now(),
                requires_action=True,
                suggested_action="Emergency stop - review strategy"
            )
        elif current_drawdown >= self.max_drawdown_limit * 0.8:  # Warning at 8%
            return RiskAlert(
                alert_type=AlertType.DRAWDOWN_LIMIT,
                severity=RiskLevel.HIGH,
                message=f"Approaching drawdown limit: {current_drawdown:.1%}",
                current_value=current_drawdown,
                limit_value=self.max_drawdown_limit,
                timestamp=datetime.now(),
                requires_action=False,
                suggested_action="Reduce risk and monitor closely"
            )
        
        return None
    
    def check_portfolio_heat(self, portfolio_heat: float) -> Optional[RiskAlert]:
        """Check portfolio heat (total risk exposure)"""
        if portfolio_heat >= self.max_portfolio_heat:
            return RiskAlert(
                alert_type=AlertType.POSITION_SIZE_LIMIT,
                severity=RiskLevel.HIGH,
                message=f"Portfolio heat too high: {portfolio_heat:.1%}",
                current_value=portfolio_heat,
                limit_value=self.max_portfolio_heat,
                timestamp=datetime.now(),
                requires_action=True,
                suggested_action="Reduce position sizes or close positions"
            )
        
        return None
    
    def check_position_limits(self, open_positions: int) -> Optional[RiskAlert]:
        """Check position count limits"""
        if open_positions >= self.max_open_positions:
            return RiskAlert(
                alert_type=AlertType.POSITION_SIZE_LIMIT,
                severity=RiskLevel.MEDIUM,
                message=f"Maximum positions reached: {open_positions}",
                current_value=open_positions,
                limit_value=self.max_open_positions,
                timestamp=datetime.now(),
                requires_action=True,
                suggested_action="Cannot open new positions"
            )
        
        return None
    
    def halt_trading(self, reason: str) -> None:
        """Halt all trading activities"""
        self.is_trading_halted = True
        self.halt_reason = reason
        self.halt_timestamp = datetime.now()
        logger.critical(f"TRADING HALTED: {reason}")
    
    def resume_trading(self, override_reason: str) -> None:
        """Resume trading activities"""
        self.is_trading_halted = False
        old_reason = self.halt_reason
        self.halt_reason = None
        self.halt_timestamp = None
        logger.warning(f"Trading resumed: {override_reason} (was halted for: {old_reason})")


class EmergencyManager:
    """Handle emergency protocols and crisis management"""
    
    def __init__(self, market_data_manager: MarketDataManager):
        self.market_data_manager = market_data_manager
        self.emergency_stop_triggered = False
        self.emergency_timestamp = None
        
    async def trigger_emergency_stop(self, reason: str) -> None:
        """Trigger emergency stop protocol"""
        try:
            self.emergency_stop_triggered = True
            self.emergency_timestamp = datetime.now()
            
            logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
            
            # Here you would:
            # 1. Immediately halt all new trading
            # 2. Close all open positions (if configured)
            # 3. Send emergency notifications
            # 4. Log all emergency actions
            
            # For now, just log the emergency
            logger.critical("Emergency protocols activated - manual intervention required")
            
        except Exception as e:
            logger.error(f"Error during emergency stop: {e}")
    
    def check_emergency_conditions(self, risk_metrics: RiskMetrics) -> bool:
        """Check if emergency conditions are met"""
        emergency_conditions = [
            risk_metrics.daily_pnl_percent < -0.05,  # 5% daily loss
            risk_metrics.current_drawdown > 0.12,    # 12% drawdown
            risk_metrics.portfolio_heat > 0.20,      # 20% portfolio heat
        ]
        
        return any(emergency_conditions)
    
    async def get_emergency_status(self) -> Dict[str, Any]:
        """Get current emergency status"""
        return {
            "emergency_stop_active": self.emergency_stop_triggered,
            "emergency_timestamp": self.emergency_timestamp.isoformat() if self.emergency_timestamp else None,
            "time_since_emergency": (datetime.now() - self.emergency_timestamp).total_seconds() 
                                  if self.emergency_timestamp else None
        }


class RiskManager:
    """Main risk management coordinator"""
    
    def __init__(self, market_data_manager: MarketDataManager):
        self.market_data_manager = market_data_manager
        self.volatility_analyzer = VolatilityAnalyzer(market_data_manager)
        self.position_sizer = PositionSizer(self.volatility_analyzer)
        self.circuit_breaker = CircuitBreaker()
        self.emergency_manager = EmergencyManager(market_data_manager)
        
        self.db_session = get_db_session()
        
        # Risk monitoring
        self.current_metrics: Optional[RiskMetrics] = None
        self.alerts: List[RiskAlert] = []
        
        # Performance tracking
        self.account_balance = 100000.0  # Default starting balance
        self.peak_balance = self.account_balance
        self.daily_start_balance = self.account_balance
        
    async def initialize(self) -> bool:
        """Initialize risk management system"""
        try:
            logger.info("Initializing risk management system...")
            
            # Load account balance from database or config
            await self._load_account_data()
            
            # Initialize risk metrics
            await self._update_risk_metrics()
            
            logger.info("Risk management system initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize risk management system: {e}")
            return False
    
    async def validate_trade(
        self, 
        symbol: str, 
        signal_type: str, 
        entry_price: float, 
        stop_loss: float,
        confidence_score: float
    ) -> Tuple[bool, Optional[PositionSize], List[RiskAlert]]:
        """Validate a trade before execution"""
        try:
            alerts = []
            
            # Check if trading is halted
            if self.circuit_breaker.is_trading_halted:
                alerts.append(RiskAlert(
                    alert_type=AlertType.EMERGENCY_STOP,
                    severity=RiskLevel.CRITICAL,
                    message=f"Trading halted: {self.circuit_breaker.halt_reason}",
                    current_value=1,
                    limit_value=0,
                    timestamp=datetime.now(),
                    requires_action=True,
                    suggested_action="Cannot execute trades while halted"
                ))
                return False, None, alerts
            
            # Update current risk metrics
            await self._update_risk_metrics()
            
            # Check circuit breakers
            circuit_alerts = self._check_all_circuit_breakers()
            alerts.extend(circuit_alerts)
            
            # Check if any critical alerts would prevent trading
            critical_alerts = [a for a in circuit_alerts if a.severity == RiskLevel.CRITICAL]
            if critical_alerts:
                return False, None, alerts
            
            # Calculate position size
            recent_performance = await self._get_recent_performance()
            position_size = await self.position_sizer.calculate_position_size(
                symbol, entry_price, stop_loss, self.account_balance, recent_performance
            )
            
            # Validate position size
            if position_size.final_size < 1000:  # Minimum position size
                alerts.append(RiskAlert(
                    alert_type=AlertType.POSITION_SIZE_LIMIT,
                    severity=RiskLevel.HIGH,
                    message="Position size too small to be viable",
                    current_value=position_size.final_size,
                    limit_value=1000,
                    timestamp=datetime.now(),
                    requires_action=True,
                    suggested_action="Increase account balance or adjust risk parameters"
                ))
                return False, position_size, alerts
            
            # Check if we can afford this position
            if position_size.final_size > self.account_balance * 0.5:
                alerts.append(RiskAlert(
                    alert_type=AlertType.POSITION_SIZE_LIMIT,
                    severity=RiskLevel.HIGH,
                    message="Position size exceeds safe allocation",
                    current_value=position_size.size_percentage,
                    limit_value=50.0,
                    timestamp=datetime.now(),
                    requires_action=True,
                    suggested_action="Reduce position size"
                ))
                return False, position_size, alerts
            
            # Additional validation based on confidence
            if confidence_score < 70 and position_size.size_percentage > 5:
                # Reduce position size for low confidence signals
                position_size.final_size *= 0.7
                position_size.size_percentage = (position_size.final_size / self.account_balance) * 100
                position_size.rationale += " (reduced for low confidence)"
                
                alerts.append(RiskAlert(
                    alert_type=AlertType.POSITION_SIZE_LIMIT,
                    severity=RiskLevel.MEDIUM,
                    message="Position size reduced due to low signal confidence",
                    current_value=confidence_score,
                    limit_value=70,
                    timestamp=datetime.now(),
                    requires_action=False,
                    suggested_action="Consider waiting for higher confidence signals"
                ))
            
            return True, position_size, alerts
            
        except Exception as e:
            logger.error(f"Error validating trade for {symbol}: {e}")
            return False, None, [RiskAlert(
                alert_type=AlertType.EMERGENCY_STOP,
                severity=RiskLevel.CRITICAL,
                message=f"Error in trade validation: {e}",
                current_value=0,
                limit_value=0,
                timestamp=datetime.now(),
                requires_action=True,
                suggested_action="Check system logs and resolve errors"
            )]
    
    async def monitor_position(
        self, symbol: str, current_price: float, entry_price: float, 
        stop_loss: float, position_size: float
    ) -> List[RiskAlert]:
        """Monitor an open position for risk"""
        try:
            alerts = []
            
            # Calculate current P&L
            if entry_price > 0:
                unrealized_pnl = (current_price - entry_price) / entry_price
                unrealized_amount = unrealized_pnl * position_size
                
                # Check for large adverse moves
                if unrealized_pnl < -0.10:  # 10% adverse move
                    alerts.append(RiskAlert(
                        alert_type=AlertType.POSITION_SIZE_LIMIT,
                        severity=RiskLevel.HIGH,
                        message=f"{symbol}: Large adverse move {unrealized_pnl:.1%}",
                        current_value=abs(unrealized_pnl),
                        limit_value=0.10,
                        timestamp=datetime.now(),
                        requires_action=True,
                        suggested_action="Consider closing position or tightening stop"
                    ))
                
                # Check volatility spike
                volatility_percentile = await self.volatility_analyzer.get_volatility_percentile(symbol)
                if volatility_percentile and volatility_percentile > 95:
                    alerts.append(RiskAlert(
                        alert_type=AlertType.VOLATILITY_SPIKE,
                        severity=RiskLevel.MEDIUM,
                        message=f"{symbol}: Extreme volatility detected",
                        current_value=volatility_percentile,
                        limit_value=95,
                        timestamp=datetime.now(),
                        requires_action=False,
                        suggested_action="Monitor position closely"
                    ))
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error monitoring position for {symbol}: {e}")
            return []
    
    async def update_account_balance(self, new_balance: float) -> None:
        """Update account balance and related metrics"""
        try:
            old_balance = self.account_balance
            self.account_balance = new_balance
            
            # Update peak balance
            if new_balance > self.peak_balance:
                self.peak_balance = new_balance
            
            # Log significant changes
            change_percent = (new_balance - old_balance) / old_balance
            if abs(change_percent) > 0.01:  # 1% change
                logger.info(f"Account balance updated: ₹{old_balance:,.0f} -> ₹{new_balance:,.0f} ({change_percent:+.1%})")
            
            # Update risk metrics
            await self._update_risk_metrics()
            
        except Exception as e:
            logger.error(f"Error updating account balance: {e}")
    
    async def get_risk_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive risk dashboard data"""
        try:
            await self._update_risk_metrics()
            
            # Get recent alerts
            recent_alerts = [a for a in self.alerts if 
                           (datetime.now() - a.timestamp).total_seconds() < 3600]  # Last hour
            
            # Get emergency status
            emergency_status = await self.emergency_manager.get_emergency_status()
            
            dashboard = {
                "risk_metrics": self.current_metrics.to_dict() if self.current_metrics else None,
                "recent_alerts": [a.to_dict() for a in recent_alerts],
                "circuit_breaker_status": {
                    "is_halted": self.circuit_breaker.is_trading_halted,
                    "halt_reason": self.circuit_breaker.halt_reason,
                    "halt_timestamp": self.circuit_breaker.halt_timestamp.isoformat() 
                                    if self.circuit_breaker.halt_timestamp else None
                },
                "emergency_status": emergency_status,
                "account_info": {
                    "current_balance": self.account_balance,
                    "peak_balance": self.peak_balance,
                    "daily_start_balance": self.daily_start_balance,
                    "current_drawdown": (self.peak_balance - self.account_balance) / self.peak_balance
                }
            }
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Error generating risk dashboard: {e}")
            return {"error": str(e)}
    
    def _check_all_circuit_breakers(self) -> List[RiskAlert]:
        """Check all circuit breaker conditions"""
        alerts = []
        
        if self.current_metrics:
            # Daily loss limit
            daily_alert = self.circuit_breaker.check_daily_loss_limit(
                self.current_metrics.daily_pnl, self.account_balance
            )
            if daily_alert:
                alerts.append(daily_alert)
                if daily_alert.severity == RiskLevel.CRITICAL:
                    self.circuit_breaker.halt_trading("Daily loss limit breached")
            
            # Drawdown limit
            drawdown_alert = self.circuit_breaker.check_drawdown_limit(
                self.current_metrics.current_drawdown
            )
            if drawdown_alert:
                alerts.append(drawdown_alert)
                if drawdown_alert.severity == RiskLevel.CRITICAL:
                    self.circuit_breaker.halt_trading("Maximum drawdown breached")
            
            # Portfolio heat
            heat_alert = self.circuit_breaker.check_portfolio_heat(
                self.current_metrics.portfolio_heat
            )
            if heat_alert:
                alerts.append(heat_alert)
            
            # Position limits
            position_alert = self.circuit_breaker.check_position_limits(
                self.current_metrics.open_positions
            )
            if position_alert:
                alerts.append(position_alert)
            
            # Emergency conditions
            if self.emergency_manager.check_emergency_conditions(self.current_metrics):
                if not self.emergency_manager.emergency_stop_triggered:
                    asyncio.create_task(self.emergency_manager.trigger_emergency_stop(
                        "Multiple risk thresholds breached"
                    ))
        
        # Store alerts
        self.alerts.extend(alerts)
        
        return alerts
    
    async def _update_risk_metrics(self) -> None:
        """Update current risk metrics"""
        try:
            # Calculate daily P&L
            daily_pnl = self.account_balance - self.daily_start_balance
            daily_pnl_percent = daily_pnl / self.daily_start_balance
            
            # Calculate drawdown
            current_drawdown = (self.peak_balance - self.account_balance) / self.peak_balance
            max_drawdown = current_drawdown  # Simplified - would track historical max
            
            # Get open positions (simplified - would query database)
            open_positions = 1 if self.account_balance < self.daily_start_balance else 0
            
            # Calculate portfolio heat (simplified)
            portfolio_heat = min(0.15, abs(daily_pnl_percent))
            
            # Risk utilization
            available_capital = self.account_balance * 0.8  # 80% usable
            risk_utilization = portfolio_heat / 0.15  # Percentage of max heat
            
            # Determine risk level
            if current_drawdown > 0.08 or daily_pnl_percent < -0.025:
                risk_level = RiskLevel.CRITICAL
            elif current_drawdown > 0.05 or daily_pnl_percent < -0.015:
                risk_level = RiskLevel.HIGH
            elif current_drawdown > 0.02 or daily_pnl_percent < -0.005:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW
            
            self.current_metrics = RiskMetrics(
                timestamp=datetime.now(),
                total_capital=self.account_balance,
                available_capital=available_capital,
                portfolio_value=self.account_balance,
                daily_pnl=daily_pnl,
                daily_pnl_percent=daily_pnl_percent,
                max_drawdown=max_drawdown,
                current_drawdown=current_drawdown,
                portfolio_heat=portfolio_heat,
                open_positions=open_positions,
                total_risk_amount=abs(daily_pnl),
                risk_utilization=risk_utilization,
                volatility_percentile=50.0,  # Default
                market_regime=MarketRegime.CALM,  # Default
                risk_level=risk_level
            )
            
        except Exception as e:
            logger.error(f"Error updating risk metrics: {e}")
    
    async def _load_account_data(self) -> None:
        """Load account data from database"""
        try:
            # Would load from database - using defaults for now
            self.account_balance = 100000.0
            self.peak_balance = self.account_balance
            self.daily_start_balance = self.account_balance
            
            logger.info(f"Loaded account balance: ₹{self.account_balance:,.0f}")
            
        except Exception as e:
            logger.error(f"Error loading account data: {e}")
    
    async def _get_recent_performance(self) -> Optional[Dict]:
        """Get recent trading performance metrics"""
        try:
            # Would calculate from database - using defaults for now
            return {
                'win_rate': 0.65,
                'avg_return': 0.025,
                'consecutive_losses': 0,
                'trades_count': 10
            }
            
        except Exception as e:
            logger.error(f"Error getting recent performance: {e}")
            return None
    
    async def cleanup(self) -> None:
        """Cleanup risk management resources"""
        try:
            if self.db_session:
                self.db_session.close()
            
            logger.info("Risk management system cleaned up")
            
        except Exception as e:
            logger.error(f"Error during risk management cleanup: {e}")


# Global risk manager instance
risk_manager = None

async def get_risk_manager() -> RiskManager:
    """Get global risk manager instance"""
    global risk_manager
    
    if risk_manager is None:
        from core.market_data import market_data_manager
        risk_manager = RiskManager(market_data_manager)
        await risk_manager.initialize()
    
    return risk_manager