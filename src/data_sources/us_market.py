import datetime
import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import requests
import yfinance as yf

logger = logging.getLogger(__name__)

class USMarketFetcher:
    """美股市場數據獲取器 (yfinance + Finnhub)"""

    def __init__(self, finnhub_key: Optional[str] = None):
        self.finnhub_key = finnhub_key
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def get_stock_data(self, symbol: str, name: Optional[str] = None, period: str = "6mo") -> Dict[str, Any]:
        """獲取單檔美股行情、均線、技術指標與基本面"""
        clean_symbol = str(symbol).strip().upper()
        try:
            ticker = yf.Ticker(clean_symbol)
            df = ticker.history(period=period)

            if df.empty:
                logger.warning(f"無法取得美股 {clean_symbol} 之歷史行情")
                return self._build_empty_stock_data(clean_symbol, name)

            df = self._calculate_technicals(df)
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            current_price = float(latest["Close"])
            prev_close = float(prev["Close"])
            change = current_price - prev_close
            pct_change = (change / prev_close) * 100 if prev_close != 0 else 0.0

            # 基本面資訊
            info = {}
            try:
                info = ticker.info or {}
            except Exception:
                pass

            display_name = name or info.get("shortName") or info.get("longName") or clean_symbol
            pe_ratio = info.get("trailingPE") or info.get("forwardPE")
            forward_pe = info.get("forwardPE")
            peg_ratio = info.get("pegRatio")
            target_mean_price = info.get("targetMeanPrice")
            recommendation_key = info.get("recommendationKey", "N/A")
            market_cap = info.get("marketCap")
            beta = info.get("beta")

            # 抓取最近 30 日走勢 (供前端 ECharts 繪製 K 線)
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
                "symbol": clean_symbol,
                "yf_symbol": clean_symbol,
                "name": display_name,
                "market": "US",
                "currency": "USD",
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
                "ma50": round(float(latest["MA50"]), 2) if not pd.isna(latest.get("MA50")) else None,
                "ma200": round(float(latest["MA200"]), 2) if not pd.isna(latest.get("MA200")) else None,
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
                "forward_pe": round(float(forward_pe), 2) if forward_pe else None,
                "peg_ratio": round(float(peg_ratio), 2) if peg_ratio else None,
                "target_mean_price": round(float(target_mean_price), 2) if target_mean_price else None,
                "recommendation": recommendation_key,
                "market_cap": market_cap,
                "beta": round(float(beta), 2) if beta else None,
                "history": history_30d,
                "date": df.index[-1].strftime("%Y-%m-%d") if hasattr(df.index[-1], "strftime") else str(df.index[-1])[:10]
            }
        except Exception as e:
            logger.error(f"獲取美股 {symbol} 資料失敗: {e}")
            return self._build_empty_stock_data(clean_symbol, name)

    def _calculate_technicals(self, df: pd.DataFrame) -> pd.DataFrame:
        """計算技術指標 (MA, RSI, MACD, ATR, Bollinger Bands)"""
        df = df.copy()
        close = df["Close"]

        # 移動平均線
        df["MA5"] = close.rolling(window=5).mean()
        df["MA10"] = close.rolling(window=10).mean()
        df["MA20"] = close.rolling(window=20).mean()
        df["MA50"] = close.rolling(window=50).mean()
        df["MA200"] = close.rolling(window=200).mean()

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
        """安全空結構"""
        return {
            "symbol": symbol,
            "yf_symbol": symbol,
            "name": name or symbol,
            "market": "US",
            "currency": "USD",
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
            "ma50": None,
            "ma200": None,
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
            "forward_pe": None,
            "peg_ratio": None,
            "target_mean_price": None,
            "recommendation": "N/A",
            "market_cap": None,
            "beta": None,
            "history": [],
            "date": datetime.datetime.now().strftime("%Y-%m-%d")
        }
