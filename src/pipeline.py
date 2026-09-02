import datetime
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from .config import Config, config as default_config
from .data_sources import TWMarketFetcher, USMarketFetcher, MacroSentimentFetcher, MarketScanner
from .data_sources.news_feed import NewsFeedService
from .analytics import QuantScorer, PriceLevelCalculator, FlowAnalyzer
from .analytics.data_validator import DataValidator
from .analytics.supply_chain import SupplyChainMapper
from .analytics.stock_universe_analyzer import StockUniverseAnalyzer
from .ai_engine import LLMClient, PromptBuilder
from .generators import HTMLDashboardGenerator, MarkdownSummaryGenerator, EmailNewsletterGenerator
from .notifiers import NotificationDispatcher

logger = logging.getLogger(__name__)

class FinancialDashboardPipeline:
    """每日財經分析與儀表板主流程流水線 (深模組調度中樞)"""

    def __init__(self, cfg: Optional[Config] = None):
        self.cfg = cfg or default_config

        # 1. 數據獲取層
        self.tw_fetcher = TWMarketFetcher(finmind_token=self.cfg.finmind_token)
        self.us_fetcher = USMarketFetcher(finnhub_key=self.cfg.finnhub_key)
        self.macro_fetcher = MacroSentimentFetcher(fred_key=self.cfg.fred_key)
        self.scanner = MarketScanner(self.tw_fetcher, self.us_fetcher, self.cfg.scanner_settings)
        self.news_service = NewsFeedService(max_age_hours=24.0)

        # 2. 量化分析、標的分析與數據驗證層
        self.scorer = QuantScorer(weights=self.cfg.scoring_weights, tiers=self.cfg.rating_tiers)
        self.level_calc = PriceLevelCalculator()
        self.flow_analyzer = FlowAnalyzer()
        self.validator = DataValidator(max_allowed_price_diff_pct=1.0, max_news_age_hours=24.0)
        self.supply_chain_mapper = SupplyChainMapper()
        self.universe_analyzer = StockUniverseAnalyzer(
            tw_fetcher=self.tw_fetcher,
            us_fetcher=self.us_fetcher,
            scorer=self.scorer,
            level_calc=self.level_calc,
            supply_chain_mapper=self.supply_chain_mapper,
            validator=self.validator
        )

        # 3. AI 推論層
        self.ai_client = LLMClient(
            provider=self.cfg.ai_provider,
            gemini_key=self.cfg.gemini_api_key,
            openai_key=self.cfg.openai_api_key,
            anthropic_key=self.cfg.anthropic_api_key,
            gemini_model=self.cfg.gemini_model
        )

        # 4. 生成器層
        template_dir = self.cfg.base_dir / "templates"
        self.html_gen = HTMLDashboardGenerator(
            template_dir=template_dir,
            output_dir=self.cfg.output_dir,
            history_dir=self.cfg.history_dir,
            data_dir=self.cfg.data_dir
        )
        self.md_gen = MarkdownSummaryGenerator()
        self.email_gen = EmailNewsletterGenerator(template_dir=template_dir)

        # 5. 推播發送層
        self.dispatcher = NotificationDispatcher(
            telegram_token=self.cfg.telegram_bot_token,
            telegram_chat_id=self.cfg.telegram_chat_id,
            discord_webhook=self.cfg.discord_webhook_url,
            line_token=self.cfg.line_channel_access_token,
            line_user_id=self.cfg.line_user_id,
            slack_webhook=self.cfg.slack_webhook_url,
            smtp_config=self.cfg.smtp_config
        )

    def run(
        self,
        mode: str = "full",
        custom_symbols: Optional[List[str]] = None,
        no_push: bool = False
    ) -> Dict[str, Any]:
        """
        執行主流程
        :param mode: 'tw_post' (台股盤後), 'us_morning' (美股晨報), 'full' (全量分析)
        :param custom_symbols: 指定單獨分析之股票代碼清單
        :param no_push: 若為 True 則不發送推播
        """
        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        updated_at = now.strftime("%Y-%m-%d %H:%M:%S")

        mode_text_map = {
            "tw_post": "台股盤後籌碼專報",
            "us_morning": "美股盤後暨全球晨報",
            "full": "每日美台財經全覽"
        }
        market_mode_text = mode_text_map.get(mode, "每日財經日報")
        logger.info(f"開始執行財經分析流水線 [{market_mode_text}] 日期: {date_str}")

        # Step 1: 獲取大盤指數與宏觀情緒
        indices_data = self.macro_fetcher.get_indices_overview(
            us_indices=self.cfg.us_indices,
            tw_indices=self.cfg.tw_indices
        )
        macro_sentiment = {
            "fear_and_greed": self.macro_fetcher.get_fear_and_greed_index(),
            "macro": self.macro_fetcher.get_macro_overview()
        }
        usdtwd_rate = macro_sentiment["macro"].get("usdtwd", {}).get("value", 32.5)
        adr_premiums = self.macro_fetcher.calculate_adr_premium(self.cfg.adr_mappings, usdtwd_rate)

        # Step 2: 決定分析標的
        stocks_to_analyze = self._prepare_stock_list(mode, custom_symbols)
        logger.info(f"待分析標的共 {len(stocks_to_analyze)} 檔: {[s['symbol'] for s in stocks_to_analyze]}")

        # Step 3: 全市場標的深度量化分析 (StockUniverseAnalyzer 深模組)
        analyzed_stocks, data_validation_report, validation_warnings = self.universe_analyzer.analyze_universe(
            stocks_to_analyze=stocks_to_analyze,
            date_str=date_str
        )

        # Step 4: 抓取 24 小時內一手已驗證權威新聞
        symbols_list = [s["symbol"] for s in analyzed_stocks]
        verified_news = self.news_service.fetch_verified_news(symbols_list)
        data_validation_report["verified_news_count"] = len(verified_news)

        # Step 5: 主力籌碼與市場風險警報偵測
        alerts = self.flow_analyzer.analyze_market_alerts(
            stocks_analysis=analyzed_stocks,
            macro_data=macro_sentiment,
            adr_data=adr_premiums
        )

        # Step 6: AI 深度邏輯推理 (含反幻覺數據注入)
        stocks_summary_for_ai = [
            {
                "symbol": s["symbol"],
                "name": s["name"],
                "price": s["stock_data"].get("price"),
                "pct_change": s["stock_data"].get("pct_change"),
                "turnover": s["stock_data"].get("turnover_display"),
                "score": s["score_info"].get("score"),
                "rating": s["score_info"].get("rating"),
                "turnover_strat": s["score_info"].get("turnover_strategy", {}).get("strategy_name"),
                "signals": s["score_info"].get("signals"),
                "levels": s["price_levels"]
            }
            for s in analyzed_stocks
        ]

        system_prompt = PromptBuilder.get_system_prompt()
        user_prompt = PromptBuilder.build_analysis_prompt(
            market_mode=mode,
            indices_data=indices_data,
            macro_data=macro_sentiment,
            adr_data=adr_premiums,
            stocks_summary=stocks_summary_for_ai,
            alerts=alerts,
            verified_news=verified_news
        )

        # 供 AI/量化引擎參考之即時上下文
        ai_context_data = {
            "indices": indices_data,
            "macro_sentiment": macro_sentiment,
            "adr_premiums": adr_premiums,
            "stocks": analyzed_stocks,
            "alerts": alerts,
            "verified_news": verified_news,
            "validation_report": data_validation_report
        }

        logger.info("啟動 AI 深度多空推論引擎...")
        ai_analysis = self.ai_client.generate_analysis(user_prompt, system_prompt, context_data=ai_context_data)

        # Step 7: 組合渲染上下文
        context = {
            "page_title": f"【{market_mode_text}】{date_str}",
            "market_mode": mode,
            "market_mode_text": market_mode_text,
            "date": date_str,
            "updated_at": updated_at,
            "timezone": self.cfg.timezone,
            "dashboard_url": self.cfg.dashboard_url,
            "indices": indices_data,
            "macro_sentiment": macro_sentiment,
            "adr_premiums": adr_premiums,
            "stocks": analyzed_stocks,
            "alerts": alerts,
            "ai_analysis": ai_analysis,
            "verified_news": verified_news,
            "data_validation_report": data_validation_report
        }

        # Step 7: 生成 Markdown 摘要與 HTML 郵件
        markdown_summary = self.md_gen.generate(context)
        context["markdown_summary"] = markdown_summary
        email_html = self.email_gen.generate(context)

        # Step 8: 生成並發布 HTML 儀表板
        dashboard_path = self.html_gen.generate(context, date_str, mode)

        # Step 9: 廣播多通道推播
        push_results = {}
        if not no_push:
            subject = f"【{market_mode_text}】{date_str} 市場定調：{ai_analysis.get('market_mood', '觀望')}"
            push_results = self.dispatcher.dispatch_all(
                markdown_summary=markdown_summary,
                email_html=email_html,
                subject=subject
            )

        logger.info(f"流水線執行圓滿完成！儀表板已輸出至: {dashboard_path}")
        return {
            "status": "success",
            "date": date_str,
            "mode": mode,
            "dashboard_file": str(dashboard_path),
            "analyzed_stocks_count": len(analyzed_stocks),
            "alerts_count": len(alerts),
            "push_results": push_results,
            "markdown_summary": markdown_summary
        }

    def _prepare_stock_list(self, mode: str, custom_symbols: Optional[List[str]]) -> List[Dict[str, Any]]:
        """根據模式或自訂參數準備標的清單"""
        if custom_symbols:
            return [{"symbol": s.strip(), "name": s.strip(), "market": "TW" if s.isdigit() or "." in s else "US"} for s in custom_symbols]

        stocks: List[Dict[str, Any]] = []
        tw_existing = [s["symbol"] for s in self.cfg.tw_stocks]
        us_existing = [s["symbol"] for s in self.cfg.us_stocks]

        if mode == "tw_post":
            # 台股自選
            for s in self.cfg.tw_stocks:
                stocks.append({**s, "market": "TW"})
            # 台股動態掃描焦點股
            if self.cfg.scanner_settings.get("enabled", True):
                focus_tw = self.scanner.scan_tw_focus_stocks(tw_existing)
                for f in focus_tw:
                    stocks.append({**f, "market": "TW"})

        elif mode == "us_morning":
            # 美股自選
            for s in self.cfg.us_stocks:
                stocks.append({**s, "market": "US"})
            # 美股動態掃描焦點股
            if self.cfg.scanner_settings.get("enabled", True):
                focus_us = self.scanner.scan_us_focus_stocks(us_existing)
                for f in focus_us:
                    stocks.append({**f, "market": "US"})
            # 納入台積電現貨以便比對
            if "2330" not in [s["symbol"] for s in stocks]:
                stocks.append({"symbol": "2330", "name": "台積電", "market": "TW", "note": "ADR 折溢價對照"})

        else: # full mode
            for s in self.cfg.tw_stocks:
                stocks.append({**s, "market": "TW"})
            for s in self.cfg.us_stocks:
                stocks.append({**s, "market": "US"})
            if self.cfg.scanner_settings.get("enabled", True):
                focus_tw = self.scanner.scan_tw_focus_stocks(tw_existing)
                for f in focus_tw:
                    stocks.append({**f, "market": "TW"})
                focus_us = self.scanner.scan_us_focus_stocks(us_existing)
                for f in focus_us:
                    stocks.append({**f, "market": "US"})

        return stocks
