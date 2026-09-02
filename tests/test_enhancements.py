import pytest
from pathlib import Path
from src.analytics.supply_chain import SupplyChainMapper
from src.analytics.quant_scoring import QuantScorer
from src.generators.html_dashboard import HTMLDashboardGenerator

def test_supply_chain_mapper_metadata():
    mapper = SupplyChainMapper()
    
    # 測試 NVDA
    item_nvda = {"symbol": "NVDA", "stock_data": {"market": "US"}, "score_info": {"score": 85.0}}
    enriched_nvda = mapper.enrich_stock_metadata(item_nvda)
    assert enriched_nvda["supply_chain"]["sector_key"] == "us_tech"
    assert "NVDA" in enriched_nvda["supply_chain"]["role"] or "AI" in enriched_nvda["supply_chain"]["role"]
    assert enriched_nvda["supply_chain"]["is_focus"] is True

    # 測試 2330 台積電
    item_tsmc = {"symbol": "2330", "stock_data": {"market": "TW"}, "score_info": {"score": 75.0}}
    enriched_tsmc = mapper.enrich_stock_metadata(item_tsmc)
    assert enriched_tsmc["supply_chain"]["sector_key"] == "semiconductor"
    assert "NVDA" in enriched_tsmc["supply_chain"]["related_us"]
    assert "CoWoS" in enriched_tsmc["supply_chain"]["chain"] or "CoWoS" in enriched_tsmc["supply_chain"]["role"]

    # 測試 2382 廣達
    item_quanta = {"symbol": "2382", "stock_data": {"market": "TW"}, "score_info": {"score": 65.0}}
    enriched_quanta = mapper.enrich_stock_metadata(item_quanta)
    assert enriched_quanta["supply_chain"]["sector_key"] == "ai_server"
    assert "NVDA" in enriched_quanta["supply_chain"]["related_us"]

def test_multi_timeframe_resonance_scoring():
    scorer = QuantScorer()

    # 週線多頭且日線拉回量縮守穩月線 (週日共振)
    bull_stock = {
        "price": 100.0,
        "ma5": 99.0,
        "ma10": 98.0,
        "ma20": 98.5,
        "ma60": 90.0,
        "rsi14": 58.0,
        "macd_hist": 1.2,
        "volume_ratio": 1.0,
        "pct_change": 0.5,
        "turnover": 500000000,
        "turnover_ma5": 500000000,
        "turnover_ratio": 1.0,
        "turnover_ma5_slope": 100,
        "price_ma5_slope": 1.0,
        "weekly_trend": "bullish"
    }
    res_bull = scorer.score_stock(bull_stock)
    assert res_bull["score"] >= 70
    assert any("週日" in s for s in res_bull["signals"])

    # 週線偏空
    bear_stock = {
        "price": 80.0,
        "ma5": 82.0,
        "ma10": 85.0,
        "ma20": 88.0,
        "ma60": 95.0,
        "rsi14": 28.0,
        "macd_hist": -2.0,
        "volume_ratio": 1.5,
        "pct_change": -3.0,
        "weekly_trend": "bearish"
    }
    res_bear = scorer.score_stock(bear_stock)
    assert res_bear["score"] < 40
    assert any("週級別" in s for s in res_bear["signals"])

def test_html_dashboard_with_supply_chain_and_sectors(tmp_path):
    template_dir = Path("templates")
    out_dir = tmp_path / "docs"
    hist_dir = out_dir / "history"
    data_dir = out_dir / "data"

    generator = HTMLDashboardGenerator(template_dir, out_dir, hist_dir, data_dir)
    context = {
        "page_title": "【每日美台財經全覽】2026-09-02",
        "market_mode": "full",
        "market_mode_text": "美台財經全覽",
        "date": "2026-09-02",
        "updated_at": "2026-09-02 20:00:00",
        "timezone": "Asia/Taipei",
        "dashboard_url": "https://example.github.io/dashboard",
        "indices": {"tw": [], "us": []},
        "macro_sentiment": {
            "fear_and_greed": {"score": 60, "rating_zh": "貪婪"},
            "macro": {}
        },
        "adr_premiums": [],
        "stocks": [
            {
                "symbol": "2330",
                "name": "台積電",
                "note": "",
                "stock_data": {
                    "market": "TW",
                    "currency": "TWD",
                    "price": 1050.0,
                    "change": 20.0,
                    "pct_change": 1.94,
                    "turnover": 45000000000,
                    "turnover_ma5": 40000000000,
                    "turnover_ratio": 1.12,
                    "turnover_display": "450.0億 (5MA: 400.0億 | 1.12x)",
                    "turnover_short": "450.0億",
                    "turnover_ma5_short": "400.0億"
                },
                "score_info": {
                    "score": 85.0,
                    "rating": "強力做多",
                    "rating_code": "strong_bull",
                    "badge_color": "emerald",
                    "tech_score": 88.0,
                    "flow_score": 85.0,
                    "fund_score": 80.0,
                    "signals": ["均線多頭排列", "週日多週期共振：週線大多頭"],
                    "turnover_strategy": {
                        "strategy_code": "strong_bull",
                        "strategy_name": "強勢主升 🟢",
                        "badge_color": "emerald",
                        "signal": "成交總值突破5MA",
                        "turnover_display": "450.0億",
                        "turnover_short": "450.0億",
                        "turnover_ma5_short": "400.0億",
                        "turnover_ratio": 1.12
                    }
                },
                "supply_chain": {
                    "sector_key": "semiconductor",
                    "sector_name": "半導體與IC設計",
                    "sector_badge": "⚡ 半導體/IC設計",
                    "sector_tags": "semiconductor focus",
                    "role": "全球先進製程/CoWoS 代工龍頭",
                    "chain": "台積電 CoWoS 生態圈",
                    "related_us": ["NVDA", "AAPL"],
                    "is_focus": True
                },
                "price_levels": {
                    "current_price": 1050.0,
                    "s1": 1030.0,
                    "s2": 1000.0,
                    "r1": 1080.0,
                    "r2": 1120.0,
                    "entry_zone": "1030.0 - 1050.0",
                    "target_price": 1080.0,
                    "stop_loss": 1010.0,
                    "risk_reward_ratio": 1.5,
                    "strategy_tip": "建議分批進場"
                },
                "institutional": {"total_lots": 8000}
            }
        ],
        "alerts": [],
        "ai_analysis": {
            "executive_summary": "多頭主升",
            "market_mood": "強勢多頭",
            "bullish_arguments": ["AI 算力鏈拉貨"],
            "bearish_risks": [],
            "catalysts": [],
            "action_checklist": []
        },
        "data_validation_report": {
            "status": "PASSED_EXACT",
            "badge_text": "🛡️ 數據雙源交叉驗證通過",
            "checked_symbols_count": 1,
            "discrepancy_results": {}
        },
        "markdown_summary": "# 摘要"
    }

    out_file = generator.generate(context, "2026-09-02", "full")
    assert out_file.exists()
    html = out_file.read_text(encoding="utf-8")
    assert "🤖 AI 伺服器與散熱" in html
    assert "⚡ 半導體與IC設計" in html
    assert "台積電 CoWoS 生態圈" in html
    assert "NVDA, AAPL" in html
