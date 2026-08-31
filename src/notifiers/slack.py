import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

class SlackNotifier:
    """Slack Incoming Webhook 推播發送器"""

    def __init__(self, webhook_url: Optional[str]):
        self.webhook_url = webhook_url
        self.session = requests.Session()

    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url and self.webhook_url.startswith("http"))

    def send_message(self, message: str) -> bool:
        if not self.is_configured:
            return False

        payload = {
            "text": message
        }

        try:
            resp = self.session.post(self.webhook_url, json=payload, timeout=10)
            if resp.status_code == 200:
                logger.info("Slack Webhook 推播成功")
                return True
            else:
                logger.warning(f"Slack 推播失敗 ({resp.status_code}): {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Slack 推播例外: {e}")
            return False
