import pytest
from src.analytics.quant_scoring import QuantScorer
from src.analytics.price_levels import PriceLevelCalculator
from src.analytics.flow_analyzer import FlowAnalyzer

def test_quant_scorer_bullish():
    scorer = QuantScorer()
    stock_data = {
        "price": 100.0,
        "ma5": 98.0,
        "ma10": 95.0,
        "ma20": 90.0,
        "ma60": 80.0,
        "rsi14": 62.0,
        "macd_hist": 1.5,
        "volume_ratio": 1.4,
        "pct_change": 2.5,
        "market": "TW"
    }
    inst_data = {
        "foreign_lots": 1500,
        "trust_lots": 800,
        "total_lots": 2300
    }
    revenue_data = {
        "growth_rate_yoy": 32.0
    }

    result = scorer.score_stock(stock_data, inst_data, revenue_data)
    assert result["score"] >= 75
    assert result["rating_code"] == "strong_bull"
    assert result["badge_color"] == "emerald"
    assert len(result["signals"]) >= 3

def test_quant_scorer_bearish():
    scorer = QuantScorer()
    stock_data = {
        "price": 50.0,
        "ma5": 52.0,
        "ma10": 55.0,
        "ma20": 60.0,
        "ma60": 70.0,
        "rsi14": 25.0,
        "macd_hist": -2.0,
        "volume_ratio": 1.8,
        "pct_change": -3.5,
        "market": "TW"
    }
    inst_data = {
        "foreign_lots": -2500,
        "trust_lots": -600,
        "total_lots": -3100
    }
    revenue_data = {
        "growth_rate_yoy": -15.0
    }

    result = scorer.score_stock(stock_data, inst_data, revenue_data)
    assert result["score"] <= 35
    assert result["rating_code"] in ("lean_bear", "strong_bear")

def test_price_level_calculator():
    calc = PriceLevelCalculator()
    stock_data = {
        "price": 1000.0,
        "atr14": 20.0,
        "ma5": 990.0,
        "ma20": 970.0,
        "ma60": 920.0,
        "bb_upper": 1040.0,
        "bb_lower": 940.0,
        "high_52w": 1100.0,
        "low_52w": 800.0
    }
    levels = calc.calculate_levels(stock_data)
    assert levels["s1"] < stock_data["price"]
    assert levels["s2"] < levels["s1"]
    assert levels["r1"] > stock_data["price"]
    assert levels["r2"] > levels["r1"]
    assert levels["stop_loss"] < levels["s1"]
    assert levels["target_price"] >= levels["r1"]
    assert levels["risk_reward_ratio"] > 0

def test_flow_analyzer_alerts():
    analyzer = FlowAnalyzer()
    stocks_analysis = [
        {
            "symbol": "2330",
            "name": "台積電",
            "stock_data": {"price": 1000.0, "pct_change": 0.2, "volume_ratio": 2.5},
            "institutional": {"foreign_lots": 2000, "trust_lots": -800},
            "score_info": {"score": 75}
        }
    ]
    macro_data = {
        "fear_and_greed": {"score": 18.0},
        "macro": {"us10y": {"value": 4.45, "pct_change": 3.2}}
    }
    adr_data = [
        {
            "adr_symbol": "TSM",
            "tw_symbol": "2330",
            "premium_pct": 12.5,
            "adr_parity_twd": 1125.0
        }
    ]

    alerts = analyzer.analyze_market_alerts(stocks_analysis, macro_data, adr_data)
    assert len(alerts) >= 3
    badges = [a["badge"] for a in alerts]
    assert "宏觀警報" in badges
    assert "ADR 溢價" in badges
    assert "土洋對作" in badges
