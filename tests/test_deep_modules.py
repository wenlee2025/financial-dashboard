import pytest
import pandas as pd
import numpy as np
from src.analytics.technicals import TechnicalsEngine
from src.analytics.stock_universe_analyzer import StockUniverseAnalyzer
from src.analytics.quant_scoring import QuantScorer
from src.analytics.price_levels import PriceLevelCalculator
from src.analytics.supply_chain import SupplyChainMapper
from src.analytics.data_validator import DataValidator
from src.data_sources import TWMarketFetcher, USMarketFetcher

def test_technicals_engine_computations():
    # 建立 30 根合成 K 線資料
    dates = pd.date_range("2026-01-01", periods=30)
    prices = np.linspace(100, 130, 30)
    df = pd.DataFrame({
        "Open": prices,
        "High": prices + 2,
        "Low": prices - 2,
        "Close": prices,
        "Volume": [10000] * 30
    }, index=dates)

    res_df = TechnicalsEngine.calculate_technicals(df)
    assert "MA5" in res_df.columns
    assert "MA20" in res_df.columns
    assert "Weekly_MA5" in res_df.columns
    assert "Weekly_MA20" in res_df.columns
    assert "Turnover_MA5" in res_df.columns
    assert "RSI14" in res_df.columns
    assert "MACD" in res_df.columns
    assert "ATR14" in res_df.columns
    assert "BB_Upper" in res_df.columns

    # 驗證無任何 NaN
    assert not res_df["MA5"].isna().any()
    assert not res_df["RSI14"].isna().any()

    # 驗證週線趨勢判定
    trend = TechnicalsEngine.evaluate_weekly_trend(current_price=130, w_ma5=120, w_ma20=110)
    assert trend == "bullish"
    trend_bear = TechnicalsEngine.evaluate_weekly_trend(current_price=90, w_ma5=100, w_ma20=110)
    assert trend_bear == "bearish"

def test_stock_universe_analyzer_deep_module(monkeypatch):
    tw_fetcher = TWMarketFetcher()
    us_fetcher = USMarketFetcher()
    scorer = QuantScorer()
    level_calc = PriceLevelCalculator()
    supply_chain_mapper = SupplyChainMapper()
    validator = DataValidator()

    analyzer = StockUniverseAnalyzer(
        tw_fetcher=tw_fetcher,
        us_fetcher=us_fetcher,
        scorer=scorer,
        level_calc=level_calc,
        supply_chain_mapper=supply_chain_mapper,
        validator=validator
    )

    # 測試 mock 股票分析
    def mock_tw_batch(stocks, period="6mo", max_workers=10):
        return {
            "2330": {
                "symbol": "2330",
                "name": "台積電",
                "market": "TW",
                "price": 1050.0,
                "change": 20.0,
                "pct_change": 1.94,
                "turnover": 45000000000,
                "turnover_ma5": 40000000000,
                "turnover_ratio": 1.12,
                "ma5": 1040.0,
                "ma10": 1020.0,
                "ma20": 1000.0,
                "ma60": 950.0,
                "rsi14": 65.0,
                "macd_hist": 2.5,
                "volume_ratio": 1.1,
                "weekly_trend": "bullish"
            }
        }

    monkeypatch.setattr(tw_fetcher, "get_batch_stock_data", mock_tw_batch)
    monkeypatch.setattr(tw_fetcher, "get_twse_institutional_data", lambda d: {"2330": {"total_lots": 5000}})
    monkeypatch.setattr(tw_fetcher, "get_monthly_revenue_yoy", lambda c: {"yoy": 25.0})

    stocks_input = [{"symbol": "2330", "name": "台積電", "market": "TW"}]
    analyzed, report, warnings = analyzer.analyze_universe(stocks_input, "2026-09-02")

    assert len(analyzed) == 1
    assert analyzed[0]["symbol"] == "2330"
    assert analyzed[0]["score_info"]["score"] >= 70
    assert analyzed[0]["supply_chain"]["sector_key"] == "semiconductor"
    assert report["status"] == "PASSED_EXACT"
