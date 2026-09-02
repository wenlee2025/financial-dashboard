import logging
from typing import Any, Dict, List, Optional
from .tw_market import TWMarketFetcher
from .us_market import USMarketFetcher

logger = logging.getLogger(__name__)

class MarketScanner:
    """全市場動態焦點強勢股 / 法人買超股掃描器"""

    def __init__(self, tw_fetcher: TWMarketFetcher, us_fetcher: USMarketFetcher, scanner_settings: Dict[str, Any]):
        self.tw_fetcher = tw_fetcher
        self.us_fetcher = us_fetcher
        self.settings = scanner_settings

    def scan_tw_focus_stocks(self, existing_symbols: List[str]) -> List[Dict[str, Any]]:
        """
        掃描台股焦點標的：
        1. 外資 + 投信同步買超張數最多
        2. 排除已在自選清單中的標的
        3. 取前 top_n 檔
        """
        top_n = self.settings.get("top_n_tw", 3)
        min_buy_lots = self.settings.get("tw_min_foreign_trust_buy_lots", 500)
        
        try:
            inst_data = self.tw_fetcher.get_twse_institutional_data()
            if not inst_data:
                logger.warning("未能取得法人籌碼數據，改用精選熱門池掃描")
                return self._scan_tw_fallback(existing_symbols, top_n)

            candidates = []
            clean_existing = [str(s).replace(".TW", "").replace(".TWO", "").strip() for s in existing_symbols]

            for code, data in inst_data.items():
                # 過濾權證、ETF (代碼通常非 4 碼或以 00/01/02 開頭)
                if len(code) != 4 or not code.isdigit() or code.startswith(("00", "01", "02", "08")):
                    continue
                if code in clean_existing:
                    continue

                foreign = data.get("foreign_lots", 0)
                trust = data.get("trust_lots", 0)
                combined = foreign + trust

                # 外資與投信皆為正，或合計大幅買超
                if combined >= min_buy_lots:
                    candidates.append({
                        "symbol": code,
                        "name": data.get("name", code),
                        "foreign_lots": foreign,
                        "trust_lots": trust,
                        "total_lots": data.get("total_lots", 0),
                        "combined_lots": combined,
                        "reason": f"外資買超 {foreign} 張，投信買超 {trust} 張 (合計買超 {combined} 張)"
                    })

            # 按法人買超張數降序排序
            candidates.sort(key=lambda x: x["combined_lots"], reverse=True)
            top_candidates = candidates[:top_n]
            
            logger.info(f"台股籌碼掃描出 {len(top_candidates)} 檔焦點股: {[c['symbol'] for c in top_candidates]}")
            return top_candidates

        except Exception as e:
            logger.error(f"台股焦點掃描失敗: {e}")
            return self._scan_tw_fallback(existing_symbols, top_n)

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
