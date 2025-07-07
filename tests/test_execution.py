"""
Tests for order execution and trade management
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from decimal import Decimal

from core.order_engine import OrderEngine, OrderStatus, OrderType, TransactionType
from core.market_data import MarketDataProvider
from core.telegram_service import TelegramService
from models.trade_models import Trade, Order, Position, Portfolio
from utils.validators import validate_order_params, validate_trading_config
from utils.encryption import encrypt_data, decrypt_data


class TestOrderExecution:
    """Test cases for order execution functionality"""
    
    @pytest.fixture
    def order_engine(self):
        """Create order engine instance for testing"""
        engine = OrderEngine()
        engine.paper_trading = True
        return engine
    
    @pytest.fixture
    def mock_portfolio(self):
        """Create mock portfolio for testing"""
        portfolio = Mock()
        portfolio.id = 1
        portfolio.balance = 100000.0
        portfolio.margin_available = 75000.0
        portfolio.margin_used = 25000.0
        return portfolio
    
    @pytest.fixture
    def sample_trade_params(self):
        """Sample trade parameters for testing"""
        return {
            "symbol": "RELIANCE",
            "quantity": 10,
            "entry_price": 2450.0,
            "stop_loss": 2400.0,
            "target_price": 2500.0,
            "trade_type": "BUY"
        }
    
    @pytest.mark.asyncio
    async def test_place_entry_order_paper_trading(self, order_engine, sample_trade_params):
        """Test placing entry order in paper trading mode"""
        # Create mock trade
        trade = Mock()
        trade.id = 1
        trade.symbol = sample_trade_params["symbol"]
        trade.trade_type = sample_trade_params["trade_type"]
        trade.quantity = sample_trade_params["quantity"]
        trade.entry_price = sample_trade_params["entry_price"]
        
        # Mock database
        order_engine.db = Mock()
        order_engine.db.add = Mock()
        order_engine.db.commit = Mock()
        
        success, message, order_id = await order_engine._place_entry_order(trade)
        
        assert success is True
        assert "Paper order placed" in message
        assert order_id is not None
        assert order_id.startswith("PAPER_")
    
    @pytest.mark.asyncio
    async def test_place_exit_orders(self, order_engine, sample_trade_params):
        """Test placing stop loss and target orders"""
        # Create mock trade
        trade = Mock()
        trade.id = 1
        trade.symbol = sample_trade_params["symbol"]
        trade.trade_type = sample_trade_params["trade_type"]
        trade.quantity = sample_trade_params["quantity"]
        trade.stop_loss = sample_trade_params["stop_loss"]
        trade.target_price = sample_trade_params["target_price"]
        
        # Mock database
        order_engine.db = Mock()
        order_engine.db.add_all = Mock()
        order_engine.db.commit = Mock()
        
        await order_engine._place_exit_orders(trade)
        
        # Verify that orders were created
        order_engine.db.add_all.assert_called_once()
        order_engine.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_order_status_market_order(self, order_engine):
        """Test updating status of market order"""
        # Create mock order
        order = Mock()
        order.id = 1
        order.order_id = "PAPER_123"
        order.symbol = "RELIANCE"
        order.order_type = "MARKET"
        order.transaction_type = "BUY"
        order.quantity = 10
        order.price = 2450.0
        order.status = "PENDING"
        
        # Mock current price
        with patch.object(order_engine, '_get_current_price', return_value=2445.0):
            with patch.object(order_engine, '_handle_order_completion') as mock_handle:
                order_engine.db = Mock()
                order_engine.db.commit = Mock()
                
                await order_engine._update_order_status(order)
                
                assert order.status == "COMPLETE"
                assert order.filled_quantity == 10
                assert order.average_price == 2445.0
                mock_handle.assert_called_once_with(order)
    
    @pytest.mark.asyncio
    async def test_update_order_status_limit_order(self, order_engine):
        """Test updating status of limit order"""
        # Create mock buy limit order
        order = Mock()
        order.id = 1
        order.order_type = "LIMIT"
        order.transaction_type = "BUY"
        order.price = 2450.0
        order.quantity = 10
        order.status = "PENDING"
        
        # Test price below limit (should execute)
        with patch.object(order_engine, '_get_current_price', return_value=2440.0):
            order_engine.db = Mock()
            order_engine.db.commit = Mock()
            
            await order_engine._update_order_status(order)
            
            assert order.status == "COMPLETE"
            assert order.average_price == 2450.0
    
    @pytest.mark.asyncio
    async def test_update_order_status_stop_loss(self, order_engine):
        """Test updating status of stop loss order"""
        # Create mock stop loss order
        order = Mock()
        order.id = 1
        order.order_type = "SL"
        order.transaction_type = "SELL"
        order.trigger_price = 2400.0
        order.quantity = 10
        order.status = "PENDING"
        
        # Test price below trigger (should execute)
        with patch.object(order_engine, '_get_current_price', return_value=2395.0):
            order_engine.db = Mock()
            order_engine.db.commit = Mock()
            
            await order_engine._update_order_status(order)
            
            assert order.status == "COMPLETE"
            assert order.average_price == 2395.0
    
    @pytest.mark.asyncio
    async def test_handle_order_completion_exit_order(self, order_engine):
        """Test handling completion of exit order"""
        # Create mock completed exit order
        order = Mock()
        order.trade_id = 1
        order.order_type = "SL"
        order.transaction_type = "SELL"
        order.average_price = 2395.0
        
        # Create mock trade
        mock_trade = Mock()
        mock_trade.id = 1
        mock_trade.trade_type = "BUY"
        mock_trade.entry_price = 2450.0
        mock_trade.quantity = 10
        
        # Mock database query
        order_engine.db = Mock()
        order_engine.db.query.return_value.filter.return_value.first.return_value = mock_trade
        order_engine.db.commit = Mock()
        
        with patch.object(order_engine, '_cancel_pending_orders') as mock_cancel:
            await order_engine._handle_order_completion(order)
            
            assert mock_trade.exit_price == 2395.0
            assert mock_trade.status == "CLOSED"
            assert mock_trade.pnl == -550.0  # (2395 - 2450) * 10
            mock_cancel.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_cancel_pending_orders(self, order_engine):
        """Test cancelling pending orders for a trade"""
        # Mock pending orders
        mock_orders = [Mock(), Mock()]
        for i, order in enumerate(mock_orders):
            order.order_id = f"ORDER_{i}"
            order.status = "PENDING"
        
        order_engine.db = Mock()
        order_engine.db.query.return_value.filter.return_value.all.return_value = mock_orders
        order_engine.db.commit = Mock()
        
        await order_engine._cancel_pending_orders(trade_id=1)
        
        for order in mock_orders:
            assert order.status == "CANCELLED"
        
        order_engine.db.commit.assert_called_once()


class TestMarketDataIntegration:
    """Test cases for market data integration"""
    
    @pytest.fixture
    def market_data(self):
        """Create market data provider instance"""
        return MarketDataProvider()
    
    @pytest.mark.asyncio
    async def test_price_subscription(self, market_data):
        """Test price update subscription mechanism"""
        received_updates = []
        
        async def price_callback(price_data):
            received_updates.append(price_data)
        
        # Subscribe to price updates
        market_data.subscribe_to_price_updates("RELIANCE", price_callback)
        
        # Simulate price update
        test_price_data = {
            "symbol": "RELIANCE",
            "price": 2450.0,
            "change": 25.0,
            "timestamp": datetime.now()
        }
        
        # Manually trigger callback (simulating websocket update)
        await price_callback(test_price_data)
        
        assert len(received_updates) == 1
        assert received_updates[0]["symbol"] == "RELIANCE"
        assert received_updates[0]["price"] == 2450.0
    
    @pytest.mark.asyncio
    async def test_market_status_detection(self, market_data):
        """Test market status detection"""
        status = await market_data.get_market_status()
        
        assert isinstance(status, dict)
        assert "is_open" in status
        assert isinstance(status["is_open"], bool)
    
    def test_price_caching(self, market_data):
        """Test price caching functionality"""
        test_price_data = {
            "symbol": "RELIANCE",
            "price": 2450.0,
            "timestamp": datetime.now()
        }
        
        # Cache price data
        market_data.price_cache["RELIANCE"] = test_price_data
        
        # Retrieve cached data
        cached_data = market_data.get_cached_price("RELIANCE")
        
        assert cached_data is not None
        assert cached_data["symbol"] == "RELIANCE"
        assert cached_data["price"] == 2450.0


class TestTelegramIntegration:
    """Test cases for Telegram bot integration"""
    
    @pytest.fixture
    def telegram_service(self):
        """Create Telegram service instance"""
        service = TelegramService()
        # Mock the bot to avoid actual API calls
        service.bot = Mock()
        service.authorized_users = ["123456789"]
        return service
    
    @pytest.mark.asyncio
    async def test_send_earnings_gap_alert(self, telegram_service):
        """Test sending earnings gap alert"""
        gap_data = {
            "symbol": "RELIANCE",
            "company_name": "Reliance Industries",
            "gap_percent": 4.2,
            "current_price": 2450.0,
            "pre_earnings_close": 2350.0,
            "post_earnings_open": 2450.0,
            "volume": 1500000,
            "volume_ratio": 2.5
        }
        
        with patch.object(telegram_service.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            success = await telegram_service.send_earnings_gap_alert(gap_data)
            
            assert success is True
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_trade_alert_entry(self, telegram_service):
        """Test sending trade entry alert"""
        trade_data = {
            "symbol": "RELIANCE",
            "trade_type": "BUY",
            "quantity": 10,
            "entry_price": 2450.0,
            "stop_loss": 2400.0,
            "target": 2500.0,
            "max_risk": 500.0,
            "trade_id": 1
        }
        
        with patch.object(telegram_service.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            success = await telegram_service.send_trade_alert(trade_data, "ENTRY")
            
            assert success is True
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_trade_alert_exit(self, telegram_service):
        """Test sending trade exit alert"""
        trade_data = {
            "symbol": "RELIANCE",
            "exit_price": 2480.0,
            "pnl": 300.0,
            "return_percent": 1.22,
            "duration": "45 minutes",
            "exit_reason": "Target Hit",
            "trade_id": 1
        }
        
        with patch.object(telegram_service.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            success = await telegram_service.send_trade_alert(trade_data, "EXIT")
            
            assert success is True
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_system_alert(self, telegram_service):
        """Test sending system alert"""
        with patch.object(telegram_service.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            success = await telegram_service.send_system_alert(
                "Trading system started successfully", 
                "SUCCESS"
            )
            
            assert success is True
            mock_send.assert_called_once()


class TestValidators:
    """Test cases for data validation utilities"""
    
    def test_validate_order_params_valid(self):
        """Test validation of valid order parameters"""
        order_params = {
            "symbol": "RELIANCE",
            "quantity": 10,
            "price": 2450.0,
            "order_type": "LIMIT",
            "transaction_type": "BUY"
        }
        
        is_valid, errors = validate_order_params(order_params)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_order_params_invalid_symbol(self):
        """Test validation with invalid symbol"""
        order_params = {
            "symbol": "INVALID_SYMBOL_123",
            "quantity": 10,
            "price": 2450.0
        }
        
        is_valid, errors = validate_order_params(order_params)
        
        assert is_valid is False
        assert any("Symbol" in error for error in errors)
    
    def test_validate_order_params_invalid_quantity(self):
        """Test validation with invalid quantity"""
        order_params = {
            "symbol": "RELIANCE",
            "quantity": -5,
            "price": 2450.0
        }
        
        is_valid, errors = validate_order_params(order_params)
        
        assert is_valid is False
        assert any("Quantity" in error for error in errors)
    
    def test_validate_trading_config_valid(self):
        """Test validation of valid trading configuration"""
        config = {
            "max_position_size": 10000.0,
            "risk_per_trade": 0.02,
            "stop_loss_percentage": 0.05,
            "target_percentage": 0.10,
            "max_daily_loss": 5000.0,
            "max_open_positions": 5
        }
        
        is_valid, errors = validate_trading_config(config)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_trading_config_invalid_risk(self):
        """Test validation with invalid risk parameters"""
        config = {
            "max_position_size": 10000.0,
            "risk_per_trade": 0.15,  # 15% - too high
            "stop_loss_percentage": 0.05,
            "target_percentage": 0.10,
            "max_daily_loss": 5000.0,
            "max_open_positions": 5
        }
        
        is_valid, errors = validate_trading_config(config)
        
        assert is_valid is False
        assert any("Risk per trade" in error for error in errors)


class TestEncryption:
    """Test cases for encryption utilities"""
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test encryption and decryption roundtrip"""
        from utils.encryption import generate_key
        
        # Generate test key
        key = generate_key()
        test_data = "sensitive_api_key_12345"
        
        # Encrypt data
        encrypted = encrypt_data(test_data, key)
        
        # Verify encryption changed the data
        assert encrypted != test_data
        assert len(encrypted) > len(test_data)
        
        # Decrypt data
        decrypted = decrypt_data(encrypted, key)
        
        # Verify roundtrip
        assert decrypted == test_data
    
    def test_encrypt_credentials(self):
        """Test encrypting credentials dictionary"""
        from utils.encryption import encrypt_credentials, decrypt_credentials, generate_key
        
        key = generate_key()
        credentials = {
            "api_key": "secret_key_123",
            "api_secret": "secret_secret_456",
            "username": "testuser"
        }
        
        # Encrypt credentials
        encrypted_creds = encrypt_credentials(credentials, key)
        
        # Verify sensitive fields are encrypted
        assert encrypted_creds["api_key"] != credentials["api_key"]
        assert encrypted_creds["api_secret"] != credentials["api_secret"]
        assert encrypted_creds["username"] == credentials["username"]  # Non-sensitive
        
        # Decrypt credentials
        decrypted_creds = decrypt_credentials(encrypted_creds, key)
        
        # Verify decryption
        assert decrypted_creds["api_key"] == credentials["api_key"]
        assert decrypted_creds["api_secret"] == credentials["api_secret"]
    
    def test_mask_sensitive_data(self):
        """Test masking sensitive data for display"""
        from utils.encryption import mask_sensitive_data
        
        sensitive_data = "1234567890abcdef"
        masked = mask_sensitive_data(sensitive_data, show_chars=4)
        
        assert masked == "1234********cdef"
        assert len(masked) == len(sensitive_data)


class TestErrorHandling:
    """Test cases for error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_order_execution_with_api_error(self):
        """Test order execution when API throws error"""
        order_engine = OrderEngine()
        order_engine.paper_trading = False  # Test live mode
        order_engine.kite = Mock()
        
        # Mock API error
        order_engine.kite.place_order.side_effect = Exception("API Error")
        
        trade = Mock()
        trade.id = 1
        trade.symbol = "RELIANCE"
        trade.trade_type = "BUY"
        trade.quantity = 10
        trade.entry_price = 2450.0
        
        order_engine.db = Mock()
        
        success, message, order_id = await order_engine._place_entry_order(trade)
        
        assert success is False
        assert "API Error" in message
        assert order_id is None
    
    @pytest.mark.asyncio
    async def test_market_data_network_error(self):
        """Test market data handling with network error"""
        market_data = MarketDataProvider()
        
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.side_effect = Exception("Network Error")
            
            price_data = await market_data.get_real_time_price("RELIANCE")
            
            assert price_data is None
    
    @pytest.mark.asyncio
    async def test_telegram_send_error(self):
        """Test Telegram service error handling"""
        telegram_service = TelegramService()
        telegram_service.bot = Mock()
        telegram_service.authorized_users = ["123456789"]
        
        # Mock send error
        telegram_service.bot.send_message = AsyncMock(side_effect=Exception("Send Error"))
        
        gap_data = {"symbol": "RELIANCE", "gap_percent": 4.2}
        success = await telegram_service.send_earnings_gap_alert(gap_data)
        
        assert success is False


class TestConcurrency:
    """Test cases for concurrent operations"""
    
    @pytest.mark.asyncio
    async def test_concurrent_order_updates(self):
        """Test concurrent order status updates"""
        order_engine = OrderEngine()
        order_engine.paper_trading = True
        order_engine.db = Mock()
        order_engine.db.commit = Mock()
        
        # Create multiple mock orders
        orders = []
        for i in range(5):
            order = Mock()
            order.id = i
            order.order_id = f"ORDER_{i}"
            order.symbol = "RELIANCE"
            order.order_type = "MARKET"
            order.status = "PENDING"
            order.quantity = 10
            orders.append(order)
        
        with patch.object(order_engine, '_get_current_price', return_value=2450.0):
            # Update orders concurrently
            tasks = [order_engine._update_order_status(order) for order in orders]
            await asyncio.gather(*tasks)
            
            # Verify all orders were processed
            for order in orders:
                assert order.status == "COMPLETE"
    
    @pytest.mark.asyncio
    async def test_concurrent_price_updates(self):
        """Test concurrent price update subscriptions"""
        market_data = MarketDataProvider()
        
        received_updates = {}
        
        async def create_callback(symbol):
            async def callback(price_data):
                received_updates[symbol] = price_data
            return callback
        
        # Subscribe multiple symbols
        symbols = ["RELIANCE", "TCS", "INFY", "HDFC"]
        for symbol in symbols:
            callback = await create_callback(symbol)
            market_data.subscribe_to_price_updates(symbol, callback)
        
        # Simulate concurrent price updates
        tasks = []
        for symbol in symbols:
            price_data = {
                "symbol": symbol,
                "price": 2450.0 + len(symbol),  # Different prices
                "timestamp": datetime.now()
            }
            # Get all callbacks for this symbol
            callbacks = market_data.subscriptions.get(symbol, [])
            for callback in callbacks:
                tasks.append(callback(price_data))
        
        await asyncio.gather(*tasks)
        
        # Verify all updates were received
        assert len(received_updates) == len(symbols)
        for symbol in symbols:
            assert symbol in received_updates
            assert received_updates[symbol]["symbol"] == symbol


if __name__ == "__main__":
    pytest.main([__file__, "-v"])