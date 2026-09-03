"""
[向後相容適配模組] price_levels.py
核心點位與策略邏輯已全數收斂深化至 src.analytics.equity_evaluator.EquityEvaluator。
本模組保留 PriceLevelCalculator 作為相容轉發器，防止外部調用斷裂。
"""
import logging
from typing import Any, Dict, Optional
from .equity_evaluator import EquityEvaluator, _safe_float

logger = logging.getLogger(__name__)

def _safe_val(val: Any, default: float = 0.0) -> float:
    return _safe_float(val, default)

class PriceLevelCalculator:
    """[相容轉發器] 關鍵買賣點位與風報比計算器 (底層代理至深模組 EquityEvaluator)"""

    def __init__(self):
        self.evaluator = EquityEvaluator()

    def calculate_levels(self, stock_data: Dict[str, Any], score_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """相容接口：轉發至 EquityEvaluator._calculate_price_levels 並返回 price_levels 字典"""
        score = _safe_float(score_info.get("score"), 50.0) if score_info else 50.0
        return self.evaluator._calculate_price_levels(stock_data, score)
