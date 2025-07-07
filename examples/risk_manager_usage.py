#!/usr/bin/env python3
"""
Example usage of the Risk Management System
This demonstrates how to integrate the risk management system into your trading application
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def example_basic_risk_management():
    """Example: Basic risk management operations"""
    print("📊 Example 1: Basic Risk Management")
    print("-" * 40)
    
    from core.risk_manager import get_risk_manager
    
    # Get the risk manager instance
    risk_manager = await get_risk_manager()
    
    # Get current risk metrics
    dashboard = await risk_manager.get_risk_dashboard()
    
    print("🎛️  Current Risk Dashboard:")
    if dashboard.get("risk_metrics"):
        metrics = dashboard["risk_metrics"]
        print(f"   💰 Account Balance: ₹{metrics['total_capital']:,.0f}")
        print(f"   📈 Daily P&L: ₹{metrics['daily_pnl']:+,.0f} ({metrics['daily_pnl_percent']:+.1%})")
        print(f"   📉 Current Drawdown: {metrics['current_drawdown']:.1%}")
        print(f"   🔥 Portfolio Heat: {metrics['portfolio_heat']:.1%}")
        print(f"   ⚠️  Risk Level: {metrics['risk_level'].upper()}")
        print(f"   📊 Market Regime: {metrics['market_regime'].title()}")
        print(f"   🎯 Open Positions: {metrics['open_positions']}")
    
    # Check circuit breaker status
    cb_status = dashboard.get("circuit_breaker_status", {})
    print(f"\n🚨 Circuit Breaker Status:")
    print(f"   Trading Halted: {'YES' if cb_status.get('is_halted') else 'NO'}")
    if cb_status.get('halt_reason'):
        print(f"   Halt Reason: {cb_status['halt_reason']}")
    
    # Check recent alerts
    alerts = dashboard.get("recent_alerts", [])
    if alerts:
        print(f"\n⚠️  Recent Alerts ({len(alerts)}):")
        for alert in alerts[:3]:  # Show top 3
            print(f"   - {alert['alert_type'].replace('_', ' ').title()}: {alert['message']}")
    else:
        print(f"\n✅ No recent alerts")


async def example_position_sizing():
    """Example: Dynamic position sizing"""
    print("\n💰 Example 2: Dynamic Position Sizing")
    print("-" * 40)
    
    from core.risk_manager import get_risk_manager
    
    risk_manager = await get_risk_manager()
    
    # Example trade parameters
    trade_examples = [
        {
            "symbol": "RELIANCE",
            "entry_price": 2475.0,
            "stop_loss": 2400.0,
            "confidence": 85.0,
            "description": "High confidence earnings gap"
        },
        {
            "symbol": "TCS", 
            "entry_price": 3200.0,
            "stop_loss": 3100.0,
            "confidence": 65.0,
            "description": "Medium confidence signal"
        },
        {
            "symbol": "INFY",
            "entry_price": 1550.0,
            "stop_loss": 1520.0,
            "confidence": 45.0,
            "description": "Low confidence signal"
        }
    ]
    
    print("🎯 Position Sizing Examples:")
    
    for trade in trade_examples:
        print(f"\n   📈 {trade['symbol']} - {trade['description']}")
        print(f"      Entry: ₹{trade['entry_price']:.2f}")
        print(f"      Stop Loss: ₹{trade['stop_loss']:.2f}")
        print(f"      Confidence: {trade['confidence']:.0f}%")
        
        # Calculate position size
        position_size = await risk_manager.position_sizer.calculate_position_size(
            symbol=trade["symbol"],
            entry_price=trade["entry_price"],
            stop_loss=trade["stop_loss"],
            account_balance=risk_manager.account_balance
        )
        
        print(f"      💰 Recommended Size: ₹{position_size.final_size:,.0f}")
        print(f"      📊 Portfolio %: {position_size.size_percentage:.1f}%")
        print(f"      ⚠️  Risk Amount: ₹{position_size.risk_amount:,.0f}")
        print(f"      📝 Rationale: {position_size.rationale}")


async def example_trade_validation():
    """Example: Pre-trade validation"""
    print("\n✅ Example 3: Trade Validation")
    print("-" * 40)
    
    from core.risk_manager import get_risk_manager
    
    risk_manager = await get_risk_manager()
    
    # Example trades to validate
    test_trades = [
        {
            "symbol": "RELIANCE",
            "signal_type": "earnings_gap_up",
            "entry_price": 2475.0,
            "stop_loss": 2400.0,
            "confidence_score": 78.0
        },
        {
            "symbol": "BHARTIARTL",
            "signal_type": "earnings_gap_down", 
            "entry_price": 850.0,
            "stop_loss": 870.0,
            "confidence_score": 55.0
        }
    ]
    
    print("🔍 Validating Trades:")
    
    for i, trade in enumerate(test_trades, 1):
        print(f"\n   Trade {i}: {trade['symbol']} {trade['signal_type']}")
        
        # Validate the trade
        is_valid, position_size, alerts = await risk_manager.validate_trade(
            symbol=trade["symbol"],
            signal_type=trade["signal_type"],
            entry_price=trade["entry_price"],
            stop_loss=trade["stop_loss"],
            confidence_score=trade["confidence_score"]
        )
        
        if is_valid:
            print(f"      ✅ APPROVED")
            if position_size:
                print(f"      💰 Position Size: ₹{position_size.final_size:,.0f}")
                print(f"      📊 Portfolio %: {position_size.size_percentage:.1f}%")
        else:
            print(f"      ❌ REJECTED")
        
        # Show any alerts
        if alerts:
            print(f"      ⚠️  Alerts ({len(alerts)}):")
            for alert in alerts:
                severity_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
                emoji = severity_emoji.get(alert.severity.value, "⚠️")
                print(f"         {emoji} {alert.message}")
                if alert.requires_action:
                    print(f"            💡 Action: {alert.suggested_action}")


async def example_volatility_analysis():
    """Example: Market volatility analysis"""
    print("\n📊 Example 4: Volatility Analysis")
    print("-" * 40)
    
    from core.risk_manager import get_risk_manager
    
    risk_manager = await get_risk_manager()
    volatility_analyzer = risk_manager.volatility_analyzer
    
    # Analyze volatility for major stocks
    symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK"]
    
    print("📈 Volatility Analysis:")
    
    for symbol in symbols:
        try:
            print(f"\n   📊 {symbol}:")
            
            # Calculate ATR
            atr = await volatility_analyzer.calculate_atr(symbol)
            if atr:
                print(f"      ATR (14-day): {atr:.2f}")
            
            # Get volatility percentile
            vol_percentile = await volatility_analyzer.get_volatility_percentile(symbol)
            if vol_percentile:
                vol_status = "HIGH" if vol_percentile > 80 else "LOW" if vol_percentile < 20 else "NORMAL"
                print(f"      Volatility Percentile: {vol_percentile:.0f}% ({vol_status})")
            
            # Detect market regime
            regime = await volatility_analyzer.detect_market_regime(symbol)
            regime_emoji = {
                "trending": "📈",
                "choppy": "📊", 
                "volatile": "🌪️",
                "calm": "😌"
            }
            emoji = regime_emoji.get(regime.value, "📊")
            print(f"      Market Regime: {emoji} {regime.value.title()}")
            
        except Exception as e:
            print(f"      ❌ Error analyzing {symbol}: {e}")


async def example_circuit_breakers():
    """Example: Circuit breaker monitoring"""
    print("\n🚨 Example 5: Circuit Breaker Monitoring")
    print("-" * 40)
    
    from core.risk_manager import get_risk_manager
    
    risk_manager = await get_risk_manager()
    circuit_breaker = risk_manager.circuit_breaker
    
    # Simulate different risk scenarios
    scenarios = [
        {
            "name": "Normal Trading",
            "daily_pnl": -500.0,
            "drawdown": 0.02,
            "portfolio_heat": 0.08,
            "open_positions": 2
        },
        {
            "name": "Moderate Stress",
            "daily_pnl": -2000.0,
            "drawdown": 0.05,
            "portfolio_heat": 0.12,
            "open_positions": 4
        },
        {
            "name": "High Risk",
            "daily_pnl": -3500.0,
            "drawdown": 0.09,
            "portfolio_heat": 0.18,
            "open_positions": 6
        }
    ]
    
    print("🔍 Circuit Breaker Scenarios:")
    
    for scenario in scenarios:
        print(f"\n   📊 {scenario['name']}:")
        print(f"      Daily P&L: ₹{scenario['daily_pnl']:+,.0f}")
        print(f"      Drawdown: {scenario['drawdown']:.1%}")
        print(f"      Portfolio Heat: {scenario['portfolio_heat']:.1%}")
        print(f"      Open Positions: {scenario['open_positions']}")
        
        alerts = []
        
        # Check daily loss
        daily_alert = circuit_breaker.check_daily_loss_limit(
            scenario['daily_pnl'], risk_manager.account_balance
        )
        if daily_alert:
            alerts.append(daily_alert)
        
        # Check drawdown
        drawdown_alert = circuit_breaker.check_drawdown_limit(scenario['drawdown'])
        if drawdown_alert:
            alerts.append(drawdown_alert)
        
        # Check portfolio heat
        heat_alert = circuit_breaker.check_portfolio_heat(scenario['portfolio_heat'])
        if heat_alert:
            alerts.append(heat_alert)
        
        # Check position limits
        position_alert = circuit_breaker.check_position_limits(scenario['open_positions'])
        if position_alert:
            alerts.append(position_alert)
        
        if alerts:
            print(f"      🚨 Circuit Breaker Alerts:")
            for alert in alerts:
                severity_colors = {
                    "low": "🟢",
                    "medium": "🟡", 
                    "high": "🟠",
                    "critical": "🔴"
                }
                color = severity_colors.get(alert.severity.value, "⚠️")
                print(f"         {color} {alert.alert_type.value.replace('_', ' ').title()}")
                print(f"            {alert.message}")
                if alert.requires_action:
                    print(f"            💡 {alert.suggested_action}")
        else:
            print(f"      ✅ All circuit breakers normal")


async def example_position_monitoring():
    """Example: Real-time position monitoring"""
    print("\n👁️ Example 6: Position Monitoring")
    print("-" * 40)
    
    from core.risk_manager import get_risk_manager
    
    risk_manager = await get_risk_manager()
    
    # Simulate monitoring open positions
    open_positions = [
        {
            "symbol": "RELIANCE",
            "entry_price": 2475.0,
            "current_price": 2450.0,  # Small loss
            "stop_loss": 2400.0,
            "position_size": 8000.0
        },
        {
            "symbol": "TCS",
            "entry_price": 3200.0,
            "current_price": 2880.0,  # Large loss
            "stop_loss": 3100.0,
            "position_size": 6000.0
        },
        {
            "symbol": "INFY",
            "entry_price": 1550.0,
            "current_price": 1620.0,  # Profit
            "stop_loss": 1520.0,
            "position_size": 5000.0
        }
    ]
    
    print("📊 Position Monitoring:")
    
    for position in open_positions:
        print(f"\n   📈 {position['symbol']}")
        print(f"      Entry: ₹{position['entry_price']:.2f}")
        print(f"      Current: ₹{position['current_price']:.2f}")
        print(f"      Stop Loss: ₹{position['stop_loss']:.2f}")
        
        # Calculate P&L
        pnl_percent = (position['current_price'] - position['entry_price']) / position['entry_price']
        pnl_amount = pnl_percent * position['position_size']
        
        pnl_emoji = "📈" if pnl_percent > 0 else "📉"
        print(f"      {pnl_emoji} P&L: ₹{pnl_amount:+,.0f} ({pnl_percent:+.1%})")
        
        # Monitor for risk alerts
        alerts = await risk_manager.monitor_position(
            symbol=position["symbol"],
            current_price=position["current_price"],
            entry_price=position["entry_price"],
            stop_loss=position["stop_loss"],
            position_size=position["position_size"]
        )
        
        if alerts:
            print(f"      ⚠️  Risk Alerts:")
            for alert in alerts:
                print(f"         🚨 {alert.message}")
                print(f"         💡 {alert.suggested_action}")
        else:
            print(f"      ✅ No risk alerts")


async def example_emergency_protocols():
    """Example: Emergency risk management"""
    print("\n🚨 Example 7: Emergency Protocols")
    print("-" * 40)
    
    from core.risk_manager import get_risk_manager, RiskMetrics, MarketRegime, RiskLevel
    
    risk_manager = await get_risk_manager()
    emergency_manager = risk_manager.emergency_manager
    
    # Create critical risk scenario
    critical_metrics = RiskMetrics(
        timestamp=datetime.now(),
        total_capital=100000.0,
        available_capital=70000.0,
        portfolio_value=92000.0,
        daily_pnl=-8000.0,  # 8% daily loss
        daily_pnl_percent=-0.08,
        max_drawdown=0.15,
        current_drawdown=0.15,  # 15% drawdown
        portfolio_heat=0.25,  # 25% portfolio heat
        open_positions=5,
        total_risk_amount=8000.0,
        risk_utilization=0.90,
        volatility_percentile=98.0,
        market_regime=MarketRegime.VOLATILE,
        risk_level=RiskLevel.CRITICAL
    )
    
    print("🔍 Emergency Condition Assessment:")
    print(f"   📉 Daily Loss: ₹{critical_metrics.daily_pnl:+,.0f} ({critical_metrics.daily_pnl_percent:+.1%})")
    print(f"   📊 Drawdown: {critical_metrics.current_drawdown:.1%}")
    print(f"   🔥 Portfolio Heat: {critical_metrics.portfolio_heat:.1%}")
    print(f"   📈 Volatility: {critical_metrics.volatility_percentile:.0f}th percentile")
    
    # Check if emergency conditions are met
    is_emergency = emergency_manager.check_emergency_conditions(critical_metrics)
    print(f"\n🚨 Emergency Conditions: {'TRIGGERED' if is_emergency else 'NORMAL'}")
    
    if is_emergency:
        print("   ⚠️  Emergency conditions detected!")
        print("   📋 Emergency Actions:")
        print("      1. 🛑 Halt all new trading")
        print("      2. 📞 Send emergency notifications")
        print("      3. 📊 Generate emergency report")
        print("      4. 👥 Alert risk management team")
        print("      5. 🔍 Review open positions")
        
        # Trigger emergency stop (in demo mode)
        print("\n   🚨 Triggering Emergency Stop (Demo)...")
        await emergency_manager.trigger_emergency_stop("Critical risk levels breached in demo")
        
        # Get emergency status
        emergency_status = await emergency_manager.get_emergency_status()
        print(f"   📊 Emergency Status: {emergency_status}")


async def example_risk_dashboard():
    """Example: Risk management dashboard"""
    print("\n📊 Example 8: Risk Management Dashboard")
    print("-" * 40)
    
    from core.risk_manager import get_risk_manager
    
    risk_manager = await get_risk_manager()
    
    # Get comprehensive dashboard
    dashboard = await risk_manager.get_risk_dashboard()
    
    print("🎛️  Risk Management Dashboard")
    print("=" * 40)
    
    # Account Information
    account_info = dashboard.get("account_info", {})
    print(f"💰 Account Information:")
    print(f"   Current Balance: ₹{account_info.get('current_balance', 0):,.0f}")
    print(f"   Peak Balance: ₹{account_info.get('peak_balance', 0):,.0f}")
    print(f"   Daily Start: ₹{account_info.get('daily_start_balance', 0):,.0f}")
    print(f"   Current Drawdown: {account_info.get('current_drawdown', 0):.1%}")
    
    # Risk Metrics
    risk_metrics = dashboard.get("risk_metrics", {})
    if risk_metrics:
        print(f"\n📊 Risk Metrics:")
        print(f"   Risk Level: {risk_metrics.get('risk_level', 'unknown').upper()}")
        print(f"   Daily P&L: ₹{risk_metrics.get('daily_pnl', 0):+,.0f}")
        print(f"   Portfolio Heat: {risk_metrics.get('portfolio_heat', 0):.1%}")
        print(f"   Risk Utilization: {risk_metrics.get('risk_utilization', 0):.1%}")
        print(f"   Open Positions: {risk_metrics.get('open_positions', 0)}")
        print(f"   Market Regime: {risk_metrics.get('market_regime', 'unknown').title()}")
    
    # Circuit Breaker Status
    cb_status = dashboard.get("circuit_breaker_status", {})
    print(f"\n🚨 Circuit Breaker:")
    print(f"   Status: {'HALTED' if cb_status.get('is_halted') else 'ACTIVE'}")
    if cb_status.get('halt_reason'):
        print(f"   Reason: {cb_status['halt_reason']}")
    
    # Recent Alerts
    alerts = dashboard.get("recent_alerts", [])
    print(f"\n⚠️  Recent Alerts ({len(alerts)}):")
    if alerts:
        for alert in alerts[-5:]:  # Show last 5 alerts
            severity_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
            emoji = severity_emoji.get(alert.get('severity'), "⚠️")
            alert_type = alert.get('alert_type', '').replace('_', ' ').title()
            print(f"   {emoji} {alert_type}: {alert.get('message', '')}")
    else:
        print(f"   ✅ No recent alerts")
    
    # Emergency Status
    emergency_status = dashboard.get("emergency_status", {})
    print(f"\n🚨 Emergency Status:")
    print(f"   Emergency Stop: {'ACTIVE' if emergency_status.get('emergency_stop_active') else 'INACTIVE'}")
    if emergency_status.get('emergency_timestamp'):
        print(f"   Last Emergency: {emergency_status['emergency_timestamp']}")


async def main():
    """Run all examples"""
    print("🎯 Risk Management System - Usage Examples")
    print("=" * 60)
    
    examples = [
        example_basic_risk_management,
        example_position_sizing,
        example_trade_validation,
        example_volatility_analysis,
        example_circuit_breakers,
        example_position_monitoring,
        example_emergency_protocols,
        example_risk_dashboard
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
    print("\n💡 Risk Management Best Practices:")
    print("1. Always validate trades before execution")
    print("2. Monitor positions in real-time")
    print("3. Set appropriate circuit breaker thresholds")
    print("4. Use dynamic position sizing based on volatility")
    print("5. Have emergency protocols ready")
    print("6. Track performance and adjust risk parameters")
    print("7. Monitor portfolio heat and concentration")
    print("8. Respect maximum drawdown limits")
    print("9. Use multiple independent safety systems")
    print("10. Keep detailed logs of all risk decisions")


if __name__ == "__main__":
    asyncio.run(main())