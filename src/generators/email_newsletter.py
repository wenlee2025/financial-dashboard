import logging
from pathlib import Path
from typing import Any, Dict
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

class EmailNewsletterGenerator:
    """HTML 電子報內容產生器"""

    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
        self.env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)

    def generate(self, context: Dict[str, Any]) -> str:
        """渲染 HTML Email 內容"""
        try:
            template = self.env.get_template("email_template.html")
            return template.render(**context)
        except Exception as e:
            logger.error(f"渲染 Email HTML 失敗: {e}")
            return f"<html><body><h2>{context.get('page_title')}</h2><p>{context.get('ai_analysis', {}).get('executive_summary')}</p></body></html>"
