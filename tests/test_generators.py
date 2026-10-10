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


def test_generated_json_and_html_zero_nan_guarantee(tmp_path):
    """
    CI 自動化零-NaN 保證測試 (Zero-NaN CI Guarantee)
    注入包含 NaN, Inf, $nan, +nan% 等異常邊界數據的髒資料，
    驗證產生的 JSON (RFC 8259) 與 HTML 100% 杜絕 NaN、Infinity 或 $nan 洩漏。
    """
    import math

    template_dir = Path("templates")
    out_dir = tmp_path / "docs"
    hist_dir = out_dir / "history"
    data_dir = out_dir / "data"

    html_gen = HTMLDashboardGenerator(template_dir, out_dir, hist_dir, data_dir)

    dirty_context = {
        "page_title": "【邊界極端數據清洗測試專報】2026-10-10",
        "market_mode": "full",
        "market_mode_text": "全覽測試專報",
        "date": "2026-10-10",
        "updated_at": "2026-10-10 16:00:00",
        "timezone": "Asia/Taipei",
        "dashboard_url": "https://example.github.io/dashboard",
        "indices": {
            "tw": [{"name": "加權指數", "price": float("nan"), "change": float("-inf"), "pct_change": "+nan%"}],
            "us": [{"name": "標普500", "price": float("inf"), "change": 0.0, "pct_change": "$nan"}]
        },
        "macro_sentiment": {
            "fear_and_greed": {"score": float("nan"), "rating_zh": "中立"},
            "macro": {
                "us10y": {"value": float("nan"), "pct_change": float("inf")},
                "usdtwd": {"value": 32.5, "pct_change": 0.0}
            }
        },
        "adr_premiums": [
            {
                "adr_symbol": "TSM",
                "tw_symbol": "2330",
                "ratio": 5,
                "premium_pct": float("nan"),
                "adr_parity_twd": "$nan",
                "usdtwd_rate": 32.5,
                "status": "平價"
            }
        ],
        "stocks": [
            {
                "symbol": "9999",
                "name": "邊界未上市股",
                "stock_data": {
                    "price": float("nan"),
                    "change": float("nan"),
                    "pct_change": float("nan"),
                    "turnover": float("inf"),
                    "turnover_display": "$nan",
                    "market": "TW",
                    "currency": "TWD"
                },
                "score_info": {
                    "score": float("nan"),
                    "rating": "中立觀望",
                    "badge_color": "gray",
                    "signals": []
                },
                "price_levels": {
                    "s1": float("nan"),
                    "s2": float("nan"),
                    "r1": float("nan"),
                    "r2": float("nan"),
                    "entry_zone": "-",
                    "target_price": "$nan",
                    "stop_loss": "-",
                    "risk_reward_ratio": float("nan"),
                    "strategy_tip": "暫無報價"
                },
                "institutional": {}
            }
        ],
        "radar_comparison": {
            "dimensions": [
                {"name": "技術動能", "max": 100},
                {"name": "主力籌碼", "max": 100},
                {"name": "基本面前瞻", "max": 100},
                {"name": "波克夏護城河", "max": 100},
                {"name": "風險防禦", "max": 100},
                {"name": "多空綜合評分", "max": 100}
            ],
            "stocks": [
                {
                    "symbol": "9999",
                    "name": "測試股",
                    "tier": "TIER_3_TACTICAL",
                    "technicals": float("nan"),
                    "flows": float("inf"),
                    "fundamentals": 50,
                    "moat": 50,
                    "defense": 50,
                    "composite": float("nan"),
                    "strengths": ["無特殊警示"],
                    "weaknesses": []
                }
            ]
        },
        "deliberation_verdicts": {
            "9999": {
                "action": "☕ 觀望等待",
                "confidence": float("nan"),
                "vetoed": False,
                "synthesis": "數據不全，安全觀望"
            }
        },
        "portfolio_summary": {
            "total_value": float("nan"),
            "risk_score": float("nan")
        },
        "alerts": [{"level": "info", "badge": "測試", "title": "無警報", "desc": "-"}],
        "ai_analysis": {
            "executive_summary": "市場休市或無效報價",
            "market_mood": "中立觀望",
            "bullish_arguments": [],
            "bearish_risks": [],
            "catalysts": [],
            "action_checklist": []
        },
        "markdown_summary": "# 測試摘要"
    }

    # 1. 執行生成 (驗證 allow_nan=False 不會崩潰抛錯)
    out_file = html_gen.generate(dirty_context, "2026-10-10", "full")
    assert out_file.exists(), "最新 index.html 未成功生成"

    json_file = data_dir / "2026-10-10_full.json"
    assert json_file.exists(), "歷史 JSON 未成功生成"

    # 2. 嚴格驗證生成的 JSON 檔案
    with open(json_file, "r", encoding="utf-8") as f:
        raw_json_str = f.read()

    import re
    # 驗證原始 JSON 字串內無非法的字面量 NaN 或 Infinity (RFC 8259 合規)
    assert not re.search(r':\s*(NaN|Infinity|-Infinity)\b', raw_json_str), "JSON 原始字串包含非法的 NaN/Infinity 字面量"
    assert "$nan" not in raw_json_str.lower(), "JSON 原始字串未清洗 $nan 字符串"
    assert "+nan%" not in raw_json_str.lower(), "JSON 原始字串未清洗 +nan% 字符串"
    assert "-nan%" not in raw_json_str.lower(), "JSON 原始字串未清洗 -nan% 字符串"

    # 遞迴檢查反序列化後的資料節點
    loaded_json = json.loads(raw_json_str)

    def _walk_and_check(node, path=""):
        if isinstance(node, float):
            assert not math.isnan(node), f"節點 {path} 包含 NaN float"
            assert not math.isinf(node), f"節點 {path} 包含 Inf float"
        elif isinstance(node, str):
            lower_v = node.lower()
            assert "$nan" not in lower_v, f"字串節點 {path} 包含 $nan"
            assert "+nan%" not in lower_v, f"字串節點 {path} 包含 +nan%"
            assert "-nan%" not in lower_v, f"字串節點 {path} 包含 -nan%"
            assert "nan%" not in lower_v, f"字串節點 {path} 包含 nan%"
        elif isinstance(node, dict):
            for k, v in node.items():
                _walk_and_check(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                _walk_and_check(v, f"{path}[{i}]")

    _walk_and_check(loaded_json)

    # 3. 嚴格驗證生成的 HTML 檔案
    with open(out_file, "r", encoding="utf-8") as f:
        html_str = f.read()

    assert "$nan" not in html_str.lower(), "HTML 輸出洩漏 $nan 字符"
    assert "+nan%" not in html_str.lower(), "HTML 輸出洩漏 +nan% 字符"
    assert "-nan%" not in html_str.lower(), "HTML 輸出洩漏 -nan% 字符"
    assert ">nan<" not in html_str.lower(), "HTML 標籤內洩漏 raw nan"
    assert "[object Object]" not in html_str, "HTML 模板中存在未展開之 JS [object Object]"

