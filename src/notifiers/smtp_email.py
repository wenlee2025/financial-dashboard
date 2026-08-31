import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class SMTPEmailNotifier:
    """標準 SMTP 電子郵件日報發送器"""

    def __init__(self, smtp_config: Dict[str, Any]):
        self.server = smtp_config.get("server")
        self.port = int(smtp_config.get("port", 587))
        self.user = smtp_config.get("user")
        self.password = smtp_config.get("password")
        self.recipients: List[str] = smtp_config.get("to", [])
        self.sender = smtp_config.get("from") or self.user

    @property
    def is_configured(self) -> bool:
        return bool(self.server and self.user and self.password and self.recipients)

    def send_email(self, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        if not self.is_configured:
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.sender
            msg["To"] = ", ".join(self.recipients)

            if text_content:
                msg.attach(MIMEText(text_content, "plain", "utf-8"))
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            if self.port == 465:
                # SSL 連線
                with smtplib.SMTP_SSL(self.server, self.port, timeout=15) as server:
                    server.login(self.user, self.password)
                    server.sendmail(self.sender, self.recipients, msg.as_string())
            else:
                # STARTTLS 連線 (如 Gmail port 587)
                with smtplib.SMTP(self.server, self.port, timeout=15) as server:
                    server.starttls()
                    server.login(self.user, self.password)
                    server.sendmail(self.sender, self.recipients, msg.as_string())

            logger.info(f"成功發送日報 Email 至 {len(self.recipients)} 位收件者")
            return True
        except Exception as e:
            logger.error(f"SMTP 電子郵件發送失敗: {e}")
            return False
