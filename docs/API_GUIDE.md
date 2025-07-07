# Earnings Gap Trader - API Guide

This guide covers the REST API endpoints, WebSocket connections, and integration patterns for the Earnings Gap Trader system.

## Table of Contents

- [Authentication](#authentication)
- [REST API Endpoints](#rest-api-endpoints)
- [WebSocket API](#websocket-api)
- [Data Models](#data-models)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Examples](#examples)

## Authentication

### API Key Authentication

All API requests require authentication using API keys or session tokens.

```http
Authorization: Bearer your_api_token
Content-Type: application/json
```

### Session Authentication

For web interface access, use session-based authentication:

```python
import requests

# Login
response = requests.post('/auth/login', {
    'username': 'your_username',
    'password': 'your_password'
})

# Use session cookie for subsequent requests
session = requests.Session()
session.cookies.update(response.cookies)
```

## REST API Endpoints

### System Endpoints

#### Get System Status
```http
GET /api/system/status
```

**Response:**
```json
{
    "status": "online",
    "trading_active": true,
    "market_open": true,
    "paper_trading": false,
    "scanner_active": true,
    "uptime": "2h 15m 30s",
    "last_scan": "2024-01-15T10:30:00Z"
}
```

#### Start/Stop Trading
```http
POST /api/system/trading/start
POST /api/system/trading/stop
```

**Request:**
```json
{
    "reason": "Manual start/stop",
    "force": false
}
```

#### System Health Check
```http
GET /api/health
```

**Response:**
```json
{
    "status": "healthy",
    "database": "connected",
    "kite_api": "connected",
    "telegram": "connected",
    "memory_usage": "45%",
    "cpu_usage": "12%"
}
```

### Portfolio Endpoints

#### Get Portfolio Summary
```http
GET /api/portfolio/summary
```

**Response:**
```json
{
    "balance": 100000.00,
    "equity": 100000.00,
    "margin_available": 75000.00,
    "margin_used": 25000.00,
    "day_pnl": 1250.00,
    "total_pnl": 15750.00,
    "positions_count": 3,
    "trades_today": 5
}
```

#### Get Current Positions
```http
GET /api/portfolio/positions
```

**Response:**
```json
{
    "positions": [
        {
            "id": 1,
            "symbol": "RELIANCE",
            "quantity": 50,
            "average_price": 2450.00,
            "current_price": 2465.00,
            "pnl": 750.00,
            "unrealized_pnl": 750.00,
            "position_type": "LONG",
            "created_at": "2024-01-15T10:15:00Z"
        }
    ],
    "total_pnl": 750.00
}
```

### Trading Endpoints

#### Get All Trades
```http
GET /api/trades?limit=50&offset=0&status=all
```

**Query Parameters:**
- `limit`: Number of trades to return (default: 50, max: 200)
- `offset`: Pagination offset (default: 0)
- `status`: Filter by status (all, open, closed, cancelled)
- `symbol`: Filter by symbol
- `strategy`: Filter by strategy
- `date_from`: Start date (ISO format)
- `date_to`: End date (ISO format)

**Response:**
```json
{
    "trades": [
        {
            "id": 1,
            "symbol": "RELIANCE",
            "trade_type": "BUY",
            "quantity": 50,
            "entry_price": 2450.00,
            "exit_price": 2465.00,
            "stop_loss": 2400.00,
            "target_price": 2500.00,
            "status": "CLOSED",
            "strategy": "earnings_gap",
            "pnl": 750.00,
            "entry_time": "2024-01-15T10:15:00Z",
            "exit_time": "2024-01-15T11:30:00Z",
            "duration_minutes": 75
        }
    ],
    "total": 1,
    "page": 1,
    "pages": 1
}
```

#### Place Manual Trade
```http
POST /api/trades
```

**Request:**
```json
{
    "symbol": "RELIANCE",
    "trade_type": "BUY",
    "quantity": 10,
    "order_type": "MARKET",
    "price": null,
    "stop_loss": 2400.00,
    "target_price": 2500.00,
    "strategy": "manual"
}
```

**Response:**
```json
{
    "trade_id": 1,
    "status": "placed",
    "message": "Trade order placed successfully",
    "order_id": "240115000001"
}
```

#### Close Trade
```http
POST /api/trades/{trade_id}/close
```

**Request:**
```json
{
    "reason": "manual_close",
    "order_type": "MARKET"
}
```

### Gap Detection Endpoints

#### Get Recent Gaps
```http
GET /api/gaps?limit=20&min_gap=3.0
```

**Query Parameters:**
- `limit`: Number of gaps to return
- `min_gap`: Minimum gap percentage
- `date_from`: Start date for gap detection
- `symbols`: Comma-separated list of symbols

**Response:**
```json
{
    "gaps": [
        {
            "symbol": "RELIANCE",
            "company_name": "Reliance Industries",
            "gap_percent": 4.2,
            "pre_earnings_close": 2350.00,
            "post_earnings_open": 2450.00,
            "current_price": 2465.00,
            "volume": 1500000,
            "volume_ratio": 2.5,
            "detected_at": "2024-01-15T09:15:00Z",
            "earnings_date": "2024-01-14T00:00:00Z"
        }
    ],
    "total": 1
}
```

#### Trigger Manual Gap Scan
```http
POST /api/gaps/scan
```

**Request:**
```json
{
    "symbols": ["RELIANCE", "TCS", "INFY"],
    "min_gap_percent": 3.0,
    "earnings_window_days": 2
}
```

### Configuration Endpoints

#### Get Trading Configuration
```http
GET /api/config/trading
```

**Response:**
```json
{
    "max_position_size": 10000.00,
    "risk_per_trade": 0.02,
    "stop_loss_percentage": 0.05,
    "target_percentage": 0.10,
    "max_daily_loss": 5000.00,
    "max_open_positions": 5,
    "min_gap_percentage": 0.03,
    "max_gap_percentage": 0.15,
    "auto_trading_enabled": true,
    "paper_trading_mode": false
}
```

#### Update Trading Configuration
```http
PUT /api/config/trading
```

**Request:**
```json
{
    "max_position_size": 15000.00,
    "risk_per_trade": 0.025,
    "stop_loss_percentage": 0.04,
    "target_percentage": 0.12
}
```

#### Get API Configuration
```http
GET /api/config/api
```

**Response:**
```json
{
    "kite_api_connected": true,
    "telegram_enabled": true,
    "market_data_provider": "kite",
    "update_interval": 5
}
```

### Analytics Endpoints

#### Get Performance Statistics
```http
GET /api/analytics/performance?period=30d
```

**Query Parameters:**
- `period`: Time period (1d, 7d, 30d, 90d, 1y)

**Response:**
```json
{
    "period": "30d",
    "total_trades": 45,
    "winning_trades": 28,
    "losing_trades": 17,
    "win_rate": 62.22,
    "total_pnl": 15750.00,
    "avg_win": 850.50,
    "avg_loss": -425.75,
    "max_win": 2500.00,
    "max_loss": -1200.00,
    "profit_factor": 1.85,
    "sharpe_ratio": 1.42,
    "max_drawdown": -3200.00
}
```

#### Get Daily P&L
```http
GET /api/analytics/pnl/daily?days=30
```

**Response:**
```json
{
    "daily_pnl": [
        {
            "date": "2024-01-15",
            "pnl": 1250.00,
            "trades": 3,
            "volume": 75000.00
        }
    ],
    "total_pnl": 15750.00,
    "best_day": 2500.00,
    "worst_day": -1200.00
}
```

## WebSocket API

### Connection

Connect to the WebSocket endpoint for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = function() {
    console.log('WebSocket connected');
    
    // Subscribe to updates
    ws.send(JSON.stringify({
        type: 'subscribe',
        payload: {
            subscriptions: [
                'price_updates',
                'gap_alerts',
                'trade_updates',
                'portfolio_updates'
            ]
        }
    }));
};
```

### Message Types

#### Price Updates
```json
{
    "type": "price_update",
    "payload": {
        "symbol": "RELIANCE",
        "price": 2465.00,
        "change": 15.00,
        "change_percent": 0.61,
        "volume": 1500000,
        "timestamp": "2024-01-15T10:30:00Z"
    }
}
```

#### Gap Alerts
```json
{
    "type": "gap_alert",
    "payload": {
        "symbol": "RELIANCE",
        "gap_percent": 4.2,
        "price": 2465.00,
        "company_name": "Reliance Industries",
        "detected_at": "2024-01-15T09:15:00Z"
    }
}
```

#### Trade Updates
```json
{
    "type": "trade_update",
    "payload": {
        "trade_id": 1,
        "symbol": "RELIANCE",
        "action": "opened",
        "status": "OPEN",
        "pnl": 0.00,
        "timestamp": "2024-01-15T10:15:00Z"
    }
}
```

#### Portfolio Updates
```json
{
    "type": "portfolio_update",
    "payload": {
        "balance": 98750.00,
        "day_pnl": 1250.00,
        "margin_used": 26250.00,
        "positions_count": 3,
        "timestamp": "2024-01-15T10:30:00Z"
    }
}
```

#### System Alerts
```json
{
    "type": "system_alert",
    "payload": {
        "level": "WARNING",
        "message": "Daily loss limit reached 80%",
        "timestamp": "2024-01-15T14:30:00Z"
    }
}
```

### Subscription Management

```javascript
// Subscribe to specific updates
ws.send(JSON.stringify({
    type: 'subscribe',
    payload: {
        subscriptions: ['price_updates'],
        symbols: ['RELIANCE', 'TCS']  // Optional symbol filter
    }
}));

// Unsubscribe
ws.send(JSON.stringify({
    type: 'unsubscribe',
    payload: {
        subscriptions: ['gap_alerts']
    }
}));
```

## Data Models

### Trade Model
```typescript
interface Trade {
    id: number;
    symbol: string;
    trade_type: 'BUY' | 'SELL';
    quantity: number;
    entry_price: number;
    exit_price?: number;
    stop_loss: number;
    target_price: number;
    status: 'PENDING' | 'OPEN' | 'CLOSED' | 'CANCELLED';
    strategy: string;
    pnl: number;
    fees: number;
    entry_time: string;
    exit_time?: string;
    notes?: string;
}
```

### Order Model
```typescript
interface Order {
    id: number;
    trade_id: number;
    order_id: string;
    symbol: string;
    order_type: 'MARKET' | 'LIMIT' | 'SL' | 'SL-M';
    transaction_type: 'BUY' | 'SELL';
    quantity: number;
    price?: number;
    trigger_price?: number;
    status: 'PENDING' | 'PLACED' | 'COMPLETE' | 'CANCELLED' | 'REJECTED';
    filled_quantity: number;
    average_price?: number;
    placed_at: string;
}
```

### Gap Model
```typescript
interface Gap {
    symbol: string;
    company_name: string;
    gap_percent: number;
    pre_earnings_close: number;
    post_earnings_open: number;
    current_price: number;
    volume: number;
    volume_ratio: number;
    detected_at: string;
    earnings_date: string;
}
```

## Error Handling

### HTTP Status Codes

- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `422`: Validation Error
- `429`: Rate Limited
- `500`: Internal Server Error

### Error Response Format

```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid trade parameters",
        "details": {
            "symbol": "Symbol is required",
            "quantity": "Quantity must be positive"
        },
        "timestamp": "2024-01-15T10:30:00Z"
    }
}
```

### Common Error Codes

- `INVALID_CREDENTIALS`: Authentication failed
- `INSUFFICIENT_BALANCE`: Not enough funds
- `POSITION_LIMIT_EXCEEDED`: Too many open positions
- `INVALID_SYMBOL`: Symbol not found or invalid
- `MARKET_CLOSED`: Trading not allowed when market is closed
- `RISK_LIMIT_EXCEEDED`: Trade violates risk management rules
- `API_ERROR`: External API error (Kite Connect)

## Rate Limiting

### Limits

- REST API: 100 requests per minute per IP
- WebSocket: 50 messages per minute per connection
- Kite API: Subject to Zerodha's rate limits

### Headers

Rate limit information is included in response headers:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642248000
```

### Handling Rate Limits

```python
import time
import requests

def api_request_with_retry(url, data=None, max_retries=3):
    for attempt in range(max_retries):
        response = requests.post(url, json=data)
        
        if response.status_code == 429:
            # Rate limited, wait and retry
            retry_after = int(response.headers.get('Retry-After', 60))
            time.sleep(retry_after)
            continue
        
        return response
    
    raise Exception("Max retries exceeded")
```

## Examples

### Python Client Example

```python
import requests
import websocket
import json

class EarningsGapTraderClient:
    def __init__(self, base_url, api_token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
    
    def get_system_status(self):
        response = requests.get(
            f'{self.base_url}/api/system/status',
            headers=self.headers
        )
        return response.json()
    
    def place_trade(self, symbol, quantity, trade_type='BUY'):
        data = {
            'symbol': symbol,
            'quantity': quantity,
            'trade_type': trade_type,
            'order_type': 'MARKET'
        }
        response = requests.post(
            f'{self.base_url}/api/trades',
            headers=self.headers,
            json=data
        )
        return response.json()
    
    def get_positions(self):
        response = requests.get(
            f'{self.base_url}/api/portfolio/positions',
            headers=self.headers
        )
        return response.json()
    
    def connect_websocket(self):
        def on_message(ws, message):
            data = json.loads(message)
            print(f"Received: {data}")
        
        def on_open(ws):
            # Subscribe to updates
            ws.send(json.dumps({
                'type': 'subscribe',
                'payload': {
                    'subscriptions': ['trade_updates', 'gap_alerts']
                }
            }))
        
        ws_url = self.base_url.replace('http', 'ws') + '/ws'
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_open=on_open
        )
        ws.run_forever()

# Usage
client = EarningsGapTraderClient('http://localhost:8000', 'your_api_token')
status = client.get_system_status()
print(status)
```

### JavaScript Client Example

```javascript
class EarningsGapTraderClient {
    constructor(baseUrl, apiToken) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${apiToken}`,
            'Content-Type': 'application/json'
        };
    }
    
    async getSystemStatus() {
        const response = await fetch(`${this.baseUrl}/api/system/status`, {
            headers: this.headers
        });
        return response.json();
    }
    
    async placeTrade(symbol, quantity, tradeType = 'BUY') {
        const response = await fetch(`${this.baseUrl}/api/trades`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({
                symbol,
                quantity,
                trade_type: tradeType,
                order_type: 'MARKET'
            })
        });
        return response.json();
    }
    
    connectWebSocket() {
        const wsUrl = this.baseUrl.replace('http', 'ws') + '/ws';
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            ws.send(JSON.stringify({
                type: 'subscribe',
                payload: {
                    subscriptions: ['trade_updates', 'gap_alerts']
                }
            }));
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Received:', data);
        };
        
        return ws;
    }
}

// Usage
const client = new EarningsGapTraderClient('http://localhost:8000', 'your_api_token');
client.getSystemStatus().then(console.log);
```

### cURL Examples

```bash
# Get system status
curl -H "Authorization: Bearer your_api_token" \
     http://localhost:8000/api/system/status

# Place a trade
curl -X POST \
     -H "Authorization: Bearer your_api_token" \
     -H "Content-Type: application/json" \
     -d '{"symbol":"RELIANCE","quantity":10,"trade_type":"BUY","order_type":"MARKET"}' \
     http://localhost:8000/api/trades

# Get recent gaps
curl -H "Authorization: Bearer your_api_token" \
     "http://localhost:8000/api/gaps?limit=10&min_gap=3.0"

# Update trading config
curl -X PUT \
     -H "Authorization: Bearer your_api_token" \
     -H "Content-Type: application/json" \
     -d '{"max_position_size":15000,"risk_per_trade":0.025}' \
     http://localhost:8000/api/config/trading
```

## Integration Patterns

### Webhook Integration

Set up webhooks for external notifications:

```python
# webhook_handler.py
from flask import Flask, request
import requests

app = Flask(__name__)

@app.route('/webhook/gap_detected', methods=['POST'])
def handle_gap_detection():
    data = request.json
    
    # Process gap detection
    symbol = data['symbol']
    gap_percent = data['gap_percent']
    
    # Send to external system
    external_api_call(symbol, gap_percent)
    
    return {'status': 'processed'}

def external_api_call(symbol, gap_percent):
    # Send to Discord, Slack, etc.
    pass
```

### Custom Strategy Integration

```python
# custom_strategy.py
from core.earnings_scanner import EarningsScanner

class CustomEarningsStrategy:
    def __init__(self):
        self.scanner = EarningsScanner()
    
    async def analyze_gap(self, gap_data):
        # Custom analysis logic
        symbol = gap_data['symbol']
        gap_percent = gap_data['gap_percent']
        
        # Technical analysis
        indicators = await self.scanner.get_technical_indicators(symbol)
        
        # Custom scoring
        score = self.calculate_score(gap_data, indicators)
        
        return {
            'should_trade': score > 0.7,
            'score': score,
            'reasoning': 'High volume with RSI support'
        }
    
    def calculate_score(self, gap_data, indicators):
        # Implement custom scoring logic
        pass
```

---

For more information, see the [Setup Guide](SETUP.md) or contact support.