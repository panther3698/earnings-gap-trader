#!/usr/bin/env python3
"""
Example usage of the Telegram Bot Service
This demonstrates how to integrate the Telegram bot into your trading application
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def example_basic_telegram_setup():
    """Example: Basic Telegram bot setup and initialization"""
    print("🤖 Example 1: Basic Telegram Bot Setup")
    print("-" * 40)
    
    from core.telegram_service import TelegramBot, TelegramConfig, TradingMode
    from core.order_engine import get_order_engine
    from core.risk_manager import get_risk_manager
    from core.market_data import market_data_manager
    
    print("📋 Setting up Telegram bot configuration...")
    
    # Create Telegram configuration
    telegram_config = TelegramConfig(
        bot_token="YOUR_BOT_TOKEN_HERE",  # Get from BotFather
        chat_ids=[123456789, 987654321],  # Your authorized chat IDs
        webhook_url=None,  # Use polling for simplicity
        approval_timeout=300,  # 5 minutes
        max_retries=3,
        rate_limit_delay=1.0
    )
    
    print(f"✅ Configuration created:")
    print(f"   Authorized chats: {len(telegram_config.chat_ids)}")
    print(f"   Approval timeout: {telegram_config.approval_timeout}s")
    print(f"   Max retries: {telegram_config.max_retries}")
    
    # Initialize dependencies
    print("\n🔧 Initializing trading components...")
    
    await market_data_manager.initialize()
    risk_manager = await get_risk_manager()
    order_engine = await get_order_engine(
        api_key="demo_api_key",
        access_token="demo_access_token",
        risk_manager=risk_manager,
        market_data_manager=market_data_manager,
        paper_trading=True
    )
    
    print("✅ Trading components initialized")
    
    # Create Telegram bot
    telegram_bot = TelegramBot(telegram_config, order_engine, risk_manager)
    
    # Initialize bot
    bot_initialized = await telegram_bot.initialize()
    print(f"✅ Telegram bot initialized: {bot_initialized}")
    
    # Set initial trading mode
    telegram_bot.set_trading_mode(TradingMode.MANUAL)
    current_mode = telegram_bot.get_trading_mode()
    print(f"✅ Trading mode set to: {current_mode.value}")
    
    # Get bot status
    status = await telegram_bot.get_status()
    print(f"\n📊 Bot Status:")
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    await telegram_bot.cleanup()
    await order_engine.cleanup()


async def example_signal_approval_workflow():
    """Example: Interactive signal approval workflow"""
    print("\n🎯 Example 2: Signal Approval Workflow")
    print("-" * 40)
    
    from core.telegram_service import TelegramBot, TelegramConfig, TradingMode
    from core.earnings_scanner import EarningsGapSignal, SignalType, SignalConfidence
    from unittest.mock import Mock, AsyncMock
    
    # Mock dependencies for demo
    mock_order_engine = Mock()
    mock_order_engine.execute_signal = AsyncMock(return_value="TRADE_12345")
    mock_risk_manager = Mock()
    
    # Create bot in manual mode
    config = TelegramConfig(
        bot_token="demo_token",
        chat_ids=[123456789]
    )
    
    bot = TelegramBot(config, mock_order_engine, mock_risk_manager)
    bot.set_trading_mode(TradingMode.MANUAL)
    
    print("🎯 Creating sample earnings gap signal...")
    
    # Create a sample signal
    signal = EarningsGapSignal(
        symbol="RELIANCE",
        company_name="Reliance Industries Limited",
        signal_type=SignalType.EARNINGS_GAP_UP,
        confidence=SignalConfidence.HIGH,
        confidence_score=88.0,
        entry_time=datetime.now(),
        entry_price=2475.0,
        stop_loss=2400.0,
        profit_target=2575.0,
        gap_percent=6.8,
        gap_amount=157.0,
        previous_close=2318.0,
        volume_ratio=4.5,
        current_volume=4500000,
        earnings_surprise=22.0,
        actual_eps=32.0,
        expected_eps=26.2,
        risk_reward_ratio=2.1,
        signal_explanation="Strong earnings beat with significant gap up and volume surge"
    )
    
    print(f"✅ Signal created: {signal.symbol}")
    print(f"   Type: {signal.signal_type.value}")
    print(f"   Confidence: {signal.confidence.value} ({signal.confidence_score:.0f}%)")
    print(f"   Entry: ₹{signal.entry_price:.2f}")
    print(f"   Target: ₹{signal.profit_target:.2f}")
    print(f"   Stop: ₹{signal.stop_loss:.2f}")
    
    print(f"\n📱 Signal Approval Workflow:")
    print(f"   1. 🎯 Signal detected and validated")
    print(f"   2. 📨 Telegram notification sent to authorized users")
    print(f"   3. ⌨️  Interactive buttons appear: [Approve] [Reject] [Modify] [Details]")
    print(f"   4. ⏱️  5-minute timeout for user response")
    print(f"   5. ✅ On approval: Execute trade automatically")
    print(f"   6. ❌ On rejection: Log reason and skip signal")
    print(f"   7. 📊 Real-time trade notifications")
    
    # Simulate approval workflow
    print(f"\n🔄 Simulating approval workflow...")
    result = await bot.process_signal(signal)
    print(f"✅ Signal processing result: {'Sent for approval' if result else 'Processed automatically'}")


async def example_trading_mode_management():
    """Example: Trading mode management and controls"""
    print("\n🎛️  Example 3: Trading Mode Management")
    print("-" * 40)
    
    from core.telegram_service import TelegramBot, TelegramConfig, TradingMode
    from unittest.mock import Mock
    
    # Mock dependencies
    mock_order_engine = Mock()
    mock_risk_manager = Mock()
    
    config = TelegramConfig(
        bot_token="demo_token",
        chat_ids=[123456789]
    )
    
    bot = TelegramBot(config, mock_order_engine, mock_risk_manager)
    
    print("🔄 Testing different trading modes...")
    
    # Test AUTO mode
    bot.set_trading_mode(TradingMode.AUTO)
    print(f"✅ AUTO mode: Signals executed automatically without approval")
    print(f"   Current mode: {bot.get_trading_mode().value}")
    print(f"   Best for: Trusted strategies, high-frequency trading")
    
    # Test MANUAL mode
    bot.set_trading_mode(TradingMode.MANUAL)
    print(f"\n✅ MANUAL mode: All signals require user approval")
    print(f"   Current mode: {bot.get_trading_mode().value}")
    print(f"   Best for: Learning, high-risk trades, market uncertainty")
    
    # Test PAUSED mode
    bot.set_trading_mode(TradingMode.PAUSED)
    print(f"\n✅ PAUSED mode: All trading suspended")
    print(f"   Current mode: {bot.get_trading_mode().value}")
    print(f"   Best for: Market maintenance, system updates, holidays")
    
    print(f"\n🎮 Trading Controls:")
    
    # Pause trading
    bot.pause_trading()
    print(f"⏸️  Trading paused: {bot.is_trading_paused()}")
    
    # Resume trading
    bot.resume_trading()
    print(f"▶️  Trading resumed: {not bot.is_trading_paused()}")
    
    # Emergency stop
    bot.emergency_stop()
    print(f"🚨 Emergency stop activated: {bot.is_emergency_stopped()}")
    
    print(f"\n📱 Telegram Commands for Mode Control:")
    print(f"   /mode auto    - Switch to automatic trading")
    print(f"   /mode manual  - Switch to manual approval")
    print(f"   /pause        - Pause all trading")
    print(f"   /resume       - Resume trading")
    print(f"   /stop         - Emergency stop (halt everything)")
    print(f"   /status       - Check current system status")


async def example_trade_notifications():
    """Example: Real-time trade notifications and updates"""
    print("\n📊 Example 4: Trade Notifications")
    print("-" * 40)
    
    from core.telegram_service import TelegramBot, TelegramConfig, MessageFormatter
    from unittest.mock import Mock, AsyncMock
    
    # Create message formatter for demo
    formatter = MessageFormatter()
    
    print("📱 Types of Telegram notifications:")
    
    # 1. Signal Alert
    print(f"\n🎯 1. Signal Alert:")
    print(f"   When: New trading opportunity detected")
    print(f"   Contains: Company, gap %, volume, confidence, entry/exit levels")
    print(f"   Action: Approve/Reject buttons (manual mode)")
    
    # 2. Trade Entry
    print(f"\n📈 2. Trade Entry Notification:")
    print(f"   When: Position opened successfully")
    print(f"   Contains: Entry price, quantity, order ID, expected targets")
    print(f"   Example: \"✅ RELIANCE: Bought 10 shares @ ₹2,477.50\"")
    
    # 3. Trade Exit
    print(f"\n📉 3. Trade Exit Notification:")
    print(f"   When: Position closed (profit/loss/stop)")
    print(f"   Contains: Exit price, P&L, return %, reason")
    print(f"   Example: \"💰 RELIANCE: Sold 10 shares @ ₹2,575.00 (+₹975, +3.9%)\"")
    
    # 4. P&L Updates
    print(f"\n💹 4. Real-time P&L Updates:")
    print(f"   When: Significant price movements (configurable threshold)")
    print(f"   Contains: Current price, unrealized P&L, percentage move")
    print(f"   Example: \"📊 RELIANCE: ₹2,520.00 (+₹425, +1.7%)\"")
    
    # 5. Risk Alerts
    print(f"\n⚠️  5. Risk Management Alerts:")
    print(f"   When: Risk limits approached or breached")
    print(f"   Contains: Alert level, reason, recommended action")
    print(f"   Example: \"🚨 HIGH RISK: Daily loss limit approaching (-₹4,850)\"")
    
    # 6. System Status
    print(f"\n🖥️  6. System Status Updates:")
    print(f"   When: Mode changes, market open/close, system events")
    print(f"   Contains: Current mode, active trades, daily stats")
    print(f"   Example: \"🤖 Mode: AUTO | Active: 3 trades | P&L: +₹1,250\"")
    
    # Demo message formatting
    print(f"\n📝 Message Formatting Features:")
    print(f"   ✅ Professional HTML formatting")
    print(f"   🎨 Context-appropriate emojis")
    print(f"   💰 Indian Rupee currency formatting")
    print(f"   📊 Progress bars and status indicators")
    print(f"   🔗 Interactive inline keyboards")
    print(f"   ⏱️  Timestamp and timeout information")


async def example_command_handling():
    """Example: Telegram command handling and system control"""
    print("\n⌨️  Example 5: Command Handling")
    print("-" * 40)
    
    from core.telegram_service import CommandHandler, TelegramBot, TelegramConfig
    from core.order_engine import PositionStatus
    from unittest.mock import Mock, AsyncMock
    from datetime import datetime
    
    # Mock dependencies
    mock_order_engine = Mock()
    mock_risk_manager = Mock()
    
    # Mock position data
    mock_positions = {
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
            current_price=3180.0,
            pnl=-100.0,
            pnl_percent=-0.63,
            unrealized_pnl=-100.0,
            day_pnl=-100.0,
            position_value=15900.0,
            last_updated=datetime.now()
        )
    }
    
    mock_order_engine.position_tracker.get_all_positions.return_value = mock_positions
    mock_order_engine.get_execution_status.return_value = {
        'active_trades': 2,
        'total_trades': 15,
        'emergency_stop': False,
        'paper_trading': True,
        'success_rate': 73.3
    }
    
    config = TelegramConfig(
        bot_token="demo_token",
        chat_ids=[123456789]
    )
    
    bot = TelegramBot(config, mock_order_engine, mock_risk_manager)
    
    print("📱 Available Telegram Commands:")
    
    # /status command
    print(f"\n🖥️  /status - System Status")
    print(f"   Shows: Trading mode, active trades, P&L, emergency status")
    print(f"   Usage: /status")
    print(f"   Response: Complete system overview with key metrics")
    
    # /pnl command
    print(f"\n💰 /pnl - Profit & Loss Summary")
    print(f"   Shows: All positions, individual P&L, total portfolio value")
    print(f"   Usage: /pnl")
    print(f"   Response: Detailed breakdown of all active positions")
    
    # /mode command
    print(f"\n🎛️  /mode - Change Trading Mode")
    print(f"   Options: auto, manual, paused")
    print(f"   Usage: /mode manual")
    print(f"   Response: Confirmation of mode change")
    
    # /pause command
    print(f"\n⏸️  /pause - Pause Trading")
    print(f"   Effect: Suspends all new trade execution")
    print(f"   Usage: /pause")
    print(f"   Response: Trading paused confirmation")
    
    # /resume command
    print(f"\n▶️  /resume - Resume Trading")
    print(f"   Effect: Reactivates trade execution")
    print(f"   Usage: /resume")
    print(f"   Response: Trading resumed confirmation")
    
    # /stop command
    print(f"\n🚨 /stop - Emergency Stop")
    print(f"   Effect: Immediately halts all trading, closes positions")
    print(f"   Usage: /stop")
    print(f"   Response: Emergency stop activated confirmation")
    
    print(f"\n🔐 Security Features:")
    print(f"   ✅ Chat ID authorization (only configured users)")
    print(f"   ✅ Command rate limiting")
    print(f"   ✅ Session logging and audit trail")
    print(f"   ✅ Error handling and graceful failures")
    
    # Demo command processing
    print(f"\n📋 Example Command Responses:")
    
    # Simulate /status response
    status = await bot.get_status()
    print(f"\n🖥️  /status response:")
    print(f"   Mode: {status.get('trading_mode', 'Unknown')}")
    print(f"   Active trades: {status.get('active_trades', 0)}")
    print(f"   Emergency stop: {status.get('emergency_stop', False)}")
    
    # Simulate /pnl response
    total_pnl = sum(pos.pnl for pos in mock_positions.values())
    total_value = sum(pos.position_value for pos in mock_positions.values())
    
    print(f"\n💰 /pnl response:")
    for symbol, position in mock_positions.items():
        pnl_emoji = "📈" if position.pnl > 0 else "📉"
        print(f"   {pnl_emoji} {symbol}: ₹{position.pnl:+,.0f} ({position.pnl_percent:+.1f}%)")
    print(f"   📊 Total: ₹{total_pnl:+,.0f} (₹{total_value:,.0f} value)")


async def example_risk_management_integration():
    """Example: Risk management alerts and notifications"""
    print("\n🛡️  Example 6: Risk Management Integration")
    print("-" * 40)
    
    from core.telegram_service import TelegramBot, TelegramConfig, MessageFormatter
    from unittest.mock import Mock, AsyncMock
    
    formatter = MessageFormatter()
    
    print("🚨 Risk Management Alert Types:")
    
    # 1. Position Size Alerts
    print(f"\n📏 1. Position Size Alerts:")
    print(f"   Trigger: Position exceeds configured size limits")
    print(f"   Severity: HIGH")
    print(f"   Example: \"Position size limit exceeded for RELIANCE (₹75,000 > ₹50,000)\"")
    
    # 2. Daily Loss Limits
    print(f"\n📉 2. Daily Loss Limits:")
    print(f"   Trigger: Daily losses approach or exceed limits")
    print(f"   Severity: HIGH/CRITICAL")
    print(f"   Example: \"Daily loss limit approached (-₹4,850 of -₹5,000 limit)\"")
    
    # 3. Correlation Alerts
    print(f"\n🔗 3. Portfolio Correlation:")
    print(f"   Trigger: Too many correlated positions")
    print(f"   Severity: MEDIUM")
    print(f"   Example: \"High correlation detected: 3 IT stocks (80% of portfolio)\"")
    
    # 4. Volatility Alerts
    print(f"\n📊 4. Market Volatility:")
    print(f"   Trigger: Unusual market conditions")
    print(f"   Severity: MEDIUM/HIGH")
    print(f"   Example: \"High volatility detected in banking sector (VIX: 28.5)\"")
    
    # 5. Drawdown Alerts
    print(f"\n📋 5. Drawdown Monitoring:")
    print(f"   Trigger: Portfolio drawdown exceeds thresholds")
    print(f"   Severity: HIGH")
    print(f"   Example: \"Portfolio drawdown: -12.5% (Warning threshold: -10%)\"")
    
    print(f"\n🔧 Risk Alert Configuration:")
    print(f"   ⚙️  Configurable thresholds per risk type")
    print(f"   🔔 Immediate Telegram notifications")
    print(f"   📊 Daily/weekly risk summaries")
    print(f"   🎯 Automatic position size adjustments")
    print(f"   🚨 Emergency stop triggers")
    
    # Demo risk alert messages
    risk_scenarios = [
        {
            "message": "Position size limit exceeded for RELIANCE",
            "severity": "HIGH",
            "action": "Reduce position or increase limits"
        },
        {
            "message": "Daily loss approaching limit (-₹4,850 of -₹5,000)",
            "severity": "HIGH", 
            "action": "Consider stopping trading for the day"
        },
        {
            "message": "Market volatility spike detected (VIX: 32.1)",
            "severity": "MEDIUM",
            "action": "Reduce position sizes, tighten stops"
        }
    ]
    
    print(f"\n📱 Example Risk Alert Messages:")
    for scenario in risk_scenarios:
        risk_message = formatter.format_risk_alert(
            scenario["message"], 
            scenario["severity"]
        )
        print(f"\n   🚨 {scenario['severity']} RISK ALERT")
        print(f"   Message: {scenario['message']}")
        print(f"   Action: {scenario['action']}")


async def example_performance_monitoring():
    """Example: Performance monitoring and analytics via Telegram"""
    print("\n📈 Example 7: Performance Monitoring")
    print("-" * 40)
    
    from core.telegram_service import MessageFormatter
    
    formatter = MessageFormatter()
    
    print("📊 Performance Metrics Available via Telegram:")
    
    # Daily Performance Summary
    print(f"\n📅 Daily Performance Summary:")
    print(f"   Sent: Every market close")
    print(f"   Contains: Total trades, win rate, P&L, best/worst performers")
    print(f"   Example: \"📊 Daily Summary: 8 trades, 75% win rate, +₹2,340 P&L\"")
    
    # Weekly Analytics
    print(f"\n📈 Weekly Analytics Report:")
    print(f"   Sent: Every Sunday evening")
    print(f"   Contains: Weekly trends, strategy performance, risk metrics")
    print(f"   Example: \"📋 Week 23: 35 trades, ₹12,450 profit, 3.2% portfolio growth\"")
    
    # Real-time Milestones
    print(f"\n🎯 Performance Milestones:")
    print(f"   Triggers: Profit targets, loss limits, win streaks")
    print(f"   Example: \"🎉 Milestone: ₹10,000 monthly profit target reached!\"")
    
    # Strategy Performance
    print(f"\n📊 Strategy Breakdown:")
    print(f"   Shows: Performance by signal type, time of day, market conditions")
    print(f"   Example: \"Gap-up signals: 82% win rate (15/18 trades)\"")
    
    # Demo performance data
    performance_data = {
        'daily_trades': 12,
        'daily_pnl': 2340.50,
        'win_rate': 75.0,
        'best_performer': 'RELIANCE (+8.2%)',
        'worst_performer': 'INFY (-1.8%)',
        'total_portfolio_value': 125000.0,
        'monthly_return': 8.4,
        'sharpe_ratio': 1.85
    }
    
    print(f"\n📱 Example Performance Notification:")
    print(f"   📊 Today: {performance_data['daily_trades']} trades")
    print(f"   💰 P&L: ₹{performance_data['daily_pnl']:+,.0f}")
    print(f"   🎯 Win Rate: {performance_data['win_rate']:.0f}%")
    print(f"   📈 Best: {performance_data['best_performer']}")
    print(f"   📉 Worst: {performance_data['worst_performer']}")
    print(f"   💼 Portfolio: ₹{performance_data['total_portfolio_value']:,.0f}")
    print(f"   📅 Monthly: +{performance_data['monthly_return']:.1f}%")
    
    print(f"\n📋 Analytics Commands:")
    print(f"   /performance - Current day/week/month stats")
    print(f"   /trades - Recent trade history")
    print(f"   /analytics - Detailed strategy breakdown")
    print(f"   /risk - Current risk exposure")


async def example_integration_workflow():
    """Example: Complete integration workflow with earnings scanner"""
    print("\n🔄 Example 8: Complete Integration Workflow")
    print("-" * 40)
    
    print("🚀 End-to-End Trading Workflow:")
    
    print(f"\n1. 🔍 Earnings Scanner Detection:")
    print(f"   • Pre-market earnings announcement detected")
    print(f"   • Gap analysis: RELIANCE +6.8% gap up")
    print(f"   • Volume surge: 4.5x normal volume")
    print(f"   • Confidence: HIGH (88%)")
    
    print(f"\n2. 🎯 Signal Generation:")
    print(f"   • Entry price: ₹2,475.00")
    print(f"   • Stop loss: ₹2,400.00 (-3.0%)")
    print(f"   • Profit target: ₹2,575.00 (+4.0%)")
    print(f"   • Risk/Reward: 1:1.33")
    
    print(f"\n3. 🛡️  Risk Validation:")
    print(f"   • Position size: ₹49,500 (4.95% of portfolio)")
    print(f"   • Daily risk exposure: Within limits")
    print(f"   • Correlation check: Passed")
    print(f"   • Volatility assessment: Normal")
    
    print(f"\n4. 📱 Telegram Notification:")
    print(f"   • Signal alert sent to authorized users")
    print(f"   • Interactive buttons: [Approve] [Reject] [Modify] [Details]")
    print(f"   • 5-minute approval timeout")
    
    print(f"\n5. ✅ User Approval (Manual Mode):")
    print(f"   • User clicks 'Approve' button")
    print(f"   • Approval logged with timestamp")
    print(f"   • Trade execution initiated")
    
    print(f"\n6. 📈 Order Execution:")
    print(f"   • Market order placed via Zerodha API")
    print(f"   • Execution: 20 shares @ ₹2,477.50")
    print(f"   • GTT OCO orders placed automatically")
    print(f"   • Position tracking activated")
    
    print(f"\n7. 📊 Real-time Monitoring:")
    print(f"   • Live P&L updates every 30 seconds")
    print(f"   • Price alerts at key levels")
    print(f"   • Risk monitoring continuous")
    
    print(f"\n8. 🎯 Trade Exit:")
    print(f"   • Profit target hit: ₹2,575.00")
    print(f"   • Automatic exit via GTT order")
    print(f"   • P&L: +₹1,950 (+3.95%)")
    print(f"   • Exit notification sent")
    
    print(f"\n9. 📋 Performance Logging:")
    print(f"   • Trade data saved to database")
    print(f"   • Performance metrics updated")
    print(f"   • Strategy statistics refreshed")
    
    print(f"\n📱 Integration Code Example:")
    print(f"""
    # Main trading loop
    async def trading_main_loop():
        # Initialize all components
        scanner = await get_earnings_gap_scanner()
        order_engine = await get_order_engine(paper_trading=True)
        telegram_bot = await initialize_telegram_bot()
        
        while trading_active:
            # 1. Scan for signals
            signals = await scanner.scan_for_signals()
            
            for signal in signals:
                # 2. Risk validation
                is_valid, position_size, warnings = await risk_manager.validate_trade(signal)
                
                if is_valid:
                    # 3. Send for approval (if manual mode)
                    if telegram_bot.get_trading_mode() == TradingMode.MANUAL:
                        approval_id = await telegram_bot.signal_notifier.send_signal_for_approval(signal)
                        # Wait for approval or timeout
                        approval = await wait_for_approval(approval_id, timeout=300)
                        if not approval:
                            continue
                    
                    # 4. Execute trade
                    trade_id = await order_engine.execute_signal(signal)
                    
                    if trade_id:
                        # 5. Notify successful execution
                        await telegram_bot.trade_notifier.notify_trade_entry(
                            symbol=signal.symbol,
                            entry_price=signal.entry_price,
                            quantity=position_size.final_size // signal.entry_price,
                            order_id=trade_id,
                            signal_id=signal.signal_id
                        )
            
            # 6. Monitor existing positions
            positions = await order_engine.position_tracker.get_all_positions()
            for symbol, position in positions.items():
                if abs(position.pnl_percent) > 2.0:  # 2% move
                    await telegram_bot.trade_notifier.notify_pnl_update(
                        symbol=symbol,
                        current_price=position.current_price,
                        pnl=position.pnl,
                        pnl_percent=position.pnl_percent,
                        unrealized_pnl=position.unrealized_pnl
                    )
            
            await asyncio.sleep(30)  # Check every 30 seconds
    """)
    
    print(f"\n⚙️  Configuration Requirements:")
    print(f"   • Telegram Bot Token (from @BotFather)")
    print(f"   • Authorized Chat IDs")
    print(f"   • Zerodha API credentials")
    print(f"   • Risk management parameters")
    print(f"   • Market data feeds")
    print(f"   • Database connection")


async def main():
    """Run all examples"""
    print("🤖 Telegram Bot Service - Usage Examples")
    print("=" * 60)
    
    examples = [
        example_basic_telegram_setup,
        example_signal_approval_workflow,
        example_trading_mode_management,
        example_trade_notifications,
        example_command_handling,
        example_risk_management_integration,
        example_performance_monitoring,
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
    print("\n💡 Telegram Bot Best Practices:")
    print("1. Always start with manual approval mode for new strategies")
    print("2. Set appropriate approval timeouts (5-10 minutes)")
    print("3. Configure multiple authorized chat IDs for redundancy")
    print("4. Use rate limiting to avoid API throttling")
    print("5. Test all commands and workflows before live trading")
    print("6. Set up proper error handling and notifications")
    print("7. Monitor chat ID authorization regularly")
    print("8. Keep bot token secure and rotate periodically")
    print("9. Use webhook for production, polling for development")
    print("10. Implement comprehensive logging and audit trails")
    
    print("\n🔐 Security Checklist:")
    print("• ✅ Bot token stored securely (environment variable)")
    print("• ✅ Chat ID authorization implemented")
    print("• ✅ Command rate limiting active")
    print("• ✅ Input validation on all commands")
    print("• ✅ Audit logging for all actions")
    print("• ✅ Emergency stop mechanisms tested")
    print("• ✅ Network error handling implemented")
    print("• ✅ Timeout handling for all operations")


if __name__ == "__main__":
    asyncio.run(main())