import logging
import requests
from typing import Optional
from .base import BaseNotifier

logger = logging.getLogger(__name__)

class TelegramNotifier(BaseNotifier):
    """Telegram Bot 推播發送器"""

    def __init__(self, bot_token: Optional[str], chat_id: Optional[str]):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.session = requests.Session()

    @property
    def name(self) -> str:
        return "telegram"

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send(self, title: str, markdown_content: str, html_content: Optional[str] = None) -> bool:
        return self.send_message(markdown_content)

    def send_message(self, message: str) -> bool:
        if not self.is_configured:
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        }

        try:
            resp = self.session.post(url, json=payload, timeout=10)
            if resp.status_code == 200 and resp.json().get("ok"):
                logger.info("Telegram 訊息推播成功")
                return True
            else:
                logger.warning(f"Telegram 推播失敗 ({resp.status_code}): {resp.text}")
                # 若 Markdown 格式錯誤，降級為純文字發送
                payload.pop("parse_mode", None)
                retry_resp = self.session.post(url, json=payload, timeout=10)
                return retry_resp.status_code == 200
        except Exception as e:
            logger.error(f"Telegram 推播例外: {e}")
            return False
