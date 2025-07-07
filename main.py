#!/usr/bin/env python3
"""
Main FastAPI application for the earnings gap trading system
Orchestrates all components with WebSocket support for real-time dashboard
"""
import asyncio
import json
import os
import sys
import signal
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
import traceback
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
import psutil

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.market_data import MarketDataManager, market_data_manager
from core.earnings_scanner import get_earnings_gap_scanner, EarningsGapScanner
from core.risk_manager import get_risk_manager, RiskManager
from core.order_engine import get_order_engine, OrderEngine
from core.telegram_service import TelegramBot, TelegramConfig, TradingMode
from database import get_db_session, test_database_connection
from config import get_config
from utils.logging_config import get_logger

# Global instances
app_logger = get_logger(__name__)
config = get_config()

# Global application state
class AppState:
    def __init__(self):
        self.market_data_manager: Optional[MarketDataManager] = None
        self.earnings_scanner: Optional[EarningsGapScanner] = None
        self.risk_manager: Optional[RiskManager] = None
        self.order_engine: Optional[OrderEngine] = None
        self.telegram_bot: Optional[TelegramBot] = None
        self.trading_active: bool = False
        self.trading_mode: TradingMode = TradingMode.MANUAL
        self.emergency_stop: bool = False
        self.system_healthy: bool = False
        self.last_heartbeat: datetime = datetime.now()
        self.performance_metrics: Dict[str, Any] = {}
        self.component_health: Dict[str, bool] = {}
        self.websocket_connections: Set[WebSocket] = set()
        self.trading_task: Optional[asyncio.Task] = None

app_state = AppState()


class WebSocketConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.connection_count = 0
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.connection_count += 1
        app_logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
        
        # Send initial system status
        await self.send_personal_message(websocket, {
            "type": "system_status",
            "data": await get_system_status()
        })
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            app_logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """Send message to specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            app_logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast_message(self, message: dict):
        """Broadcast message to all connected WebSocket clients"""
        if not self.active_connections:
            return
        
        message_text = json.dumps(message)
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_text)
            except Exception as e:
                app_logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.add(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_signal_alert(self, signal_data: dict):
        """Broadcast new signal alert"""
        await self.broadcast_message({
            "type": "signal_alert",
            "data": signal_data,
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_trade_update(self, trade_data: dict):
        """Broadcast trade execution update"""
        await self.broadcast_message({
            "type": "trade_update",
            "data": trade_data,
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_pnl_update(self, pnl_data: dict):
        """Broadcast P&L update"""
        await self.broadcast_message({
            "type": "pnl_update",
            "data": pnl_data,
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_system_status(self, status_data: dict):
        """Broadcast system status update"""
        await self.broadcast_message({
            "type": "system_status",
            "data": status_data,
            "timestamp": datetime.now().isoformat()
        })

# Global WebSocket manager
websocket_manager = WebSocketConnectionManager()


# Pydantic models for API requests/responses
class SystemStatusResponse(BaseModel):
    trading_active: bool
    trading_mode: str
    emergency_stop: bool
    system_healthy: bool
    last_heartbeat: datetime
    active_trades: int
    total_pnl: float
    component_health: Dict[str, bool]
    websocket_connections: int


class PerformanceMetrics(BaseModel):
    daily_trades: int
    daily_pnl: float
    win_rate: float
    total_portfolio_value: float
    best_performer: Optional[str]
    worst_performer: Optional[str]
    risk_metrics: Dict[str, float]


class EmergencyStopRequest(BaseModel):
    reason: str = "Manual emergency stop"
    force: bool = False


class TradingModeRequest(BaseModel):
    mode: str = Field(..., pattern="^(AUTO|MANUAL|PAUSED)$")


class ConfigurationUpdate(BaseModel):
    key: str
    value: Any
    component: Optional[str] = None


class FullConfigurationRequest(BaseModel):
    api: Optional[Dict[str, Any]] = None
    trading: Optional[Dict[str, Any]] = None
    risk: Optional[Dict[str, Any]] = None
    telegram: Optional[Dict[str, Any]] = None
    scanner: Optional[Dict[str, Any]] = None


class TokenGenerationRequest(BaseModel):
    api_key: str
    api_secret: str
    request_token: str


class ApiTestRequest(BaseModel):
    api_key: str
    access_token: str


class TelegramTestRequest(BaseModel):
    bot_token: str
    chat_ids: List[str]


async def update_env_file(updates: Dict[str, str]):
    """Update .env file with new configuration values"""
    import os
    
    env_file_path = ".env"
    
    # Read current .env file
    env_lines = []
    if os.path.exists(env_file_path):
        with open(env_file_path, 'r', encoding='utf-8') as f:
            env_lines = f.readlines()
    
    # Create a dictionary of existing values
    existing_vars = {}
    for i, line in enumerate(env_lines):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            existing_vars[key] = i
    
    # Update existing variables or add new ones
    for key, value in updates.items():
        line_content = f"{key}={value}\n"
        if key in existing_vars:
            # Update existing line
            env_lines[existing_vars[key]] = line_content
        else:
            # Add new line
            env_lines.append(line_content)
    
    # Write back to file
    with open(env_file_path, 'w', encoding='utf-8') as f:
        f.writelines(env_lines)


async def initialize_components():
    """Initialize all trading system components"""
    app_logger.info("Initializing trading system components...")
    
    try:
        # Test database connection
        if test_database_connection():
            app_logger.info("✅ Database connection verified")
        else:
            app_logger.warning("⚠️ Database connection failed")
        
        # Initialize market data manager
        app_state.market_data_manager = market_data_manager
        await app_state.market_data_manager.initialize()
        app_state.component_health["market_data"] = True
        app_logger.info("✅ Market data manager initialized")
        
        # Initialize risk manager
        app_state.risk_manager = await get_risk_manager()
        app_state.component_health["risk_manager"] = True
        app_logger.info("✅ Risk manager initialized")
        
        # Initialize order engine
        if not config.kite_api_key or not config.kite_access_token:
            app_logger.error("❌ Production requires valid API credentials")
            raise ValueError("Missing required API credentials for production deployment")
        
        app_state.order_engine = await get_order_engine(
            api_key=config.kite_api_key.get_secret_value(),
            access_token=config.kite_access_token.get_secret_value(),
            risk_manager=app_state.risk_manager,
            market_data_manager=app_state.market_data_manager,
            paper_trading=config.paper_trading
        )
        app_state.component_health["order_engine"] = True
        app_logger.info("✅ Order engine initialized")
        
        # Initialize earnings scanner
        app_state.earnings_scanner = await get_earnings_gap_scanner()
        app_state.component_health["earnings_scanner"] = True
        app_logger.info("✅ Earnings scanner initialized")
        
        # Initialize Telegram bot (only if enabled)
        telegram_enabled = getattr(config, 'telegram_enabled', False)
        if telegram_enabled:
            telegram_config = TelegramConfig(
                bot_token=getattr(config, 'telegram_bot_token', None) and str(config.telegram_bot_token.get_secret_value()) or "",
                chat_ids=getattr(config, 'telegram_chat_id', None) and [config.telegram_chat_id] or [],
                approval_timeout=300
            )
            
            if telegram_config.bot_token and telegram_config.chat_ids:
                app_state.telegram_bot = TelegramBot(
                    telegram_config,
                    app_state.order_engine,
                    app_state.risk_manager
                )
                await app_state.telegram_bot.start()
                app_state.component_health["telegram_bot"] = True
                app_logger.info("✅ Telegram bot initialized")
            else:
                app_logger.warning("⚠️  Telegram bot configured but missing token or chat IDs")
                app_state.component_health["telegram_bot"] = False
        else:
            app_logger.info("📵 Telegram bot disabled in configuration")
            app_state.component_health["telegram_bot"] = False
        
        app_state.system_healthy = True
        app_logger.info("🚀 All components initialized successfully")
        
    except Exception as e:
        app_logger.error(f"❌ Component initialization failed: {e}")
        app_logger.error(traceback.format_exc())
        app_state.system_healthy = False
        raise


async def cleanup_components():
    """Cleanup all components during shutdown"""
    app_logger.info("Cleaning up trading system components...")
    
    try:
        # Stop trading loop
        if app_state.trading_task and not app_state.trading_task.done():
            app_state.trading_task.cancel()
            try:
                await app_state.trading_task
            except asyncio.CancelledError:
                pass
        
        # Cleanup components
        if app_state.telegram_bot:
            await app_state.telegram_bot.stop()
            app_logger.info("✅ Telegram bot cleaned up")
        
        if app_state.order_engine:
            await app_state.order_engine.cleanup()
            app_logger.info("✅ Order engine cleaned up")
        
        if app_state.earnings_scanner:
            await app_state.earnings_scanner.cleanup()
            app_logger.info("✅ Earnings scanner cleaned up")
        
        if app_state.market_data_manager:
            await app_state.market_data_manager.cleanup()
            app_logger.info("✅ Market data manager cleaned up")
        
        # Close all WebSocket connections
        for websocket in list(websocket_manager.active_connections):
            try:
                await websocket.close()
            except:
                pass
        websocket_manager.active_connections.clear()
        
        app_logger.info("🧹 All components cleaned up successfully")
        
    except Exception as e:
        app_logger.error(f"❌ Cleanup error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown"""
    # Startup
    try:
        await initialize_components()
        
        # Start background tasks
        if app_state.system_healthy:
            # Start trading loop
            app_state.trading_task = asyncio.create_task(main_trading_loop())
            
            # Start health monitoring
            asyncio.create_task(health_monitoring_loop())
            
            # Start performance monitoring
            asyncio.create_task(performance_monitoring_loop())
        
        app_logger.info("🚀 FastAPI application startup complete")
        yield
        
    except Exception as e:
        app_logger.error(f"❌ Startup failed: {e}")
        raise
    finally:
        # Shutdown
        app_logger.info("🛑 Shutting down FastAPI application...")
        app_state.trading_active = False
        await cleanup_components()


# Create FastAPI application
app = FastAPI(
    title="Earnings Gap Trading System",
    description="Professional earnings gap trading system with real-time dashboard",
    version="1.0.0",
    lifespan=lifespan
)

# Production security settings
security = HTTPBearer(auto_error=False)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; font-src 'self' https://cdn.jsdelivr.net"
    return response

# Trusted hosts for production
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
)

# CORS middleware - restricted for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"] if config.debug else [],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Static files and templates
static_dir = Path(__file__).parent / "frontend" / "static"
templates_dir = Path(__file__).parent / "frontend" / "templates"

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

if templates_dir.exists():
    templates = Jinja2Templates(directory=templates_dir)


async def main_trading_loop():
    """Main trading loop that coordinates all components"""
    app_logger.info("🔄 Starting main trading loop...")
    app_state.trading_active = True
    
    loop_count = 0
    last_signal_scan = datetime.now() - timedelta(minutes=5)
    
    while app_state.trading_active and not app_state.emergency_stop:
        try:
            loop_count += 1
            app_state.last_heartbeat = datetime.now()
            
            # Check if market is open
            if not app_state.market_data_manager:
                await asyncio.sleep(30)
                continue
            
            market_status = await app_state.market_data_manager.get_market_status()
            if not market_status.get("is_open", False):
                await asyncio.sleep(60)  # Check every minute when market is closed
                continue
            
            # Scan for signals (every 5 minutes)
            current_time = datetime.now()
            if (current_time - last_signal_scan).total_seconds() >= 300:  # 5 minutes
                await scan_and_process_signals()
                last_signal_scan = current_time
            
            # Monitor existing positions
            await monitor_positions()
            
            # Update performance metrics every 10 loops
            if loop_count % 10 == 0:
                await update_performance_metrics()
            
            # Broadcast system status every 5 loops
            if loop_count % 5 == 0:
                await websocket_manager.send_system_status(await get_system_status())
            
            # Sleep before next iteration
            await asyncio.sleep(30)  # 30-second loop
            
        except asyncio.CancelledError:
            app_logger.info("🛑 Trading loop cancelled")
            break
        except Exception as e:
            app_logger.error(f"❌ Trading loop error: {e}")
            app_logger.error(traceback.format_exc())
            await asyncio.sleep(60)  # Wait longer on error
    
    app_state.trading_active = False
    app_logger.info("🔄 Trading loop stopped")


async def scan_and_process_signals():
    """Scan for signals and process them according to trading mode"""
    if not app_state.earnings_scanner or app_state.emergency_stop:
        return
    
    try:
        app_logger.info("🔍 Scanning for earnings gap signals...")
        
        # Scan for signals
        signals = await app_state.earnings_scanner.scan_for_signals()
        
        if not signals:
            app_logger.debug("No signals detected")
            return
        
        app_logger.info(f"📊 Found {len(signals)} potential signals")
        
        for signal in signals:
            try:
                # Risk validation
                is_valid, position_size, warnings = await app_state.risk_manager.validate_trade(signal)
                
                if not is_valid:
                    app_logger.warning(f"❌ Signal rejected by risk manager: {signal.symbol}")
                    continue
                
                # Broadcast signal alert
                signal_data = {
                    "symbol": signal.symbol,
                    "signal_type": signal.signal_type.value,
                    "confidence": signal.confidence.value,
                    "confidence_score": signal.confidence_score,
                    "entry_price": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "profit_target": signal.profit_target,
                    "gap_percent": signal.gap_percent,
                    "volume_ratio": signal.volume_ratio,
                    "position_size": position_size.final_size if position_size else 0
                }
                
                await websocket_manager.send_signal_alert(signal_data)
                
                # Process signal based on trading mode
                if app_state.trading_mode == TradingMode.AUTO:
                    # Automatic execution
                    trade_id = await app_state.order_engine.execute_signal(signal)
                    
                    if trade_id:
                        app_logger.info(f"✅ Auto-executed signal: {signal.symbol} (Trade: {trade_id})")
                        
                        # Notify via Telegram
                        if app_state.telegram_bot:
                            await app_state.telegram_bot.trade_notifier.notify_trade_entry(
                                symbol=signal.symbol,
                                entry_price=signal.entry_price,
                                quantity=int(position_size.final_size / signal.entry_price),
                                order_id=trade_id,
                                signal_id=signal.signal_id if hasattr(signal, 'signal_id') else f"auto_{trade_id}"
                            )
                        
                        # Broadcast trade update
                        await websocket_manager.send_trade_update({
                            "action": "entry",
                            "symbol": signal.symbol,
                            "trade_id": trade_id,
                            "entry_price": signal.entry_price,
                            "quantity": int(position_size.final_size / signal.entry_price),
                            "mode": "AUTO"
                        })
                    
                elif app_state.trading_mode == TradingMode.MANUAL:
                    # Manual approval required
                    if app_state.telegram_bot:
                        approval_sent = await app_state.telegram_bot.signal_notifier.send_signal_for_approval(
                            signal, f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        )
                        
                        if approval_sent:
                            app_logger.info(f"📱 Manual approval requested: {signal.symbol}")
                        else:
                            app_logger.warning(f"❌ Failed to send approval request: {signal.symbol}")
                
                elif app_state.trading_mode == TradingMode.PAUSED:
                    app_logger.info(f"⏸️  Signal ignored (trading paused): {signal.symbol}")
                
            except Exception as e:
                app_logger.error(f"❌ Error processing signal {signal.symbol}: {e}")
                app_logger.error(traceback.format_exc())
    
    except Exception as e:
        app_logger.error(f"❌ Signal scanning error: {e}")
        app_logger.error(traceback.format_exc())


async def monitor_positions():
    """Monitor existing positions and send updates"""
    if not app_state.order_engine:
        return
    
    try:
        positions = await app_state.order_engine.position_tracker.get_all_positions()
        
        if not positions:
            return
        
        total_pnl = 0
        position_updates = []
        
        for symbol, position in positions.items():
            total_pnl += position.pnl
            
            # Check for significant moves (>2% change)
            if abs(position.pnl_percent) > 2.0:
                position_updates.append({
                    "symbol": symbol,
                    "current_price": position.current_price,
                    "pnl": position.pnl,
                    "pnl_percent": position.pnl_percent,
                    "quantity": position.quantity,
                    "entry_price": position.entry_price
                })
                
                # Send Telegram notification for significant moves
                if app_state.telegram_bot:
                    await app_state.telegram_bot.trade_notifier.notify_pnl_update(
                        symbol=symbol,
                        current_price=position.current_price,
                        pnl=position.pnl,
                        pnl_percent=position.pnl_percent,
                        unrealized_pnl=position.unrealized_pnl
                    )
        
        # Broadcast P&L updates
        if position_updates:
            await websocket_manager.send_pnl_update({
                "positions": position_updates,
                "total_pnl": total_pnl,
                "timestamp": datetime.now().isoformat()
            })
        
        # Update app state
        app_state.performance_metrics["total_pnl"] = total_pnl
        app_state.performance_metrics["active_positions"] = len(positions)
    
    except Exception as e:
        app_logger.error(f"❌ Position monitoring error: {e}")


async def update_performance_metrics():
    """Update performance metrics"""
    try:
        if not app_state.order_engine:
            return
        
        # Get execution status
        status = await app_state.order_engine.get_execution_status()
        
        # Get positions
        positions = await app_state.order_engine.position_tracker.get_all_positions()
        
        # Calculate metrics
        total_pnl = sum(pos.pnl for pos in positions.values()) if positions else 0
        total_value = sum(pos.position_value for pos in positions.values()) if positions else 0
        
        # Update performance metrics
        app_state.performance_metrics.update({
            "active_trades": status.get("active_trades", 0),
            "total_trades": status.get("total_trades", 0),
            "total_pnl": total_pnl,
            "total_portfolio_value": total_value,
            "paper_trading": status.get("paper_trading", True),
            "success_rate": status.get("success_rate", 0),
            "last_updated": datetime.now().isoformat()
        })
        
        # Find best/worst performers
        if positions:
            best_performer = max(positions.values(), key=lambda p: p.pnl_percent)
            worst_performer = min(positions.values(), key=lambda p: p.pnl_percent)
            
            app_state.performance_metrics["best_performer"] = f"{best_performer.symbol} ({best_performer.pnl_percent:+.1f}%)"
            app_state.performance_metrics["worst_performer"] = f"{worst_performer.symbol} ({worst_performer.pnl_percent:+.1f}%)"
    
    except Exception as e:
        app_logger.error(f"❌ Performance metrics update error: {e}")


async def health_monitoring_loop():
    """Monitor component health and system resources"""
    while app_state.trading_active:
        try:
            # Check component health
            app_state.component_health["market_data"] = (
                app_state.market_data_manager is not None and 
                await app_state.market_data_manager.health_check() if hasattr(app_state.market_data_manager, 'health_check') else True
            )
            
            app_state.component_health["risk_manager"] = app_state.risk_manager is not None
            app_state.component_health["order_engine"] = app_state.order_engine is not None
            app_state.component_health["earnings_scanner"] = app_state.earnings_scanner is not None
            app_state.component_health["telegram_bot"] = app_state.telegram_bot is not None
            
            # Update system health
            app_state.system_healthy = all(app_state.component_health.values())
            
            await asyncio.sleep(60)  # Check every minute
            
        except Exception as e:
            app_logger.error(f"❌ Health monitoring error: {e}")
            await asyncio.sleep(60)


async def performance_monitoring_loop():
    """Monitor system performance metrics"""
    while app_state.trading_active:
        try:
            # System resource monitoring
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            app_state.performance_metrics.update({
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available": memory.available,
                "websocket_connections": len(websocket_manager.active_connections),
                "system_uptime": (datetime.now() - app_state.last_heartbeat).total_seconds()
            })
            
            await asyncio.sleep(300)  # Check every 5 minutes
            
        except Exception as e:
            app_logger.error(f"❌ Performance monitoring error: {e}")
            await asyncio.sleep(300)


async def get_system_status() -> Dict[str, Any]:
    """Get current system status"""
    active_trades = 0
    total_pnl = 0
    
    if app_state.order_engine:
        try:
            status = await app_state.order_engine.get_execution_status()
            active_trades = status.get("active_trades", 0)
            
            positions = await app_state.order_engine.position_tracker.get_all_positions()
            total_pnl = sum(pos.pnl for pos in positions.values()) if positions else 0
        except:
            pass
    
    return {
        "trading_active": app_state.trading_active,
        "trading_mode": app_state.trading_mode.value,
        "emergency_stop": app_state.emergency_stop,
        "system_healthy": app_state.system_healthy,
        "last_heartbeat": app_state.last_heartbeat.isoformat(),
        "active_trades": active_trades,
        "total_pnl": total_pnl,
        "component_health": app_state.component_health,
        "websocket_connections": len(websocket_manager.active_connections),
        "performance_metrics": app_state.performance_metrics
    }


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time dashboard updates"""
    await websocket_manager.connect(websocket)
    
    try:
        while True:
            # Wait for client messages (heartbeat, commands, etc.)
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "heartbeat":
                    # Respond to client heartbeat
                    await websocket_manager.send_personal_message(websocket, {
                        "type": "heartbeat_response",
                        "timestamp": datetime.now().isoformat()
                    })
                
                elif message_type == "request_status":
                    # Send current system status
                    await websocket_manager.send_personal_message(websocket, {
                        "type": "system_status",
                        "data": await get_system_status()
                    })
                
                elif message_type == "request_performance":
                    # Send performance metrics
                    await websocket_manager.send_personal_message(websocket, {
                        "type": "performance_metrics",
                        "data": app_state.performance_metrics
                    })
                
            except json.JSONDecodeError:
                app_logger.warning("Invalid JSON received from WebSocket client")
            except Exception as e:
                app_logger.error(f"WebSocket message processing error: {e}")
    
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        app_logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)


# API Endpoints
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    try:
        if templates_dir.exists():
            return templates.TemplateResponse("dashboard.html", {"request": request})
        else:
            return HTMLResponse("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Earnings Gap Trading System</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .status { padding: 20px; border-radius: 8px; margin: 20px 0; }
                    .healthy { background: #d4edda; border: 1px solid #c3e6cb; }
                    .unhealthy { background: #f8d7da; border: 1px solid #f5c6cb; }
                </style>
            </head>
            <body>
                <h1>🚀 Earnings Gap Trading System</h1>
                <div class="status healthy">
                    <h2>System Status</h2>
                    <p>FastAPI application is running successfully!</p>
                    <p>WebSocket endpoint: <code>ws://localhost:8000/ws</code></p>
                    <p>API endpoints: <code>/api/status</code>, <code>/api/performance</code></p>
                </div>
                <div>
                    <h3>Available Endpoints:</h3>
                    <ul>
                        <li><a href="/api/status">System Status</a></li>
                        <li><a href="/api/performance">Performance Metrics</a></li>
                        <li><a href="/docs">API Documentation</a></li>
                    </ul>
                </div>
            </body>
            </html>
            """)
    except Exception as e:
        app_logger.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Dashboard unavailable")


@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    """Configuration page"""
    try:
        if templates_dir.exists():
            return templates.TemplateResponse("config.html", {"request": request})
        else:
            return HTMLResponse("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Configuration - Earnings Gap Trading System</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .config-section { padding: 20px; border: 1px solid #ddd; margin: 20px 0; border-radius: 8px; }
                </style>
            </head>
            <body>
                <h1>⚙️ System Configuration</h1>
                <div class="config-section">
                    <h2>Trading Configuration</h2>
                    <p>Current Mode: <strong id="trading-mode">Loading...</strong></p>
                    <p>Emergency Stop: <strong id="emergency-stop">Loading...</strong></p>
                </div>
                <div class="config-section">
                    <h2>Component Health</h2>
                    <ul id="component-health">
                        <li>Loading...</li>
                    </ul>
                </div>
                <script>
                    fetch('/api/status')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('trading-mode').textContent = data.trading_mode;
                            document.getElementById('emergency-stop').textContent = data.emergency_stop ? 'ACTIVE' : 'INACTIVE';
                            
                            const healthList = document.getElementById('component-health');
                            healthList.innerHTML = '';
                            for (const [component, health] of Object.entries(data.component_health)) {
                                const li = document.createElement('li');
                                li.innerHTML = `${component}: <strong>${health ? '✅ Healthy' : '❌ Unhealthy'}</strong>`;
                                healthList.appendChild(li);
                            }
                        });
                </script>
            </body>
            </html>
            """)
    except Exception as e:
        app_logger.error(f"Config page error: {e}")
        raise HTTPException(status_code=500, detail="Configuration page unavailable")


@app.get("/api/status", response_model=SystemStatusResponse)
async def get_status():
    """Get current system status"""
    try:
        status_data = await get_system_status()
        return SystemStatusResponse(**status_data)
    except Exception as e:
        app_logger.error(f"Status API error: {e}")
        raise HTTPException(status_code=500, detail=f"Status unavailable: {str(e)}")


@app.get("/api/performance", response_model=PerformanceMetrics)
async def get_performance():
    """Get performance metrics"""
    try:
        metrics = app_state.performance_metrics
        
        return PerformanceMetrics(
            daily_trades=metrics.get("total_trades", 0),
            daily_pnl=metrics.get("total_pnl", 0.0),
            win_rate=metrics.get("success_rate", 0.0),
            total_portfolio_value=metrics.get("total_portfolio_value", 0.0),
            best_performer=metrics.get("best_performer"),
            worst_performer=metrics.get("worst_performer"),
            risk_metrics={
                "active_positions": metrics.get("active_positions", 0),
                "cpu_percent": metrics.get("cpu_percent", 0.0),
                "memory_percent": metrics.get("memory_percent", 0.0)
            }
        )
    except Exception as e:
        app_logger.error(f"Performance API error: {e}")
        raise HTTPException(status_code=500, detail=f"Performance data unavailable: {str(e)}")


@app.post("/api/emergency-stop")
async def emergency_stop(request: EmergencyStopRequest):
    """Emergency stop all trading"""
    try:
        app_logger.warning(f"🚨 Emergency stop requested: {request.reason}")
        
        app_state.emergency_stop = True
        app_state.trading_active = False
        
        # Stop order engine
        if app_state.order_engine:
            await app_state.order_engine.emergency_stop_all(request.reason)
        
        # Notify via Telegram
        if app_state.telegram_bot:
            await app_state.telegram_bot.broadcast_message(f"🚨 EMERGENCY STOP: {request.reason}")
        
        # Broadcast to WebSocket clients
        await websocket_manager.send_system_status({
            "emergency_stop": True,
            "message": f"Emergency stop: {request.reason}",
            "timestamp": datetime.now().isoformat()
        })
        
        return {"status": "emergency_stop_activated", "reason": request.reason}
        
    except Exception as e:
        app_logger.error(f"Emergency stop error: {e}")
        raise HTTPException(status_code=500, detail=f"Emergency stop failed: {str(e)}")


@app.post("/api/toggle-mode")
async def toggle_trading_mode(request: TradingModeRequest):
    """Toggle trading mode (AUTO/MANUAL/PAUSED)"""
    try:
        new_mode = TradingMode(request.mode)
        old_mode = app_state.trading_mode
        
        app_state.trading_mode = new_mode
        
        # Update Telegram bot mode
        if app_state.telegram_bot:
            app_state.telegram_bot.set_trading_mode(new_mode)
        
        app_logger.info(f"🎛️  Trading mode changed: {old_mode.value} → {new_mode.value}")
        
        # Notify via Telegram
        if app_state.telegram_bot:
            await app_state.telegram_bot.broadcast_message(
                f"🎛️  Trading mode changed to: {new_mode.value}"
            )
        
        # Broadcast to WebSocket clients
        await websocket_manager.send_system_status(await get_system_status())
        
        return {
            "status": "mode_changed",
            "old_mode": old_mode.value,
            "new_mode": new_mode.value
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid trading mode: {request.mode}")
    except Exception as e:
        app_logger.error(f"Mode toggle error: {e}")
        raise HTTPException(status_code=500, detail=f"Mode change failed: {str(e)}")


@app.get("/api/config")
async def get_configuration():
    """Get current system configuration"""
    try:
        app_logger.info("📋 Configuration requested")
        
        # Helper function to safely get config values
        def safe_get_config(attr_name, default=''):
            """Safely get config value handling SecretStr types"""
            value = getattr(config, attr_name, default)
            if hasattr(value, 'get_secret_value'):
                return value.get_secret_value()
            return value
        
        # Get current configuration from config
        current_config = {
            "api": {
                "api_key": safe_get_config('kite_api_key', ''),
                "api_secret": safe_get_config('kite_api_secret', ''),
                "access_token": safe_get_config('kite_access_token', ''),
                "paper_trading": safe_get_config('paper_trading', False)
            },
            "trading": {
                "portfolio_value": float(safe_get_config('max_position_size', 100000)),
                "max_positions": int(safe_get_config('max_open_positions', 5)),
                "position_size_percent": float(safe_get_config('risk_per_trade', 0.05)) * 100,
                "stop_loss_percent": float(safe_get_config('stop_loss_percentage', 0.03)) * 100,
                "profit_target_percent": float(safe_get_config('target_percentage', 0.08)) * 100,
                "trading_mode": "MANUAL",
                "market_open_time": safe_get_config('market_start_time', '09:15'),
                "market_close_time": safe_get_config('market_end_time', '15:30')
            },
            "risk": {
                "daily_loss_limit": float(safe_get_config('daily_loss_limit', 25000)),
                "weekly_loss_limit": float(safe_get_config('max_daily_loss', 25000)) * 7,
                "max_drawdown": float(safe_get_config('max_drawdown_percentage', 8.0)),
                "max_position_size": float(safe_get_config('max_position_size', 50000)),
                "correlation_limit": 60.0,
                "volatility_threshold": 25.0,
                "emergency_stop_enabled": True,
                "risk_alerts_enabled": True
            },
            "telegram": {
                "bot_token": safe_get_config('telegram_bot_token', ''),
                "chat_ids": [safe_get_config('telegram_chat_id', '')],
                "enabled": bool(safe_get_config('telegram_enabled', False)),
                "notifications": {
                    "signals": True,
                    "trades": True,
                    "risk_alerts": True
                }
            },
            "scanner": {
                "min_gap_percent": float(safe_get_config('min_gap_percentage', 2.5)),
                "min_volume_ratio": 2.0,
                "min_market_cap": 1000,
                "max_market_cap": 500000,
                "scan_interval": 15,
                "confidence_threshold": 70,
                "excluded_symbols": [],
                "enable_premarket_scan": True,
                "enable_earnings_filter": True
            }
        }
        
        return {
            "success": True,
            "data": current_config
        }
        
    except Exception as e:
        app_logger.error(f"Configuration retrieval error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/config")
async def update_configuration(request: FullConfigurationRequest):
    """Update system configuration"""
    try:
        app_logger.info("🔧 Configuration update received")
        
        # Update .env file with new configuration
        env_updates = {}
        
        # Process API configuration
        if request.api:
            if 'api_key' in request.api:
                env_updates['KITE_API_KEY'] = request.api['api_key']
            if 'api_secret' in request.api:
                env_updates['KITE_API_SECRET'] = request.api['api_secret']
            if 'access_token' in request.api:
                env_updates['KITE_ACCESS_TOKEN'] = request.api['access_token']
            if 'paper_trading' in request.api:
                env_updates['PAPER_TRADING'] = str(request.api['paper_trading']).lower()
        
        # Process trading configuration
        if request.trading:
            if 'portfolio_value' in request.trading:
                env_updates['MAX_POSITION_SIZE'] = str(request.trading['portfolio_value'])
            if 'max_positions' in request.trading:
                env_updates['MAX_OPEN_POSITIONS'] = str(request.trading['max_positions'])
            if 'position_size_percent' in request.trading:
                env_updates['RISK_PER_TRADE'] = str(request.trading['position_size_percent'] / 100)
            if 'stop_loss_percent' in request.trading:
                env_updates['STOP_LOSS_PERCENTAGE'] = str(request.trading['stop_loss_percent'] / 100)
            if 'profit_target_percent' in request.trading:
                env_updates['TARGET_PERCENTAGE'] = str(request.trading['profit_target_percent'] / 100)
        
        # Process risk management configuration
        if request.risk:
            if 'daily_loss_limit' in request.risk:
                env_updates['DAILY_LOSS_LIMIT'] = str(request.risk['daily_loss_limit'])
            if 'max_drawdown' in request.risk:
                env_updates['MAX_DRAWDOWN_PERCENTAGE'] = str(request.risk['max_drawdown'])
            if 'max_position_size' in request.risk:
                env_updates['MAX_POSITION_SIZE'] = str(request.risk['max_position_size'])
        
        # Process Telegram configuration
        if request.telegram:
            if 'bot_token' in request.telegram:
                env_updates['TELEGRAM_BOT_TOKEN'] = request.telegram['bot_token']
            if 'chat_ids' in request.telegram and request.telegram['chat_ids']:
                env_updates['TELEGRAM_CHAT_ID'] = str(request.telegram['chat_ids'][0])
            if 'enabled' in request.telegram:
                env_updates['TELEGRAM_ENABLED'] = str(request.telegram['enabled']).lower()
        
        # Process scanner configuration
        if request.scanner:
            if 'min_gap_percent' in request.scanner:
                env_updates['MIN_GAP_PERCENTAGE'] = str(request.scanner['min_gap_percent'])
        
        # Update .env file
        if env_updates:
            await update_env_file(env_updates)
            app_logger.info(f"Updated {len(env_updates)} configuration settings")
        
        return {
            "success": True,
            "message": "Configuration saved successfully",
            "updated_count": len(env_updates)
        }
        
    except Exception as e:
        app_logger.error(f"Configuration update error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy" if app_state.system_healthy else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "components": app_state.component_health
    }


@app.post("/api/generate-token")
async def generate_access_token(request: TokenGenerationRequest):
    """Generate access token from request token"""
    try:
        from kiteconnect import KiteConnect
        
        # Create KiteConnect instance
        kite = KiteConnect(api_key=request.api_key)
        
        # Generate access token using request token
        data = kite.generate_session(request.request_token, api_secret=request.api_secret)
        
        if data and "access_token" in data:
            access_token = data["access_token"]
            
            # Optionally update the config file
            # You might want to update .env file here
            
            return {
                "success": True,
                "access_token": access_token,
                "user_id": data.get("user_id"),
                "user_name": data.get("user_name")
            }
        else:
            return {
                "success": False,
                "error": "Failed to generate access token"
            }
            
    except Exception as e:
        app_logger.error(f"Token generation failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/test-connection")
async def test_api_connection(request: ApiTestRequest):
    """Test Zerodha API connection"""
    try:
        from kiteconnect import KiteConnect
        
        # Create KiteConnect instance
        kite = KiteConnect(api_key=request.api_key)
        kite.set_access_token(request.access_token)
        
        # Test connection by getting profile
        profile = kite.profile()
        
        if profile and "user_name" in profile:
            return {
                "success": True,
                "message": "Connection successful",
                "user_name": profile.get("user_name"),
                "email": profile.get("email"),
                "broker": profile.get("broker")
            }
        else:
            return {
                "success": False,
                "error": "Failed to retrieve profile data"
            }
            
    except Exception as e:
        app_logger.error(f"API connection test failed: {e}")
        error_message = str(e)
        
        # Provide more specific error messages
        if "api_key" in error_message.lower() or "incorrect" in error_message.lower():
            error_message = "Invalid API key or access token"
        elif "network" in error_message.lower() or "connection" in error_message.lower():
            error_message = "Network connection failed"
        elif "token" in error_message.lower():
            error_message = "Access token expired or invalid"
        
        return {
            "success": False,
            "error": error_message
        }


@app.post("/api/test-telegram")
async def test_telegram_bot(request: TelegramTestRequest):
    """Test Telegram bot connection"""
    try:
        app_logger.info("🤖 Testing Telegram bot connection")
        
        # Import Telegram classes
        from telegram import Bot
        from telegram.error import TelegramError
        
        # Create bot instance
        bot = Bot(token=request.bot_token)
        
        # Test bot by getting bot info
        bot_info = await bot.get_me()
        
        if not bot_info:
            return {
                "success": False,
                "error": "Failed to get bot information"
            }
        
        # Test sending message to each chat ID
        test_results = []
        for chat_id in request.chat_ids:
            try:
                chat_id = chat_id.strip()
                if not chat_id:
                    continue
                    
                # Send test message
                test_message = "🧪 Test message from Earnings Gap Trader - Bot connection successful!"
                message = await bot.send_message(
                    chat_id=chat_id,
                    text=test_message
                )
                
                test_results.append({
                    "chat_id": chat_id,
                    "success": True,
                    "message_id": message.message_id
                })
                
            except TelegramError as e:
                test_results.append({
                    "chat_id": chat_id,
                    "success": False,
                    "error": str(e)
                })
        
        # Check if at least one chat worked
        successful_chats = [r for r in test_results if r["success"]]
        
        if successful_chats:
            return {
                "success": True,
                "message": f"Bot connected successfully. Tested {len(successful_chats)} chat(s).",
                "bot_username": bot_info.username,
                "bot_name": bot_info.first_name,
                "test_results": test_results
            }
        else:
            failed_errors = [r["error"] for r in test_results if not r["success"]]
            return {
                "success": False,
                "error": f"Failed to send messages to any chat. Errors: {', '.join(failed_errors)}"
            }
            
    except TelegramError as e:
        app_logger.error(f"Telegram bot test failed: {e}")
        error_message = str(e)
        
        # Provide more specific error messages
        if "unauthorized" in error_message.lower():
            error_message = "Invalid bot token"
        elif "not found" in error_message.lower():
            error_message = "Bot token not found or bot was deleted"
        elif "forbidden" in error_message.lower():
            error_message = "Bot is blocked or has no permission to send messages"
        
        return {
            "success": False,
            "error": error_message
        }
        
    except Exception as e:
        app_logger.error(f"Telegram test error: {e}")
        return {
            "success": False,
            "error": f"Test failed: {str(e)}"
        }


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    app_logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    app_state.trading_active = False
    app_state.emergency_stop = True


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":
    # Configuration
    HOST = config.host
    PORT = config.port
    DEBUG = config.debug
    WORKERS = 1
    
    app_logger.info(f"🚀 Starting Earnings Gap Trading System on {HOST}:{PORT}")
    
    # Run the application
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        workers=WORKERS,
        log_level="info" if not DEBUG else "debug",
        access_log=True
    )