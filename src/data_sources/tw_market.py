import datetime
import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import requests
import yfinance as yf

logger = logging.getLogger(__name__)

class TWMarketFetcher:
    """台股市場數據獲取器 (TWSE/TPEx + FinMind + yfinance)"""

    def __init__(self, finmind_token: Optional[str] = None):
        self.finmind_token = finmind_token
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def _normalize_tw_symbol(self, symbol: str) -> str:
        """標準化台股代碼為 yfinance 格式 (例: 2330 -> 2330.TW)"""
        symbol = str(symbol).strip().upper()
        if symbol.startswith("^"):
            return symbol
        if "." in symbol:
            return symbol
        # 預設上市為 .TW
        return f"{symbol}.TW"

    def get_stock_data(self, symbol: str, name: Optional[str] = None, period: str = "6mo") -> Dict[str, Any]:
        """
        獲取單檔台股行情、均線、技術指標與量能
        """
        raw_symbol = str(symbol).strip()
        yf_symbol = self._normalize_tw_symbol(raw_symbol)

        try:
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period=period)
            
            # 若 .TW 無資料，嘗試 .TWO (上櫃)
            if df.empty and not raw_symbol.startswith("^"):
                yf_symbol = f"{raw_symbol}.TWO"
                ticker = yf.Ticker(yf_symbol)
                df = ticker.history(period=period)

            if df.empty:
                logger.warning(f"無法取得台股 {raw_symbol} 之歷史行情")
                return self._build_empty_stock_data(raw_symbol, name)

            # 計算各項技術指標
            df = self._calculate_technicals(df)
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            current_price = float(latest["Close"])
            prev_close = float(prev["Close"])
            change = current_price - prev_close
            pct_change = (change / prev_close) * 100 if prev_close != 0 else 0.0

            # 抓取基本面摘要
            info = {}
            try:
                info = ticker.info or {}
            except Exception:
                pass

            display_name = name or info.get("shortName") or info.get("longName") or raw_symbol
            pe_ratio = info.get("trailingPE") or info.get("forwardPE")
            dividend_yield = (info.get("dividendYield") or 0.0) * 100 if info.get("dividendYield") else None
            market_cap = info.get("marketCap")

            # 抓取最近 30 日歷史走勢 (供前端 ECharts 繪製 K 線)
            history_30d = []
            for date_idx, row in df.tail(30).iterrows():
                d_str = date_idx.strftime("%Y-%m-%d") if hasattr(date_idx, "strftime") else str(date_idx)[:10]
                history_30d.append({
                    "date": d_str,
                    "open": round(float(row["Open"]), 2),
                    "close": round(float(row["Close"]), 2),
                    "high": round(float(row["High"]), 2),
                    "low": round(float(row["Low"]), 2),
                    "volume": int(row["Volume"]),
                    "ma5": round(float(row.get("MA5", row["Close"])), 2) if not pd.isna(row.get("MA5")) else None,
                    "ma20": round(float(row.get("MA20", row["Close"])), 2) if not pd.isna(row.get("MA20")) else None,
                })

            return {
                "symbol": raw_symbol,
                "yf_symbol": yf_symbol,
                "name": display_name,
                "market": "TW",
                "currency": "TWD",
                "price": round(current_price, 2),
                "change": round(change, 2),
                "pct_change": round(pct_change, 2),
                "open": round(float(latest["Open"]), 2),
                "high": round(float(latest["High"]), 2),
                "low": round(float(latest["Low"]), 2),
                "volume": int(latest["Volume"]),
                "prev_volume": int(prev["Volume"]),
                "volume_ratio": round(float(latest["Volume"]) / max(1, float(prev["Volume"])), 2),
                "ma5": round(float(latest["MA5"]), 2) if not pd.isna(latest.get("MA5")) else None,
                "ma10": round(float(latest["MA10"]), 2) if not pd.isna(latest.get("MA10")) else None,
                "ma20": round(float(latest["MA20"]), 2) if not pd.isna(latest.get("MA20")) else None,
                "ma60": round(float(latest["MA60"]), 2) if not pd.isna(latest.get("MA60")) else None,
                "rsi14": round(float(latest["RSI14"]), 2) if not pd.isna(latest.get("RSI14")) else 50.0,
                "macd": round(float(latest["MACD"]), 2) if not pd.isna(latest.get("MACD")) else 0.0,
                "macd_signal": round(float(latest["MACD_Signal"]), 2) if not pd.isna(latest.get("MACD_Signal")) else 0.0,
                "macd_hist": round(float(latest["MACD_Hist"]), 2) if not pd.isna(latest.get("MACD_Hist")) else 0.0,
                "atr14": round(float(latest["ATR14"]), 2) if not pd.isna(latest.get("ATR14")) else round(current_price * 0.02, 2),
                "bb_upper": round(float(latest["BB_Upper"]), 2) if not pd.isna(latest.get("BB_Upper")) else None,
                "bb_lower": round(float(latest["BB_Lower"]), 2) if not pd.isna(latest.get("BB_Lower")) else None,
                "high_52w": round(float(df["High"].max()), 2),
                "low_52w": round(float(df["Low"].min()), 2),
                "pe_ratio": round(float(pe_ratio), 2) if pe_ratio else None,
                "dividend_yield": round(float(dividend_yield), 2) if dividend_yield else None,
                "market_cap": market_cap,
                "history": history_30d,
                "date": df.index[-1].strftime("%Y-%m-%d") if hasattr(df.index[-1], "strftime") else str(df.index[-1])[:10]
            }
        except Exception as e:
            logger.error(f"獲取台股 {symbol} 資料失敗: {e}")
            return self._build_empty_stock_data(raw_symbol, name)

    def get_twse_institutional_data(self, date_str: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        獲取 TWSE 官方全市場三大法人買賣超 (T86)
        返回: { "2330": {"foreign_buy": 1000, "trust_buy": 500, "dealer_buy": 200, "total_buy": 1700}, ... }
        """
        if not date_str:
            date_str = datetime.datetime.now().strftime("%Y%m%d")
        else:
            date_str = date_str.replace("-", "")

        url = f"https://www.twse.com.tw/rwd/zh/fund/T86?response=json&date={date_str}&selectType=ALL"
        result: Dict[str, Dict[str, Any]] = {}

        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("stat") == "OK" and "data" in data:
                    # TWSE 欄位: 0證券代號, 1證券名稱, 4外陸資買賣超股數, 10投信買賣超股數, 11自營商買賣超股數, 18三大法人買賣超股數合計
                    for row in data["data"]:
                        code = str(row[0]).strip()
                        def parse_num(val_str):
                            try:
                                return int(str(val_str).replace(",", "").strip()) // 1000 # 轉為「張」
                            except Exception:
                                return 0

                        foreign_lots = parse_num(row[4]) if len(row) > 4 else 0
                        trust_lots = parse_num(row[10]) if len(row) > 10 else 0
                        dealer_lots = parse_num(row[11]) if len(row) > 11 else 0
                        total_lots = parse_num(row[18]) if len(row) > 18 else (foreign_lots + trust_lots + dealer_lots)

                        result[code] = {
                            "symbol": code,
                            "name": str(row[1]).strip() if len(row) > 1 else "",
                            "foreign_lots": foreign_lots,
                            "trust_lots": trust_lots,
                            "dealer_lots": dealer_lots,
                            "total_lots": total_lots
                        }
                    logger.info(f"成功抓取 TWSE 三大法人籌碼資料共 {len(result)} 檔")
                    return result
        except Exception as e:
            logger.warning(f"TWSE 官方 API 三大法人抓取失敗: {e}")

        # 若 TWSE 失敗且有 FinMind Token，嘗試 FinMind
        if self.finmind_token:
            result = self._get_finmind_institutional(date_str)

        return result

    def _get_finmind_institutional(self, date_str: str) -> Dict[str, Dict[str, Any]]:
        """FinMind 三大法人備援 API"""
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}" if len(date_str) == 8 else date_str
        url = "https://api.finmindtrade.com/api/v4/data"
        params = {
            "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
            "start_date": formatted_date,
            "end_date": formatted_date,
            "token": self.finmind_token
        }
        result: Dict[str, Dict[str, Any]] = {}
        try:
            resp = self.session.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                for item in data:
                    code = str(item.get("stock_id", "")).strip()
                    if not code:
                        continue
                    if code not in result:
                        result[code] = {"symbol": code, "foreign_lots": 0, "trust_lots": 0, "dealer_lots": 0, "total_lots": 0}
                    name = item.get("name", "")
                    diff = int(item.get("buy", 0)) - int(item.get("sell", 0))
                    lots = diff // 1000
                    if "Foreign" in name:
                        result[code]["foreign_lots"] += lots
                    elif "Investment" in name:
                        result[code]["trust_lots"] += lots
                    elif "Dealer" in name:
                        result[code]["dealer_lots"] += lots
                    result[code]["total_lots"] += lots
        except Exception as e:
            logger.warning(f"FinMind 籌碼備援抓取失敗: {e}")
        return result

    def get_monthly_revenue_yoy(self, symbol: str) -> Optional[Dict[str, Any]]:
        """獲取月營收 YoY (年增率) 與趨勢"""
        raw_symbol = str(symbol).strip()
        url = "https://api.finmindtrade.com/api/v4/data"
        params = {
            "dataset": "TaiwanStockMonthRevenue",
            "data_id": raw_symbol,
            "start_date": (datetime.datetime.now() - datetime.timedelta(days=120)).strftime("%Y-%m-%d"),
            "token": self.finmind_token or ""
        }
        try:
            resp = self.session.get(url, params=params, timeout=8)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                if data:
                    latest = data[-1]
                    prev_year = data[-2] if len(data) > 1 else latest
                    revenue = latest.get("revenue", 0)
                    rev_year = latest.get("revenue_year", 0)
                    rev_month = latest.get("revenue_month", 0)
                    # 簡易計算年增率
                    growth_rate = None
                    for prev_item in reversed(data[:-1]):
                        if prev_item.get("revenue_month") == rev_month and prev_item.get("revenue_year") == rev_year - 1:
                            old_rev = prev_item.get("revenue", 0)
                            if old_rev > 0:
                                growth_rate = round(((revenue - old_rev) / old_rev) * 100, 2)
                            break
                    return {
                        "revenue": revenue,
                        "revenue_year": rev_year,
                        "revenue_month": rev_month,
                        "growth_rate_yoy": growth_rate,
                        "revenue_date": f"{rev_year}/{rev_month:02d}"
                    }
        except Exception as e:
            logger.debug(f"FinMind 月營收抓取略過 ({raw_symbol}): {e}")
        return None

    def _calculate_technicals(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算技術指標 (MA, RSI, MACD, ATR, Bollinger Bands)"""
        df = df.copy()
        close = df["Close"]

        # 移動平均線 (Moving Averages)
        df["MA5"] = close.rolling(window=5).mean()
        df["MA10"] = close.rolling(window=10).mean()
        df["MA20"] = close.rolling(window=20).mean()
        df["MA60"] = close.rolling(window=60).mean()

        # RSI (14)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, np.nan)
        df["RSI14"] = 100 - (100 / (1 + rs))
        df["RSI14"] = df["RSI14"].fillna(50.0)

        # MACD (12, 26, 9)
        exp12 = close.ewm(span=12, adjust=False).mean()
        exp26 = close.ewm(span=26, adjust=False).mean()
        df["MACD"] = exp12 - exp26
        df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
        df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

        # ATR (14)
        high = df["High"]
        low = df["Low"]
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df["ATR14"] = tr.rolling(window=14).mean().fillna(close * 0.02)

        # Bollinger Bands (20, 2)
        ma20 = df["MA20"]
        std20 = close.rolling(window=20).std()
        df["BB_Upper"] = ma20 + (std20 * 2)
        df["BB_Lower"] = ma20 - (std20 * 2)

        return df

    def _build_empty_stock_data(self, symbol: str, name: Optional[str] = None) -> Dict[str, Any]:
        """回傳安全空的股票結構"""
        return {
            "symbol": symbol,
            "yf_symbol": self._normalize_tw_symbol(symbol),
            "name": name or symbol,
            "market": "TW",
            "currency": "TWD",
            "price": 0.0,
            "change": 0.0,
            "pct_change": 0.0,
            "open": 0.0,
            "high": 0.0,
            "low": 0.0,
            "volume": 0,
            "prev_volume": 0,
            "volume_ratio": 1.0,
            "ma5": None,
            "ma10": None,
            "ma20": None,
            "ma60": None,
            "rsi14": 50.0,
            "macd": 0.0,
            "macd_signal": 0.0,
            "macd_hist": 0.0,
            "atr14": 0.0,
            "bb_upper": None,
            "bb_lower": None,
            "high_52w": 0.0,
            "low_52w": 0.0,
            "pe_ratio": None,
            "dividend_yield": None,
            "market_cap": None,
            "history": [],
            "date": datetime.datetime.now().strftime("%Y-%m-%d")
        }
