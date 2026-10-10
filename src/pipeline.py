import datetime
import logging
from typing import Any, Dict, List, Optional

from .config import Config, config as default_config
from .data_sources import TWMarketFetcher, USMarketFetcher, MacroSentimentFetcher, MarketScanner, MarketGateway
from .data_sources.news_feed import NewsFeedService
from .analytics import QuantScorer, PriceLevelCalculator, FlowAnalyzer, EquityEvaluator, MarketIntelligence
from .analytics.data_validator import DataValidator
from .analytics.supply_chain import SupplyChainMapper
from .analytics.stock_universe_analyzer import StockUniverseAnalyzer
from .ai_engine import LLMClient
from .generators import HTMLDashboardGenerator, MarkdownSummaryGenerator, EmailNewsletterGenerator
from .notifiers import NotificationDispatcher

logger = logging.getLogger(__name__)

class FinancialDashboardPipeline:
    """每日財經分析與儀表板主流程流水線 (深模組調度中樞)"""

    def __init__(self, cfg: Optional[Config] = None):
        self.cfg = cfg or default_config

        # 1. 深數據閘道層 (MarketGateway)
        self.market_gateway = MarketGateway(
            tw_fetcher=TWMarketFetcher(finmind_token=self.cfg.finmind_token),
            us_fetcher=USMarketFetcher(finnhub_key=self.cfg.finnhub_key),
            macro_fetcher=MacroSentimentFetcher(fred_key=self.cfg.fred_key)
        )
        self.tw_fetcher = self.market_gateway.tw_fetcher
        self.us_fetcher = self.market_gateway.us_fetcher
        self.macro_fetcher = self.market_gateway.macro_fetcher
        self.scanner = MarketScanner(self.tw_fetcher, self.us_fetcher, self.cfg.scanner_settings)
        self.news_service = NewsFeedService(max_age_hours=24.0)

        # 2. 深度標的評價與分析協同層
        self.evaluator = EquityEvaluator(weights=self.cfg.scoring_weights, tiers=self.cfg.rating_tiers)
        self.scorer = QuantScorer(weights=self.cfg.scoring_weights, tiers=self.cfg.rating_tiers)
        self.level_calc = PriceLevelCalculator()
        self.flow_analyzer = FlowAnalyzer()
        self.validator = DataValidator(max_allowed_price_diff_pct=1.0, max_news_age_hours=24.0)
        self.supply_chain_mapper = SupplyChainMapper()
        self.universe_analyzer = StockUniverseAnalyzer(
            gateway=self.market_gateway,
            evaluator=self.evaluator,
            supply_chain_mapper=self.supply_chain_mapper,
            validator=self.validator
        )

        # 3. 市場全維情報與推論層 (MarketIntelligence)
        self.ai_client = LLMClient(
            provider=self.cfg.ai_provider,
            gemini_key=self.cfg.gemini_api_key,
            openai_key=self.cfg.openai_api_key,
            anthropic_key=self.cfg.anthropic_api_key,
            gemini_model=self.cfg.gemini_model
        )
        self.market_intelligence = MarketIntelligence(
            news_service=self.news_service,
            flow_analyzer=self.flow_analyzer,
            ai_client=self.ai_client
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
            "macro": self.macro_fetcher.get_macro_overview(),
            "tx_futures": self.macro_fetcher.get_tx_futures_net_oi()
        }
        usdtwd_rate = macro_sentiment["macro"].get("usdtwd", {}).get("value", 32.5)
        adr_premiums = self.macro_fetcher.calculate_adr_premium(self.cfg.adr_mappings, usdtwd_rate)

        # Step 2: 決定分析標的
        stocks_to_analyze = self._prepare_stock_list(mode, custom_symbols)
        logger.info(f"待分析標的共 {len(stocks_to_analyze)} 檔: {[s['symbol'] for s in stocks_to_analyze]}")

        # Step 3: 全市場標的深度量化分析 (含自適應市場體制與期現貨大盤防護)
        analyzed_stocks, data_validation_report, validation_warnings = self.universe_analyzer.analyze_universe(
            stocks_to_analyze=stocks_to_analyze,
            date_str=date_str,
            macro_sentiment=macro_sentiment
        )

        # Step 4: 透過深模組 MarketIntelligence 一站式產出市場情報 (新聞、異常警報與深度 AI/規則推理報告)
        intel_report = self.market_intelligence.produce_intelligence(
            analyzed_stocks=analyzed_stocks,
            macro_sentiment=macro_sentiment,
            indices_data=indices_data,
            adr_premiums=adr_premiums,
            market_mode=mode,
            market_mode_text=market_mode_text,
            data_validation_report=data_validation_report
        )
        verified_news = intel_report.verified_news
        data_validation_report["verified_news_count"] = intel_report.verified_news_count
        alerts = intel_report.alerts
        ai_analysis = intel_report.ai_analysis

        # Step 5: 計算六大維度多股雷達指標 (Radar Metrics)
        try:
            from src.analytics.radar_metrics import RadarMetricsCalculator
            radar_comparison = RadarMetricsCalculator.compute_universe_radar(
                analyzed_stocks=analyzed_stocks,
                macro_sentiment=macro_sentiment
            )
        except Exception as e:
            logger.warning(f"六大維度雷達指標計算略過: {e}")
            radar_comparison = {"dimensions": [], "stocks": [], "series": []}

        # Step 6: 投資組合資產管家盯市重估與四大大師論文漂移審計 (Portfolio Governor)
        try:
            from src.analytics.portfolio_governor import PortfolioGovernor
            governor = PortfolioGovernor(portfolio_path=self.cfg.data_dir / "portfolio.json")
            portfolio_audit = governor.audit_and_rebalance(
                analyzed_stocks=analyzed_stocks,
                macro_sentiment=macro_sentiment,
                audit_date=date_str
            )
            portfolio_summary = portfolio_audit.to_dict()
        except Exception as e:
            logger.warning(f"投資組合資產管家審計略過: {e}")
            portfolio_summary = {
                "audit_date": date_str,
                "total_cost": 0.0,
                "total_market_value": 0.0,
                "unrealized_pnl": 0.0,
                "overall_return_pct": 0.0,
                "holdings": [],
                "drift_items": [],
                "hard_drift_count": 0,
                "soft_drift_count": 0
            }

        # Step 6.5: 焦點標的多智能體激辯與風控委員會裁決 (Deliberation Engine)
        deliberation_verdicts = {}
        try:
            from src.analytics.deliberation_engine import DeliberationEngine

            # 1. 精準篩選受審查標的 (持倉股 + Top 5 多空極端股 + 多空分歧爭議股)
            holding_syms = {str(h.get("symbol", "")).strip() for h in portfolio_summary.get("holdings", [])}
            selected_symbols = set()
            target_stocks = []

            # (A) 投資組合實盤持倉
            for s in analyzed_stocks:
                sym = str(s.get("symbol", "")).strip()
                if sym in holding_syms and sym not in selected_symbols:
                    selected_symbols.add(sym)
                    target_stocks.append(s)

            # (B) 前 5 檔多頭強勢股與後 5 檔空頭破線股
            for s in analyzed_stocks[:5]:
                sym = str(s.get("symbol", "")).strip()
                if sym not in selected_symbols:
                    selected_symbols.add(sym)
                    target_stocks.append(s)
            
            if len(analyzed_stocks) >= 10:
                for s in analyzed_stocks[-5:]:
                    sym = str(s.get("symbol", "")).strip()
                    if sym not in selected_symbols:
                        selected_symbols.add(sym)
                        target_stocks.append(s)

            # (C) 多空分歧爭議股 (高量化分但遇破線或天量出貨)
            for s in analyzed_stocks:
                sym = str(s.get("symbol", "")).strip()
                if sym in selected_symbols:
                    continue
                score = float(s.get("score_info", {}).get("score", 50.0) or 50.0)
                price = float(s.get("stock_data", {}).get("price", 0.0) or 0.0)
                sl = float(s.get("price_levels", {}).get("stop_loss", 0.0) or 0.0)
                turnover_ratio = float(s.get("stock_data", {}).get("turnover_ratio", 1.0) or 1.0)
                pct = float(s.get("stock_data", {}).get("pct_change", 0.0) or 0.0)
                
                is_divergent = (score >= 60.0 and sl > 0 and price < sl) or (score >= 60.0 and turnover_ratio > 2.5 and pct < -1.0)
                if is_divergent and len(target_stocks) < 15:
                    selected_symbols.add(sym)
                    target_stocks.append(s)

            logger.info(f"多智能體激辯定向鎖定審查共 {len(target_stocks)} 檔: {[s.get('symbol') for s in target_stocks]}")

            # 2. 執行階層激辯並落實「風控委員會一票否決 (Downside Veto)」
            for s in target_stocks:
                sym = str(s.get("symbol", "")).strip()
                if not sym:
                    continue
                verdict = DeliberationEngine.deliberate(s, eval_date=date_str)
                v_dict = verdict.to_dict()
                deliberation_verdicts[sym] = v_dict
                s["deliberation_verdict"] = v_dict

                # 觸發一票否決時，強制覆寫決策動作為警戒撤退/嚴禁進場
                if verdict.veto_triggered:
                    s["decision_matrix"] = {
                        "action_code": "alert_exit" if "警戒撤退" in verdict.action else "defense",
                        "action_badge": verdict.action,
                        "badge_color": "rose",
                        "sort_rank": 0,
                        "guidance": verdict.risk_committee_summary,
                        "confidence": "HIGH",
                        "veto_overridden": True
                    }
                    s["veto_triggered"] = True
                    s["divergence_warning"] = True
                    logger.warning(f"標的 {sym} ({s.get('name')}) 觸發風控一票否決: {verdict.action}")
                else:
                    s["veto_triggered"] = False
                    s["divergence_warning"] = verdict.divergence_warning

        except Exception as e:
            logger.warning(f"多智能體激辯引擎執行略過: {e}")

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
            "data_validation_report": data_validation_report,
            "radar_comparison": radar_comparison,
            "portfolio_summary": portfolio_summary,
            "deliberation_verdicts": deliberation_verdicts
        }

        # Step 7: 生成 Markdown 摘要與 HTML 郵件
        markdown_summary = self.md_gen.generate(context)
        context["markdown_summary"] = markdown_summary
        email_html = self.email_gen.generate(context)

        # Step 7.5: 滾動更新 WikiSkill 復盤統計 (Post-Mortem Verification)
        try:
            from src.evolution.historical_bootstrapper import HistoricalBootstrapper
            bootstrapper = HistoricalBootstrapper(data_dir=str(self.cfg.data_dir), output_dir=str(self.cfg.data_dir))
            pm_report = bootstrapper.bootstrap_from_existing_snapshots()
            context["post_mortem_report"] = pm_report.to_dict()
        except Exception as e:
            logger.warning(f"WikiSkill 復盤統計更新略過: {e}")

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

    def run_backtest(self, symbols: List[str], period: str = "1y") -> Dict[str, Any]:
        """
        執行多標的走動量化回測 (BacktestEngine)
        :param symbols: 欲回測之股票代碼列表 (例: ['2330', 'NVDA'])
        :param period: 歷史資料期間 (預設 1y)
        """
        import yfinance as yf
        import json
        from .analytics.backtest_engine import BacktestEngine

        results: Dict[str, Any] = {}
        logger.info(f"啟動量化回測引擎，回測標的: {symbols}，期間: {period}...")

        for sym in symbols:
            raw_sym = sym.strip().upper()
            if raw_sym.isdigit() or raw_sym in getattr(self.tw_fetcher, "OTC_SYMBOLS", set()):
                query_sym = self.tw_fetcher._normalize_tw_symbol(raw_sym)
            else:
                query_sym = raw_sym

            try:
                t = yf.Ticker(query_sym)
                df = t.history(period=period)
                if df.empty or len(df) < 30:
                    logger.warning(f"標的 {raw_sym} ({query_sym}) 歷史數據不足，無法執行回測")
                    continue
                res = BacktestEngine.run_backtest(symbol=raw_sym, df=df)
                results[raw_sym] = res.to_dict()
            except Exception as e:
                logger.error(f"標的 {raw_sym} 回測執行失敗: {e}")

        # 輸出結構化結果至 docs/data/backtest_results.json
        out_file = self.cfg.data_dir / "backtest_results.json"
        try:
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            logger.info(f"回測完成，結果已存至: {out_file}")
        except Exception as e:
            logger.warning(f"儲存回測結果檔案失敗: {e}")

        return results

