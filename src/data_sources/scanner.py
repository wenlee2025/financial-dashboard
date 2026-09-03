import logging
from typing import Any, Dict, List, Optional
from .tw_market import TWMarketFetcher
from .us_market import USMarketFetcher

logger = logging.getLogger(__name__)

from .market_gateway import MarketGateway

class MarketScanner:
    """[相容轉發器] 全市場動態焦點強勢股 / 法人買超股掃描器 (底層代理至深模組 MarketGateway)"""

    def __init__(self, tw_fetcher: TWMarketFetcher, us_fetcher: USMarketFetcher, scanner_settings: Dict[str, Any]):
        self.tw_fetcher = tw_fetcher
        self.us_fetcher = us_fetcher
        self.settings = scanner_settings
        self.gateway = MarketGateway(tw_fetcher=tw_fetcher, us_fetcher=us_fetcher)

    def scan_tw_focus_stocks(self, existing_symbols: List[str]) -> List[Dict[str, Any]]:
        """掃描台股焦點標的 (代理至 MarketGateway)"""
        top_n = self.settings.get("top_n_tw", 3)
        min_buy_lots = self.settings.get("tw_min_foreign_trust_buy_lots", 500)
        res = self.gateway.scan_focus_stocks(existing_symbols, top_n=top_n, min_buy_lots=min_buy_lots)
        if not res:
            return self._scan_tw_fallback(existing_symbols, top_n)
        logger.info(f"台股籌碼掃描出 {len(res)} 檔焦點股: {[c['symbol'] for c in res]}")
        return res

    def _scan_tw_fallback(self, existing_symbols: List[str], top_n: int) -> List[Dict[str, Any]]:
        """台股備用候選池 (熱門產業龍頭)"""
        universe = [
            {"symbol": "3035", "name": "智原", "sector": "ASIC IP"},
            {"symbol": "3443", "name": "創意", "sector": "ASIC IP"},
            {"symbol": "6669", "name": "緯穎", "sector": "AI 伺服器"},
            {"symbol": "3037", "name": "欣興", "sector": "ABF 載板"},
            {"symbol": "2376", "name": "技嘉", "sector": "AI 伺服器/主機板"},
            {"symbol": "3661", "name": "世芯-KY", "sector": "ASIC 設計"}
        ]
        clean_existing = [str(s).replace(".TW", "").replace(".TWO", "").strip() for s in existing_symbols]
        results = []
        for stock in universe:
            if stock["symbol"] not in clean_existing:
                results.append({
                    "symbol": stock["symbol"],
                    "name": stock["name"],
                    "reason": f"產業熱門焦點標的 ({stock['sector']})"
                })
                if len(results) >= top_n:
                    break
        return results

    def scan_us_focus_stocks(self, existing_symbols: List[str]) -> List[Dict[str, Any]]:
        """
        掃描美股動態焦點標的 (量增突破、動能成長股)
        """
        top_n = self.settings.get("top_n_us", 3)
        universe = [
            {"symbol": "AMD", "name": "AMD (超微)", "sector": "AI 晶片"},
            {"symbol": "AVGO", "name": "Broadcom (博通)", "sector": "AI 網路/客製晶片"},
            {"symbol": "META", "name": "Meta (臉書)", "sector": "社群 / 開源 AI"},
            {"symbol": "AMZN", "name": "Amazon (亞馬遜)", "sector": "AWS 雲端 / 電商"},
            {"symbol": "GOOGL", "name": "Alphabet (Google)", "sector": "搜尋 / Gemini AI"},
            {"symbol": "ARM", "name": "ARM Holdings", "sector": "晶片架構 IP"},
            {"symbol": "COIN", "name": "Coinbase", "sector": "加密貨幣交易所"},
            {"symbol": "CRWD", "name": "CrowdStrike", "sector": "雲端資安"}
        ]

        clean_existing = [str(s).strip().upper() for s in existing_symbols]
        candidates = []

        for stock in universe:
            sym = stock["symbol"]
            if sym in clean_existing:
                continue

            try:
                data = self.us_fetcher.get_stock_data(sym, name=stock["name"], period="1mo")
                if data and data.get("price", 0) > 0:
                    pct = data.get("pct_change", 0.0)
                    vol_ratio = data.get("volume_ratio", 1.0)
                    ma20 = data.get("ma20")
                    price = data.get("price", 0.0)

                    # 動能評分: 漲跌幅 + 量比 + 是否站上 20MA
                    score = pct * 1.5 + (vol_ratio - 1.0) * 5.0
                    if ma20 and price > ma20:
                        score += 5.0

                    candidates.append({
                        "symbol": sym,
                        "name": stock["name"],
                        "data": data,
                        "score": score,
                        "reason": f"單日變動 {pct:+.2f}%，量比 {vol_ratio:.1f}x，{stock['sector']}"
                    })
            except Exception as e:
                logger.debug(f"美股候選掃描略過 {sym}: {e}")

        # 依動能分數排序
        candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_candidates = candidates[:top_n]
        return [{
            "symbol": c["symbol"],
            "name": c["name"],
            "reason": c["reason"]
        } for c in top_candidates]
