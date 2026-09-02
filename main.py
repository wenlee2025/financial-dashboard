import argparse
import logging
import sys
from pathlib import Path

# 在 Windows 控制台確保 UTF-8 編碼支援 Emoji 與繁體中文
if sys.platform.startswith("win"):
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.pipeline import FinancialDashboardPipeline
from src.config import config

def setup_logging(level_name: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level_name.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def main():
    parser = argparse.ArgumentParser(description="每日美股／台股量化分析推播系統與財經儀表板")
    parser.add_argument(
        "--mode",
        choices=["tw_post", "us_morning", "full"],
        default="full",
        help="執行模式: tw_post (台股盤後 15:30), us_morning (美股晨報 06:30), full (全量分析)"
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default="",
        help="指定分析之股票代碼（逗號分隔，例如: 'NVDA,2330,AAPL'）"
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="僅生成 HTML 儀表板與報告，不發送通訊軟體與 Email 推播"
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="生成後自動啟動本地 Web 伺服器進行儀表板預覽"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="本地預覽伺服器通訊埠 (預設: 8000)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="日誌級別 (DEBUG, INFO, WARNING, ERROR)"
    )

    # 自選股清單管理參數
    parser.add_argument(
        "--list-watchlist",
        action="store_true",
        help="列出目前所有的自選股清單並退出"
    )
    parser.add_argument(
        "--add-stock",
        type=str,
        default="",
        help="新增單檔股票至自選清單 (例如: --add-stock 3231)"
    )
    parser.add_argument(
        "--name",
        type=str,
        default="",
        help="新增股票時指定公司名稱 (選填，例如: --name '緯創')"
    )
    parser.add_argument(
        "--sector",
        type=str,
        default="",
        help="新增股票時指定所屬產業/板塊 (選填，例如: --sector 'AI 伺服器')"
    )
    parser.add_argument(
        "--note",
        type=str,
        default="",
        help="新增股票時指定備註 (選填)"
    )
    parser.add_argument(
        "--remove-stock",
        type=str,
        default="",
        help="從自選清單中移除指定股票 (例如: --remove-stock 1785)"
    )
    parser.add_argument(
        "--batch-add",
        type=str,
        default="",
        help="批次新增多檔股票（逗號分隔，例如: --batch-add '3231,2356,AMD'）"
    )
    parser.add_argument(
        "--batch-remove",
        type=str,
        default="",
        help="批次移除多檔股票（逗號分隔，例如: --batch-remove '1785,6223'）"
    )

    args = parser.parse_args()
    setup_logging(args.log_level)

    # 處理自選股管理指令
    from src.watchlist_manager import WatchlistManager
    wm = WatchlistManager()

    if args.list_watchlist:
        print(wm.get_summary_text())
        return

    if args.add_stock:
        success, msg, item = wm.add_stock(
            symbol=args.add_stock,
            name=args.name or None,
            sector=args.sector or None,
            note=args.note or None
        )
        if success:
            print(f"✅ {msg}")
        else:
            print(f"❌ {msg}")
        return

    if args.remove_stock:
        success, msg, item = wm.remove_stock(args.remove_stock)
        if success:
            print(f"✅ {msg}")
        else:
            print(f"❌ {msg}")
        return

    if args.batch_add:
        added = wm.batch_add(args.batch_add)
        print(f"✅ 成功批次新增 {len(added)} 檔標的至自選清單！")
        return

    if args.batch_remove:
        removed = wm.batch_remove(args.batch_remove)
        print(f"✅ 成功批次移除 {len(removed)} 檔標的！")
        return

    custom_symbols = [s.strip() for s in args.symbols.split(",") if s.strip()] if args.symbols else None

    print("\n=======================================================")
    print("  🚀 每日財經分析推播系統 (Financial Dashboard) 啟動")
    print(f"  模式: {args.mode} | 推播: {'停用 (--no-push)' if args.no_push else '啟用'}")
    if custom_symbols:
        print(f"  自訂標的: {custom_symbols}")
    print("=======================================================\n")

    pipeline = FinancialDashboardPipeline(cfg=config)
    result = pipeline.run(
        mode=args.mode,
        custom_symbols=custom_symbols,
        no_push=args.no_push
    )

    print("\n=======================================================")
    print("  ✅ 分析與生成圓滿完成！")
    print(f"  📅 報告日期: {result['date']}")
    print(f"  📊 分析標的數量: {result['analyzed_stocks_count']} 檔")
    print(f"  ⚠️ 風險警報數量: {result['alerts_count']} 則")
    print(f"  🌐 儀表板輸出路徑: {result['dashboard_file']}")
    if result["push_results"]:
        print(f"  📬 推播狀態: {result['push_results']}")
    print("=======================================================\n")

    if args.serve:
        import http.server
        import socketserver
        import webbrowser
        import os

        web_dir = str(config.output_dir)
        port = args.port
        os.chdir(web_dir)

        class CustomHandler(http.server.SimpleHTTPRequestHandler):
            def end_headers(self):
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
                super().end_headers()

        print(f"🌐 本地儀表板伺服器已啟動: http://localhost:{port}")
        print("💡 按下 Ctrl + C 可停止伺服器\n")
        try:
            webbrowser.open(f"http://localhost:{port}")
        except Exception:
            pass

        with socketserver.TCPServer(("", port), CustomHandler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\n🛑 伺服器已停止。")

if __name__ == "__main__":
    main()
