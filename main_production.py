#!/usr/bin/env python3
"""
Production Main Application for Earnings Gap Trading System
Optimized for live trading with enhanced error handling and monitoring
"""

import os
import sys
import asyncio
import signal
import logging
from typing import Optional
from pathlib import Path

# Set production environment first
os.environ["ENVIRONMENT"] = "production"
os.environ["DEBUG"] = "false"

# Copy production environment file
import shutil
if os.path.exists(".env.production"):
    shutil.copy(".env.production", ".env")
    print("Production environment loaded")

# Import main application after setting environment
from main import app, app_state, cleanup_components
from config import get_config
from utils.logging_config import get_logger

# Production configuration
config = get_config()
logger = get_logger(__name__)

class ProductionManager:
    """Production environment manager"""
    
    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self.setup_signal_handlers()
        
    def setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""
        if sys.platform != "win32":
            # Unix-like systems
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
        else:
            # Windows
            signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_event.set()
    
    async def run_production(self):
        """Run the production server"""
        try:
            logger.info("🚀 Starting Earnings Gap Trading System in PRODUCTION mode")
            logger.info(f"📊 Dashboard: http://{config.host}:{config.port}")
            logger.info("⚠️  LIVE TRADING ENABLED - Real money at risk!")
            
            # Import uvicorn here to avoid import issues
            import uvicorn
            
            # Configure uvicorn for production
            uvicorn_config = uvicorn.Config(
                app=app,
                host=config.host,
                port=config.port,
                reload=False,  # Disable auto-reload in production
                workers=1,     # Single worker for state consistency
                access_log=True,
                log_level="info",
                loop="asyncio"
            )
            
            server = uvicorn.Server(uvicorn_config)
            
            # Run server until shutdown signal
            await server.serve()
            
        except Exception as e:
            logger.error(f"❌ Production server failed: {e}")
            raise
        finally:
            logger.info("🛑 Production server shutdown complete")

def main():
    """Main production entry point"""
    try:
        # Ensure logs directory exists
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Initialize production manager
        prod_manager = ProductionManager()
        
        # Run the production server
        asyncio.run(prod_manager.run_production())
        
    except KeyboardInterrupt:
        logger.info("👋 Shutdown requested by user")
    except Exception as e:
        logger.error(f"💥 Fatal error in production: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()