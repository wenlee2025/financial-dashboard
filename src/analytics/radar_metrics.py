import math
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

def _sanitize_score(val: Any, default: float = 50.0) -> float:
    """Zero-NaN 嚴格保證：確保數值在 0.0 至 100.0 之間且絕不輸出 NaN 或 Inf"""
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return round(max(0.0, min(100.0, f)), 1)
    except (ValueError, TypeError):
        return default

@dataclass
class StockRadarMetrics:
    """單檔標的 6 大維度雷達圖評分實體 (Zero-NaN 嚴格保證)"""
    symbol: str
    name: str
    tier: str               # "TIER_1_CORE" 或 "TIER_2_MOMENTUM"
    technicals: float       # 1. 技術動能 (0-100)
    flows: float            # 2. 主力籌碼 (0-100)
    fundamentals: float     # 3. 基本面前瞻 (0-100)
    moat: float             # 4. 波克夏護城河 (0-100)
    defense: float          # 5. 風險防禦 (0-100)
    composite: float        # 6. 多空綜合評分 (0-100)
    strengths: List[str]    # 優勢亮點標籤
    weaknesses: List[str]   # 風險待觀察標籤
    regime: str = "Normal"  # 當前市場體制

    def __post_init__(self):
        self.technicals = _sanitize_score(self.technicals)
        self.flows = _sanitize_score(self.flows)
        self.fundamentals = _sanitize_score(self.fundamentals)
        self.moat = _sanitize_score(self.moat)
        self.defense = _sanitize_score(self.defense)
        self.composite = _sanitize_score(self.composite)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_radar_series(self) -> Dict[str, Any]:
        """供前端 ECharts / Chart.js 直接消費之數組"""
        return {
            "name": f"{self.symbol} {self.name}",
            "symbol": self.symbol,
            "tier": self.tier,
            "value": [
                self.technicals,
                self.flows,
                self.fundamentals,
                self.moat,
                self.defense,
                self.composite
            ]
        }

class RadarMetricsCalculator:
    """
    深模組：六大維度多股雷達圖評分計算器
    
    封裝技術動能、主力籌碼、基本價值、波克夏護城河與下檔防守的量化標準化演算法，
    並依市場體制自適應調節綜合評分權重。
    """

    RADAR_DIMENSIONS = [
        {"name": "技術動能", "max": 100, "key": "technicals"},
        {"name": "主力籌碼", "max": 100, "key": "flows"},
        {"name": "基本面前瞻", "max": 100, "key": "fundamentals"},
        {"name": "波克夏護城河", "max": 100, "key": "moat"},
        {"name": "風險防禦", "max": 100, "key": "defense"},
        {"name": "多空綜合評分", "max": 100, "key": "composite"}
    ]

    @classmethod
    def compute_stock_radar(
        cls,
        stock_item: Dict[str, Any],
        macro_sentiment: Optional[Dict[str, Any]] = None
    ) -> StockRadarMetrics:
        """計算單檔標的之 6 大維度評分"""
        symbol = str(stock_item.get("symbol", ""))
        name = str(stock_item.get("name", symbol))
        tier = str(stock_item.get("tier", "TIER_2_MOMENTUM"))
        stock_data = stock_item.get("stock_data", {})
        score_info = stock_item.get("score_info", {})
        price_levels = stock_item.get("price_levels", {})
        
        # 判斷市場體制 (Panic / Momentum / Normal)
        fg_score = 50.0
        vix_val = 18.0
        foreign_net_oi = -10000
        if macro_sentiment:
            fg_score = float(macro_sentiment.get("fear_and_greed", {}).get("score", 50.0) or 50.0)
            vix_val = float(macro_sentiment.get("macro", {}).get("vix", {}).get("value", 18.0) or 18.0)
            tx = macro_sentiment.get("tx_futures", {})
            foreign_net_oi = int(tx.get("foreign_net_oi", -10000) or -10000)

        if fg_score < 30.0 or vix_val > 22.0:
            regime = "Panic"
        elif fg_score > 60.0 and vix_val < 16.0:
            regime = "Momentum"
        else:
            regime = "Normal"

        strengths: List[str] = []
        weaknesses: List[str] = []

        # ==========================================
        # 1. 技術動能 (Technicals, 0-100)
        # ==========================================
        # 因子: MA多頭排列 (35%), 成交總值量比動能 (30%), RSI/KD (20%), 多週期共振 (15%)
        s_ma = 50.0
        close = float(stock_data.get("price", 0.0) or 0.0)
        ma5 = float(stock_data.get("ma5", 0.0) or 0.0)
        ma20 = float(stock_data.get("ma20", 0.0) or 0.0)
        ma60 = float(stock_data.get("ma60", 0.0) or 0.0)

        if close > 0 and ma5 > 0 and ma20 > 0 and ma60 > 0:
            if close > ma5 > ma20 > ma60:
                s_ma = 95.0
                strengths.append("均線完美多頭排列")
            elif close > ma20 > ma60:
                s_ma = 80.0
            elif close > ma60:
                s_ma = 60.0
            else:
                s_ma = 35.0
                weaknesses.append("跌破季線生命線")

        # 成交金額量比 5MA
        turnover_ratio = float(stock_data.get("turnover_ratio", 1.0) or 1.0)
        pct_change = float(stock_data.get("pct_change", 0.0) or 0.0)
        s_turnover = 50.0
        if 1.1 <= turnover_ratio <= 2.5 and pct_change >= 0:
            s_turnover = 95.0
            strengths.append("健康換手放量主升")
        elif turnover_ratio > 3.0:
            s_turnover = 45.0
            weaknesses.append("單日爆量注意出貨")
        elif turnover_ratio < 0.7:
            s_turnover = 65.0

        # RSI 動能
        rsi = float(stock_data.get("rsi", 50.0) or 50.0)
        s_rsi = 50.0
        if 55.0 <= rsi <= 72.0:
            s_rsi = 90.0
        elif rsi > 80.0:
            s_rsi = 55.0
            weaknesses.append("短線超買過熱")
        elif rsi < 35.0:
            s_rsi = 40.0

        s_resonance = 85.0 if s_ma >= 80.0 and s_turnover >= 65.0 else 50.0
        tech_score = 0.35 * s_ma + 0.30 * s_turnover + 0.20 * s_rsi + 0.15 * s_resonance

        # ==========================================
        # 2. 主力籌碼 (Smart Money / Flows, 0-100)
        # ==========================================
        foreign_lots = float(stock_data.get("foreign_buy_lots", 0.0) or 0.0)
        trust_lots = float(stock_data.get("trust_buy_lots", 0.0) or 0.0)
        streak_days = int(stock_data.get("inst_streak_days", 0) or 0)
        
        s_inst = 50.0
        if foreign_lots > 0 and trust_lots > 0:
            s_inst = 95.0
            strengths.append("土洋法人同步大買")
        elif trust_lots > 0:
            s_inst = 80.0
            strengths.append("投信實質鎖碼")
        elif foreign_lots < 0 and trust_lots < 0:
            s_inst = 25.0
            weaknesses.append("三大法人同步出貨")
        elif foreign_lots < 0:
            s_inst = 45.0

        s_streak = 50.0
        if streak_days >= 5:
            s_streak = 95.0
            strengths.append(f"法人連買 {streak_days} 日")
        elif streak_days >= 3:
            s_streak = 80.0
        elif streak_days <= -3:
            s_streak = 30.0

        s_holders = 65.0 if s_inst >= 70.0 else 50.0
        flow_score = 0.40 * s_inst + 0.30 * s_streak + 0.30 * s_holders

        # ==========================================
        # 3. 基本面前瞻 (Fundamentals, 0-100)
        # ==========================================
        rev_yoy = float(stock_data.get("rev_yoy", 0.0) or 0.0)
        s_rev = 50.0
        if rev_yoy >= 25.0:
            s_rev = 95.0
            strengths.append(f"月營收高速增長 ({rev_yoy:.1f}%)")
        elif rev_yoy >= 10.0:
            s_rev = 80.0
        elif rev_yoy < 0.0:
            s_rev = 35.0
            weaknesses.append(f"月營收年減衰退 ({rev_yoy:.1f}%)")

        peg = float(stock_data.get("peg_ratio", 1.5) or 1.5)
        s_peg = 50.0
        if 0.1 <= peg < 1.0:
            s_peg = 95.0
            strengths.append(f"高成長性價比 (PEG={peg:.2f})")
        elif 1.0 <= peg <= 1.8:
            s_peg = 75.0
        elif peg > 2.5:
            s_peg = 40.0

        s_margin = 70.0 if s_rev >= 70.0 else 50.0
        fund_score = 0.40 * s_rev + 0.35 * s_margin + 0.25 * s_peg

        # ==========================================
        # 4. 波克夏護城河 (Moat & Quality, 0-100)
        # ==========================================
        # 特許核心 95 分基底 vs 戰術動量 55 分基底
        berkshire_score = float(stock_item.get("berkshire_score", 4.0) or 4.0)
        if tier == "TIER_1_CORE":
            s_tier = 95.0
            strengths.append("👑 波克夏特許核心資產")
        else:
            s_tier = 60.0

        s_moat_quality = _sanitize_score((berkshire_score / 5.0) * 100.0, default=65.0)
        moat_score = 0.50 * s_tier + 0.50 * s_moat_quality

        # ==========================================
        # 5. 風險防禦 (Defense & Risk Buffer, 0-100)
        # ==========================================
        stop_loss = float(price_levels.get("stop_loss", 0.0) or 0.0)
        s_buffer = 60.0
        if close > 0 and stop_loss > 0 and close >= stop_loss:
            buffer_pct = ((close - stop_loss) / close) * 100.0
            if 3.5 <= buffer_pct <= 7.5:
                s_buffer = 95.0
                strengths.append("停損空間緊實防守嚴密")
            elif buffer_pct < 2.0:
                s_buffer = 35.0
                weaknesses.append("緊貼停損線隨時觸發")
            else:
                s_buffer = 65.0
        elif close > 0 and stop_loss > 0 and close < stop_loss:
            s_buffer = 20.0
            weaknesses.append("🚨 已跌破停損防守價")

        volatility = float(price_levels.get("volatility_20d", 25.0) or 25.0)
        s_vol = 85.0 if volatility <= 22.0 else (65.0 if volatility <= 35.0 else 40.0)

        # 台指期外資淨空單避險係數
        s_futures = 90.0
        if foreign_net_oi < -35000:
            s_futures = 40.0
            weaknesses.append("外資期貨淨空單破警戒壓盤")
        elif foreign_net_oi < -25000:
            s_futures = 65.0

        defense_score = 0.40 * s_buffer + 0.35 * s_vol + 0.25 * s_futures

        # ==========================================
        # 6. 多空綜合評分 (Composite Score, 0-100)
        # ==========================================
        raw_quant = float(score_info.get("score", 0.0) or 0.0)
        if raw_quant > 0:
            # 結合現有成熟評分與體制加權雷達得分
            composite_score = 0.50 * raw_quant + 0.50 * (
                0.25 * tech_score + 0.25 * flow_score + 0.20 * fund_score + 0.15 * moat_score + 0.15 * defense_score
            )
        else:
            if regime == "Panic":
                composite_score = 0.15 * tech_score + 0.35 * flow_score + 0.15 * fund_score + 0.15 * moat_score + 0.20 * defense_score
            elif regime == "Momentum":
                composite_score = 0.35 * tech_score + 0.25 * flow_score + 0.20 * fund_score + 0.10 * moat_score + 0.10 * defense_score
            else:
                composite_score = 0.25 * tech_score + 0.25 * flow_score + 0.20 * fund_score + 0.15 * moat_score + 0.15 * defense_score

        return StockRadarMetrics(
            symbol=symbol,
            name=name,
            tier=tier,
            technicals=tech_score,
            flows=flow_score,
            fundamentals=fund_score,
            moat=moat_score,
            defense=defense_score,
            composite=composite_score,
            strengths=strengths[:3],
            weaknesses=weaknesses[:3],
            regime=regime
        )

    @classmethod
    def compute_universe_radar(
        cls,
        analyzed_stocks: List[Dict[str, Any]],
        macro_sentiment: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """批量計算全市場股票之多股雷達數據，回傳可供前端 JSON 序列化之結構"""
        stock_radars: List[StockRadarMetrics] = []
        for stock_item in analyzed_stocks:
            radar = cls.compute_stock_radar(stock_item, macro_sentiment)
            stock_radars.append(radar)

        return {
            "dimensions": cls.RADAR_DIMENSIONS,
            "stocks": [r.to_dict() for r in stock_radars],
            "series": [r.to_radar_series() for r in stock_radars]
        }
