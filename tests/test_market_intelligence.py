import pytest
from unittest.mock import MagicMock
from src.analytics.market_intelligence import MarketIntelligence, MarketIntelligenceReport

def test_market_intelligence_produce_report():
    """驗證 MarketIntelligence 統一產出市場情報報告"""
    news_service = MagicMock()
    flow_analyzer = MagicMock()
    ai_client = MagicMock()

    news_service.fetch_verified_news.return_value = [
        {"title": "台積電 3nm 產能供不應求", "source": "經濟日報", "symbol": "2330", "time_str": "1 小時前"}
    ]
    flow_analyzer.analyze_market_alerts.return_value = [
        {"level": "warning", "title": "外資台指期巨額淨空單壓盤", "desc": "外資淨空單超過 35,000 口"}
    ]
    ai_client.generate_analysis.return_value = {
        "summary": "市場偏多震盪，台積電供應鏈強勁",
        "key_takeaways": ["台積電營收成長創高"]
    }

    intelligence = MarketIntelligence(
        news_service=news_service,
        flow_analyzer=flow_analyzer,
        ai_client=ai_client
    )

    analyzed_stocks = [
        {
            "symbol": "2330",
            "name": "台積電",
            "stock_data": {"price": 1000.0, "pct_change": 1.5, "turnover_display": "350 億"},
            "score_info": {"score": 85.0, "rating": "強力做多", "signals": ["多頭排列"]},
            "price_levels": {"s1": 980.0, "r1": 1050.0},
            "tier": "TIER_1_CORE"
        }
    ]
    macro_sentiment = {
        "fear_and_greed": {"score": 55.0},
        "macro": {"vix": {"value": 15.0}},
        "tx_futures": {"foreign_net_oi": -38000, "is_high_risk": True}
    }

    report = intelligence.produce_intelligence(
        analyzed_stocks=analyzed_stocks,
        macro_sentiment=macro_sentiment,
        market_mode="tw_post"
    )

    assert isinstance(report, MarketIntelligenceReport)
    assert len(report.alerts) == 1
    assert len(report.verified_news) == 1
    assert report.verified_news_count == 1
    assert "summary" in report.ai_analysis
    assert report.stocks_summary[0]["symbol"] == "2330"
    
    # 驗證 to_dict
    d = report.to_dict()
    assert d["verified_news_count"] == 1
    assert len(d["alerts"]) == 1


def test_market_intelligence_autonomous_fallback():
    """驗證當 AI Client 連線異常時，情報模組依然能安全自治降級產出報告"""
    news_service = MagicMock()
    flow_analyzer = MagicMock()
    ai_client = MagicMock()

    news_service.fetch_verified_news.return_value = []
    flow_analyzer.analyze_market_alerts.return_value = []
    # 模擬 LLMClient 在調用 API 時 fallback 返回規則推理字典
    ai_client.generate_analysis.return_value = {
        "summary": "【量化規則推理】市場處於平衡體制",
        "is_fallback": True
    }

    intelligence = MarketIntelligence(
        news_service=news_service,
        flow_analyzer=flow_analyzer,
        ai_client=ai_client
    )

    analyzed_stocks = [
        {
            "symbol": "2330",
            "name": "台積電",
            "stock_data": {"price": 1000.0},
            "score_info": {"score": 80.0, "rating": "強力做多"},
            "price_levels": {}
        }
    ]
    macro_sentiment = {}

    report = intelligence.produce_intelligence(
        analyzed_stocks=analyzed_stocks,
        macro_sentiment=macro_sentiment
    )

    assert report.ai_analysis.get("is_fallback") is True
    assert "量化規則推理" in report.ai_analysis.get("summary", "")
