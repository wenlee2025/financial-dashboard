from dataclasses import dataclass, field
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

def _safe_float(val: Any, default: float = 0.0) -> float:
    """安全浮點數轉換，過濾 None、NaN 與 Inf"""
    if val is None:
        return default
    try:
        f = float(val)
        return default if math.isnan(f) or math.isinf(f) else f
    except (ValueError, TypeError):
        return default


@dataclass
class EquityEvaluationResult:
    """投資標的完整評價實體 (方向性評分 + 執行點位 + 風報比 + 雙軌策略)"""
    score: float
    rating: str
    rating_code: str
    badge_color: str
    regime_label: str
    tech_score: float
    flow_score: float
    fund_score: float
    score_info: Dict[str, Any] = field(default_factory=dict)
    price_levels: Dict[str, Any] = field(default_factory=dict)
    signals: List[str] = field(default_factory=list)
    turnover_strategy: Dict[str, Any] = field(default_factory=dict)
    tier: str = "TIER_2_MOMENTUM"
    tier_label: str = "⚡ 戰術動量"
    moat_badge: str = "⚡ 戰術動量"
    strategy_tip: str = ""
    stop_loss_display: str = ""
    stop_loss: float = 0.0
    entry_zone: str = ""
    target_price: float = 0.0
    risk_reward_ratio: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """產出兼顧既有範本 (Template) 與 JSON 導出的複合字典"""
        return {
            "score": self.score,
            "rating": self.rating,
            "rating_code": self.rating_code,
            "badge_color": self.badge_color,
            "regime_label": self.regime_label,
            "tech_score": self.tech_score,
            "flow_score": self.flow_score,
            "fund_score": self.fund_score,
            "score_info": self.score_info,
            "price_levels": self.price_levels,
            "signals": self.signals,
            "turnover_strategy": self.turnover_strategy,
            "tier": self.tier,
            "tier_label": self.tier_label,
            "moat_badge": self.moat_badge,
            "strategy_tip": self.strategy_tip,
            "stop_loss_display": self.stop_loss_display,
            "stop_loss": self.stop_loss,
            "entry_zone": self.entry_zone,
            "target_price": self.target_price,
            "risk_reward_ratio": self.risk_reward_ratio
        }


class EquityEvaluator:
    """
    深模組：投資標的深度評價引擎 (Equity Evaluation Engine)
    
    【深模組介面 (Deep Seam)】
    調用端僅需調用單一方法 evaluate(stock_data, inst_data, revenue_data, macro_sentiment)。
    
    【接縫後隱藏之內部實作】
    1. 市場體制自適應調節 (Regime-Adaptive Weighting)
    2. 多週期技術排列與 5MA 成交總值動能策略 (Technicals & Turnover 5MA)
    3. 外資投信自營商法人籌碼流向 (Smart Money Flows)
    4. 前瞻動態本益比 (Forward PE) 與 PEG 成長性價比 (Forward Consensus)
    5. 外資台指期巨額淨空單大盤防護網 (TX Futures Macro Guard)
    6. 雙軌執行點位規劃：👑 波克夏特許核心 (金字塔加碼 + 豁免ATR停損) vs ⚡ 戰術動量 (嚴格ATR停損)
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None, tiers: Optional[Dict[str, int]] = None):
        self.weights = weights or {"technicals": 0.40, "flows": 0.35, "fundamentals": 0.25}
        self.tiers = tiers or {
            "strong_bull": 78,
            "lean_bull": 60,
            "neutral": 42,
            "lean_bear": 28,
            "strong_bear": 0
        }

    def evaluate(
        self,
        stock_data: Dict[str, Any],
        inst_data: Optional[Dict[str, Any]] = None,
        revenue_data: Optional[Dict[str, Any]] = None,
        macro_sentiment: Optional[Dict[str, Any]] = None
    ) -> EquityEvaluationResult:
        """
        全市場統一標的深度評價入口
        """
        c_price = _safe_float(stock_data.get("price"), 0.0)
        if c_price <= 0:
            return self._build_empty_evaluation(stock_data)

        signals: List[str] = []

        # 1. 市場體制自適應調節 (Regime-Adaptive Weights)
        w_t = self.weights.get("technicals", 0.40)
        w_fl = self.weights.get("flows", 0.35)
        w_fu = self.weights.get("fundamentals", 0.25)
        regime_label = "常態平衡體制"

        if macro_sentiment:
            fg_data = macro_sentiment.get("fear_and_greed", {})
            fg_score = _safe_float(fg_data.get("score"), 50.0) if isinstance(fg_data, dict) else 50.0
            macro_data = macro_sentiment.get("macro", {})
            vix_item = macro_data.get("vix", {})
            vix_val = _safe_float(vix_item.get("value"), 15.0) if isinstance(vix_item, dict) else 15.0

            if fg_score < 30.0 or vix_val > 22.0:
                w_t, w_fl, w_fu = 0.30, 0.50, 0.20
                regime_label = "恐慌防守體制 (籌碼風控優先 50%)"
            elif fg_score > 65.0 and vix_val < 16.0:
                w_t, w_fl, w_fu = 0.50, 0.30, 0.20
                regime_label = "強勢主升體制 (動量進攻優先 50%)"

        # 2. 技術面多因子評分 (0-100)
        tech_score, tech_signals = self._eval_technicals(stock_data)
        signals.extend(tech_signals)

        # 3. 籌碼面評分 (0-100)
        flow_score, flow_signals = self._eval_flows(stock_data, inst_data)
        signals.extend(flow_signals)

        # 4. 基本面與前瞻估值評分 (Forward PE & PEG, 0-100)
        fund_score, fund_signals = self._eval_fundamentals(stock_data, revenue_data)
        signals.extend(fund_signals)

        # 5. 成交總值 5MA 資金動能策略評估
        turnover_strategy = self._evaluate_turnover_strategy(stock_data)
        if turnover_strategy.get("signal"):
            signals.insert(0, turnover_strategy["signal"])

        # 6. 台指期大盤外資淨空單防護 (TX Futures Macro Guard)
        futures_penalty = 0
        if macro_sentiment:
            tx_guard = macro_sentiment.get("tx_futures", {})
            if tx_guard.get("is_high_risk"):
                sym = str(stock_data.get("symbol", "")).strip()
                if sym in ["2330", "2317", "2454", "2382", "2308", "3711"]:
                    futures_penalty = -10
                    signals.append("⚠️ 外資台指期巨額淨空單壓盤 (大盤結算提款風險高，權值股扣減 10 分)")

        # 綜合加權總分
        base_score = (tech_score * w_t) + (flow_score * w_fl) + (fund_score * w_fu)
        total_score = base_score + turnover_strategy.get("score_modifier", 0) + futures_penalty
        total_score = round(max(0.0, min(100.0, total_score)), 1)

        rating, rating_code, badge_color = self._determine_rating(total_score)

        score_info = {
            "score": total_score,
            "regime_label": regime_label,
            "rating": rating,
            "rating_code": rating_code,
            "badge_color": badge_color,
            "tech_score": round(tech_score, 1),
            "flow_score": round(flow_score, 1),
            "fund_score": round(fund_score, 1),
            "turnover_strategy": turnover_strategy,
            "signals": signals
        }

        # 7. 關鍵進出場點位、金字塔加碼階梯與雙軌風報比計算
        price_levels = self._calculate_price_levels(stock_data, total_score)

        return EquityEvaluationResult(
            score=total_score,
            rating=rating,
            rating_code=rating_code,
            badge_color=badge_color,
            regime_label=regime_label,
            tech_score=round(tech_score, 1),
            flow_score=round(flow_score, 1),
            fund_score=round(fund_score, 1),
            score_info=score_info,
            price_levels=price_levels,
            signals=signals,
            turnover_strategy=turnover_strategy,
            tier=price_levels.get("tier", "TIER_2_MOMENTUM"),
            tier_label=price_levels.get("tier_label", "⚡ 戰術動量"),
            moat_badge=price_levels.get("moat_badge", "⚡ 戰術動量"),
            strategy_tip=price_levels.get("strategy_tip", ""),
            stop_loss_display=price_levels.get("stop_loss_display", ""),
            stop_loss=price_levels.get("stop_loss", 0.0),
            entry_zone=price_levels.get("entry_zone", ""),
            target_price=price_levels.get("target_price", 0.0),
            risk_reward_ratio=price_levels.get("risk_reward_ratio", 1.0)
        )

    # ---------------- 內部私有實作 (Private to Module) ----------------

    def _eval_technicals(self, data: Dict[str, Any]) -> Tuple[float, List[str]]:
        score = 50.0
        signals = []
        price = _safe_float(data.get("price"))
        ma5 = _safe_float(data.get("ma5"), price)
        ma10 = _safe_float(data.get("ma10"), price)
        ma20 = _safe_float(data.get("ma20"), price)
        ma60 = _safe_float(data.get("ma60"), price)
        rsi = _safe_float(data.get("rsi14"), 50.0)
        macd_hist = _safe_float(data.get("macd_hist"), 0.0)

        # 均線多空排列
        if price > ma5 > ma10 > ma20 > ma60:
            score += 25
            signals.append("均線呈強大多頭排列 (站上全天期均線)")
        elif price > ma20:
            score += 15
            signals.append("股價站上月線 (中線偏多)")
        elif price < ma5 < ma10 < ma20:
            score -= 25
            signals.append("均線呈空頭排列 (跌破全期均線)")
        elif price < ma20:
            score -= 15
            signals.append("股價跌破月線 (中線偏空)")

        # 5. 週日多週期趨勢共振 (Multi-Timeframe Resonance)
        weekly_trend = data.get("weekly_trend", "neutral")
        if weekly_trend == "bullish":
            if ma20 and price >= ma20 and abs(price - ma20) / max(1.0, ma20) <= 0.035:
                score += 15
                signals.append("✓ 週日多週期共振：週線大多頭 + 日線拉回測試月線 (高勝率買點)")
            elif ma5 and price >= ma5:
                score += 8
                signals.append("✓ 週日線雙週期同步多頭走揚 (週5MA多方控盤)")
        elif weekly_trend == "bearish":
            score -= 10
            signals.append("⚠️ 週級別大趨勢偏空 (中長線結構受壓)")

        # RSI 指標
        if 50 <= rsi <= 65:
            score += 10
            signals.append(f"RSI({rsi:.1f}) 位於健康上升擴張區")
        elif rsi > 80:
            score -= 5
            signals.append(f"RSI({rsi:.1f}) 進入超買過熱警戒區")
        elif rsi < 25:
            score += 5
            signals.append(f"RSI({rsi:.1f}) 進入嚴重超賣背離區")

        # MACD 柱狀體
        if macd_hist > 0:
            score += 10
            signals.append("MACD 柱狀體紅柱擴張")
        elif macd_hist < 0:
            score -= 10
            signals.append("MACD 柱狀體綠柱發散")

        return max(0.0, min(100.0, score)), signals

    def _eval_flows(self, stock_data: Dict[str, Any], inst_data: Optional[Dict[str, Any]]) -> Tuple[float, List[str]]:
        score = 50.0
        signals = []
        vol_ratio = _safe_float(stock_data.get("volume_ratio"), 1.0)
        pct_change = _safe_float(stock_data.get("pct_change"), 0.0)

        # 價量配合
        if pct_change > 0 and vol_ratio >= 1.5:
            score += 15
            signals.append(f"放量上攻 (量比 {vol_ratio:.1f}x)")
        elif pct_change < -1.5 and vol_ratio >= 1.5:
            score -= 20
            signals.append(f"帶量下殺 (量比 {vol_ratio:.1f}x 籌碼出走)")
        elif vol_ratio < 0.6:
            signals.append("量能急凍沉澱")

        # 三大法人籌碼
        if inst_data:
            tot = inst_data.get("total_lots", 0)
            f_lots = inst_data.get("foreign_lots", 0)
            t_lots = inst_data.get("trust_lots", 0)

            if tot > 500:
                score += 20
                signals.append(f"三大法人大買 +{tot:,d} 張")
            elif tot > 0:
                score += 10
                signals.append(f"三大法人小買 +{tot:,d} 張")
            elif tot < -500:
                score -= 20
                signals.append(f"三大法人重挫賣超 {tot:,d} 張")
            elif tot < 0:
                score -= 10
                signals.append(f"三大法人調節賣超 {tot:,d} 張")

            # 土洋合力或對作
            if f_lots > 200 and t_lots > 200:
                score += 15
                signals.append("外資投信土洋同步大買合力作多")
            elif f_lots < -200 and t_lots < -200:
                score -= 15
                signals.append("外資投信雙邊同時大幅提款")

        return max(0.0, min(100.0, score)), signals

    def _eval_fundamentals(self, data: Dict[str, Any], revenue_data: Optional[Dict[str, Any]]) -> Tuple[float, List[str]]:
        score = 50.0
        signals = []

        price = data.get("price", 0.0)
        ma20 = data.get("ma20") or price
        ma60 = data.get("ma60") or price
        yoy = revenue_data.get("growth_rate_yoy") if revenue_data else None
        weekly_bullish = data.get("weekly_trend") == "bullish"
        price_ma5_up = data.get("price_ma5_slope", 0.0) > 0
        pct_change = data.get("pct_change", 0.0)

        is_turnaround_breakout = (
            (yoy is not None and yoy >= 25.0) or
            (weekly_bullish and price > ma20 and ma20 > ma60) or
            (weekly_bullish and price_ma5_up and pct_change > 0.5)
        )

        # 月營收年增率
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

        # 轉折反轉爆發加權
        if is_turnaround_breakout:
            score += 15
            signals.append("✓ 轉折反轉爆發主升：啟動高成長爆發加權，豁免高本益比抑制")

        # 本益比評估
        pe = data.get("pe_ratio")
        dy = data.get("dividend_yield")
        if pe:
            if 0 < pe < 20:
                score += 15
                signals.append(f"本益比 {pe:.1f}x 處於合理偏低評價區間")
            elif pe > 60:
                if is_turnaround_breakout:
                    signals.append(f"本益比 {pe:.1f}x 雖偏高，但處於轉折爆發期，豁免估值扣分")
                else:
                    score -= 10
                    signals.append(f"本益比 {pe:.1f}x 估值偏高 (定價已反映未來樂觀預期)")

        # 前瞻動態本益比 (Forward PE) 與 PEG 比率 (Forward Consensus)
        forward_pe = data.get("forward_pe")
        peg_ratio = data.get("peg_ratio")
        if forward_pe and forward_pe > 0:
            if forward_pe < 22:
                score += 15
                signals.append(f"預估 Forward PE 僅 {forward_pe:.1f}x (實質未來評價處於合理偏低區間)")
            elif forward_pe > 50 and not is_turnaround_breakout:
                score -= 5

        if peg_ratio and 0 < peg_ratio < 1.0:
            score += 10
            signals.append(f"本益成長比 PEG {peg_ratio:.2f} < 1.0 (具備高性價比之實質成長低估)")

        if dy and dy >= 4.0:
            score += 10
            signals.append(f"現金殖利率達 {dy:.1f}% 具備下檔股息防守保護")

        return max(0.0, min(100.0, score)), signals

    def _evaluate_turnover_strategy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        price = data.get("price", 0.0)
        ma5 = data.get("ma5") or price
        ma20 = data.get("ma20") or price
        high_52w = data.get("high_52w", price)
        pct_change = data.get("pct_change", 0.0)

        turnover = data.get("turnover", 0.0)
        turnover_ma5 = data.get("turnover_ma5", turnover) or 1.0
        turnover_ratio = data.get("turnover_ratio", 1.0)
        turnover_ma5_slope = data.get("turnover_ma5_slope", 0.0)
        price_ma5_slope = data.get("price_ma5_slope", 0.0)

        # 1. 爆量出貨 (防守停損 🔴)
        if (pct_change <= -1.5 or price < ma5) and turnover_ratio >= 1.3:
            return {
                "strategy_code": "heavy_dump",
                "strategy_name": "爆量出貨 🔴",
                "badge_color": "rose",
                "score_modifier": -15,
                "signal": f"⚠️ 成交總值爆量下殺 (金額量比 {turnover_ratio}x，提防主力出貨)",
                "action_tip": "大資金獲利了結或殺盤，籌碼結構轉弱，應嚴格執行停損防守",
                "turnover_display": data.get("turnover_display", ""),
                "turnover_short": data.get("turnover_short", ""),
                "turnover_ma5_short": data.get("turnover_ma5_short", ""),
                "turnover_ratio": turnover_ratio
            }

        # 2. 強勢主升 (追多訊號 🟢)
        if price >= ma5 and price_ma5_slope >= 0 and turnover >= turnover_ma5 and turnover_ma5_slope >= 0:
            return {
                "strategy_code": "strong_bull",
                "strategy_name": "強勢主升 🟢",
                "badge_color": "emerald",
                "score_modifier": 10,
                "signal": f"✓ 成交總值突破5MA (金額量比 {turnover_ratio}x，價量齊揚)",
                "action_tip": "主力大單積極推進，趨勢延續性強，可順勢持有或分批加碼",
                "turnover_display": data.get("turnover_display", ""),
                "turnover_short": data.get("turnover_short", ""),
                "turnover_ma5_short": data.get("turnover_ma5_short", ""),
                "turnover_ratio": turnover_ratio
            }

        # 3. 動能衰竭 (逢高減碼 🟠)
        if (price >= ma5 or price >= high_52w * 0.95) and (turnover < turnover_ma5 or turnover_ma5_slope < 0):
            return {
                "strategy_code": "momentum_decay",
                "strategy_name": "動能衰竭 🟠",
                "badge_color": "amber",
                "score_modifier": -8,
                "signal": f"⚠️ 高檔成交總值萎縮 (金額量比 {turnover_ratio}x，量價背離)",
                "action_tip": "實質大資金買盤追價遞減，多單應調緊移動停利點",
                "turnover_display": data.get("turnover_display", ""),
                "turnover_short": data.get("turnover_short", ""),
                "turnover_ma5_short": data.get("turnover_ma5_short", ""),
                "turnover_ratio": turnover_ratio
            }

        # 4. 量縮築底 (潛伏觀察 🟡)
        if abs(price - ma20) / max(1.0, ma20) <= 0.05 and turnover < turnover_ma5:
            return {
                "strategy_code": "consolidation_bottom",
                "strategy_name": "量縮築底 🟡",
                "badge_color": "yellow",
                "score_modifier": 0,
                "signal": f"✓ 成交總值量縮 (金額量比 {turnover_ratio}x，籌碼沉澱整理)",
                "action_tip": "賣壓減輕籌碼沉澱，靜待成交總值帶量穿越 5MA 作為右側進場點",
                "turnover_display": data.get("turnover_display", ""),
                "turnover_short": data.get("turnover_short", ""),
                "turnover_ma5_short": data.get("turnover_ma5_short", ""),
                "turnover_ratio": turnover_ratio
            }

        # 5. 常態整理 ⚪
        return {
            "strategy_code": "normal",
            "strategy_name": "常態整理 ⚪",
            "badge_color": "gray",
            "score_modifier": 0,
            "signal": f"成交總值維持常態 (金額量比 {turnover_ratio}x)",
            "action_tip": "維持既定區間操作原則",
            "turnover_display": data.get("turnover_display", ""),
            "turnover_short": data.get("turnover_short", ""),
            "turnover_ma5_short": data.get("turnover_ma5_short", ""),
            "turnover_ratio": turnover_ratio
        }

    def _calculate_price_levels(self, stock_data: Dict[str, Any], score: float) -> Dict[str, Any]:
        price = _safe_float(stock_data.get("price"), 0.0)
        if price <= 0:
            return self._build_empty_levels(stock_data)
        atr = _safe_float(stock_data.get("atr14"), price * 0.02)
        if atr <= 0:
            atr = price * 0.02

        ma20 = _safe_float(stock_data.get("ma20"), price)
        ma60 = _safe_float(stock_data.get("ma60"), price * 0.95)
        bb_upper = _safe_float(stock_data.get("bb_upper"), price + 2 * atr)
        high_52w = _safe_float(stock_data.get("high_52w"), price * 1.15)

        s1 = round(max(min(price, ma20), price - 1.2 * atr), 2)
        s2 = round(max(min(s1, ma60), price - 2.5 * atr), 2)
        if s2 >= s1:
            s2 = round(s1 - 1.5 * atr, 2)

        r1 = round(min(max(price, bb_upper), price + 1.5 * atr), 2)
        r2 = round(max(r1 + 1.2 * atr, high_52w if high_52w > price else price + 2.5 * atr), 2)
        if r1 <= price:
            r1 = round(price + 1.2 * atr, 2)
        if r2 <= r1:
            r2 = round(r1 + 1.5 * atr, 2)

        sl = round(min(s1 * 0.985, price - 1.2 * atr), 2)
        if sl >= price:
            sl = round(price - 1.2 * atr, 2)

        tp = round(r1, 2)
        if tp <= price:
            tp = round(price + 2.0 * atr, 2)

        entry_low = round(min(s1, price * 0.99), 2)
        entry_high = round(max(price, s1 * 1.01), 2)

        potential_profit = tp - price
        potential_risk = price - sl
        rr_ratio = round(potential_profit / potential_risk, 2) if potential_risk > 0 else 1.0

        # 雙軌分級執行策略
        tier = stock_data.get("tier", "TIER_2_MOMENTUM")
        tier_label = stock_data.get("tier_label", "⚡ 戰術動量")
        moat_badge = stock_data.get("moat_badge", "⚡ 戰術動量")
        knife_pause = stock_data.get("knife_pause", False)
        pyramid_buys = stock_data.get("pyramid_buys", [])

        if tier == "TIER_1_CORE":
            # 特許核心：左側金字塔分批佈局
            if knife_pause:
                strategy_tip = "👑 波克夏核心資產 (豁免 ATR 停損) | ⚠️ 落刀暫停：Squeeze 暴跌破位開花中，暫停掛單接刀，待量縮止跌後再啟動金字塔加碼。"
                sl_display = "⚠️ 落刀暫停 (待止跌)"
            else:
                if pyramid_buys:
                    p1 = pyramid_buys[0].get("price", round(price * 0.9, 1))
                    p2 = pyramid_buys[1].get("price", round(price * 0.8, 1)) if len(pyramid_buys) > 1 else round(price * 0.8, 1)
                    p3 = pyramid_buys[2].get("price", round(price * 0.7, 1)) if len(pyramid_buys) > 2 else round(price * 0.7, 1)
                    strategy_tip = f"👑 波克夏核心資產 (豁免 ATR 停損) | 採左側金字塔分批佈局 (上限20%): -10% (${p1}, 5%), -20% (${p2}, 7%), -30% (${p3}, 8%)。"
                else:
                    strategy_tip = "👑 波克夏核心資產 (豁免 ATR 停損) | 採左側越跌越買金字塔佈局 (上限20%)，以 Kill Criteria 為唯一清倉標準。"
                sl_display = "🛡️ 豁免硬停損 (論文控管)"
            sl_val = round(price * 0.70, 2)
        else:
            # 戰術動量：標準 ATR 止損與右側動量
            if score >= 75:
                strategy_tip = f"建議在進場區 ${entry_low} ~ ${entry_high} 分批佈局，跌破 ${sl} 嚴格止損。"
            elif score >= 60:
                strategy_tip = f"多頭震盪格局，拉回測試支撐 ${s1} 守穩可低接，目標前高 ${r1}。"
            elif score <= 35:
                strategy_tip = f"走勢偏弱，反彈遇壓力 ${r1} 建議減碼防守，不宜盲目抄底。"
            else:
                strategy_tip = f"區間整理格局，箱型操作於 ${s1} 至 ${r1} 區間，等待放量突破。"
            sl_display = f"${sl:.2f}"
            sl_val = sl

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
            "stop_loss": sl_val,
            "stop_loss_display": sl_display,
            "risk_reward_ratio": rr_ratio,
            "strategy_tip": strategy_tip,
            "atr": round(atr, 2),
            "tier": tier,
            "tier_label": tier_label,
            "moat_badge": moat_badge,
            "knife_pause": knife_pause,
            "pyramid_buys": pyramid_buys
        }

    def _determine_rating(self, score: float) -> Tuple[str, str, str]:
        if score >= self.tiers["strong_bull"]:
            return "強力做多", "strong_bull", "emerald"
        elif score >= self.tiers["lean_bull"]:
            return "偏多震盪", "lean_bull", "green"
        elif score >= self.tiers["neutral"]:
            return "中立觀望", "neutral", "yellow"
        elif score >= self.tiers["lean_bear"]:
            return "偏空防守", "lean_bear", "rose"
        else:
            return "避險做空", "strong_bear", "rose"

    def _build_empty_levels(self, stock_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        st = stock_data or {}
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
            "stop_loss_display": "-",
            "risk_reward_ratio": 1.0,
            "strategy_tip": "數據暫時無法計算點位",
            "atr": 0.0,
            "tier": st.get("tier", "TIER_2_MOMENTUM"),
            "tier_label": st.get("tier_label", "⚡ 戰術動量"),
            "moat_badge": st.get("moat_badge", "⚡ 戰術動量"),
            "knife_pause": False,
            "pyramid_buys": []
        }

    def _build_empty_evaluation(self, stock_data: Dict[str, Any]) -> EquityEvaluationResult:
        sym = stock_data.get("symbol", "")
        empty_score_info = {
            "score": 50.0,
            "regime_label": "常態平衡體制",
            "rating": "暫無報價",
            "rating_code": "neutral",
            "badge_color": "gray",
            "tech_score": 50.0,
            "flow_score": 50.0,
            "fund_score": 50.0,
            "turnover_strategy": {
                "strategy_code": "normal",
                "strategy_name": "常態整理 ⚪",
                "badge_color": "gray",
                "score_modifier": 0,
                "signal": "",
                "turnover_display": "-",
                "turnover_short": "-",
                "turnover_ma5_short": "-",
                "turnover_ratio": 1.0
            },
            "signals": ["數據不足，維持中立觀望"]
        }
        empty_levels = self._build_empty_levels(stock_data)
        return EquityEvaluationResult(
            score=50.0,
            rating="暫無報價",
            rating_code="neutral",
            badge_color="gray",
            regime_label="常態平衡體制",
            tech_score=50.0,
            flow_score=50.0,
            fund_score=50.0,
            score_info=empty_score_info,
            price_levels=empty_levels
        )
