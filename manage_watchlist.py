#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自選股清單管理終端工具 (Watchlist Management CLI)
可快速新增、刪除、查詢股票清單，並自動同步 config/watchlist.yaml
"""

import sys
from pathlib import Path

# 在 Windows 控制台確保 UTF-8 編碼支援
if sys.platform.startswith("win"):
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.watchlist_manager import WatchlistManager
from src.pipeline import FinancialDashboardPipeline
from src.config import config

def print_menu():
    print("\n=======================================================")
    print("  📊 每日財經儀表板 - 自選股清單管理器")
    print("=======================================================")
    print("  1. 📋 查看目前自選股清單 (List All Stocks)")
    print("  2. ➕ 新增股票 (單檔或批次新增)")
    print("  3. ➖ 移除股票 (單檔或批次移除)")
    print("  4. 🔍 搜尋股票代碼或名稱")
    print("  5. 🚀 儲存並直接執行財經分析流水線 (Run Pipeline)")
    print("  0. 🚪 退出")
    print("=======================================================")

def main():
    wm = WatchlistManager()

    while True:
        print_menu()
        choice = input("請選擇操作 (0-5): ").strip()

        if choice == "1":
            print(wm.get_summary_text())

        elif choice == "2":
            print("\n【➕ 新增股票】")
            sym_input = input("請輸入股票代碼 (單檔如 3231 或多檔逗號分隔如 3231,2356,AMD): ").strip()
            if not sym_input:
                print("⚠️ 未輸入代碼，取消操作。")
                continue

            if "," in sym_input or "，" in sym_input:
                added = wm.batch_add(sym_input)
                print(f"✅ 成功批次新增 {len(added)} 檔股票！")
            else:
                name = input("請輸入股票名稱 (選填，直接按 Enter 自動抓取): ").strip() or None
                sector = input("請輸入產業板塊 (選填，如 AI 伺服器/散熱/半導體): ").strip() or None
                note = input("請輸入監控備註 (選填): ").strip() or None
                success, msg, item = wm.add_stock(sym_input, name=name, sector=sector, note=note)
                if success:
                    print(f"✅ {msg}")
                else:
                    print(f"❌ {msg}")

        elif choice == "3":
            print("\n【➖ 移除股票】")
            sym_input = input("請輸入欲移除的股票代碼 (單檔如 1785 或多檔逗號分隔如 1785,6223): ").strip()
            if not sym_input:
                print("⚠️ 未輸入代碼，取消操作。")
                continue

            if "," in sym_input or "，" in sym_input:
                removed = wm.batch_remove(sym_input)
                print(f"✅ 成功批次移除 {len(removed)} 檔股票！")
            else:
                success, msg, item = wm.remove_stock(sym_input)
                if success:
                    print(f"✅ {msg}")
                else:
                    print(f"❌ {msg}")

        elif choice == "4":
            print("\n【🔍 搜尋股票】")
            query = input("請輸入欲搜尋的代碼或關鍵字: ").strip().lower()
            if not query:
                continue
            all_stocks = wm.list_stocks()
            matched = []
            for st in all_stocks.get("tw_stocks", []):
                if query in str(st.get("symbol", "")).lower() or query in str(st.get("name", "")).lower() or query in str(st.get("note", "")).lower():
                    matched.append((st, "TW"))
            for st in all_stocks.get("us_stocks", []):
                if query in str(st.get("symbol", "")).lower() or query in str(st.get("name", "")).lower() or query in str(st.get("note", "")).lower():
                    matched.append((st, "US"))

            if matched:
                print(f"\n找到 {len(matched)} 筆符合標的：")
                for st, mkt in matched:
                    print(f"  [{mkt}] {st.get('symbol')} {st.get('name')} | 板塊: {st.get('sector')} | 備註: {st.get('note')}")
            else:
                print("⚠️ 未找到任何符合的股票。")

        elif choice == "5":
            print("\n🚀 正在啟動最新自選股財經分析流水線...")
            pipeline = FinancialDashboardPipeline(cfg=config)
            result = pipeline.run(mode="full", no_push=True)
            print(f"✅ 生成完成！儀表板已更新至: {result['dashboard_file']}")

        elif choice == "0":
            print("👋 感謝使用，已安全儲存自選股設定！")
            break

        else:
            print("⚠️ 無效的選項，請重新輸入。")

if __name__ == "__main__":
    main()
