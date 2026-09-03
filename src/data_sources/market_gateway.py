from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional
from .tw_market import TWMarketFetcher
from .us_market import USMarketFetcher
from .macro_sentiment import MacroSentimentFetcher

logger = logging.getLogger(__name__)

@dataclass
class StockMarketBundle:
    """單檔標的之全維度市場數據包 (行情 + 籌碼 + 營收 + 護城河分級)"""
    symbol: str
    name: str
    market: str
    stock_data: Dict[str, Any]
    inst_data: Optional[Dict[str, Any]] = None
    revenue_data: Optional[Dict[str, Any]] = None
    tier: str = "TIER_2_MOMENTUM"
    tier_label: str = "⚡ 戰術動量"
    moat_badge: str = "⚡ 戰術動量"
    berkshire_score: Optional[float] = None
    knife_pause: bool = False
    veto_triggered: bool = False
    pyramid_buys: List[Dict[str, Any]] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "market": self.market,
            "stock_data": self.stock_data,
            "institutional": self.inst_data,
            "revenue": self.revenue_data,
            "tier": self.tier,
            "tier_label": self.tier_label,
            "moat_badge": self.moat_badge,
            "berkshire_score": self.berkshire_score,
            "knife_pause": self.knife_pause,
            "veto_triggered": self.veto_triggered,
            "pyramid_buys": self.pyramid_buys,
            "note": self.note
        }


class MarketGateway:
    """
    深模組：全市場統一數據閘道 (Unified Market Data Gateway)
    
    【深模組介面 (Deep Seam)】
    1. fetch_universe_bundles(items, date_str): 一站式獲取全市場標的完整行情、籌碼與營收包。
    2. get_macro_overview(): 獲取宏觀指數、Fear & Greed、台指期淨空單防護與 ADR 溢價率。
    3. scan_focus_stocks(): 掃描法人大買之動態焦點股。
    
    【接縫後隱藏之內部實作】
    - 台美市場代碼路由 (TWSE vs TPEx OTC .TWO vs US)
    - 多執行緒並行批次行情採集
    - TWSE T86 三大法人買賣超全市場查表與關聯
    - 月營收年增率 (Revenue YoY) 查詢與關聯
    - 波克夏分級中繼資料自動組裝
    """

    def __init__(
        self,
        tw_fetcher: Optional[TWMarketFetcher] = None,
        us_fetcher: Optional[USMarketFetcher] = None,
        macro_fetcher: Optional[MacroSentimentFetcher] = None,
        finmind_token: Optional[str] = None
    ):
        self.tw_fetcher = tw_fetcher or TWMarketFetcher(finmind_token=finmind_token)
        self.us_fetcher = us_fetcher or USMarketFetcher()
        self.macro_fetcher = macro_fetcher or MacroSentimentFetcher()

    def fetch_universe_bundles(
        self,
        items: List[Dict[str, Any]],
        date_str: str
    ) -> Dict[str, StockMarketBundle]:
        """
        批次並行拉取全市場標的數據包
        """
        if not items:
            return {}

        # 1. 內部自動劃分台美股
        tw_items = [s for s in items if s.get("market") == "TW" or str(s["symbol"]).isdigit() or "." in str(s["symbol"])]
        us_items = [s for s in items if s not in tw_items]

        # 2. 並行批次採集行情
        tw_stock_data_map = self.tw_fetcher.get_batch_stock_data(tw_items) if tw_items else {}
        us_stock_data_map = self.us_fetcher.get_batch_stock_data(us_items) if us_items else {}

        # 3. 獲取 TWSE 全市場法人籌碼 T86 表
        tw_inst_all = self.tw_fetcher.get_twse_institutional_data(date_str) if tw_items else {}

        bundles: Dict[str, StockMarketBundle] = {}

        for item in items:
            sym = str(item["symbol"]).strip()
            name = item.get("name") or sym
            market = item.get("market", "TW" if sym.isdigit() or "." in sym else "US")

            if market == "TW":
                stock_data = tw_stock_data_map.get(sym) or self.tw_fetcher.get_stock_data(sym, name=name)
                clean_code = sym.replace(".TW", "").replace(".TWO", "")
                inst_data = tw_inst_all.get(clean_code)
                revenue_data = self.tw_fetcher.get_monthly_revenue_yoy(clean_code)
            else:
                stock_data = us_stock_data_map.get(sym) or self.us_fetcher.get_stock_data(sym, name=name)
                inst_data = None
                revenue_data = None

            # 注入波克夏雙軌屬性
            tier = item.get("tier", "TIER_2_MOMENTUM")
            tier_label = item.get("tier_label", "⚡ 戰術動量")
            moat_badge = item.get("moat_badge", "⚡ 戰術動量")
            berkshire_score = item.get("berkshire_score")
            knife_pause = item.get("knife_pause", False)
            veto_triggered = item.get("veto_triggered", False)
            pyramid_buys = item.get("pyramid_buys", [])
            note = item.get("note", item.get("reason", ""))

            stock_data["tier"] = tier
            stock_data["tier_label"] = tier_label
            stock_data["moat_badge"] = moat_badge
            stock_data["berkshire_score"] = berkshire_score
            stock_data["knife_pause"] = knife_pause
            stock_data["veto_triggered"] = veto_triggered
            stock_data["pyramid_buys"] = pyramid_buys

            bundle = StockMarketBundle(
                symbol=sym,
                name=stock_data.get("name", name),
                market=market,
                stock_data=stock_data,
                inst_data=inst_data,
                revenue_data=revenue_data,
                tier=tier,
                tier_label=tier_label,
                moat_badge=moat_badge,
                berkshire_score=berkshire_score,
                knife_pause=knife_pause,
                veto_triggered=veto_triggered,
                pyramid_buys=pyramid_buys,
                note=note
            )
            bundles[sym] = bundle

        return bundles

    def scan_focus_stocks(
        self,
        existing_symbols: List[str],
        top_n: int = 3,
        min_buy_lots: int = 500
    ) -> List[Dict[str, Any]]:
        """
        掃描三大法人大舉合力買超之焦點個股
        """
        try:
            inst_data = self.tw_fetcher.get_twse_institutional_data()
            if not inst_data:
                return []

            candidates = []
            clean_existing = [str(s).replace(".TW", "").replace(".TWO", "").strip() for s in existing_symbols]

            for code, data in inst_data.items():
                if len(code) != 4 or not code.isdigit() or code.startswith(("00", "01", "02", "08")):
                    continue
                if code in clean_existing:
                    continue

                foreign = data.get("foreign_lots", 0)
                trust = data.get("trust_lots", 0)
                combined = foreign + trust

                if combined >= min_buy_lots:
                    candidates.append({
                        "symbol": code,
                        "name": data.get("name", code),
                        "foreign_lots": foreign,
                        "trust_lots": trust,
                        "total_lots": data.get("total_lots", 0),
                        "combined_lots": combined,
                        "reason": f"外資買超 {foreign:,d} 張，投信買超 {trust:,d} 張 (合計買超 {combined:,d} 張)"
                    })

            candidates.sort(key=lambda x: x["combined_lots"], reverse=True)
            return candidates[:top_n]
        except Exception as e:
            logger.warning(f"市場焦點股掃描異常: {e}")
            return []

    def get_macro_sentiment_bundle(self, adr_mappings: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        一次性獲取宏觀情緒、VIX、台指期淨空單防護與 ADR 溢價率
        """
        macro = self.macro_fetcher.get_macro_overview()
        fear_and_greed = self.macro_fetcher.get_fear_and_greed_index()
        tx_futures = self.macro_fetcher.get_tx_futures_net_oi()

        usdtwd_rate = macro.get("usdtwd", {}).get("value", 32.5)
        adr_premiums = []
        if adr_mappings:
            adr_premiums = self.macro_fetcher.calculate_adr_premium(adr_mappings, usdtwd_rate)

        return {
            "fear_and_greed": fear_and_greed,
            "macro": macro,
            "tx_futures": tx_futures,
            "adr_premiums": adr_premiums
        }
