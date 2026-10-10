import pytest
import math
from src.analytics.radar_metrics import RadarMetricsCalculator, StockRadarMetrics, _sanitize_score

def test_sanitize_score():
    """驗證 Zero-NaN 清洗保證"""
    assert _sanitize_score(None, 50.0) == 50.0
    assert _sanitize_score(float('nan'), 50.0) == 50.0
    assert _sanitize_score(float('inf'), 50.0) == 50.0
    assert _sanitize_score("invalid", 50.0) == 50.0
    assert _sanitize_score(120.0) == 100.0
    assert _sanitize_score(-15.0) == 0.0
    assert _sanitize_score(88.456) == 88.5

def test_compute_stock_radar_tier1_core():
    """驗證 Tier 1 特許核心資產高護城河得分與雷達系列輸出"""
    stock_item = {
        "symbol": "2330",
        "name": "台積電",
        "tier": "TIER_1_CORE",
        "berkshire_score": 4.8,
        "stock_data": {
            "price": 1050.0,
            "ma5": 1040.0,
            "ma20": 1010.0,
            "ma60": 980.0,
            "turnover_ratio": 1.5,
            "pct_change": 2.0,
            "rsi": 65.0,
            "foreign_buy_lots": 12000,
            "trust_buy_lots": 3500,
            "inst_streak_days": 5,
            "rev_yoy": 32.5,
            "peg_ratio": 0.85
        },
        "score_info": {"score": 92.0},
        "price_levels": {
            "stop_loss": 995.0,
            "volatility_20d": 18.5
        }
    }
    macro = {
        "fear_and_greed": {"score": 65.0},
        "macro": {"vix": {"value": 14.5}},
        "tx_futures": {"foreign_net_oi": -12000}
    }

    metrics = RadarMetricsCalculator.compute_stock_radar(stock_item, macro)
    assert isinstance(metrics, StockRadarMetrics)
    assert metrics.symbol == "2330"
    assert metrics.tier == "TIER_1_CORE"
    assert metrics.moat >= 90.0  # 特許核心享有護城河高分
    assert metrics.technicals >= 80.0
    assert metrics.flows >= 85.0
    assert metrics.fundamentals >= 85.0
    assert metrics.defense >= 80.0
    assert metrics.composite >= 85.0

    series = metrics.to_radar_series()
    assert series["name"] == "2330 台積電"
    assert len(series["value"]) == 6
    for val in series["value"]:
        assert not math.isnan(val)
        assert 0.0 <= val <= 100.0

def test_compute_universe_radar_with_missing_data():
    """驗證缺值情況下全市場雷達資料仍能優雅降級為 Zero-NaN"""
    analyzed_stocks = [
        {
            "symbol": "6223",
            "name": "旺矽",
            "tier": "TIER_2_MOMENTUM",
            "stock_data": {},  # 空數據
            "score_info": {},
            "price_levels": {}
        }
    ]

    universe_data = RadarMetricsCalculator.compute_universe_radar(analyzed_stocks)
    assert "dimensions" in universe_data
    assert len(universe_data["dimensions"]) == 6
    assert len(universe_data["stocks"]) == 1
    stock = universe_data["stocks"][0]
    assert stock["symbol"] == "6223"
    assert stock["tier"] == "TIER_2_MOMENTUM"
    assert 0.0 <= stock["technicals"] <= 100.0
    assert 0.0 <= stock["composite"] <= 100.0
