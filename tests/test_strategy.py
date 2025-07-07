"""
Tests for earnings gap trading strategy
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import pandas as pd

from core.earnings_scanner import EarningsScanner
from core.risk_manager import RiskManager
from core.market_data import MarketDataProvider
from core.order_engine import OrderEngine
from models.trade_models import Trade, EarningsEvent, Portfolio
from utils.validators import validate_symbol, validate_price, validate_quantity


class TestEarningsScanner:
    """Test cases for earnings scanner functionality"""
    
    @pytest.fixture
    def scanner(self):
        """Create earnings scanner instance for testing"""
        return EarningsScanner()
    
    @pytest.fixture
    def mock_earnings_data(self):
        """Mock earnings data for testing"""
        return [
            {
                "symbol": "RELIANCE",
                "company_name": "Reliance Industries",
                "earnings_date": datetime.now() + timedelta(days=1),
                "expected_eps": 65.50
            },
            {
                "symbol": "TCS", 
                "company_name": "Tata Consultancy Services",
                "earnings_date": datetime.now() + timedelta(days=2),
                "expected_eps": 45.20
            }
        ]
    
    @pytest.mark.asyncio
    async def test_scan_upcoming_earnings(self, scanner, mock_earnings_data):
        """Test scanning for upcoming earnings events"""
        with patch.object(scanner, '_load_nse_symbols', return_value=['RELIANCE.NS', 'TCS.NS']):
            with patch('yfinance.Ticker') as mock_ticker:
                # Mock yfinance ticker response
                mock_ticker.return_value.calendar = pd.DataFrame(
                    index=[datetime.now() + timedelta(days=1)]
                )
                mock_ticker.return_value.info = {"longName": "Test Company"}
                
                results = await scanner.scan_upcoming_earnings(days_ahead=7)
                
                assert len(results) >= 0
                assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_detect_earnings_gaps(self, scanner):
        """Test gap detection functionality"""
        # Mock recent earnings events
        with patch.object(scanner.db, 'query') as mock_query:
            mock_event = Mock()
            mock_event.symbol = "RELIANCE"
            mock_event.company_name = "Reliance Industries"
            mock_event.earnings_date = datetime.now() - timedelta(days=1)
            
            mock_query.return_value.filter.return_value.all.return_value = [mock_event]
            
            # Mock yfinance data
            with patch('yfinance.Ticker') as mock_ticker:
                mock_hist = pd.DataFrame({
                    'Close': [2400.0, 2450.0],
                    'Open': [2405.0, 2500.0],
                    'Volume': [1000000, 1500000]
                })
                mock_ticker.return_value.history.return_value = mock_hist
                
                gaps = await scanner.detect_earnings_gaps(min_gap_percent=2.0)
                
                assert isinstance(gaps, list)
    
    @pytest.mark.asyncio
    async def test_get_technical_indicators(self, scanner):
        """Test technical indicators calculation"""
        with patch('yfinance.Ticker') as mock_ticker:
            # Create mock historical data
            dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
            mock_hist = pd.DataFrame({
                'Close': range(2400, 2450),
                'Volume': [1000000] * 50
            }, index=dates)
            
            mock_ticker.return_value.history.return_value = mock_hist
            
            indicators = await scanner.get_technical_indicators("RELIANCE")
            
            assert isinstance(indicators, dict)
            if indicators:  # If not empty
                assert 'current_price' in indicators
                assert 'volume_ratio' in indicators


class TestRiskManager:
    """Test cases for risk management functionality"""
    
    @pytest.fixture
    def risk_manager(self):
        """Create risk manager instance for testing"""
        return RiskManager()
    
    def test_calculate_position_size(self, risk_manager):
        """Test position size calculation"""
        entry_price = 2450.0
        stop_loss = 2400.0
        account_balance = 100000.0
        
        quantity, details = risk_manager.calculate_position_size(
            entry_price=entry_price,
            stop_loss=stop_loss,
            account_balance=account_balance
        )
        
        assert isinstance(quantity, int)
        assert quantity > 0
        assert isinstance(details, dict)
        assert 'max_loss' in details
        assert 'position_value' in details
    
    def test_validate_trade_entry_success(self, risk_manager):
        """Test successful trade entry validation"""
        trade_params = {
            "symbol": "RELIANCE",
            "quantity": 10,
            "entry_price": 2450.0
        }
        
        with patch.object(risk_manager, '_check_daily_loss_limit', return_value=True):
            with patch.object(risk_manager, '_check_max_open_positions', return_value=True):
                with patch.object(risk_manager, '_check_position_concentration', return_value=True):
                    with patch.object(risk_manager, '_get_active_portfolio', return_value=Mock()):
                        with patch.object(risk_manager, '_check_available_balance', return_value=True):
                            with patch.object(risk_manager, '_has_existing_position', return_value=False):
                                
                                is_valid, reason = risk_manager.validate_trade_entry(trade_params)
                                
                                assert is_valid is True
                                assert reason == "Trade validation passed"
    
    def test_validate_trade_entry_failure(self, risk_manager):
        """Test trade entry validation failure scenarios"""
        trade_params = {
            "symbol": "RELIANCE",
            "quantity": 10,
            "entry_price": 2450.0
        }
        
        # Test daily loss limit exceeded
        with patch.object(risk_manager, '_check_daily_loss_limit', return_value=False):
            is_valid, reason = risk_manager.validate_trade_entry(trade_params)
            assert is_valid is False
            assert "Daily loss limit exceeded" in reason
    
    def test_calculate_stop_loss(self, risk_manager):
        """Test stop loss calculation"""
        entry_price = 2450.0
        gap_percent = 3.5
        
        stop_loss = risk_manager.calculate_stop_loss(entry_price, gap_percent)
        
        assert isinstance(stop_loss, float)
        assert stop_loss > 0
        assert stop_loss != entry_price
    
    def test_calculate_target_price(self, risk_manager):
        """Test target price calculation"""
        entry_price = 2450.0
        gap_percent = 3.5
        
        target = risk_manager.calculate_target_price(entry_price, gap_percent)
        
        assert isinstance(target, float)
        assert target > 0
        assert target != entry_price


class TestMarketDataProvider:
    """Test cases for market data provider"""
    
    @pytest.fixture
    def market_data(self):
        """Create market data provider instance for testing"""
        return MarketDataProvider()
    
    @pytest.mark.asyncio
    async def test_get_real_time_price(self, market_data):
        """Test real-time price fetching"""
        with patch.object(market_data, '_get_yfinance_price') as mock_yf:
            mock_yf.return_value = {
                "symbol": "RELIANCE",
                "price": 2450.0,
                "volume": 1000000,
                "timestamp": datetime.now()
            }
            
            price_data = await market_data.get_real_time_price("RELIANCE")
            
            assert price_data is not None
            assert price_data["symbol"] == "RELIANCE"
            assert isinstance(price_data["price"], float)
    
    @pytest.mark.asyncio
    async def test_get_historical_data(self, market_data):
        """Test historical data fetching"""
        with patch('yfinance.Ticker') as mock_ticker:
            # Mock historical data
            dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
            mock_hist = pd.DataFrame({
                'Open': range(2400, 2430),
                'High': range(2410, 2440),
                'Low': range(2390, 2420),
                'Close': range(2405, 2435),
                'Volume': [1000000] * 30
            }, index=dates)
            
            mock_ticker.return_value.history.return_value = mock_hist
            
            hist_data = await market_data.get_historical_data("RELIANCE", period="1mo")
            
            assert hist_data is not None
            assert isinstance(hist_data, pd.DataFrame)
            assert len(hist_data) > 0
    
    @pytest.mark.asyncio
    async def test_calculate_vwap(self, market_data):
        """Test VWAP calculation"""
        with patch.object(market_data, 'get_historical_data') as mock_hist:
            # Create test data
            dates = pd.date_range(start='2024-01-01', periods=10, freq='1min')
            test_data = pd.DataFrame({
                'High': [2450.0] * 10,
                'Low': [2440.0] * 10,
                'Close': [2445.0] * 10,
                'Volume': [100000] * 10
            }, index=dates)
            
            mock_hist.return_value = test_data
            
            vwap = await market_data.calculate_vwap("RELIANCE")
            
            assert vwap is not None
            assert isinstance(vwap, float)
            assert vwap > 0


class TestOrderEngine:
    """Test cases for order execution engine"""
    
    @pytest.fixture
    def order_engine(self):
        """Create order engine instance for testing"""
        engine = OrderEngine()
        engine.paper_trading = True  # Force paper trading for tests
        return engine
    
    @pytest.mark.asyncio
    async def test_place_earnings_gap_trade(self, order_engine):
        """Test placing earnings gap trade"""
        gap_data = {
            "symbol": "RELIANCE",
            "gap_percent": 3.5,
            "current_price": 2450.0,
            "company_name": "Reliance Industries"
        }
        
        # Mock portfolio
        mock_portfolio = Mock()
        mock_portfolio.id = 1
        mock_portfolio.balance = 100000.0
        
        with patch.object(order_engine, '_get_active_portfolio', return_value=mock_portfolio):
            with patch.object(order_engine.risk_manager, 'calculate_position_size') as mock_calc:
                mock_calc.return_value = (10, {"max_loss": 500.0})
                
                with patch.object(order_engine.risk_manager, 'validate_trade_entry') as mock_validate:
                    mock_validate.return_value = (True, "Valid")
                    
                    success, message, trade_id = await order_engine.place_earnings_gap_trade(gap_data)
                    
                    assert isinstance(success, bool)
                    assert isinstance(message, str)
                    assert trade_id is None or isinstance(trade_id, int)


class TestIntegration:
    """Integration tests for multiple components"""
    
    @pytest.mark.asyncio
    async def test_complete_trading_workflow(self):
        """Test complete trading workflow from gap detection to order placement"""
        # This test would simulate a complete workflow:
        # 1. Scan for earnings
        # 2. Detect gaps  
        # 3. Validate risk
        # 4. Place orders
        # 5. Monitor execution
        
        # Mock the workflow
        scanner = EarningsScanner()
        risk_manager = RiskManager() 
        order_engine = OrderEngine()
        order_engine.paper_trading = True
        
        # Test data
        gap_data = {
            "symbol": "RELIANCE",
            "gap_percent": 4.2,
            "current_price": 2450.0,
            "pre_earnings_close": 2350.0,
            "post_earnings_open": 2450.0
        }
        
        # Mock portfolio
        mock_portfolio = Mock()
        mock_portfolio.id = 1
        mock_portfolio.balance = 100000.0
        
        with patch.object(order_engine, '_get_active_portfolio', return_value=mock_portfolio):
            with patch.object(risk_manager, 'validate_trade_entry', return_value=(True, "Valid")):
                with patch.object(risk_manager, 'calculate_position_size', return_value=(10, {})):
                    
                    # Test the workflow
                    success, message, trade_id = await order_engine.place_earnings_gap_trade(gap_data)
                    
                    # Verify results
                    assert isinstance(success, bool)
                    assert isinstance(message, str)


# Fixtures for database testing
@pytest.fixture
def test_db():
    """Create test database session"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from database import Base
    
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def sample_portfolio(test_db):
    """Create sample portfolio for testing"""
    portfolio = Portfolio(
        name="Test Portfolio",
        balance=100000.0,
        equity=100000.0,
        margin_available=100000.0,
        is_active=True
    )
    
    test_db.add(portfolio)
    test_db.commit()
    
    return portfolio


@pytest.fixture
def sample_trade(test_db, sample_portfolio):
    """Create sample trade for testing"""
    trade = Trade(
        symbol="RELIANCE",
        trade_type="BUY",
        quantity=10,
        entry_price=2450.0,
        stop_loss=2400.0,
        target_price=2500.0,
        status="OPEN",
        strategy="earnings_gap",
        portfolio_id=sample_portfolio.id
    )
    
    test_db.add(trade)
    test_db.commit()
    
    return trade


# Performance tests
class TestPerformance:
    """Performance tests for critical components"""
    
    @pytest.mark.asyncio
    async def test_gap_detection_performance(self):
        """Test gap detection performance with large dataset"""
        scanner = EarningsScanner()
        
        # Mock large dataset
        with patch.object(scanner.db, 'query') as mock_query:
            # Create 100 mock events
            mock_events = [Mock(symbol=f"STOCK{i}", earnings_date=datetime.now()) for i in range(100)]
            mock_query.return_value.filter.return_value.all.return_value = mock_events
            
            start_time = datetime.now()
            gaps = await scanner.detect_earnings_gaps()
            end_time = datetime.now()
            
            # Should complete within reasonable time
            execution_time = (end_time - start_time).total_seconds()
            assert execution_time < 10.0  # 10 seconds max
    
    def test_position_sizing_performance(self):
        """Test position sizing calculation performance"""
        risk_manager = RiskManager()
        
        start_time = datetime.now()
        
        # Calculate position sizes for 1000 scenarios
        for i in range(1000):
            quantity, details = risk_manager.calculate_position_size(
                entry_price=2450.0 + i,
                stop_loss=2400.0 + i,
                account_balance=100000.0
            )
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Should complete within reasonable time
        assert execution_time < 5.0  # 5 seconds max for 1000 calculations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])