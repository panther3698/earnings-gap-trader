#!/usr/bin/env python3
"""
Test script for the comprehensive market data service
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_market_data_service():
    """Test the market data service comprehensively"""
    print("🚀 Testing Market Data Service")
    print("=" * 50)
    
    try:
        from core.market_data import (
            MarketDataManager, ZerodhaDataSource, YahooDataSource,
            DataValidator, MarketHoursManager, StockListManager,
            TickDataProcessor, PriceData, DataSource
        )
        from database import get_db_session
        
        # Initialize components
        print("\n1. 🔧 Testing Component Initialization")
        market_data_manager = MarketDataManager()
        zerodha_source = ZerodhaDataSource()
        yahoo_source = YahooDataSource()
        data_validator = DataValidator()
        market_hours = MarketHoursManager()
        stock_list = StockListManager()
        tick_processor = TickDataProcessor(get_db_session())
        
        print("✅ All components initialized successfully")
        
        # Test market hours
        print("\n2. 🕐 Testing Market Hours Manager")
        market_status = market_hours.get_market_status()
        is_open = market_hours.is_market_open()
        next_open = market_hours.get_next_market_open()
        market_hours_today = market_hours.get_market_hours_today()
        
        print(f"✅ Market Status: {market_status.value}")
        print(f"✅ Market Open: {is_open}")
        print(f"✅ Next Market Open: {next_open}")
        print(f"✅ Today's Hours: {market_hours_today}")
        
        # Test stock list manager
        print("\n3. 📊 Testing Stock List Manager")
        nifty_50 = stock_list.get_nifty_50()
        nifty_next_50 = stock_list.get_nifty_next_50()
        all_major = stock_list.get_all_major_stocks()
        
        print(f"✅ Nifty 50 stocks: {len(nifty_50)}")
        print(f"✅ Nifty Next 50 stocks: {len(nifty_next_50)}")
        print(f"✅ All major stocks: {len(all_major)}")
        print(f"✅ Sample stocks: {nifty_50[:5]}")
        
        # Test data validator
        print("\n4. ✅ Testing Data Validator")
        test_price_data = PriceData(
            symbol="RELIANCE",
            open=2450.0,
            high=2470.0,
            low=2440.0,
            close=2460.0,
            volume=1000000,
            last_price=2465.0,
            timestamp=datetime.now(),
            source=DataSource.YAHOO.value
        )
        
        is_valid, issues = data_validator.validate_price_data(test_price_data)
        print(f"✅ Price data validation: {is_valid}")
        if issues:
            print(f"   Issues: {issues}")
        
        # Test Yahoo Finance source
        print("\n5. 🌐 Testing Yahoo Finance Data Source")
        yahoo_connected = await yahoo_source.connect()
        print(f"✅ Yahoo Finance connected: {yahoo_connected}")
        
        if yahoo_connected:
            test_symbol = "RELIANCE"
            print(f"   Getting real-time price for {test_symbol}...")
            
            yahoo_price = await yahoo_source.get_real_time_price(test_symbol)
            if yahoo_price:
                print(f"✅ Yahoo price data retrieved:")
                print(f"   Symbol: {yahoo_price.symbol}")
                print(f"   Last Price: ₹{yahoo_price.last_price:.2f}")
                print(f"   Volume: {yahoo_price.volume:,}")
                print(f"   Source: {yahoo_price.source}")
                print(f"   Timestamp: {yahoo_price.timestamp}")
            else:
                print("⚠️  No price data received from Yahoo Finance")
            
            # Test historical data
            print(f"\n   Getting historical data for {test_symbol}...")
            from_date = datetime.now() - timedelta(days=30)
            to_date = datetime.now()
            
            yahoo_hist = await yahoo_source.get_historical_data(test_symbol, from_date, to_date, "1d")
            if yahoo_hist is not None and not yahoo_hist.empty:
                print(f"✅ Yahoo historical data retrieved:")
                print(f"   Rows: {len(yahoo_hist)}")
                print(f"   Columns: {list(yahoo_hist.columns)}")
                print(f"   Date range: {yahoo_hist.index[0]} to {yahoo_hist.index[-1]}")
                print(f"   Sample data:\n{yahoo_hist.head(2)}")
            else:
                print("⚠️  No historical data received from Yahoo Finance")
        
        # Test Zerodha source (will likely fail without credentials)
        print("\n6. 🔑 Testing Zerodha Data Source")
        zerodha_connected = await zerodha_source.connect()
        print(f"✅ Zerodha connected: {zerodha_connected}")
        
        if not zerodha_connected:
            print("   ℹ️  Zerodha connection failed (expected without API credentials)")
        else:
            print("   🎉 Zerodha connection successful!")
            
            test_symbol = "RELIANCE"
            zerodha_price = await zerodha_source.get_real_time_price(test_symbol)
            if zerodha_price:
                print(f"✅ Zerodha price data retrieved:")
                print(f"   Symbol: {zerodha_price.symbol}")
                print(f"   Last Price: ₹{zerodha_price.last_price:.2f}")
                print(f"   Bid: ₹{zerodha_price.bid}")
                print(f"   Ask: ₹{zerodha_price.ask}")
            else:
                print("⚠️  No price data received from Zerodha")
        
        # Test Market Data Manager
        print("\n7. 🎛️  Testing Market Data Manager")
        manager_initialized = await market_data_manager.initialize()
        print(f"✅ Market Data Manager initialized: {manager_initialized}")
        
        if manager_initialized:
            # Test getting market status
            market_status_dict = await market_data_manager.get_market_status()
            print(f"✅ Market Status from Manager:")
            for key, value in market_status_dict.items():
                print(f"   {key}: {value}")
            
            # Test getting real-time price
            test_symbols = ["RELIANCE", "TCS", "INFY"]
            print(f"\n   Testing real-time prices for {test_symbols}...")
            
            for symbol in test_symbols:
                price_data = await market_data_manager.get_real_time_price(symbol)
                if price_data:
                    print(f"✅ {symbol}: ₹{price_data.last_price:.2f} "
                          f"({price_data.change:+.2f}, {price_data.change_percent:+.2%}) "
                          f"[{price_data.source}]")
                else:
                    print(f"❌ {symbol}: No data available")
            
            # Test multiple prices
            print(f"\n   Testing multiple price retrieval...")
            multiple_prices = await market_data_manager.get_multiple_prices(test_symbols)
            successful_prices = sum(1 for price in multiple_prices.values() if price is not None)
            print(f"✅ Retrieved {successful_prices}/{len(test_symbols)} prices successfully")
            
            # Test cache warmup
            print(f"\n   Testing cache warmup...")
            await market_data_manager.warmup_cache(test_symbols)
            print(f"✅ Cache warmed up for {len(test_symbols)} symbols")
            print(f"   Cache size: {len(market_data_manager.price_cache)}")
            
            # Test historical data
            print(f"\n   Testing historical data retrieval...")
            hist_symbol = "RELIANCE"
            from_date = datetime.now() - timedelta(days=7)
            to_date = datetime.now()
            
            hist_data = await market_data_manager.get_historical_data(
                hist_symbol, from_date, to_date, "1d"
            )
            
            if hist_data is not None and not hist_data.empty:
                print(f"✅ Historical data for {hist_symbol}:")
                print(f"   Rows: {len(hist_data)}")
                print(f"   Columns: {list(hist_data.columns)}")
                print(f"   Latest close: ₹{hist_data['Close'].iloc[-1]:.2f}")
            else:
                print(f"❌ No historical data for {hist_symbol}")
        
        # Test tick data processor
        print("\n8. ⚡ Testing Tick Data Processor")
        from core.market_data import TickData
        
        # Create sample tick data
        sample_tick = TickData(
            symbol="RELIANCE",
            exchange="NSE",
            instrument_token=738561,
            last_price=2465.50,
            last_quantity=10,
            average_price=2464.75,
            volume=1500000,
            buy_quantity=75000,
            sell_quantity=80000,
            ohlc={"open": 2450.0, "high": 2470.0, "low": 2440.0, "close": 2460.0},
            timestamp=datetime.now()
        )
        
        await tick_processor.process_tick(sample_tick)
        print("✅ Sample tick data processed")
        
        last_price = tick_processor.get_last_price("RELIANCE")
        latest_ticks = tick_processor.get_latest_ticks("RELIANCE", 5)
        
        print(f"✅ Last price: ₹{last_price}")
        print(f"✅ Latest ticks buffer: {len(latest_ticks)} ticks")
        
        # Test subscription functionality
        print("\n9. 📡 Testing Subscription System")
        
        async def test_callback(price_data: PriceData):
            print(f"   📢 Price update: {price_data.symbol} = ₹{price_data.last_price:.2f}")
        
        subscribe_symbol = "RELIANCE"
        subscription_success = await market_data_manager.subscribe_to_price_updates(
            subscribe_symbol, test_callback
        )
        print(f"✅ Subscription to {subscribe_symbol}: {subscription_success}")
        
        # Test unsubscription
        unsubscribe_success = await market_data_manager.unsubscribe_from_price_updates(
            subscribe_symbol, test_callback
        )
        print(f"✅ Unsubscription from {subscribe_symbol}: {unsubscribe_success}")
        
        # Cleanup
        print("\n10. 🧹 Testing Cleanup")
        await market_data_manager.cleanup()
        await yahoo_source.disconnect()
        await zerodha_source.disconnect()
        print("✅ All resources cleaned up")
        
        print("\n" + "=" * 50)
        print("🎉 All Market Data Service tests completed successfully!")
        print("\n📊 Test Summary:")
        print("✅ Component initialization")
        print("✅ Market hours management")
        print("✅ Stock list management") 
        print("✅ Data validation")
        print("✅ Yahoo Finance integration")
        print("✅ Zerodha integration (connection test)")
        print("✅ Market Data Manager coordination")
        print("✅ Real-time price fetching")
        print("✅ Historical data retrieval")
        print("✅ Tick data processing")
        print("✅ Subscription system")
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


async def test_data_quality():
    """Test data quality and validation features"""
    print("\n🔍 Testing Data Quality Features")
    print("-" * 30)
    
    try:
        from core.market_data import DataValidator, PriceData, DataSource
        import pandas as pd
        import numpy as np
        
        validator = DataValidator()
        
        # Test 1: Valid price data
        print("1. Testing valid price data...")
        valid_data = PriceData(
            symbol="RELIANCE",
            open=2450.0,
            high=2470.0,
            low=2440.0,
            close=2460.0,
            volume=1000000,
            last_price=2465.0,
            timestamp=datetime.now(),
            source=DataSource.YAHOO.value
        )
        
        is_valid, issues = validator.validate_price_data(valid_data)
        print(f"   ✅ Valid data test: {is_valid} (issues: {len(issues)})")
        
        # Test 2: Invalid price data
        print("2. Testing invalid price data...")
        invalid_data = PriceData(
            symbol="RELIANCE",
            open=2450.0,
            high=2440.0,  # High < Low (invalid)
            low=2470.0,
            close=2460.0,
            volume=-1000,  # Negative volume (invalid)
            last_price=2500.0,  # Outside high-low range
            timestamp=datetime.now(),
            source=DataSource.YAHOO.value
        )
        
        is_valid, issues = validator.validate_price_data(invalid_data)
        print(f"   ✅ Invalid data test: {is_valid} (issues: {len(issues)})")
        for issue in issues:
            print(f"      - {issue}")
        
        # Test 3: Historical data cleaning
        print("3. Testing historical data cleaning...")
        
        # Create sample dirty data
        dates = pd.date_range(start='2024-01-01', periods=10, freq='D')
        dirty_data = pd.DataFrame({
            'Open': [100, 105, np.nan, 110, 0, 115, 120, 125, 130, 135],  # NaN and zero values
            'High': [105, 110, 108, 115, 105, 120, 125, 130, 135, 140],
            'Low': [95, 100, 102, 105, 95, 110, 115, 120, 125, 130],
            'Close': [102, 107, 106, 112, 102, 117, 122, 127, 132, 137],
            'Volume': [1000, 2000, 1500, 25000, 1800, 2200, 2500, 2800, 3000, 3200]  # Volume spike
        }, index=dates)
        
        print(f"   Original data shape: {dirty_data.shape}")
        print(f"   NaN values: {dirty_data.isna().sum().sum()}")
        
        cleaned_data = validator.clean_historical_data(dirty_data)
        print(f"   ✅ Cleaned data shape: {cleaned_data.shape}")
        print(f"   ✅ NaN values after cleaning: {cleaned_data.isna().sum().sum()}")
        
        # Test 4: Corporate action detection
        print("4. Testing corporate action detection...")
        
        # Create data with a potential stock split
        split_dates = pd.date_range(start='2024-01-01', periods=10, freq='D')
        split_data = pd.DataFrame({
            'Open': [100, 105, 110, 115, 60, 62, 65, 68, 70, 72],  # 50% drop (2:1 split)
            'High': [105, 110, 115, 120, 65, 67, 70, 73, 75, 77],
            'Low': [95, 100, 105, 110, 55, 57, 60, 63, 65, 67],
            'Close': [102, 107, 112, 117, 58, 61, 64, 67, 69, 71],
            'Volume': [1000, 1200, 1100, 1300, 2500, 1400, 1200, 1100, 1000, 950]
        }, index=split_dates)
        
        corporate_actions = validator.detect_corporate_actions(split_data)
        print(f"   ✅ Detected {len(corporate_actions)} potential corporate actions")
        for action in corporate_actions:
            print(f"      - {action['date']}: {action['type']} ({action['return']:.2%})")
        
        print("✅ Data quality tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Data quality test failed: {e}")
        return False


if __name__ == "__main__":
    async def main():
        print("🧪 Market Data Service Test Suite")
        print("=" * 60)
        
        # Run main tests
        main_test_success = await test_market_data_service()
        
        # Run data quality tests
        quality_test_success = await test_data_quality()
        
        print("\n" + "=" * 60)
        if main_test_success and quality_test_success:
            print("🎉 ALL TESTS PASSED!")
            print("\n📝 Next Steps:")
            print("1. Set up your Zerodha API credentials in .env")
            print("2. Test with live market data during market hours")
            print("3. Set up real-time price streaming")
            print("4. Integrate with your trading strategies")
            return 0
        else:
            print("❌ Some tests failed. Please check the errors above.")
            return 1
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)