import httpx
from typing import Optional, Dict, Any
from config import settings
import logging

logger = logging.getLogger(__name__)


class BackendAPI:
    """Client for interacting with Rust backend API"""
    
    def __init__(self):
        self.base_url = settings.api_base_url
        # Increase timeout and add retries
        self.client = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
    
    async def close(self):
        await self.client.aclose()
    
    # User endpoints
    async def get_or_create_wallet(self, telegram_id: int) -> Dict[str, Any]:
        """Get or create user wallet"""
        url = f"{self.base_url}/user/{telegram_id}/wallet"
        logger.info(f"GET {url}")
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()
    
    async def check_wallet_balance(self, telegram_id: int) -> Dict[str, Any]:
        """Check wallet balance"""
        url = f"{self.base_url}/user/{telegram_id}/wallet/balance"
        logger.info(f"GET {url}")
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()
    
    # Token endpoints
    async def check_token_supported(self, token_ca: str) -> Dict[str, Any]:
        """Check if token is supported"""
        response = await self.client.get(f"{self.base_url}/token/{token_ca}/is-supported")
        response.raise_for_status()
        return response.json()
    
    async def get_token_pools(self, token_ca: str) -> Dict[str, Any]:
        """Get liquidity pools for token"""
        response = await self.client.get(f"{self.base_url}/token/{token_ca}/pools")
        response.raise_for_status()
        return response.json()
    
    # Bot session endpoints
    async def start_session(
        self,
        telegram_id: int,
        token_ca: str,
        pump_amount_wei: str,
        swap_amount_wei: str,
        delay_millis: int = 1000
    ) -> Dict[str, Any]:
        """Start pump session. Idempotent - returns created: false if session already exists."""
        payload = {
            "user_telegram_id": telegram_id,
            "token_ca": token_ca,
            "pump_amount_wei": pump_amount_wei,
            "swap_amount_wei": swap_amount_wei,
            "delay_millis": delay_millis
        }
        response = await self.client.post(f"{self.base_url}/bot/session/run", json=payload)
        response.raise_for_status()
        return response.json()
    
    async def get_session_status(self, telegram_id: int) -> Dict[str, Any]:
        """Get session status. Used for long-polling."""
        # Backend uses GET but accepts JSON body (non-standard but works)
        payload = {"user_telegram_id": telegram_id}
        response = await self.client.request(
            "GET",
            f"{self.base_url}/bot/session/status",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def pause_session(self, telegram_id: int) -> None:
        """Pause running session"""
        payload = {"user_telegram_id": telegram_id}
        response = await self.client.post(f"{self.base_url}/bot/session/pause", json=payload)
        response.raise_for_status()
    
    async def resume_session(self, telegram_id: int) -> None:
        """Resume paused session"""
        payload = {"user_telegram_id": telegram_id}
        response = await self.client.post(f"{self.base_url}/bot/session/resume", json=payload)
        response.raise_for_status()
    
    async def set_session_delay(self, telegram_id: int, delay_millis: int) -> None:
        """Update delay between swaps in running session"""
        payload = {
            "user_telegram_id": telegram_id,
            "delay_millis": delay_millis
        }
        response = await self.client.put(f"{self.base_url}/bot/session/delay", json=payload)
        response.raise_for_status()
    
    async def set_session_swap_amount(self, telegram_id: int, swap_amount_wei: str) -> None:
        """Update swap amount in running session"""
        payload = {
            "user_telegram_id": telegram_id,
            "swap_amount_wei": swap_amount_wei
        }
        response = await self.client.put(f"{self.base_url}/bot/session/swap-amount", json=payload)
        response.raise_for_status()
    
    # Price endpoints
    async def bnb_to_usd(self, amount_wei: str) -> Dict[str, Any]:
        """Convert BNB to USD"""
        payload = {"amount_wei": amount_wei}
        response = await self.client.post(f"{self.base_url}/price/bnb-to-usd", json=payload)
        response.raise_for_status()
        return response.json()


# Global API client instance
api = BackendAPI()
