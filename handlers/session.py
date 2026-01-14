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
from utils import bnb_to_wei

logger = logging.getLogger(__name__)

# Path to welcome image
WELCOME_IMAGE_PATH = Path(__file__).parent.parent / "assets" / "welcome.jpg"


async def _update_config_menu(context: ContextTypes.DEFAULT_TYPE, telegram_id: int, confirmation_text: str = None):
    """Helper function to update configuration menu"""
    session = session_storage.get(telegram_id)
    if not session or not session.token_ca:
        return None
    
    token_ca = session.token_ca
    
    # Get session status
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
        status_text = "⚪️ Not Started"
    
    # Get balance
    try:
        balance_data = await api.check_wallet_balance(telegram_id)
        balance_bnb = f"{float(balance_data['ui']):.4f}"
    except:
        balance_bnb = "N/A"
    
    # Get current amounts
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
    
    # Create dexscreener link
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
    
    # Get saved message_id to update it
    message_id = context.user_data.get('config_message_id')
    chat_id = context.user_data.get('config_chat_id')
    
    if message_id and chat_id:
        # Update existing message
        await context.bot.edit_message_text(
            text=config_text,
            chat_id=chat_id,
            message_id=message_id,
            parse_mode='Markdown',
            reply_markup=get_pump_config_keyboard(),
            disable_web_page_preview=True
        )
    
    return config_text


async def receive_token_ca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receiving token contract address"""
    telegram_id = update.effective_user.id
    token_ca = update.message.text.strip()
    
    await update.message.reply_text("🔍 Checking token...")
    
    try:
        # Check if token is supported
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
        
        # Get pools information
        pools_data = await api.get_token_pools(token_ca)
        # Backend returns {"pools": {"pairs": [...]}} but pairs is a list
        pools = pools_data.get("pools", {})
        if isinstance(pools, dict):
            pools_count = len(pools.get("pairs", []))
        else:
            # If pools is already a list
            pools_count = len(pools) if isinstance(pools, list) else 0
        
        # Save contract address
        session = session_storage.get(telegram_id)
        if session:
            session.token_ca = token_ca
        
        # Get session status
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
            status_text = "⚪️ Not Started"
        
        # Get current balance
        try:
            balance_data = await api.check_wallet_balance(telegram_id)
            balance_bnb = f"{float(balance_data['ui']):.4f}"
        except:
            balance_bnb = "N/A"
        
        # Get current amounts from session or show as not configured
        pump_amount_bnb = "0.0"
        pump_indicator = "🔴"  # red = not configured
        swap_amount_bnb = "0.0"
        swap_indicator = "🔴"
        delay_seconds = "1.0"  # default
        delay_indicator = "🔴"
        
        if session:
            if session.pump_amount_wei and float(session.pump_amount_wei) > 0:
                pump_amount_bnb = f"{float(session.pump_amount_wei) / 1e18:.4f}"
                pump_indicator = "🟢"  # green = configured
            if session.swap_amount_wei and float(session.swap_amount_wei) > 0:
                swap_amount_bnb = f"{float(session.swap_amount_wei) / 1e18:.4f}"
                swap_indicator = "🟢"
            if hasattr(session, 'delay_millis') and session.delay_millis:
                delay_seconds = f"{session.delay_millis / 1000:.1f}"
                delay_indicator = "🟢"
        
        from keyboards.inline import get_pump_config_keyboard
        
        # Create dexscreener link
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
            reply_markup=get_pump_config_keyboard(),
            disable_web_page_preview=True
        )
        
        # Save message_id for later updates
        context.user_data['config_message_id'] = config_message.message_id
        context.user_data['config_chat_id'] = config_message.chat_id
        
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
    
    try:
        pump_amount_bnb = Decimal(update.message.text.strip())
        
        if pump_amount_bnb <= 0:
            await update.message.reply_text("❌ Amount must be greater than 0. Try again:")
            return ConversationState.WAITING_PUMP_AMOUNT
        
        # Delete user input message
        try:
            await update.message.delete()
        except:
            pass
        
        # Convert BNB to Wei
        pump_amount_wei = bnb_to_wei(pump_amount_bnb)
        
        # Convert to USD for display
        usd_data = await api.bnb_to_usd(pump_amount_wei)
        pump_amount_usd = usd_data["amount_usd"]
        
        # Save amount
        session = session_storage.get(telegram_id)
        if session:
            session.pump_amount_wei = pump_amount_wei
        
        # Update config menu
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
    
    try:
        swap_amount_bnb = Decimal(update.message.text.strip())
        
        if swap_amount_bnb <= 0:
            await update.message.reply_text("❌ Amount must be greater than 0. Try again:")
            return ConversationState.WAITING_SWAP_AMOUNT
        
        # Delete user input message
        try:
            await update.message.delete()
        except:
            pass
        
        # Convert BNB to Wei
        swap_amount_wei = bnb_to_wei(swap_amount_bnb)
        
        # Convert to USD for display
        usd_data = await api.bnb_to_usd(swap_amount_wei)
        swap_amount_usd = usd_data["amount_usd"]
        
        # Save amount
        session = session_storage.get(telegram_id)
        if not session:
            await update.message.reply_text("❌ Session expired. Start over with /start")
            return ConversationHandler.END
        
        session.swap_amount_wei = swap_amount_wei
        
        # Update config menu
        await _update_config_menu(
            context, 
            telegram_id, 
            f"Swap amount set to {swap_amount_bnb} BNB (≈${swap_amount_usd:.2f})"
        )
        
        return ConversationState.WAITING_TOKEN_CA
        
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid format. Enter a number (e.g. 0.01):"
        )
        return ConversationState.WAITING_SWAP_AMOUNT
    except Exception as e:
        logger.error(f"Error processing swap amount: {e}")
        await update.message.reply_text(
            f"❌ Error: {str(e)}\nTry again:"
        )
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
        # Start session
        result = await api.start_session(
            telegram_id=telegram_id,
            token_ca=session.token_ca,
            pump_amount_wei=session.pump_amount_wei,
            swap_amount_wei=session.swap_amount_wei,
            delay_millis=session.delay_millis
        )
        
        if result.get("created", False):
            # Get current status and balance
            try:
                status_data = await api.get_session_status(telegram_id)
                status = status_data.get("status", "InProcess")
                
                balance_data = await api.check_wallet_balance(telegram_id)
                balance_ui = balance_data["ui"]
                balance_formatted = f"{float(balance_ui):.3f}"
            except:
                status = "InProcess"
                balance_formatted = "N/A"
            
            # Format status for display
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
        
        # Clear session
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
        # Get wallet info
        wallet_data = await api.get_or_create_wallet(telegram_id)
        wallet_address = wallet_data["wallet_dto"]["evm_address"]
        
        # Check balance
        balance_data = await api.check_wallet_balance(telegram_id)
        balance_ui = balance_data["ui"]
        
        # Format balance to max 3 decimal places
        try:
            balance_formatted = f"{float(balance_ui):.3f}"
            balance_float = float(balance_ui)
        except:
            balance_formatted = balance_ui
            balance_float = 0.0
        
        logger.info(f"Refresh balance: {balance_float} BNB (>= 0.097: {balance_float >= 0.097})")
        
        # If balance is now sufficient, update to "Ready to start" message with photo
        if balance_float >= 0.097:
            logger.info("Balance is sufficient, switching to ready message")
            welcome_text = (
                f"💼 Your wallet: `{wallet_address}`\n"
                f"💰 Current balance: {balance_formatted} BNB\n\n"
                f"🚀 Ready to start!\n"
                f"Send me the token contract address (CA) to begin pumping.\n\n"
                f"Example: `0x718447E29B90D00461966D01E533Fa1b69574444`"
            )
            
            # Replace message with photo and no button
            if WELCOME_IMAGE_PATH.exists():
                logger.info("Deleting old message and sending new one with photo")
                # Delete old message
                await query.message.delete()
                # Send new message with photo
                with open(WELCOME_IMAGE_PATH, 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=telegram_id,
                        photo=photo,
                        caption=welcome_text,
                        parse_mode='Markdown'
                    )
            else:
                logger.info("Photo not found, editing message text")
                # If message has photo (caption), need to delete and resend as text
                try:
                    await query.message.delete()
                    await context.bot.send_message(
                        chat_id=telegram_id,
                        text=welcome_text,
                        parse_mode='Markdown'
                    )
                except:
                    # Fallback to edit if delete fails
                    await query.edit_message_text(
                        welcome_text,
                        parse_mode='Markdown'
                    )
        else:
            # Balance still insufficient, just update the balance amount
            from keyboards.inline import get_refresh_keyboard
            from telegram.error import BadRequest
            
            welcome_text = (
                f"⚡️Save 30% vs others while keeping your chart fully organic — from just 0.1BNB!\n\n"
                f"— 🌿Organic & randomized: Unique wallets, random buy/sell and timing — no bot-look, no spam\n\n"
                f"— 🛠Manage it your way: Run with battle-tested defaults or customize your own settings — your chart, your rules\n\n"
                f"🎁 Free Microbots and Bumps included\n\n"
                f"➔ Deposit to this address to start:\n"
                f"`{wallet_address}`\n\n"
                f"💰 Current balance: {balance_formatted} BNB\n"
                f"⚠️ Minimum required: 0.097 BNB"
            )
            
            try:
                await query.edit_message_caption(
                    caption=welcome_text,
                    parse_mode='Markdown',
                    reply_markup=get_refresh_keyboard()
                )
            except BadRequest as e:
                # If message is not modified (same content), just ignore
                if "not modified" in str(e).lower():
                    pass
                else:
                    raise
            
    except Exception as e:
        logger.error(f"Error refreshing balance: {e}")
        # Don't try to edit message text if it's a photo message
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)


async def refresh_session_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Refresh Session Status button press"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    
    try:
        from telegram.error import BadRequest
        
        # Get session status
        status_data = await api.get_session_status(telegram_id)
        status = status_data.get("status", "Unknown")
        
        # Get wallet balance
        balance_data = await api.check_wallet_balance(telegram_id)
        balance_ui = balance_data["ui"]
        balance_formatted = f"{float(balance_ui):.3f}"
        
        # Format status for display
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
            # If message is not modified (same content), just ignore
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
            # If can't edit message, show alert instead
            await query.answer(f"❌ Error: {str(e)}", show_alert=True)


async def set_pump_amount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Pump Amount button"""
    query = update.callback_query
    await query.answer()
    
    # Save message_id to update it later
    context.user_data['config_message_id'] = query.message.message_id
    context.user_data['config_chat_id'] = query.message.chat_id
    
    await query.edit_message_text(
        "💰 **Set Pump Amount**\n\n"
        "Enter the total amount in BNB for pumping.\n"
        "Example: 0.1\n\n"
        "This amount will be split across subwallets for volume distribution.",
        parse_mode='Markdown'
    )
    
    return ConversationState.WAITING_PUMP_AMOUNT


async def set_swap_amount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Swap Amount button"""
    query = update.callback_query
    await query.answer()
    
    # Save message_id to update it later
    context.user_data['config_message_id'] = query.message.message_id
    context.user_data['config_chat_id'] = query.message.chat_id
    
    await query.edit_message_text(
        "💱 **Set Swap Amount**\n\n"
        "Enter the amount in BNB for each swap operation.\n"
        "Example: 0.01\n\n"
        "This is the amount used per individual swap transaction.",
        parse_mode='Markdown'
    )
    
    return ConversationState.WAITING_SWAP_AMOUNT


async def set_delay_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Set Delay button"""
    query = update.callback_query
    await query.answer()
    
    # Save message_id to update it later
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
    
    try:
        delay_seconds = float(update.message.text.strip())
        
        if delay_seconds <= 0:
            await update.message.reply_text("❌ Delay must be greater than 0. Try again:")
            return ConversationState.WAITING_DELAY
        
        # Delete user input message
        try:
            await update.message.delete()
        except:
            pass
        
        # Convert seconds to milliseconds
        delay_millis = int(delay_seconds * 1000)
        
        # Save delay
        session = session_storage.get(telegram_id)
        if session:
            session.delay_millis = delay_millis
        
        # Update config menu
        await _update_config_menu(
            context, 
            telegram_id, 
            f"Delay set to {delay_seconds}s"
        )
        
        return ConversationState.WAITING_TOKEN_CA
        
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid format. Enter a number in seconds (e.g. 1 or 0.5):"
        )
        return ConversationState.WAITING_DELAY
    except Exception as e:
        logger.error(f"Error processing delay: {e}")
        await update.message.reply_text(
            f"❌ Error: {str(e)}\nTry again:"
        )
        return ConversationState.WAITING_DELAY


async def start_pump_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle START button"""
    query = update.callback_query
    telegram_id = update.effective_user.id
    
    await query.answer("🚀 Starting pump session...")
    
    try:
        # Get session data
        session = session_storage.get(telegram_id)
        if not session:
            await query.edit_message_text("❌ Session not found. Please start over with /start")
            return ConversationHandler.END
        
        # Start the pump session
        result = await api.start_session(
            telegram_id=telegram_id,
            token_ca=session.token_ca,
            pump_amount_wei=session.pump_amount_wei,
            swap_amount_wei=session.swap_amount_wei
        )
        
        await query.edit_message_text(
            "🚀 **Pump Session Started!**\n\n"
            f"Token: `{session.token_ca[:10]}...{session.token_ca[-8:]}`\n"
            f"Pump Amount: {float(session.pump_amount_wei)/1e18:.4f} BNB\n"
            f"Swap Amount: {float(session.swap_amount_wei)/1e18:.4f} BNB\n\n"
            "Monitor progress with /status",
            parse_mode='Markdown'
        )
        
        # Clear session after starting
        session_storage.remove(telegram_id)
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error starting pump: {e}")
        await query.edit_message_text(
            f"❌ Error starting pump session:\n{str(e)}\n\n"
            "Please try again or contact support."
        )
        return ConversationHandler.END


async def pause_pump_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Pause button"""
    query = update.callback_query
    telegram_id = update.effective_user.id
    
    await query.answer("⏸ Pausing pump session...")
    
    try:
        result = await api.pause_session(telegram_id)
        
        await query.edit_message_text(
            "⏸ **Pump Session Paused**\n\n"
            "The session has been paused.\n"
            "Use /resume to continue or /stop to end completely."
        )
        
    except Exception as e:
        logger.error(f"Error pausing pump: {e}")
        await query.edit_message_text(
            f"❌ Error pausing session:\n{str(e)}"
        )
