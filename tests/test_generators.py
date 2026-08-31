import json
from pathlib import Path
from src.generators.html_dashboard import HTMLDashboardGenerator
from src.generators.markdown_summary import MarkdownSummaryGenerator
from src.generators.email_newsletter import EmailNewsletterGenerator

def test_markdown_summary_generator():
    gen = MarkdownSummaryGenerator()
    context = {
        "date": "2026-09-01",
        "market_mode_text": "台股盤後專報",
        "ai_analysis": {
            "executive_summary": "台股維持強勢多頭格局，台積電外資大買領漲。",
            "market_mood": "強勢多頭",
            "bullish_arguments": ["AI 供應鏈拉貨強勁", "外資連三買"],
            "bearish_risks": ["美債殖利率反彈"],
            "action_checklist": ["持股水位 60%"]
        },
        "macro_sentiment": {
            "fear_and_greed": {"score": 68, "rating_zh": "貪婪"},
            "macro": {"us10y": {"value": 4.25}}
        },
        "stocks": [
            {
                "symbol": "2330",
                "name": "台積電",
                "stock_data": {"price": 1050.0, "pct_change": 2.5, "currency": "TWD"},
                "score_info": {"score": 88, "rating": "強力做多"},
                "price_levels": {"entry_zone": "1030 - 1050", "stop_loss": "1010", "target_price": "1100", "risk_reward_ratio": 2.5}
            }
        ],
        "alerts": [{"badge": "籌碼主力", "title": "外資買超創月新高"}],
        "dashboard_url": "https://example.github.io/dashboard"
    }

    md = gen.generate(context)
    assert "【台股盤後專報】2026-09-01" in md
    assert "2330 台積電" in md
    assert "強力做多" in md
    assert "https://example.github.io/dashboard" in md

def test_html_and_email_generators(tmp_path):
    template_dir = Path("templates")
    out_dir = tmp_path / "docs"
    hist_dir = out_dir / "history"
    data_dir = out_dir / "data"

    html_gen = HTMLDashboardGenerator(template_dir, out_dir, hist_dir, data_dir)
    email_gen = EmailNewsletterGenerator(template_dir)

    context = {
        "page_title": "【台股盤後專報】2026-09-01",
        "market_mode": "tw_post",
        "market_mode_text": "台股盤後籌碼專報",
        "date": "2026-09-01",
        "updated_at": "2026-09-01 15:30:00",
        "timezone": "Asia/Taipei",
        "dashboard_url": "https://example.github.io/dashboard",
        "indices": {"tw": [{"name": "加權指數", "price": 23000, "change": 150, "pct_change": 0.65}], "us": []},
        "macro_sentiment": {
            "fear_and_greed": {"score": 65, "rating_zh": "貪婪"},
            "macro": {"us10y": {"value": 4.25, "pct_change": -0.5}, "usdtwd": {"value": 32.2, "pct_change": 0.1}}
        },
        "adr_premiums": [{"adr_symbol": "TSM", "tw_symbol": "2330", "ratio": 5, "premium_pct": 10.5, "adr_parity_twd": 1150, "usdtwd_rate": 32.2, "status": "溢價"}],
        "stocks": [
            {
                "symbol": "2330",
                "name": "台積電",
                "stock_data": {"price": 1050.0, "change": 25.0, "pct_change": 2.44, "market": "TW", "currency": "TWD"},
                "score_info": {"score": 88, "rating": "強力做多", "badge_color": "emerald", "signals": ["均線多頭排列"]},
                "price_levels": {"s1": 1030, "s2": 1000, "r1": 1080, "r2": 1120, "entry_zone": "1030-1050", "target_price": 1100, "stop_loss": 1010, "risk_reward_ratio": 2.5, "strategy_tip": "拉回量縮守穩進場"},
                "institutional": {"total_lots": 5000}
            }
        ],
        "alerts": [{"level": "warning", "badge": "ADR 溢價", "title": "TSM 溢價 10.5%", "desc": "美股買盤強勁"}],
        "ai_analysis": {
            "executive_summary": "台股受台積電領軍大漲，外資法人積極回補。",
            "market_mood": "強勢多頭",
            "bullish_arguments": ["AI 權值股動能強"],
            "bearish_risks": ["高檔震盪加劇"],
            "catalysts": ["輝達即將召開 GTC 大會"],
            "action_checklist": ["持股水位控制於 60%"]
        },
        "markdown_summary": "# 摘要"
    }

    out_file = html_gen.generate(context, "2026-09-01", "tw_post")
    assert out_file.exists()
    assert (hist_dir / "2026-09-01_tw_post.html").exists()
    assert (data_dir / "2026-09-01_tw_post.json").exists()
    assert (data_dir / "history_index.json").exists()

    email_html = email_gen.generate(context)
    assert "台股盤後籌碼專報" in email_html
    assert "台積電" in email_html
