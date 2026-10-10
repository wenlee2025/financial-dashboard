import pytest
import pandas as pd
import numpy as np
from src.analytics.backtest_engine import BacktestEngine, BacktestResult

def test_backtest_engine_run():
    """驗證回測引擎對假資料的步進運算與指標輸出"""
    # 建立 60 天模擬行情 (呈現先漲後跌趨勢)
    dates = pd.date_range("2026-01-01", periods=60)
    prices = [100.0 + i * 2.0 if i < 30 else 160.0 - (i - 30) * 1.5 for i in range(60)]
    volumes = [10000 + i * 100 for i in range(60)]

    df = pd.DataFrame({
        "Date": dates,
        "Open": prices,
        "High": [p + 2.0 for p in prices],
        "Low": [p - 2.0 for p in prices],
        "Close": prices,
        "Volume": volumes
    })

    result = BacktestEngine.run_backtest(
        symbol="2330",
        df=df,
        initial_capital=1000000.0,
        stop_loss_pct=0.06,
        take_profit_pct=0.15
    )

    assert isinstance(result, BacktestResult)
    assert result.symbol == "2330"
    assert result.total_trades >= 1
    assert isinstance(result.win_rate_pct, float)
    assert isinstance(result.total_return_pct, float)
    assert isinstance(result.max_drawdown_pct, float)
    assert len(result.equity_curve) > 0

def test_backtest_engine_empty_df():
    """驗證空資料時能優雅輸出安全結構而不崩潰"""
    df = pd.DataFrame()
    result = BacktestEngine.run_backtest(symbol="TEST", df=df)
    assert result.total_trades == 0
    assert result.win_rate_pct == 0.0
    assert result.equity_curve == []
