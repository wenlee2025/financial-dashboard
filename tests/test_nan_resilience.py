import pytest
import math
from pathlib import Path
import numpy as np
import pandas as pd
from src.analytics.price_levels import PriceLevelCalculator, _safe_val
from src.analytics.quant_scoring import QuantScorer, _safe_float
from src.data_sources.tw_market import TWMarketFetcher
from src.generators.html_dashboard import HTMLDashboardGenerator

def test_safe_val_and_safe_float():
    assert _safe_val(float("nan"), 0.0) == 0.0
    assert _safe_val(None, 10.0) == 10.0
    assert _safe_val("invalid", 5.0) == 5.0
    assert _safe_val(123.45, 0.0) == 123.45

    assert _safe_float(float("nan"), 0.0) == 0.0
    assert _safe_float(None, 50.0) == 50.0
    assert _safe_float("bad", 0.0) == 0.0
    assert _safe_float(77.5, 0.0) == 77.5

def test_price_level_calculator_nan_resilience():
    calc = PriceLevelCalculator()
    
    # 測試現價為 NaN 或 0
    dirty_stock = {
        "price": float("nan"),
        "atr14": float("nan"),
        "ma5": float("nan"),
        "ma20": float("nan"),
    }
    levels = calc.calculate_levels(dirty_stock)
    assert levels["current_price"] == 0.0
    assert levels["s1"] == 0.0
    assert levels["stop_loss"] == 0.0
    assert levels["target_price"] == 0.0
    assert levels["entry_zone"] == "-"
    assert not math.isnan(levels["risk_reward_ratio"])

def test_quant_scorer_nan_resilience():
    scorer = QuantScorer()
    
    dirty_stock = {
        "price": float("nan"),
        "volume": 0,
        "ma5": float("nan"),
        "ma20": float("nan"),
    }
    res = scorer.score_stock(dirty_stock)
    assert res["score"] == 50.0
    assert res["rating_code"] == "neutral"
    assert res["turnover_strategy"]["turnover_display"] == "-"

def test_technicals_nan_guard():
    fetcher = TWMarketFetcher()
    df = pd.DataFrame({
        "Open": [100.0, 102.0],
        "High": [105.0, 106.0],
        "Low": [99.0, 101.0],
        "Close": [103.0, 105.0],
        "Volume": [1000, 2000]
    })
    res_df = fetcher._calculate_technicals(df)
    assert not res_df["MA5"].isna().any()
    assert not res_df["MA20"].isna().any()
    assert not res_df["Turnover_MA5"].isna().any()

def test_html_dashboard_zero_nan_rendering(tmp_path):
    template_dir = Path("templates")
    out_dir = tmp_path / "docs"
    hist_dir = out_dir / "history"
    data_dir = out_dir / "data"

    generator = HTMLDashboardGenerator(template_dir, out_dir, hist_dir, data_dir)
    dirty_context = {
        "page_title": "【每日美台財經全覽】2026-09-02",
        "market_mode": "full",
        "market_mode_text": "美台財經全覽",
        "date": "2026-09-02",
        "updated_at": "2026-09-02 20:00:00",
        "timezone": "Asia/Taipei",
        "dashboard_url": "https://example.github.io/dashboard",
        "indices": {"tw": [], "us": []},
        "macro_sentiment": {
            "fear_and_greed": {"score": 50, "rating_zh": "中立"},
            "macro": {}
        },
        "adr_premiums": [],
        "stocks": [
            {
                "symbol": "3034",
                "name": "聯詠",
                "note": "",
                "stock_data": {
                    "market": "TW",
                    "currency": "TWD",
                    "price": 0.0,
                    "change": 0.0,
                    "pct_change": 0.0,
                    "turnover": 0.0,
                    "turnover_ma5": 0.0,
                    "turnover_ratio": 1.0,
                    "turnover_display": "-",
                    "turnover_short": "-",
                    "turnover_ma5_short": "-"
                },
                "score_info": {
                    "score": 50.0,
                    "rating": "中立觀望",
                    "rating_code": "neutral",
                    "badge_color": "yellow",
                    "tech_score": 50.0,
                    "flow_score": 50.0,
                    "fund_score": 50.0,
                    "signals": [],
                    "turnover_strategy": {
                        "strategy_code": "normal",
                        "strategy_name": "常態整理 ⚪",
                        "badge_color": "gray",
                        "signal": "",
                        "turnover_display": "-",
                        "turnover_short": "-",
                        "turnover_ma5_short": "-",
                        "turnover_ratio": 1.0
                    }
                },
                "price_levels": {
                    "current_price": 0.0,
                    "s1": 0.0,
                    "s2": 0.0,
                    "r1": 0.0,
                    "r2": 0.0,
                    "entry_zone": "-",
                    "target_price": 0.0,
                    "stop_loss": 0.0,
                    "risk_reward_ratio": 1.0,
                    "strategy_tip": "數據暫時無法計算點位"
                },
                "institutional": None
            }
        ],
        "alerts": [],
        "ai_analysis": {
            "executive_summary": "市場維持多頭輪動格局",
            "market_mood": "中立震盪",
            "bullish_arguments": ["基本面穩健"],
            "bearish_risks": ["高檔震盪"],
            "catalysts": [],
            "action_checklist": ["持股水位 50%"]
        },
        "data_validation_report": {
            "status": "PASSED_EXACT",
            "badge_text": "🛡️ 數據雙源交叉驗證通過 (誤差 ≤ 1.0%) | 24h 一手信源",
            "checked_symbols_count": 1,
            "discrepancy_results": {}
        },
        "markdown_summary": "# 摘要"
    }

    out_file = generator.generate(dirty_context, "2026-09-02", "full")
    assert out_file.exists()
    html = out_file.read_text(encoding="utf-8")
    assert "$nan" not in html
    assert "+nan%" not in html
    assert "nan億" not in html
    assert "$nan - nan" not in html
