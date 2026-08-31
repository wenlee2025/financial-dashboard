import logging
from typing import Any, Dict, List
from .telegram import TelegramNotifier
from .discord import DiscordNotifier
from .line import LineNotifier
from .slack import SlackNotifier
from .smtp_email import SMTPEmailNotifier

logger = logging.getLogger(__name__)

class NotificationDispatcher:
    """多通道推播統一調度器"""

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

    def dispatch_all(
        self,
        markdown_summary: str,
        email_html: str,
        subject: str
    ) -> Dict[str, bool]:
        """
        將日報推播至所有已設定金鑰之通道
        """
        results = {}

        # 1. Telegram
        if self.telegram.is_configured:
            results["telegram"] = self.telegram.send_message(markdown_summary)
        else:
            logger.debug("Telegram 未設定，略過推播")

        # 2. Discord
        if self.discord.is_configured:
            results["discord"] = self.discord.send_message(markdown_summary)
        else:
            logger.debug("Discord 未設定，略過推播")

        # 3. LINE
        if self.line.is_configured:
            results["line"] = self.line.send_message(markdown_summary)
        else:
            logger.debug("LINE 未設定，略過推播")

        # 4. Slack
        if self.slack.is_configured:
            results["slack"] = self.slack.send_message(markdown_summary)
        else:
            logger.debug("Slack 未設定，略過推播")

        # 5. Email
        if self.email.is_configured:
            results["email"] = self.email.send_email(subject, email_html, markdown_summary)
        else:
            logger.debug("Email SMTP 未設定，略過郵件發送")

        active_count = len(results)
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"多通道推播完成: 共啟用 {active_count} 個通道，成功發送 {success_count} 個")

        return results
