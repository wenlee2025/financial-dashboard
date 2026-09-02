import logging
import math
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

def _safe_val(val: Any, default: float = 0.0) -> float:
    """安全浮點數轉換，過濾 None、NaN 與 Inf"""
    if val is None:
        return default
    try:
        f = float(val)
        return default if math.isnan(f) or math.isinf(f) else f
    except (ValueError, TypeError):
        return default

class PriceLevelCalculator:
    """關鍵買賣點位、支撐壓力、停損停利 (TP/SL) 與風報比計算器 (零 NaN 保證)"""

    def calculate_levels(self, stock_data: Dict[str, Any], score_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        計算關鍵點位與交易規劃
        """
        price = _safe_val(stock_data.get("price"), 0.0)
        if price <= 0:
            return self._build_empty_levels()

        atr = _safe_val(stock_data.get("atr14"), price * 0.02)
        if atr <= 0:
            atr = price * 0.02

        ma5 = _safe_val(stock_data.get("ma5"), price)
        ma20 = _safe_val(stock_data.get("ma20"), price)
        ma60 = _safe_val(stock_data.get("ma60"), price * 0.95)
        bb_upper = _safe_val(stock_data.get("bb_upper"), price + 2 * atr)
        bb_lower = _safe_val(stock_data.get("bb_lower"), price - 2 * atr)
        high_52w = _safe_val(stock_data.get("high_52w"), price * 1.15)
        low_52w = _safe_val(stock_data.get("low_52w"), price * 0.85)

        # 支撐位 (S1: 第一防守線，S2: 核心強支撐)
        s1 = round(max(min(price, ma20), price - 1.2 * atr), 2)
        s2 = round(max(min(s1, ma60), price - 2.5 * atr), 2)
        if s2 >= s1:
            s2 = round(s1 - 1.5 * atr, 2)

        # 壓力位 (R1: 第一阻力，R2: 突破大目標)
        r1 = round(min(max(price, bb_upper), price + 1.5 * atr), 2)
        r2 = round(max(r1 + 1.2 * atr, high_52w if high_52w > price else price + 2.5 * atr), 2)
        if r1 <= price:
            r1 = round(price + 1.2 * atr, 2)
        if r2 <= r1:
            r2 = round(r1 + 1.5 * atr, 2)

        # 停損位 (Stop Loss - SL)
        sl = round(min(s1 * 0.985, price - 1.2 * atr), 2)
        if sl >= price:
            sl = round(price - 1.2 * atr, 2)

        # 停利目標 (Take Profit - TP)
        tp = round(r1, 2)
        if tp <= price:
            tp = round(price + 2.0 * atr, 2)

        # 建議分批進場區間 (Entry Zone)
        entry_low = round(min(s1, price * 0.99), 2)
        entry_high = round(max(price, s1 * 1.01), 2)

        # 風險報酬比 (Risk/Reward Ratio)
        potential_profit = tp - price
        potential_risk = price - sl
        rr_ratio = round(potential_profit / potential_risk, 2) if potential_risk > 0 else 1.0

        # 操作建議描述
        score = _safe_val(score_info.get("score"), 50.0) if score_info else 50.0
        if score >= 75:
            strategy_tip = f"建議在進場區 ${entry_low} ~ ${entry_high} 分批佈局，跌破 ${sl} 嚴格止損。"
        elif score >= 60:
            strategy_tip = f"多頭震盪格局，拉回測試支撐 ${s1} 守穩可低接，目標前高 ${r1}。"
        elif score <= 35:
            strategy_tip = f"走勢偏弱，反彈遇壓力 ${r1} 建議減碼防守，不宜盲目抄底。"
        else:
            strategy_tip = f"區間整理格局，箱型操作於 ${s1} 至 ${r1} 區間，等待放量突破。"

        return {
            "current_price": round(price, 2),
            "s1": s1,
            "s2": s2,
            "r1": r1,
            "r2": r2,
            "entry_zone": f"{entry_low} - {entry_high}",
            "entry_low": entry_low,
            "entry_high": entry_high,
            "target_price": tp,
            "stop_loss": sl,
            "risk_reward_ratio": rr_ratio,
            "strategy_tip": strategy_tip,
            "atr": round(atr, 2)
        }

    def _build_empty_levels(self) -> Dict[str, Any]:
        """安全空點位結構 (100% 零 NaN)"""
        return {
            "current_price": 0.0,
            "s1": 0.0,
            "s2": 0.0,
            "r1": 0.0,
            "r2": 0.0,
            "entry_zone": "-",
            "entry_low": 0.0,
            "entry_high": 0.0,
            "target_price": 0.0,
            "stop_loss": 0.0,
            "risk_reward_ratio": 1.0,
            "strategy_tip": "數據暫時無法計算點位",
            "atr": 0.0
        }
