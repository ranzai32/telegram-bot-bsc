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
    pause_pump_callback
)

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


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
                CallbackQueryHandler(pause_pump_callback, pattern="^pause_pump$")
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
    
    # Start the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
