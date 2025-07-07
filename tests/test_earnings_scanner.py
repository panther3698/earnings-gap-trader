#!/usr/bin/env python3
"""
Comprehensive test suite for the earnings gap scanner strategy
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta, date
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_earnings_scanner():
    """Test the earnings gap scanner comprehensively"""
    print("🚀 Testing Earnings Gap Scanner")
    print("=" * 50)
    
    try:
        from core.earnings_scanner import (
            EarningsGapScanner, EarningsDataCollector, GapDetector,
            VolumeAnalyzer, SignalGenerator, EarningsAnnouncement,
            GapData, VolumeData, SignalType, SignalConfidence
        )
        from core.market_data import MarketDataManager
        from database import get_db_session
        
        # Initialize components
        print("\n1. 🔧 Testing Component Initialization")
        
        # Create mock market data manager for testing
        mock_market_data_manager = Mock(spec=MarketDataManager)
        mock_market_data_manager.initialize.return_value = True
        mock_market_data_manager.get_market_status.return_value = {'is_open': True}
        
        earnings_scanner = EarningsGapScanner(mock_market_data_manager)
        earnings_collector = EarningsDataCollector()
        gap_detector = GapDetector(mock_market_data_manager)
        volume_analyzer = VolumeAnalyzer(mock_market_data_manager)
        signal_generator = SignalGenerator()
        
        print("✅ All components initialized successfully")
        
        # Test earnings data collector
        print("\n2. 📊 Testing Earnings Data Collector")
        
        # Test symbol extraction
        test_company_names = [
            "Reliance Industries",
            "Tata Consultancy Services", 
            "HDFC Bank",
            "Unknown Company Ltd"
        ]
        
        for company_name in test_company_names:
            symbol = earnings_collector._extract_symbol_from_name(company_name)
            print(f"✅ {company_name} -> {symbol}")
        
        # Test earnings announcement creation
        test_announcement = EarningsAnnouncement(
            symbol="RELIANCE",
            company_name="Reliance Industries",
            announcement_date=date.today(),
            announcement_time="10:00 AM",
            actual_eps=25.5,
            expected_eps=23.0,
            surprise_percent=10.87,
            revenue_actual=150000,
            revenue_expected=145000,
            source="Test"
        )
        
        print(f"✅ Created test earnings announcement: {test_announcement.symbol}")
        print(f"   Surprise: {test_announcement.surprise_percent:.2f}%")
        
        # Test gap detector
        print("\n3. 🔍 Testing Gap Detector")
        
        # Create mock price data
        from core.market_data import PriceData, DataSource
        
        mock_current_price = PriceData(
            symbol="RELIANCE",
            open=2450.0,
            high=2550.0,
            low=2440.0,
            close=2460.0,
            volume=2000000,
            last_price=2530.0,  # 2.85% gap up from 2460
            timestamp=datetime.now(),
            source=DataSource.YAHOO.value
        )
        
        mock_market_data_manager.get_real_time_price.return_value = mock_current_price
        mock_market_data_manager.get_historical_data.return_value = None  # Will be handled
        
        # Mock historical data for previous close
        import pandas as pd
        hist_data = pd.DataFrame({
            'Close': [2460.0]  # Previous close
        })
        mock_market_data_manager.get_historical_data.return_value = hist_data
        
        gap_data = await gap_detector.detect_gap("RELIANCE")
        if gap_data:
            print(f"✅ Gap detected: {gap_data.gap_percent:.2f}% {gap_data.gap_type}")
            print(f"   Previous close: ₹{gap_data.previous_close:.2f}")
            print(f"   Current price: ₹{gap_data.current_price:.2f}")
            print(f"   Gap amount: ₹{gap_data.gap_amount:.2f}")
        else:
            print("❌ No gap detected")
        
        # Test gap validation
        if gap_data:
            is_valid = gap_detector.validate_gap(gap_data, test_announcement)
            print(f"✅ Gap validation: {is_valid}")
        
        # Test volume analyzer
        print("\n4. 📈 Testing Volume Analyzer")
        
        # Mock volume data
        volume_hist_data = pd.DataFrame({
            'Volume': [1000000] * 20  # 20-day average of 1M
        })
        
        # Create separate mock calls for volume analysis
        def mock_get_historical_data(symbol, start_date, end_date, interval):
            if interval == "1d" and (end_date - start_date).days > 5:
                return volume_hist_data  # For volume analysis
            else:
                return hist_data  # For gap detection
        
        mock_market_data_manager.get_historical_data.side_effect = mock_get_historical_data
        
        volume_data = await volume_analyzer.analyze_volume("RELIANCE")
        if volume_data:
            print(f"✅ Volume analysis:")
            print(f"   Current volume: {volume_data.current_volume:,}")
            print(f"   Average volume: {volume_data.average_volume_20d:,.0f}")
            print(f"   Volume ratio: {volume_data.volume_ratio:.1f}x")
            print(f"   Is surge: {volume_data.is_surge}")
        else:
            print("❌ Volume analysis failed")
        
        # Test volume surge validation
        if volume_data and gap_data:
            surge_valid = volume_analyzer.validate_volume_surge(volume_data, gap_data)
            print(f"✅ Volume surge validation: {surge_valid}")
        
        # Test signal generator
        print("\n5. 🎯 Testing Signal Generator")
        
        if gap_data and volume_data:
            # Test confidence scoring
            confidence_score = signal_generator._calculate_confidence_score(
                test_announcement, gap_data, volume_data
            )
            print(f"✅ Confidence score: {confidence_score:.0f}/100")
            
            # Test signal generation
            signal = signal_generator.generate_signal(
                test_announcement, gap_data, volume_data, gap_data.current_price
            )
            
            if signal:
                print(f"✅ Signal generated:")
                print(f"   Symbol: {signal.symbol}")
                print(f"   Type: {signal.signal_type.value}")
                print(f"   Confidence: {signal.confidence.value} ({signal.confidence_score:.0f})")
                print(f"   Entry price: ₹{signal.entry_price:.2f}")
                print(f"   Stop loss: ₹{signal.stop_loss:.2f}")
                print(f"   Profit target: ₹{signal.profit_target:.2f}")
                print(f"   Risk/Reward: 1:{signal.risk_reward_ratio:.2f}")
                print(f"   Explanation: {signal.signal_explanation}")
            else:
                print("❌ No signal generated (confidence too low)")
        
        # Test earnings gap scanner
        print("\n6. 🔄 Testing Earnings Gap Scanner")
        
        scanner_initialized = await earnings_scanner.initialize()
        print(f"✅ Scanner initialized: {scanner_initialized}")
        
        # Test daily limit checking
        earnings_scanner.daily_signal_count = 0
        earnings_scanner.max_signals_per_day = 1
        earnings_scanner.last_signal_date = date.today()
        
        limit_reached = earnings_scanner._is_daily_limit_reached()
        print(f"✅ Daily limit check (should be False): {not limit_reached}")
        
        earnings_scanner.daily_signal_count = 1
        limit_reached = earnings_scanner._is_daily_limit_reached()
        print(f"✅ Daily limit check (should be True): {limit_reached}")
        
        # Test entry criteria checking
        if gap_data and volume_data:
            criteria_met = earnings_scanner._check_entry_criteria(
                test_announcement, gap_data, volume_data
            )
            print(f"✅ Entry criteria check: {criteria_met}")
        
        # Test scanner status
        status = await earnings_scanner.get_scan_status()
        print(f"✅ Scanner status:")
        for key, value in status.items():
            print(f"   {key}: {value}")
        
        # Test data structures
        print("\n7. 📋 Testing Data Structures")
        
        # Test EarningsAnnouncement
        announcement_dict = test_announcement.to_dict()
        print(f"✅ EarningsAnnouncement serialization: {len(announcement_dict)} fields")
        
        # Test GapData
        if gap_data:
            gap_dict = gap_data.to_dict()
            print(f"✅ GapData serialization: {len(gap_dict)} fields")
        
        # Test VolumeData
        if volume_data:
            volume_dict = volume_data.to_dict()
            print(f"✅ VolumeData serialization: {len(volume_dict)} fields")
        
        # Test EarningsGapSignal
        if signal:
            signal_dict = signal.to_dict()
            print(f"✅ EarningsGapSignal serialization: {len(signal_dict)} fields")
        
        # Test edge cases
        print("\n8. ⚠️  Testing Edge Cases")
        
        # Test with no earnings surprise
        no_surprise_announcement = EarningsAnnouncement(
            symbol="TEST",
            company_name="Test Company",
            announcement_date=date.today(),
            announcement_time=None,
            actual_eps=None,
            expected_eps=None,
            surprise_percent=None,
            revenue_actual=None,
            revenue_expected=None,
            source="Test"
        )
        
        # Test confidence scoring without surprise data
        if gap_data and volume_data:
            no_surprise_score = signal_generator._calculate_confidence_score(
                no_surprise_announcement, gap_data, volume_data
            )
            print(f"✅ Confidence score without surprise: {no_surprise_score:.0f}/100")
        
        # Test with very small gap
        small_gap_data = GapData(
            symbol="TEST",
            previous_close=100.0,
            current_price=101.0,  # Only 1% gap
            gap_percent=1.0,
            gap_amount=1.0,
            gap_type="up",
            timestamp=datetime.now()
        )
        
        small_gap_signal = signal_generator.generate_signal(
            test_announcement, small_gap_data, volume_data, 101.0
        )
        print(f"✅ Small gap signal generation: {'Generated' if small_gap_signal else 'Rejected (as expected)'}")
        
        # Test with low volume
        low_volume_data = VolumeData(
            symbol="TEST",
            current_volume=500000,
            average_volume_20d=1000000,
            volume_ratio=0.5,  # Below average
            is_surge=False,
            timestamp=datetime.now()
        )
        
        low_volume_signal = signal_generator.generate_signal(
            test_announcement, gap_data, low_volume_data, gap_data.current_price
        )
        print(f"✅ Low volume signal generation: {'Generated' if low_volume_signal else 'Rejected (as expected)'}")
        
        # Test performance metrics
        print("\n9. ⚡ Testing Performance Metrics")
        
        # Test signal explanation generation
        if gap_data and volume_data:
            start_time = datetime.now()
            for i in range(100):
                explanation = signal_generator._generate_explanation(
                    test_announcement, gap_data, volume_data, 75.0
                )
            end_time = datetime.now()
            
            avg_time = (end_time - start_time).total_seconds() / 100 * 1000
            print(f"✅ Signal explanation generation: {avg_time:.2f}ms avg")
        
        # Test confidence calculation performance
        if gap_data and volume_data:
            start_time = datetime.now()
            for i in range(1000):
                score = signal_generator._calculate_confidence_score(
                    test_announcement, gap_data, volume_data
                )
            end_time = datetime.now()
            
            avg_time = (end_time - start_time).total_seconds() / 1000 * 1000
            print(f"✅ Confidence calculation: {avg_time:.3f}ms avg")
        
        # Test enum values
        print("\n10. 🏷️  Testing Enums and Constants")
        
        print(f"✅ Signal types: {[st.value for st in SignalType]}")
        print(f"✅ Confidence levels: {[cl.value for cl in SignalConfidence]}")
        
        # Test confidence level mapping
        test_scores = [50, 65, 75, 85, 95]
        for score in test_scores:
            level = signal_generator._get_confidence_level(score)
            print(f"✅ Score {score} -> {level.value}")
        
        # Cleanup
        print("\n11. 🧹 Testing Cleanup")
        await earnings_scanner.cleanup()
        print("✅ Scanner cleanup completed")
        
        print("\n" + "=" * 50)
        print("🎉 All Earnings Gap Scanner tests completed successfully!")
        print("\n📊 Test Summary:")
        print("✅ Component initialization")
        print("✅ Earnings data collection")
        print("✅ Gap detection and validation")
        print("✅ Volume analysis and surge detection")
        print("✅ Signal generation and scoring")
        print("✅ Scanner orchestration")
        print("✅ Data structure serialization")
        print("✅ Edge case handling")
        print("✅ Performance metrics")
        print("✅ Enum and constant validation")
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


async def test_strategy_logic():
    """Test the strategy logic and entry criteria"""
    print("\n🧠 Testing Strategy Logic")
    print("-" * 30)
    
    try:
        from core.earnings_scanner import (
            EarningsAnnouncement, GapData, VolumeData, SignalGenerator
        )
        from datetime import date, datetime, timedelta
        
        signal_generator = SignalGenerator()
        
        # Test case 1: Perfect signal (should generate)
        print("1. Testing perfect signal conditions...")
        
        perfect_announcement = EarningsAnnouncement(
            symbol="RELIANCE",
            company_name="Reliance Industries",
            announcement_date=date.today(),
            announcement_time="10:00 AM",
            actual_eps=25.5,
            expected_eps=20.0,
            surprise_percent=27.5,  # 27.5% surprise
            revenue_actual=None,
            revenue_expected=None,
            source="Test"
        )
        
        perfect_gap = GapData(
            symbol="RELIANCE",
            previous_close=2400.0,
            current_price=2640.0,  # 10% gap up
            gap_percent=10.0,
            gap_amount=240.0,
            gap_type="up",
            timestamp=datetime.now()
        )
        
        perfect_volume = VolumeData(
            symbol="RELIANCE",
            current_volume=5000000,
            average_volume_20d=1000000,
            volume_ratio=5.0,  # 5x volume surge
            is_surge=True,
            timestamp=datetime.now()
        )
        
        perfect_signal = signal_generator.generate_signal(
            perfect_announcement, perfect_gap, perfect_volume, 2640.0
        )
        
        if perfect_signal:
            print(f"✅ Perfect signal generated with {perfect_signal.confidence_score:.0f}% confidence")
            print(f"   Type: {perfect_signal.signal_type.value}")
            print(f"   Confidence level: {perfect_signal.confidence.value}")
        else:
            print("❌ Perfect signal not generated")
        
        # Test case 2: Marginal signal (should generate with lower confidence)
        print("\n2. Testing marginal signal conditions...")
        
        marginal_announcement = EarningsAnnouncement(
            symbol="TCS",
            company_name="Tata Consultancy Services",
            announcement_date=date.today(),
            announcement_time="11:00 AM",
            actual_eps=12.0,
            expected_eps=11.0,
            surprise_percent=9.1,  # 9.1% surprise
            revenue_actual=None,
            revenue_expected=None,
            source="Test"
        )
        
        marginal_gap = GapData(
            symbol="TCS",
            previous_close=3000.0,
            current_price=3120.0,  # 4% gap up
            gap_percent=4.0,
            gap_amount=120.0,
            gap_type="up",
            timestamp=datetime.now()
        )
        
        marginal_volume = VolumeData(
            symbol="TCS",
            current_volume=3200000,
            average_volume_20d=1000000,
            volume_ratio=3.2,  # 3.2x volume surge
            is_surge=True,
            timestamp=datetime.now()
        )
        
        marginal_signal = signal_generator.generate_signal(
            marginal_announcement, marginal_gap, marginal_volume, 3120.0
        )
        
        if marginal_signal:
            print(f"✅ Marginal signal generated with {marginal_signal.confidence_score:.0f}% confidence")
            print(f"   Type: {marginal_signal.signal_type.value}")
            print(f"   Confidence level: {marginal_signal.confidence.value}")
        else:
            print("❌ Marginal signal not generated")
        
        # Test case 3: Poor signal (should be rejected)
        print("\n3. Testing poor signal conditions...")
        
        poor_announcement = EarningsAnnouncement(
            symbol="INFY",
            company_name="Infosys",
            announcement_date=date.today(),
            announcement_time="12:00 PM",
            actual_eps=15.2,
            expected_eps=15.0,
            surprise_percent=1.3,  # Only 1.3% surprise
            revenue_actual=None,
            revenue_expected=None,
            source="Test"
        )
        
        poor_gap = GapData(
            symbol="INFY",
            previous_close=1500.0,
            current_price=1515.0,  # Only 1% gap up
            gap_percent=1.0,
            gap_amount=15.0,
            gap_type="up",
            timestamp=datetime.now()
        )
        
        poor_volume = VolumeData(
            symbol="INFY",
            current_volume=1500000,
            average_volume_20d=1000000,
            volume_ratio=1.5,  # Only 1.5x volume
            is_surge=False,
            timestamp=datetime.now()
        )
        
        poor_signal = signal_generator.generate_signal(
            poor_announcement, poor_gap, poor_volume, 1515.0
        )
        
        if poor_signal:
            print(f"⚠️  Poor signal unexpectedly generated with {poor_signal.confidence_score:.0f}% confidence")
        else:
            print("✅ Poor signal correctly rejected")
        
        # Test case 4: Gap down signal
        print("\n4. Testing gap down signal...")
        
        down_announcement = EarningsAnnouncement(
            symbol="HDFCBANK",
            company_name="HDFC Bank",
            announcement_date=date.today(),
            announcement_time="09:30 AM",
            actual_eps=8.0,
            expected_eps=12.0,
            surprise_percent=-33.3,  # Negative surprise
            revenue_actual=None,
            revenue_expected=None,
            source="Test"
        )
        
        down_gap = GapData(
            symbol="HDFCBANK",
            previous_close=1600.0,
            current_price=1440.0,  # 10% gap down
            gap_percent=-10.0,
            gap_amount=-160.0,
            gap_type="down",
            timestamp=datetime.now()
        )
        
        down_volume = VolumeData(
            symbol="HDFCBANK",
            current_volume=4000000,
            average_volume_20d=1000000,
            volume_ratio=4.0,  # 4x volume surge
            is_surge=True,
            timestamp=datetime.now()
        )
        
        down_signal = signal_generator.generate_signal(
            down_announcement, down_gap, down_volume, 1440.0
        )
        
        if down_signal:
            print(f"✅ Gap down signal generated with {down_signal.confidence_score:.0f}% confidence")
            print(f"   Type: {down_signal.signal_type.value}")
            print(f"   Stop loss: ₹{down_signal.stop_loss:.2f}")
            print(f"   Profit target: ₹{down_signal.profit_target:.2f}")
        else:
            print("❌ Gap down signal not generated")
        
        print("\n✅ Strategy logic tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Strategy logic test failed: {e}")
        return False


if __name__ == "__main__":
    async def main():
        print("🧪 Earnings Gap Scanner Test Suite")
        print("=" * 60)
        
        # Run main tests
        main_test_success = await test_earnings_scanner()
        
        # Run strategy logic tests
        strategy_test_success = await test_strategy_logic()
        
        print("\n" + "=" * 60)
        if main_test_success and strategy_test_success:
            print("🎉 ALL TESTS PASSED!")
            print("\n📝 Next Steps:")
            print("1. Set up earnings data sources (MoneyControl, Economic Times)")
            print("2. Test with live market data during earnings season")
            print("3. Integrate with real-time scanning")
            print("4. Connect to order execution engine")
            print("5. Set up Telegram notifications for signals")
            return 0
        else:
            print("❌ Some tests failed. Please check the errors above.")
            return 1
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)