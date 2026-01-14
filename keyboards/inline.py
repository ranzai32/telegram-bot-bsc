"""Inline keyboards for the bot"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard with START and Cancel buttons"""
    keyboard = [
        [
            InlineKeyboardButton("🚀 START", callback_data="confirm_start"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_start")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_refresh_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard with Refresh button"""
    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_balance")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_session_status_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard with Refresh button for session status"""
    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh Status", callback_data="refresh_session_status")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_pump_config_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for pump configuration with amount buttons and start/pause"""
    keyboard = [
        [
            InlineKeyboardButton("💰 Pump Amount", callback_data="set_pump_amount"),
            InlineKeyboardButton("💱 Swap Amount", callback_data="set_swap_amount"),
            InlineKeyboardButton("⏱️ Set Delay", callback_data="set_delay")
        ],
        [
            InlineKeyboardButton("🚀 START", callback_data="start_pump"),
            InlineKeyboardButton("⏸ Pause", callback_data="pause_pump")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
