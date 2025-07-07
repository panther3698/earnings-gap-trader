#!/usr/bin/env python3
"""
Example usage of the Earnings Gap Scanner Strategy
This demonstrates how to integrate the earnings gap scanner into your trading application
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta, date

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def example_basic_scanning():
    """Example: Basic earnings gap scanning"""
    print("📊 Example 1: Basic Earnings Gap Scanning")
    print("-" * 40)
    
    from core.earnings_scanner import get_earnings_gap_scanner
    
    # Get the earnings gap scanner instance
    scanner = await get_earnings_gap_scanner()
    
    # Perform a single scan for signals
    signals = await scanner.scan_for_signals()
    
    if signals:
        print(f"🎯 Found {len(signals)} earnings gap signals:")
        for signal in signals:
            print(f"   📈 {signal.symbol} ({signal.company_name})")
            print(f"      Type: {signal.signal_type.value}")
            print(f"      Confidence: {signal.confidence.value} ({signal.confidence_score:.0f}%)")
            print(f"      Entry: ₹{signal.entry_price:.2f}")
            print(f"      Stop Loss: ₹{signal.stop_loss:.2f}")
            print(f"      Target: ₹{signal.profit_target:.2f}")
            print(f"      Gap: {signal.gap_percent:.1f}%")
            print(f"      Volume: {signal.volume_ratio:.1f}x")
            print(f"      Explanation: {signal.signal_explanation}")
            print()
    else:
        print("📭 No earnings gap signals found")
    
    # Get scanner status
    status = await scanner.get_scan_status()
    print(f"📊 Scanner Status:")
    print(f"   Daily signals: {status['daily_signal_count']}/{status['max_signals_per_day']}")
    print(f"   Is scanning: {status['is_scanning']}")
    print(f"   Scan interval: {status['scan_interval']}s")


async def example_real_time_scanning():
    """Example: Real-time earnings gap scanning"""
    print("\n📡 Example 2: Real-time Earnings Gap Scanning")
    print("-" * 40)
    
    from core.earnings_scanner import get_earnings_gap_scanner
    
    scanner = await get_earnings_gap_scanner()
    
    # Start real-time scanning
    print("🔄 Starting real-time scanning for 30 seconds...")
    await scanner.start_real_time_scanning()
    
    # Let it run for 30 seconds
    await asyncio.sleep(30)
    
    # Stop scanning
    await scanner.stop_real_time_scanning()
    print("⏹️  Real-time scanning stopped")


async def example_earnings_calendar():
    """Example: Fetching and analyzing earnings calendar"""
    print("\n📅 Example 3: Earnings Calendar Analysis")
    print("-" * 40)
    
    from core.earnings_scanner import EarningsDataCollector
    
    collector = EarningsDataCollector()
    
    # Get earnings for the next 7 days
    from_date = date.today()
    to_date = from_date + timedelta(days=7)
    
    print(f"📊 Fetching earnings calendar from {from_date} to {to_date}...")
    announcements = await collector.get_earnings_calendar(from_date, to_date)
    
    if announcements:
        print(f"📈 Found {len(announcements)} upcoming earnings announcements:")
        for announcement in announcements:
            print(f"   🏢 {announcement.company_name} ({announcement.symbol})")
            print(f"      Date: {announcement.announcement_date}")
            print(f"      Time: {announcement.announcement_time or 'TBD'}")
            print(f"      Expected EPS: {announcement.expected_eps or 'N/A'}")
            print(f"      Source: {announcement.source}")
            print()
    else:
        print("📭 No upcoming earnings announcements found")


async def example_gap_detection():
    """Example: Manual gap detection and analysis"""
    print("\n🔍 Example 4: Manual Gap Detection")
    print("-" * 40)
    
    from core.market_data import market_data_manager
    from core.earnings_scanner import GapDetector, VolumeAnalyzer
    
    # Initialize market data manager
    await market_data_manager.initialize()
    
    gap_detector = GapDetector(market_data_manager)
    volume_analyzer = VolumeAnalyzer(market_data_manager)
    
    # Test symbols for gap detection
    test_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK"]
    
    print(f"🔍 Analyzing gaps for {len(test_symbols)} symbols...")
    
    for symbol in test_symbols:
        try:
            # Detect gap
            gap_data = await gap_detector.detect_gap(symbol)
            
            if gap_data:
                print(f"📊 {symbol} - Gap detected:")
                print(f"   Gap: {gap_data.gap_percent:.2f}% {gap_data.gap_type}")
                print(f"   Previous close: ₹{gap_data.previous_close:.2f}")
                print(f"   Current price: ₹{gap_data.current_price:.2f}")
                print(f"   Gap amount: ₹{gap_data.gap_amount:.2f}")
                
                # Analyze volume
                volume_data = await volume_analyzer.analyze_volume(symbol)
                if volume_data:
                    print(f"   Volume ratio: {volume_data.volume_ratio:.1f}x")
                    print(f"   Volume surge: {volume_data.is_surge}")
                print()
            else:
                print(f"📈 {symbol} - No significant gap detected")
                
        except Exception as e:
            print(f"❌ Error analyzing {symbol}: {e}")
    
    await market_data_manager.cleanup()


async def example_signal_generation():
    """Example: Manual signal generation and scoring"""
    print("\n🎯 Example 5: Signal Generation and Scoring")
    print("-" * 40)
    
    from core.earnings_scanner import (
        SignalGenerator, EarningsAnnouncement, GapData, VolumeData
    )
    
    signal_generator = SignalGenerator()
    
    # Create sample data for signal generation
    sample_announcement = EarningsAnnouncement(
        symbol="RELIANCE",
        company_name="Reliance Industries Limited",
        announcement_date=date.today(),
        announcement_time="10:00 AM",
        actual_eps=28.5,
        expected_eps=25.0,
        surprise_percent=14.0,  # 14% positive surprise
        revenue_actual=175000,
        revenue_expected=165000,
        source="Example"
    )
    
    sample_gap = GapData(
        symbol="RELIANCE",
        previous_close=2400.0,
        current_price=2520.0,  # 5% gap up
        gap_percent=5.0,
        gap_amount=120.0,
        gap_type="up",
        timestamp=datetime.now()
    )
    
    sample_volume = VolumeData(
        symbol="RELIANCE",
        current_volume=3500000,
        average_volume_20d=1000000,
        volume_ratio=3.5,  # 3.5x volume surge
        is_surge=True,
        timestamp=datetime.now()
    )
    
    # Generate signal
    signal = signal_generator.generate_signal(
        sample_announcement, sample_gap, sample_volume, 2520.0
    )
    
    if signal:
        print(f"🚀 Signal Generated for {signal.symbol}:")
        print(f"   📊 Basic Info:")
        print(f"      Company: {signal.company_name}")
        print(f"      Type: {signal.signal_type.value}")
        print(f"      Confidence: {signal.confidence.value} ({signal.confidence_score:.0f}%)")
        print(f"      Entry Time: {signal.entry_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"   💰 Trading Details:")
        print(f"      Entry Price: ₹{signal.entry_price:.2f}")
        print(f"      Stop Loss: ₹{signal.stop_loss:.2f}")
        print(f"      Profit Target: ₹{signal.profit_target:.2f}")
        print(f"      Risk/Reward Ratio: 1:{signal.risk_reward_ratio:.2f}")
        
        print(f"   📈 Market Data:")
        print(f"      Gap: {signal.gap_percent:.1f}% ({signal.gap_amount:+.2f})")
        print(f"      Previous Close: ₹{signal.previous_close:.2f}")
        print(f"      Volume Ratio: {signal.volume_ratio:.1f}x")
        print(f"      Current Volume: {signal.current_volume:,}")
        
        print(f"   📊 Earnings Data:")
        print(f"      Earnings Surprise: {signal.earnings_surprise:.1f}%")
        print(f"      Actual EPS: ₹{signal.actual_eps}")
        print(f"      Expected EPS: ₹{signal.expected_eps}")
        
        print(f"   📝 Explanation:")
        print(f"      {signal.signal_explanation}")
        
    else:
        print("❌ No signal generated (confidence too low)")


async def example_custom_strategy():
    """Example: Custom strategy using earnings scanner components"""
    print("\n🤖 Example 6: Custom Strategy Implementation")
    print("-" * 40)
    
    from core.earnings_scanner import (
        EarningsDataCollector, GapDetector, VolumeAnalyzer, SignalGenerator
    )
    from core.market_data import market_data_manager
    
    # Initialize components
    await market_data_manager.initialize()
    
    collector = EarningsDataCollector()
    gap_detector = GapDetector(market_data_manager)
    volume_analyzer = VolumeAnalyzer(market_data_manager)
    signal_generator = SignalGenerator()
    
    class CustomEarningsStrategy:
        def __init__(self):
            self.min_gap_threshold = 3.0  # Minimum 3% gap
            self.min_volume_ratio = 2.5   # Minimum 2.5x volume
            self.min_surprise = 7.5       # Minimum 7.5% earnings surprise
            
        async def scan_custom_signals(self):
            """Custom scanning logic with different thresholds"""
            signals = []
            
            # Get earnings for today and yesterday
            today = date.today()
            yesterday = today - timedelta(days=1)
            
            announcements = await collector.get_earnings_calendar(yesterday, today)
            
            print(f"🔍 Analyzing {len(announcements)} earnings announcements with custom criteria:")
            print(f"   Min gap: {self.min_gap_threshold}%")
            print(f"   Min volume ratio: {self.min_volume_ratio}x")
            print(f"   Min surprise: {self.min_surprise}%")
            print()
            
            for announcement in announcements:
                try:
                    # Apply custom filtering
                    gap_data = await gap_detector.detect_gap(announcement.symbol)
                    if not gap_data or abs(gap_data.gap_percent) < self.min_gap_threshold:
                        print(f"   ❌ {announcement.symbol}: Gap too small")
                        continue
                    
                    volume_data = await volume_analyzer.analyze_volume(announcement.symbol)
                    if not volume_data or volume_data.volume_ratio < self.min_volume_ratio:
                        print(f"   ❌ {announcement.symbol}: Volume too low")
                        continue
                    
                    # Get earnings surprise if available
                    if announcement.surprise_percent is None:
                        surprise = await collector.get_earnings_surprise(
                            announcement.symbol, announcement.announcement_date
                        )
                        announcement.surprise_percent = surprise
                    
                    if (announcement.surprise_percent is not None and 
                        abs(announcement.surprise_percent) < self.min_surprise):
                        print(f"   ❌ {announcement.symbol}: Earnings surprise too small")
                        continue
                    
                    # Generate signal with custom logic
                    signal = signal_generator.generate_signal(
                        announcement, gap_data, volume_data, gap_data.current_price
                    )
                    
                    if signal:
                        signals.append(signal)
                        print(f"   ✅ {announcement.symbol}: Signal generated!")
                    else:
                        print(f"   ⚠️  {announcement.symbol}: Signal confidence too low")
                        
                except Exception as e:
                    print(f"   ❌ {announcement.symbol}: Error - {e}")
            
            return signals
    
    # Run custom strategy
    strategy = CustomEarningsStrategy()
    custom_signals = await strategy.scan_custom_signals()
    
    if custom_signals:
        print(f"\n🎯 Custom strategy found {len(custom_signals)} signals:")
        for signal in custom_signals:
            print(f"   📈 {signal.symbol}: {signal.confidence.value} confidence")
    else:
        print("\n📭 No signals found with custom criteria")
    
    await market_data_manager.cleanup()


async def example_backtesting_data():
    """Example: Collecting data for backtesting"""
    print("\n📊 Example 7: Backtesting Data Collection")
    print("-" * 40)
    
    from core.earnings_scanner import EarningsDataCollector
    from core.market_data import market_data_manager
    
    # Initialize
    await market_data_manager.initialize()
    collector = EarningsDataCollector()
    
    # Collect historical earnings and price data
    print("📈 Collecting backtesting data...")
    
    # Get earnings from last 30 days
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    historical_earnings = await collector.get_earnings_calendar(start_date, end_date)
    
    backtesting_data = []
    
    for announcement in historical_earnings[:5]:  # Limit to 5 for example
        try:
            symbol = announcement.symbol
            earnings_date = announcement.announcement_date
            
            # Get price data around earnings date
            price_start = datetime.combine(earnings_date - timedelta(days=2), datetime.min.time())
            price_end = datetime.combine(earnings_date + timedelta(days=2), datetime.min.time())
            
            hist_data = await market_data_manager.get_historical_data(
                symbol, price_start, price_end, "1d"
            )
            
            if hist_data is not None and not hist_data.empty:
                pre_earnings_close = hist_data['Close'].iloc[0] if len(hist_data) > 0 else None
                post_earnings_open = hist_data['Open'].iloc[1] if len(hist_data) > 1 else None
                
                if pre_earnings_close and post_earnings_open:
                    gap_percent = (post_earnings_open - pre_earnings_close) / pre_earnings_close * 100
                    
                    backtest_record = {
                        'symbol': symbol,
                        'company_name': announcement.company_name,
                        'earnings_date': earnings_date,
                        'surprise_percent': announcement.surprise_percent,
                        'pre_earnings_close': pre_earnings_close,
                        'post_earnings_open': post_earnings_open,
                        'gap_percent': gap_percent,
                        'volume': hist_data['Volume'].iloc[1] if len(hist_data) > 1 else None
                    }
                    
                    backtesting_data.append(backtest_record)
                    
                    print(f"✅ {symbol}: {gap_percent:+.1f}% gap")
            else:
                print(f"❌ {symbol}: No price data available")
                
        except Exception as e:
            print(f"❌ {announcement.symbol}: Error collecting data - {e}")
    
    print(f"\n📊 Collected {len(backtesting_data)} records for backtesting:")
    for record in backtesting_data:
        print(f"   {record['symbol']}: {record['gap_percent']:+.1f}% gap on {record['earnings_date']}")
    
    await market_data_manager.cleanup()


async def example_integration_workflow():
    """Example: Complete integration workflow"""
    print("\n🔄 Example 8: Complete Integration Workflow")
    print("-" * 40)
    
    from core.earnings_scanner import get_earnings_gap_scanner
    
    # This example shows how to integrate the earnings scanner
    # into a complete trading workflow
    
    print("🚀 Starting complete earnings gap trading workflow...")
    
    # Step 1: Initialize scanner
    scanner = await get_earnings_gap_scanner()
    print("✅ Scanner initialized")
    
    # Step 2: Check market status
    market_status = await scanner.market_data_manager.get_market_status()
    print(f"📊 Market status: {market_status['status']} (open: {market_status['is_open']})")
    
    # Step 3: Scan for signals
    signals = await scanner.scan_for_signals()
    print(f"🎯 Found {len(signals)} signals")
    
    # Step 4: Process signals (this is where you'd integrate with order engine)
    for signal in signals:
        print(f"\n📈 Processing signal for {signal.symbol}:")
        print(f"   Entry price: ₹{signal.entry_price:.2f}")
        print(f"   Stop loss: ₹{signal.stop_loss:.2f}")
        print(f"   Profit target: ₹{signal.profit_target:.2f}")
        
        # Here you would:
        # 1. Calculate position size based on risk management
        # 2. Place orders through order execution engine
        # 3. Set up monitoring for stop loss and profit targets
        # 4. Send notifications through Telegram
        
        print(f"   📝 Action: Place {signal.signal_type.value} order")
        print(f"   💰 Risk management: Stop at ₹{signal.stop_loss:.2f}")
        print(f"   🎯 Profit target: ₹{signal.profit_target:.2f}")
    
    # Step 5: Start real-time monitoring (optional)
    if signals:
        print(f"\n🔄 Starting real-time monitoring for {len(signals)} positions...")
        # Here you would start position monitoring
        
    print("\n✅ Workflow completed successfully!")


async def main():
    """Run all examples"""
    print("🎯 Earnings Gap Scanner - Usage Examples")
    print("=" * 60)
    
    examples = [
        example_basic_scanning,
        example_real_time_scanning, 
        example_earnings_calendar,
        example_gap_detection,
        example_signal_generation,
        example_custom_strategy,
        example_backtesting_data,
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
    print("\n💡 Integration Tips:")
    print("1. Always initialize the scanner before using")
    print("2. Check market status before scanning")
    print("3. Set appropriate confidence thresholds")
    print("4. Implement proper risk management")
    print("5. Use real-time scanning during market hours")
    print("6. Store signals in database for tracking")
    print("7. Integrate with order execution engine")
    print("8. Set up notifications for new signals")


if __name__ == "__main__":
    asyncio.run(main())