import pytest
from pathlib import Path
from src.analytics.portfolio_governor import PortfolioGovernor, HoldingRecord, PortfolioAuditResult

def test_portfolio_governor_add_and_audit(tmp_path):
    test_json = tmp_path / "portfolio.json"
    gov = PortfolioGovernor(portfolio_path=test_json)

    # 1. 新增 Tier 1 特許核心資產 (台積電 2330)
    rec1 = gov.add_or_update_holding(
        symbol="2330",
        company_name="台積電",
        shares=1000,
        buy_price=950.0,
        buy_date="2026-08-01",
        tier="TIER_1_CORE",
        stop_loss=900.0,
        target_price=1100.0
    )
    assert rec1.symbol == "2330"
    assert rec1.tier == "TIER_1_CORE"

    # 2. 新增 Tier 2 戰術動量資產 (某動量股 3017)
    rec2 = gov.add_or_update_holding(
        symbol="3017",
        company_name="奇鋐",
        shares=2000,
        buy_price=600.0,
        buy_date="2026-08-15",
        tier="TIER_2_MOMENTUM",
        stop_loss=580.0,
        target_price=700.0
    )
    assert rec2.symbol == "3017"

    # 3. 模擬市場行情報告 (2330 上漲, 3017 跌破停損)
    analyzed_stocks = [
        {
            "symbol": "2330",
            "tier": "TIER_1_CORE",
            "stock_data": {"price": 1050.0, "rev_yoy": 30.0}
        },
        {
            "symbol": "3017",
            "tier": "TIER_2_MOMENTUM",
            "stock_data": {"price": 570.0, "rev_yoy": -8.0} # 跌破 580 且營收衰退
        }
    ]

    result = gov.audit_and_rebalance(analyzed_stocks=analyzed_stocks, audit_date="2026-10-10")
    assert isinstance(result, PortfolioAuditResult)
    assert result.total_cost == (1000 * 950.0) + (2000 * 600.0) # 950,000 + 1,200,000 = 2,150,000
    assert result.total_market_value == (1000 * 1050.0) + (2000 * 570.0) # 1,050,000 + 1,140,000 = 2,190,000
    assert result.unrealized_pnl == 40000.0
    assert result.hard_drift_count == 1  # 3017 戰術動量資產跌破停損
    assert result.soft_drift_count >= 1  # 3017 營收衰退

    # 驗證 3017 狀態被標記為嚴重破位
    h_3017 = next(h for h in result.holdings if h["symbol"] == "3017")
    assert "🚨" in h_3017["alert_status"]

    # 4. 測試移除持倉
    assert gov.remove_holding("3017") is True
    assert len(gov.data["holdings"]) == 1
