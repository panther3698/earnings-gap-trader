#!/usr/bin/env python3
"""
Example usage of the Market Data Service
This demonstrates how to integrate the market data service into your trading application
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def example_basic_usage():
    """Example: Basic market data usage"""
    print("📊 Example 1: Basic Market Data Usage")
    print("-" * 40)
    
    from core.market_data import market_data_manager
    
    # Initialize the market data manager
    await market_data_manager.initialize()
    
    # Get real-time price for a single stock
    symbol = "RELIANCE"
    price_data = await market_data_manager.get_real_time_price(symbol)
    
    if price_data:
        print(f"💰 {symbol} Current Price: ₹{price_data.last_price:.2f}")
        print(f"   Change: ₹{price_data.change:+.2f} ({price_data.change_percent:+.2%})")
        print(f"   Volume: {price_data.volume:,}")
        print(f"   Source: {price_data.source}")
    
    # Get prices for multiple stocks
    symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK"]
    prices = await market_data_manager.get_multiple_prices(symbols)
    
    print(f"\n📈 Multiple Stock Prices:")
    for symbol, price_data in prices.items():
        if price_data:
            print(f"   {symbol}: ₹{price_data.last_price:.2f} ({price_data.change_percent:+.2%})")
        else:
            print(f"   {symbol}: No data available")
    
    await market_data_manager.cleanup()


async def example_real_time_streaming():
    """Example: Real-time price streaming"""
    print("\n📡 Example 2: Real-time Price Streaming")
    print("-" * 40)
    
    from core.market_data import market_data_manager, PriceData
    
    await market_data_manager.initialize()
    
    # Define callback for price updates
    async def price_update_callback(price_data: PriceData):
        print(f"🔄 {price_data.symbol}: ₹{price_data.last_price:.2f} "
              f"({price_data.change:+.2f}) at {price_data.timestamp.strftime('%H:%M:%S')}")
    
    # Subscribe to price updates
    symbols_to_watch = ["RELIANCE", "TCS"]
    for symbol in symbols_to_watch:
        await market_data_manager.subscribe_to_price_updates(symbol, price_update_callback)
    
    # Start streaming (this would run continuously in a real application)
    print(f"🎯 Watching {len(symbols_to_watch)} symbols for 10 seconds...")
    await market_data_manager.start_price_streaming(update_interval=2)
    
    # Let it run for 10 seconds
    await asyncio.sleep(10)
    
    # Stop streaming and cleanup
    await market_data_manager.stop_price_streaming()
    
    for symbol in symbols_to_watch:
        await market_data_manager.unsubscribe_from_price_updates(symbol, price_update_callback)
    
    await market_data_manager.cleanup()


async def example_historical_data():
    """Example: Historical data analysis"""
    print("\n📊 Example 3: Historical Data Analysis")
    print("-" * 40)
    
    from core.market_data import market_data_manager
    
    await market_data_manager.initialize()
    
    symbol = "RELIANCE"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)  # Last 30 days
    
    # Get historical data
    hist_data = await market_data_manager.get_historical_data(
        symbol, start_date, end_date, "1d"
    )
    
    if hist_data is not None and not hist_data.empty:
        print(f"📈 {symbol} - Last 30 Days Analysis:")
        print(f"   Data Points: {len(hist_data)}")
        print(f"   Date Range: {hist_data.index[0].date()} to {hist_data.index[-1].date()}")
        
        # Calculate some basic statistics
        latest_close = hist_data['Close'].iloc[-1]
        highest_price = hist_data['High'].max()
        lowest_price = hist_data['Low'].min()
        avg_volume = hist_data['Volume'].mean()
        
        # Calculate returns
        returns = hist_data['Close'].pct_change().dropna()
        volatility = returns.std() * (252 ** 0.5)  # Annualized volatility
        
        print(f"   Latest Close: ₹{latest_close:.2f}")
        print(f"   30-Day High: ₹{highest_price:.2f}")
        print(f"   30-Day Low: ₹{lowest_price:.2f}")
        print(f"   Avg Daily Volume: {avg_volume:,.0f}")
        print(f"   Annualized Volatility: {volatility:.2%}")
        
        # Show recent performance
        recent_change = (latest_close - hist_data['Close'].iloc[0]) / hist_data['Close'].iloc[0]
        print(f"   30-Day Return: {recent_change:+.2%}")
    
    await market_data_manager.cleanup()


async def example_market_status():
    """Example: Market status and hours"""
    print("\n🕐 Example 4: Market Status and Hours")
    print("-" * 40)
    
    from core.market_data import market_data_manager
    
    await market_data_manager.initialize()
    
    # Get comprehensive market status
    market_status = await market_data_manager.get_market_status()
    
    print("🏢 Market Information:")
    print(f"   Current Status: {market_status['status'].upper()}")
    print(f"   Market Open: {'Yes' if market_status['is_open'] else 'No'}")
    print(f"   Next Open: {market_status['next_market_open']}")
    
    print(f"\n⏰ Today's Market Hours:")
    hours = market_status['market_hours']
    for key, time_str in hours.items():
        time_obj = datetime.fromisoformat(time_str)
        print(f"   {key.replace('_', ' ').title()}: {time_obj.strftime('%H:%M')}")
    
    print(f"\n🔌 Data Sources:")
    sources = market_status['data_sources']
    print(f"   Primary: {sources['primary']} ({'Connected' if sources['primary_connected'] else 'Disconnected'})")
    if sources['backup']:
        print(f"   Backup: {sources['backup']} ({'Connected' if sources['backup_connected'] else 'Disconnected'})")
    
    print(f"\n📊 System Stats:")
    print(f"   Active Subscriptions: {market_status['subscriptions']}")
    print(f"   Cache Size: {market_status['cache_size']}")
    print(f"   Streaming Active: {'Yes' if market_status['streaming_active'] else 'No'}")
    
    await market_data_manager.cleanup()


async def example_error_handling():
    """Example: Error handling and failover"""
    print("\n⚠️  Example 5: Error Handling and Failover")
    print("-" * 40)
    
    from core.market_data import market_data_manager
    
    await market_data_manager.initialize()
    
    # Test with invalid symbol
    invalid_symbol = "INVALID_SYMBOL"
    price_data = await market_data_manager.get_real_time_price(invalid_symbol)
    
    if price_data is None:
        print(f"✅ Properly handled invalid symbol: {invalid_symbol}")
    else:
        print(f"⚠️  Unexpected data for invalid symbol: {price_data}")
    
    # Test with valid symbol to show failover working
    valid_symbol = "RELIANCE"
    price_data = await market_data_manager.get_real_time_price(valid_symbol)
    
    if price_data:
        print(f"✅ Failover working - got data for {valid_symbol} from {price_data.source}")
    else:
        print(f"❌ No data available for {valid_symbol} (check network/API)")
    
    await market_data_manager.cleanup()


async def example_custom_callback():
    """Example: Custom trading strategy with market data"""
    print("\n🤖 Example 6: Custom Trading Strategy Integration")
    print("-" * 40)
    
    from core.market_data import market_data_manager, PriceData
    
    await market_data_manager.initialize()
    
    # Example: Simple moving average crossover strategy
    class SimpleStrategy:
        def __init__(self):
            self.prices = {}
            self.moving_avg_period = 5
        
        async def on_price_update(self, price_data: PriceData):
            symbol = price_data.symbol
            price = price_data.last_price
            
            # Store price history
            if symbol not in self.prices:
                self.prices[symbol] = []
            
            self.prices[symbol].append(price)
            
            # Keep only last N prices
            if len(self.prices[symbol]) > self.moving_avg_period:
                self.prices[symbol] = self.prices[symbol][-self.moving_avg_period:]
            
            # Calculate moving average
            if len(self.prices[symbol]) >= self.moving_avg_period:
                moving_avg = sum(self.prices[symbol]) / len(self.prices[symbol])
                
                # Simple strategy logic
                if price > moving_avg * 1.01:  # Price 1% above MA
                    print(f"🚀 BUY SIGNAL: {symbol} @ ₹{price:.2f} (MA: ₹{moving_avg:.2f})")
                elif price < moving_avg * 0.99:  # Price 1% below MA
                    print(f"📉 SELL SIGNAL: {symbol} @ ₹{price:.2f} (MA: ₹{moving_avg:.2f})")
                else:
                    print(f"➡️  HOLD: {symbol} @ ₹{price:.2f} (MA: ₹{moving_avg:.2f})")
    
    # Initialize strategy
    strategy = SimpleStrategy()
    
    # Subscribe to price updates
    symbol = "RELIANCE"
    await market_data_manager.subscribe_to_price_updates(symbol, strategy.on_price_update)
    
    print(f"📊 Running simple strategy on {symbol} for 10 seconds...")
    
    # Simulate price updates
    for i in range(5):
        price_data = await market_data_manager.get_real_time_price(symbol)
        if price_data:
            await strategy.on_price_update(price_data)
        await asyncio.sleep(2)
    
    # Cleanup
    await market_data_manager.unsubscribe_from_price_updates(symbol, strategy.on_price_update)
    await market_data_manager.cleanup()


async def main():
    """Run all examples"""
    print("🎯 Market Data Service - Usage Examples")
    print("=" * 60)
    
    examples = [
        example_basic_usage,
        example_real_time_streaming,
        example_historical_data,
        example_market_status,
        example_error_handling,
        example_custom_callback
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
    print("\n💡 Integration Tips:")
    print("1. Always call initialize() before using the market data manager")
    print("2. Use cleanup() to properly close connections")
    print("3. Handle None returns gracefully (network issues, invalid symbols)")
    print("4. Subscribe to price updates for real-time strategies")
    print("5. Use historical data for backtesting and analysis")
    print("6. Check market status before making trading decisions")


if __name__ == "__main__":
    asyncio.run(main())