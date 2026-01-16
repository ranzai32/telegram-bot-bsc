"""Session creation handlers - token, amounts, confirmation"""

import logging
from pathlib import Path
from decimal import Decimal
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from api_client import api
from models import session_storage
from states import ConversationState
from keyboards import get_confirmation_keyboard, get_session_status_keyboard
from utils import bnb_to_wei, wei_to_bnb
from config import settings

logger = logging.getLogger(__name__)

WELCOME_IMAGE_PATH = Path(__file__).parent.parent / "assets" / "welcome.jpg"


async def _update_config_menu(context: ContextTypes.DEFAULT_TYPE, telegram_id: int, confirmation_text: str = None):
    """Helper function to update configuration menu"""
    session = session_storage.get(telegram_id)
    if not session or not session.token_ca:
        return None
    
    token_ca = session.token_ca
    
    status = "Not Started"
    status_text = "⚪️ Not Started"
    
    if session.backend_started:
        try:
            status_data = await api.get_session_status(telegram_id)
            status = status_data.get("status", "Not Started")
            if status == "InProcess":
                status_text = "🔄 In Progress"
            elif isinstance(status, dict) and "Success" in status:
                status_text = "✅ Completed"
            elif isinstance(status, dict) and "Error" in status:
                status_text = "❌ Error"
            else:
                status_text = "⚪️ Not Started"
        except:
            pass
    
    try:
        balance_data = await api.check_wallet_balance(telegram_id)
        balance_bnb = f"{float(balance_data['ui']):.4f}"
    except:
        balance_bnb = "N/A"
    
    pump_amount_bnb = "0.0"
    pump_indicator = "🔴"
    swap_amount_bnb = "0.0"
    swap_indicator = "🔴"
    delay_seconds = "1.0"
    delay_indicator = "🔴"
    
    if session.pump_amount_wei and float(session.pump_amount_wei) > 0:
        pump_amount_bnb = f"{float(session.pump_amount_wei) / 1e18:.4f}"
        pump_indicator = "🟢"
    if session.swap_amount_wei and float(session.swap_amount_wei) > 0:
        swap_amount_bnb = f"{float(session.swap_amount_wei) / 1e18:.4f}"
        swap_indicator = "🟢"
    if hasattr(session, 'delay_millis') and session.delay_millis:
        delay_seconds = f"{session.delay_millis / 1000:.1f}"
        delay_indicator = "🟢"
    
    from keyboards.inline import get_pump_config_keyboard
    
    dex_link = f"https://dexscreener.com/bsc/{token_ca}"
    
    config_text = (
        f"{'✅ ' + confirmation_text + chr(10) + chr(10) if confirmation_text else ''}"
        f"🎯 **Token Analysis Complete**\n\n"
        f"✅ Verified & Ready for Volume Boost\n"
        f"🔗 CA: [{token_ca[:10]}...{token_ca[-8:]}]({dex_link})\n\n"
        f"⚙️ **Current Configuration:**\n"
        f"{pump_indicator} Pump Amount: **{pump_amount_bnb} BNB**\n"
        f"{swap_indicator} Swap Amount: **{swap_amount_bnb} BNB**\n"
        f"{delay_indicator} Delay: **{delay_seconds}s**\n\n"
        f"📊 Status: {status_text}\n"
        f"💰 Balance: **{balance_bnb} BNB**\n\n"
        f"👇 Configure amounts or start pumping:"
    )
    
    message_id = context.user_data.get('config_message_id')
    chat_id = context.user_data.get('config_chat_id')

    pump_configured = session.pump_amount_wei and float(session.pump_amount_wei) > 0
    swap_configured = session.swap_amount_wei and float(session.swap_amount_wei) > 0

    display_status = "Paused" if session.is_paused else status
    
    if message_id and chat_id:
        await context.bot.edit_message_text(
            text=config_text,
            chat_id=chat_id,
            message_id=message_id,
            parse_mode='Markdown',
            reply_markup=get_pump_config_keyboard(display_status, pump_configured, swap_configured),
            disable_web_page_preview=True
        )
    
    return config_text


async def receive_token_ca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receiving token contract address"""
    telegram_id = update.effective_user.id
    token_ca = update.message.text.strip()
    
    await update.message.reply_text("🔍 Checking token...")
    
    try:
        support_data = await api.check_token_supported(token_ca)
        
        if not support_data.get("is_supported", False):
            await update.message.reply_text(
                "❌ This token is not supported.\n"
                "Possible reasons:\n"
                "• No liquidity pools on PancakeSwap\n"
                "• Token is incompatible with the bot\n\n"
                "Send another contract address or /cancel to abort."
            )
            return ConversationState.WAITING_TOKEN_CA
        
        pools_data = await api.get_token_pools(token_ca)
        pools = pools_data.get("pools", {})
        if isinstance(pools, dict):
            pools_count = len(pools.get("pairs", []))
        else:
            # If pools is already a list
            pools_count = len(pools) if isinstance(pools, list) else 0
        
        session = session_storage.get(telegram_id)
        if session:
            session.token_ca = token_ca
        
        status = "Not Started"
        status_text = "⚪️ Not Started"
        
        if session and session.backend_started:
            try:
                status_data = await api.get_session_status(telegram_id)
                status = status_data.get("status", "Not Started")
                if status == "InProcess":
                    status_text = "🔄 In Progress"
                elif isinstance(status, dict) and "Success" in status:
                    status_text = "✅ Completed"
                elif isinstance(status, dict) and "Error" in status:
                    status_text = "❌ Error"
                else:
                    status_text = "⚪️ Not Started"
            except:
                pass
        
        try:
            balance_data = await api.check_wallet_balance(telegram_id)
            balance_bnb = f"{float(balance_data['ui']):.4f}"
        except:
            balance_bnb = "N/A"
        
        pump_amount_bnb = "0.0"
        pump_indicator = "🔴"
        swap_amount_bnb = "0.0"
        swap_indicator = "🔴"
        delay_seconds = "1.0"
        delay_indicator = "🔴"
        
        if session:
            if session.pump_amount_wei and float(session.pump_amount_wei) > 0:
                pump_amount_bnb = f"{float(session.pump_amount_wei) / 1e18:.4f}"
                pump_indicator = "🟢"
            if session.swap_amount_wei and float(session.swap_amount_wei) > 0:
                swap_amount_bnb = f"{float(session.swap_amount_wei) / 1e18:.4f}"
                swap_indicator = "🟢"
            if hasattr(session, 'delay_millis') and session.delay_millis:
                delay_seconds = f"{session.delay_millis / 1000:.1f}"
                delay_indicator = "🟢"
        
        from keyboards.inline import get_pump_config_keyboard
        
        dex_link = f"https://dexscreener.com/bsc/{token_ca}"
        
        config_message = await update.message.reply_text(
            f"🎯 **Token Analysis Complete**\n\n"
            f"✅ Verified & Ready for Volume Boost\n"
            f"📊 Active Pools: {pools_count}\n"
            f"🔗 CA: [{token_ca[:10]}...{token_ca[-8:]}]({dex_link})\n\n"
            f"⚙️ **Current Configuration:**\n"
            f"{pump_indicator} Pump Amount: **{pump_amount_bnb} BNB**\n"
            f"{swap_indicator} Swap Amount: **{swap_amount_bnb} BNB**\n"
            f"{delay_indicator} Delay: **{delay_seconds}s**\n\n"
            f"📊 Status: {status_text}\n"
            f"💰 Balance: **{balance_bnb} BNB**\n\n"
            f"👇 Configure amounts or start pumping:",
            parse_mode='Markdown',
            reply_markup=get_pump_config_keyboard(
                status,
                pump_configured=(session and session.pump_amount_wei and float(session.pump_amount_wei) > 0),
                swap_configured=(session and session.swap_amount_wei and float(session.swap_amount_wei) > 0)
            ),
            disable_web_page_preview=True
        )
        
        # save for updates and background job
        context.user_data['config_message_id'] = config_message.message_id
        context.user_data['config_chat_id'] = config_message.chat_id
        context.application.bot_data[f'config_message_{telegram_id}'] = config_message.message_id
        context.application.bot_data[f'config_chat_{telegram_id}'] = config_message.chat_id
        
        return ConversationState.WAITING_TOKEN_CA
        
    except Exception as e:
        logger.error(f"Error checking token: {e}")
        await update.message.reply_text(
            f"❌ Error checking token: {str(e)}\n"
            "Check the contract address and try again."
        )
        return ConversationState.WAITING_TOKEN_CA


async def receive_pump_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receiving pump amount"""
    telegram_id = update.effective_user.id
    
    error_message_id = context.user_data.get('pump_amount_error_message_id')
    if error_message_id:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=error_message_id
            )
            context.user_data.pop('pump_amount_error_message_id', None)
        except:
            pass
    
    try:
        pump_amount_bnb = Decimal(update.message.text.strip())
        
        if pump_amount_bnb <= 0:
            error_msg = await update.message.reply_text("❌ Amount must be greater than 0. Try again:")
            context.user_data['pump_amount_error_message_id'] = error_msg.message_id
            return ConversationState.WAITING_PUMP_AMOUNT
        
        # сheck that pump amount doesn't exceed balance
        balance_data = await api.check_wallet_balance(telegram_id)
        balance_bnb = Decimal(balance_data["ui"])
        
        if pump_amount_bnb > balance_bnb:
            error_msg = await update.message.reply_text(
                f"❌ Pump Amount cannot exceed your balance\n\n"
                f"💰 Your Balance: **{balance_bnb:.4f} BNB**\n"
                f"📊 Maximum Allowed: **{balance_bnb:.4f} BNB**\n\n"
                f"Please enter a smaller amount:",
                parse_mode='Markdown'
            )
            context.user_data['pump_amount_error_message_id'] = error_msg.message_id
            return ConversationState.WAITING_PUMP_AMOUNT
        
        try:
            await update.message.delete()
        except:
            pass
        
        pump_amount_wei = bnb_to_wei(pump_amount_bnb)
        
        usd_data = await api.bnb_to_usd(pump_amount_wei)
        pump_amount_usd = usd_data["amount_usd"]
        
        session = session_storage.get(telegram_id)
        if session:
            session.pump_amount_wei = pump_amount_wei
        
        # reset max swap amount cache when pump amount changes
        context.user_data.pop('max_swap_amount_wei', None)
        
        await _update_config_menu(
            context, 
            telegram_id, 
            f"Pump amount set to {pump_amount_bnb} BNB (≈${pump_amount_usd:.2f})"
        )
        
        return ConversationState.WAITING_TOKEN_CA
        
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid format. Enter a number (e.g. 0.1):"
        )
        return ConversationState.WAITING_PUMP_AMOUNT
    except Exception as e:
        logger.error(f"Error processing pump amount: {e}")
        await update.message.reply_text(
            f"❌ Error: {str(e)}\nTry again:"
        )
        return ConversationState.WAITING_PUMP_AMOUNT


async def receive_swap_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receiving swap amount and launch confirmation"""
    telegram_id = update.effective_user.id
    
    error_message_id = context.user_data.get('swap_amount_error_message_id')
    if error_message_id:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=error_message_id
            )
            context.user_data.pop('swap_amount_error_message_id', None)
        except:
            pass
    
    try:
        swap_amount_bnb = Decimal(update.message.text.strip())
        
        if swap_amount_bnb <= 0:
            error_msg = await update.message.reply_text("❌ Amount must be greater than 0. Try again:")
            context.user_data['swap_amount_error_message_id'] = error_msg.message_id
            return ConversationState.WAITING_SWAP_AMOUNT
        
        # check against maximum allowed swap amount
        max_swap_amount_wei = context.user_data.get('max_swap_amount_wei', '0')
        max_allowed_bnb = Decimal(max_swap_amount_wei) / Decimal('1000000000000000000')
        
        if swap_amount_bnb > max_allowed_bnb:
            error_msg = await update.message.reply_text(
                f"❌ Swap Amount exceeds maximum allowed\n\n"
                f"📊 Maximum Allowed: **{max_allowed_bnb:.6f} BNB**\n"
                f"💡 This is calculated based on your Pump Amount\n\n"
                f"Please enter a smaller amount:",
                parse_mode='Markdown'
            )
            context.user_data['swap_amount_error_message_id'] = error_msg.message_id
            return ConversationState.WAITING_SWAP_AMOUNT
        
        try:
            await update.message.delete()
        except:
            pass
        
        swap_amount_wei = bnb_to_wei(swap_amount_bnb)
        
        usd_data = await api.bnb_to_usd(swap_amount_wei)
        swap_amount_usd = usd_data["amount_usd"]
        
        session = session_storage.get(telegram_id)
        if not session:
            await update.message.reply_text("❌ Session expired. Start over with /start")
            return ConversationHandler.END
        
        session.swap_amount_wei = swap_amount_wei
        
        # if session is already running, update swap amount on backend
        if session.backend_started:
            try:
                await api.set_session_swap_amount(telegram_id, swap_amount_wei)
            except Exception as e:
                logger.error(f"Error updating swap amount on backend: {e}")
                error_msg = await update.message.reply_text(
                    f"⚠️ Warning: Could not update backend. Error: {str(e)}"
                )
        
        await _update_config_menu(
            context, 
            telegram_id, 
            f"Swap amount set to {swap_amount_bnb} BNB (≈${swap_amount_usd:.2f})"
        )
        
        return ConversationState.WAITING_TOKEN_CA
        
    except ValueError:
        error_msg = await update.message.reply_text(
            "❌ Invalid format. Enter a number (e.g. 0.01):"
        )
        context.user_data['swap_amount_error_message_id'] = error_msg.message_id
        return ConversationState.WAITING_SWAP_AMOUNT
    except Exception as e:
        logger.error(f"Error processing swap amount: {e}")
        error_msg = await update.message.reply_text(
            f"❌ Error: {str(e)}\nTry again:"
        )
        context.user_data['swap_amount_error_message_id'] = error_msg.message_id
        return ConversationState.WAITING_SWAP_AMOUNT


async def confirm_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handling START button press"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    
    session = session_storage.get(telegram_id)
    if not session:
        await query.edit_message_text("❌ Session expired. Start over with /start")
        return
    
    try:
        result = await api.start_session(
            telegram_id=telegram_id,
            token_ca=session.token_ca,
            pump_amount_wei=session.pump_amount_wei,
            swap_amount_wei=session.swap_amount_wei,
            delay_millis=session.delay_millis
        )
        
        if result.get("created", False):
            try:
                status_data = await api.get_session_status(telegram_id)
                status = status_data.get("status", "InProcess")
                
                balance_data = await api.check_wallet_balance(telegram_id)
                balance_ui = balance_data["ui"]
                balance_formatted = f"{float(balance_ui):.3f}"
            except:
                status = "InProcess"
                balance_formatted = "N/A"
            
            if status == "InProcess":
                status_text = "🔄 In Progress"
            elif isinstance(status, dict):
                if "Success" in status:
                    status_text = "✅ Success"
                elif "Error" in status:
                    status_text = f"❌ Error: {status['Error']}"
                else:
                    status_text = str(status)
            else:
                status_text = str(status)
            
            await query.edit_message_text(
                "🚀 Volume pumping session started successfully!\n\n"
                f"Status: {status_text}\n"
                f"Wallet Balance: {balance_formatted} BNB\n\n"
                "Press Refresh to update data.",
                reply_markup=get_session_status_keyboard()
            )
        else:
            await query.edit_message_text(
                "⚠️ You already have an active session.\n"
                "Use /stop to stop it, then try again."
            )
        
        session_storage.delete(telegram_id)
        
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        await query.edit_message_text(
            f"❌ Error starting session: {str(e)}\n"
            "Try again with /start"
        )


async def cancel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handling Cancel button press"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    session_storage.delete(telegram_id)
    
    await query.edit_message_text(
        "❌ Operation cancelled.\n"
        "Use /start to start over."
    )


async def refresh_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Refresh button press to check balance"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    
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
        
        min_deposit = settings.min_deposit_bnb
        logger.info(f"Refresh balance: {balance_float} BNB (>= {min_deposit - 0.003}: {balance_float >= min_deposit - 0.003})")
        
        if balance_float >= min_deposit - 0.003:
            logger.info("Balance is sufficient, switching to ready message")
            welcome_text = (
                f"💼 Your wallet: `{wallet_address}`\n"
                f"💰 Current balance: {balance_formatted} BNB\n\n"
                f"🚀 Ready to start!\n"
                f"Send me the token contract address (CA) to begin pumping.\n\n"
                f"Example: `0x718447E29B90D00461966D01E533Fa1b69574444`"
            )
            
            if WELCOME_IMAGE_PATH.exists():
                logger.info("Deleting old message and sending new one with photo")
                await query.message.delete()
                with open(WELCOME_IMAGE_PATH, 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=telegram_id,
                        photo=photo,
                        caption=welcome_text,
                        parse_mode='Markdown'
                    )
            else:
                logger.info("Photo not found, editing message text")
                try:
                    await query.message.delete()
                    await context.bot.send_message(
                        chat_id=telegram_id,
                        text=welcome_text,
                        parse_mode='Markdown'
                    )
                except:
                    await query.edit_message_text(
                        welcome_text,
                        parse_mode='Markdown'
                    )
        else:
            from keyboards.inline import get_refresh_keyboard
            from telegram.error import BadRequest
            
            welcome_text = (
                f"⚡️Save 30% vs others while keeping your chart fully organic — from just {settings.min_deposit_bnb} BNB!\n\n"
                f"— 🌿Organic & randomized: Unique wallets, random buy/sell and timing — no bot-look, no spam\n\n"
                f"— 🛠Manage it your way: Run with battle-tested defaults or customize your own settings — your chart, your rules\n\n"
                f"🎁 Free Microbots and Bumps included\n\n"
                f"➔ Deposit to this address to start:\n"
                f"`{wallet_address}`\n\n"
                f"💰 Current balance: {balance_formatted} BNB\n"
                f"⚠️ Minimum required: {settings.min_deposit_bnb} BNB"
            )
            
            try:
                await query.edit_message_caption(
                    caption=welcome_text,
                    parse_mode='Markdown',
                    reply_markup=get_refresh_keyboard()
                )
            except BadRequest as e:
                if "not modified" in str(e).lower():
                    pass
                else:
                    raise
            
    except Exception as e:
        logger.error(f"Error refreshing balance: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)


async def refresh_session_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Refresh Session Status button press"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    
    try:
        from telegram.error import BadRequest
        
        status_data = await api.get_session_status(telegram_id)
        status = status_data.get("status", "Unknown")
        
        balance_data = await api.check_wallet_balance(telegram_id)
        balance_ui = balance_data["ui"]
        balance_formatted = f"{float(balance_ui):.3f}"
        
        if status == "InProcess":
            status_text = "🔄 In Progress"
        elif isinstance(status, dict):
            if "Success" in status:
                stats = status["Success"]
                pumped_wei = stats.get("pumped_amount_wei", "0")
                pumped_usd = stats.get("pumped_amount_usd", "0")
                time_ms = stats.get("time_spent_millis", 0)
                status_text = (
                    f"✅ Success\n"
                    f"  Pumped: {float(pumped_wei)/1e18:.4f} BNB (${pumped_usd})\n"
                    f"  Time: {time_ms/1000:.1f}s"
                )
            elif "Error" in status:
                status_text = f"❌ Error: {status['Error']}"
            else:
                status_text = str(status)
        else:
            status_text = str(status)
        
        message_text = (
            "🚀 Volume pumping session status:\n\n"
            f"Status: {status_text}\n"
            f"Wallet Balance: {balance_formatted} BNB\n\n"
            "Press Refresh to update data."
        )
        
        try:
            await query.edit_message_text(
                message_text,
                reply_markup=get_session_status_keyboard()
            )
        except BadRequest as e:
            if "not modified" in str(e).lower():
                pass
            else:
                raise
        
    except Exception as e:
        logger.error(f"Error refreshing session status: {e}")
        try:
            await query.edit_message_text(
                f"❌ Error getting status: {str(e)}\n"
                "The session may have ended or not been found.",
                reply_markup=get_session_status_keyboard()
            )
        except:
            await query.answer(f"❌ Error: {str(e)}", show_alert=True)


async def set_pump_amount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Pump Amount button"""
    query = update.callback_query
    telegram_id = update.effective_user.id
    
    session = session_storage.get(telegram_id)
    
    if session and session.backend_started and not session.is_paused:
        try:
            status_data = await api.get_session_status(telegram_id)
            status = status_data.get("status", "Not Started")
            if status == "InProcess":
                await query.answer("⚠️ Cannot change Pump Amount while session is running!", show_alert=True)
                return ConversationState.WAITING_TOKEN_CA
        except:
            pass
    
    await query.answer()
    
    context.user_data['config_message_id'] = query.message.message_id
    context.user_data['config_chat_id'] = query.message.chat_id
    
    await query.edit_message_text(
        "💰 **What is Pump Amount?**\n\n"
        "This is the **total budget** for your volume pumping session.\n\n"
        "💡 The bot will use this amount to create buy/sell transactions,\n"
        "generating trading volume for your token.\n\n"
        "⚠️ **Important:**\n"
        "• Cannot be changed after session starts\n\n"
        "📝 Enter pump amount in BNB:\n\n"
        "Example: 0.5",
        parse_mode='Markdown'
    )
    
    return ConversationState.WAITING_PUMP_AMOUNT


async def set_swap_amount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Swap Amount button"""
    query = update.callback_query
    telegram_id = update.effective_user.id
    
    # check if pump amount is set first
    session = session_storage.get(telegram_id)
    if not session or not session.pump_amount_wei or float(session.pump_amount_wei) <= 0:
        await query.answer("⚠️ Please set Pump Amount first!", show_alert=True)
        return ConversationState.WAITING_TOKEN_CA
    
    await query.answer()

    # use cached max swap amount if available, otherwise fetch from backend
    max_swap_amount_wei = context.user_data.get('max_swap_amount_wei')
    
    if not max_swap_amount_wei:
        try:
            max_swap_data = await api.estimate_max_swap_amount(session.pump_amount_wei)
            max_swap_amount_wei = max_swap_data["swap_amount_wei"]
            
            # save max swap amount in context for future use
            context.user_data['max_swap_amount_wei'] = max_swap_amount_wei
        except Exception as e:
            logger.error(f"Error estimating max swap amount: {e}")
            max_swap_amount_wei = "0"
            context.user_data['max_swap_amount_wei'] = "0"
    
    max_swap_amount_bnb = float(max_swap_amount_wei) / 1e18
    
    context.user_data['config_message_id'] = query.message.message_id
    context.user_data['config_chat_id'] = query.message.chat_id
    
    await query.edit_message_text(
        "💱 **Set Swap Amount**\n\n"
        "Enter the amount in BNB for each swap operation.\n\n"
        "⚠️ **Important Limits:**\n"
        f"• Maximum: **{max_swap_amount_bnb:.6f} BNB**\n"
        "  (calculated based on your Pump Amount)\n\n"
        "📝 Enter swap amount in BNB:\n\n"
        "Example: 0.01",
        parse_mode='Markdown'
    )
    
    return ConversationState.WAITING_SWAP_AMOUNT


async def set_delay_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Set Delay button"""
    query = update.callback_query
    await query.answer()
    
    # save message_id to update it later
    context.user_data['config_message_id'] = query.message.message_id
    context.user_data['config_chat_id'] = query.message.chat_id
    
    await query.edit_message_text(
        "⏱️ **Set Transaction Delay**\n\n"
        "Enter the delay between transactions in seconds.\n"
        "Example: 1 (= 1 second)\n\n"
        "Recommended: 0.5-2 seconds for optimal performance.",
        parse_mode='Markdown'
    )
    
    return ConversationState.WAITING_DELAY


async def receive_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receiving delay value"""
    telegram_id = update.effective_user.id
    
    error_message_id = context.user_data.get('delay_error_message_id')
    if error_message_id:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=error_message_id
            )
            context.user_data.pop('delay_error_message_id', None)
        except:
            pass
    
    try:
        delay_seconds = float(update.message.text.strip())
        
        if delay_seconds <= 0:
            error_msg = await update.message.reply_text("❌ Delay must be greater than 0. Try again:")
            context.user_data['delay_error_message_id'] = error_msg.message_id
            return ConversationState.WAITING_DELAY
        
        try:
            await update.message.delete()
        except:
            pass
        
        delay_millis = int(delay_seconds * 1000)
        
        session = session_storage.get(telegram_id)
        if session:
            session.delay_millis = delay_millis
            
            # if session is already running, update delay on backend
            if session.backend_started:
                try:
                    await api.set_session_delay(telegram_id, delay_millis)
                except Exception as e:
                    logger.error(f"Error updating delay on backend: {e}")
                    error_msg = await update.message.reply_text(
                        f"⚠️ Warning: Could not update backend. Error: {str(e)}"
                    )
        
        await _update_config_menu(
            context, 
            telegram_id, 
            f"Delay set to {delay_seconds}s"
        )
        
        return ConversationState.WAITING_TOKEN_CA
        
    except ValueError:
        error_msg = await update.message.reply_text(
            "❌ Invalid format. Enter a number in seconds (e.g. 1 or 0.5):"
        )
        context.user_data['delay_error_message_id'] = error_msg.message_id
        return ConversationState.WAITING_DELAY
    except Exception as e:
        logger.error(f"Error processing delay: {e}")
        error_msg = await update.message.reply_text(
            f"❌ Error: {str(e)}\nTry again:"
        )
        context.user_data['delay_error_message_id'] = error_msg.message_id
        return ConversationState.WAITING_DELAY


async def start_pump_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle START button"""
    query = update.callback_query
    telegram_id = update.effective_user.id
    
    try:
        session = session_storage.get(telegram_id)
        if not session:
            await query.answer("❌ Session not found. Please start over with /start", show_alert=True)
            return ConversationState.WAITING_TOKEN_CA
        
        if not session.pump_amount_wei or float(session.pump_amount_wei) <= 0:
            await query.answer("⚠️ Please configure Pump Amount first!", show_alert=True)
            return ConversationState.WAITING_TOKEN_CA
        
        if not session.swap_amount_wei or float(session.swap_amount_wei) <= 0:
            await query.answer("⚠️ Please configure Swap Amount first!", show_alert=True)
            return ConversationState.WAITING_TOKEN_CA
        
        await query.answer("🚀 Starting pump session...")
        
        result = await api.start_session(
            telegram_id=telegram_id,
            token_ca=session.token_ca,
            pump_amount_wei=session.pump_amount_wei,
            swap_amount_wei=session.swap_amount_wei
        )
        
        session.backend_started = True
        
        import main
        if telegram_id in main.notified_completions:
            main.notified_completions.remove(telegram_id)
        
        await _update_config_menu(
            context, 
            telegram_id, 
            "🚀 Pump session started successfully!"
        )
        
        return ConversationState.WAITING_TOKEN_CA
        
    except Exception as e:
        logger.error(f"Error starting pump: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)
        return ConversationState.WAITING_TOKEN_CA


async def pause_pump_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Pause button"""
    query = update.callback_query
    telegram_id = update.effective_user.id
    
    await query.answer("⏸ Pausing pump session...")
    
    try:
        result = await api.pause_session(telegram_id)
        
        session = session_storage.get(telegram_id)
        if session:
            session.is_paused = True
        
        await _update_config_menu(
            context, 
            telegram_id, 
            "⏸ Pump session paused"
        )
        
    except Exception as e:
        logger.error(f"Error pausing pump: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)


async def resume_pump_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Resume button"""
    query = update.callback_query
    telegram_id = update.effective_user.id
    
    await query.answer("▶️ Resuming pump session...")
    
    try:
        result = await api.resume_session(telegram_id)
        
        session = session_storage.get(telegram_id)
        if session:
            session.is_paused = False
        
        await _update_config_menu(
            context, 
            telegram_id, 
            "▶️ Pump session resumed"
        )
        
    except Exception as e:
        logger.error(f"Error resuming pump: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)
