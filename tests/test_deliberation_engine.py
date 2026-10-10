from src.analytics.deliberation_engine import DeliberationEngine, DeliberationVerdict

def test_deliberation_engine_bullish_verdict():
    """驗證多頭強勢標的之激辯結論與風控委員會放行"""
    stock_item = {
        "symbol": "2330",
        "name": "台積電",
        "date": "2026-10-10",
        "tier": "TIER_1_CORE",
        "stock_data": {
            "price": 1050.0,
            "foreign_buy_lots": 8000,
            "trust_buy_lots": 2500,
            "rev_yoy": 35.0,
            "turnover_ratio": 1.4
        },
        "score_info": {
            "score": 88.0,
            "rating": "強力做多",
            "signals": ["均線多頭排列", "外資投信合買"]
        },
        "price_levels": {
            "stop_loss": 990.0,
            "target_price": 1200.0
        }
    }

    verdict = DeliberationEngine.deliberate(stock_item)
    assert isinstance(verdict, DeliberationVerdict)
    assert verdict.symbol == "2330"
    assert verdict.rating == "強力做多"
    assert verdict.action == "🚀 順勢進攻"
    assert verdict.target_price == 1200.0
    assert verdict.stop_loss == 990.0
    assert len(verdict.bull_arguments) > 0
    assert verdict.jev_triage["choice"] == "BUY"
    assert verdict.divergence_warning is False

def test_deliberation_engine_bearish_veto():
    """驗證破線空頭標的被風控委員會一票否決"""
    stock_item = {
        "symbol": "2327",
        "name": "國巨",
        "date": "2026-10-10",
        "tier": "TIER_2_MOMENTUM",
        "stock_data": {
            "price": 500.0,
            "foreign_buy_lots": -5000,
            "rev_yoy": -12.0,
            "turnover_ratio": 3.5  # 爆量
        },
        "score_info": {
            "score": 22.0,
            "rating": "避險做空",
            "signals": ["均線空頭排列", "外資大賣"]
        },
        "price_levels": {
            "stop_loss": 520.0,  # 已跌破
            "target_price": 550.0
        }
    }

    verdict = DeliberationEngine.deliberate(stock_item)
    assert verdict.rating == "避險做空"
    assert verdict.action == "🛡️ 嚴禁進場"
    assert "一票否決" in verdict.risk_committee_summary
    assert verdict.jev_triage["choice"] == "SELL"
