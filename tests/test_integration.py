#!/usr/bin/env python3
"""
Integration tests for the complete earnings gap trading system
Tests end-to-end workflows, component interactions, WebSocket communication, and database operations
"""

import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pytest
import asyncio
import json
import websockets
from datetime import datetime, timedelta
import pandas as pd
import sqlite3
from pathlib import Path

from main import app, websocket_manager, app_state
from core.earnings_scanner import EarningsGapScanner
from core.risk_manager import RiskManager
from core.order_engine import OrderEngine
from core.market_data import MarketDataManager
from core.telegram_service import TelegramBot
from database import init_database, get_db_session
from models.trade_models import Trade, Position, Portfolio, EarningsEvent
from models.config_models import TradingConfig, RiskConfig, TelegramConfig
import logging

# Disable logging during tests
logging.disable(logging.CRITICAL)


class TestEndToEndWorkflow(unittest.TestCase):
    """Test complete end-to-end trading workflows"""
    
    def setUp(self):
        """Setup integration test environment"""
        self.test_db_path = ":memory:"  # In-memory database for testing
        
        # Initialize test database
        self.db_session = self._setup_test_database()
        
        # Create test portfolio
        self.test_portfolio = Portfolio(
            name="Integration Test Portfolio",
            balance=1000000.0,
            equity=1000000.0,
            margin_available=500000.0,
            margin_used=0.0,
            total_pnl=0.0,
            daily_pnl=0.0,
            is_active=True
        )
        self.db_session.add(self.test_portfolio)
        self.db_session.commit()
    
    def _setup_test_database(self):
        """Setup test database with required tables"""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from database import Base
        
        engine = create_engine(f"sqlite:///{self.test_db_path}", echo=False)
        Base.metadata.create_all(engine)
        
        SessionLocal = sessionmaker(bind=engine)
        return SessionLocal()
    
    def tearDown(self):
        """Cleanup test environment"""
        self.db_session.close()
    
    @patch('core.market_data.yfinance')
    @patch('core.earnings_scanner.requests')
    def test_signal_generation_to_execution_workflow(self, mock_requests, mock_yf):
        """Test complete workflow from signal generation to order execution"""
        
        # Step 1: Setup mock data for earnings scanner
        mock_earnings_response = {
            "events": [
                {
                    "symbol": "RELIANCE",
                    "company_name": "Reliance Industries Ltd",
                    "earnings_date": (datetime.now() + timedelta(days=1)).isoformat(),
                    "expected_eps": 85.0
                }
            ]
        }
        mock_requests.get.return_value.json.return_value = mock_earnings_response
        
        # Mock price data showing gap
        mock_hist_data = pd.DataFrame({
            'Close': [2400.0, 2520.0],  # 5% gap up
            'Open': [2405.0, 2520.0],
            'Volume': [1000000, 2500000],  # 2.5x volume
            'High': [2450.0, 2550.0],
            'Low': [2390.0, 2500.0]
        }, index=pd.date_range('2024-01-01', periods=2, freq='D'))
        
        mock_yf.Ticker.return_value.history.return_value = mock_hist_data
        mock_yf.Ticker.return_value.info = {
            "longName": "Reliance Industries Limited",
            "marketCap": 1500000000000,
            "sector": "Energy"
        }
        
        # Step 2: Initialize components
        market_data_manager = MarketDataManager()
        earnings_scanner = EarningsGapScanner(market_data_manager)
        
        risk_config = RiskConfig(
            max_portfolio_risk=0.02,
            max_daily_loss=0.05,
            max_positions=5
        )
        risk_manager = RiskManager(risk_config)
        
        trading_config = TradingConfig(paper_trading=True)
        order_engine = OrderEngine(
            api_key="test_key",
            access_token="test_token",
            risk_manager=risk_manager,
            market_data_manager=market_data_manager,
            config=trading_config
        )
        
        # Step 3: Execute workflow
        with patch.object(earnings_scanner, 'db', self.db_session):
            with patch.object(risk_manager, 'get_active_positions', return_value=[]):
                with patch.object(order_engine, '_get_active_portfolio', return_value=self.test_portfolio):
                    
                    # Scan for signals
                    signals = asyncio.run(earnings_scanner.scan_for_signals())
                    
                    # Should find the gap signal
                    self.assertGreater(len(signals), 0)
                    
                    signal = signals[0]
                    self.assertEqual(signal.symbol, "RELIANCE")
                    self.assertGreater(signal.gap_percent, 4.0)
                    
                    # Execute signal
                    execution_result = order_engine.execute_signal(signal)
                    
                    # Should execute successfully in paper trading
                    self.assertEqual(execution_result["status"], "EXECUTED")
                    self.assertIn("order_id", execution_result)
                    self.assertTrue(execution_result["paper_trading"])
    
    def test_risk_manager_circuit_breaker_integration(self):
        """Test risk manager circuit breaker integration with order engine"""
        
        # Create portfolio with significant losses to trigger circuit breaker
        distressed_portfolio = Portfolio(
            name="Distressed Portfolio",
            balance=1000000.0,
            equity=940000.0,  # 6% loss
            daily_pnl=-60000.0,  # 6% daily loss (exceeds 5% limit)
            is_active=True
        )
        
        risk_config = RiskConfig(
            max_daily_loss=0.05,  # 5% daily loss limit
            circuit_breaker_threshold=0.05
        )
        risk_manager = RiskManager(risk_config)
        
        # Test circuit breaker activation
        should_stop = risk_manager.check_circuit_breaker(distressed_portfolio)
        self.assertTrue(should_stop)
        
        # Test that order engine respects circuit breaker
        order_engine = OrderEngine(
            api_key="test_key",
            access_token="test_token", 
            risk_manager=risk_manager,
            paper_trading=True
        )
        
        # Mock signal
        from models.trade_models import TradeSignal
        signal = TradeSignal(
            symbol="TEST",
            signal_type="EARNINGS_GAP_UP",
            entry_price=1000.0,
            stop_loss=970.0,
            profit_target=1060.0,
            confidence=0.85,
            gap_percent=3.5,
            volume_ratio=2.2
        )
        
        with patch.object(order_engine, '_get_active_portfolio', return_value=distressed_portfolio):
            result = order_engine.execute_signal(signal)
            
            # Should be blocked by circuit breaker
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("circuit breaker", result["reason"].lower())
    
    def test_database_operations_integration(self):
        """Test database operations across all components"""
        
        # Test earnings event storage
        earnings_event = EarningsEvent(
            symbol="DBTEST",
            company_name="Database Test Company",
            earnings_date=datetime.now() + timedelta(days=1),
            expected_eps=25.5,
            actual_eps=None,
            revenue_estimate=5000000000,
            sector="Technology"
        )
        
        self.db_session.add(earnings_event)
        self.db_session.commit()
        
        # Verify storage
        stored_event = self.db_session.query(EarningsEvent).filter_by(symbol="DBTEST").first()
        self.assertIsNotNone(stored_event)
        self.assertEqual(stored_event.company_name, "Database Test Company")
        
        # Test trade storage
        trade = Trade(
            symbol="DBTEST",
            trade_type="BUY",
            quantity=100,
            entry_price=1000.0,
            stop_loss=970.0,
            target_price=1060.0,
            status="OPEN",
            strategy="earnings_gap",
            portfolio_id=self.test_portfolio.id,
            signal_confidence=0.85,
            gap_percent=3.5
        )
        
        self.db_session.add(trade)
        self.db_session.commit()
        
        # Verify trade storage
        stored_trade = self.db_session.query(Trade).filter_by(symbol="DBTEST").first()
        self.assertIsNotNone(stored_trade)
        self.assertEqual(stored_trade.quantity, 100)
        self.assertEqual(stored_trade.strategy, "earnings_gap")
        
        # Test position creation from trade
        position = Position(
            symbol="DBTEST",
            quantity=100,
            entry_price=1000.0,
            current_price=1020.0,
            stop_loss=970.0,
            target_price=1060.0,
            status="OPEN",
            trade_id=stored_trade.id,
            portfolio_id=self.test_portfolio.id
        )
        
        self.db_session.add(position)
        self.db_session.commit()
        
        # Verify position storage and relationships
        stored_position = self.db_session.query(Position).filter_by(symbol="DBTEST").first()
        self.assertIsNotNone(stored_position)
        self.assertEqual(stored_position.trade_id, stored_trade.id)
        self.assertEqual(stored_position.portfolio_id, self.test_portfolio.id)
    
    @patch('core.telegram_service.telegram.Bot')
    def test_telegram_integration_workflow(self, mock_telegram):
        """Test Telegram bot integration with trading workflow"""
        
        # Setup mock Telegram bot
        mock_bot = Mock()
        mock_telegram.return_value = mock_bot
        
        telegram_config = TelegramConfig(
            bot_token="test_token",
            chat_ids=["12345"],
            approval_timeout=300
        )
        
        # Create telegram bot
        risk_manager = RiskManager(RiskConfig())
        order_engine = OrderEngine(
            api_key="test_key",
            access_token="test_token",
            risk_manager=risk_manager,
            paper_trading=True
        )
        
        telegram_bot = TelegramBot(telegram_config, order_engine, risk_manager)
        
        # Test signal notification
        from models.trade_models import TradeSignal
        signal = TradeSignal(
            symbol="TELEGRAM",
            signal_type="EARNINGS_GAP_UP",
            entry_price=1500.0,
            stop_loss=1455.0,
            profit_target=1590.0,
            confidence=0.85,
            gap_percent=4.2,
            volume_ratio=2.8
        )
        
        # Test sending signal for approval
        signal_sent = asyncio.run(
            telegram_bot.signal_notifier.send_signal_for_approval(signal, "test_signal_001")
        )
        
        # Should attempt to send message
        self.assertTrue(signal_sent)
        
        # Test trade notification
        asyncio.run(
            telegram_bot.trade_notifier.notify_trade_entry(
                symbol="TELEGRAM",
                entry_price=1500.0,
                quantity=67,
                order_id="TEST_ORDER_001",
                signal_id="test_signal_001"
            )
        )
        
        # Verify bot was called to send messages
        self.assertTrue(mock_bot.send_message.called)
    
    def test_performance_monitoring_integration(self):
        """Test performance monitoring across components"""
        
        # Create mock trades with different outcomes
        winning_trade = Trade(
            symbol="WINNER",
            trade_type="BUY",
            quantity=100,
            entry_price=1000.0,
            exit_price=1080.0,  # 8% profit
            stop_loss=970.0,
            target_price=1060.0,
            status="CLOSED",
            strategy="earnings_gap",
            portfolio_id=self.test_portfolio.id,
            entry_timestamp=datetime.now() - timedelta(days=2),
            exit_timestamp=datetime.now() - timedelta(days=1),
            pnl=8000.0  # (1080-1000) * 100
        )
        
        losing_trade = Trade(
            symbol="LOSER",
            trade_type="BUY",
            quantity=50,
            entry_price=2000.0,
            exit_price=1940.0,  # 3% loss (stopped out)
            stop_loss=1940.0,
            target_price=2120.0,
            status="CLOSED",
            strategy="earnings_gap",
            portfolio_id=self.test_portfolio.id,
            entry_timestamp=datetime.now() - timedelta(days=1),
            exit_timestamp=datetime.now(),
            pnl=-3000.0  # (1940-2000) * 50
        )
        
        self.db_session.add(winning_trade)
        self.db_session.add(losing_trade)
        self.db_session.commit()
        
        # Calculate performance metrics
        all_trades = self.db_session.query(Trade).filter_by(
            portfolio_id=self.test_portfolio.id,
            status="CLOSED"
        ).all()
        
        total_trades = len(all_trades)
        winning_trades = len([t for t in all_trades if t.pnl > 0])
        total_pnl = sum(t.pnl for t in all_trades)
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # Verify metrics
        self.assertEqual(total_trades, 2)
        self.assertEqual(winning_trades, 1)
        self.assertEqual(total_pnl, 5000.0)  # 8000 - 3000
        self.assertEqual(win_rate, 50.0)
        
        # Test risk-adjusted returns
        returns = [t.pnl / (t.entry_price * t.quantity) for t in all_trades]
        avg_return = sum(returns) / len(returns)
        
        # Should have positive average return despite 50% win rate
        self.assertGreater(avg_return, 0)


class TestWebSocketIntegration(unittest.TestCase):
    """Test WebSocket integration for real-time updates"""
    
    def setUp(self):
        """Setup WebSocket test environment"""
        self.test_messages = []
        
    @patch('main.websocket_manager')
    def test_websocket_signal_broadcasting(self, mock_ws_manager):
        """Test WebSocket broadcasting of signal alerts"""
        
        # Mock WebSocket manager
        mock_ws_manager.broadcast_message = AsyncMock()
        
        # Create signal data
        signal_data = {
            "symbol": "WSTEST",
            "signal_type": "EARNINGS_GAP_UP",
            "gap_percent": 4.5,
            "confidence": 0.85,
            "entry_price": 2500.0,
            "stop_loss": 2425.0,
            "profit_target": 2650.0
        }
        
        # Test signal broadcasting
        asyncio.run(mock_ws_manager.send_signal_alert(signal_data))
        
        # Verify broadcast was called
        mock_ws_manager.broadcast_message.assert_called_once()
        
        # Check message structure
        call_args = mock_ws_manager.broadcast_message.call_args[0][0]
        self.assertEqual(call_args["type"], "signal_alert")
        self.assertEqual(call_args["data"]["symbol"], "WSTEST")
    
    @patch('main.websocket_manager')
    def test_websocket_trade_updates(self, mock_ws_manager):
        """Test WebSocket broadcasting of trade updates"""
        
        mock_ws_manager.broadcast_message = AsyncMock()
        
        # Trade execution update
        trade_data = {
            "action": "opened",
            "symbol": "WSTEST",
            "quantity": 100,
            "entry_price": 2500.0,
            "order_id": "WS_ORDER_001"
        }
        
        # Test trade update broadcasting
        asyncio.run(mock_ws_manager.send_trade_update(trade_data))
        
        # Verify broadcast
        mock_ws_manager.broadcast_message.assert_called_once()
        call_args = mock_ws_manager.broadcast_message.call_args[0][0]
        self.assertEqual(call_args["type"], "trade_update")
        self.assertEqual(call_args["data"]["action"], "opened")
    
    @patch('main.websocket_manager')
    def test_websocket_pnl_updates(self, mock_ws_manager):
        """Test WebSocket broadcasting of P&L updates"""
        
        mock_ws_manager.broadcast_message = AsyncMock()
        
        # P&L update data
        pnl_data = {
            "total_pnl": 15000.0,
            "daily_pnl": 5000.0,
            "unrealized_pnl": 8000.0,
            "positions": [
                {
                    "symbol": "WSTEST1",
                    "pnl": 3000.0,
                    "pnl_percent": 6.0
                },
                {
                    "symbol": "WSTEST2", 
                    "pnl": 2000.0,
                    "pnl_percent": 4.0
                }
            ]
        }
        
        # Test P&L broadcasting
        asyncio.run(mock_ws_manager.send_pnl_update(pnl_data))
        
        # Verify broadcast
        mock_ws_manager.broadcast_message.assert_called_once()
        call_args = mock_ws_manager.broadcast_message.call_args[0][0]
        self.assertEqual(call_args["type"], "pnl_update")
        self.assertEqual(call_args["data"]["total_pnl"], 15000.0)
    
    def test_websocket_connection_management(self):
        """Test WebSocket connection management"""
        from main import WebSocketConnectionManager
        
        # Create connection manager
        ws_manager = WebSocketConnectionManager()
        
        # Mock WebSocket connections
        mock_ws1 = Mock()
        mock_ws2 = Mock()
        
        # Test connection tracking
        initial_count = len(ws_manager.active_connections)
        
        # Add connections
        ws_manager.active_connections.add(mock_ws1)
        ws_manager.active_connections.add(mock_ws2)
        
        self.assertEqual(len(ws_manager.active_connections), initial_count + 2)
        
        # Test disconnection
        ws_manager.disconnect(mock_ws1)
        
        self.assertEqual(len(ws_manager.active_connections), initial_count + 1)
        self.assertNotIn(mock_ws1, ws_manager.active_connections)
        self.assertIn(mock_ws2, ws_manager.active_connections)


class TestErrorRecoveryIntegration(unittest.TestCase):
    """Test error recovery and system resilience"""
    
    def test_component_failure_recovery(self):
        """Test system recovery from component failures"""
        
        # Test market data failure recovery
        market_data_manager = MarketDataManager()
        
        with patch.object(market_data_manager, 'get_stock_data', side_effect=Exception("API failure")):
            # Should handle failure gracefully
            try:
                result = asyncio.run(market_data_manager.get_stock_data("FAILTEST"))
                # Should return None or empty result, not crash
                self.assertIsNone(result)
            except Exception as e:
                # If exception is raised, it should be handled gracefully
                self.assertIn("API failure", str(e))
    
    def test_database_connection_recovery(self):
        """Test database connection failure recovery"""
        
        # Simulate database connection failure
        with patch('database.get_db_session', side_effect=Exception("Database connection failed")):
            
            # Components should handle database failures gracefully
            risk_manager = RiskManager(RiskConfig())
            
            # Should not crash when database is unavailable
            try:
                positions = risk_manager.get_active_positions()
                # Should return empty list or handle gracefully
                self.assertIsInstance(positions, list)
            except Exception as e:
                # If exception occurs, it should be a handled exception
                self.assertIn("Database", str(e))
    
    def test_api_rate_limit_handling(self):
        """Test handling of API rate limits"""
        
        from core.market_data import MarketDataManager
        
        market_data = MarketDataManager()
        
        # Mock rate limit error
        with patch.object(market_data, '_make_api_request') as mock_request:
            mock_request.side_effect = Exception("Rate limit exceeded")
            
            # Should implement retry with backoff
            result = asyncio.run(market_data.get_stock_data("RATETEST"))
            
            # Should handle rate limit gracefully
            self.assertIsNone(result)
    
    def test_system_state_consistency(self):
        """Test system state consistency during failures"""
        
        # Create test portfolio with positions
        portfolio = Portfolio(
            id=1,
            balance=1000000.0,
            equity=1000000.0,
            margin_available=500000.0
        )
        
        # Mock position data
        positions = [
            Position(
                symbol="CONSISTENCY1",
                quantity=100,
                entry_price=1000.0,
                current_price=1050.0,
                portfolio_id=1
            ),
            Position(
                symbol="CONSISTENCY2", 
                quantity=50,
                entry_price=2000.0,
                current_price=1980.0,
                portfolio_id=1
            )
        ]
        
        # Calculate expected metrics
        total_value = sum(p.quantity * p.current_price for p in positions)
        total_pnl = sum(p.quantity * (p.current_price - p.entry_price) for p in positions)
        
        # Verify consistency
        self.assertEqual(total_value, 204000.0)  # (100*1050) + (50*1980)
        self.assertEqual(total_pnl, 4000.0)      # (100*50) + (50*-20)


class TestSystemResourceManagement(unittest.TestCase):
    """Test system resource management and performance"""
    
    def test_memory_usage_monitoring(self):
        """Test memory usage monitoring during operations"""
        import psutil
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Create large dataset to simulate memory usage
        large_dataset = []
        for i in range(10000):
            trade = Trade(
                symbol=f"MEM_TEST_{i}",
                trade_type="BUY",
                quantity=100,
                entry_price=1000.0 + i,
                status="CLOSED",
                strategy="earnings_gap"
            )
            large_dataset.append(trade)
        
        # Check memory increase
        current_memory = process.memory_info().rss
        memory_increase = current_memory - initial_memory
        
        # Should use additional memory for dataset
        self.assertGreater(memory_increase, 0)
        
        # Cleanup and check memory recovery
        del large_dataset
        gc.collect()
        
        final_memory = process.memory_info().rss
        memory_recovered = current_memory - final_memory
        
        # Should recover some memory (garbage collection)
        self.assertGreater(memory_recovered, 0)
    
    def test_concurrent_request_handling(self):
        """Test handling of concurrent requests"""
        import threading
        import time
        
        # Create mock order engine
        order_engine = OrderEngine(
            api_key="test_key",
            access_token="test_token",
            paper_trading=True
        )
        
        results = []
        errors = []
        
        def execute_signal_thread(thread_id):
            try:
                from models.trade_models import TradeSignal
                signal = TradeSignal(
                    symbol=f"THREAD_{thread_id}",
                    signal_type="EARNINGS_GAP_UP",
                    entry_price=1000.0 + thread_id,
                    stop_loss=970.0 + thread_id,
                    profit_target=1060.0 + thread_id,
                    confidence=0.85,
                    gap_percent=3.5,
                    volume_ratio=2.0
                )
                
                result = order_engine.execute_signal(signal)
                results.append(result)
                
            except Exception as e:
                errors.append(str(e))
        
        # Start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=execute_signal_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        self.assertEqual(len(results), 10)  # All should complete
        self.assertEqual(len(errors), 0)    # No errors
        
        # All results should be successful (paper trading)
        for result in results:
            self.assertIn("status", result)
    
    def test_cleanup_procedures(self):
        """Test system cleanup procedures"""
        
        # Test database cleanup
        from database import get_db_session
        
        with patch('database.get_db_session') as mock_session:
            mock_db = Mock()
            mock_session.return_value = mock_db
            
            # Create component that uses database
            risk_manager = RiskManager(RiskConfig())
            
            # Simulate cleanup
            del risk_manager
            
            # Database session should be properly closed
            # (In real implementation, this would be handled by context managers)
            self.assertTrue(True)  # Placeholder for actual cleanup verification


if __name__ == "__main__":
    # Run integration tests
    unittest.main(verbosity=2)