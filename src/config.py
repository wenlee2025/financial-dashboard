import os
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

# 取得專案根目錄
BASE_DIR = Path(__file__).resolve().parent.parent

def load_yaml(file_path: Path) -> Dict[str, Any]:
    """安全載入 YAML 設定檔"""
    if not file_path.exists():
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

class Config:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or BASE_DIR
        self.config_dir = self.base_dir / "config"
        
        # 載入 YAML 設定
        self.watchlist_raw = load_yaml(self.config_dir / "watchlist.yaml")
        self.settings_raw = load_yaml(self.config_dir / "settings.yaml")
        
        # 嘗試載入 .env 檔案（如果存在）
        self._load_dotenv(self.base_dir / ".env")

    def _load_dotenv(self, env_path: Path):
        """簡易 .env 載入器（免額外套件）"""
        if not env_path.exists():
            return
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k not in os.environ:
                        os.environ[k] = v

    # ---------------- 系統與目錄路徑 ----------------
    @property
    def timezone(self) -> str:
        return self.settings_raw.get("system", {}).get("timezone", "Asia/Taipei")

    @property
    def output_dir(self) -> Path:
        rel = self.settings_raw.get("system", {}).get("output_dir", "docs")
        out_path = self.base_dir / rel
        out_path.mkdir(parents=True, exist_ok=True)
        return out_path

    @property
    def history_dir(self) -> Path:
        rel = self.settings_raw.get("system", {}).get("history_dir", "docs/history")
        hist_path = self.base_dir / rel
        hist_path.mkdir(parents=True, exist_ok=True)
        return hist_path

    @property
    def data_dir(self) -> Path:
        rel = self.settings_raw.get("system", {}).get("data_dir", "docs/data")
        data_path = self.base_dir / rel
        data_path.mkdir(parents=True, exist_ok=True)
        return data_path

    @property
    def dashboard_url(self) -> str:
        return os.environ.get("DASHBOARD_URL", "")

    # ---------------- 標的清單 ----------------
    @property
    def us_indices(self) -> List[Dict[str, str]]:
        return self.watchlist_raw.get("indices", {}).get("us", [])

    @property
    def tw_indices(self) -> List[Dict[str, str]]:
        return self.watchlist_raw.get("indices", {}).get("tw", [])

    @property
    def us_stocks(self) -> List[Dict[str, Any]]:
        return self.watchlist_raw.get("us_stocks", [])

    @property
    def tw_stocks(self) -> List[Dict[str, Any]]:
        return self.watchlist_raw.get("tw_stocks", [])

    @property
    def adr_mappings(self) -> List[Dict[str, Any]]:
        return self.watchlist_raw.get("adr_mappings", [])

    # ---------------- 量化與評分參數 ----------------
    @property
    def scoring_weights(self) -> Dict[str, float]:
        return self.settings_raw.get("scoring_weights", {
            "technicals": 0.40,
            "flows": 0.35,
            "fundamentals": 0.25
        })

    @property
    def rating_tiers(self) -> Dict[str, int]:
        return self.settings_raw.get("rating_tiers", {
            "strong_bull": 78,
            "lean_bull": 60,
            "neutral": 42,
            "lean_bear": 28,
            "strong_bear": 0
        })

    @property
    def scanner_settings(self) -> Dict[str, Any]:
        return self.settings_raw.get("scanner", {
            "enabled": True,
            "top_n_tw": 3,
            "top_n_us": 3,
            "tw_min_turnover_billion": 1.0,
            "tw_min_foreign_trust_buy_lots": 500,
            "us_min_volume_million": 2.0
        })

    # ---------------- AI / LLM API 設定 ----------------
    @property
    def ai_provider(self) -> str:
        # 若指定環境變數則優先，否則讀取 settings.yaml
        return os.environ.get("AI_PROVIDER", self.settings_raw.get("ai_engine", {}).get("provider", "gemini"))

    @property
    def gemini_api_key(self) -> Optional[str]:
        return os.environ.get("GEMINI_API_KEY")

    @property
    def openai_api_key(self) -> Optional[str]:
        return os.environ.get("OPENAI_API_KEY")

    @property
    def anthropic_api_key(self) -> Optional[str]:
        return os.environ.get("ANTHROPIC_API_KEY")

    @property
    def gemini_model(self) -> str:
        return self.settings_raw.get("ai_engine", {}).get("gemini", {}).get("model", "gemini-2.5-flash")

    # ---------------- 數據源 API Tokens ----------------
    @property
    def finmind_token(self) -> Optional[str]:
        return os.environ.get("FINMIND_API_TOKEN")

    @property
    def finnhub_key(self) -> Optional[str]:
        return os.environ.get("FINNHUB_API_KEY")

    @property
    def fred_key(self) -> Optional[str]:
        return os.environ.get("FRED_API_KEY")

    # ---------------- 推播通道 Tokens ----------------
    @property
    def telegram_bot_token(self) -> Optional[str]:
        return os.environ.get("TELEGRAM_BOT_TOKEN")

    @property
    def telegram_chat_id(self) -> Optional[str]:
        return os.environ.get("TELEGRAM_CHAT_ID")

    @property
    def discord_webhook_url(self) -> Optional[str]:
        return os.environ.get("DISCORD_WEBHOOK_URL")

    @property
    def line_channel_access_token(self) -> Optional[str]:
        return os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

    @property
    def line_user_id(self) -> Optional[str]:
        return os.environ.get("LINE_USER_ID")

    @property
    def slack_webhook_url(self) -> Optional[str]:
        return os.environ.get("SLACK_WEBHOOK_URL")

    @property
    def smtp_config(self) -> Dict[str, Any]:
        return {
            "server": os.environ.get("SMTP_SERVER"),
            "port": int(os.environ.get("SMTP_PORT", 587)),
            "user": os.environ.get("SMTP_USER"),
            "password": os.environ.get("SMTP_PASSWORD"),
            "to": [x.strip() for x in os.environ.get("EMAIL_TO", "").split(",") if x.strip()],
            "from": os.environ.get("EMAIL_FROM") or os.environ.get("SMTP_USER")
        }

# 全域單例
config = Config()
