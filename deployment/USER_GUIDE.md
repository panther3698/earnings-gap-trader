# User Guide - Earnings Gap Trading System

This comprehensive user guide will help you understand and effectively use the Earnings Gap Trading System for automated trading.

## Table of Contents
- [Getting Started](#getting-started)
- [Dashboard Overview](#dashboard-overview)
- [Trading Configuration](#trading-configuration)
- [Portfolio Management](#portfolio-management)
- [Risk Management](#risk-management)
- [Notifications and Alerts](#notifications-and-alerts)
- [Telegram Integration](#telegram-integration)
- [Performance Monitoring](#performance-monitoring)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [FAQ](#frequently-asked-questions)

## Getting Started

### First Time Setup

#### 1. Access the Dashboard
After deployment, access your trading dashboard at:
- **Local**: `http://localhost:8000`
- **Production**: `https://your-domain.com`

#### 2. Initial Configuration
Before starting trading, complete these essential configurations:

1. **API Credentials**: Set up your Zerodha Kite Connect API credentials
2. **Risk Parameters**: Configure position sizing and risk limits
3. **Notification Settings**: Set up Telegram and email alerts
4. **Trading Hours**: Configure market hours and trading windows
5. **Strategy Parameters**: Set gap detection thresholds and filters

#### 3. Paper Trading Mode
**IMPORTANT**: Always start with paper trading to test the system:
```
Settings > Trading Configuration > Paper Trading: ON
```

### System Overview

The Earnings Gap Trading System automatically:
1. **Scans** for earnings announcements and price gaps
2. **Analyzes** market conditions and validates trading signals
3. **Executes** trades based on your configured parameters
4. **Manages** positions with stop-loss and profit targets
5. **Monitors** risk exposure and portfolio performance

## Dashboard Overview

### Main Dashboard Sections

#### 1. Portfolio Summary
- **Account Balance**: Current cash and margin available
- **Total P&L**: Realized and unrealized profit/loss
- **Active Positions**: Number of open positions
- **Daily Performance**: Today's trading performance

#### 2. Gap Scanner
- **Live Gaps**: Real-time earnings gap detection
- **Gap Alerts**: Notifications for new opportunities
- **Signal Quality**: Confidence scores for each gap
- **Market Data**: Live price feeds and volume data

#### 3. Active Positions
- **Position Details**: Symbol, quantity, entry price, current P&L
- **Risk Metrics**: Position size, stop-loss levels, time in trade
- **Action Buttons**: Manual close, modify stop-loss, update targets

#### 4. Recent Trades
- **Trade History**: Recent completed trades with outcomes
- **Performance Metrics**: Win rate, average profit/loss
- **Trade Analysis**: Entry/exit reasons and timing

#### 5. System Status
- **Service Health**: Trading engine, database, API connectivity
- **Market Status**: Market hours, trading session info
- **System Alerts**: Important notifications and warnings

### Navigation Menu

#### Trading
- **Dashboard**: Main trading interface
- **Positions**: Detailed position management
- **Orders**: Order history and status
- **Signals**: Trading signal analysis
- **Scanner**: Gap detection and market scanning

#### Portfolio
- **Performance**: Detailed performance analytics
- **Reports**: Trading reports and analysis
- **Risk**: Risk exposure and limits monitoring
- **History**: Complete trading history

#### Configuration
- **Trading Settings**: Core trading parameters
- **Risk Management**: Risk limits and controls
- **Notifications**: Alert and notification settings
- **API Settings**: External service configurations

## Trading Configuration

### Core Trading Settings

#### Gap Detection Parameters
```
Minimum Gap Percentage: 3.0%
Maximum Gap Percentage: 15.0%
Volume Ratio Threshold: 1.5x
Confidence Threshold: 70%
```

**Explanation**:
- **Min Gap**: Smallest gap percentage to consider trading
- **Max Gap**: Upper limit to avoid extremely volatile situations
- **Volume Ratio**: Required volume increase vs. average
- **Confidence**: Minimum signal confidence to execute trades

#### Position Sizing
```
Position Size Method: Fixed Percentage
Risk Per Trade: 2.0%
Maximum Position Size: ₹50,000
Position Size Percentage: 5.0%
```

**Methods Available**:
- **Fixed Amount**: Same amount per trade
- **Fixed Percentage**: Percentage of account balance
- **Risk-Based**: Based on stop-loss distance
- **Volatility-Based**: Adjusted for stock volatility

#### Risk Controls
```
Maximum Daily Loss: ₹10,000
Maximum Weekly Loss: ₹25,000
Maximum Open Positions: 5
Position Concentration Limit: 20%
Circuit Breaker Threshold: 5%
```

### Advanced Settings

#### Market Timing
```
Trading Window Start: 09:30 AM
Trading Window End: 03:00 PM
Pre-Market Scanning: ON
After-Hours Monitoring: OFF
Weekend Processing: OFF
```

#### Order Management
```
Order Type: GTT (Good Till Triggered)
Stop Loss Type: Percentage
Profit Target Type: Risk-Reward Ratio
Slippage Tolerance: 0.5%
Order Timeout: 60 minutes
```

#### Filters and Screening
```
Minimum Market Cap: ₹1,000 Cr
Maximum Market Cap: ₹50,000 Cr
Sector Filters: All Enabled
Liquidity Requirement: High
Beta Range: 0.5 - 2.0
```

## Portfolio Management

### Position Monitoring

#### Active Positions Table
The active positions table shows:
- **Symbol**: Stock symbol and company name
- **Quantity**: Number of shares
- **Entry Price**: Average entry price
- **Current Price**: Live market price
- **P&L**: Unrealized profit/loss
- **Duration**: Time in position
- **Stop Loss**: Current stop-loss level
- **Target**: Profit target level

#### Position Actions
For each position, you can:
- **Close Position**: Manually exit the position
- **Modify Stop Loss**: Adjust stop-loss level
- **Update Target**: Change profit target
- **Add to Position**: Increase position size
- **View Details**: Detailed position information

### Order Management

#### Order Status Types
- **Pending**: Order placed but not yet triggered
- **Triggered**: Order conditions met, executing
- **Filled**: Order successfully executed
- **Partial**: Partially filled order
- **Cancelled**: Order cancelled by system or user
- **Rejected**: Order rejected by exchange

#### Order Actions
- **Cancel Pending Orders**: Cancel untriggered orders
- **Modify Orders**: Change price or quantity
- **View Order Details**: Complete order information
- **Repeat Order**: Place similar order

### Performance Analytics

#### Key Performance Metrics
- **Total Return**: Overall portfolio return
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Ratio of gross profit to gross loss
- **Average Win**: Average profit per winning trade
- **Average Loss**: Average loss per losing trade
- **Sharpe Ratio**: Risk-adjusted return measure
- **Maximum Drawdown**: Largest peak-to-trough decline

#### Performance Charts
- **Equity Curve**: Portfolio value over time
- **Daily P&L**: Daily profit/loss chart
- **Win/Loss Distribution**: Trade outcome distribution
- **Monthly Returns**: Calendar heat map of returns

## Risk Management

### Risk Monitoring Dashboard

#### Real-time Risk Metrics
- **Portfolio Risk**: Total portfolio risk exposure
- **Concentration Risk**: Largest position percentage
- **Sector Exposure**: Risk by sector allocation
- **Correlation Risk**: Portfolio correlation matrix
- **VaR (Value at Risk)**: Potential loss estimation

#### Risk Alerts
The system monitors and alerts for:
- **Position Limit Breach**: Too many open positions
- **Loss Limit Approach**: Nearing daily/weekly loss limits
- **Concentration Risk**: Single position too large
- **High Correlation**: Positions moving together
- **Circuit Breaker**: Rapid portfolio decline

### Risk Controls Configuration

#### Daily Limits
```
Maximum Daily Loss: ₹10,000
Circuit Breaker: 5% portfolio decline
Emergency Stop: Manual override capability
Loss Limit Actions: Stop trading, close positions
```

#### Position Limits
```
Maximum Positions: 5
Single Position Limit: 20% of portfolio
Sector Concentration: 40% maximum
Correlation Limit: 0.7 maximum
```

#### Automatic Risk Actions
When limits are breached:
1. **Warning Alerts**: Sent via configured channels
2. **Trading Suspension**: New trades blocked
3. **Position Closure**: Automatic position exits
4. **System Shutdown**: Complete trading halt

## Notifications and Alerts

### Alert Types

#### Trading Alerts
- **Gap Detected**: New earnings gap opportunity
- **Trade Executed**: Position entry/exit notifications
- **Target Hit**: Profit target achieved
- **Stop Loss Hit**: Stop-loss triggered
- **Order Status**: Order fill/rejection notifications

#### Risk Alerts
- **Loss Limit Warning**: Approaching loss limits
- **Position Limit**: Too many open positions
- **Circuit Breaker**: Rapid portfolio decline
- **Margin Call**: Insufficient margin warning
- **System Error**: Technical issues detected

#### System Alerts
- **Market Status**: Market open/close notifications
- **Service Health**: System component status
- **API Issues**: External service problems
- **Backup Status**: Backup success/failure
- **Update Available**: Software updates

### Notification Channels

#### Email Notifications
Configure email alerts:
```
Email Address: trader@yourdomain.com
Alert Types: All Critical Alerts
Frequency: Immediate
Format: HTML with charts
Attachment: Daily reports
```

#### Telegram Integration
Set up Telegram bot:
```
Bot Token: Your bot token
Chat ID: Your chat ID
Alert Level: Info and above
Commands Enabled: Yes
Approval Required: For large trades
```

#### Webhook Integration
For custom integrations:
```
Webhook URL: https://your-service.com/webhook
Authentication: Bearer token
Retry Logic: 3 attempts
Timeout: 30 seconds
```

## Telegram Integration

### Bot Setup

#### Creating Your Telegram Bot
1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Follow instructions to create your bot
4. Save the **Bot Token** for configuration
5. Get your **Chat ID** by messaging the bot

#### Bot Configuration
In your system settings:
```
Telegram Bot Token: YOUR_BOT_TOKEN
Chat IDs: YOUR_CHAT_ID,GROUP_CHAT_ID
Approval Required: Yes (for safety)
Command Access: Restricted to your Chat ID
```

### Available Commands

#### Status Commands
- `/status` - Get overall system status
- `/positions` - View current positions
- `/pnl` - Today's profit/loss summary
- `/balance` - Account balance information
- `/health` - System health check

#### Trading Commands
- `/stop` - Stop automated trading
- `/resume` - Resume automated trading
- `/pause` - Pause for specified time
- `/emergency` - Emergency stop all trading

#### Information Commands
- `/signals` - Recent trading signals
- `/trades` - Recent trade history
- `/alerts` - Active alerts and warnings
- `/config` - Current configuration summary

#### Approval Commands
When trade approval is required:
- `/approve [trade_id]` - Approve pending trade
- `/reject [trade_id]` - Reject pending trade
- `/approve_all` - Approve all pending trades

### Interactive Features

#### Trade Approval Workflow
1. System detects trading opportunity
2. Telegram message sent with trade details
3. User reviews trade information
4. User approves or rejects via Telegram
5. System executes or cancels based on response

#### Real-time Notifications
Receive instant notifications for:
- New gap opportunities detected
- Trades executed or closed
- Risk limits approached
- System errors or warnings

## Performance Monitoring

### Performance Dashboard

#### Key Metrics Display
- **Today's P&L**: Current day performance
- **Week to Date**: Weekly performance
- **Month to Date**: Monthly performance
- **Year to Date**: Annual performance
- **All Time**: Complete performance history

#### Performance Charts
- **Equity Curve**: Portfolio growth over time
- **Drawdown Chart**: Peak-to-trough declines
- **Rolling Returns**: Performance over rolling periods
- **Risk-Return Scatter**: Risk vs. return analysis

### Detailed Analytics

#### Trade Analysis
- **Win/Loss Ratio**: Percentage of winning trades
- **Average Trade**: Mean profit/loss per trade
- **Best/Worst Trade**: Highest profit/loss trades
- **Trade Duration**: Average holding periods
- **Entry/Exit Analysis**: Timing analysis

#### Risk Metrics
- **Sharpe Ratio**: Risk-adjusted returns
- **Sortino Ratio**: Downside risk adjustment
- **Maximum Drawdown**: Largest decline
- **Volatility**: Return volatility measure
- **Beta**: Market correlation

#### Strategy Performance
- **Signal Accuracy**: Signal prediction accuracy
- **Gap Performance**: Performance by gap size
- **Sector Performance**: Returns by sector
- **Time Analysis**: Performance by time periods

### Reports and Exports

#### Daily Reports
Automatically generated daily reports include:
- Trading summary
- P&L analysis
- Risk metrics
- Position details
- Market observations

#### Weekly/Monthly Reports
Comprehensive periodic reports with:
- Performance summary
- Risk analysis
- Strategy review
- Recommendations
- Market outlook

#### Export Options
- **CSV Export**: Raw trading data
- **PDF Reports**: Formatted reports
- **Excel Files**: Detailed analysis
- **JSON Data**: API integrations

## Troubleshooting

### Common Issues and Solutions

#### Trading Not Working

**Issue**: System not detecting gaps or placing trades
**Solutions**:
1. Check if paper trading mode is enabled
2. Verify API credentials are correct
3. Ensure market is open during trading hours
4. Check if trading is paused or stopped
5. Review log files for errors

#### Position Not Closing

**Issue**: Stop-loss or profit target not triggering
**Solutions**:
1. Verify order is placed and active
2. Check if order was modified or cancelled
3. Ensure sufficient margin for order execution
4. Review order status in orders section
5. Manually close position if needed

#### Missing Notifications

**Issue**: Not receiving Telegram or email alerts
**Solutions**:
1. Verify notification settings are enabled
2. Check Telegram bot token and chat ID
3. Ensure email settings are correct
4. Test notification system manually
5. Check spam/junk folders for emails

#### Poor Performance

**Issue**: Strategy underperforming or losing money
**Solutions**:
1. Review and adjust strategy parameters
2. Increase minimum confidence threshold
3. Reduce position sizes
4. Tighten stop-loss levels
5. Consider market conditions and volatility

#### High System Usage

**Issue**: System using too much CPU or memory
**Solutions**:
1. Restart the application
2. Check for memory leaks in logs
3. Reduce scanning frequency
4. Optimize database queries
5. Upgrade system resources

### Getting Support

#### Before Contacting Support
1. Check this user guide
2. Review log files for errors
3. Try basic troubleshooting steps
4. Document the issue with screenshots
5. Note exact error messages

#### Support Channels
- **Documentation**: Check README and guides
- **GitHub Issues**: Report bugs and feature requests
- **Email Support**: support@yourdomain.com
- **Telegram Group**: Community support channel

## Best Practices

### Trading Best Practices

#### Risk Management
1. **Start Small**: Begin with small position sizes
2. **Diversify**: Don't put all capital in one trade
3. **Use Stop Losses**: Always protect against large losses
4. **Monitor Performance**: Regularly review and adjust
5. **Stay Disciplined**: Follow your trading plan

#### Strategy Optimization
1. **Paper Trade First**: Test strategies without risk
2. **Gradual Scaling**: Increase size as confidence grows
3. **Regular Reviews**: Analyze performance monthly
4. **Market Adaptation**: Adjust for changing conditions
5. **Continuous Learning**: Stay updated on market trends

#### System Management
1. **Regular Updates**: Keep system updated
2. **Backup Data**: Ensure data is backed up
3. **Monitor Health**: Check system status daily
4. **Test Disaster Recovery**: Practice recovery procedures
5. **Document Changes**: Keep configuration history

### Security Best Practices

#### Account Security
1. **Strong Passwords**: Use complex, unique passwords
2. **Two-Factor Authentication**: Enable where possible
3. **API Key Security**: Protect and rotate API keys
4. **Access Control**: Limit who can access system
5. **Regular Audits**: Review access logs

#### System Security
1. **Keep Updated**: Install security updates promptly
2. **Firewall Protection**: Use proper firewall rules
3. **Secure Communication**: Use HTTPS/SSL everywhere
4. **Regular Backups**: Maintain secure backups
5. **Monitor Logs**: Watch for suspicious activity

## Frequently Asked Questions

### General Questions

**Q: Is the system suitable for beginners?**
A: The system is designed for users with some trading knowledge. We recommend starting with paper trading and understanding the basics of gap trading before using real money.

**Q: How much capital do I need to start?**
A: The minimum recommended capital is ₹1,00,000, but you can start with less in paper trading mode. Ensure you never risk more than you can afford to lose.

**Q: What markets does the system support?**
A: Currently, the system supports NSE (National Stock Exchange) equities through Zerodha Kite Connect API.

### Technical Questions

**Q: Can I run this on a VPS or cloud server?**
A: Yes, the system is designed for deployment on VPS, cloud servers, or dedicated hardware. See the deployment guide for details.

**Q: How often does the system scan for opportunities?**
A: The system scans continuously during market hours, with configurable intervals (default: every 30 seconds for gap detection).

**Q: Can I customize the trading strategy?**
A: Yes, many parameters are configurable including gap thresholds, risk parameters, timing settings, and filters.

### Trading Questions

**Q: How does the gap detection work?**
A: The system monitors earnings announcements and detects significant price gaps between previous close and current price, validated with volume and technical indicators.

**Q: What happens if my internet connection drops?**
A: The system includes reconnection logic and will attempt to maintain positions. Consider running on a VPS for better reliability.

**Q: Can I override automatic trades?**
A: Yes, you can enable manual approval mode, manually close positions, or stop automated trading at any time.

### Risk Questions

**Q: How are stop-losses handled?**
A: The system uses GTT (Good Till Triggered) orders for stop-losses, which remain active even if the system is offline.

**Q: What if I exceed my daily loss limit?**
A: The system will automatically stop trading and can close existing positions based on your configuration.

**Q: How is position sizing calculated?**
A: Position sizing can be based on fixed amounts, percentage of account, or risk-based calculations considering stop-loss distance.

---

**Need Additional Help?**

If you need further assistance:
1. Check the troubleshooting section
2. Review the deployment and setup guides
3. Contact support with specific details
4. Join our community channels for peer support

**Remember**: Always trade responsibly and never risk more than you can afford to lose.

---

**Last Updated**: January 2024  
**Version**: 1.0  
**Next Update**: Based on user feedback