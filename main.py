"""
Telegram bot for managing BSC pump bot
Maximum simple UI: paste contract -> press start
"""

import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)

from config import settings
from states import ConversationState
from handlers import (
    start,
    cancel,
    help_command,
    balance,
    receive_token_ca,
    receive_pump_amount,
    receive_swap_amount,
    receive_delay,
    confirm_start,
    cancel_start,
    refresh_balance,
    refresh_session_status,
    set_pump_amount_callback,
    set_swap_amount_callback,
    set_delay_callback,
    start_pump_callback,
    pause_pump_callback,
    resume_pump_callback
)
from models.session import session_storage
from api_client import api
from pathlib import Path

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Path to welcome image
WELCOME_IMAGE_PATH = Path(__file__).parent / "assets" / "welcome.jpg"

# Track which users we've already notified about completion
notified_completions = set()


def create_conversation_handler() -> ConversationHandler:
    """Create and configure the main conversation handler"""
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ConversationState.WAITING_TOKEN_CA: [
                CommandHandler("start", start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_token_ca),
                CallbackQueryHandler(set_pump_amount_callback, pattern="^set_pump_amount$"),
                CallbackQueryHandler(set_swap_amount_callback, pattern="^set_swap_amount$"),
                CallbackQueryHandler(set_delay_callback, pattern="^set_delay$"),
                CallbackQueryHandler(start_pump_callback, pattern="^start_pump$"),
                CallbackQueryHandler(pause_pump_callback, pattern="^pause_pump$"),
                CallbackQueryHandler(resume_pump_callback, pattern="^resume_pump$")
            ],
            ConversationState.WAITING_PUMP_AMOUNT: [
                CommandHandler("start", start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_pump_amount)
            ],
            ConversationState.WAITING_SWAP_AMOUNT: [
                CommandHandler("start", start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_swap_amount)
            ],
            ConversationState.WAITING_DELAY: [
                CommandHandler("start", start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_delay)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
        ],
        allow_reentry=True,
    )


async def check_session_completions(context):
    """Background job to check for completed pump sessions"""
    global notified_completions
    
    # Get all active sessions
    for telegram_id, session in list(session_storage._sessions.items()):
        # Skip if not started on backend or already notified
        if not session.backend_started or telegram_id in notified_completions:
            continue
        
        try:
            # Check status from backend
            status_data = await api.get_session_status(telegram_id)
            status = status_data.get("status", "Not Started")
            
            # If completed successfully
            if isinstance(status, dict) and "Success" in status:
                # Get config message info to delete it
                message_id = context.bot_data.get(f'config_message_{telegram_id}')
                chat_id = context.bot_data.get(f'config_chat_{telegram_id}')
                
                # Delete old config message if exists
                if message_id and chat_id:
                    try:
                        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except:
                        pass
                
                success_stats = status.get("Success", {})
                pumped_bnb = float(success_stats.get("pumped_amount_wei", "0")) / 1e18
                pumped_usd = success_stats.get("pumped_amount_usd", "0")
                time_spent = int(success_stats.get("time_spent_millis", 0)) / 1000
                
                completion_text = (
                    "🎉 **Volume Pumping Completed!**\n\n"
                    f"✅ Successfully generated volume for your token\n"
                    f"💰 Total Pumped: **{pumped_bnb:.4f} BNB** (~${pumped_usd})\n"
                    f"⏱ Time: **{time_spent:.0f}s**\n\n"
                    f"🔗 Token: `{session.token_ca}`\n\n"
                    "Ready to start a new session? Use /start"
                )
                
                # Send completion message with image
                if WELCOME_IMAGE_PATH.exists():
                    with open(WELCOME_IMAGE_PATH, 'rb') as photo:
                        await context.bot.send_photo(
                            chat_id=telegram_id,
                            photo=photo,
                            caption=completion_text,
                            parse_mode='Markdown'
                        )
                else:
                    await context.bot.send_message(
                        chat_id=telegram_id,
                        text=completion_text,
                        parse_mode='Markdown'
                    )
                
                # Mark as notified
                notified_completions.add(telegram_id)
                
                # Clean up session
                session.backend_started = False
                session.is_paused = False
                
        except Exception as e:
            logger.error(f"Error checking session completion for user {telegram_id}: {e}")


def register_handlers(application: Application) -> None:
    """Register all bot handlers"""
    # Main conversation handler
    conv_handler = create_conversation_handler()
    application.add_handler(conv_handler)
    
    # Callback query handlers for buttons (outside conversation)
    application.add_handler(
        CallbackQueryHandler(confirm_start, pattern="^confirm_start$")
    )
    application.add_handler(
        CallbackQueryHandler(cancel_start, pattern="^cancel_start$")
    )
    application.add_handler(
        CallbackQueryHandler(refresh_balance, pattern="^refresh_balance$")
    )
    application.add_handler(
        CallbackQueryHandler(refresh_session_status, pattern="^refresh_session_status$")
    )
    
    # Standalone command handlers
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("help", help_command))


def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(settings.telegram_bot_token).build()
    
    # Register all handlers
    register_handlers(application)
    
    # Add background job to check session completions every 10 seconds
    application.job_queue.run_repeating(
        check_session_completions,
        interval=10,
        first=5
    )
    
    # Start the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
