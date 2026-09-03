import pytest
from unittest.mock import MagicMock
from src.data_sources.market_gateway import MarketGateway, StockMarketBundle

def test_market_gateway_bundle_tw_and_us():
    """驗證 MarketGateway 一站式並行批次組裝台股與美股數據包"""
    tw_fetcher = MagicMock()
    us_fetcher = MagicMock()
    macro_fetcher = MagicMock()

    # Mock TW Market Fetcher
    tw_fetcher.get_batch_stock_data.return_value = {
        "2330": {
            "symbol": "2330",
            "name": "台積電",
            "price": 1000.0,
            "ma5": 990.0,
            "pct_change": 1.5
        }
    }
    tw_fetcher.get_twse_institutional_data.return_value = {
        "2330": {
            "foreign_lots": 2000,
            "trust_lots": 500,
            "total_lots": 2500
        }
    }
    tw_fetcher.get_monthly_revenue_yoy.return_value = {
        "growth_rate_yoy": 33.0
    }

    # Mock US Market Fetcher
    us_fetcher.get_batch_stock_data.return_value = {
        "NVDA": {
            "symbol": "NVDA",
            "name": "NVIDIA",
            "price": 125.0,
            "pct_change": 2.0
        }
    }

    gateway = MarketGateway(tw_fetcher=tw_fetcher, us_fetcher=us_fetcher, macro_fetcher=macro_fetcher)

    items = [
        {
            "symbol": "2330",
            "name": "台積電",
            "tier": "TIER_1_CORE",
            "tier_label": "👑 波克夏特許核心",
            "moat_badge": "👑 波克夏核心",
            "knife_pause": False,
            "pyramid_buys": [{"price": 900.0, "ratio": 0.05}]
        },
        {
            "symbol": "NVDA",
            "name": "NVIDIA",
            "tier": "TIER_2_MOMENTUM",
            "tier_label": "⚡ 戰術動量"
        }
    ]

    bundles = gateway.fetch_universe_bundles(items, date_str="2026-09-03")

    assert len(bundles) == 2
    assert "2330" in bundles
    assert "NVDA" in bundles

    # 驗證台股 Bundle 細節
    tw_bundle = bundles["2330"]
    assert isinstance(tw_bundle, StockMarketBundle)
    assert tw_bundle.market == "TW"
    assert tw_bundle.stock_data["price"] == 1000.0
    assert tw_bundle.inst_data["total_lots"] == 2500
    assert tw_bundle.revenue_data["growth_rate_yoy"] == 33.0
    assert tw_bundle.tier == "TIER_1_CORE"
    assert tw_bundle.pyramid_buys[0]["price"] == 900.0

    # 驗證美股 Bundle 細節
    us_bundle = bundles["NVDA"]
    assert isinstance(us_bundle, StockMarketBundle)
    assert us_bundle.market == "US"
    assert us_bundle.stock_data["price"] == 125.0
    assert us_bundle.tier == "TIER_2_MOMENTUM"


def test_market_gateway_scan_focus_stocks():
    """驗證 MarketGateway 吸收之籌碼掃描能力"""
    tw_fetcher = MagicMock()
    tw_fetcher.get_twse_institutional_data.return_value = {
        "2409": {"name": "友達", "foreign_lots": 5000, "trust_lots": 2000, "total_lots": 7000},
        "2886": {"name": "兆豐金", "foreign_lots": 3000, "trust_lots": 1000, "total_lots": 4000},
        "2330": {"name": "台積電", "foreign_lots": 8000, "trust_lots": 1000, "total_lots": 9000}
    }

    gateway = MarketGateway(tw_fetcher=tw_fetcher)
    # 排除已在清單中的 2330
    res = gateway.scan_focus_stocks(existing_symbols=["2330"], top_n=2)
    assert len(res) == 2
    assert res[0]["symbol"] == "2409"
    assert res[1]["symbol"] == "2886"


def test_market_gateway_macro_sentiment_bundle():
    """驗證 MarketGateway 宏觀情緒包獲取"""
    macro_fetcher = MagicMock()
    macro_fetcher.get_macro_overview.return_value = {"usdtwd": {"value": 32.5}}
    macro_fetcher.get_fear_and_greed_index.return_value = {"score": 55.0}
    macro_fetcher.get_tx_futures_net_oi.return_value = {"foreign_net_oi": -38000, "is_high_risk": True}
    macro_fetcher.calculate_adr_premium.return_value = [{"symbol": "TSM", "premium": 12.5}]

    gateway = MarketGateway(macro_fetcher=macro_fetcher)
    bundle = gateway.get_macro_sentiment_bundle(adr_mappings=[{"tw_symbol": "2330", "us_symbol": "TSM"}])

    assert bundle["fear_and_greed"]["score"] == 55.0
    assert bundle["tx_futures"]["is_high_risk"] is True
    assert bundle["adr_premiums"][0]["symbol"] == "TSM"
