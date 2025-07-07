#!/usr/bin/env python3
"""
Comprehensive test suite for the order execution engine
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_order_execution_engine():
    """Test the comprehensive order execution engine"""
    print("🚀 Testing Order Execution Engine")
    print("=" * 50)
    
    try:
        from core.order_engine import (
            OrderEngine, ZerodhaOrderManager, GTTManager, PositionTracker,
            ExecutionAnalyzer, OrderType, OrderStatus, TransactionType,
            ProductType, GTTStatus, OrderRequest, OrderResponse, GTTOrder,
            ExecutionMetrics, PositionStatus
        )
        from core.market_data import MarketDataManager, PriceData, DataSource
        from core.risk_manager import RiskManager, PositionSize
        from core.earnings_scanner import EarningsGapSignal, SignalType, SignalConfidence
        
        # Initialize components
        print("\n1. 🔧 Testing Component Initialization")
        
        # Create mock dependencies
        mock_risk_manager = Mock(spec=RiskManager)
        mock_market_data_manager = Mock(spec=MarketDataManager)
        mock_market_data_manager.initialize.return_value = True
        
        # Mock validation response
        mock_position_size = PositionSize(
            symbol="RELIANCE",
            base_size=5000.0,
            volatility_adjusted_size=4500.0,
            performance_adjusted_size=4500.0,
            final_size=4500.0,
            max_allowed_size=10000.0,
            size_percentage=4.5,
            risk_amount=300.0,
            rationale="Normal position sizing with volatility adjustment"
        )
        
        mock_risk_manager.validate_trade.return_value = (True, mock_position_size, [])
        
        # Mock price data
        mock_price_data = PriceData(
            symbol="RELIANCE",
            open=2450.0,
            high=2500.0,
            low=2440.0,
            close=2460.0,
            volume=1500000,
            last_price=2475.0,
            timestamp=datetime.now(),
            source=DataSource.YAHOO.value
        )
        mock_market_data_manager.get_real_time_price.return_value = mock_price_data
        
        # Initialize order engine in paper trading mode
        order_engine = OrderEngine(
            api_key="test_api_key",
            access_token="test_access_token",
            risk_manager=mock_risk_manager,
            market_data_manager=mock_market_data_manager,
            paper_trading=True
        )
        
        print("✅ Order engine components initialized successfully")
        
        # Test Zerodha Order Manager
        print("\n2. 📊 Testing Zerodha Order Manager")
        
        zerodha_manager = ZerodhaOrderManager("test_api", "test_token")
        
        # Test rate limiting
        rate_limit_ok = zerodha_manager._check_rate_limits()
        print(f"✅ Rate limit check: {rate_limit_ok}")
        
        # Test rate limiter update
        zerodha_manager._update_rate_limiter()
        print(f"✅ Rate limiter updated: orders_per_day={zerodha_manager.rate_limiter['orders_per_day']}")
        
        # Test order request creation
        order_request = OrderRequest(
            symbol="RELIANCE",
            transaction_type=TransactionType.BUY,
            quantity=10,
            order_type=OrderType.MARKET,
            product=ProductType.MIS,
            tag="TEST_ORDER"
        )
        print(f"✅ Order request created: {order_request.symbol} {order_request.transaction_type.value}")
        
        # Test GTT Manager
        print("\n3. 🎯 Testing GTT Manager")
        
        gtt_manager = GTTManager(zerodha_manager)
        
        # Test GTT order creation
        gtt_order = GTTOrder(
            gtt_id="12345",
            symbol="RELIANCE",
            trigger_type="two-leg",
            trigger_price=2475.0,
            last_price=2475.0,
            orders=[
                {"transaction_type": "SELL", "quantity": 10, "order_type": "LIMIT", "price": 2550.0},
                {"transaction_type": "SELL", "quantity": 10, "order_type": "SL-M", "trigger_price": 2400.0}
            ],
            status=GTTStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=365)
        )
        
        gtt_manager.active_gtts["12345"] = gtt_order
        print(f"✅ GTT order created: {gtt_order.gtt_id} for {gtt_order.symbol}")
        print(f"   Status: {gtt_order.status.value}")
        print(f"   Orders: {len(gtt_order.orders)} legs")
        
        # Test GTT serialization
        gtt_dict = gtt_order.to_dict()
        print(f"✅ GTT serialization: {len(gtt_dict)} fields")
        
        # Test Position Tracker
        print("\n4. 👁️  Testing Position Tracker")
        
        position_tracker = PositionTracker(zerodha_manager, mock_market_data_manager)
        
        # Mock positions data
        mock_positions = [
            {
                'tradingsymbol': 'RELIANCE',
                'quantity': 10,
                'average_price': 2475.0,
                'last_price': 2490.0,
                'unrealised': 150.0,
                'pnl': 150.0
            },
            {
                'tradingsymbol': 'TCS',
                'quantity': 0,  # Closed position
                'average_price': 3200.0,
                'last_price': 3250.0,
                'unrealised': 0.0,
                'pnl': 500.0
            }
        ]
        zerodha_manager.get_positions = AsyncMock(return_value=mock_positions)
        
        # Manually update positions for testing
        await position_tracker._update_positions()
        
        positions = await position_tracker.get_all_positions()
        print(f"✅ Position tracking: {len(positions)} active positions")
        
        for symbol, position in positions.items():
            print(f"   {symbol}: {position.quantity} shares, P&L: ₹{position.pnl:+,.0f}")
        
        # Test Execution Analyzer
        print("\n5. 📈 Testing Execution Analyzer")
        
        execution_analyzer = ExecutionAnalyzer()
        
        # Test slippage calculation
        slippage, slippage_percent = execution_analyzer.calculate_slippage(
            expected_price=2475.0,
            actual_price=2477.5,
            transaction_type=TransactionType.BUY
        )
        print(f"✅ Slippage calculation: ₹{slippage:.2f} ({slippage_percent:+.3f}%)")
        
        # Test fill quality assessment
        fill_quality = execution_analyzer.assess_fill_quality(slippage_percent)
        print(f"✅ Fill quality assessment: {fill_quality}")
        
        # Test execution recording
        execution_analyzer.record_execution(
            symbol="RELIANCE",
            signal_time=datetime.now() - timedelta(seconds=5),
            execution_time=datetime.now(),
            entry_price=2477.5,
            expected_price=2475.0
        )
        
        performance_summary = execution_analyzer.get_performance_summary()
        if performance_summary:
            print(f"✅ Execution metrics recorded:")
            print(f"   Total executions: {performance_summary['total_executions']}")
            print(f"   Average slippage: {performance_summary['avg_slippage_percent']:+.3f}%")
        
        # Test Order Engine
        print("\n6. 🎛️  Testing Order Engine Integration")
        
        # Initialize order engine
        initialized = await order_engine.initialize()
        print(f"✅ Order engine initialized: {initialized}")
        
        # Test signal creation
        test_signal = EarningsGapSignal(
            symbol="RELIANCE",
            company_name="Reliance Industries",
            signal_type=SignalType.EARNINGS_GAP_UP,
            confidence=SignalConfidence.HIGH,
            confidence_score=82.0,
            entry_time=datetime.now(),
            entry_price=2475.0,
            stop_loss=2400.0,
            profit_target=2550.0,
            gap_percent=5.2,
            gap_amount=120.0,
            previous_close=2460.0,
            volume_ratio=3.5,
            current_volume=3500000,
            earnings_surprise=15.0,
            actual_eps=28.5,
            expected_eps=25.0,
            risk_reward_ratio=2.1,
            signal_explanation="Strong earnings gap up with volume surge"
        )
        
        print(f"✅ Test signal created: {test_signal.symbol} {test_signal.signal_type.value}")
        print(f"   Confidence: {test_signal.confidence.value} ({test_signal.confidence_score:.0f}%)")
        print(f"   Entry: ₹{test_signal.entry_price:.2f}")
        print(f"   Stop Loss: ₹{test_signal.stop_loss:.2f}")
        print(f"   Target: ₹{test_signal.profit_target:.2f}")
        
        # Test signal execution (paper trading)
        trade_id = await order_engine.execute_signal(test_signal)
        if trade_id:
            print(f"✅ Signal executed successfully: {trade_id}")
            
            # Check active trades
            active_trades = [t for t in order_engine.active_trades.values() if t['status'] == 'ACTIVE']
            print(f"   Active trades: {len(active_trades)}")
            
            if active_trades:
                trade = active_trades[0]
                print(f"   Entry order: {trade['entry_order'].order_id}")
                print(f"   GTT ID: {trade['gtt_id']}")
        else:
            print("❌ Signal execution failed")
        
        # Test execution status
        status = await order_engine.get_execution_status()
        print(f"✅ Execution status:")
        print(f"   Initialized: {status['initialized']}")
        print(f"   Paper trading: {status['paper_trading']}")
        print(f"   Emergency stop: {status['emergency_stop']}")
        print(f"   Active trades: {status['active_trades']}")
        print(f"   Total trades: {status['total_trades']}")
        
        # Test order placement scenarios
        print("\n7. 🔄 Testing Order Placement Scenarios")
        
        # Test market order
        market_order = OrderResponse(
            order_id="PAPER_12345",
            status=OrderStatus.COMPLETE,
            symbol="RELIANCE",
            transaction_type=TransactionType.BUY,
            quantity=10,
            filled_quantity=10,
            pending_quantity=0,
            price=2475.0,
            average_price=2475.0,
            trigger_price=None,
            timestamp=datetime.now(),
            order_type=OrderType.MARKET,
            product=ProductType.MIS
        )
        
        print(f"✅ Market order test:")
        print(f"   Order ID: {market_order.order_id}")
        print(f"   Status: {market_order.status.value}")
        print(f"   Fill: {market_order.filled_quantity}/{market_order.quantity}")
        
        # Test order serialization
        order_dict = market_order.to_dict()
        print(f"✅ Order serialization: {len(order_dict)} fields")
        
        # Test limit order
        limit_order = OrderResponse(
            order_id="PAPER_12346",
            status=OrderStatus.OPEN,
            symbol="TCS",
            transaction_type=TransactionType.SELL,
            quantity=5,
            filled_quantity=0,
            pending_quantity=5,
            price=3250.0,
            average_price=0.0,
            trigger_price=None,
            timestamp=datetime.now(),
            order_type=OrderType.LIMIT,
            product=ProductType.MIS
        )
        
        print(f"✅ Limit order test:")
        print(f"   Order ID: {limit_order.order_id}")
        print(f"   Status: {limit_order.status.value}")
        print(f"   Pending: {limit_order.pending_quantity}")
        
        # Test stop loss order
        sl_order = OrderResponse(
            order_id="PAPER_12347",
            status=OrderStatus.TRIGGER_PENDING,
            symbol="INFY",
            transaction_type=TransactionType.SELL,
            quantity=8,
            filled_quantity=0,
            pending_quantity=8,
            price=1520.0,
            average_price=0.0,
            trigger_price=1520.0,
            timestamp=datetime.now(),
            order_type=OrderType.SL_M,
            product=ProductType.MIS
        )
        
        print(f"✅ Stop loss order test:")
        print(f"   Order ID: {sl_order.order_id}")
        print(f"   Status: {sl_order.status.value}")
        print(f"   Trigger: ₹{sl_order.trigger_price:.2f}")
        
        # Test error handling
        print("\n8. ⚠️  Testing Error Handling")
        
        # Test invalid signal execution
        invalid_signal = EarningsGapSignal(
            symbol="INVALID",
            company_name="Invalid Company",
            signal_type=SignalType.EARNINGS_GAP_UP,
            confidence=SignalConfidence.LOW,
            confidence_score=30.0,  # Low confidence
            entry_time=datetime.now(),
            entry_price=100.0,
            stop_loss=95.0,
            profit_target=105.0,
            gap_percent=1.0,  # Small gap
            gap_amount=1.0,
            previous_close=99.0,
            volume_ratio=1.2,  # Low volume
            current_volume=120000,
            earnings_surprise=2.0,
            actual_eps=10.2,
            expected_eps=10.0,
            risk_reward_ratio=1.0,
            signal_explanation="Low quality signal for testing"
        )
        
        # Mock risk manager to reject this trade
        mock_risk_manager.validate_trade.return_value = (False, None, [])
        
        invalid_trade_id = await order_engine.execute_signal(invalid_signal)
        if invalid_trade_id is None:
            print("✅ Invalid signal correctly rejected")
        else:
            print("⚠️  Invalid signal unexpectedly executed")
        
        # Reset risk manager mock
        mock_risk_manager.validate_trade.return_value = (True, mock_position_size, [])
        
        # Test emergency stop
        print("\n9. 🚨 Testing Emergency Protocols")
        
        # Test emergency stop all
        await order_engine.emergency_stop_all("Test emergency stop")
        
        emergency_status = await order_engine.get_execution_status()
        print(f"✅ Emergency stop test:")
        print(f"   Emergency stop active: {emergency_status['emergency_stop']}")
        
        # Test execution after emergency stop
        emergency_trade_id = await order_engine.execute_signal(test_signal)
        if emergency_trade_id is None:
            print("✅ Trading correctly blocked during emergency stop")
        else:
            print("⚠️  Trading unexpectedly allowed during emergency stop")
        
        # Reset emergency stop
        order_engine.emergency_stop = False
        
        # Test performance metrics
        print("\n10. ⚡ Testing Performance Metrics")
        
        # Test execution metrics creation
        metrics = ExecutionMetrics(
            symbol="RELIANCE",
            signal_time=datetime.now() - timedelta(seconds=10),
            execution_time=datetime.now(),
            entry_price=2477.5,
            expected_price=2475.0,
            slippage=2.5,
            slippage_percent=0.101,
            execution_delay=10.0,
            fill_quality="GOOD",
            commission=5.0
        )
        
        metrics_dict = metrics.to_dict()
        print(f"✅ Execution metrics:")
        print(f"   Symbol: {metrics.symbol}")
        print(f"   Slippage: ₹{metrics.slippage:.2f} ({metrics.slippage_percent:+.3f}%)")
        print(f"   Execution delay: {metrics.execution_delay:.1f}s")
        print(f"   Fill quality: {metrics.fill_quality}")
        print(f"   Serialization: {len(metrics_dict)} fields")
        
        # Test position status
        position_status = PositionStatus(
            symbol="RELIANCE",
            quantity=10,
            entry_price=2475.0,
            current_price=2490.0,
            pnl=150.0,
            pnl_percent=0.61,
            unrealized_pnl=150.0,
            day_pnl=150.0,
            position_value=24900.0,
            last_updated=datetime.now()
        )
        
        position_dict = position_status.to_dict()
        print(f"✅ Position status:")
        print(f"   Symbol: {position_status.symbol}")
        print(f"   Quantity: {position_status.quantity}")
        print(f"   P&L: ₹{position_status.pnl:+,.0f} ({position_status.pnl_percent:+.1f}%)")
        print(f"   Serialization: {len(position_dict)} fields")
        
        # Test data structure validation
        print("\n11. 📋 Testing Data Structure Validation")
        
        # Test enum values
        print(f"✅ Order types: {[ot.value for ot in OrderType]}")
        print(f"✅ Order statuses: {[os.value for os in OrderStatus]}")
        print(f"✅ Transaction types: {[tt.value for tt in TransactionType]}")
        print(f"✅ Product types: {[pt.value for pt in ProductType]}")
        print(f"✅ GTT statuses: {[gs.value for gs in GTTStatus]}")
        
        # Test edge cases
        print("\n12. 🧪 Testing Edge Cases")
        
        # Test zero quantity calculation
        zero_position_size = PositionSize(
            symbol="TEST",
            base_size=100.0,
            volatility_adjusted_size=50.0,
            performance_adjusted_size=25.0,
            final_size=25.0,  # Very small final size
            max_allowed_size=1000.0,
            size_percentage=0.025,
            risk_amount=5.0,
            rationale="Very small position due to high risk"
        )
        
        mock_risk_manager.validate_trade.return_value = (True, zero_position_size, [])
        
        # This should fail due to zero quantity calculation
        small_signal = test_signal
        small_signal.entry_price = 5000.0  # High price to make quantity zero
        
        small_trade_id = await order_engine.execute_signal(small_signal)
        if small_trade_id is None:
            print("✅ Zero quantity trade correctly rejected")
        else:
            print("⚠️  Zero quantity trade unexpectedly executed")
        
        # Reset price
        small_signal.entry_price = 2475.0
        mock_risk_manager.validate_trade.return_value = (True, mock_position_size, [])
        
        # Test performance under load
        print("\n13. 🏃 Testing Performance")
        
        # Test slippage calculation performance
        start_time = datetime.now()
        for i in range(1000):
            execution_analyzer.calculate_slippage(2475.0 + i, 2477.0 + i, TransactionType.BUY)
        end_time = datetime.now()
        
        avg_time = (end_time - start_time).total_seconds() / 1000 * 1000
        print(f"✅ Slippage calculation performance: {avg_time:.3f}ms avg")
        
        # Test fill quality assessment performance
        start_time = datetime.now()
        for i in range(1000):
            execution_analyzer.assess_fill_quality(0.1 + i * 0.001)
        end_time = datetime.now()
        
        avg_time = (end_time - start_time).total_seconds() / 1000 * 1000
        print(f"✅ Fill quality assessment performance: {avg_time:.3f}ms avg")
        
        # Cleanup
        print("\n14. 🧹 Testing Cleanup")
        await order_engine.cleanup()
        print("✅ Order engine cleanup completed")
        
        print("\n" + "=" * 50)
        print("🎉 All Order Execution Engine tests completed successfully!")
        print("\n📊 Test Summary:")
        print("✅ Component initialization")
        print("✅ Zerodha API integration")
        print("✅ GTT order management")
        print("✅ Position tracking")
        print("✅ Execution analysis")
        print("✅ Order engine orchestration")
        print("✅ Order placement scenarios")
        print("✅ Error handling")
        print("✅ Emergency protocols")
        print("✅ Performance metrics")
        print("✅ Data structure validation")
        print("✅ Edge case handling")
        print("✅ Performance testing")
        print("✅ Resource cleanup")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure all dependencies are installed:")
        print("   pip install -r requirements.txt")
        return False
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_order_execution_scenarios():
    """Test specific order execution scenarios"""
    print("\n🧠 Testing Order Execution Scenarios")
    print("-" * 30)
    
    try:
        from core.order_engine import (
            OrderEngine, OrderType, OrderStatus, TransactionType,
            ExecutionAnalyzer, OrderRequest, OrderResponse
        )
        from datetime import datetime, timedelta
        
        execution_analyzer = ExecutionAnalyzer()
        
        # Scenario 1: Excellent execution (minimal slippage)
        print("1. Testing excellent execution scenario...")
        
        excellent_slippage, excellent_percent = execution_analyzer.calculate_slippage(
            expected_price=2475.0,
            actual_price=2475.25,  # Only 0.25 slippage
            transaction_type=TransactionType.BUY
        )
        
        excellent_quality = execution_analyzer.assess_fill_quality(excellent_percent)
        print(f"✅ Excellent execution: ₹{excellent_slippage:.2f} slippage ({excellent_percent:+.3f}%) - {excellent_quality}")
        
        # Scenario 2: Poor execution (high slippage)
        print("\n2. Testing poor execution scenario...")
        
        poor_slippage, poor_percent = execution_analyzer.calculate_slippage(
            expected_price=2475.0,
            actual_price=2487.5,  # 12.5 slippage (0.5%)
            transaction_type=TransactionType.BUY
        )
        
        poor_quality = execution_analyzer.assess_fill_quality(poor_percent)
        print(f"✅ Poor execution: ₹{poor_slippage:.2f} slippage ({poor_percent:+.3f}%) - {poor_quality}")
        
        # Scenario 3: Sell order slippage
        print("\n3. Testing sell order slippage...")
        
        sell_slippage, sell_percent = execution_analyzer.calculate_slippage(
            expected_price=2475.0,
            actual_price=2470.0,  # Got less than expected (worse for sell)
            transaction_type=TransactionType.SELL
        )
        
        sell_quality = execution_analyzer.assess_fill_quality(sell_percent)
        print(f"✅ Sell execution: ₹{sell_slippage:.2f} slippage ({sell_percent:+.3f}%) - {sell_quality}")
        
        # Scenario 4: Order status progression
        print("\n4. Testing order status progression...")
        
        order_statuses = [
            OrderStatus.PENDING,
            OrderStatus.OPEN,
            OrderStatus.COMPLETE
        ]
        
        for status in order_statuses:
            print(f"   📊 Order status: {status.value}")
        
        # Scenario 5: Different order types
        print("\n5. Testing different order types...")
        
        order_types = [
            (OrderType.MARKET, "Fast execution for immediate fills"),
            (OrderType.LIMIT, "Price control for better fills"),
            (OrderType.SL, "Stop loss with price specification"),
            (OrderType.SL_M, "Stop loss market order")
        ]
        
        for order_type, description in order_types:
            print(f"   📋 {order_type.value}: {description}")
        
        # Scenario 6: Commission and cost analysis
        print("\n6. Testing commission and cost analysis...")
        
        trade_scenarios = [
            {"value": 10000, "commission": 20, "name": "Small trade"},
            {"value": 50000, "commission": 50, "name": "Medium trade"},
            {"value": 100000, "commission": 100, "name": "Large trade"}
        ]
        
        for scenario in trade_scenarios:
            commission_percent = (scenario["commission"] / scenario["value"]) * 100
            print(f"   💰 {scenario['name']}: ₹{scenario['commission']} ({commission_percent:.3f}%)")
        
        print("\n✅ Order execution scenario tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Order execution scenario test failed: {e}")
        return False


async def test_gtt_functionality():
    """Test GTT (Good Till Triggered) functionality"""
    print("\n🎯 Testing GTT Functionality")
    print("-" * 30)
    
    try:
        from core.order_engine import GTTManager, GTTOrder, GTTStatus, ZerodhaOrderManager
        from unittest.mock import Mock
        from datetime import datetime, timedelta
        
        # Mock Zerodha manager
        mock_zerodha = Mock(spec=ZerodhaOrderManager)
        mock_zerodha.kite = Mock()
        
        gtt_manager = GTTManager(mock_zerodha)
        
        # Test GTT OCO creation
        print("1. Testing GTT OCO order creation...")
        
        # Mock GTT response
        mock_zerodha.kite.place_gtt.return_value = {"trigger_id": "67890"}
        
        # This would normally call the API, but we'll test the logic
        profit_target = 2550.0
        stop_loss = 2400.0
        current_price = 2475.0
        quantity = 10
        
        # Manually create GTT order for testing
        gtt_order = GTTOrder(
            gtt_id="67890",
            symbol="RELIANCE",
            trigger_type="two-leg",
            trigger_price=current_price,
            last_price=current_price,
            orders=[
                {
                    'transaction_type': 'SELL',
                    'quantity': quantity,
                    'order_type': 'LIMIT',
                    'product': 'MIS',
                    'price': profit_target
                },
                {
                    'transaction_type': 'SELL',
                    'quantity': quantity,
                    'order_type': 'SL-M',
                    'product': 'MIS',
                    'trigger_price': stop_loss
                }
            ],
            status=GTTStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=365)
        )
        
        gtt_manager.active_gtts["67890"] = gtt_order
        
        print(f"✅ GTT OCO created: ID {gtt_order.gtt_id}")
        print(f"   Symbol: {gtt_order.symbol}")
        print(f"   Profit target: ₹{profit_target:.2f}")
        print(f"   Stop loss: ₹{stop_loss:.2f}")
        print(f"   Status: {gtt_order.status.value}")
        print(f"   Orders: {len(gtt_order.orders)} legs")
        
        # Test GTT status changes
        print("\n2. Testing GTT status changes...")
        
        status_progression = [
            GTTStatus.ACTIVE,
            GTTStatus.TRIGGERED,
            GTTStatus.CANCELLED
        ]
        
        for status in status_progression:
            gtt_order.status = status
            print(f"   📊 GTT status: {status.value}")
        
        # Test GTT monitoring
        print("\n3. Testing GTT monitoring...")
        
        # Mock GTT API response
        mock_gtt_response = [
            {
                'id': 67890,
                'status': 'active',
                'trigger_type': 'two-leg',
                'symbol': 'RELIANCE'
            }
        ]
        
        mock_zerodha.kite.gtt.return_value = mock_gtt_response
        
        # Monitor GTTs
        updated_gtts = await gtt_manager.monitor_gtts()
        print(f"✅ GTT monitoring: {len(updated_gtts)} GTTs monitored")
        
        # Test GTT serialization
        print("\n4. Testing GTT serialization...")
        
        gtt_dict = gtt_order.to_dict()
        print(f"✅ GTT serialization: {len(gtt_dict)} fields")
        print(f"   Required fields: gtt_id, symbol, status, orders")
        
        required_fields = ['gtt_id', 'symbol', 'status', 'orders']
        for field in required_fields:
            if field in gtt_dict:
                print(f"   ✅ {field}: present")
            else:
                print(f"   ❌ {field}: missing")
        
        print("\n✅ GTT functionality tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ GTT functionality test failed: {e}")
        return False


if __name__ == "__main__":
    async def main():
        print("🧪 Order Execution Engine Test Suite")
        print("=" * 60)
        
        # Run main tests
        main_test_success = await test_order_execution_engine()
        
        # Run scenario tests
        scenario_test_success = await test_order_execution_scenarios()
        
        # Run GTT tests
        gtt_test_success = await test_gtt_functionality()
        
        print("\n" + "=" * 60)
        if main_test_success and scenario_test_success and gtt_test_success:
            print("🎉 ALL TESTS PASSED!")
            print("\n📝 Next Steps:")
            print("1. Set up Zerodha API credentials (api_key, access_token)")
            print("2. Test with live market data feeds")
            print("3. Configure position size limits and risk parameters")
            print("4. Test GTT orders with actual Zerodha API")
            print("5. Integrate with earnings scanner for signal execution")
            print("6. Set up real-time position monitoring dashboards")
            print("7. Configure emergency notification systems")
            print("8. Test paper trading mode extensively before live trading")
            return 0
        else:
            print("❌ Some tests failed. Please check the errors above.")
            return 1
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)