#!/usr/bin/env python3
"""
Example usage of the Order Execution Engine
This demonstrates how to integrate the order engine into your trading application
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def example_basic_order_execution():
    """Example: Basic order execution workflow"""
    print("📊 Example 1: Basic Order Execution")
    print("-" * 40)
    
    from core.order_engine import get_order_engine
    from core.risk_manager import get_risk_manager
    from core.market_data import market_data_manager
    from core.earnings_scanner import EarningsGapSignal, SignalType, SignalConfidence
    
    # Initialize components
    await market_data_manager.initialize()
    risk_manager = await get_risk_manager()
    
    # Get order engine instance (paper trading mode)
    order_engine = await get_order_engine(
        api_key="demo_api_key",
        access_token="demo_access_token",
        risk_manager=risk_manager,
        market_data_manager=market_data_manager,
        paper_trading=True
    )
    
    # Create a sample earnings gap signal
    signal = EarningsGapSignal(
        symbol="RELIANCE",
        company_name="Reliance Industries Limited",
        signal_type=SignalType.EARNINGS_GAP_UP,
        confidence=SignalConfidence.HIGH,
        confidence_score=85.0,
        entry_time=datetime.now(),
        entry_price=2475.0,
        stop_loss=2400.0,
        profit_target=2550.0,
        gap_percent=6.2,
        gap_amount=145.0,
        previous_close=2330.0,
        volume_ratio=4.2,
        current_volume=4200000,
        earnings_surprise=18.5,
        actual_eps=32.5,
        expected_eps=27.5,
        risk_reward_ratio=2.0,
        signal_explanation="Strong earnings beat with significant gap up and volume surge"
    )
    
    print(f"🎯 Executing signal for {signal.symbol}")
    print(f"   Type: {signal.signal_type.value}")
    print(f"   Confidence: {signal.confidence.value} ({signal.confidence_score:.0f}%)")
    print(f"   Entry: ₹{signal.entry_price:.2f}")
    print(f"   Stop Loss: ₹{signal.stop_loss:.2f}")
    print(f"   Target: ₹{signal.profit_target:.2f}")
    
    # Execute the signal
    trade_id = await order_engine.execute_signal(signal)
    
    if trade_id:
        print(f"✅ Trade executed successfully: {trade_id}")
        
        # Get execution status
        status = await order_engine.get_execution_status()
        print(f"   Active trades: {status['active_trades']}")
        print(f"   Paper trading: {status['paper_trading']}")
    else:
        print("❌ Trade execution failed")
    
    await order_engine.cleanup()


async def example_manual_order_placement():
    """Example: Manual order placement and monitoring"""
    print("\n📋 Example 2: Manual Order Placement")
    print("-" * 40)
    
    from core.order_engine import (
        ZerodhaOrderManager, OrderRequest, OrderType, 
        TransactionType, ProductType
    )
    
    # Create Zerodha order manager (paper trading simulation)
    zerodha_manager = ZerodhaOrderManager("demo_api", "demo_token")
    
    # Create order request
    order_request = OrderRequest(
        symbol="TCS",
        transaction_type=TransactionType.BUY,
        quantity=5,
        order_type=OrderType.MARKET,
        product=ProductType.MIS,
        tag="MANUAL_ORDER_DEMO"
    )
    
    print(f"📦 Order Request:")
    print(f"   Symbol: {order_request.symbol}")
    print(f"   Type: {order_request.transaction_type.value} {order_request.order_type.value}")
    print(f"   Quantity: {order_request.quantity}")
    print(f"   Product: {order_request.product.value}")
    
    # In real implementation, this would place actual order
    print("   🔄 Simulating order placement...")
    print("   ✅ Order would be placed via Zerodha API")
    
    # Simulate order response
    from core.order_engine import OrderResponse, OrderStatus
    
    simulated_response = OrderResponse(
        order_id="DEMO_12345",
        status=OrderStatus.COMPLETE,
        symbol=order_request.symbol,
        transaction_type=order_request.transaction_type,
        quantity=order_request.quantity,
        filled_quantity=order_request.quantity,
        pending_quantity=0,
        price=3200.0,
        average_price=3202.5,
        trigger_price=None,
        timestamp=datetime.now(),
        order_type=order_request.order_type,
        product=order_request.product
    )
    
    print(f"📥 Order Response:")
    print(f"   Order ID: {simulated_response.order_id}")
    print(f"   Status: {simulated_response.status.value}")
    print(f"   Average Price: ₹{simulated_response.average_price:.2f}")
    print(f"   Fill: {simulated_response.filled_quantity}/{simulated_response.quantity}")


async def example_gtt_oco_orders():
    """Example: GTT OCO (One Cancels Other) order placement"""
    print("\n🎯 Example 3: GTT OCO Orders")
    print("-" * 40)
    
    from core.order_engine import GTTManager, ZerodhaOrderManager, GTTOrder, GTTStatus
    
    # Create managers
    zerodha_manager = ZerodhaOrderManager("demo_api", "demo_token")
    gtt_manager = GTTManager(zerodha_manager)
    
    # GTT OCO parameters
    symbol = "HDFCBANK"
    quantity = 10
    current_price = 1600.0
    profit_target = 1680.0  # 5% profit
    stop_loss = 1520.0      # 5% loss
    
    print(f"🎯 GTT OCO Setup:")
    print(f"   Symbol: {symbol}")
    print(f"   Quantity: {quantity} shares")
    print(f"   Current Price: ₹{current_price:.2f}")
    print(f"   Profit Target: ₹{profit_target:.2f} (+{((profit_target/current_price)-1)*100:.1f}%)")
    print(f"   Stop Loss: ₹{stop_loss:.2f} ({((stop_loss/current_price)-1)*100:.1f}%)")
    
    # Simulate GTT placement
    print("   🔄 Simulating GTT OCO placement...")
    
    # Create simulated GTT order
    gtt_order = GTTOrder(
        gtt_id="GTT_DEMO_789",
        symbol=symbol,
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
    
    gtt_manager.active_gtts[gtt_order.gtt_id] = gtt_order
    
    print(f"   ✅ GTT OCO placed: {gtt_order.gtt_id}")
    print(f"   📊 Status: {gtt_order.status.value}")
    print(f"   📅 Expires: {gtt_order.expires_at.strftime('%Y-%m-%d')}")
    print(f"   🔗 Orders: {len(gtt_order.orders)} legs configured")


async def example_position_monitoring():
    """Example: Real-time position monitoring"""
    print("\n👁️ Example 4: Position Monitoring")
    print("-" * 40)
    
    from core.order_engine import PositionTracker, ZerodhaOrderManager, PositionStatus
    from core.market_data import market_data_manager
    
    # Initialize components
    zerodha_manager = ZerodhaOrderManager("demo_api", "demo_token")
    position_tracker = PositionTracker(zerodha_manager, market_data_manager)
    
    # Simulate position data
    positions = {
        "RELIANCE": PositionStatus(
            symbol="RELIANCE",
            quantity=10,
            entry_price=2475.0,
            current_price=2520.0,
            pnl=450.0,
            pnl_percent=1.82,
            unrealized_pnl=450.0,
            day_pnl=450.0,
            position_value=25200.0,
            last_updated=datetime.now()
        ),
        "TCS": PositionStatus(
            symbol="TCS",
            quantity=5,
            entry_price=3200.0,
            current_price=3150.0,
            pnl=-250.0,
            pnl_percent=-1.56,
            unrealized_pnl=-250.0,
            day_pnl=-250.0,
            position_value=15750.0,
            last_updated=datetime.now()
        )
    }
    
    print("📊 Current Positions:")
    
    total_pnl = 0
    total_value = 0
    
    for symbol, position in positions.items():
        pnl_emoji = "📈" if position.pnl > 0 else "📉"
        print(f"\n   {pnl_emoji} {symbol}:")
        print(f"      Quantity: {position.quantity} shares")
        print(f"      Entry: ₹{position.entry_price:.2f}")
        print(f"      Current: ₹{position.current_price:.2f}")
        print(f"      P&L: ₹{position.pnl:+,.0f} ({position.pnl_percent:+.1f}%)")
        print(f"      Value: ₹{position.position_value:,.0f}")
        print(f"      Updated: {position.last_updated.strftime('%H:%M:%S')}")
        
        total_pnl += position.pnl
        total_value += position.position_value
    
    print(f"\n📊 Portfolio Summary:")
    print(f"   Total Value: ₹{total_value:,.0f}")
    print(f"   Total P&L: ₹{total_pnl:+,.0f}")
    print(f"   Overall Return: {(total_pnl/total_value)*100:+.2f}%")


async def example_execution_analysis():
    """Example: Execution performance analysis"""
    print("\n📈 Example 5: Execution Analysis")
    print("-" * 40)
    
    from core.order_engine import ExecutionAnalyzer, ExecutionMetrics, TransactionType
    
    execution_analyzer = ExecutionAnalyzer()
    
    # Simulate execution records
    sample_executions = [
        {
            "symbol": "RELIANCE",
            "signal_time": datetime.now() - timedelta(seconds=30),
            "execution_time": datetime.now() - timedelta(seconds=28),
            "entry_price": 2477.5,
            "expected_price": 2475.0,
            "commission": 15.0
        },
        {
            "symbol": "TCS",
            "signal_time": datetime.now() - timedelta(seconds=45),
            "execution_time": datetime.now() - timedelta(seconds=42),
            "entry_price": 3205.0,
            "expected_price": 3200.0,
            "commission": 18.0
        },
        {
            "symbol": "INFY",
            "signal_time": datetime.now() - timedelta(seconds=60),
            "execution_time": datetime.now() - timedelta(seconds=55),
            "entry_price": 1548.0,
            "expected_price": 1550.0,
            "commission": 12.0
        }
    ]
    
    print("📋 Recording Executions:")
    
    for execution in sample_executions:
        execution_analyzer.record_execution(**execution)
        
        # Calculate metrics manually for display
        slippage, slippage_percent = execution_analyzer.calculate_slippage(
            execution["expected_price"],
            execution["entry_price"],
            TransactionType.BUY
        )
        
        fill_quality = execution_analyzer.assess_fill_quality(slippage_percent)
        execution_delay = (execution["execution_time"] - execution["signal_time"]).total_seconds()
        
        print(f"\n   📊 {execution['symbol']}:")
        print(f"      Expected: ₹{execution['expected_price']:.2f}")
        print(f"      Actual: ₹{execution['entry_price']:.2f}")
        print(f"      Slippage: ₹{slippage:.2f} ({slippage_percent:+.3f}%)")
        print(f"      Fill Quality: {fill_quality}")
        print(f"      Execution Delay: {execution_delay:.1f}s")
        print(f"      Commission: ₹{execution['commission']:.2f}")
    
    # Get performance summary
    summary = execution_analyzer.get_performance_summary()
    
    print(f"\n📊 Execution Performance Summary:")
    print(f"   Total Executions: {summary['total_executions']}")
    print(f"   Average Slippage: {summary['avg_slippage_percent']:+.3f}%")
    print(f"   Max Slippage: {summary['max_slippage_percent']:+.3f}%")
    print(f"   Min Slippage: {summary['min_slippage_percent']:+.3f}%")
    print(f"   Average Delay: {summary['avg_execution_delay']:.1f}s")
    
    print(f"\n📈 Fill Quality Distribution:")
    for quality, count in summary['fill_quality_distribution'].items():
        if count > 0:
            percentage = (count / summary['total_executions']) * 100
            print(f"   {quality}: {count} ({percentage:.0f}%)")


async def example_emergency_protocols():
    """Example: Emergency stop and risk management"""
    print("\n🚨 Example 6: Emergency Protocols")
    print("-" * 40)
    
    from core.order_engine import get_order_engine
    from core.risk_manager import get_risk_manager
    from core.market_data import market_data_manager
    
    # Initialize components
    await market_data_manager.initialize()
    risk_manager = await get_risk_manager()
    
    order_engine = await get_order_engine(
        api_key="demo_api_key",
        access_token="demo_access_token",
        risk_manager=risk_manager,
        market_data_manager=market_data_manager,
        paper_trading=True
    )
    
    # Simulate normal operation
    print("🔄 Normal Trading Status:")
    status = await order_engine.get_execution_status()
    print(f"   Emergency Stop: {status['emergency_stop']}")
    print(f"   Active Trades: {status['active_trades']}")
    print(f"   Paper Trading: {status['paper_trading']}")
    
    # Simulate emergency scenarios
    emergency_scenarios = [
        "Market crash detected",
        "Network connectivity issues",
        "Risk limits breached",
        "Manual intervention required"
    ]
    
    for scenario in emergency_scenarios:
        print(f"\n⚠️  Emergency Scenario: {scenario}")
        print("   📋 Actions taken:")
        print("      1. 🛑 Halt all new trading")
        print("      2. 📞 Cancel all pending GTT orders") 
        print("      3. 🚪 Exit all open positions at market")
        print("      4. 📢 Send emergency notifications")
        print("      5. 📊 Generate incident report")
        break  # Only show first scenario
    
    # Trigger emergency stop
    print(f"\n🚨 Triggering Emergency Stop...")
    await order_engine.emergency_stop_all("Demo emergency stop")
    
    # Check status after emergency stop
    emergency_status = await order_engine.get_execution_status()
    print(f"✅ Emergency Stop Status:")
    print(f"   Emergency Stop Active: {emergency_status['emergency_stop']}")
    print(f"   All Trading Halted: {'YES' if emergency_status['emergency_stop'] else 'NO'}")
    
    await order_engine.cleanup()


async def example_paper_vs_live_trading():
    """Example: Paper trading vs live trading modes"""
    print("\n🧪 Example 7: Paper vs Live Trading")
    print("-" * 40)
    
    # Paper Trading Mode
    print("📋 Paper Trading Mode:")
    print("   ✅ Safe for testing and development")
    print("   ✅ No real money at risk")
    print("   ✅ Instant order fills")
    print("   ✅ No API rate limits")
    print("   ✅ Perfect for backtesting")
    print("   📊 Use for: Strategy testing, development, learning")
    
    print("\n💰 Live Trading Mode:")
    print("   ⚠️  Real money and positions")
    print("   ⚠️  API rate limits apply (3000/day, 200/min)")
    print("   ⚠️  Market slippage and delays")
    print("   ⚠️  Commission charges")
    print("   ⚠️  Requires valid Zerodha credentials")
    print("   🎯 Use for: Live trading with real capital")
    
    print("\n🔄 Mode Selection:")
    print("   # Paper trading (default)")
    print("   order_engine = OrderEngine(..., paper_trading=True)")
    print("")
    print("   # Live trading (production)")
    print("   order_engine = OrderEngine(..., paper_trading=False)")
    
    print("\n📊 Feature Comparison:")
    features = [
        ("Order Placement", "Simulated", "Real API"),
        ("Position Tracking", "Mock Data", "Live Positions"),
        ("GTT Orders", "Simulated", "Real GTT"),
        ("Slippage", "Minimal", "Market Reality"),
        ("Commission", "Estimated", "Actual Charges"),
        ("Risk", "Zero", "Real Capital")
    ]
    
    print(f"   {'Feature':<20} {'Paper':<12} {'Live'}")
    print("   " + "-" * 45)
    for feature, paper, live in features:
        print(f"   {feature:<20} {paper:<12} {live}")


async def example_integration_workflow():
    """Example: Complete integration workflow"""
    print("\n🔄 Example 8: Complete Integration Workflow")
    print("-" * 40)
    
    print("🚀 Order Engine Integration Steps:")
    
    steps = [
        "1. 🔧 Initialize Dependencies",
        "2. 📊 Set up Market Data Manager", 
        "3. 🛡️  Configure Risk Manager",
        "4. 🎯 Initialize Order Engine",
        "5. 📈 Connect Earnings Scanner",
        "6. 🔄 Start Real-time Monitoring",
        "7. 🎯 Process Trading Signals",
        "8. 📊 Monitor Positions",
        "9. ⚠️  Handle Emergencies",
        "10. 📈 Analyze Performance"
    ]
    
    for step in steps:
        print(f"   {step}")
    
    print(f"\n📋 Code Integration Example:")
    print("""
    # 1. Initialize components
    market_data_manager = await MarketDataManager.initialize()
    risk_manager = await get_risk_manager()
    scanner = await get_earnings_gap_scanner()
    
    # 2. Create order engine
    order_engine = await get_order_engine(
        api_key=ZERODHA_API_KEY,
        access_token=ZERODHA_ACCESS_TOKEN,
        risk_manager=risk_manager,
        market_data_manager=market_data_manager,
        paper_trading=True  # Start with paper trading
    )
    
    # 3. Trading loop
    while trading_active:
        # Scan for signals
        signals = await scanner.scan_for_signals()
        
        # Execute valid signals
        for signal in signals:
            trade_id = await order_engine.execute_signal(signal)
            if trade_id:
                logger.info(f"Trade executed: {trade_id}")
        
        # Monitor positions
        positions = await order_engine.position_tracker.get_all_positions()
        for symbol, position in positions.items():
            if abs(position.pnl_percent) > 5:  # 5% move
                logger.info(f"{symbol} significant move: {position.pnl_percent:+.1f}%")
        
        await asyncio.sleep(60)  # Check every minute
    """)
    
    print(f"\n⚠️  Important Considerations:")
    considerations = [
        "Always start with paper trading mode",
        "Set appropriate position size limits",
        "Configure emergency stop protocols",
        "Monitor API rate limits carefully",
        "Test all scenarios before live trading",
        "Keep detailed logs of all activities",
        "Have backup plans for system failures",
        "Regular performance analysis and optimization"
    ]
    
    for consideration in considerations:
        print(f"   • {consideration}")


async def main():
    """Run all examples"""
    print("🎯 Order Execution Engine - Usage Examples")
    print("=" * 60)
    
    examples = [
        example_basic_order_execution,
        example_manual_order_placement,
        example_gtt_oco_orders,
        example_position_monitoring,
        example_execution_analysis,
        example_emergency_protocols,
        example_paper_vs_live_trading,
        example_integration_workflow
    ]
    
    for i, example_func in enumerate(examples, 1):
        try:
            await example_func()
            if i < len(examples):
                print("\n" + "="*60)
        except Exception as e:
            print(f"❌ Example {i} failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("🎉 All examples completed!")
    print("\n💡 Order Engine Best Practices:")
    print("1. Always start with paper trading mode")
    print("2. Validate all signals through risk manager")
    print("3. Use GTT OCO orders for automatic exits")
    print("4. Monitor positions in real-time")
    print("5. Set up emergency stop protocols")
    print("6. Track execution performance metrics")
    print("7. Respect API rate limits (3000/day, 200/min)")
    print("8. Keep detailed logs of all trading activities")
    print("9. Test thoroughly before live trading")
    print("10. Have backup plans for system failures")


if __name__ == "__main__":
    asyncio.run(main())