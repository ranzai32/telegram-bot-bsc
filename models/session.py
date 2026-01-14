"""User session model"""

from dataclasses import dataclass


@dataclass
class UserSession:
    """Temporary storage for user data during session setup"""
    token_ca: str = ""
    pump_amount_wei: str = ""
    swap_amount_wei: str = ""
    delay_millis: int = 1000
    backend_started: bool = False  # track if session was started on backend
    is_paused: bool = False  # track if session is currently paused


class SessionStorage:
    """Thread-safe storage for user sessions"""
    
    def __init__(self):
        self._sessions: dict[int, UserSession] = {}
    
    def get(self, telegram_id: int) -> UserSession | None:
        """Get user session by telegram ID"""
        return self._sessions.get(telegram_id)
    
    def create(self, telegram_id: int) -> UserSession:
        """Create new user session"""
        session = UserSession()
        self._sessions[telegram_id] = session
        return session
    
    def delete(self, telegram_id: int) -> None:
        """Delete user session"""
        if telegram_id in self._sessions:
            del self._sessions[telegram_id]
    
    def exists(self, telegram_id: int) -> bool:
        """Check if user session exists"""
        return telegram_id in self._sessions

session_storage = SessionStorage()
