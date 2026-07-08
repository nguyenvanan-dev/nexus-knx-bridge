"""
NotificationService — Gửi thông báo từ hệ thống tới user (Telegram/Zalo/Email).
"""
import logging
import asyncio
import os
import aiohttp
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.event_bus import EventBus, DomainEvent

logger = logging.getLogger(__name__)

class NotificationEngine:
    def __init__(self, event_bus: "EventBus"):
        self._bus = event_bus
        self.telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        self.zalo_webhook_url = os.environ.get("ZALO_WEBHOOK_URL")

    def register(self):
        from core.event_bus import EventType
        self._bus.subscribe(EventType.NOTIFICATION_REQUEST, self._handle_notification_request)
        logger.info("NotificationEngine: registered with EventBus")

    async def _handle_notification_request(self, event: "DomainEvent"):
        p = event.payload
        title = p.get("title", "Thông báo")
        message = p.get("message", "")
        channel = p.get("channel", "telegram")
        await self.send_notification(title, message, channel)

    async def send_notification(self, title: str, message: str, channel: str = "telegram"):
        """Gửi thông báo qua kênh chỉ định."""
        full_msg = f"*{title}*\n{message}"
        
        logger.info(f"Notification [{channel}]: {title} - {message}")
        
        if channel == "telegram":
            await self._send_telegram(full_msg)
        elif channel == "zalo":
            await self._send_zalo(full_msg)
        else:
            logger.warning(f"Unsupported notification channel: {channel}")

    async def _send_telegram(self, message: str):
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logger.debug("Telegram credentials not configured, skipping actual send.")
            return

        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=5) as resp:
                    if resp.status != 200:
                        logger.error(f"Telegram send failed: {resp.status} {await resp.text()}")
        except Exception as e:
            logger.error(f"Telegram send exception: {e}")

    async def _send_zalo(self, message: str):
        if not self.zalo_webhook_url:
            logger.debug("Zalo webhook not configured, skipping actual send.")
            return
            
        payload = {"message": message}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.zalo_webhook_url, json=payload, timeout=5) as resp:
                    if resp.status != 200:
                        logger.error(f"Zalo send failed: {resp.status}")
        except Exception as e:
            logger.error(f"Zalo send exception: {e}")
