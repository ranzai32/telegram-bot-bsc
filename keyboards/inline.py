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


def get_pump_config_keyboard(session_status: str = "Not Started", pump_configured: bool = False, swap_configured: bool = False) -> InlineKeyboardMarkup:
    """Get keyboard for pump configuration with amount buttons and start/pause/resume"""
    # First row - configuration buttons
    first_row = [
        InlineKeyboardButton("💱 Swap Amount", callback_data="set_swap_amount"),
        InlineKeyboardButton("⏱️ Set Delay", callback_data="set_delay")
    ]
    
    # Add Pump Amount button only if session is not running
    if session_status != "InProcess":
        first_row.insert(0, InlineKeyboardButton("💰 Pump Amount", callback_data="set_pump_amount"))
    
    # Second row - action buttons
    second_row = []
    
    if session_status == "InProcess":
        # Session is running - show START (disabled) and Pause
        second_row = [
            InlineKeyboardButton("🚀 START", callback_data="start_pump"),
            InlineKeyboardButton("⏸ Pause", callback_data="pause_pump")
        ]
    elif session_status == "Paused":
        # Session is paused - show Resume button
        second_row = [
            InlineKeyboardButton("▶️ Resume", callback_data="resume_pump")
        ]
    elif session_status in ["Success", "Error"] or (isinstance(session_status, dict) and ("Success" in session_status or "Error" in session_status)):
        # Session stopped/completed - show Resume
        second_row = [
            InlineKeyboardButton("▶️ Resume", callback_data="resume_pump"),
        ]
    else:
        # Not started - show START (disabled if not configured) and Pause
        if pump_configured and swap_configured:
            start_button = InlineKeyboardButton("🚀 START", callback_data="start_pump")
        else:
            start_button = InlineKeyboardButton("❌ Not Ready", callback_data="start_pump")
        
        second_row = [
            start_button,
            InlineKeyboardButton("⏸ Pause", callback_data="pause_pump")
        ]
    
    keyboard = [first_row, second_row]
    return InlineKeyboardMarkup(keyboard)
