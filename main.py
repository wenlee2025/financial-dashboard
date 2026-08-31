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
        "--log-level",
        default="INFO",
        help="日誌級別 (DEBUG, INFO, WARNING, ERROR)"
    )

    args = parser.parse_args()
    setup_logging(args.log_level)

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

if __name__ == "__main__":
    main()
