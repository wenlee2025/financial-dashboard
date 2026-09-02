import logging
import requests
from typing import Optional
from .base import BaseNotifier

logger = logging.getLogger(__name__)

class DiscordNotifier(BaseNotifier):
    """Discord Webhook 推播發送器"""

    def __init__(self, webhook_url: Optional[str], username: str = "每日財經儀表板"):
        self.webhook_url = webhook_url
        self.username = username
        self.session = requests.Session()

    @property
    def name(self) -> str:
        return "discord"

    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url and self.webhook_url.startswith("http"))

    def send(self, title: str, markdown_content: str, html_content: Optional[str] = None) -> bool:
        return self.send_message(markdown_content)

    def send_message(self, message: str) -> bool:
        if not self.is_configured:
            return False

        # Discord 單條訊息上限為 2000 字元
        if len(message) > 1950:
            message = message[:1950] + "\n...(訊息已截斷，請開啟完整儀表板查看)"

        payload = {
            "username": self.username,
            "content": message
        }

        try:
            resp = self.session.post(self.webhook_url, json=payload, timeout=10)
            if resp.status_code in (200, 204):
                logger.info("Discord Webhook 推播成功")
                return True
            else:
                logger.warning(f"Discord 推播失敗 ({resp.status_code}): {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Discord 推播例外: {e}")
            return False
