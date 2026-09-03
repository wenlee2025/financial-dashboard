import pytest
from pathlib import Path
import yaml
from src.bridge.berkshire_bridge import BerkshireBridge, BerkshireAssetContract, SyncResult

def test_berkshire_contract_validation_success():
    """驗證合法防腐層契約"""
    c = BerkshireAssetContract(
        symbol="2330",
        name="台積電",
        tier="TIER_1_CORE",
        tier_label="👑 波克夏特許核心",
        berkshire_score=4.9
    )
    assert c.tier == "TIER_1_CORE"
    assert len(c.pyramid_buys) == 3
    assert c.pyramid_buys[0]["ratio"] == 0.05


def test_berkshire_contract_validation_invalid_tier():
    """驗證非法資產等級會被契約立即阻斷"""
    with pytest.raises(ValueError, match="非法資產分級"):
        BerkshireAssetContract(
            symbol="XYZ",
            name="無效",
            tier="INVALID_TIER",
            berkshire_score=4.0
        )


def test_berkshire_contract_validation_excessive_pyramid():
    """驗證超額金字塔配置上限阻斷"""
    with pytest.raises(ValueError, match="金字塔總配置上限不可超過"):
        BerkshireAssetContract(
            symbol="2330",
            name="台積電",
            tier="TIER_1_CORE",
            berkshire_score=4.9,
            pyramid_buys=[
                {"ratio": 0.15},
                {"ratio": 0.15}
            ]  # 總計 30% > 25% 警戒上限
        )


def test_berkshire_bridge_sync_upstream_assets(tmp_path):
    """驗證跨專案同步時能安全原子化更新目標 watchlist.yaml"""
    # 建立臨時 watchlist.yaml
    test_yaml_path = tmp_path / "watchlist.yaml"
    initial_data = {
        "tw_stocks": [
            {"symbol": "2330", "name": "台積電", "sector": "半導體"},
            {"symbol": "9999", "name": "測試股", "sector": "其他"}
        ],
        "us_stocks": []
    }
    with open(test_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(initial_data, f)

    bridge = BerkshireBridge(watchlist_path=test_yaml_path)
    res = bridge.sync_upstream_assets(watchlist_path=test_yaml_path)

    assert res.success is True
    assert "2330" in res.updated_symbols
    assert res.synced_count >= 1

    # 讀取回寫之 YAML 結構確認欄位完整且格式未損壞
    with open(test_yaml_path, "r", encoding="utf-8") as f:
        updated_data = yaml.safe_load(f)

    tsmc_entry = next(s for s in updated_data["tw_stocks"] if s["symbol"] == "2330")
    assert tsmc_entry["tier"] == "TIER_1_CORE"
    assert tsmc_entry["moat_badge"] == "👑 波克夏核心"
    assert len(tsmc_entry["pyramid_buys"]) == 3
