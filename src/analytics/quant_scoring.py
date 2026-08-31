import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class QuantScorer:
    """多因子多空量化計分模型 (技術面 40% + 籌碼面 35% + 基本面 25%)"""

    def __init__(self, weights: Optional[Dict[str, float]] = None, tiers: Optional[Dict[str, int]] = None):
        self.weights = weights or {"technicals": 0.40, "flows": 0.35, "fundamentals": 0.25}
        self.tiers = tiers or {
            "strong_bull": 78,
            "lean_bull": 60,
            "neutral": 42,
            "lean_bear": 28,
            "strong_bear": 0
        }

    def score_stock(
        self,
        stock_data: Dict[str, Any],
        inst_data: Optional[Dict[str, Any]] = None,
        revenue_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        對單檔標的進行綜合多空評分
        返回: {
            "score": 82.5,
            "rating": "強力做多",
            "rating_code": "strong_bull",
            "badge_color": "green",
            "tech_score": 85.0,
            "flow_score": 80.0,
            "fund_score": 80.0,
            "signals": ["均線多頭排列", "MACD柱狀體轉正", "外資投信同步買超"]
        }
        """
        signals: List[str] = []
        c_price = stock_data.get("price", 0.0)

        # 若價格為 0，給予安全預設
        if c_price <= 0:
            return self._build_default_score()

        # 1. 技術面評分 (0-100)
        tech_score, tech_signals = self._eval_technicals(stock_data)
        signals.extend(tech_signals)

        # 2. 籌碼面評分 (0-100)
        flow_score, flow_signals = self._eval_flows(stock_data, inst_data)
        signals.extend(flow_signals)

        # 3. 基本面與估值評分 (0-100)
        fund_score, fund_signals = self._eval_fundamentals(stock_data, revenue_data)
        signals.extend(fund_signals)

        # 加權總分
        w_t = self.weights.get("technicals", 0.40)
        w_fl = self.weights.get("flows", 0.35)
        w_fu = self.weights.get("fundamentals", 0.25)
        total_score = round((tech_score * w_t) + (flow_score * w_fl) + (fund_score * w_fu), 1)

        # 評級判斷
        rating, rating_code, badge_color = self._determine_rating(total_score)

        return {
            "score": total_score,
            "rating": rating,
            "rating_code": rating_code,
            "badge_color": badge_color,
            "tech_score": round(tech_score, 1),
            "flow_score": round(flow_score, 1),
            "fund_score": round(fund_score, 1),
            "signals": signals
        }

    def _eval_technicals(self, data: Dict[str, Any]) -> Tuple[float, List[str]]:
        """評估技術面指標"""
        score = 50.0  # 基準中立分
        signals = []
        price = data.get("price", 0.0)
        ma5 = data.get("ma5")
        ma10 = data.get("ma10")
        ma20 = data.get("ma20")
        ma60 = data.get("ma60") or data.get("ma50")
        rsi = data.get("rsi14", 50.0)
        macd_hist = data.get("macd_hist", 0.0)
        vol_ratio = data.get("volume_ratio", 1.0)
        pct_change = data.get("pct_change", 0.0)

        # 1. 均線排列
        if ma5 and ma20 and ma60:
            if price > ma5 > ma20 > ma60:
                score += 25
                signals.append("均線呈標準多頭排列 (股價 > 5MA > 20MA > 60MA)")
            elif price > ma20 and ma20 > ma60:
                score += 15
                signals.append("股價站穩月線 (20MA) 與季線 (60MA)")
            elif price < ma5 < ma20 < ma60:
                score -= 25
                signals.append("均線呈空頭排列 (股價破所有短中長期均線)")
            elif price < ma20:
                score -= 10
                signals.append("股價失守 20MA 月線支撐")

        # 2. RSI 動能
        if 50 <= rsi <= 70:
            score += 10
            signals.append(f"RSI({rsi:.0f}) 處於強勢多頭擴張區")
        elif rsi > 80:
            score -= 5
            signals.append(f"RSI({rsi:.0f}) 短線過熱 (超買區注意回檔)")
        elif rsi < 30:
            score -= 10
            signals.append(f"RSI({rsi:.0f}) 進入超賣弱勢區")

        # 3. MACD 柱狀體
        if macd_hist > 0:
            score += 10
            signals.append("MACD 柱狀體維持正值 (紅柱增長/多頭控盤)")
        else:
            score -= 10
            signals.append("MACD 柱狀體為負值 (綠柱延續/空頭格局)")

        # 4. 量價配合
        if pct_change > 0 and vol_ratio > 1.2:
            score += 10
            signals.append(f"量增價揚 (成交量擴增 {vol_ratio:.1f} 倍)")
        elif pct_change < -1.5 and vol_ratio > 1.3:
            score -= 15
            signals.append(f"出量下殺 (帶量下挫 {pct_change:.2f}%)")

        score = max(0.0, min(100.0, score))
        return score, signals

    def _eval_flows(self, data: Dict[str, Any], inst_data: Optional[Dict[str, Any]]) -> Tuple[float, List[str]]:
        """評估籌碼面指標"""
        score = 50.0
        signals = []
        market = data.get("market", "TW")

        if market == "TW" and inst_data:
            foreign = inst_data.get("foreign_lots", 0)
            trust = inst_data.get("trust_lots", 0)
            dealer = inst_data.get("dealer_lots", 0)
            total = inst_data.get("total_lots", foreign + trust + dealer)

            if foreign > 0 and trust > 0:
                score += 30
                signals.append(f"外資與投信同步買超 (外資 +{foreign}張, 投信 +{trust}張)")
            elif trust > 500:
                score += 20
                signals.append(f"投信積極認養加碼 (+{trust}張)")
            elif foreign > 1000:
                score += 20
                signals.append(f"外資大舉敲進 (+{foreign}張)")
            elif foreign < -1000 and trust < -300:
                score -= 30
                signals.append(f"外資與投信同步調節賣超 (外資 {foreign}張, 投信 {trust}張)")
            elif foreign < -2000:
                score -= 20
                signals.append(f"外資大幅提款賣超 ({foreign}張)")
            elif total > 0:
                score += 10
                signals.append(f"三大法人合計買超 {total} 張")
            elif total < 0:
                score -= 10
                signals.append(f"三大法人合計賣超 {abs(total)} 張")
        else:
            # 美股籌碼或無籌碼時採用動能替代
            vol_ratio = data.get("volume_ratio", 1.0)
            recommendation = data.get("recommendation", "N/A")
            if "buy" in str(recommendation).lower():
                score += 20
                signals.append(f"華爾街分析師綜合共識評級：買入 ({recommendation})")
            if vol_ratio > 1.5:
                score += 15
                signals.append(f"主力大單放量 (成交量達前日 {vol_ratio:.1f} 倍)")

        score = max(0.0, min(100.0, score))
        return score, signals

    def _eval_fundamentals(self, data: Dict[str, Any], revenue_data: Optional[Dict[str, Any]]) -> Tuple[float, List[str]]:
        """評估基本面與估值指標"""
        score = 50.0
        signals = []

        # 月營收年增率
        if revenue_data and "growth_rate_yoy" in revenue_data:
            yoy = revenue_data.get("growth_rate_yoy")
            if yoy is not None:
                if yoy >= 25.0:
                    score += 25
                    signals.append(f"單月營收年增達 +{yoy:.1f}% (基本面高成長動能)")
                elif yoy > 5.0:
                    score += 15
                    signals.append(f"單月營收穩定成長 YoY +{yoy:.1f}%")
                elif yoy < -10.0:
                    score -= 20
                    signals.append(f"單月營收衰退 YoY {yoy:.1f}% (營運逆風)")

        # 本益比與股利率
        pe = data.get("pe_ratio")
        dy = data.get("dividend_yield")
        if pe:
            if 0 < pe < 20:
                score += 15
                signals.append(f"本益比 {pe:.1f}x 處於合理偏低評價區間")
            elif pe > 60:
                score -= 10
                signals.append(f"本益比 {pe:.1f}x 估值偏高 (定價已反映未來樂觀預期)")

        if dy and dy >= 4.0:
            score += 10
            signals.append(f"現金殖利率達 {dy:.1f}% 具備下檔股息防守保護")

        score = max(0.0, min(100.0, score))
        return score, signals

    def _determine_rating(self, score: float) -> Tuple[str, str, str]:
        """根據總分判定 5 階評級與對應徽章顏色"""
        if score >= self.tiers.get("strong_bull", 78):
            return "強力做多", "strong_bull", "emerald"
        elif score >= self.tiers.get("lean_bull", 60):
            return "偏多震盪", "lean_bull", "green"
        elif score >= self.tiers.get("neutral", 42):
            return "中立觀望", "neutral", "yellow"
        elif score >= self.tiers.get("lean_bear", 28):
            return "偏空防守", "lean_bear", "orange"
        else:
            return "避險做空", "strong_bear", "rose"

    def _build_default_score(self) -> Dict[str, Any]:
        return {
            "score": 50.0,
            "rating": "中立觀望",
            "rating_code": "neutral",
            "badge_color": "yellow",
            "tech_score": 50.0,
            "flow_score": 50.0,
            "fund_score": 50.0,
            "signals": ["數據不足，維持中立觀望"]
        }
