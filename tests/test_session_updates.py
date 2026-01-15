"""
Tests for session updates during active session
Testing swap_amount and delay updates while session is:
- Not started
- Running (InProcess)
- Paused
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from decimal import Decimal

# Mock telegram imports
import sys
sys.modules['telegram'] = MagicMock()
sys.modules['telegram.ext'] = MagicMock()

from handlers.session import receive_swap_amount, receive_delay
from models.session import UserSession, SessionStorage
from states import ConversationState


@pytest.fixture
def session_storage():
    """Create fresh session storage for each test"""
    storage = SessionStorage()
    return storage


@pytest.fixture
def mock_update():
    """Mock telegram Update object"""
    update = Mock()
    update.effective_user = Mock()
    update.effective_user.id = 123456
    update.effective_chat = Mock()
    update.effective_chat.id = 123456
    update.message = Mock()
    # Need to make text.strip() return a string
    update.message.text = Mock()
    update.message.text.strip = Mock(return_value="0.05")
    update.message.reply_text = AsyncMock()
    update.message.delete = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Mock telegram Context object"""
    context = Mock()
    context.user_data = {}
    context.bot.delete_message = AsyncMock()
    return context


class TestSwapAmountUpdate:
    """Test swap amount updates in different session states"""
    
    @pytest.mark.asyncio
    @patch('handlers.session.bnb_to_wei')
    @patch('handlers.session.api')
    @patch('handlers.session.session_storage')
    @patch('handlers.session._update_config_menu')
    async def test_swap_amount_before_session_start(
        self, 
        mock_update_menu, 
        mock_storage, 
        mock_api,
        mock_bnb_to_wei,
        mock_update,
        mock_context,
        caplog
    ):
        """Test: Swap amount update works BEFORE session starts"""
        # Arrange
        telegram_id = 123456
        session = UserSession()
        session.token_ca = "0x123"
        session.backend_started = False  # Session NOT started
        
        mock_storage.get.return_value = session
        mock_api.check_wallet_balance = AsyncMock(return_value={"ui": "1.0"})
        mock_api.bnb_to_usd = AsyncMock(return_value={"amount_usd": "25.0"})
        mock_api.set_session_swap_amount = AsyncMock()
        mock_bnb_to_wei.return_value = "50000000000000000"
        
        # Act
        result = await receive_swap_amount(mock_update, mock_context)
        
        # Print logs for debugging
        print("LOGS:", caplog.text)
        print("Result:", result)
        
        # Assert
        assert result == ConversationState.WAITING_TOKEN_CA
        assert session.swap_amount_wei == "50000000000000000"  # 0.05 BNB in wei
        # Should NOT call backend API (session not started)
        mock_api.set_session_swap_amount.assert_not_called()
        mock_update_menu.assert_called_once()


    @pytest.mark.asyncio
    @patch('handlers.session.bnb_to_wei')
    @patch('handlers.session.api')
    @patch('handlers.session.session_storage')
    @patch('handlers.session._update_config_menu')
    async def test_swap_amount_during_active_session(
        self, 
        mock_update_menu, 
        mock_storage, 
        mock_api,
        mock_bnb_to_wei,
        mock_update,
        mock_context
    ):
        """Test: Swap amount update works DURING active session"""
        # Arrange
        telegram_id = 123456
        session = UserSession()
        session.token_ca = "0x123"
        session.backend_started = True  # Session IS RUNNING
        session.is_paused = False
        
        mock_storage.get.return_value = session
        mock_api.check_wallet_balance = AsyncMock(return_value={"ui": "1.0"})
        mock_api.bnb_to_usd = AsyncMock(return_value={"amount_usd": "25.0"})
        mock_api.set_session_swap_amount = AsyncMock()
        mock_bnb_to_wei.return_value = "50000000000000000"
        
        # Act
        result = await receive_swap_amount(mock_update, mock_context)
        
        # Assert
        assert result == ConversationState.WAITING_TOKEN_CA
        assert session.swap_amount_wei == "50000000000000000"
        # Should CALL backend API (session is running)
        mock_api.set_session_swap_amount.assert_called_once_with(
            telegram_id, 
            "50000000000000000"
        )
        mock_update_menu.assert_called_once()


    @pytest.mark.asyncio
    @patch('handlers.session.bnb_to_wei')
    @patch('handlers.session.api')
    @patch('handlers.session.session_storage')
    @patch('handlers.session._update_config_menu')
    async def test_swap_amount_during_paused_session(
        self, 
        mock_update_menu, 
        mock_storage, 
        mock_api,
        mock_bnb_to_wei,
        mock_update,
        mock_context
    ):
        """Test: Swap amount update works DURING paused session"""
        # Arrange
        telegram_id = 123456
        session = UserSession()
        session.token_ca = "0x123"
        session.backend_started = True  # Session started
        session.is_paused = True  # But PAUSED
        
        mock_storage.get.return_value = session
        mock_api.check_wallet_balance = AsyncMock(return_value={"ui": "1.0"})
        mock_api.bnb_to_usd = AsyncMock(return_value={"amount_usd": "25.0"})
        mock_api.set_session_swap_amount = AsyncMock()
        mock_bnb_to_wei.return_value = "50000000000000000"
        
        # Act
        result = await receive_swap_amount(mock_update, mock_context)
        
        # Assert
        assert result == ConversationState.WAITING_TOKEN_CA
        assert session.swap_amount_wei == "50000000000000000"
        # Should STILL call backend API (even when paused)
        mock_api.set_session_swap_amount.assert_called_once_with(
            telegram_id, 
            "50000000000000000"
        )
        mock_update_menu.assert_called_once()


    @pytest.mark.asyncio
    @patch('handlers.session.api')
    @patch('handlers.session.session_storage')
    async def test_swap_amount_exceeds_50_percent(
        self, 
        mock_storage, 
        mock_api,
        mock_update,
        mock_context
    ):
        """Test: Swap amount validation - cannot exceed 50% of balance"""
        # Arrange
        telegram_id = 123456
        session = UserSession()
        session.token_ca = "0x123"
        
        mock_update.message.text.strip.return_value = "0.6"  # 60% of 1.0 BNB
        mock_storage.get.return_value = session
        mock_api.check_wallet_balance = AsyncMock(return_value={"ui": "1.0"})
        
        # Act
        result = await receive_swap_amount(mock_update, mock_context)
        
        # Assert
        assert result == ConversationState.WAITING_SWAP_AMOUNT
        # Should show error message
        mock_update.message.reply_text.assert_called()
        error_call = mock_update.message.reply_text.call_args[0][0]
        assert "cannot exceed 50%" in error_call.lower()


class TestDelayUpdate:
    """Test delay updates in different session states"""
    
    @pytest.mark.asyncio
    @patch('handlers.session.api')
    @patch('handlers.session.session_storage')
    @patch('handlers.session._update_config_menu')
    async def test_delay_before_session_start(
        self, 
        mock_update_menu, 
        mock_storage, 
        mock_api,
        mock_update,
        mock_context
    ):
        """Test: Delay update works BEFORE session starts"""
        # Arrange
        telegram_id = 123456
        session = UserSession()
        session.token_ca = "0x123"
        session.backend_started = False
        
        mock_update.message.text.strip.return_value = "2.5"  # 2.5 seconds
        mock_storage.get.return_value = session
        mock_api.set_session_delay = AsyncMock()
        
        # Act
        result = await receive_delay(mock_update, mock_context)
        
        # Assert
        assert result == ConversationState.WAITING_TOKEN_CA
        assert session.delay_millis == 2500  # 2.5 seconds = 2500ms
        # Should NOT call backend API (session not started)
        mock_api.set_session_delay.assert_not_called()
        mock_update_menu.assert_called_once()


    @pytest.mark.asyncio
    @patch('handlers.session.api')
    @patch('handlers.session.session_storage')
    @patch('handlers.session._update_config_menu')
    async def test_delay_during_active_session(
        self, 
        mock_update_menu, 
        mock_storage, 
        mock_api,
        mock_update,
        mock_context
    ):
        """Test: Delay update works DURING active session"""
        # Arrange
        telegram_id = 123456
        session = UserSession()
        session.token_ca = "0x123"
        session.backend_started = True  # Session IS RUNNING
        session.is_paused = False
        
        mock_update.message.text.strip.return_value = "1.5"
        mock_storage.get.return_value = session
        mock_api.set_session_delay = AsyncMock()
        
        # Act
        result = await receive_delay(mock_update, mock_context)
        
        # Assert
        assert result == ConversationState.WAITING_TOKEN_CA
        assert session.delay_millis == 1500
        # Should CALL backend API (session is running)
        mock_api.set_session_delay.assert_called_once_with(telegram_id, 1500)
        mock_update_menu.assert_called_once()


    @pytest.mark.asyncio
    @patch('handlers.session.api')
    @patch('handlers.session.session_storage')
    @patch('handlers.session._update_config_menu')
    async def test_delay_during_paused_session(
        self, 
        mock_update_menu, 
        mock_storage, 
        mock_api,
        mock_update,
        mock_context
    ):
        """Test: Delay update works DURING paused session"""
        # Arrange
        telegram_id = 123456
        session = UserSession()
        session.token_ca = "0x123"
        session.backend_started = True
        session.is_paused = True  # PAUSED
        
        mock_update.message.text.strip.return_value = "0.8"
        mock_storage.get.return_value = session
        mock_api.set_session_delay = AsyncMock()
        
        # Act
        result = await receive_delay(mock_update, mock_context)
        
        # Assert
        assert result == ConversationState.WAITING_TOKEN_CA
        assert session.delay_millis == 800
        # Should STILL call backend API (even when paused)
        mock_api.set_session_delay.assert_called_once_with(telegram_id, 800)
        mock_update_menu.assert_called_once()


    @pytest.mark.asyncio
    @patch('handlers.session.session_storage')
    async def test_delay_invalid_value(
        self, 
        mock_storage,
        mock_update,
        mock_context
    ):
        """Test: Invalid delay value shows error"""
        # Arrange
        telegram_id = 123456
        session = UserSession()
        
        mock_update.message.text.strip.return_value = "invalid"
        mock_storage.get.return_value = session
        
        # Act
        result = await receive_delay(mock_update, mock_context)
        
        # Assert
        assert result == ConversationState.WAITING_DELAY
        # Should show error message
        mock_update.message.reply_text.assert_called()
        error_call = mock_update.message.reply_text.call_args[0][0]
        assert "invalid format" in error_call.lower()
