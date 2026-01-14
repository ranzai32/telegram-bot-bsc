import logging
import os
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from api_client import api
from models import session_storage
from states import ConversationState
from keyboards.inline import get_refresh_keyboard

logger = logging.getLogger(__name__)

WELCOME_IMAGE_PATH = Path(__file__).parent.parent / "assets" / "welcome.jpg"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start command - bot initialization"""
    user = update.effective_user
    telegram_id = user.id
    
    try:
        wallet_data = await api.get_or_create_wallet(telegram_id)
        wallet_address = wallet_data["wallet_dto"]["evm_address"]
        
        balance_data = await api.check_wallet_balance(telegram_id)
        balance_ui = balance_data["ui"]

        try:
            balance_formatted = f"{float(balance_ui):.3f}"
            balance_float = float(balance_ui)
        except:
            balance_formatted = balance_ui
            balance_float = 0.0

        if balance_float >= 0.097:
            welcome_text = (
                f"💼 Your wallet: `{wallet_address}`\n"
                f"💰 Current balance: {balance_formatted} BNB\n\n"
                f"🚀 Ready to start!\n"
                f"Send me the token contract address (CA) to begin pumping.\n\n"
                f"Example: `0x718447E29B90D00461966D01E533Fa1b69574444`"
            )
        else:
            welcome_text = (
                f"⚡️Save 30% vs others while keeping your chart fully organic — from just 0.097BNB!\n\n"
                f"— 🌿Organic & randomized: Unique wallets, random buy/sell and timing — no bot-look, no spam\n\n"
                f"— 🛠Manage it your way: Run with battle-tested defaults or customize your own settings — your chart, your rules\n\n"
                f"🎁 Free Microbots and Bumps included\n\n"
                f"➔ Deposit to this address to start:\n"
                f"`{wallet_address}`\n\n"
                f"💰 Current balance: {balance_formatted} BNB\n"
                f"⚠️ Minimum required: 0.097 BNB"
            )
        
        reply_markup = get_refresh_keyboard() if balance_float < 0.097 else None
        
        if WELCOME_IMAGE_PATH.exists():
            with open(WELCOME_IMAGE_PATH, 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=welcome_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
        else:
            await update.message.reply_text(
                welcome_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        
        session_storage.create(telegram_id)
        
        return ConversationState.WAITING_TOKEN_CA
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while creating the wallet. Please try again later."
        )
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    telegram_id = update.effective_user.id
    
    session_storage.delete(telegram_id)
    
    await update.message.reply_text(
        "❌ Operation cancelled.\n"
        "Use /start to start over."
    )
    
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = (
        "🤖 *BSC Pump Bot*\n\n"
        "*Available commands:*\n"
        "/start - Start bot and create session\n"
        "/balance - Check wallet balance\n"
        "/cancel - Cancel current operation\n"
        "/help - Show this message\n\n"
        "*How to use:*\n"
        "1. Send /start\n"
        "2. Paste token contract address\n"
        "3. Enter pump amount\n"
        "4. Enter swap amount\n"
        "5. Press START 🚀"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def   balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check wallet balance"""
    telegram_id = update.effective_user.id
    
    try:
        balance_data = await api.check_wallet_balance(telegram_id)
        balance_ui = balance_data["ui"]
        balance_wei = balance_data["raw"]
        
        # format balance to max 3 decimal places
        try:
            balance_formatted = f"{float(balance_ui):.3f}"
        except:
            balance_formatted = balance_ui
        
        # сonvert to USD
        usd_data = await api.bnb_to_usd(balance_wei)
        balance_usd = usd_data["amount_usd"]
        
        await update.message.reply_text(
            f"💰 Your balance:\n\n"
            f"BNB: {balance_formatted}\n"
            f"USD: ≈${balance_usd:.2f}"
        )
        
    except Exception as e:
        logger.error(f"Error checking balance: {e}")
        await update.message.reply_text(
            f"❌ Error checking balance: {str(e)}"
        )
