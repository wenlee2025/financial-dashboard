import pytest
from src.analytics.equity_evaluator import EquityEvaluator, EquityEvaluationResult

def test_equity_evaluator_tier1_core_complete_decision():
    """驗證特許核心標的 (Tier 1 Core) 的完整決策閉環：前瞻估值、豁免停損、金字塔掛單"""
    evaluator = EquityEvaluator()
    
    stock_data = {
        "symbol": "2330",
        "price": 1000.0,
        "ma5": 990.0,
        "ma10": 980.0,
        "ma20": 950.0,
        "ma60": 900.0,
        "weekly_trend": "bullish",
        "rsi14": 58.0,
        "macd_hist": 2.0,
        "forward_pe": 16.5,
        "peg_ratio": 0.75,
        "tier": "TIER_1_CORE",
        "tier_label": "👑 波克夏特許核心",
        "moat_badge": "👑 波克夏核心",
        "pyramid_buys": [
            {"price": 900.0, "ratio": 0.05},
            {"price": 800.0, "ratio": 0.07},
            {"price": 700.0, "ratio": 0.08}
        ]
    }
    
    inst_data = {"total_lots": 3000, "foreign_lots": 2000, "trust_lots": 1000}
    revenue_data = {"growth_rate_yoy": 35.0}
    
    result = evaluator.evaluate(stock_data, inst_data, revenue_data)
    
    assert isinstance(result, EquityEvaluationResult)
    assert result.score >= 75
    assert result.tier == "TIER_1_CORE"
    # 核心資產豁免硬停損
    assert result.stop_loss_display == "🛡️ 豁免硬停損 (論文控管)"
    assert "👑 波克夏核心資產 (豁免 ATR 停損)" in result.strategy_tip
    assert "-10% ($900.0, 5%)" in result.strategy_tip
    # 前瞻估值信號確認
    assert any("Forward PE" in sig for sig in result.signals)
    assert any("PEG" in sig for sig in result.signals)
    
    # 驗證 to_dict 兼顧現有介面
    d = result.to_dict()
    assert "score_info" in d
    assert "price_levels" in d
    assert d["score_info"]["score"] == result.score
    assert d["price_levels"]["stop_loss_display"] == result.stop_loss_display


def test_equity_evaluator_tier2_momentum_strict_stop_loss():
    """驗證戰術動量標的 (Tier 2 Momentum)：嚴格 ATR 止損與右側風報比"""
    evaluator = EquityEvaluator()
    
    stock_data = {
        "symbol": "6415",
        "price": 300.0,
        "ma5": 310.0,
        "ma10": 320.0,
        "ma20": 330.0,
        "ma60": 350.0,
        "atr14": 12.0,
        "weekly_trend": "bearish",
        "tier": "TIER_2_MOMENTUM",
        "tier_label": "⚡ 戰術動量"
    }
    
    result = evaluator.evaluate(stock_data)
    
    assert result.tier == "TIER_2_MOMENTUM"
    assert result.stop_loss > 0
    assert "$" in result.stop_loss_display
    assert "🛡️ 豁免" not in result.stop_loss_display
    assert result.score <= 45


def test_equity_evaluator_tx_futures_guard_penalty():
    """驗證外資台指期巨額淨空單對權值股的 -10 分防護懲罰"""
    evaluator = EquityEvaluator()
    
    stock_data = {
        "symbol": "2330",
        "price": 1000.0,
        "ma5": 1000.0,
        "ma20": 1000.0
    }
    
    macro_sentiment = {
        "tx_futures": {
            "foreign_net_oi": -38000,
            "is_high_risk": True
        }
    }
    
    result = evaluator.evaluate(stock_data, macro_sentiment=macro_sentiment)
    assert any("外資台指期巨額淨空單壓盤" in sig for sig in result.signals)


def test_equity_evaluator_regime_adaptive_weights():
    """驗證恐慌體制下籌碼權重提升至 50%"""
    evaluator = EquityEvaluator()
    
    stock_data = {"symbol": "2330", "price": 100.0, "ma5": 100.0, "ma20": 100.0}
    
    panic_macro = {
        "fear_and_greed": {"score": 20.0},
        "macro": {"vix": {"value": 26.0}}
    }
    
    result = evaluator.evaluate(stock_data, macro_sentiment=panic_macro)
    assert "恐慌防守體制" in result.regime_label


def test_equity_evaluator_empty_price_resilience():
    """驗證 0 價格或無效數據零崩潰保證"""
    evaluator = EquityEvaluator()
    result = evaluator.evaluate({"symbol": "NULL", "price": 0.0})
    assert result.score == 50.0
    assert result.rating == "暫無報價"
    assert result.stop_loss == 0.0


def test_equity_evaluator_decision_matrix_archetypes():
    """驗證評級與資金動能 5 大實戰決策原型的交叉映射"""
    evaluator = EquityEvaluator()

    # 1. 做多 + 強勢主升 -> 順勢進攻
    m1 = evaluator._derive_decision_matrix(rating_code="strong_bull", strategy_code="strong_bull")
    assert m1["action_code"] == "attack"
    assert "順勢進攻" in m1["action_badge"]
    assert m1["sort_rank"] == 5

    # 2. 做多 + 動能衰竭 -> 耐心等待 (勿急追高)
    m2 = evaluator._derive_decision_matrix(rating_code="strong_bull", strategy_code="momentum_decay")
    assert m2["action_code"] == "wait_pullback"
    assert "耐心等待" in m2["action_badge"]
    assert "等回踩S1" in m2["guidance"]

    # 3. 做多 + 常態整理 / 量縮築底 -> 逢低潛伏
    m3 = evaluator._derive_decision_matrix(rating_code="lean_bull", strategy_code="normal")
    assert m3["action_code"] == "lurk_accumulate"
    assert "逢低潛伏" in m3["action_badge"]

    # 4. 任何評級 + 爆量出貨 -> 警戒撤退
    m4 = evaluator._derive_decision_matrix(rating_code="strong_bull", strategy_code="heavy_volume_dump")
    assert m4["action_code"] == "alert_exit"
    assert "警戒撤退" in m4["action_badge"]
    assert m4["sort_rank"] == 1

    # 5. 空頭評級 + 常態整理 -> 嚴禁進場 (空手避險)
    m5 = evaluator._derive_decision_matrix(rating_code="strong_bear", strategy_code="normal")
    assert m5["action_code"] == "defense"
    assert "嚴禁進場" in m5["action_badge"]
