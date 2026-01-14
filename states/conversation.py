"""Conversation states for the bot"""

from enum import IntEnum


class ConversationState(IntEnum):
    """States for the session creation conversation flow"""
    WAITING_TOKEN_CA = 0
    WAITING_PUMP_AMOUNT = 1
    WAITING_SWAP_AMOUNT = 2
    WAITING_DELAY = 3
