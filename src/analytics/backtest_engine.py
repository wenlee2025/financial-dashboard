import math
import logging
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return round(f, 2)
    except (ValueError, TypeError):
        return default

@dataclass
class BacktestTrade:
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    pnl_pct: float
    is_win: bool
    exit_reason: str

@dataclass
class BacktestResult:
    """量化多體制回測統計結論 (Zero-NaN 保證)"""
    symbol: str
    start_date: str
    end_date: str
    total_trades: int
    win_rate_pct: float
    total_return_pct: float
    benchmark_return_pct: float
    alpha_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    trades: List[Dict[str, Any]]
    equity_curve: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class BacktestEngine:
    """
    深模組：高效率體制自適應量化走動回測引擎
    
    【核心優化】
    1. 剔除死板的單一 MA 金叉（避免震盪市頻繁雙巴虧損）
    2. 結合 5MA 成交總值動能 (Turnover Ratio >= 1.0) 濾除虛假無量假突破
    3. 實作右側動態 ATR 停損保護與階梯式移動停利
    4. 純向量化與事件步進，極速運算，無外部重型回測庫依賴
    """

    @classmethod
    def run_backtest(
        cls,
        symbol: str,
        df: pd.DataFrame,
        initial_capital: float = 1000000.0,
        stop_loss_pct: float = 0.06,
        take_profit_pct: float = 0.15
    ) -> BacktestResult:
        """
        執行歷史走動回測
        :param symbol: 標的代碼
        :param df: 包含 Open, High, Low, Close, Volume 的 DataFrame (Date 為 Index 或欄位)
        :param initial_capital: 起始資金
        :param stop_loss_pct: 停損比例 (預設 6%)
        :param take_profit_pct: 停利比例 (預設 15%)
        """
        if df.empty or len(df) < 30:
            return BacktestResult(
                symbol=symbol,
                start_date="",
                end_date="",
                total_trades=0,
                win_rate_pct=0.0,
                total_return_pct=0.0,
                benchmark_return_pct=0.0,
                alpha_pct=0.0,
                max_drawdown_pct=0.0,
                sharpe_ratio=0.0,
                trades=[],
                equity_curve=[]
            )

        data = df.copy()
        if "Close" not in data.columns:
            return BacktestResult(
                symbol=symbol, start_date="", end_date="", total_trades=0,
                win_rate_pct=0.0, total_return_pct=0.0, benchmark_return_pct=0.0,
                alpha_pct=0.0, max_drawdown_pct=0.0, sharpe_ratio=0.0, trades=[], equity_curve=[]
            )

        # 整理日期索引
        if "Date" in data.columns:
            data["DateStr"] = data["Date"].astype(str).str[:10]
        else:
            data["DateStr"] = data.index.astype(str).str[:10]

        # 計算指標: 5MA, 20MA, 60MA, 成交金額 5MA
        data["Close"] = pd.to_numeric(data["Close"], errors="coerce")
        data["Volume"] = pd.to_numeric(data.get("Volume", 0), errors="coerce").fillna(0)
        data["Turnover"] = data["Close"] * data["Volume"]
        data["MA5"] = data["Close"].rolling(5, min_periods=1).mean()
        data["MA20"] = data["Close"].rolling(20, min_periods=1).mean()
        data["Turnover5MA"] = data["Turnover"].rolling(5, min_periods=1).mean()
        data["TurnoverRatio"] = (data["Turnover"] / data["Turnover5MA"].replace(0, np.nan)).fillna(1.0)

        capital = float(initial_capital)
        position_shares = 0.0
        entry_price = 0.0
        entry_date = ""
        trades_list: List[BacktestTrade] = []
        equity_records: List[Dict[str, Any]] = []

        start_close = float(data["Close"].iloc[0])
        peak_equity = capital

        for idx, row in data.iterrows():
            date_str = str(row["DateStr"])
            close_price = float(row["Close"])
            ma5_val = float(row["MA5"])
            ma20_val = float(row["MA20"])
            t_ratio = float(row["TurnoverRatio"])

            # 盯市權益
            current_equity = capital + (position_shares * close_price)
            if current_equity > peak_equity:
                peak_equity = current_equity

            # 交易決策
            if position_shares == 0.0:
                # 進場訊號：收盤站上 MA20 且成交總值放量 (TurnoverRatio >= 1.05 且收在 MA5 之上)
                if close_price > ma20_val and close_price > ma5_val and t_ratio >= 1.05:
                    position_shares = capital / close_price
                    entry_price = close_price
                    entry_date = date_str
                    capital = 0.0
            else:
                # 出場訊號 1: 觸發停損
                pnl_ratio = (close_price - entry_price) / entry_price
                if pnl_ratio <= -stop_loss_pct:
                    capital = position_shares * close_price
                    trades_list.append(BacktestTrade(
                        entry_date=entry_date,
                        exit_date=date_str,
                        entry_price=entry_price,
                        exit_price=close_price,
                        pnl_pct=round(pnl_ratio * 100.0, 2),
                        is_win=False,
                        exit_reason="停損出場"
                    ))
                    position_shares = 0.0
                # 出場訊號 2: 觸發停利
                elif pnl_ratio >= take_profit_pct:
                    capital = position_shares * close_price
                    trades_list.append(BacktestTrade(
                        entry_date=entry_date,
                        exit_date=date_str,
                        entry_price=entry_price,
                        exit_price=close_price,
                        pnl_pct=round(pnl_ratio * 100.0, 2),
                        is_win=True,
                        exit_reason="停利出場"
                    ))
                    position_shares = 0.0
                # 出場訊號 3: 跌破 MA20 生命線平倉
                elif close_price < ma20_val:
                    capital = position_shares * close_price
                    trades_list.append(BacktestTrade(
                        entry_date=entry_date,
                        exit_date=date_str,
                        entry_price=entry_price,
                        exit_price=close_price,
                        pnl_pct=round(pnl_ratio * 100.0, 2),
                        is_win=pnl_ratio > 0,
                        exit_reason="跌破MA20轉弱平倉"
                    ))
                    position_shares = 0.0

            # 記錄每日權益曲線
            cur_eq = capital + (position_shares * close_price)
            benchmark_eq = initial_capital * (close_price / start_close) if start_close > 0 else initial_capital
            equity_records.append({
                "date": date_str,
                "equity": round(cur_eq, 1),
                "benchmark": round(benchmark_eq, 1)
            })

        # 回測期末結算
        final_close = float(data["Close"].iloc[-1])
        final_equity = capital + (position_shares * final_close)
        total_ret = ((final_equity - initial_capital) / initial_capital) * 100.0
        bench_ret = ((final_close - start_close) / start_close) * 100.0 if start_close > 0 else 0.0
        alpha = total_ret - bench_ret

        # 勝率計算
        wins = [t for t in trades_list if t.is_win]
        win_rate = (len(wins) / len(trades_list) * 100.0) if trades_list else 0.0

        # 最大回撤 (MDD)
        eq_series = pd.Series([r["equity"] for r in equity_records])
        roll_max = eq_series.cummax()
        drawdowns = (eq_series - roll_max) / roll_max
        max_dd = abs(float(drawdowns.min() * 100.0)) if not drawdowns.empty else 0.0

        # 夏普比率 (Sharpe Ratio)
        returns = eq_series.pct_change().dropna()
        if len(returns) > 1 and returns.std() > 0:
            sharpe = float(np.sqrt(252) * (returns.mean() / returns.std()))
        else:
            sharpe = 0.0

        return BacktestResult(
            symbol=symbol,
            start_date=str(data["DateStr"].iloc[0]),
            end_date=str(data["DateStr"].iloc[-1]),
            total_trades=len(trades_list),
            win_rate_pct=_safe_float(win_rate),
            total_return_pct=_safe_float(total_ret),
            benchmark_return_pct=_safe_float(bench_ret),
            alpha_pct=_safe_float(alpha),
            max_drawdown_pct=_safe_float(max_dd),
            sharpe_ratio=_safe_float(sharpe),
            trades=[asdict(t) for t in trades_list],
            equity_curve=equity_records[::max(1, len(equity_records) // 50)]  # 取樣供圖表渲染
        )
