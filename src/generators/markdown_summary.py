from typing import Any, Dict, List, Optional

class MarkdownSummaryGenerator:
    """通訊軟體 (Telegram / Discord / LINE / Slack) Markdown 摘要卡片產生器"""

    def generate(self, context: Dict[str, Any]) -> str:
        date_str = context.get("date", "")
        mode_text = context.get("market_mode_text", "每日財經日報")
        ai_data = context.get("ai_analysis", {})
        macro = context.get("macro_sentiment", {})
        stocks = context.get("stocks", [])
        alerts = context.get("alerts", [])
        dashboard_url = context.get("dashboard_url", "")

        fg_score = macro.get("fear_and_greed", {}).get("score", 50)
        fg_zh = macro.get("fear_and_greed", {}).get("rating_zh", "中立")
        us10y = macro.get("macro", {}).get("us10y", {}).get("value", 0)

        lines = [
            f"📊 *【{mode_text}】{date_str}*",
            f"━━━━━━━━━━━━━━━━━━",
            f"🎯 *核心結論*：{ai_data.get('executive_summary', '市場維持區間震盪')}",
            f"📈 *市場氛圍*：`{ai_data.get('market_mood', '觀望')}` | 恐慌指數：`{fg_score} ({fg_zh})` | 美債10Y：`{us10y}%`",
            ""
        ]

        # 核心多空論點
        bulls = ai_data.get("bullish_arguments", [])
        if bulls:
            lines.append("🟢 *多方主線*：")
            for b in bulls[:2]:
                lines.append(f"  • {b}")
            lines.append("")

        bears = ai_data.get("bearish_risks", [])
        if bears:
            lines.append("🔴 *空方風險*：")
            for br in bears[:2]:
                lines.append(f"  • {br}")
            lines.append("")

        # 焦點標的多空評分與點位
        if stocks:
            lines.append("📌 *焦點標的多空評分與操作點位*：")
            for item in stocks[:5]:
                sym = item.get("symbol", "")
                name = item.get("name", "")
                st = item.get("stock_data", {})
                score_info = item.get("score_info", {})
                pl = item.get("price_levels", {})

                pct = st.get("pct_change", 0.0)
                score = score_info.get("score", 50)
                rating = score_info.get("rating", "中立")

                lines.append(
                    f"• *{sym} {name}* ({st.get('currency', '')} ${st.get('price', 0)} | `{pct:+.2f}%`)\n"
                    f"  評分: `{score}分 ({rating})` | 進場: `${pl.get('entry_zone', '')}`\n"
                    f"  防守 SL: `${pl.get('stop_loss', '')}` | 目標 TP: `${pl.get('target_price', '')}` (風報比 {pl.get('risk_reward_ratio', 1)}:1)"
                )
            lines.append("")

        # 主力警報
        if alerts:
            lines.append("⚠️ *主力籌碼與市場警報*：")
            for al in alerts[:3]:
                lines.append(f"  • *[{al.get('badge')}]* {al.get('title')}")
            lines.append("")

        # 操作檢查清單
        checklist = ai_data.get("action_checklist", [])
        if checklist:
            lines.append("📋 *操作紀律檢查清單*：")
            for chk in checklist[:3]:
                lines.append(f"  ☑ {chk}")
            lines.append("")

        if dashboard_url:
            lines.append(f"🌐 [開啟完整互動式財經儀表板]({dashboard_url})")

        return "\n".join(lines)
