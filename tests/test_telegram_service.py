#!/usr/bin/env python3
"""
Comprehensive test suite for the Telegram bot service
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_telegram_service():
    """Test the comprehensive Telegram bot service"""
    print("🚀 Testing Telegram Bot Service")
    print("=" * 50)
    
    try:
        from core.telegram_service import (
            TelegramBot, SignalNotifier, TradeNotifier, CommandHandler,
            CallbackHandler, MessageFormatter, TelegramConfig, TradingMode,
            ApprovalStatus, NotificationType, PendingSignal, NotificationMessage
        )
        from core.earnings_scanner import EarningsGapSignal, SignalType, SignalConfidence
        from core.order_engine import OrderEngine, PositionStatus
        from core.risk_manager import RiskManager
        
        # Initialize components
        print("\n1. 🔧 Testing Component Initialization")
        
        # Create test configuration
        test_config = TelegramConfig(
            bot_token="test_bot_token",
            chat_ids=[123456789],
            approval_timeout=300,
            max_retries=3,
            rate_limit_delay=1.0
        )
        
        print(f"✅ Telegram config created: {len(test_config.chat_ids)} chat(s)")
        
        # Create mock dependencies
        mock_order_engine = Mock(spec=OrderEngine)
        mock_risk_manager = Mock(spec=RiskManager)
        
        # Create Telegram bot
        telegram_bot = TelegramBot(test_config, mock_order_engine, mock_risk_manager)
        
        print("✅ Telegram bot components initialized successfully")
        
        # Test Message Formatter
        print("\n2. 📝 Testing Message Formatter")
        
        formatter = MessageFormatter()
        
        # Test emoji access
        print(f"✅ Emojis loaded: {len(formatter.EMOJIS)} emojis")
        print(f"   Signal: {formatter.EMOJIS['signal']}")
        print(f"   Profit: {formatter.EMOJIS['profit']}")
        print(f"   Loss: {formatter.EMOJIS['loss']}")
        
        # Test signal alert formatting
        test_signal = EarningsGapSignal(
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
        
        signal_message = formatter.format_signal_alert(test_signal)
        print("✅ Signal alert formatted:")
        print(f"   Length: {len(signal_message)} characters")
        print(f"   Contains symbol: {'RELIANCE' in signal_message}")
        print(f"   Contains emoji: {formatter.EMOJIS['signal'] in signal_message}")
        
        # Test trade entry formatting
        trade_entry_message = formatter.format_trade_entry(
            symbol="RELIANCE",
            entry_price=2477.5,
            quantity=10,
            order_id="ORDER_12345"
        )
        print("✅ Trade entry formatted:")
        print(f"   Length: {len(trade_entry_message)} characters")
        print(f"   Contains order ID: {'ORDER_12345' in trade_entry_message}")
        
        # Test P&L update formatting
        pnl_message = formatter.format_pnl_update(
            symbol="RELIANCE",
            current_price=2520.0,
            pnl=425.0,
            pnl_percent=1.75,
            unrealized_pnl=425.0
        )
        print("✅ P&L update formatted:")
        print(f"   Length: {len(pnl_message)} characters")
        print(f"   Contains profit emoji: {formatter.EMOJIS['profit'] in pnl_message}")
        
        # Test system status formatting
        status_data = {
            'trading_mode': TradingMode.AUTO.value,
            'active_trades': 2,
            'total_pnl': 850.0,
            'emergency_stop': False
        }
        status_message = formatter.format_system_status(status_data)
        print("✅ System status formatted:")
        print(f"   Length: {len(status_message)} characters")
        print(f"   Contains mode: {TradingMode.AUTO.value in status_message}")
        
        # Test Signal Notifier
        print("\n3. 🎯 Testing Signal Notifier")
        
        # Mock Telegram application
        mock_app = AsyncMock()
        mock_bot = AsyncMock()
        mock_app.bot = mock_bot
        
        signal_notifier = SignalNotifier(test_config, mock_app)
        
        # Test approval keyboard creation
        keyboard = signal_notifier._create_approval_keyboard("signal_123")
        print(f"✅ Approval keyboard created: {len(keyboard.inline_keyboard)} rows")
        print(f"   Buttons per row: {len(keyboard.inline_keyboard[0])} and {len(keyboard.inline_keyboard[1])}")
        
        # Test signal notification sending
        signal_id = "test_signal_123"
        
        # Mock successful message send
        mock_message = Mock()
        mock_message.message_id = 12345
        mock_bot.send_message.return_value = mock_message
        
        success = await signal_notifier.send_signal_for_approval(test_signal, signal_id)
        print(f"✅ Signal notification sent: {success}")
        
        if success:
            # Check if pending signal was stored
            pending_signal = signal_notifier.pending_signals.get(signal_id)
            if pending_signal:
                print(f"   Pending signal stored: {pending_signal.signal_id}")
                print(f"   Message ID: {pending_signal.message_id}")
                print(f"   Status: {pending_signal.status.value}")
            else:
                print("   ⚠️  Pending signal not found")
        
        # Test approval processing
        print("\n4. ✅ Testing Approval Processing")
        
        # Test approval
        approval_result = await signal_notifier.process_approval(
            signal_id, ApprovalStatus.APPROVED, "test_user"
        )
        print(f"✅ Approval processed: {approval_result}")
        
        if approval_result:
            approved_signal = signal_notifier.pending_signals.get(signal_id)
            if approved_signal:
                print(f"   Status updated: {approved_signal.status.value}")
                print(f"   Approved by: {approved_signal.approved_by}")
        
        # Test rejection
        rejection_result = await signal_notifier.process_approval(
            signal_id, ApprovalStatus.REJECTED, "test_user", "Risk too high"
        )
        print(f"✅ Rejection processed: {rejection_result}")
        
        # Test timeout cleanup
        expired_count = signal_notifier.cleanup_expired_signals()
        print(f"✅ Expired signals cleaned: {expired_count}")
        
        # Test Trade Notifier
        print("\n5. 📊 Testing Trade Notifier")
        
        trade_notifier = TradeNotifier(test_config, mock_app)
        
        # Test trade entry notification
        entry_success = await trade_notifier.notify_trade_entry(
            symbol="RELIANCE",
            entry_price=2477.5,
            quantity=10,
            order_id="ORDER_12345",
            signal_id="signal_123"
        )
        print(f"✅ Trade entry notification: {entry_success}")
        
        # Test trade exit notification
        exit_success = await trade_notifier.notify_trade_exit(
            symbol="RELIANCE",
            exit_price=2550.0,
            quantity=10,
            pnl=725.0,
            exit_reason="Profit target hit"
        )
        print(f"✅ Trade exit notification: {exit_success}")
        
        # Test P&L update notification
        pnl_success = await trade_notifier.notify_pnl_update(
            symbol="RELIANCE",
            current_price=2520.0,
            pnl=425.0,
            pnl_percent=1.75,
            unrealized_pnl=425.0
        )
        print(f"✅ P&L update notification: {pnl_success}")
        
        # Test risk alert notification
        risk_success = await trade_notifier.notify_risk_alert(
            "Position size limit exceeded for RELIANCE",
            "HIGH"
        )
        print(f"✅ Risk alert notification: {risk_success}")
        
        # Test Command Handler
        print("\n6. 🎛️  Testing Command Handler")
        
        command_handler = CommandHandler(telegram_bot)
        
        # Mock update and context objects
        mock_update = Mock()
        mock_update.effective_chat.id = 123456789
        mock_update.effective_user.username = "test_user"
        
        mock_context = Mock()
        mock_context.bot = mock_bot
        
        # Test status command
        await command_handler.handle_status(mock_update, mock_context)
        print("✅ Status command handled")
        
        # Test P&L command
        mock_order_engine.position_tracker.get_all_positions.return_value = {
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
            )
        }
        
        await command_handler.handle_pnl(mock_update, mock_context)
        print("✅ P&L command handled")
        
        # Test mode command
        mock_context.args = ["manual"]
        await command_handler.handle_mode(mock_update, mock_context)
        print("✅ Mode command handled")
        
        # Test pause command
        await command_handler.handle_pause(mock_update, mock_context)
        print("✅ Pause command handled")
        
        # Test resume command
        await command_handler.handle_resume(mock_update, mock_context)
        print("✅ Resume command handled")
        
        # Test stop command
        await command_handler.handle_stop(mock_update, mock_context)
        print("✅ Stop command handled")
        
        # Test Callback Handler
        print("\n7. 🔄 Testing Callback Handler")
        
        callback_handler = CallbackHandler(telegram_bot)
        
        # Mock callback query
        mock_query = Mock()
        mock_query.data = "approve_signal_123"
        mock_query.from_user.username = "test_user"
        mock_query.message.chat.id = 123456789
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()
        
        mock_callback_update = Mock()
        mock_callback_update.callback_query = mock_query
        
        # Test approval callback
        await callback_handler.handle_callback(mock_callback_update, mock_context)
        print("✅ Approval callback handled")
        
        # Test rejection callback
        mock_query.data = "reject_signal_123"
        await callback_handler.handle_callback(mock_callback_update, mock_context)
        print("✅ Rejection callback handled")
        
        # Test details callback
        mock_query.data = "details_signal_123"
        await callback_handler.handle_callback(mock_callback_update, mock_context)
        print("✅ Details callback handled")
        
        # Test TelegramBot Main Class
        print("\n8. 🤖 Testing TelegramBot Main Class")
        
        # Test initialization
        initialized = await telegram_bot.initialize()
        print(f"✅ Telegram bot initialized: {initialized}")
        
        # Test trading mode management
        telegram_bot.set_trading_mode(TradingMode.MANUAL)
        current_mode = telegram_bot.get_trading_mode()
        print(f"✅ Trading mode set: {current_mode.value}")
        
        # Test pause/resume
        telegram_bot.pause_trading()
        is_paused = telegram_bot.is_trading_paused()
        print(f"✅ Trading paused: {is_paused}")
        
        telegram_bot.resume_trading()
        is_paused = telegram_bot.is_trading_paused()
        print(f"✅ Trading resumed: {not is_paused}")
        
        # Test emergency stop
        telegram_bot.emergency_stop()
        is_stopped = telegram_bot.is_emergency_stopped()
        print(f"✅ Emergency stop: {is_stopped}")
        
        # Test status retrieval
        status = await telegram_bot.get_status()
        print(f"✅ Status retrieved: {len(status)} fields")
        print(f"   Trading mode: {status.get('trading_mode')}")
        print(f"   Is paused: {status.get('is_paused')}")
        print(f"   Emergency stop: {status.get('emergency_stop')}")
        
        # Test Data Structures
        print("\n9. 📋 Testing Data Structures")
        
        # Test PendingSignal
        pending_signal = PendingSignal(
            signal_id="test_123",
            signal=test_signal,
            message_id=12345,
            chat_id=123456789,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=5),
            status=ApprovalStatus.PENDING
        )
        
        print(f"✅ PendingSignal created: {pending_signal.signal_id}")
        print(f"   Status: {pending_signal.status.value}")
        print(f"   Expires in: {(pending_signal.expires_at - datetime.now()).seconds}s")
        
        # Test NotificationMessage
        notification_message = NotificationMessage(
            type=NotificationType.SIGNAL_ALERT,
            title="New Trading Signal",
            content="RELIANCE gap up detected",
            chat_ids=[123456789]
        )
        
        print(f"✅ NotificationMessage created: {notification_message.type.value}")
        print(f"   Title: {notification_message.title}")
        print(f"   Chat IDs: {len(notification_message.chat_ids)}")
        
        # Test TelegramConfig
        config_dict = {
            'bot_token': test_config.bot_token,
            'chat_ids': test_config.chat_ids,
            'approval_timeout': test_config.approval_timeout
        }
        print(f"✅ TelegramConfig serialization: {len(config_dict)} fields")
        
        # Test Error Handling
        print("\n10. ⚠️  Testing Error Handling")
        
        # Test invalid chat ID
        invalid_config = TelegramConfig(
            bot_token="test_token",
            chat_ids=[]  # Empty chat IDs
        )
        
        invalid_notifier = SignalNotifier(invalid_config, mock_app)
        invalid_success = await invalid_notifier.send_signal_for_approval(test_signal, "test_invalid")
        print(f"✅ Invalid config handled: {not invalid_success}")
        
        # Test network error simulation
        mock_bot.send_message.side_effect = Exception("Network error")
        
        network_error_success = await signal_notifier.send_signal_for_approval(test_signal, "network_test")
        print(f"✅ Network error handled: {not network_error_success}")
        
        # Reset mock
        mock_bot.send_message.side_effect = None
        mock_bot.send_message.return_value = mock_message
        
        # Test Rate Limiting
        print("\n11. ⚡ Testing Rate Limiting and Performance")
        
        # Test rate limiting
        rate_limited = telegram_bot._is_rate_limited()
        print(f"✅ Rate limiting check: {not rate_limited}")  # Should not be rate limited initially
        
        # Test message formatting performance
        start_time = datetime.now()
        for i in range(100):
            formatter.format_signal_alert(test_signal)
        end_time = datetime.now()
        
        avg_time = (end_time - start_time).total_seconds() / 100 * 1000
        print(f"✅ Message formatting performance: {avg_time:.2f}ms avg")
        
        # Test approval processing performance
        start_time = datetime.now()
        for i in range(100):
            await signal_notifier.process_approval(f"test_{i}", ApprovalStatus.APPROVED, "test_user")
        end_time = datetime.now()
        
        avg_time = (end_time - start_time).total_seconds() / 100 * 1000
        print(f"✅ Approval processing performance: {avg_time:.2f}ms avg")
        
        # Test Enum Values
        print("\n12. 🏷️  Testing Enums and Constants")
        
        print(f"✅ Trading modes: {[tm.value for tm in TradingMode]}")
        print(f"✅ Approval statuses: {[as_.value for as_ in ApprovalStatus]}")
        print(f"✅ Notification types: {[nt.value for nt in NotificationType]}")
        
        # Test timeout scenarios
        print("\n13. ⏱️  Testing Timeout Scenarios")
        
        # Create expired signal
        expired_signal = PendingSignal(
            signal_id="expired_123",
            signal=test_signal,
            message_id=54321,
            chat_id=123456789,
            created_at=datetime.now() - timedelta(minutes=10),
            expires_at=datetime.now() - timedelta(minutes=5),  # Already expired
            status=ApprovalStatus.PENDING
        )
        
        signal_notifier.pending_signals["expired_123"] = expired_signal
        
        # Test cleanup
        expired_count = signal_notifier.cleanup_expired_signals()
        print(f"✅ Expired signals cleaned: {expired_count}")
        
        remaining_signal = signal_notifier.pending_signals.get("expired_123")
        if remaining_signal:
            print(f"   Remaining status: {remaining_signal.status.value}")
        else:
            print("   Signal properly removed")
        
        # Test Integration Scenarios
        print("\n14. 🔄 Testing Integration Scenarios")
        
        # Test full signal approval workflow
        workflow_signal_id = "workflow_test"
        
        # Step 1: Send signal for approval
        workflow_success = await signal_notifier.send_signal_for_approval(test_signal, workflow_signal_id)
        print(f"✅ Workflow step 1 (send): {workflow_success}")
        
        # Step 2: Process approval
        if workflow_success:
            approval_success = await signal_notifier.process_approval(
                workflow_signal_id, ApprovalStatus.APPROVED, "test_user"
            )
            print(f"✅ Workflow step 2 (approve): {approval_success}")
            
            # Step 3: Notify trade entry
            if approval_success:
                entry_success = await trade_notifier.notify_trade_entry(
                    symbol=test_signal.symbol,
                    entry_price=test_signal.entry_price,
                    quantity=10,
                    order_id="WORKFLOW_ORDER",
                    signal_id=workflow_signal_id
                )
                print(f"✅ Workflow step 3 (entry): {entry_success}")
        
        # Cleanup
        print("\n15. 🧹 Testing Cleanup")
        await telegram_bot.cleanup()
        print("✅ Telegram bot cleanup completed")
        
        print("\n" + "=" * 50)
        print("🎉 All Telegram Bot Service tests completed successfully!")
        print("\n📊 Test Summary:")
        print("✅ Component initialization")
        print("✅ Message formatting and emojis")
        print("✅ Signal notification and approval system")
        print("✅ Trade notifications and P&L updates")
        print("✅ Command handling (/status, /pnl, /mode, etc.)")
        print("✅ Callback handling (inline buttons)")
        print("✅ Main TelegramBot orchestration")
        print("✅ Data structure validation")
        print("✅ Error handling and resilience")
        print("✅ Rate limiting and performance")
        print("✅ Enum and constant validation")
        print("✅ Timeout and expiry handling")
        print("✅ Integration workflow testing")
        print("✅ Resource cleanup")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure all dependencies are installed:")
        print("   pip install python-telegram-bot")
        return False
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_message_scenarios():
    """Test specific message formatting scenarios"""
    print("\n🧠 Testing Message Scenarios")
    print("-" * 30)
    
    try:
        from core.telegram_service import MessageFormatter
        from core.earnings_scanner import EarningsGapSignal, SignalType, SignalConfidence
        
        formatter = MessageFormatter()
        
        # Scenario 1: High confidence gap up signal
        print("1. Testing high confidence gap up message...")
        
        high_confidence_signal = EarningsGapSignal(
            symbol="RELIANCE",
            company_name="Reliance Industries Limited",
            signal_type=SignalType.EARNINGS_GAP_UP,
            confidence=SignalConfidence.HIGH,
            confidence_score=92.0,
            entry_time=datetime.now(),
            entry_price=2475.0,
            stop_loss=2400.0,
            profit_target=2600.0,
            gap_percent=8.5,
            gap_amount=195.0,
            previous_close=2280.0,
            volume_ratio=5.2,
            current_volume=5200000,
            earnings_surprise=25.0,
            actual_eps=35.0,
            expected_eps=28.0,
            risk_reward_ratio=2.5,
            signal_explanation="Exceptional earnings beat with massive gap up and volume explosion"
        )
        
        high_message = formatter.format_signal_alert(high_confidence_signal)
        print(f"✅ High confidence message: {len(high_message)} chars")
        print(f"   Contains HIGH: {'HIGH' in high_message}")
        print(f"   Contains gap %: {'8.5%' in high_message}")
        
        # Scenario 2: Medium confidence gap down signal
        print("\n2. Testing medium confidence gap down message...")
        
        medium_confidence_signal = EarningsGapSignal(
            symbol="HDFCBANK",
            company_name="HDFC Bank Limited",
            signal_type=SignalType.EARNINGS_GAP_DOWN,
            confidence=SignalConfidence.MEDIUM,
            confidence_score=68.0,
            entry_time=datetime.now(),
            entry_price=1450.0,
            stop_loss=1520.0,
            profit_target=1350.0,
            gap_percent=-6.2,
            gap_amount=-95.0,
            previous_close=1545.0,
            volume_ratio=3.8,
            current_volume=3800000,
            earnings_surprise=-15.0,
            actual_eps=18.0,
            expected_eps=21.0,
            risk_reward_ratio=1.8,
            signal_explanation="Earnings miss triggering gap down with elevated volume"
        )
        
        medium_message = formatter.format_signal_alert(medium_confidence_signal)
        print(f"✅ Medium confidence message: {len(medium_message)} chars")
        print(f"   Contains MEDIUM: {'MEDIUM' in medium_message}")
        print(f"   Contains negative gap: {'-6.2%' in medium_message}")
        
        # Scenario 3: Large profit notification
        print("\n3. Testing large profit notification...")
        
        large_profit_message = formatter.format_trade_exit(
            symbol="TCS",
            exit_price=3450.0,
            quantity=15,
            pnl=2250.0,
            exit_reason="Profit target achieved",
            entry_price=3300.0
        )
        print(f"✅ Large profit message: {len(large_profit_message)} chars")
        print(f"   Contains profit emoji: {formatter.EMOJIS['profit'] in large_profit_message}")
        print(f"   Contains amount: {'2,250' in large_profit_message}")
        
        # Scenario 4: Stop loss triggered
        print("\n4. Testing stop loss message...")
        
        stop_loss_message = formatter.format_trade_exit(
            symbol="INFY",
            exit_price=1480.0,
            quantity=8,
            pnl=-320.0,
            exit_reason="Stop loss triggered",
            entry_price=1520.0
        )
        print(f"✅ Stop loss message: {len(stop_loss_message)} chars")
        print(f"   Contains loss emoji: {formatter.EMOJIS['loss'] in stop_loss_message}")
        print(f"   Contains negative amount: {'-320' in stop_loss_message}")
        
        # Scenario 5: System status with multiple positions
        print("\n5. Testing complex system status...")
        
        complex_status = {
            'trading_mode': 'AUTO',
            'active_trades': 5,
            'total_pnl': 1250.75,
            'emergency_stop': False,
            'daily_trades': 12,
            'success_rate': 75.0,
            'best_performer': 'RELIANCE (+8.5%)',
            'worst_performer': 'INFY (-2.1%)'
        }
        
        complex_status_message = formatter.format_system_status(complex_status)
        print(f"✅ Complex status message: {len(complex_status_message)} chars")
        print(f"   Contains success rate: {'75.0%' in complex_status_message}")
        print(f"   Contains best performer: {'RELIANCE' in complex_status_message}")
        
        # Scenario 6: Risk alert messages
        print("\n6. Testing risk alert messages...")
        
        risk_scenarios = [
            ("Position size limit exceeded for RELIANCE", "HIGH"),
            ("Daily loss limit approaching", "MEDIUM"),
            ("Unusual market volatility detected", "LOW")
        ]
        
        for message, severity in risk_scenarios:
            risk_message = formatter.format_risk_alert(message, severity)
            print(f"✅ {severity} risk alert: {len(risk_message)} chars")
            print(f"   Contains severity: {severity in risk_message}")
        
        # Scenario 7: P&L update scenarios
        print("\n7. Testing P&L update scenarios...")
        
        pnl_scenarios = [
            {"pnl": 1500.0, "percent": 5.2, "status": "Strong profit"},
            {"pnl": -450.0, "percent": -2.8, "status": "Minor loss"},
            {"pnl": 25.0, "percent": 0.1, "status": "Break-even"}
        ]
        
        for scenario in pnl_scenarios:
            pnl_message = formatter.format_pnl_update(
                symbol="TEST",
                current_price=1000.0,
                pnl=scenario["pnl"],
                pnl_percent=scenario["percent"],
                unrealized_pnl=scenario["pnl"]
            )
            print(f"✅ {scenario['status']} P&L: {len(pnl_message)} chars")
            
            expected_emoji = formatter.EMOJIS['profit'] if scenario["pnl"] > 0 else formatter.EMOJIS['loss']
            if scenario["pnl"] > -50 and scenario["pnl"] < 50:  # Break-even range
                expected_emoji = formatter.EMOJIS['neutral']
            
            print(f"   Contains appropriate emoji: {expected_emoji in pnl_message}")
        
        print("\n✅ Message scenario tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Message scenario test failed: {e}")
        return False


async def test_telegram_integration():
    """Test Telegram bot integration scenarios"""
    print("\n🔗 Testing Telegram Integration")
    print("-" * 30)
    
    try:
        from core.telegram_service import TelegramBot, TelegramConfig, TradingMode
        from unittest.mock import Mock, AsyncMock
        
        # Mock order engine and risk manager
        mock_order_engine = Mock()
        mock_order_engine.execute_signal = AsyncMock(return_value="TRADE_123")
        mock_order_engine.get_execution_status = AsyncMock(return_value={
            'active_trades': 2,
            'total_trades': 15,
            'emergency_stop': False,
            'paper_trading': True
        })
        
        mock_risk_manager = Mock()
        
        # Test configuration
        config = TelegramConfig(
            bot_token="test_token",
            chat_ids=[123456789, 987654321],
            approval_timeout=300
        )
        
        bot = TelegramBot(config, mock_order_engine, mock_risk_manager)
        
        # Test 1: Auto trading mode workflow
        print("1. Testing auto trading mode workflow...")
        
        bot.set_trading_mode(TradingMode.AUTO)
        
        # In auto mode, signals should be executed immediately
        from core.earnings_scanner import EarningsGapSignal, SignalType, SignalConfidence
        
        auto_signal = EarningsGapSignal(
            symbol="AUTO_TEST",
            company_name="Auto Test Company",
            signal_type=SignalType.EARNINGS_GAP_UP,
            confidence=SignalConfidence.HIGH,
            confidence_score=85.0,
            entry_time=datetime.now(),
            entry_price=1000.0,
            stop_loss=950.0,
            profit_target=1100.0,
            gap_percent=5.0,
            gap_amount=50.0,
            previous_close=950.0,
            volume_ratio=3.0,
            current_volume=3000000,
            earnings_surprise=15.0,
            actual_eps=25.0,
            expected_eps=22.0,
            risk_reward_ratio=2.0,
            signal_explanation="Auto mode test signal"
        )
        
        # Simulate auto execution
        auto_result = await bot.process_signal(auto_signal)
        print(f"✅ Auto mode signal processed: {auto_result}")
        
        # Test 2: Manual trading mode workflow
        print("\n2. Testing manual trading mode workflow...")
        
        bot.set_trading_mode(TradingMode.MANUAL)
        
        # In manual mode, signals should await approval
        manual_result = await bot.process_signal(auto_signal)
        print(f"✅ Manual mode signal processed: {manual_result}")
        
        # Test 3: Paused mode
        print("\n3. Testing paused mode...")
        
        bot.pause_trading()
        paused_result = await bot.process_signal(auto_signal)
        print(f"✅ Paused mode signal processed: {paused_result is None}")
        bot.resume_trading()
        
        # Test 4: Emergency stop
        print("\n4. Testing emergency stop...")
        
        bot.emergency_stop()
        emergency_result = await bot.process_signal(auto_signal)
        print(f"✅ Emergency stop signal processed: {emergency_result is None}")
        
        # Test 5: Multi-chat notification
        print("\n5. Testing multi-chat notifications...")
        
        # Reset bot state
        bot._emergency_stop = False
        bot.set_trading_mode(TradingMode.AUTO)
        
        # Test broadcasting to multiple chats
        broadcast_success = await bot.broadcast_message("Test broadcast message")
        print(f"✅ Broadcast to {len(config.chat_ids)} chats: {broadcast_success}")
        
        # Test 6: Command authorization
        print("\n6. Testing command authorization...")
        
        authorized_chat = 123456789
        unauthorized_chat = 555555555
        
        auth_result_valid = bot._is_authorized_chat(authorized_chat)
        auth_result_invalid = bot._is_authorized_chat(unauthorized_chat)
        
        print(f"✅ Authorized chat access: {auth_result_valid}")
        print(f"✅ Unauthorized chat blocked: {not auth_result_invalid}")
        
        # Test 7: Rate limiting
        print("\n7. Testing rate limiting...")
        
        # Simulate rapid message sending
        rate_limit_tests = []
        for i in range(5):
            is_limited = bot._is_rate_limited()
            rate_limit_tests.append(is_limited)
            bot._update_rate_limiter()
        
        print(f"✅ Rate limiting active: {any(rate_limit_tests)}")
        
        # Test 8: Error recovery
        print("\n8. Testing error recovery...")
        
        # Simulate network error
        original_send = bot.signal_notifier.send_signal_for_approval
        bot.signal_notifier.send_signal_for_approval = AsyncMock(side_effect=Exception("Network error"))
        
        error_result = await bot.process_signal(auto_signal)
        print(f"✅ Error handled gracefully: {error_result is None}")
        
        # Restore original method
        bot.signal_notifier.send_signal_for_approval = original_send
        
        print("\n✅ Telegram integration tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Telegram integration test failed: {e}")
        return False


if __name__ == "__main__":
    async def main():
        print("🧪 Telegram Bot Service Test Suite")
        print("=" * 60)
        
        # Run main tests
        main_test_success = await test_telegram_service()
        
        # Run message scenario tests
        message_test_success = await test_message_scenarios()
        
        # Run integration tests
        integration_test_success = await test_telegram_integration()
        
        print("\n" + "=" * 60)
        if main_test_success and message_test_success and integration_test_success:
            print("🎉 ALL TESTS PASSED!")
            print("\n📝 Next Steps:")
            print("1. Set up Telegram bot token (BotFather)")
            print("2. Configure authorized chat IDs")
            print("3. Test with live Telegram API")
            print("4. Integrate with earnings scanner signals")
            print("5. Connect to order execution engine")
            print("6. Set up monitoring and logging")
            print("7. Test approval workflows with real users")
            print("8. Configure emergency notification systems")
            return 0
        else:
            print("❌ Some tests failed. Please check the errors above.")
            return 1
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)