"""
Professional order execution engine with Zerodha Kite Connect integration
Handles complete trade lifecycle from signal to execution to exit
"""
import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from datetime import datetime, timedelta, time as dt_time
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import logging
from kiteconnect import KiteConnect
from kiteconnect.exceptions import NetworkException, TokenException, OrderException

from database import get_db_session
from models.trade_models import Trade, Order, Position
from core.market_data import MarketDataManager, PriceData
from core.risk_manager import RiskManager, PositionSize
from core.earnings_scanner import EarningsGapSignal
from utils.logging_config import get_logger
from config import get_config

logger = get_logger(__name__)
config = get_config()


class OrderType(Enum):
    """Order type classifications"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"


class OrderStatus(Enum):
    """Order status classifications"""
    PENDING = "PENDING"
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    TRIGGER_PENDING = "TRIGGER PENDING"


class TransactionType(Enum):
    """Transaction type"""
    BUY = "BUY"
    SELL = "SELL"


class ProductType(Enum):
    """Product type for orders"""
    MIS = "MIS"  # Intraday
    CNC = "CNC"  # Cash and Carry
    NRML = "NRML"  # Normal


class GTTStatus(Enum):
    """GTT order status"""
    ACTIVE = "active"
    TRIGGERED = "triggered"
    DISABLED = "disabled"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class OrderRequest:
    """Order execution request"""
    symbol: str
    transaction_type: TransactionType
    quantity: int
    order_type: OrderType
    product: ProductType
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    disclosed_quantity: Optional[int] = None
    validity: str = "DAY"
    tag: Optional[str] = None


@dataclass
class OrderResponse:
    """Order execution response"""
    order_id: str
    status: OrderStatus
    symbol: str
    transaction_type: TransactionType
    quantity: int
    filled_quantity: int
    pending_quantity: int
    price: float
    average_price: float
    trigger_price: Optional[float]
    timestamp: datetime
    order_type: OrderType
    product: ProductType
    exchange_order_id: Optional[str] = None
    parent_order_id: Optional[str] = None
    status_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        result['transaction_type'] = self.transaction_type.value
        result['status'] = self.status.value
        result['order_type'] = self.order_type.value
        result['product'] = self.product.value
        return result


@dataclass
class GTTOrder:
    """GTT (Good Till Triggered) order details"""
    gtt_id: str
    symbol: str
    trigger_type: str  # "single" or "two-leg"
    trigger_price: float
    last_price: float
    orders: List[Dict]
    status: GTTStatus
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    meta: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        result['status'] = self.status.value
        return result


@dataclass
class ExecutionMetrics:
    """Trade execution performance metrics"""
    symbol: str
    signal_time: datetime
    execution_time: datetime
    entry_price: float
    expected_price: float
    slippage: float
    slippage_percent: float
    execution_delay: float
    fill_quality: str
    commission: float
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PositionStatus:
    """Real-time position status"""
    symbol: str
    quantity: int
    entry_price: float
    current_price: float
    pnl: float
    pnl_percent: float
    unrealized_pnl: float
    day_pnl: float
    position_value: float
    last_updated: datetime
    
    def to_dict(self) -> Dict:
        return asdict(self)


class ZerodhaOrderManager:
    """Direct Zerodha API interface for order management"""
    
    def __init__(self, api_key: str, access_token: str):
        self.api_key = api_key
        self.access_token = access_token
        self.kite = None
        self.rate_limiter = {
            'orders_per_day': 0,
            'orders_per_minute': 0,
            'last_minute_reset': datetime.now(),
            'last_day_reset': datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        }
        self.max_orders_per_day = 3000
        self.max_orders_per_minute = 200
        
    async def initialize(self) -> bool:
        """Initialize Zerodha KiteConnect client"""
        try:
            self.kite = KiteConnect(api_key=self.api_key)
            self.kite.set_access_token(self.access_token)
            
            # Test connection
            profile = self.kite.profile()
            logger.info(f"Connected to Zerodha for user: {profile['user_name']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Zerodha connection: {e}")
            return False
    
    def _check_rate_limits(self) -> bool:
        """Check if we're within API rate limits"""
        now = datetime.now()
        
        # Reset daily counter
        if now.date() > self.rate_limiter['last_day_reset'].date():
            self.rate_limiter['orders_per_day'] = 0
            self.rate_limiter['last_day_reset'] = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Reset minute counter
        if (now - self.rate_limiter['last_minute_reset']).total_seconds() >= 60:
            self.rate_limiter['orders_per_minute'] = 0
            self.rate_limiter['last_minute_reset'] = now
        
        # Check limits
        if self.rate_limiter['orders_per_day'] >= self.max_orders_per_day:
            logger.warning("Daily order limit reached")
            return False
            
        if self.rate_limiter['orders_per_minute'] >= self.max_orders_per_minute:
            logger.warning("Per-minute order limit reached")
            return False
            
        return True
    
    def _update_rate_limiter(self):
        """Update rate limiter counters"""
        self.rate_limiter['orders_per_day'] += 1
        self.rate_limiter['orders_per_minute'] += 1
    
    async def place_order(self, order_request: OrderRequest) -> Optional[OrderResponse]:
        """Place an order through Zerodha API"""
        if not self._check_rate_limits():
            logger.error("Rate limit exceeded, cannot place order")
            return None
        
        try:
            # Prepare order parameters
            order_params = {
                'tradingsymbol': order_request.symbol,
                'exchange': 'NSE',  # Default to NSE
                'transaction_type': order_request.transaction_type.value,
                'quantity': order_request.quantity,
                'order_type': order_request.order_type.value,
                'product': order_request.product.value,
                'validity': order_request.validity
            }
            
            # Add price for limit orders
            if order_request.order_type in [OrderType.LIMIT, OrderType.SL]:
                order_params['price'] = order_request.price
            
            # Add trigger price for stop loss orders
            if order_request.order_type in [OrderType.SL, OrderType.SL_M]:
                order_params['trigger_price'] = order_request.trigger_price
            
            # Add optional parameters
            if order_request.disclosed_quantity:
                order_params['disclosed_quantity'] = order_request.disclosed_quantity
            
            if order_request.tag:
                order_params['tag'] = order_request.tag
            
            # Place order
            order_id = self.kite.place_order(**order_params)
            self._update_rate_limiter()
            
            # Get order details
            order_details = await self.get_order_status(order_id)
            
            logger.info(f"Order placed successfully: {order_id} for {order_request.symbol}")
            return order_details
            
        except OrderException as e:
            logger.error(f"Order placement failed: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error placing order: {e}")
            return None
    
    async def get_order_status(self, order_id: str) -> Optional[OrderResponse]:
        """Get current status of an order"""
        try:
            orders = self.kite.orders()
            order_info = None
            
            for order in orders:
                if order['order_id'] == order_id:
                    order_info = order
                    break
            
            if not order_info:
                logger.warning(f"Order {order_id} not found")
                return None
            
            # Convert to OrderResponse
            return OrderResponse(
                order_id=order_info['order_id'],
                status=OrderStatus(order_info['status']),
                symbol=order_info['tradingsymbol'],
                transaction_type=TransactionType(order_info['transaction_type']),
                quantity=order_info['quantity'],
                filled_quantity=order_info['filled_quantity'],
                pending_quantity=order_info['pending_quantity'],
                price=float(order_info['price'] or 0),
                average_price=float(order_info['average_price'] or 0),
                trigger_price=float(order_info['trigger_price']) if order_info['trigger_price'] else None,
                timestamp=datetime.strptime(order_info['order_timestamp'], '%Y-%m-%d %H:%M:%S'),
                order_type=OrderType(order_info['order_type']),
                product=ProductType(order_info['product']),
                exchange_order_id=order_info.get('exchange_order_id'),
                parent_order_id=order_info.get('parent_order_id'),
                status_message=order_info.get('status_message')
            )
            
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return None
    
    async def modify_order(self, order_id: str, **kwargs) -> bool:
        """Modify an existing order"""
        try:
            self.kite.modify_order(order_id=order_id, **kwargs)
            logger.info(f"Order {order_id} modified successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error modifying order {order_id}: {e}")
            return False
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            self.kite.cancel_order(order_id=order_id)
            logger.info(f"Order {order_id} cancelled successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    async def get_positions(self) -> List[Dict]:
        """Get current positions"""
        try:
            if not self.kite:
                return []
            positions = self.kite.positions()
            if positions and isinstance(positions, dict):
                return positions.get('net', []) + positions.get('day', [])
            return []
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def get_holdings(self) -> List[Dict]:
        """Get current holdings"""
        try:
            holdings = self.kite.holdings()
            return holdings
            
        except Exception as e:
            logger.error(f"Error getting holdings: {e}")
            return []


class GTTManager:
    """GTT (Good Till Triggered) order management"""
    
    def __init__(self, zerodha_manager: ZerodhaOrderManager):
        self.zerodha_manager = zerodha_manager
        self.active_gtts: Dict[str, GTTOrder] = {}
    
    async def place_gtt_oco(self, symbol: str, quantity: int, 
                           profit_target: float, stop_loss: float,
                           current_price: float) -> Optional[str]:
        """Place GTT OCO (One Cancels Other) order for profit target and stop loss"""
        try:
            # Determine if we're long or short based on quantity
            is_long = quantity > 0
            
            # Create GTT order with two legs (profit target and stop loss)
            gtt_params = {
                'trigger_type': 'two-leg',
                'tradingsymbol': symbol,
                'exchange': 'NSE',
                'trigger_values': [profit_target, stop_loss],
                'last_price': current_price,
                'orders': [
                    {
                        'transaction_type': 'SELL' if is_long else 'BUY',
                        'quantity': abs(quantity),
                        'order_type': 'LIMIT',
                        'product': 'MIS',
                        'price': profit_target
                    },
                    {
                        'transaction_type': 'SELL' if is_long else 'BUY',
                        'quantity': abs(quantity),
                        'order_type': 'SL-M',
                        'product': 'MIS',
                        'trigger_price': stop_loss
                    }
                ]
            }
            
            # Place GTT order
            gtt_response = self.zerodha_manager.kite.place_gtt(**gtt_params)
            gtt_id = gtt_response['trigger_id']
            
            # Create GTT order object
            gtt_order = GTTOrder(
                gtt_id=gtt_id,
                symbol=symbol,
                trigger_type='two-leg',
                trigger_price=current_price,
                last_price=current_price,
                orders=gtt_params['orders'],
                status=GTTStatus.ACTIVE,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=365)  # GTT valid for 1 year
            )
            
            self.active_gtts[gtt_id] = gtt_order
            
            logger.info(f"GTT OCO placed for {symbol}: ID {gtt_id}")
            logger.info(f"  Profit target: ₹{profit_target:.2f}")
            logger.info(f"  Stop loss: ₹{stop_loss:.2f}")
            
            return gtt_id
            
        except Exception as e:
            logger.error(f"Error placing GTT OCO order: {e}")
            return None
    
    async def get_gtt_status(self, gtt_id: str) -> Optional[GTTOrder]:
        """Get status of a GTT order"""
        try:
            gtt_orders = self.zerodha_manager.kite.gtt()
            
            for gtt in gtt_orders:
                if gtt['id'] == int(gtt_id):
                    # Update our local GTT object
                    if gtt_id in self.active_gtts:
                        self.active_gtts[gtt_id].status = GTTStatus(gtt['status'])
                        self.active_gtts[gtt_id].updated_at = datetime.now()
                        return self.active_gtts[gtt_id]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting GTT status: {e}")
            return None
    
    async def modify_gtt(self, gtt_id: str, **kwargs) -> bool:
        """Modify an existing GTT order"""
        try:
            self.zerodha_manager.kite.modify_gtt(gtt_id, **kwargs)
            logger.info(f"GTT {gtt_id} modified successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error modifying GTT {gtt_id}: {e}")
            return False
    
    async def cancel_gtt(self, gtt_id: str) -> bool:
        """Cancel a GTT order"""
        try:
            self.zerodha_manager.kite.delete_gtt(gtt_id)
            
            # Update local status
            if gtt_id in self.active_gtts:
                self.active_gtts[gtt_id].status = GTTStatus.CANCELLED
                self.active_gtts[gtt_id].updated_at = datetime.now()
            
            logger.info(f"GTT {gtt_id} cancelled successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling GTT {gtt_id}: {e}")
            return False
    
    async def monitor_gtts(self) -> Dict[str, GTTOrder]:
        """Monitor all active GTT orders"""
        updated_gtts = {}
        
        for gtt_id in list(self.active_gtts.keys()):
            gtt_order = await self.get_gtt_status(gtt_id)
            if gtt_order:
                updated_gtts[gtt_id] = gtt_order
                
                # Remove completed/cancelled GTTs from active tracking
                if gtt_order.status in [GTTStatus.TRIGGERED, GTTStatus.CANCELLED, GTTStatus.EXPIRED]:
                    logger.info(f"GTT {gtt_id} status changed to {gtt_order.status.value}")
                    if gtt_id in self.active_gtts:
                        del self.active_gtts[gtt_id]
        
        return updated_gtts


class PositionTracker:
    """Real-time position tracking and monitoring"""
    
    def __init__(self, zerodha_manager: ZerodhaOrderManager, 
                 market_data_manager: MarketDataManager):
        self.zerodha_manager = zerodha_manager
        self.market_data_manager = market_data_manager
        self.positions: Dict[str, PositionStatus] = {}
        self.monitoring = False
        self.monitor_task = None
    
    async def start_monitoring(self):
        """Start real-time position monitoring"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info("Position monitoring started")
    
    async def stop_monitoring(self):
        """Stop position monitoring"""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Position monitoring stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                await self._update_positions()
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in position monitoring loop: {e}")
                await asyncio.sleep(10)  # Wait longer on error
    
    async def _update_positions(self):
        """Update all tracked positions"""
        try:
            # Get positions from Zerodha
            zerodha_positions = await self.zerodha_manager.get_positions()
            
            for pos in zerodha_positions:
                symbol = pos['tradingsymbol']
                quantity = pos['quantity']
                
                if quantity != 0:  # Only track open positions
                    # Get current price
                    current_price_data = await self.market_data_manager.get_real_time_price(symbol)
                    current_price = current_price_data.last_price if current_price_data else pos['last_price']
                    
                    # Calculate P&L
                    entry_price = pos['average_price']
                    pnl = (current_price - entry_price) * quantity
                    pnl_percent = (pnl / (entry_price * abs(quantity))) * 100
                    
                    # Update position status
                    self.positions[symbol] = PositionStatus(
                        symbol=symbol,
                        quantity=quantity,
                        entry_price=entry_price,
                        current_price=current_price,
                        pnl=pnl,
                        pnl_percent=pnl_percent,
                        unrealized_pnl=pos['unrealised'],
                        day_pnl=pos['pnl'],
                        position_value=current_price * abs(quantity),
                        last_updated=datetime.now()
                    )
                else:
                    # Remove closed positions
                    if symbol in self.positions:
                        del self.positions[symbol]
                        logger.info(f"Position closed for {symbol}")
                        
        except Exception as e:
            logger.error(f"Error updating positions: {e}")
    
    async def get_position(self, symbol: str) -> Optional[PositionStatus]:
        """Get current position status for a symbol"""
        return self.positions.get(symbol)
    
    async def get_all_positions(self) -> Dict[str, PositionStatus]:
        """Get all current positions"""
        return self.positions.copy()


class ExecutionAnalyzer:
    """Performance tracking and slippage analysis"""
    
    def __init__(self):
        self.execution_records: List[ExecutionMetrics] = []
    
    def calculate_slippage(self, expected_price: float, actual_price: float,
                          transaction_type: TransactionType) -> Tuple[float, float]:
        """Calculate slippage amount and percentage"""
        if transaction_type == TransactionType.BUY:
            slippage = actual_price - expected_price  # Positive = worse fill
        else:
            slippage = expected_price - actual_price  # Positive = worse fill
        
        slippage_percent = (slippage / expected_price) * 100
        return slippage, slippage_percent
    
    def assess_fill_quality(self, slippage_percent: float) -> str:
        """Assess the quality of order fill based on slippage"""
        abs_slippage = abs(slippage_percent)
        
        if abs_slippage <= 0.05:
            return "EXCELLENT"
        elif abs_slippage <= 0.1:
            return "GOOD"
        elif abs_slippage <= 0.2:
            return "FAIR"
        elif abs_slippage <= 0.5:
            return "POOR"
        else:
            return "VERY_POOR"
    
    def record_execution(self, symbol: str, signal_time: datetime,
                        execution_time: datetime, entry_price: float,
                        expected_price: float, commission: float = 0.0):
        """Record execution metrics for analysis"""
        slippage, slippage_percent = self.calculate_slippage(
            expected_price, entry_price, TransactionType.BUY
        )
        
        execution_delay = (execution_time - signal_time).total_seconds()
        fill_quality = self.assess_fill_quality(slippage_percent)
        
        metrics = ExecutionMetrics(
            symbol=symbol,
            signal_time=signal_time,
            execution_time=execution_time,
            entry_price=entry_price,
            expected_price=expected_price,
            slippage=slippage,
            slippage_percent=slippage_percent,
            execution_delay=execution_delay,
            fill_quality=fill_quality,
            commission=commission
        )
        
        self.execution_records.append(metrics)
        
        logger.info(f"Execution recorded for {symbol}:")
        logger.info(f"  Slippage: ₹{slippage:.2f} ({slippage_percent:+.3f}%)")
        logger.info(f"  Fill quality: {fill_quality}")
        logger.info(f"  Execution delay: {execution_delay:.2f}s")
    
    def get_performance_summary(self) -> Dict:
        """Get execution performance summary"""
        if not self.execution_records:
            return {}
        
        slippages = [r.slippage_percent for r in self.execution_records]
        delays = [r.execution_delay for r in self.execution_records]
        
        return {
            'total_executions': len(self.execution_records),
            'avg_slippage_percent': sum(slippages) / len(slippages),
            'max_slippage_percent': max(slippages),
            'min_slippage_percent': min(slippages),
            'avg_execution_delay': sum(delays) / len(delays),
            'max_execution_delay': max(delays),
            'fill_quality_distribution': {
                quality: len([r for r in self.execution_records if r.fill_quality == quality])
                for quality in ['EXCELLENT', 'GOOD', 'FAIR', 'POOR', 'VERY_POOR']
            }
        }


class OrderEngine:
    """Main order execution engine orchestrating all components"""
    
    def __init__(self, api_key: str, access_token: str, 
                 risk_manager: RiskManager, market_data_manager: MarketDataManager,
                 paper_trading: bool = False):
        self.api_key = api_key
        self.access_token = access_token
        self.risk_manager = risk_manager
        self.market_data_manager = market_data_manager
        self.paper_trading = paper_trading
        
        # Initialize components
        self.zerodha_manager = ZerodhaOrderManager(api_key, access_token)
        self.gtt_manager = GTTManager(self.zerodha_manager)
        self.position_tracker = PositionTracker(self.zerodha_manager, market_data_manager)
        self.execution_analyzer = ExecutionAnalyzer()
        
        # State tracking
        self.active_trades: Dict[str, Dict] = {}
        self.initialized = False
        self.emergency_stop = False
        
        # Performance metrics
        self.daily_stats = {
            'orders_placed': 0,
            'orders_filled': 0,
            'orders_rejected': 0,
            'total_slippage': 0.0,
            'avg_execution_time': 0.0
        }
    
    async def initialize(self) -> bool:
        """Initialize the order execution engine"""
        try:
            if not self.paper_trading:
                # Initialize Zerodha connection
                success = await self.zerodha_manager.initialize()
                if not success:
                    logger.error("Failed to initialize Zerodha connection")
                    return False
            
            # Start position monitoring
            await self.position_tracker.start_monitoring()
            
            self.initialized = True
            logger.info(f"Order engine initialized (Paper trading: {self.paper_trading})")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing order engine: {e}")
            return False
    
    async def execute_signal(self, signal: EarningsGapSignal) -> Optional[str]:
        """Execute a trading signal end-to-end"""
        if not self.initialized:
            logger.error("Order engine not initialized")
            return None
        
        if self.emergency_stop:
            logger.warning("Emergency stop active, cannot execute trades")
            return None
        
        try:
            logger.info(f"Executing signal for {signal.symbol}")
            
            # Step 1: Validate signal with risk manager
            is_valid, position_size, alerts = await self.risk_manager.validate_trade(
                symbol=signal.symbol,
                signal_type=signal.signal_type.value,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                confidence_score=signal.confidence_score
            )
            
            if not is_valid:
                logger.warning(f"Signal validation failed for {signal.symbol}")
                if alerts:
                    for alert in alerts:
                        logger.warning(f"  Alert: {alert.message}")
                return None
            
            if not position_size:
                logger.error("No position size calculated")
                return None
            
            # Step 2: Calculate quantity
            quantity = int(position_size.final_size / signal.entry_price)
            if quantity <= 0:
                logger.warning(f"Calculated quantity is zero for {signal.symbol}")
                return None
            
            logger.info(f"Position size: ₹{position_size.final_size:,.0f} ({quantity} shares)")
            
            # Step 3: Place entry order
            entry_order = await self._place_entry_order(signal, quantity)
            if not entry_order:
                logger.error(f"Failed to place entry order for {signal.symbol}")
                return None
            
            # Step 4: Monitor entry order until filled
            filled_order = await self._monitor_entry_order(entry_order)
            if not filled_order:
                logger.error(f"Entry order not filled for {signal.symbol}")
                return None
            
            # Step 5: Place exit orders (GTT OCO)
            gtt_id = await self._place_exit_orders(signal, quantity, filled_order.average_price)
            
            # Step 6: Record trade and start monitoring
            trade_id = await self._record_trade(signal, filled_order, gtt_id, position_size)
            
            # Step 7: Start position monitoring
            await self._start_trade_monitoring(trade_id, signal.symbol)
            
            logger.info(f"Signal execution completed for {signal.symbol}, Trade ID: {trade_id}")
            return trade_id
            
        except Exception as e:
            logger.error(f"Error executing signal for {signal.symbol}: {e}")
            return None
    
    async def _place_entry_order(self, signal: EarningsGapSignal, quantity: int) -> Optional[OrderResponse]:
        """Place entry order with market order for speed"""
        try:
            # Use market order for fast execution
            order_request = OrderRequest(
                symbol=signal.symbol,
                transaction_type=TransactionType.BUY if signal.signal_type.value.endswith('_up') else TransactionType.SELL,
                quantity=quantity,
                order_type=OrderType.MARKET,
                product=ProductType.MIS,  # Intraday
                tag=f"EGS_ENTRY_{signal.symbol}"
            )
            
            if self.paper_trading:
                # Simulate order placement
                return OrderResponse(
                    order_id=f"PAPER_{int(time.time())}",
                    status=OrderStatus.COMPLETE,
                    symbol=signal.symbol,
                    transaction_type=order_request.transaction_type,
                    quantity=quantity,
                    filled_quantity=quantity,
                    pending_quantity=0,
                    price=signal.entry_price,
                    average_price=signal.entry_price,
                    trigger_price=None,
                    timestamp=datetime.now(),
                    order_type=order_request.order_type,
                    product=order_request.product
                )
            else:
                # Place actual order
                return await self.zerodha_manager.place_order(order_request)
                
        except Exception as e:
            logger.error(f"Error placing entry order: {e}")
            return None
    
    async def _monitor_entry_order(self, order: OrderResponse, timeout: int = 30) -> Optional[OrderResponse]:
        """Monitor entry order until filled or timeout"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if self.paper_trading:
                    # Paper trading orders are immediately filled
                    return order
                else:
                    # Check order status
                    current_status = await self.zerodha_manager.get_order_status(order.order_id)
                    
                    if current_status:
                        if current_status.status == OrderStatus.COMPLETE:
                            logger.info(f"Entry order filled: {order.symbol} at ₹{current_status.average_price:.2f}")
                            return current_status
                        elif current_status.status in [OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                            logger.error(f"Entry order failed: {current_status.status.value}")
                            return None
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error monitoring entry order: {e}")
                break
        
        logger.warning(f"Entry order monitoring timeout for {order.symbol}")
        return None
    
    async def _place_exit_orders(self, signal: EarningsGapSignal, quantity: int, 
                               entry_price: float) -> Optional[str]:
        """Place exit orders using GTT OCO"""
        try:
            if self.paper_trading:
                # Simulate GTT placement
                return f"PAPER_GTT_{int(time.time())}"
            else:
                return await self.gtt_manager.place_gtt_oco(
                    symbol=signal.symbol,
                    quantity=quantity,
                    profit_target=signal.profit_target,
                    stop_loss=signal.stop_loss,
                    current_price=entry_price
                )
                
        except Exception as e:
            logger.error(f"Error placing exit orders: {e}")
            
            # Fallback: Place individual orders
            return await self._place_fallback_exit_orders(signal, quantity)
    
    async def _place_fallback_exit_orders(self, signal: EarningsGapSignal, 
                                        quantity: int) -> Optional[str]:
        """Fallback exit order placement if GTT fails"""
        try:
            # Place stop loss order
            sl_order_request = OrderRequest(
                symbol=signal.symbol,
                transaction_type=TransactionType.SELL if signal.signal_type.value.endswith('_up') else TransactionType.BUY,
                quantity=quantity,
                order_type=OrderType.SL_M,
                product=ProductType.MIS,
                trigger_price=signal.stop_loss,
                tag=f"EGS_SL_{signal.symbol}"
            )
            
            if not self.paper_trading:
                sl_order = await self.zerodha_manager.place_order(sl_order_request)
                if sl_order:
                    logger.info(f"Fallback stop loss order placed: {sl_order.order_id}")
                    return f"FALLBACK_{sl_order.order_id}"
            
            return "FALLBACK_PLACED"
            
        except Exception as e:
            logger.error(f"Error placing fallback exit orders: {e}")
            return None
    
    async def _record_trade(self, signal: EarningsGapSignal, order: OrderResponse,
                          gtt_id: Optional[str], position_size: PositionSize) -> str:
        """Record trade in database and active trades"""
        try:
            trade_id = f"EGS_{signal.symbol}_{int(time.time())}"
            
            # Record execution metrics
            self.execution_analyzer.record_execution(
                symbol=signal.symbol,
                signal_time=signal.entry_time,
                execution_time=order.timestamp,
                entry_price=order.average_price,
                expected_price=signal.entry_price
            )
            
            # Store in active trades
            self.active_trades[trade_id] = {
                'signal': signal,
                'entry_order': order,
                'gtt_id': gtt_id,
                'position_size': position_size,
                'status': 'ACTIVE',
                'entry_time': order.timestamp,
                'monitoring': True
            }
            
            # Save trade to database
            from models.trade_models import Trade
            from database import get_db_session
            
            try:
                with get_db_session() as db:
                    trade_record = Trade(
                        symbol=signal.symbol,
                        trade_type="BUY",
                        quantity=quantity,
                        entry_price=signal.current_price,
                        stop_loss=stop_loss,
                        target_price=target_price,
                        status="OPEN",
                        strategy="earnings_gap",
                        pnl=0.0,
                        fees=0.0
                    )
                    db.add(trade_record)
                    db.commit()
                    logger.info(f"Trade saved to database: {trade_id}")
            except Exception as db_error:
                logger.error(f"Failed to save trade to database: {db_error}")
            
            logger.info(f"Trade recorded: {trade_id}")
            return trade_id
            
        except Exception as e:
            logger.error(f"Error recording trade: {e}")
            return f"ERROR_{int(time.time())}"
    
    async def _start_trade_monitoring(self, trade_id: str, symbol: str):
        """Start monitoring a trade for time-based exits"""
        try:
            # Create monitoring task
            monitor_task = asyncio.create_task(
                self._monitor_trade_lifecycle(trade_id, symbol)
            )
            
            if trade_id in self.active_trades:
                self.active_trades[trade_id]['monitor_task'] = monitor_task
                
        except Exception as e:
            logger.error(f"Error starting trade monitoring: {e}")
    
    async def _monitor_trade_lifecycle(self, trade_id: str, symbol: str):
        """Monitor trade lifecycle for time-based exits and P&L tracking"""
        try:
            start_time = datetime.now()
            max_duration = timedelta(hours=2)  # Max 2 hours per trade
            
            while trade_id in self.active_trades:
                try:
                    # Check if trade is still active
                    if not self.active_trades[trade_id]['monitoring']:
                        break
                    
                    # Check time-based exit
                    if datetime.now() - start_time > max_duration:
                        logger.info(f"Time-based exit triggered for {symbol}")
                        await self._emergency_exit_trade(trade_id, "TIME_LIMIT")
                        break
                    
                    # Check position status
                    position = await self.position_tracker.get_position(symbol)
                    if not position:
                        # Position closed, trade completed
                        logger.info(f"Position closed for {symbol}, trade completed")
                        self._complete_trade(trade_id)
                        break
                    
                    # Log position status periodically
                    if int(time.time()) % 60 == 0:  # Every minute
                        logger.info(f"{symbol} P&L: ₹{position.pnl:+,.0f} ({position.pnl_percent:+.1f}%)")
                    
                    await asyncio.sleep(10)  # Check every 10 seconds
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in trade monitoring for {trade_id}: {e}")
                    await asyncio.sleep(30)
                    
        except Exception as e:
            logger.error(f"Error in trade lifecycle monitoring: {e}")
    
    async def _emergency_exit_trade(self, trade_id: str, reason: str):
        """Emergency exit a trade"""
        try:
            if trade_id not in self.active_trades:
                return
            
            trade_info = self.active_trades[trade_id]
            signal = trade_info['signal']
            
            logger.warning(f"Emergency exit initiated for {signal.symbol}: {reason}")
            
            # Cancel GTT orders
            if trade_info.get('gtt_id'):
                await self.gtt_manager.cancel_gtt(trade_info['gtt_id'])
            
            # Place market exit order
            position = await self.position_tracker.get_position(signal.symbol)
            if position and position.quantity != 0:
                exit_order_request = OrderRequest(
                    symbol=signal.symbol,
                    transaction_type=TransactionType.SELL if position.quantity > 0 else TransactionType.BUY,
                    quantity=abs(position.quantity),
                    order_type=OrderType.MARKET,
                    product=ProductType.MIS,
                    tag=f"EGS_EMERGENCY_{reason}"
                )
                
                if not self.paper_trading:
                    exit_order = await self.zerodha_manager.place_order(exit_order_request)
                    if exit_order:
                        logger.info(f"Emergency exit order placed: {exit_order.order_id}")
            
            # Mark trade as completed with emergency exit
            trade_info['status'] = 'EMERGENCY_EXIT'
            trade_info['exit_reason'] = reason
            trade_info['monitoring'] = False
            
        except Exception as e:
            logger.error(f"Error in emergency exit: {e}")
    
    def _complete_trade(self, trade_id: str):
        """Mark trade as completed"""
        if trade_id in self.active_trades:
            self.active_trades[trade_id]['status'] = 'COMPLETED'
            self.active_trades[trade_id]['monitoring'] = False
            self.active_trades[trade_id]['completion_time'] = datetime.now()
    
    async def emergency_stop_all(self, reason: str = "Manual stop"):
        """Emergency stop all trading activities"""
        logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
        self.emergency_stop = True
        
        # Cancel all GTT orders
        for gtt_id in list(self.gtt_manager.active_gtts.keys()):
            await self.gtt_manager.cancel_gtt(gtt_id)
        
        # Emergency exit all active trades
        for trade_id in list(self.active_trades.keys()):
            if self.active_trades[trade_id]['status'] == 'ACTIVE':
                await self._emergency_exit_trade(trade_id, f"EMERGENCY_STOP: {reason}")
        
        logger.critical("All emergency stops completed")
    
    async def get_execution_status(self) -> Dict:
        """Get current execution engine status"""
        return {
            'initialized': self.initialized,
            'paper_trading': self.paper_trading,
            'emergency_stop': self.emergency_stop,
            'active_trades': len([t for t in self.active_trades.values() if t['status'] == 'ACTIVE']),
            'total_trades': len(self.active_trades),
            'daily_stats': self.daily_stats,
            'performance_summary': self.execution_analyzer.get_performance_summary(),
            'active_positions': len(await self.position_tracker.get_all_positions()),
            'active_gtts': len(self.gtt_manager.active_gtts)
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            await self.position_tracker.stop_monitoring()
            self.initialized = False
            logger.info("Order engine cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# Singleton instance management
_order_engine_instance = None

async def get_order_engine(api_key: str = None, access_token: str = None,
                          risk_manager: RiskManager = None, 
                          market_data_manager: MarketDataManager = None,
                          paper_trading: bool = False) -> OrderEngine:
    """Get or create order engine singleton instance"""
    global _order_engine_instance
    
    if _order_engine_instance is None:
        if not all([api_key, access_token, risk_manager, market_data_manager]):
            raise ValueError("All parameters required for first initialization")
        
        _order_engine_instance = OrderEngine(
            api_key, access_token, risk_manager, market_data_manager, paper_trading
        )
        
        await _order_engine_instance.initialize()
    
    return _order_engine_instance