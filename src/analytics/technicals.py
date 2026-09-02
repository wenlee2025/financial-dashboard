import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class TechnicalsEngine:
    """單一真實來源技術指標計算引擎 (Technicals Engine)"""

    @staticmethod
    def calculate_technicals(df: pd.DataFrame, is_us: bool = False) -> pd.DataFrame:
        """
        為行情 DataFrame 計算所有標準量化技術指標與週線級別趨勢
        具備 min_periods=1 零 NaN 防護保證
        """
        if df.empty:
            return df

        df = df.copy()
        close = df["Close"].ffill().bfill().fillna(0.0)

        # 1. 移動平均線 (Moving Averages)
        df["MA5"] = close.rolling(window=5, min_periods=1).mean()
        df["MA10"] = close.rolling(window=10, min_periods=1).mean()
        df["MA20"] = close.rolling(window=20, min_periods=1).mean()
        df["MA50"] = close.rolling(window=50, min_periods=1).mean()
        df["MA60"] = close.rolling(window=60, min_periods=1).mean()
        df["MA200"] = close.rolling(window=200, min_periods=1).mean()

        # 2. 週級別均線 (週 5MA ≈ 25 日線, 週 20MA ≈ 100 日線)
        df["Weekly_MA5"] = close.rolling(window=25, min_periods=1).mean()
        df["Weekly_MA20"] = close.rolling(window=100, min_periods=1).mean()

        # 3. 成交總值 (Turnover / Dollar Volume) 與 5MA
        volume = df["Volume"].fillna(0)
        df["Turnover"] = close * volume
        df["Turnover_MA5"] = df["Turnover"].rolling(window=5, min_periods=1).mean().fillna(df["Turnover"])

        # 4. RSI (14)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
        rs = gain / loss.replace(0, np.nan)
        df["RSI14"] = 100 - (100 / (1 + rs))
        df["RSI14"] = df["RSI14"].fillna(50.0)

        # 5. MACD (12, 26, 9)
        exp12 = close.ewm(span=12, adjust=False).mean()
        exp26 = close.ewm(span=26, adjust=False).mean()
        df["MACD"] = exp12 - exp26
        df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
        df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

        # 6. ATR (14)
        high = df["High"]
        low = df["Low"]
        prev_close = close.shift(1).fillna(close)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df["ATR14"] = tr.rolling(window=14, min_periods=1).mean().fillna(close * 0.02)

        # 7. Bollinger Bands (20, 2)
        ma20 = df["MA20"]
        std20 = close.rolling(window=20, min_periods=1).std().fillna(0.0)
        df["BB_Upper"] = ma20 + (std20 * 2)
        df["BB_Lower"] = ma20 - (std20 * 2)

        return df

    @staticmethod
    def evaluate_weekly_trend(current_price: float, w_ma5: float, w_ma20: float) -> str:
        """判定週級別中長線大趨勢"""
        if current_price >= w_ma5 >= w_ma20:
            return "bullish"
        elif current_price < w_ma5 < w_ma20:
            return "bearish"
        return "neutral"
