import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml
import yfinance as yf

logger = logging.getLogger(__name__)

class WatchlistManager:
    """自選股清單管理器：支援動態新增、刪除、查詢與 YAML 設定檔安全同步"""

    def __init__(self, watchlist_path: Optional[Path] = None):
        if watchlist_path is None:
            base_dir = Path(__file__).resolve().parent.parent
            self.watchlist_path = base_dir / "config" / "watchlist.yaml"
        else:
            self.watchlist_path = Path(watchlist_path)
        
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        """載入 YAML 檔案"""
        if not self.watchlist_path.exists():
            logger.warning(f"自選股設定檔不存在: {self.watchlist_path}，初始化空結構")
            return {
                "indices": {"us": [], "tw": []},
                "us_stocks": [],
                "tw_stocks": [],
                "adr_mappings": []
            }
        try:
            with open(self.watchlist_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f) or {}
                if "us_stocks" not in content:
                    content["us_stocks"] = []
                if "tw_stocks" not in content:
                    content["tw_stocks"] = []
                return content
        except Exception as e:
            logger.error(f"讀取自選股設定檔失敗: {e}")
            return {"us_stocks": [], "tw_stocks": []}

    def save(self) -> bool:
        """將目前自選股結構寫回 YAML 檔案"""
        try:
            self.watchlist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.watchlist_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    self.data,
                    f,
                    allow_unicode=True,
                    sort_keys=False,
                    indent=2,
                    default_flow_style=False
                )
            logger.info(f"已成功儲存自選股清單至 {self.watchlist_path}")
            return True
        except Exception as e:
            logger.error(f"儲存自選股清單失敗: {e}")
            return False

    def _detect_market(self, symbol: str) -> str:
        """自動辨識股票市場 (TW 或 US)"""
        clean = str(symbol).strip().upper()
        if clean.startswith("^"):
            return "INDEX"
        if clean.endswith(".TW") or clean.endswith(".TWO"):
            return "TW"
        if clean.isdigit():
            return "TW"
        return "US"

    def _auto_fetch_info(self, symbol: str, market: str) -> Dict[str, str]:
        """透過 yfinance 自動抓取公司名稱與行業資訊"""
        clean = str(symbol).strip().upper()
        yf_symbol = f"{clean}.TW" if market == "TW" and "." not in clean else clean
        try:
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info or {}
            name = info.get("shortName") or info.get("longName") or clean
            sector = info.get("sector") or info.get("industry") or "科技/零組件"
            return {"name": name, "sector": sector}
        except Exception:
            return {"name": clean, "sector": "自選股"}

    def add_stock(
        self,
        symbol: str,
        name: Optional[str] = None,
        market: Optional[str] = None,
        sector: Optional[str] = None,
        note: Optional[str] = None,
        auto_save: bool = True
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        新增單檔股票至自選股清單
        :return: (是否成功, 提示訊息, 股票物件)
        """
        clean_symbol = str(symbol).strip().upper()
        if not clean_symbol:
            return False, "股票代碼不可為空", {}

        detected_market = market.upper() if market else self._detect_market(clean_symbol)
        target_list_key = "tw_stocks" if detected_market == "TW" else "us_stocks"

        # 檢查是否已存在
        target_list = self.data.setdefault(target_list_key, [])
        for item in target_list:
            if str(item.get("symbol", "")).strip().upper() == clean_symbol:
                # 若已存在，更新備註與名稱
                if name:
                    item["name"] = name
                if sector:
                    item["sector"] = sector
                if note:
                    item["note"] = note
                if auto_save:
                    self.save()
                return True, f"標的 {clean_symbol} 已在清單中，已更新資訊", item

        # 若未提供名稱或產業，嘗試自動擷取
        if not name or not sector:
            fetched = self._auto_fetch_info(clean_symbol, detected_market)
            name = name or fetched["name"]
            sector = sector or fetched["sector"]

        new_stock = {
            "symbol": clean_symbol,
            "name": name or clean_symbol,
            "sector": sector or ("台股自選" if detected_market == "TW" else "美股自選"),
            "note": note or "用戶自選監控標的"
        }

        target_list.append(new_stock)
        if auto_save:
            self.save()

        return True, f"成功將 {clean_symbol} ({new_stock['name']}) 加入 {detected_market} 自選清單", new_stock

    def remove_stock(self, symbol: str, auto_save: bool = True) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        從自選股清單中移除指定股票
        :return: (是否成功, 提示訊息, 被移除的股票物件)
        """
        clean_symbol = str(symbol).strip().upper()
        if not clean_symbol:
            return False, "請指定欲移除的股票代碼", None

        # 在台股與美股清單中查找並刪除
        removed_item = None
        for key in ["tw_stocks", "us_stocks"]:
            stocks = self.data.get(key, [])
            for i, item in enumerate(stocks):
                item_sym = str(item.get("symbol", "")).strip().upper()
                if item_sym == clean_symbol or item_sym.replace(".TW", "").replace(".TWO", "") == clean_symbol:
                    removed_item = stocks.pop(i)
                    break
            if removed_item:
                break

        if not removed_item:
            return False, f"在自選清單中未找到標的: {clean_symbol}", None

        if auto_save:
            self.save()

        return True, f"已成功從自選清單中移除: {clean_symbol} ({removed_item.get('name', '')})", removed_item

    def batch_add(self, symbols_str_or_list: Any, auto_save: bool = True) -> List[Dict[str, Any]]:
        """批次新增股票（支援逗號分隔字串或列表）"""
        if isinstance(symbols_str_or_list, str):
            symbols = [s.strip() for s in symbols_str_or_list.replace("，", ",").split(",") if s.strip()]
        else:
            symbols = [str(s).strip() for s in symbols_str_or_list if str(s).strip()]

        added_list = []
        for sym in symbols:
            success, msg, item = self.add_stock(sym, auto_save=False)
            if success:
                added_list.append(item)
                logger.info(msg)

        if auto_save and added_list:
            self.save()
        return added_list

    def batch_remove(self, symbols_str_or_list: Any, auto_save: bool = True) -> List[Dict[str, Any]]:
        """批次移除股票（支援逗號分隔字串或列表）"""
        if isinstance(symbols_str_or_list, str):
            symbols = [s.strip() for s in symbols_str_or_list.replace("，", ",").split(",") if s.strip()]
        else:
            symbols = [str(s).strip() for s in symbols_str_or_list if str(s).strip()]

        removed_list = []
        for sym in symbols:
            success, msg, item = self.remove_stock(sym, auto_save=False)
            if success and item:
                removed_list.append(item)
                logger.info(msg)

        if auto_save and removed_list:
            self.save()
        return removed_list

    def list_stocks(self, market: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """列出目前所有的自選股"""
        m = market.upper() if market else "ALL"
        result = {}
        if m in ["ALL", "TW"]:
            result["tw_stocks"] = self.data.get("tw_stocks", [])
        if m in ["ALL", "US"]:
            result["us_stocks"] = self.data.get("us_stocks", [])
        return result

    def get_summary_text(self) -> str:
        """產出格式化純文字清單供終端顯示"""
        tw_list = self.data.get("tw_stocks", [])
        us_list = self.data.get("us_stocks", [])
        
        lines = []
        lines.append("=======================================================")
        lines.append(f"  📋 目前自選監控標的清單 (總計 {len(tw_list) + len(us_list)} 檔)")
        lines.append("=======================================================")
        
        lines.append(f"\n🇹🇼 台股清單 ({len(tw_list)} 檔):")
        lines.append("-" * 55)
        lines.append(f"{'代碼':<8} {'名稱':<12} {'板塊/產業':<16} {'備註'}")
        lines.append("-" * 55)
        for s in tw_list:
            sym = s.get("symbol", "")
            name = s.get("name", "")
            sec = s.get("sector", "-")
            note = s.get("note", "")
            lines.append(f"{sym:<8} {name:<12} {sec:<16} {note}")

        lines.append(f"\n🇺🇸 美股清單 ({len(us_list)} 檔):")
        lines.append("-" * 55)
        lines.append(f"{'代碼':<8} {'名稱':<16} {'板塊/產業':<16} {'備註'}")
        lines.append("-" * 55)
        for s in us_list:
            sym = s.get("symbol", "")
            name = s.get("name", "")
            sec = s.get("sector", "-")
            note = s.get("note", "")
            lines.append(f"{sym:<8} {name:<16} {sec:<16} {note}")
        
        lines.append("\n=======================================================")
        return "\n".join(lines)
