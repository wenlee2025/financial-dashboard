import logging
from typing import Any, Dict, List
from .base import BaseNotifier
from .telegram import TelegramNotifier
from .discord import DiscordNotifier
from .line import LineNotifier
from .slack import SlackNotifier
from .smtp_email import SMTPEmailNotifier

logger = logging.getLogger(__name__)

class NotificationDispatcher:
    """多通道推播統一調度器 (多型插件架構)"""

    def __init__(
        self,
        telegram_token: str = None,
        telegram_chat_id: str = None,
        discord_webhook: str = None,
        line_token: str = None,
        line_user_id: str = None,
        slack_webhook: str = None,
        smtp_config: Dict[str, Any] = None
    ):
        self.telegram = TelegramNotifier(telegram_token, telegram_chat_id)
        self.discord = DiscordNotifier(discord_webhook)
        self.line = LineNotifier(line_token, line_user_id)
        self.slack = SlackNotifier(slack_webhook)
        self.email = SMTPEmailNotifier(smtp_config or {})

        # 註冊所有通道適配器
        self.notifiers: List[BaseNotifier] = [
            self.telegram,
            self.discord,
            self.line,
            self.slack,
            self.email
        ]

    def dispatch_all(
        self,
        markdown_summary: str,
        email_html: str,
        subject: str
    ) -> Dict[str, bool]:
        """
        多型廣播日報至所有已啟用之通訊通道
        """
        results = {}
        for notifier in self.notifiers:
            if notifier.is_configured:
                success = notifier.send(
                    title=subject,
                    markdown_content=markdown_summary,
                    html_content=email_html
                )
                results[notifier.name] = success
            else:
                logger.debug(f"{notifier.name.capitalize()} 未設定，略過推播")

        active_count = len(results)
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"多通道推播完成: 共啟用 {active_count} 個通道，成功發送 {success_count} 個")

        return results
