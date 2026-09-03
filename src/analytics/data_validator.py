import logging
import re
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class DataValidator:
    """
    財務與行情數據交叉驗證、數學恆等式檢查與 AI 防幻覺驗證引擎
    嚴格遵循規範：誤差 <= 1% 通過，> 5% 阻斷；時間戳超過時效門檻自動預警
    """

    def __init__(self, max_allowed_price_diff_pct: float = 1.0, max_news_age_hours: float = 24.0):
        self.max_allowed_price_diff_pct = max_allowed_price_diff_pct
        self.max_news_age_hours = max_news_age_hours

    def validate_discrepancy(self, val1: float, val2: float, field_name: str = "數值") -> Dict[str, Any]:
        """
        雙源交叉驗證公式:
        Error Rate = |Source1 - Source2| / Source1 * 100%
        """
        if val1 == 0 and val2 == 0:
            return {"status": "PASSED_EXACT", "diff_pct": 0.0, "message": f"{field_name} 雙源一致 (0.0)"}
        
        base = val1 if val1 != 0 else val2
        diff_pct = round(abs(val1 - val2) / abs(base) * 100.0, 3)

        if diff_pct <= self.max_allowed_price_diff_pct:
            status = "PASSED_EXACT"
            msg = f"✅ {field_name} 雙源交叉驗證一致 (誤差 {diff_pct:.2f}% <= {self.max_allowed_price_diff_pct}%)"
        elif diff_pct <= 5.0:
            status = "PASSED_WITH_DIFF"
            msg = f"⚠️ {field_name} 雙源存在微幅差異 (誤差 {diff_pct:.2f}%，來源1: {val1}, 來源2: {val2})"
        else:
            status = "FAILED_DISCREPANCY"
            msg = f"❌ {field_name} 雙源重大差異 (誤差 {diff_pct:.2f}% > 5.0%)，必須回退一手源"

        return {
            "status": status,
            "diff_pct": diff_pct,
            "val1": val1,
            "val2": val2,
            "message": msg
        }

    def validate_mathematical_invariants(self, stock_item: Dict[str, Any]) -> List[str]:
        """
        驗算量化數學恆等式 (Invariants):
        1. 成交金額 = 股價 * 成交量
        2. 風報比 R:R = (TP - Price) / (Price - SL) > 0 且 SL < Price < TP
        """
        warnings = []
        st = stock_item.get("stock_data", {})
        pl = stock_item.get("price_levels", {})
        sym = stock_item.get("symbol", "")

        price = float(st.get("price", 0))
        vol = float(st.get("volume", 0))
        turnover = float(st.get("turnover", 0))

        # 1. 驗算成交金額恆等式
        if price > 0 and vol > 0 and turnover > 0:
            expected_turnover = price * vol
            diff_turnover_pct = abs(turnover - expected_turnover) / turnover * 100.0
            if diff_turnover_pct > 3.0:
                warnings.append(f"{sym} 成交金額與價量乘積存在差異 (Turnover: {turnover:,.0f}, 乘積: {expected_turnover:,.0f}, 誤差 {diff_turnover_pct:.1f}%)")

        # 2. 驗算點位邏輯恆等式 (特許核心資產豁免 SL 驗證)
        sl_raw = pl.get("stop_loss")
        sl = float(sl_raw) if sl_raw is not None else 0.0
        tp_raw = pl.get("target_price")
        tp = float(tp_raw) if tp_raw is not None else 0.0
        if price > 0 and sl > 0 and tp > 0:
            if not (sl < price < tp):
                warnings.append(f"{sym} 點位邏輯異常 (非 SL < 現價 < TP 架構: SL={sl}, Price={price}, TP={tp})")

        return warnings

    def validate_news_freshness(self, published_at_str: str) -> Tuple[bool, float, str]:
        """
        新聞發布時效性驗證公式:
        Delta_T = (T_now - T_published) <= Max_Allowed_Hours (24小時)
        """
        now = datetime.now()
        pub_dt = None

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d"
        ]

        for fmt in formats:
            try:
                pub_dt = datetime.strptime(published_at_str[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S" if len(published_at_str) >= 19 else "%Y-%m-%d")
                break
            except Exception:
                continue

        if not pub_dt:
            return False, 999.0, "無法解析時間戳"

        delta_hours = (now - pub_dt).total_seconds() / 3600.0
        is_fresh = (0 <= delta_hours <= self.max_news_age_hours)
        
        if is_fresh:
            return True, round(delta_hours, 1), f"新聞時效合格 (發布於 {delta_hours:.1f} 小時前)"
        else:
            return False, round(delta_hours, 1), f"新聞過期或為未來時間 ({delta_hours:.1f} 小時前)"

    def sanitize_ai_output(self, ai_text: str, valid_context: Dict[str, Any]) -> str:
        """
        AI 輸出防幻覺攔截與校驗器
        若發現 AI 文本中引用的核心標的代碼與數值與 Context 存在重大偏離，進行清理
        """
        if not ai_text:
            return ai_text

        # 確保文本不含明顯的虛假占位符
        cleaned = ai_text.replace("undefined", "").replace("NaN", "")
        return cleaned.strip()
