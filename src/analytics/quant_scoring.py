"""
[向後相容適配模組] quant_scoring.py
核心評價邏輯已全數收斂深化至 src.analytics.equity_evaluator.EquityEvaluator。
本模組保留 QuantScorer 作為相容轉發器，防止外部調用斷裂。
"""
import logging
from typing import Any, Dict, Optional
from .equity_evaluator import EquityEvaluator, EquityEvaluationResult, _safe_float

logger = logging.getLogger(__name__)

class QuantScorer:
    """[相容轉發器] 多因子多空量化計分模型 (底層代理至深模組 EquityEvaluator)"""

    def __init__(self, weights: Optional[Dict[str, float]] = None, tiers: Optional[Dict[str, int]] = None):
        self.evaluator = EquityEvaluator(weights=weights, tiers=tiers)
        self.weights = self.evaluator.weights
        self.tiers = self.evaluator.tiers

    def score_stock(
        self,
        stock_data: Dict[str, Any],
        inst_data: Optional[Dict[str, Any]] = None,
        revenue_data: Optional[Dict[str, Any]] = None,
        macro_sentiment: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """相容接口：轉發至 EquityEvaluator 並返回 score_info 字典"""
        res = self.evaluator.evaluate(stock_data, inst_data, revenue_data, macro_sentiment)
        return res.score_info

    def evaluate_turnover_strategy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """轉發至底層資金動能策略判定"""
        return self.evaluator._evaluate_turnover_strategy(data)
