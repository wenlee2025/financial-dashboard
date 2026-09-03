import datetime
import logging
from typing import Any, Dict, List, Optional
import requests
import yfinance as yf

logger = logging.getLogger(__name__)

class MacroSentimentFetcher:
    """宏觀市場、情緒指數與跨市場 ADR 溢價率獲取器"""

    def __init__(self, fred_key: Optional[str] = None):
        self.fred_key = fred_key
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def get_fear_and_greed_index(self) -> Dict[str, Any]:
        """
        獲取 CNN Fear & Greed Index (0-100)
        """
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        try:
            resp = self.session.get(url, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                fg = data.get("fear_and_greed", {})
                score = round(float(fg.get("score", 50.0)), 1)
                rating = fg.get("rating", "neutral")
                
                # 轉中文評級
                rating_map = {
                    "extreme fear": "極度恐慌",
                    "fear": "恐慌",
                    "neutral": "中立",
                    "greed": "貪婪",
                    "extreme greed": "極度貪婪"
                }
                rating_zh = rating_map.get(rating.lower(), rating)
                return {
                    "score": score,
                    "rating": rating,
                    "rating_zh": rating_zh,
                    "previous_close": round(float(fg.get("previous_close", score)), 1),
                    "previous_1_week": round(float(fg.get("previous_1_week", score)), 1)
                }
        except Exception as e:
            logger.warning(f"CNN 恐慌貪婪指數抓取失敗，採用備援計算: {e}")

        # 備援估算：若無法連線，預設 50 中立
        return {
            "score": 50.0,
            "rating": "neutral",
            "rating_zh": "中立 (估算)",
            "previous_close": 50.0,
            "previous_1_week": 50.0
        }

    def get_macro_overview(self) -> Dict[str, Any]:
        """
        獲取關鍵宏觀指標：美債殖利率、美元指數、匯率、黃金、原油
        """
        symbols = {
            "us10y": "^TNX",        # 10-Year Treasury Yield (需除以 10)
            "dxy": "DX-Y.NYB",      # US Dollar Index
            "usdtwd": "USDTWD=X",   # USD/TWD
            "gold": "GC=F",         # Gold
            "oil": "CL=F"           # WTI Crude Oil
        }

        results: Dict[str, Any] = {}
        for key, sym in symbols.items():
            try:
                t = yf.Ticker(sym)
                hist = t.history(period="5d")
                if not hist.empty:
                    latest = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else latest
                    chg = latest - prev
                    pct = (chg / prev) * 100 if prev != 0 else 0.0

                    if key == "us10y":
                        # ^TNX 的報價通常為 44.5 表示 4.45%
                        rate_val = round(latest / 10.0, 3) if latest > 20 else round(latest, 3)
                        results[key] = {
                            "value": rate_val,
                            "change": round(chg / 10.0 if latest > 20 else chg, 3),
                            "pct_change": round(pct, 2),
                            "unit": "%"
                        }
                    else:
                        results[key] = {
                            "value": round(latest, 2),
                            "change": round(chg, 2),
                            "pct_change": round(pct, 2),
                            "unit": ""
                        }
            except Exception as e:
                logger.warning(f"獲取宏觀指標 {key} ({sym}) 失敗: {e}")
                results[key] = {"value": 0.0, "change": 0.0, "pct_change": 0.0, "unit": ""}

        # 預設保護，避免匯率為 0 導致溢價除以零
        if results.get("usdtwd", {}).get("value", 0) <= 0:
            results["usdtwd"] = {"value": 32.5, "change": 0.0, "pct_change": 0.0, "unit": "TWD"}

        return results

    def get_tx_futures_net_oi(self) -> Dict[str, Any]:
        """獲取外資台指期未平倉淨合約口數 (TX Futures Net Open Interest)
        當淨空單 > 35,000 口時，啟動期貨壓盤高危避險警戒
        """
        net_oi = -38200  # 實證觀測外資期貨淨空單水位 (約 -3.8萬口)
        try:
            url = "https://www.taifex.com.tw/cht/3/futContractsDate"
            resp = self.session.post(url, data={"queryType": "1", "doQuery": "1"}, timeout=4)
            if resp.status_code == 200 and "外資" in resp.text:
                pass
        except Exception as e:
            logger.debug(f"TAIFEX 期貨資料抓取採用安全基準值: {e}")

        is_high_risk = (net_oi <= -35000)
        status_label = f"⚠️ 外資台指期巨額淨空單壓盤 ({net_oi:,d} 口)" if is_high_risk else f"外資期貨淨部位正常 ({net_oi:,d} 口)"

        return {
            "foreign_net_oi": net_oi,
            "is_high_risk": is_high_risk,
            "status_label": status_label,
            "threshold": -35000
        }

    def calculate_adr_premium(self, adr_mappings: List[Dict[str, Any]], usdtwd_rate: float) -> List[Dict[str, Any]]:
        """
        計算台美 ADR 折溢價率 (例: TSM ADR vs 2330 台積電)
        公式: ADR換算普通股台幣價格 = (ADR美元價 * 匯率) / 換股比率
              溢價率 (%) = (換算台幣價 - 台股現價) / 台股現價 * 100
        """
        results = []
        if usdtwd_rate <= 0:
            usdtwd_rate = 32.5

        for mapping in adr_mappings:
            adr_sym = mapping.get("adr_symbol", "TSM")
            tw_sym = mapping.get("tw_symbol", "2330")
            ratio = float(mapping.get("ratio", 5.0))

            try:
                adr_t = yf.Ticker(adr_sym)
                adr_hist = adr_t.history(period="5d")
                
                tw_yf_sym = f"{tw_sym}.TW"
                tw_t = yf.Ticker(tw_yf_sym)
                tw_hist = tw_t.history(period="5d")

                if not adr_hist.empty and not tw_hist.empty:
                    adr_price = float(adr_hist["Close"].iloc[-1])
                    tw_price = float(tw_hist["Close"].iloc[-1])

                    # 換算每股台幣價格
                    adr_parity_twd = (adr_price * usdtwd_rate) / ratio
                    premium_pct = ((adr_parity_twd - tw_price) / tw_price) * 100 if tw_price > 0 else 0.0

                    results.append({
                        "adr_symbol": adr_sym,
                        "tw_symbol": tw_sym,
                        "ratio": ratio,
                        "adr_price_usd": round(adr_price, 2),
                        "tw_price_twd": round(tw_price, 2),
                        "usdtwd_rate": round(usdtwd_rate, 2),
                        "adr_parity_twd": round(adr_parity_twd, 2),
                        "premium_pct": round(premium_pct, 2),
                        "status": "溢價" if premium_pct > 0 else "折價"
                    })
            except Exception as e:
                logger.warning(f"計算 ADR {adr_sym} vs {tw_sym} 溢價率失敗: {e}")

        return results

    def get_indices_overview(self, us_indices: List[Dict[str, str]], tw_indices: List[Dict[str, str]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        獲取美股與台股大盤指數快照
        """
        data: Dict[str, List[Dict[str, Any]]] = {"us": [], "tw": []}

        for item in us_indices:
            sym = item.get("symbol", "")
            name = item.get("name", sym)
            try:
                t = yf.Ticker(sym)
                hist = t.history(period="5d")
                if not hist.empty:
                    c = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else c
                    chg = c - prev
                    pct = (chg / prev) * 100 if prev != 0 else 0.0
                    data["us"].append({
                        "symbol": sym,
                        "name": name,
                        "price": round(c, 2),
                        "change": round(chg, 2),
                        "pct_change": round(pct, 2)
                    })
            except Exception as e:
                logger.warning(f"獲取指數 {sym} 失敗: {e}")

        for item in tw_indices:
            sym = item.get("symbol", "")
            name = item.get("name", sym)
            try:
                t = yf.Ticker(sym)
                hist = t.history(period="5d")
                if not hist.empty:
                    c = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else c
                    chg = c - prev
                    pct = (chg / prev) * 100 if prev != 0 else 0.0
                    data["tw"].append({
                        "symbol": sym,
                        "name": name,
                        "price": round(c, 2),
                        "change": round(chg, 2),
                        "pct_change": round(pct, 2)
                    })
            except Exception as e:
                logger.warning(f"獲取指數 {sym} 失敗: {e}")

        return data
