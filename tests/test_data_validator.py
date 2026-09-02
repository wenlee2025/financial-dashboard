import pytest
from datetime import datetime, timedelta
from src.analytics.data_validator import DataValidator
from src.data_sources.news_feed import NewsFeedService

def test_data_validator_discrepancy():
    validator = DataValidator(max_allowed_price_diff_pct=1.0)

    # 1. 誤差 <= 1% (Passed Exact)
    res_pass = validator.validate_discrepancy(100.0, 100.5, "收盤價")
    assert res_pass["status"] == "PASSED_EXACT"
    assert res_pass["diff_pct"] == 0.5

    # 2. 1% < 誤差 <= 5% (Passed with diff)
    res_diff = validator.validate_discrepancy(100.0, 103.0, "成交量")
    assert res_diff["status"] == "PASSED_WITH_DIFF"
    assert res_diff["diff_pct"] == 3.0

    # 3. 誤差 > 5% (Failed discrepancy)
    res_fail = validator.validate_discrepancy(100.0, 110.0, "EPS")
    assert res_fail["status"] == "FAILED_DISCREPANCY"
    assert res_fail["diff_pct"] == 10.0

def test_data_validator_mathematical_invariants():
    validator = DataValidator()

    # 合格標的
    valid_stock = {
        "symbol": "2330",
        "stock_data": {"price": 1000.0, "volume": 30000000, "turnover": 30000000000.0},
        "price_levels": {"stop_loss": 970.0, "s1": 985.0, "target_price": 1080.0}
    }
    warnings = validator.validate_mathematical_invariants(valid_stock)
    assert len(warnings) == 0

    # 點位邏輯異常 (SL > Price)
    invalid_stock = {
        "symbol": "2330",
        "stock_data": {"price": 1000.0, "volume": 30000000, "turnover": 30000000000.0},
        "price_levels": {"stop_loss": 1050.0, "target_price": 1080.0}
    }
    warnings2 = validator.validate_mathematical_invariants(invalid_stock)
    assert len(warnings2) >= 1
    assert "點位邏輯異常" in warnings2[0]

def test_news_freshness_gate():
    validator = DataValidator(max_news_age_hours=24.0)

    # 3 小時前發布的新聞 (合格)
    fresh_time = (datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
    is_fresh, age_h, msg = validator.validate_news_freshness(fresh_time)
    assert is_fresh is True
    assert 2.5 <= age_h <= 3.5

    # 36 小時前發布的舊新聞 (不合格)
    stale_time = (datetime.now() - timedelta(hours=36)).strftime("%Y-%m-%d %H:%M:%S")
    is_stale, stale_age_h, msg = validator.validate_news_freshness(stale_time)
    assert is_stale is False
    assert stale_age_h >= 35.0

def test_news_feed_service_structure():
    service = NewsFeedService(max_age_hours=24.0)
    news = service.fetch_verified_news(["2330", "NVDA", "2454"])
    assert isinstance(news, list)
    assert len(news) > 0

    first = news[0]
    assert "title" in first
    assert "publisher" in first
    assert "url" in first
    assert "published_at" in first
    assert "age_text" in first
    assert first["is_verified"] is True
