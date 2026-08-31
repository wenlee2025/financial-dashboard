import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

class HTMLDashboardGenerator:
    """HTML 靜態儀表板與歷史報告產生器"""

    def __init__(self, template_dir: Path, output_dir: Path, history_dir: Path, data_dir: Path):
        self.template_dir = template_dir
        self.output_dir = output_dir
        self.history_dir = history_dir
        self.data_dir = data_dir
        
        # 確保目標目錄均存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=True)

    def generate(self, context: Dict[str, Any], date_str: str, market_mode: str) -> Path:
        """
        生成 docs/index.html 以及 docs/history/{date}_{mode}.html
        """
        # 1. 載入並更新歷史索引
        history_list = self._update_history_index(date_str, market_mode)
        context["history_list"] = history_list

        # 2. 渲染模板
        template = self.env.get_template("dashboard_template.html")
        html_content = template.render(**context)

        # 3. 寫入最新 docs/index.html
        latest_file = self.output_dir / "index.html"
        with open(latest_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        # 4. 寫入歷史存檔 docs/history/{date}_{mode}.html
        history_file = self.history_dir / f"{date_str}_{market_mode}.html"
        with open(history_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        # 5. 寫入歷史 JSON 結構化數據
        data_file = self.data_dir / f"{date_str}_{market_mode}.json"
        # 過濾不可序列化物件
        safe_context = self._make_json_safe(context)
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(safe_context, f, ensure_ascii=False, indent=2)

        logger.info(f"成功生成最新儀表板: {latest_file} 及歷史存檔: {history_file}")
        return latest_file

    def _update_history_index(self, date_str: str, market_mode: str) -> List[Dict[str, str]]:
        """維護 docs/data/history_index.json"""
        index_file = self.data_dir / "history_index.json"
        history_entries: List[Dict[str, str]] = []

        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    history_entries = json.load(f)
            except Exception:
                history_entries = []

        mode_name = "台股盤後" if market_mode == "tw_post" else ("美股晨報" if market_mode == "us_morning" else "全覽")
        title = f"{date_str} {mode_name}"
        url = f"history/{date_str}_{market_mode}.html"

        # 檢查是否已存在，若存在先移除舊項
        history_entries = [e for e in history_entries if e.get("url") != url]
        # 插入最前
        history_entries.insert(0, {
            "date": date_str,
            "mode": market_mode,
            "title": title,
            "url": url
        })

        # 保留最近 90 筆
        history_entries = history_entries[:90]

        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(history_entries, f, ensure_ascii=False, indent=2)

        return history_entries

    def _make_json_safe(self, obj: Any) -> Any:
        """確保所有物件均可 JSON 序列化"""
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj
        elif isinstance(obj, dict):
            return {k: self._make_json_safe(v) for k, v in obj.items() if not k.startswith("_")}
        elif isinstance(obj, (list, tuple)):
            return [self._make_json_safe(x) for x in obj]
        else:
            return str(obj)
