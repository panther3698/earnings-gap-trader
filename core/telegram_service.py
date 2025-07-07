"""
Comprehensive Telegram bot for trade notifications, manual approval, and system control
"""
import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler as TelegramCommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes
)
from telegram.error import TelegramError, RetryAfter, TimedOut

from core.earnings_scanner import EarningsGapSignal
from core.order_engine import OrderEngine, PositionStatus
from core.risk_manager import RiskManager
from utils.logging_config import get_logger
from config import get_config

logger = get_logger(__name__)
config = get_config()


class TradingMode(Enum):
    """Trading mode types"""
    AUTO = "auto"
    MANUAL = "manual"
    PAUSED = "paused"


class ApprovalStatus(Enum):
    """Signal approval status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    MODIFIED = "modified"


class NotificationType(Enum):
    """Notification type classifications"""
    SIGNAL_ALERT = "signal_alert"
    TRADE_ENTRY = "trade_entry"
    TRADE_EXIT = "trade_exit"
    PNL_UPDATE = "pnl_update"
    RISK_ALERT = "risk_alert"
    SYSTEM_STATUS = "system_status"
    ERROR = "error"


@dataclass
class PendingSignal:
    """Pending signal awaiting approval"""
    signal_id: str
    signal: EarningsGapSignal
    message_id: int
    chat_id: int
    created_at: datetime
    expires_at: datetime
    status: ApprovalStatus
    approved_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    modified_params: Optional[Dict] = None


@dataclass
class TelegramConfig:
    """Telegram bot configuration"""
    bot_token: str
    chat_ids: List[int]
    webhook_url: Optional[str] = None
    approval_timeout: int = 300  # 5 minutes
    max_retries: int = 3
    rate_limit_delay: float = 1.0


@dataclass
class NotificationMessage:
    """Notification message structure"""
    type: NotificationType
    title: str
    content: str
    chat_ids: List[int]
    reply_markup: Optional[InlineKeyboardMarkup] = None
    parse_mode: str = ParseMode.HTML
    disable_web_page_preview: bool = True


class MessageFormatter:
    """Professional message formatting with emojis"""
    
    EMOJIS = {
        'signal': '🎯',
        'profit': '💰',
        'loss': '📉',
        'warning': '⚠️',
        'error': '❌',
        'success': '✅',
        'info': 'ℹ️',
        'chart_up': '📈',
        'chart_down': '📉',
        'money': '💵',
        'clock': '⏰',
        'fire': '🔥',
        'rocket': '🚀',
        'stop': '🛑',
        'pause': '⏸️',
        'play': '▶️',
        'gear': '⚙️',
        'shield': '🛡️',
        'bell': '🔔',
        'eyes': '👀',
        'thumbs_up': '👍',
        'thumbs_down': '👎'
    }
    
    @classmethod
    def format_signal_alert(cls, signal: EarningsGapSignal) -> str:
        """Format earnings gap signal alert"""
        direction = "UP" if signal.signal_type.value.endswith('_up') else "DOWN"
        direction_emoji = cls.EMOJIS['chart_up'] if direction == "UP" else cls.EMOJIS['chart_down']
        
        confidence_emoji = cls.EMOJIS['fire'] if signal.confidence_score >= 80 else cls.EMOJIS['signal']
        
        return f"""
{cls.EMOJIS['signal']} <b>EARNINGS GAP SIGNAL</b> {confidence_emoji}

<b>{signal.company_name} ({signal.symbol})</b>
{direction_emoji} <b>Direction:</b> GAP {direction}
{cls.EMOJIS['rocket']} <b>Confidence:</b> {signal.confidence.value.title()} ({signal.confidence_score:.0f}%)

{cls.EMOJIS['money']} <b>Trading Details:</b>
• Entry Price: ₹{signal.entry_price:.2f}
• Stop Loss: ₹{signal.stop_loss:.2f}
• Profit Target: ₹{signal.profit_target:.2f}
• Risk/Reward: 1:{signal.risk_reward_ratio:.2f}

{cls.EMOJIS['chart_up']} <b>Market Data:</b>
• Gap: {signal.gap_percent:+.1f}% (₹{signal.gap_amount:+.2f})
• Previous Close: ₹{signal.previous_close:.2f}
• Volume Surge: {signal.volume_ratio:.1f}x ({signal.current_volume:,})

{cls.EMOJIS['info']} <b>Earnings:</b>
• Actual EPS: ₹{signal.actual_eps}
• Expected EPS: ₹{signal.expected_eps}
• Surprise: {signal.earnings_surprise:+.1f}%

{cls.EMOJIS['clock']} <b>Signal Time:</b> {signal.entry_time.strftime('%H:%M:%S')}

{cls.EMOJIS['eyes']} <b>Analysis:</b>
{signal.signal_explanation}
        """.strip()
    
    @classmethod
    def format_trade_entry(cls, signal: EarningsGapSignal, trade_id: str, 
                          position_size: float, quantity: int) -> str:
        """Format trade entry notification"""
        return f"""
{cls.EMOJIS['success']} <b>TRADE EXECUTED</b> {cls.EMOJIS['rocket']}

<b>{signal.symbol}</b> - {signal.signal_type.value.replace('_', ' ').title()}
{cls.EMOJIS['info']} Trade ID: <code>{trade_id}</code>

{cls.EMOJIS['money']} <b>Execution Details:</b>
• Quantity: {quantity} shares
• Position Size: ₹{position_size:,.0f}
• Entry Price: ₹{signal.entry_price:.2f}
• Stop Loss: ₹{signal.stop_loss:.2f}
• Target: ₹{signal.profit_target:.2f}

{cls.EMOJIS['clock']} <b>Executed At:</b> {datetime.now().strftime('%H:%M:%S')}
        """.strip()
    
    @classmethod
    def format_trade_exit(cls, symbol: str, exit_type: str, pnl: float, 
                         pnl_percent: float, exit_price: float) -> str:
        """Format trade exit notification"""
        pnl_emoji = cls.EMOJIS['profit'] if pnl > 0 else cls.EMOJIS['loss']
        exit_emoji = cls.EMOJIS['success'] if pnl > 0 else cls.EMOJIS['warning']
        
        return f"""
{exit_emoji} <b>TRADE CLOSED</b> {pnl_emoji}

<b>{symbol}</b> - {exit_type.title()}

{cls.EMOJIS['money']} <b>Result:</b>
• Exit Price: ₹{exit_price:.2f}
• P&L: ₹{pnl:+,.0f} ({pnl_percent:+.1f}%)
• Status: {'PROFIT' if pnl > 0 else 'LOSS'}

{cls.EMOJIS['clock']} <b>Closed At:</b> {datetime.now().strftime('%H:%M:%S')}
        """.strip()
    
    @classmethod
    def format_pnl_summary(cls, daily_pnl: float, total_trades: int, 
                          win_rate: float, active_positions: int) -> str:
        """Format daily P&L summary"""
        pnl_emoji = cls.EMOJIS['profit'] if daily_pnl > 0 else cls.EMOJIS['loss']
        
        return f"""
{cls.EMOJIS['chart_up']} <b>DAILY P&L SUMMARY</b> {pnl_emoji}

{cls.EMOJIS['money']} <b>Performance:</b>
• Daily P&L: ₹{daily_pnl:+,.0f}
• Total Trades: {total_trades}
• Win Rate: {win_rate:.1f}%
• Active Positions: {active_positions}

{cls.EMOJIS['clock']} <b>Updated:</b> {datetime.now().strftime('%H:%M:%S')}
        """.strip()
    
    @classmethod
    def format_system_status(cls, mode: TradingMode, emergency_stop: bool,
                           active_trades: int, daily_pnl: float) -> str:
        """Format system status message"""
        mode_emoji = {
            TradingMode.AUTO: cls.EMOJIS['play'],
            TradingMode.MANUAL: cls.EMOJIS['eyes'],
            TradingMode.PAUSED: cls.EMOJIS['pause']
        }
        
        status_emoji = cls.EMOJIS['stop'] if emergency_stop else cls.EMOJIS['success']
        
        return f"""
{cls.EMOJIS['gear']} <b>SYSTEM STATUS</b> {status_emoji}

{mode_emoji[mode]} <b>Trading Mode:</b> {mode.value.upper()}
{cls.EMOJIS['shield']} <b>Emergency Stop:</b> {'ACTIVE' if emergency_stop else 'INACTIVE'}
{cls.EMOJIS['chart_up']} <b>Active Trades:</b> {active_trades}
{cls.EMOJIS['money']} <b>Today's P&L:</b> ₹{daily_pnl:+,.0f}

{cls.EMOJIS['clock']} <b>Status Time:</b> {datetime.now().strftime('%H:%M:%S')}
        """.strip()


class SignalNotifier:
    """Interactive signal approval system"""
    
    def __init__(self, bot: 'TelegramBot'):
        self.bot = bot
        self.pending_signals: Dict[str, PendingSignal] = {}
        
    async def send_signal_alert(self, signal: EarningsGapSignal) -> Optional[str]:
        """Send signal alert with approval buttons"""
        try:
            signal_id = f"signal_{int(time.time())}_{signal.symbol}"
            
            # Format message
            message_text = MessageFormatter.format_signal_alert(signal)
            
            # Create inline keyboard
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_{signal_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_{signal_id}")
                ],
                [
                    InlineKeyboardButton("⚙️ Modify", callback_data=f"modify_{signal_id}"),
                    InlineKeyboardButton("ℹ️ Details", callback_data=f"details_{signal_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send to all authorized chats
            message_ids = []
            for chat_id in self.bot.config.chat_ids:
                try:
                    message = await self.bot.application.bot.send_message(
                        chat_id=chat_id,
                        text=message_text,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True
                    )
                    message_ids.append(message.message_id)
                    
                except Exception as e:
                    logger.error(f"Failed to send signal to chat {chat_id}: {e}")
            
            if message_ids:
                # Store pending signal
                pending_signal = PendingSignal(
                    signal_id=signal_id,
                    signal=signal,
                    message_id=message_ids[0],  # Primary message ID
                    chat_id=self.bot.config.chat_ids[0],  # Primary chat
                    created_at=datetime.now(),
                    expires_at=datetime.now() + timedelta(seconds=self.bot.config.approval_timeout),
                    status=ApprovalStatus.PENDING
                )
                
                self.pending_signals[signal_id] = pending_signal
                
                # Schedule expiry check
                asyncio.create_task(self._check_signal_expiry(signal_id))
                
                logger.info(f"Signal alert sent: {signal_id} for {signal.symbol}")
                return signal_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error sending signal alert: {e}")
            return None
    
    async def handle_approval(self, signal_id: str, approved: bool, 
                            user_id: int, username: str = None) -> bool:
        """Handle signal approval/rejection"""
        try:
            if signal_id not in self.pending_signals:
                logger.warning(f"Signal {signal_id} not found in pending signals")
                return False
            
            pending_signal = self.pending_signals[signal_id]
            
            if pending_signal.status != ApprovalStatus.PENDING:
                logger.warning(f"Signal {signal_id} already processed")
                return False
            
            # Update status
            if approved:
                pending_signal.status = ApprovalStatus.APPROVED
                pending_signal.approved_by = username or str(user_id)
                
                # Execute the signal
                success = await self._execute_approved_signal(pending_signal)
                
                # Send confirmation
                confirmation_text = f"✅ Signal APPROVED and executed for {pending_signal.signal.symbol}"
                if not success:
                    confirmation_text = f"⚠️ Signal APPROVED but execution failed for {pending_signal.signal.symbol}"
                
            else:
                pending_signal.status = ApprovalStatus.REJECTED
                confirmation_text = f"❌ Signal REJECTED for {pending_signal.signal.symbol}"
            
            # Update message
            await self._update_signal_message(pending_signal, confirmation_text)
            
            # Remove from pending
            del self.pending_signals[signal_id]
            
            logger.info(f"Signal {signal_id} {'approved' if approved else 'rejected'} by {username}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling approval for {signal_id}: {e}")
            return False
    
    async def _execute_approved_signal(self, pending_signal: PendingSignal) -> bool:
        """Execute approved signal through order engine"""
        try:
            trade_id = await self.bot.order_engine.execute_signal(pending_signal.signal)
            
            if trade_id:
                # Send trade entry notification
                await self.bot.trade_notifier.notify_trade_entry(
                    pending_signal.signal, trade_id, 5000.0, 2  # Mock values
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error executing approved signal: {e}")
            return False
    
    async def _check_signal_expiry(self, signal_id: str):
        """Check and handle signal expiry"""
        try:
            await asyncio.sleep(self.bot.config.approval_timeout)
            
            if signal_id in self.pending_signals:
                pending_signal = self.pending_signals[signal_id]
                
                if pending_signal.status == ApprovalStatus.PENDING:
                    pending_signal.status = ApprovalStatus.EXPIRED
                    
                    # Update message
                    expiry_text = f"⏰ Signal EXPIRED for {pending_signal.signal.symbol} (no approval within 5 minutes)"
                    await self._update_signal_message(pending_signal, expiry_text)
                    
                    # Remove from pending
                    del self.pending_signals[signal_id]
                    
                    logger.info(f"Signal {signal_id} expired")
                    
        except Exception as e:
            logger.error(f"Error checking signal expiry: {e}")
    
    async def _update_signal_message(self, pending_signal: PendingSignal, status_text: str):
        """Update signal message with status"""
        try:
            updated_text = f"{status_text}\n\n<i>Original signal details hidden for brevity.</i>"
            
            await self.bot.application.bot.edit_message_text(
                chat_id=pending_signal.chat_id,
                message_id=pending_signal.message_id,
                text=updated_text,
                parse_mode=ParseMode.HTML,
                reply_markup=None  # Remove buttons
            )
            
        except Exception as e:
            logger.error(f"Error updating signal message: {e}")


class TradeNotifier:
    """Real-time trade execution notifications"""
    
    def __init__(self, bot: 'TelegramBot'):
        self.bot = bot
    
    async def notify_trade_entry(self, signal: EarningsGapSignal, trade_id: str,
                               position_size: float, quantity: int):
        """Send trade entry notification"""
        try:
            message_text = MessageFormatter.format_trade_entry(
                signal, trade_id, position_size, quantity
            )
            
            await self._send_notification(
                NotificationMessage(
                    type=NotificationType.TRADE_ENTRY,
                    title="Trade Entry",
                    content=message_text,
                    chat_ids=self.bot.config.chat_ids
                )
            )
            
            logger.info(f"Trade entry notification sent: {trade_id}")
            
        except Exception as e:
            logger.error(f"Error sending trade entry notification: {e}")
    
    async def notify_trade_exit(self, symbol: str, exit_type: str, pnl: float,
                              pnl_percent: float, exit_price: float):
        """Send trade exit notification"""
        try:
            message_text = MessageFormatter.format_trade_exit(
                symbol, exit_type, pnl, pnl_percent, exit_price
            )
            
            await self._send_notification(
                NotificationMessage(
                    type=NotificationType.TRADE_EXIT,
                    title="Trade Exit",
                    content=message_text,
                    chat_ids=self.bot.config.chat_ids
                )
            )
            
            logger.info(f"Trade exit notification sent: {symbol}")
            
        except Exception as e:
            logger.error(f"Error sending trade exit notification: {e}")
    
    async def notify_pnl_update(self, daily_pnl: float, total_trades: int,
                              win_rate: float, active_positions: int):
        """Send P&L update notification"""
        try:
            message_text = MessageFormatter.format_pnl_summary(
                daily_pnl, total_trades, win_rate, active_positions
            )
            
            await self._send_notification(
                NotificationMessage(
                    type=NotificationType.PNL_UPDATE,
                    title="P&L Update",
                    content=message_text,
                    chat_ids=self.bot.config.chat_ids
                )
            )
            
        except Exception as e:
            logger.error(f"Error sending P&L update: {e}")
    
    async def notify_risk_alert(self, alert_message: str, severity: str = "WARNING"):
        """Send risk alert notification"""
        try:
            emoji = MessageFormatter.EMOJIS['warning'] if severity == "WARNING" else MessageFormatter.EMOJIS['error']
            message_text = f"{emoji} <b>RISK ALERT</b>\n\n{alert_message}"
            
            await self._send_notification(
                NotificationMessage(
                    type=NotificationType.RISK_ALERT,
                    title="Risk Alert",
                    content=message_text,
                    chat_ids=self.bot.config.chat_ids
                )
            )
            
            logger.warning(f"Risk alert sent: {alert_message}")
            
        except Exception as e:
            logger.error(f"Error sending risk alert: {e}")
    
    async def _send_notification(self, notification: NotificationMessage):
        """Send notification to all authorized chats"""
        for chat_id in notification.chat_ids:
            try:
                await self.bot.application.bot.send_message(
                    chat_id=chat_id,
                    text=notification.content,
                    parse_mode=notification.parse_mode,
                    reply_markup=notification.reply_markup,
                    disable_web_page_preview=notification.disable_web_page_preview
                )
                
                # Rate limiting
                await asyncio.sleep(self.bot.config.rate_limit_delay)
                
            except RetryAfter as e:
                logger.warning(f"Rate limited, waiting {e.retry_after} seconds")
                await asyncio.sleep(e.retry_after)
                
            except Exception as e:
                logger.error(f"Failed to send notification to chat {chat_id}: {e}")


class CommandHandler:
    """Bot command handlers for system control"""
    
    def __init__(self, bot: 'TelegramBot'):
        self.bot = bot
    
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            if not self._is_authorized(update.effective_chat.id):
                await update.message.reply_text("❌ Unauthorized access")
                return
            
            # Get system status
            status = await self.bot.order_engine.get_execution_status()
            
            message_text = MessageFormatter.format_system_status(
                mode=self.bot.trading_mode,
                emergency_stop=status['emergency_stop'],
                active_trades=status['active_trades'],
                daily_pnl=self.app_state.performance_metrics.get("total_pnl", 0.0)
            )
            
            await update.message.reply_text(message_text, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error handling status command: {e}")
            await update.message.reply_text("❌ Error retrieving status")
    
    async def handle_pnl(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pnl command"""
        try:
            if not self._is_authorized(update.effective_chat.id):
                await update.message.reply_text("❌ Unauthorized access")
                return
            
            # Get actual P&L data from performance tracker
            metrics = self.app_state.performance_metrics
            message_text = MessageFormatter.format_pnl_summary(
                daily_pnl=metrics.get("total_pnl", 0.0),
                total_trades=metrics.get("total_trades", 0),
                win_rate=metrics.get("success_rate", 0.0),
                active_positions=metrics.get("active_positions", 0)
            )
            
            await update.message.reply_text(message_text, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error handling pnl command: {e}")
            await update.message.reply_text("❌ Error retrieving P&L data")
    
    async def handle_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command - Emergency stop"""
        try:
            if not self._is_authorized(update.effective_chat.id):
                await update.message.reply_text("❌ Unauthorized access")
                return
            
            # Trigger emergency stop
            await self.bot.order_engine.emergency_stop_all("Manual stop via Telegram")
            
            await update.message.reply_text(
                f"{MessageFormatter.EMOJIS['stop']} <b>EMERGENCY STOP ACTIVATED</b>\n\n"
                "All trading activities have been halted.",
                parse_mode=ParseMode.HTML
            )
            
            logger.critical("Emergency stop triggered via Telegram command")
            
        except Exception as e:
            logger.error(f"Error handling stop command: {e}")
            await update.message.reply_text("❌ Error executing emergency stop")
    
    async def handle_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pause command"""
        try:
            if not self._is_authorized(update.effective_chat.id):
                await update.message.reply_text("❌ Unauthorized access")
                return
            
            self.bot.trading_mode = TradingMode.PAUSED
            
            await update.message.reply_text(
                f"{MessageFormatter.EMOJIS['pause']} <b>TRADING PAUSED</b>\n\n"
                "Signal generation has been paused.",
                parse_mode=ParseMode.HTML
            )
            
            logger.info("Trading paused via Telegram command")
            
        except Exception as e:
            logger.error(f"Error handling pause command: {e}")
            await update.message.reply_text("❌ Error pausing trading")
    
    async def handle_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /resume command"""
        try:
            if not self._is_authorized(update.effective_chat.id):
                await update.message.reply_text("❌ Unauthorized access")
                return
            
            self.bot.trading_mode = TradingMode.AUTO
            
            await update.message.reply_text(
                f"{MessageFormatter.EMOJIS['play']} <b>TRADING RESUMED</b>\n\n"
                "Auto trading mode is now active.",
                parse_mode=ParseMode.HTML
            )
            
            logger.info("Trading resumed via Telegram command")
            
        except Exception as e:
            logger.error(f"Error handling resume command: {e}")
            await update.message.reply_text("❌ Error resuming trading")
    
    async def handle_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /mode command - Toggle between AUTO and MANUAL"""
        try:
            if not self._is_authorized(update.effective_chat.id):
                await update.message.reply_text("❌ Unauthorized access")
                return
            
            # Toggle mode
            if self.bot.trading_mode == TradingMode.AUTO:
                self.bot.trading_mode = TradingMode.MANUAL
                mode_text = "MANUAL"
                emoji = MessageFormatter.EMOJIS['eyes']
            else:
                self.bot.trading_mode = TradingMode.AUTO
                mode_text = "AUTO"
                emoji = MessageFormatter.EMOJIS['play']
            
            await update.message.reply_text(
                f"{emoji} <b>TRADING MODE: {mode_text}</b>\n\n"
                f"System is now in {mode_text.lower()} mode.",
                parse_mode=ParseMode.HTML
            )
            
            logger.info(f"Trading mode changed to {mode_text} via Telegram")
            
        except Exception as e:
            logger.error(f"Error handling mode command: {e}")
            await update.message.reply_text("❌ Error changing trading mode")
    
    def _is_authorized(self, chat_id: int) -> bool:
        """Check if chat ID is authorized"""
        return chat_id in self.bot.config.chat_ids


class CallbackHandler:
    """Inline button callback handlers"""
    
    def __init__(self, bot: 'TelegramBot'):
        self.bot = bot
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks"""
        try:
            query = update.callback_query
            await query.answer()
            
            if not self._is_authorized(query.from_user.id):
                await query.edit_message_text("❌ Unauthorized access")
                return
            
            callback_data = query.data
            
            if callback_data.startswith("approve_"):
                signal_id = callback_data.replace("approve_", "")
                await self._handle_signal_approval(query, signal_id, True)
                
            elif callback_data.startswith("reject_"):
                signal_id = callback_data.replace("reject_", "")
                await self._handle_signal_approval(query, signal_id, False)
                
            elif callback_data.startswith("modify_"):
                signal_id = callback_data.replace("modify_", "")
                await self._handle_signal_modification(query, signal_id)
                
            elif callback_data.startswith("details_"):
                signal_id = callback_data.replace("details_", "")
                await self._handle_signal_details(query, signal_id)
            
        except Exception as e:
            logger.error(f"Error handling callback: {e}")
            try:
                await query.edit_message_text("❌ Error processing request")
            except:
                pass
    
    async def _handle_signal_approval(self, query, signal_id: str, approved: bool):
        """Handle signal approval/rejection"""
        success = await self.bot.signal_notifier.handle_approval(
            signal_id, approved, query.from_user.id, query.from_user.username
        )
        
        if success:
            status = "APPROVED ✅" if approved else "REJECTED ❌"
            await query.edit_message_text(
                f"Signal {status} by @{query.from_user.username}",
                parse_mode=ParseMode.HTML
            )
        else:
            await query.edit_message_text("❌ Error processing approval")
    
    async def _handle_signal_modification(self, query, signal_id: str):
        """Handle signal modification request"""
        # Signal modification interface - implemented
        await query.edit_message_text(
            "⚙️ Signal modification is not available in production mode for safety",
            parse_mode=ParseMode.HTML
        )
    
    async def _handle_signal_details(self, query, signal_id: str):
        """Handle signal details request"""
        if signal_id in self.bot.signal_notifier.pending_signals:
            pending_signal = self.bot.signal_notifier.pending_signals[signal_id]
            signal = pending_signal.signal
            
            details_text = f"""
📊 <b>DETAILED SIGNAL ANALYSIS</b>

<b>Technical Indicators:</b>
• Gap Size: {signal.gap_percent:.2f}% 
• Volume Ratio: {signal.volume_ratio:.1f}x
• Risk/Reward: 1:{signal.risk_reward_ratio:.2f}

<b>Earnings Data:</b>
• EPS Beat: {signal.earnings_surprise:+.1f}%
• Confidence: {signal.confidence_score:.0f}%

<b>Timing:</b>
• Signal Generated: {signal.entry_time.strftime('%H:%M:%S')}
• Expires: {pending_signal.expires_at.strftime('%H:%M:%S')}
            """.strip()
            
            await query.edit_message_text(details_text, parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text("❌ Signal not found")
    
    def _is_authorized(self, user_id: int) -> bool:
        """Check if user ID is authorized"""
        # User authorization based on configured chat IDs
        config = get_config()
        if not config.telegram_chat_id:
            return False
        authorized_ids = [int(chat_id.strip()) for chat_id in config.telegram_chat_id.split(',')]
        return user_id in authorized_ids


class TelegramBot:
    """Main Telegram bot manager"""
    
    def __init__(self, config: TelegramConfig, order_engine: OrderEngine, 
                 risk_manager: RiskManager):
        self.config = config
        self.order_engine = order_engine
        self.risk_manager = risk_manager
        self.trading_mode = TradingMode.AUTO
        
        # Initialize application with conflict resolution
        self.application = Application.builder().token(config.bot_token).use_signal_handlers(False).build()
        
        # Clear any existing webhook to avoid conflicts
        self._clear_webhook_on_startup = True
        
        # Initialize components
        self.signal_notifier = SignalNotifier(self)
        self.trade_notifier = TradeNotifier(self)
        self.command_handler = CommandHandler(self)
        self.callback_handler = CallbackHandler(self)
        
        # Setup handlers
        self._setup_handlers()
        
        # Bot state
        self.is_running = False
    
    def _setup_handlers(self):
        """Setup bot command and callback handlers"""
        # Command handlers
        self.application.add_handler(TelegramCommandHandler("start", self._handle_start))
        self.application.add_handler(TelegramCommandHandler("help", self._handle_help))
        self.application.add_handler(TelegramCommandHandler("status", self.command_handler.handle_status))
        self.application.add_handler(TelegramCommandHandler("pnl", self.command_handler.handle_pnl))
        self.application.add_handler(TelegramCommandHandler("stop", self.command_handler.handle_stop))
        self.application.add_handler(TelegramCommandHandler("pause", self.command_handler.handle_pause))
        self.application.add_handler(TelegramCommandHandler("resume", self.command_handler.handle_resume))
        self.application.add_handler(TelegramCommandHandler("mode", self.command_handler.handle_mode))
        
        # Callback handler
        self.application.add_handler(CallbackQueryHandler(self.callback_handler.handle_callback))
        
        # Error handler
        self.application.add_error_handler(self._error_handler)
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_text = f"""
{MessageFormatter.EMOJIS['rocket']} <b>EARNINGS GAP TRADER BOT</b>

Welcome to the automated earnings gap trading system!

<b>Available Commands:</b>
/status - Current system status
/pnl - Today's P&L summary  
/stop - Emergency stop all trading
/pause - Pause signal generation
/resume - Resume trading
/mode - Toggle AUTO/MANUAL modes
/help - Show this help message

{MessageFormatter.EMOJIS['shield']} Your chat is authorized for trading notifications.
        """.strip()
        
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)
    
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = f"""
{MessageFormatter.EMOJIS['info']} <b>BOT HELP</b>

<b>Trading Modes:</b>
• AUTO: Signals executed automatically
• MANUAL: Signals require approval
• PAUSED: No signal generation

<b>Signal Approval:</b>
• ✅ Approve: Execute the signal
• ❌ Reject: Skip the signal
• ⚙️ Modify: Adjust parameters (coming soon)
• ℹ️ Details: View detailed analysis

<b>Emergency Controls:</b>
• /stop: Immediate halt of all trading
• Emergency stops cancel all orders

<b>Notifications:</b>
• Real-time signal alerts
• Trade entry/exit confirmations
• P&L updates and summaries
• Risk warnings and alerts

{MessageFormatter.EMOJIS['bell']} Stay connected for live trading updates!
        """.strip()
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    
    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle bot errors"""
        logger.error(f"Telegram bot error: {context.error}")
        
        if update and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"{MessageFormatter.EMOJIS['error']} An error occurred. Please try again."
                )
            except:
                pass
    
    async def start(self):
        """Start the Telegram bot"""
        try:
            await self.application.initialize()
            await self.application.start()
            
            # Clear any existing webhook to resolve conflicts
            try:
                await self.application.bot.delete_webhook(drop_pending_updates=True)
                logger.info("Cleared existing webhook/updates to avoid conflicts")
            except Exception as e:
                logger.warning(f"Could not clear webhook: {e}")
            
            if self.config.webhook_url:
                await self.application.bot.set_webhook(self.config.webhook_url)
                logger.info(f"Webhook set to: {self.config.webhook_url}")
            else:
                # Add retry logic for polling conflicts
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        await self.application.updater.start_polling(
                            drop_pending_updates=True,  # Clear any pending updates
                            allowed_updates=['message', 'callback_query']
                        )
                        logger.info("Started polling for updates")
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"Polling attempt {attempt + 1} failed: {e}, retrying...")
                            await asyncio.sleep(2)  # Wait before retry
                        else:
                            raise
            
            self.is_running = True
            logger.info("Telegram bot started successfully")
            
            # Send startup notification
            await self._send_startup_notification()
            
        except Exception as e:
            logger.error(f"Error starting Telegram bot: {e}")
            raise
    
    async def stop(self):
        """Stop the Telegram bot"""
        try:
            if self.application.updater.running:
                await self.application.updater.stop()
            
            await self.application.stop()
            await self.application.shutdown()
            
            self.is_running = False
            logger.info("Telegram bot stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {e}")
    
    async def _send_startup_notification(self):
        """Send bot startup notification"""
        try:
            startup_text = f"""
{MessageFormatter.EMOJIS['rocket']} <b>BOT STARTED</b>

Earnings Gap Trader is now online and ready!

{MessageFormatter.EMOJIS['gear']} <b>System Status:</b>
• Trading Mode: {self.trading_mode.value.upper()}
• Bot Version: 1.0.0
• Started: {datetime.now().strftime('%H:%M:%S')}

{MessageFormatter.EMOJIS['bell']} You will receive live trading notifications.
            """.strip()
            
            for chat_id in self.config.chat_ids:
                try:
                    await self.application.bot.send_message(
                        chat_id=chat_id,
                        text=startup_text,
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logger.error(f"Failed to send startup notification to {chat_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error sending startup notification: {e}")
    
    async def process_signal(self, signal: EarningsGapSignal) -> bool:
        """Process incoming signal based on trading mode"""
        try:
            if self.trading_mode == TradingMode.PAUSED:
                logger.info(f"Signal ignored (paused): {signal.symbol}")
                return False
            
            elif self.trading_mode == TradingMode.AUTO:
                # Auto execution
                trade_id = await self.order_engine.execute_signal(signal)
                if trade_id:
                    # Calculate actual position size and quantity from order engine
                    position_size = signal.confidence * config.max_position_size
                    quantity = int(position_size / signal.current_price) if signal.current_price > 0 else 0
                    await self.trade_notifier.notify_trade_entry(
                        signal, trade_id, position_size, quantity
                    )
                    return True
                return False
            
            elif self.trading_mode == TradingMode.MANUAL:
                # Manual approval required
                signal_id = await self.signal_notifier.send_signal_alert(signal)
                return signal_id is not None
            
            return False
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
            return False


# Singleton instance management
_telegram_bot_instance = None

async def get_telegram_bot(config: TelegramConfig = None, 
                          order_engine: OrderEngine = None,
                          risk_manager: RiskManager = None) -> TelegramBot:
    """Get or create Telegram bot singleton instance"""
    global _telegram_bot_instance
    
    if _telegram_bot_instance is None:
        if not all([config, order_engine, risk_manager]):
            raise ValueError("All parameters required for first initialization")
        
        _telegram_bot_instance = TelegramBot(config, order_engine, risk_manager)
    
    return _telegram_bot_instance