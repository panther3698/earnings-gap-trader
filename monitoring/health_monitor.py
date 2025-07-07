#!/usr/bin/env python3
"""
Comprehensive health monitoring system for Earnings Gap Trading System
Monitors system health, performance metrics, and sends alerts
"""

import asyncio
import json
import logging
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import redis
import psycopg2

from dataclasses import dataclass
from enum import Enum


class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class HealthCheckResult:
    component: str
    status: HealthStatus
    message: str
    metrics: Dict[str, Any]
    timestamp: datetime
    response_time: float


@dataclass
class Alert:
    level: AlertLevel
    component: str
    message: str
    timestamp: datetime
    resolved: bool = False


class HealthMonitor:
    """Main health monitoring class"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.redis_client = None
        self.alerts_history: List[Alert] = []
        self.health_results: Dict[str, HealthCheckResult] = {}
        
        # Initialize components
        self._setup_redis()
        
    def _setup_redis(self):
        """Setup Redis connection for metrics storage"""
        try:
            self.redis_client = redis.Redis(
                host=self.config.get('redis_host', 'localhost'),
                port=self.config.get('redis_port', 6379),
                db=self.config.get('redis_db', 1),
                decode_responses=True
            )
            self.redis_client.ping()
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
    
    async def run_health_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all health checks and return results"""
        checks = [
            self._check_application_health(),
            self._check_database_health(),
            self._check_redis_health(),
            self._check_system_resources(),
            self._check_disk_space(),
            self._check_network_connectivity(),
            self._check_trading_engine_health(),
            self._check_websocket_connections(),
            self._check_external_apis()
        ]
        
        results = await asyncio.gather(*checks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Health check failed: {result}")
                continue
            
            if isinstance(result, HealthCheckResult):
                self.health_results[result.component] = result
                
                # Store metrics in Redis
                if self.redis_client:
                    await self._store_metrics(result)
                
                # Check for alerts
                await self._process_alert(result)
        
        return self.health_results
    
    async def _check_application_health(self) -> HealthCheckResult:
        """Check main application health"""
        start_time = time.time()
        
        try:
            app_url = self.config.get('app_url', 'http://localhost:8000')
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{app_url}/health") as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        status = HealthStatus.HEALTHY
                        if response_time > 5.0:
                            status = HealthStatus.WARNING
                        
                        return HealthCheckResult(
                            component="application",
                            status=status,
                            message=f"Application responding in {response_time:.2f}s",
                            metrics={
                                "response_time": response_time,
                                "status_code": response.status,
                                "uptime": data.get("uptime", 0)
                            },
                            timestamp=datetime.now(),
                            response_time=response_time
                        )
                    else:
                        return HealthCheckResult(
                            component="application",
                            status=HealthStatus.CRITICAL,
                            message=f"Application returned status {response.status}",
                            metrics={"status_code": response.status},
                            timestamp=datetime.now(),
                            response_time=response_time
                        )
                        
        except Exception as e:
            return HealthCheckResult(
                component="application",
                status=HealthStatus.CRITICAL,
                message=f"Application health check failed: {str(e)}",
                metrics={},
                timestamp=datetime.now(),
                response_time=time.time() - start_time
            )
    
    async def _check_database_health(self) -> HealthCheckResult:
        """Check PostgreSQL database health"""
        start_time = time.time()
        
        try:
            db_config = {
                'host': self.config.get('db_host', 'localhost'),
                'port': self.config.get('db_port', 5432),
                'database': self.config.get('db_name', 'earnings_gap_trader'),
                'user': self.config.get('db_user', 'trader'),
                'password': self.config.get('db_password', '')
            }
            
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()
            
            # Test query
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            # Get database stats
            cursor.execute("""
                SELECT 
                    count(*) as active_connections,
                    pg_database_size(current_database()) as db_size
                FROM pg_stat_activity 
                WHERE state = 'active'
            """)
            
            stats = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            response_time = time.time() - start_time
            
            status = HealthStatus.HEALTHY
            if stats[0] > 50:  # Too many connections
                status = HealthStatus.WARNING
            
            return HealthCheckResult(
                component="database",
                status=status,
                message=f"Database responding in {response_time:.2f}s",
                metrics={
                    "response_time": response_time,
                    "active_connections": stats[0],
                    "database_size": stats[1]
                },
                timestamp=datetime.now(),
                response_time=response_time
            )
            
        except Exception as e:
            return HealthCheckResult(
                component="database",
                status=HealthStatus.CRITICAL,
                message=f"Database health check failed: {str(e)}",
                metrics={},
                timestamp=datetime.now(),
                response_time=time.time() - start_time
            )
    
    async def _check_redis_health(self) -> HealthCheckResult:
        """Check Redis health"""
        start_time = time.time()
        
        try:
            # Test Redis connection
            result = self.redis_client.ping()
            
            # Get Redis info
            info = self.redis_client.info()
            
            response_time = time.time() - start_time
            
            memory_usage = info.get('used_memory', 0)
            max_memory = info.get('maxmemory', 0)
            
            status = HealthStatus.HEALTHY
            if max_memory > 0 and memory_usage / max_memory > 0.9:
                status = HealthStatus.WARNING
            
            return HealthCheckResult(
                component="redis",
                status=status,
                message=f"Redis responding in {response_time:.2f}s",
                metrics={
                    "response_time": response_time,
                    "memory_usage": memory_usage,
                    "connected_clients": info.get('connected_clients', 0),
                    "uptime": info.get('uptime_in_seconds', 0)
                },
                timestamp=datetime.now(),
                response_time=response_time
            )
            
        except Exception as e:
            return HealthCheckResult(
                component="redis",
                status=HealthStatus.CRITICAL,
                message=f"Redis health check failed: {str(e)}",
                metrics={},
                timestamp=datetime.now(),
                response_time=time.time() - start_time
            )
    
    async def _check_system_resources(self) -> HealthCheckResult:
        """Check system resource usage"""
        start_time = time.time()
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Load average (Unix only)
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            response_time = time.time() - start_time
            
            # Determine status
            status = HealthStatus.HEALTHY
            if cpu_percent > 80 or memory.percent > 85:
                status = HealthStatus.WARNING
            if cpu_percent > 95 or memory.percent > 95:
                status = HealthStatus.CRITICAL
            
            return HealthCheckResult(
                component="system_resources",
                status=status,
                message=f"CPU: {cpu_percent:.1f}%, Memory: {memory.percent:.1f}%",
                metrics={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available": memory.available,
                    "load_average_1m": load_avg[0],
                    "load_average_5m": load_avg[1],
                    "load_average_15m": load_avg[2]
                },
                timestamp=datetime.now(),
                response_time=response_time
            )
            
        except Exception as e:
            return HealthCheckResult(
                component="system_resources",
                status=HealthStatus.CRITICAL,
                message=f"System resources check failed: {str(e)}",
                metrics={},
                timestamp=datetime.now(),
                response_time=time.time() - start_time
            )
    
    async def _check_disk_space(self) -> HealthCheckResult:
        """Check disk space usage"""
        start_time = time.time()
        
        try:
            disk_usage = psutil.disk_usage('/')
            
            used_percent = (disk_usage.used / disk_usage.total) * 100
            
            status = HealthStatus.HEALTHY
            if used_percent > 80:
                status = HealthStatus.WARNING
            if used_percent > 90:
                status = HealthStatus.CRITICAL
            
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                component="disk_space",
                status=status,
                message=f"Disk usage: {used_percent:.1f}%",
                metrics={
                    "used_percent": used_percent,
                    "total_bytes": disk_usage.total,
                    "used_bytes": disk_usage.used,
                    "free_bytes": disk_usage.free
                },
                timestamp=datetime.now(),
                response_time=response_time
            )
            
        except Exception as e:
            return HealthCheckResult(
                component="disk_space",
                status=HealthStatus.CRITICAL,
                message=f"Disk space check failed: {str(e)}",
                metrics={},
                timestamp=datetime.now(),
                response_time=time.time() - start_time
            )
    
    async def _check_network_connectivity(self) -> HealthCheckResult:
        """Check network connectivity to external services"""
        start_time = time.time()
        
        try:
            # Test connectivity to key external services
            services = [
                'https://www.google.com',
                'https://api.kite.zerodha.com',
                'https://api.telegram.org'
            ]
            
            successful_connections = 0
            timeout = aiohttp.ClientTimeout(total=5)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for service in services:
                    try:
                        async with session.get(service) as response:
                            if response.status < 500:
                                successful_connections += 1
                    except:
                        continue
            
            response_time = time.time() - start_time
            
            success_rate = successful_connections / len(services)
            
            status = HealthStatus.HEALTHY
            if success_rate < 0.8:
                status = HealthStatus.WARNING
            if success_rate < 0.5:
                status = HealthStatus.CRITICAL
            
            return HealthCheckResult(
                component="network_connectivity",
                status=status,
                message=f"Network connectivity: {success_rate:.1%}",
                metrics={
                    "success_rate": success_rate,
                    "successful_connections": successful_connections,
                    "total_services": len(services)
                },
                timestamp=datetime.now(),
                response_time=response_time
            )
            
        except Exception as e:
            return HealthCheckResult(
                component="network_connectivity",
                status=HealthStatus.CRITICAL,
                message=f"Network connectivity check failed: {str(e)}",
                metrics={},
                timestamp=datetime.now(),
                response_time=time.time() - start_time
            )
    
    async def _check_trading_engine_health(self) -> HealthCheckResult:
        """Check trading engine health"""
        start_time = time.time()
        
        try:
            # Check if trading engine is responsive
            app_url = self.config.get('app_url', 'http://localhost:8000')
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{app_url}/api/status") as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        response_time = time.time() - start_time
                        
                        # Check trading system status
                        system_healthy = data.get('system_healthy', False)
                        active_trades = data.get('active_trades', 0)
                        emergency_stop = data.get('emergency_stop', False)
                        
                        status = HealthStatus.HEALTHY
                        if not system_healthy or emergency_stop:
                            status = HealthStatus.CRITICAL
                        elif active_trades > 10:  # Too many active trades
                            status = HealthStatus.WARNING
                        
                        return HealthCheckResult(
                            component="trading_engine",
                            status=status,
                            message=f"Trading engine: {'healthy' if system_healthy else 'unhealthy'}",
                            metrics={
                                "response_time": response_time,
                                "system_healthy": system_healthy,
                                "active_trades": active_trades,
                                "emergency_stop": emergency_stop,
                                "total_pnl": data.get('total_pnl', 0)
                            },
                            timestamp=datetime.now(),
                            response_time=response_time
                        )
                    else:
                        return HealthCheckResult(
                            component="trading_engine",
                            status=HealthStatus.CRITICAL,
                            message=f"Trading engine API returned {response.status}",
                            metrics={"status_code": response.status},
                            timestamp=datetime.now(),
                            response_time=time.time() - start_time
                        )
                        
        except Exception as e:
            return HealthCheckResult(
                component="trading_engine",
                status=HealthStatus.CRITICAL,
                message=f"Trading engine check failed: {str(e)}",
                metrics={},
                timestamp=datetime.now(),
                response_time=time.time() - start_time
            )
    
    async def _check_websocket_connections(self) -> HealthCheckResult:
        """Check WebSocket connection health"""
        start_time = time.time()
        
        try:
            # Check WebSocket endpoint
            app_url = self.config.get('app_url', 'http://localhost:8000')
            ws_url = app_url.replace('http', 'ws') + '/ws'
            
            # Simple WebSocket connection test
            import websockets
            
            async with websockets.connect(ws_url, timeout=5) as websocket:
                # Send ping
                await websocket.send('{"type": "ping"}')
                response = await websocket.recv()
                
                response_time = time.time() - start_time
                
                return HealthCheckResult(
                    component="websocket",
                    status=HealthStatus.HEALTHY,
                    message=f"WebSocket responding in {response_time:.2f}s",
                    metrics={"response_time": response_time},
                    timestamp=datetime.now(),
                    response_time=response_time
                )
                
        except Exception as e:
            return HealthCheckResult(
                component="websocket",
                status=HealthStatus.CRITICAL,
                message=f"WebSocket check failed: {str(e)}",
                metrics={},
                timestamp=datetime.now(),
                response_time=time.time() - start_time
            )
    
    async def _check_external_apis(self) -> HealthCheckResult:
        """Check external API health"""
        start_time = time.time()
        
        try:
            # Test external APIs
            apis = {
                'zerodha': 'https://api.kite.zerodha.com',
                'telegram': 'https://api.telegram.org',
                'yfinance': 'https://query1.finance.yahoo.com'
            }
            
            api_status = {}
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for name, url in apis.items():
                    try:
                        async with session.get(url) as response:
                            api_status[name] = response.status < 500
                    except:
                        api_status[name] = False
            
            response_time = time.time() - start_time
            healthy_apis = sum(api_status.values())
            total_apis = len(apis)
            
            status = HealthStatus.HEALTHY
            if healthy_apis < total_apis * 0.8:
                status = HealthStatus.WARNING
            if healthy_apis < total_apis * 0.5:
                status = HealthStatus.CRITICAL
            
            return HealthCheckResult(
                component="external_apis",
                status=status,
                message=f"External APIs: {healthy_apis}/{total_apis} healthy",
                metrics={
                    "healthy_apis": healthy_apis,
                    "total_apis": total_apis,
                    "api_status": api_status
                },
                timestamp=datetime.now(),
                response_time=response_time
            )
            
        except Exception as e:
            return HealthCheckResult(
                component="external_apis",
                status=HealthStatus.CRITICAL,
                message=f"External APIs check failed: {str(e)}",
                metrics={},
                timestamp=datetime.now(),
                response_time=time.time() - start_time
            )
    
    async def _store_metrics(self, result: HealthCheckResult):
        """Store health check metrics in Redis"""
        if not self.redis_client:
            return
        
        try:
            # Store current metrics
            key = f"health:{result.component}"
            data = {
                "status": result.status.value,
                "message": result.message,
                "timestamp": result.timestamp.isoformat(),
                "response_time": result.response_time,
                **result.metrics
            }
            
            await asyncio.get_event_loop().run_in_executor(
                None, self.redis_client.hset, key, mapping=data
            )
            
            # Set expiration (24 hours)
            await asyncio.get_event_loop().run_in_executor(
                None, self.redis_client.expire, key, 86400
            )
            
            # Store time series data
            ts_key = f"health_ts:{result.component}"
            timestamp = int(result.timestamp.timestamp())
            
            await asyncio.get_event_loop().run_in_executor(
                None, self.redis_client.zadd, ts_key, {json.dumps(data): timestamp}
            )
            
            # Keep only last 1000 entries
            await asyncio.get_event_loop().run_in_executor(
                None, self.redis_client.zremrangebyrank, ts_key, 0, -1001
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store metrics: {e}")
    
    async def _process_alert(self, result: HealthCheckResult):
        """Process health check result for alerts"""
        if result.status in [HealthStatus.WARNING, HealthStatus.CRITICAL]:
            
            # Determine alert level
            alert_level = AlertLevel.WARNING if result.status == HealthStatus.WARNING else AlertLevel.CRITICAL
            
            # Check if this is a new alert (not repeated)
            recent_alerts = [
                alert for alert in self.alerts_history
                if alert.component == result.component
                and alert.timestamp > datetime.now() - timedelta(minutes=30)
                and not alert.resolved
            ]
            
            if not recent_alerts:
                alert = Alert(
                    level=alert_level,
                    component=result.component,
                    message=result.message,
                    timestamp=result.timestamp
                )
                
                self.alerts_history.append(alert)
                await self._send_alert(alert, result)
    
    async def _send_alert(self, alert: Alert, result: HealthCheckResult):
        """Send alert notification"""
        try:
            # Email alert
            if self.config.get('email_alerts_enabled', True):
                await self._send_email_alert(alert, result)
            
            # Telegram alert
            if self.config.get('telegram_alerts_enabled', True):
                await self._send_telegram_alert(alert, result)
            
            # Store alert in Redis
            if self.redis_client:
                alert_data = {
                    "level": alert.level.value,
                    "component": alert.component,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat(),
                    "metrics": json.dumps(result.metrics)
                }
                
                await asyncio.get_event_loop().run_in_executor(
                    None, 
                    self.redis_client.lpush, 
                    "alerts", 
                    json.dumps(alert_data)
                )
                
                # Keep only last 100 alerts
                await asyncio.get_event_loop().run_in_executor(
                    None, self.redis_client.ltrim, "alerts", 0, 99
                )
            
        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")
    
    async def _send_email_alert(self, alert: Alert, result: HealthCheckResult):
        """Send email alert"""
        try:
            smtp_config = self.config.get('smtp', {})
            
            if not all(k in smtp_config for k in ['host', 'port', 'user', 'password']):
                return
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = smtp_config['user']
            msg['To'] = self.config.get('alert_email', smtp_config['user'])
            msg['Subject'] = f"[{alert.level.value.upper()}] Trading System Alert - {alert.component}"
            
            # Email body
            body = f"""
Trading System Health Alert

Component: {alert.component}
Status: {result.status.value.upper()}
Alert Level: {alert.level.value.upper()}
Message: {alert.message}
Timestamp: {alert.timestamp}
Response Time: {result.response_time:.2f}s

Metrics:
{json.dumps(result.metrics, indent=2)}

Please investigate immediately.

---
Earnings Gap Trading System
Health Monitoring Service
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(smtp_config['host'], smtp_config['port'])
            server.starttls()
            server.login(smtp_config['user'], smtp_config['password'])
            server.send_message(msg)
            server.quit()
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
    
    async def _send_telegram_alert(self, alert: Alert, result: HealthCheckResult):
        """Send Telegram alert"""
        try:
            telegram_config = self.config.get('telegram', {})
            bot_token = telegram_config.get('bot_token')
            chat_ids = telegram_config.get('alert_chat_ids', [])
            
            if not bot_token or not chat_ids:
                return
            
            # Format message
            status_emoji = {
                HealthStatus.HEALTHY: "✅",
                HealthStatus.WARNING: "⚠️",
                HealthStatus.CRITICAL: "🚨",
                HealthStatus.UNKNOWN: "❓"
            }
            
            message = f"""
{status_emoji.get(result.status, '❓')} *Trading System Alert*

*Component:* {alert.component}
*Status:* {result.status.value.upper()}
*Level:* {alert.level.value.upper()}
*Message:* {alert.message}
*Time:* {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

*Response Time:* {result.response_time:.2f}s

Please investigate immediately.
            """
            
            # Send to all chat IDs
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for chat_id in chat_ids:
                    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    data = {
                        'chat_id': chat_id,
                        'text': message,
                        'parse_mode': 'Markdown'
                    }
                    
                    async with session.post(url, json=data) as response:
                        if response.status != 200:
                            self.logger.error(f"Failed to send Telegram alert to {chat_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to send Telegram alert: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        if not self.health_results:
            return {"status": "unknown", "message": "No health checks run yet"}
        
        # Determine overall status
        statuses = [result.status for result in self.health_results.values()]
        
        if HealthStatus.CRITICAL in statuses:
            overall_status = "critical"
        elif HealthStatus.WARNING in statuses:
            overall_status = "warning"
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            overall_status = "healthy"
        else:
            overall_status = "unknown"
        
        return {
            "status": overall_status,
            "components": {
                name: {
                    "status": result.status.value,
                    "message": result.message,
                    "response_time": result.response_time,
                    "timestamp": result.timestamp.isoformat()
                }
                for name, result in self.health_results.items()
            },
            "last_check": max(
                result.timestamp for result in self.health_results.values()
            ).isoformat() if self.health_results else None
        }