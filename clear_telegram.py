#!/usr/bin/env python3
"""
Clear Telegram Bot Session
This script clears any existing webhook or polling sessions for the bot
"""

import asyncio
import os
from telegram import Bot
from telegram.error import TelegramError

async def clear_bot_session():
    """Clear any existing bot sessions"""
    
    # Load bot token from environment
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "7912170276:AAGjJu-u-UCnA0PT4pOEzilDE775EoBmw5Y")
    
    if not bot_token or bot_token == "your_telegram_bot_token":
        print("ERROR: No valid bot token found")
        return False
    
    try:
        print("Connecting to Telegram Bot API...")
        bot = Bot(token=bot_token)
        
        # Get current bot info
        me = await bot.get_me()
        print(f"Connected to bot: @{me.username}")
        
        # Clear webhook
        print("Clearing webhook...")
        await bot.delete_webhook(drop_pending_updates=True)
        print("Webhook cleared")
        
        # Get current updates and drop them
        print("Dropping pending updates...")
        updates = await bot.get_updates(limit=100, timeout=1)
        if updates:
            print(f"Dropped {len(updates)} pending updates")
            # Get updates again to clear them
            await bot.get_updates(offset=updates[-1].update_id + 1, limit=1, timeout=1)
        else:
            print("No pending updates found")
        
        print("Bot session cleared successfully!")
        return True
        
    except TelegramError as e:
        print(f"Telegram error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

async def main():
    print("================================================")
    print("   TELEGRAM BOT SESSION CLEANER")
    print("================================================")
    print()
    
    success = await clear_bot_session()
    
    print()
    print("================================================")
    if success:
        print("SUCCESS: Bot session cleared - you can now start the system")
    else:
        print("FAILED: Failed to clear bot session - check your bot token")
    print("================================================")

if __name__ == "__main__":
    asyncio.run(main())