import pytest
from pathlib import Path
from src.watchlist_manager import WatchlistManager

def test_watchlist_manager_add_and_remove(tmp_path):
    test_yaml = tmp_path / "watchlist.yaml"
    wm = WatchlistManager(watchlist_path=test_yaml)

    # 1. 測試新增台股
    success, msg, item = wm.add_stock(symbol="3231", name="緯創", sector="AI 伺服器", note="GB200 代工")
    assert success is True
    assert item["symbol"] == "3231"
    assert item["name"] == "緯創"
    assert len(wm.data["tw_stocks"]) == 1

    # 2. 測試新增美股
    success_us, msg_us, item_us = wm.add_stock(symbol="AMD", name="超微", sector="晶片設計", note="MI300X")
    assert success_us is True
    assert item_us["symbol"] == "AMD"
    assert len(wm.data["us_stocks"]) == 1

    # 3. 測試重複新增 (更新屬性)
    success_dup, msg_dup, item_dup = wm.add_stock(symbol="3231", note="更新後的備註")
    assert success_dup is True
    assert item_dup["note"] == "更新後的備註"
    assert len(wm.data["tw_stocks"]) == 1

    # 4. 測試批次新增
    added = wm.batch_add("2356, 3017, AVGO")
    assert len(added) == 3

    # 5. 測試移除股票
    success_rm, msg_rm, rm_item = wm.remove_stock("3231")
    assert success_rm is True
    assert rm_item["symbol"] == "3231"

    # 6. 測試批次移除
    removed = wm.batch_remove("AMD, 2356")
    assert len(removed) == 2

    # 7. 驗證重新載入檔案資料持久化
    wm_reloaded = WatchlistManager(watchlist_path=test_yaml)
    assert any(s["symbol"] == "3017" for s in wm_reloaded.data["tw_stocks"])
    assert not any(s["symbol"] == "3231" for s in wm_reloaded.data["tw_stocks"])

def test_watchlist_manager_summary_text(tmp_path):
    test_yaml = tmp_path / "watchlist.yaml"
    wm = WatchlistManager(watchlist_path=test_yaml)
    wm.add_stock(symbol="2330", name="台積電", sector="晶圓代工")
    wm.add_stock(symbol="NVDA", name="輝達", sector="AI 算力")

    summary = wm.get_summary_text()
    assert "台積電" in summary
    assert "NVDA" in summary
    assert "2330" in summary
