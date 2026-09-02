from abc import ABC, abstractmethod
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class BaseNotifier(ABC):
    """推播通道適配器抽象基底 (Base Notifier Adapter)"""

    @property
    @abstractmethod
    def name(self) -> str:
        """通道識別代碼 (如 telegram, discord, line, slack, email)"""
        pass

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """是否已配置有效之金鑰或 Webhook"""
        pass

    @abstractmethod
    def send(self, title: str, markdown_content: str, html_content: Optional[str] = None) -> bool:
        """統一多型發送介面"""
        pass
