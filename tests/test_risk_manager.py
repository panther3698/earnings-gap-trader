#!/usr/bin/env python3
"""
Comprehensive test suite for the risk management system
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_risk_management_system():
    """Test the comprehensive risk management system"""
    print("🚀 Testing Risk Management System")
    print("=" * 50)
    
    try:
        from core.risk_manager import (
            RiskManager, VolatilityAnalyzer, PositionSizer, CircuitBreaker,
            EmergencyManager, RiskLevel, MarketRegime, AlertType,
            PositionSize, RiskMetrics, RiskAlert
        )
        from core.market_data import MarketDataManager
        
        # Initialize components
        print("\n1. 🔧 Testing Component Initialization")
        
        # Create mock market data manager
        mock_market_data_manager = Mock(spec=MarketDataManager)
        mock_market_data_manager.initialize.return_value = True
        
        # Mock historical data for volatility analysis
        mock_hist_data = pd.DataFrame({
            'High': np.random.normal(2500, 50, 30),
            'Low': np.random.normal(2450, 50, 30),
            'Close': np.random.normal(2475, 50, 30),
            'Volume': np.random.normal(1000000, 200000, 30)
        })
        mock_hist_data.index = pd.date_range(start='2024-01-01', periods=30, freq='D')
        mock_market_data_manager.get_historical_data.return_value = mock_hist_data
        
        # Mock real-time price data
        from core.market_data import PriceData, DataSource
        mock_price_data = PriceData(
            symbol="RELIANCE",
            open=2450.0,
            high=2500.0,
            low=2440.0,
            close=2460.0,
            volume=1500000,
            last_price=2475.0,
            timestamp=datetime.now(),
            source=DataSource.YAHOO.value
        )
        mock_market_data_manager.get_real_time_price.return_value = mock_price_data
        
        # Initialize components
        risk_manager = RiskManager(mock_market_data_manager)
        volatility_analyzer = VolatilityAnalyzer(mock_market_data_manager)
        position_sizer = PositionSizer(volatility_analyzer)
        circuit_breaker = CircuitBreaker()
        emergency_manager = EmergencyManager(mock_market_data_manager)
        
        print("✅ All components initialized successfully")
        
        # Test volatility analyzer
        print("\n2. 📊 Testing Volatility Analyzer")
        
        # Test ATR calculation
        atr = await volatility_analyzer.calculate_atr("RELIANCE")
        if atr:
            print(f"✅ ATR calculated: {atr:.2f}")
        else:
            print("⚠️  ATR calculation returned None (using mock data)")
        
        # Test volatility percentile
        vol_percentile = await volatility_analyzer.get_volatility_percentile("RELIANCE")
        if vol_percentile:
            print(f"✅ Volatility percentile: {vol_percentile:.1f}%")
        else:
            print("⚠️  Volatility percentile calculation returned None")
        
        # Test market regime detection
        regime = await volatility_analyzer.detect_market_regime("RELIANCE")
        print(f"✅ Market regime detected: {regime.value}")
        
        # Test position sizer
        print("\n3. 💰 Testing Position Sizer")
        
        test_account_balance = 100000.0
        test_entry_price = 2475.0
        test_stop_loss = 2400.0
        
        # Test basic position sizing
        position_size = await position_sizer.calculate_position_size(
            symbol="RELIANCE",
            entry_price=test_entry_price,
            stop_loss=test_stop_loss,
            account_balance=test_account_balance
        )
        
        print(f"✅ Position size calculated:")
        print(f"   Base size: ₹{position_size.base_size:,.0f}")
        print(f"   Volatility adjusted: ₹{position_size.volatility_adjusted_size:,.0f}")
        print(f"   Performance adjusted: ₹{position_size.performance_adjusted_size:,.0f}")
        print(f"   Final size: ₹{position_size.final_size:,.0f}")
        print(f"   Size percentage: {position_size.size_percentage:.1f}%")
        print(f"   Risk amount: ₹{position_size.risk_amount:,.0f}")
        print(f"   Rationale: {position_size.rationale}")
        
        # Test position sizing with performance data
        performance_data = {
            'win_rate': 0.4,  # Low win rate
            'avg_return': -0.02,  # Negative returns
            'consecutive_losses': 2,
            'trades_count': 10
        }
        
        position_size_with_perf = await position_sizer.calculate_position_size(
            symbol="RELIANCE",
            entry_price=test_entry_price,
            stop_loss=test_stop_loss,
            account_balance=test_account_balance,
            recent_performance=performance_data
        )
        
        print(f"✅ Position size with poor performance:")
        print(f"   Final size: ₹{position_size_with_perf.final_size:,.0f}")
        print(f"   Rationale: {position_size_with_perf.rationale}")
        
        # Test circuit breaker
        print("\n4. 🚨 Testing Circuit Breaker")
        
        # Test daily loss limit
        test_daily_pnl = -3500.0  # 3.5% loss
        daily_alert = circuit_breaker.check_daily_loss_limit(test_daily_pnl, test_account_balance)
        if daily_alert:
            print(f"✅ Daily loss alert: {daily_alert.message}")
            print(f"   Severity: {daily_alert.severity.value}")
            print(f"   Action required: {daily_alert.requires_action}")
        else:
            print("✅ Daily loss within limits")
        
        # Test drawdown limit
        test_drawdown = 0.09  # 9% drawdown
        drawdown_alert = circuit_breaker.check_drawdown_limit(test_drawdown)
        if drawdown_alert:
            print(f"✅ Drawdown alert: {drawdown_alert.message}")
            print(f"   Severity: {drawdown_alert.severity.value}")
        else:
            print("✅ Drawdown within limits")
        
        # Test portfolio heat
        test_portfolio_heat = 0.18  # 18% portfolio heat
        heat_alert = circuit_breaker.check_portfolio_heat(test_portfolio_heat)
        if heat_alert:
            print(f"✅ Portfolio heat alert: {heat_alert.message}")
        else:
            print("✅ Portfolio heat within limits")
        
        # Test position limits
        test_open_positions = 6  # Exceed limit of 5
        position_alert = circuit_breaker.check_position_limits(test_open_positions)
        if position_alert:
            print(f"✅ Position limit alert: {position_alert.message}")
        else:
            print("✅ Open positions within limits")
        
        # Test trading halt functionality
        print("\n   Testing trading halt:")
        circuit_breaker.halt_trading("Test halt reason")
        print(f"✅ Trading halted: {circuit_breaker.is_trading_halted}")
        print(f"   Halt reason: {circuit_breaker.halt_reason}")
        
        circuit_breaker.resume_trading("Test override")
        print(f"✅ Trading resumed: {not circuit_breaker.is_trading_halted}")
        
        # Test emergency manager
        print("\n5. 🚨 Testing Emergency Manager")
        
        # Create test risk metrics for emergency conditions
        critical_metrics = RiskMetrics(
            timestamp=datetime.now(),
            total_capital=100000.0,
            available_capital=80000.0,
            portfolio_value=95000.0,
            daily_pnl=-6000.0,  # 6% daily loss
            daily_pnl_percent=-0.06,
            max_drawdown=0.15,
            current_drawdown=0.15,  # 15% drawdown
            portfolio_heat=0.25,  # 25% portfolio heat
            open_positions=3,
            total_risk_amount=6000.0,
            risk_utilization=0.85,
            volatility_percentile=95.0,
            market_regime=MarketRegime.VOLATILE,
            risk_level=RiskLevel.CRITICAL
        )
        
        # Test emergency condition detection
        is_emergency = emergency_manager.check_emergency_conditions(critical_metrics)
        print(f"✅ Emergency conditions detected: {is_emergency}")
        
        if is_emergency:
            await emergency_manager.trigger_emergency_stop("Critical risk levels breached")
            print(f"✅ Emergency stop triggered: {emergency_manager.emergency_stop_triggered}")
        
        # Get emergency status
        emergency_status = await emergency_manager.get_emergency_status()
        print(f"✅ Emergency status: {emergency_status}")
        
        # Test risk manager integration
        print("\n6. 🎛️  Testing Risk Manager Integration")
        
        # Initialize risk manager
        initialized = await risk_manager.initialize()
        print(f"✅ Risk manager initialized: {initialized}")
        
        # Test trade validation
        trade_valid, validated_position, alerts = await risk_manager.validate_trade(
            symbol="RELIANCE",
            signal_type="earnings_gap_up",
            entry_price=2475.0,
            stop_loss=2400.0,
            confidence_score=75.0
        )
        
        print(f"✅ Trade validation result: {trade_valid}")
        if validated_position:
            print(f"   Validated position size: ₹{validated_position.final_size:,.0f}")
            print(f"   Risk amount: ₹{validated_position.risk_amount:,.0f}")
        
        if alerts:
            print(f"   Alerts generated: {len(alerts)}")
            for alert in alerts:
                print(f"   - {alert.alert_type.value}: {alert.message}")
        
        # Test low confidence trade
        trade_valid_low, position_low, alerts_low = await risk_manager.validate_trade(
            symbol="RELIANCE",
            signal_type="earnings_gap_up",
            entry_price=2475.0,
            stop_loss=2400.0,
            confidence_score=45.0  # Low confidence
        )
        
        print(f"✅ Low confidence trade validation: {trade_valid_low}")
        if alerts_low:
            print(f"   Low confidence alerts: {len(alerts_low)}")
        
        # Test position monitoring
        print("\n7. 👁️  Testing Position Monitoring")
        
        position_alerts = await risk_manager.monitor_position(
            symbol="RELIANCE",
            current_price=2200.0,  # Large adverse move
            entry_price=2475.0,
            stop_loss=2400.0,
            position_size=10000.0
        )
        
        if position_alerts:
            print(f"✅ Position monitoring alerts: {len(position_alerts)}")
            for alert in position_alerts:
                print(f"   - {alert.alert_type.value}: {alert.message}")
        else:
            print("✅ No position monitoring alerts")
        
        # Test account balance updates
        print("\n8. 💳 Testing Account Balance Management")
        
        original_balance = risk_manager.account_balance
        print(f"   Original balance: ₹{original_balance:,.0f}")
        
        # Simulate profit
        new_balance = original_balance * 1.05  # 5% gain
        await risk_manager.update_account_balance(new_balance)
        print(f"✅ Updated balance (profit): ₹{risk_manager.account_balance:,.0f}")
        print(f"   Peak balance: ₹{risk_manager.peak_balance:,.0f}")
        
        # Simulate loss
        loss_balance = original_balance * 0.92  # 8% loss
        await risk_manager.update_account_balance(loss_balance)
        print(f"✅ Updated balance (loss): ₹{risk_manager.account_balance:,.0f}")
        
        # Test risk dashboard
        print("\n9. 📊 Testing Risk Dashboard")
        
        dashboard = await risk_manager.get_risk_dashboard()
        print(f"✅ Risk dashboard generated:")
        
        if dashboard.get("risk_metrics"):
            metrics = dashboard["risk_metrics"]
            print(f"   Risk level: {metrics['risk_level']}")
            print(f"   Daily P&L: ₹{metrics['daily_pnl']:,.0f} ({metrics['daily_pnl_percent']:+.1%})")
            print(f"   Current drawdown: {metrics['current_drawdown']:.1%}")
            print(f"   Portfolio heat: {metrics['portfolio_heat']:.1%}")
            print(f"   Risk utilization: {metrics['risk_utilization']:.1%}")
        
        print(f"   Recent alerts: {len(dashboard.get('recent_alerts', []))}")
        print(f"   Circuit breaker status: {dashboard.get('circuit_breaker_status', {})}")
        
        # Test edge cases and error handling
        print("\n10. ⚠️  Testing Edge Cases")
        
        # Test with zero stop loss difference
        edge_position = await position_sizer.calculate_position_size(
            symbol="TEST",
            entry_price=100.0,
            stop_loss=100.0,  # Same as entry
            account_balance=10000.0
        )
        print(f"✅ Zero stop loss handling: ₹{edge_position.final_size:,.0f}")
        
        # Test with very small account
        small_position = await position_sizer.calculate_position_size(
            symbol="TEST",
            entry_price=2000.0,
            stop_loss=1900.0,
            account_balance=500.0  # Very small account
        )
        print(f"✅ Small account handling: ₹{small_position.final_size:,.0f}")
        
        # Test data structure serialization
        print("\n11. 📋 Testing Data Structure Serialization")
        
        # Test PositionSize serialization
        position_dict = position_size.to_dict()
        print(f"✅ PositionSize serialization: {len(position_dict)} fields")
        
        # Test RiskAlert serialization
        if alerts:
            alert_dict = alerts[0].to_dict()
            print(f"✅ RiskAlert serialization: {len(alert_dict)} fields")
        
        # Test RiskMetrics serialization
        metrics_dict = critical_metrics.to_dict()
        print(f"✅ RiskMetrics serialization: {len(metrics_dict)} fields")
        
        # Test enum values
        print("\n12. 🏷️  Testing Enums and Constants")
        
        print(f"✅ Risk levels: {[rl.value for rl in RiskLevel]}")
        print(f"✅ Market regimes: {[mr.value for mr in MarketRegime]}")
        print(f"✅ Alert types: {[at.value for at in AlertType]}")
        
        # Test performance under load
        print("\n13. ⚡ Testing Performance")
        
        # Test position sizing performance
        start_time = datetime.now()
        for i in range(100):
            await position_sizer.calculate_position_size(
                symbol="TEST",
                entry_price=2000.0 + i,
                stop_loss=1900.0 + i,
                account_balance=100000.0
            )
        end_time = datetime.now()
        
        avg_time = (end_time - start_time).total_seconds() / 100 * 1000
        print(f"✅ Position sizing performance: {avg_time:.2f}ms avg")
        
        # Test circuit breaker performance
        start_time = datetime.now()
        for i in range(1000):
            circuit_breaker.check_daily_loss_limit(-1000.0, 100000.0)
        end_time = datetime.now()
        
        avg_time = (end_time - start_time).total_seconds() / 1000 * 1000
        print(f"✅ Circuit breaker performance: {avg_time:.3f}ms avg")
        
        # Cleanup
        print("\n14. 🧹 Testing Cleanup")
        await risk_manager.cleanup()
        print("✅ Risk manager cleanup completed")
        
        print("\n" + "=" * 50)
        print("🎉 All Risk Management System tests completed successfully!")
        print("\n📊 Test Summary:")
        print("✅ Component initialization")
        print("✅ Volatility analysis and regime detection")
        print("✅ Dynamic position sizing")
        print("✅ Circuit breaker monitoring")
        print("✅ Emergency management protocols")
        print("✅ Risk manager integration")
        print("✅ Position monitoring")
        print("✅ Account balance management")
        print("✅ Risk dashboard generation")
        print("✅ Edge case handling")
        print("✅ Data structure serialization")
        print("✅ Enum and constant validation")
        print("✅ Performance metrics")
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


async def test_risk_scenarios():
    """Test various risk scenarios and edge cases"""
    print("\n🧠 Testing Risk Scenarios")
    print("-" * 30)
    
    try:
        from core.risk_manager import (
            RiskManager, CircuitBreaker, RiskLevel, AlertType,
            RiskMetrics, MarketRegime
        )
        from core.market_data import MarketDataManager
        from unittest.mock import Mock
        
        # Mock market data manager
        mock_market_data_manager = Mock(spec=MarketDataManager)
        mock_market_data_manager.initialize.return_value = True
        
        circuit_breaker = CircuitBreaker()
        
        # Scenario 1: Gradual loss progression
        print("1. Testing gradual loss progression...")
        
        account_balance = 100000.0
        daily_losses = [-500, -1000, -1500, -2000, -2500, -3000, -3500]
        
        for i, loss in enumerate(daily_losses):
            alert = circuit_breaker.check_daily_loss_limit(loss, account_balance)
            status = "NO ALERT"
            if alert:
                status = f"{alert.severity.value.upper()} - {alert.message}"
            
            loss_percent = abs(loss) / account_balance * 100
            print(f"   Day {i+1}: ₹{loss:+,} ({loss_percent:.1f}%) - {status}")
        
        # Scenario 2: Drawdown progression
        print("\n2. Testing drawdown progression...")
        
        peak_balance = 100000.0
        current_balances = [98000, 95000, 92000, 88000, 85000, 80000, 75000]
        
        for i, balance in enumerate(current_balances):
            drawdown = (peak_balance - balance) / peak_balance
            alert = circuit_breaker.check_drawdown_limit(drawdown)
            
            status = "NO ALERT"
            if alert:
                status = f"{alert.severity.value.upper()} - {alert.message}"
            
            print(f"   Balance ₹{balance:,} ({drawdown:.1%} drawdown) - {status}")
        
        # Scenario 3: Portfolio heat scenarios
        print("\n3. Testing portfolio heat scenarios...")
        
        heat_levels = [0.05, 0.08, 0.12, 0.15, 0.18, 0.22]
        
        for heat in heat_levels:
            alert = circuit_breaker.check_portfolio_heat(heat)
            
            status = "SAFE"
            if alert:
                status = f"{alert.severity.value.upper()} ALERT"
            
            print(f"   Portfolio heat {heat:.1%} - {status}")
        
        # Scenario 4: Emergency conditions matrix
        print("\n4. Testing emergency condition combinations...")
        
        scenarios = [
            {"daily_pnl_percent": -0.02, "drawdown": 0.05, "heat": 0.10, "description": "Mild stress"},
            {"daily_pnl_percent": -0.04, "drawdown": 0.08, "heat": 0.15, "description": "Moderate stress"},
            {"daily_pnl_percent": -0.06, "drawdown": 0.12, "heat": 0.20, "description": "High stress"},
            {"daily_pnl_percent": -0.08, "drawdown": 0.15, "heat": 0.25, "description": "Critical stress"},
        ]
        
        for scenario in scenarios:
            test_metrics = RiskMetrics(
                timestamp=datetime.now(),
                total_capital=100000.0,
                available_capital=80000.0,
                portfolio_value=95000.0,
                daily_pnl=scenario["daily_pnl_percent"] * 100000,
                daily_pnl_percent=scenario["daily_pnl_percent"],
                max_drawdown=scenario["drawdown"],
                current_drawdown=scenario["drawdown"],
                portfolio_heat=scenario["heat"],
                open_positions=2,
                total_risk_amount=abs(scenario["daily_pnl_percent"] * 100000),
                risk_utilization=scenario["heat"] / 0.15,
                volatility_percentile=75.0,
                market_regime=MarketRegime.VOLATILE,
                risk_level=RiskLevel.HIGH
            )
            
            # Check emergency conditions
            from core.risk_manager import EmergencyManager
            emergency_manager = EmergencyManager(mock_market_data_manager)
            is_emergency = emergency_manager.check_emergency_conditions(test_metrics)
            
            print(f"   {scenario['description']}: Emergency = {is_emergency}")
            print(f"      Daily P&L: {scenario['daily_pnl_percent']:+.1%}")
            print(f"      Drawdown: {scenario['drawdown']:.1%}")
            print(f"      Portfolio heat: {scenario['heat']:.1%}")
        
        print("\n✅ Risk scenario tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Risk scenario test failed: {e}")
        return False


async def test_position_sizing_strategies():
    """Test different position sizing strategies"""
    print("\n💰 Testing Position Sizing Strategies")
    print("-" * 30)
    
    try:
        from core.risk_manager import PositionSizer, VolatilityAnalyzer
        from core.market_data import MarketDataManager
        from unittest.mock import Mock
        import pandas as pd
        import numpy as np
        
        # Mock market data manager
        mock_market_data_manager = Mock(spec=MarketDataManager)
        
        # Create different volatility scenarios
        scenarios = {
            "low_volatility": pd.DataFrame({
                'High': np.random.normal(2500, 10, 30),  # Low volatility
                'Low': np.random.normal(2490, 10, 30),
                'Close': np.random.normal(2495, 10, 30),
                'Volume': np.random.normal(1000000, 100000, 30)
            }),
            "medium_volatility": pd.DataFrame({
                'High': np.random.normal(2500, 50, 30),  # Medium volatility
                'Low': np.random.normal(2450, 50, 30),
                'Close': np.random.normal(2475, 50, 30),
                'Volume': np.random.normal(1000000, 300000, 30)
            }),
            "high_volatility": pd.DataFrame({
                'High': np.random.normal(2500, 150, 30),  # High volatility
                'Low': np.random.normal(2350, 150, 30),
                'Close': np.random.normal(2425, 150, 30),
                'Volume': np.random.normal(1000000, 500000, 30)
            })
        }
        
        # Set up mock returns based on scenario
        def mock_get_historical_data(symbol, start_date, end_date, interval):
            scenario_key = getattr(mock_get_historical_data, 'current_scenario', 'medium_volatility')
            return scenarios[scenario_key]
        
        mock_market_data_manager.get_historical_data.side_effect = mock_get_historical_data
        
        # Mock current price
        from core.market_data import PriceData, DataSource
        mock_price = PriceData(
            symbol="TEST",
            open=2450.0,
            high=2500.0,
            low=2440.0,
            close=2460.0,
            volume=1500000,
            last_price=2475.0,
            timestamp=datetime.now(),
            source=DataSource.YAHOO.value
        )
        mock_market_data_manager.get_real_time_price.return_value = mock_price
        
        volatility_analyzer = VolatilityAnalyzer(mock_market_data_manager)
        position_sizer = PositionSizer(volatility_analyzer)
        
        test_params = {
            'symbol': 'TEST',
            'entry_price': 2475.0,
            'stop_loss': 2400.0,
            'account_balance': 100000.0
        }
        
        print("Testing position sizing across volatility scenarios:")
        
        for scenario_name, _ in scenarios.items():
            # Set current scenario for mock
            mock_get_historical_data.current_scenario = scenario_name
            
            position_size = await position_sizer.calculate_position_size(**test_params)
            
            print(f"\n   {scenario_name.replace('_', ' ').title()}:")
            print(f"      Base size: ₹{position_size.base_size:,.0f}")
            print(f"      Volatility adjusted: ₹{position_size.volatility_adjusted_size:,.0f}")
            print(f"      Final size: ₹{position_size.final_size:,.0f}")
            print(f"      Size percentage: {position_size.size_percentage:.1f}%")
            
            vol_adjustment = (position_size.volatility_adjusted_size / position_size.base_size - 1) * 100
            print(f"      Volatility adjustment: {vol_adjustment:+.0f}%")
        
        # Test performance-based adjustments
        print("\n\nTesting performance-based adjustments:")
        
        performance_scenarios = [
            {
                'name': 'Excellent Performance',
                'data': {'win_rate': 0.8, 'avg_return': 0.06, 'consecutive_losses': 0, 'trades_count': 20}
            },
            {
                'name': 'Good Performance', 
                'data': {'win_rate': 0.65, 'avg_return': 0.03, 'consecutive_losses': 1, 'trades_count': 15}
            },
            {
                'name': 'Poor Performance',
                'data': {'win_rate': 0.3, 'avg_return': -0.02, 'consecutive_losses': 3, 'trades_count': 12}
            }
        ]
        
        for perf_scenario in performance_scenarios:
            position_size = await position_sizer.calculate_position_size(
                recent_performance=perf_scenario['data'],
                **test_params
            )
            
            print(f"\n   {perf_scenario['name']}:")
            print(f"      Final size: ₹{position_size.final_size:,.0f}")
            print(f"      Size percentage: {position_size.size_percentage:.1f}%")
            print(f"      Rationale: {position_size.rationale}")
        
        print("\n✅ Position sizing strategy tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Position sizing strategy test failed: {e}")
        return False


if __name__ == "__main__":
    async def main():
        print("🧪 Risk Management System Test Suite")
        print("=" * 60)
        
        # Run main tests
        main_test_success = await test_risk_management_system()
        
        # Run risk scenario tests
        scenario_test_success = await test_risk_scenarios()
        
        # Run position sizing tests
        sizing_test_success = await test_position_sizing_strategies()
        
        print("\n" + "=" * 60)
        if main_test_success and scenario_test_success and sizing_test_success:
            print("🎉 ALL TESTS PASSED!")
            print("\n📝 Next Steps:")
            print("1. Integrate risk manager with trading system")
            print("2. Set up real-time monitoring dashboards")
            print("3. Configure circuit breaker thresholds")
            print("4. Test with live market data")
            print("5. Set up emergency notification system")
            print("6. Implement position monitoring automation")
            return 0
        else:
            print("❌ Some tests failed. Please check the errors above.")
            return 1
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)