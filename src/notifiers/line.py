import logging
import requests
from typing import Optional
from .base import BaseNotifier

logger = logging.getLogger(__name__)

class LineNotifier(BaseNotifier):
    """LINE Messaging API (Bot) 推播發送器"""

    def __init__(self, channel_access_token: Optional[str], user_id: Optional[str]):
        self.channel_access_token = channel_access_token
        self.user_id = user_id
        self.session = requests.Session()

    @property
    def name(self) -> str:
        return "line"

    @property
    def is_configured(self) -> bool:
        return bool(self.channel_access_token and self.user_id)

    def send(self, title: str, markdown_content: str, html_content: Optional[str] = None) -> bool:
        return self.send_message(markdown_content)

    def send_message(self, message: str) -> bool:
        if not self.is_configured:
            return False

        url = "https://api.line.me/v2/bot/message/push"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.channel_access_token}"
        }
        # LINE 限制單則文字上限 5000 字
        payload = {
            "to": self.user_id,
            "messages": [
                {
                    "type": "text",
                    "text": message[:4900]
                }
            ]
        }

        try:
            resp = self.session.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                logger.info("LINE 訊息推播成功")
                return True
            else:
                logger.warning(f"LINE 推播失敗 ({resp.status_code}): {resp.text}")
                return False
        except Exception as e:
            logger.error(f"LINE 推播例外: {e}")
            return False
