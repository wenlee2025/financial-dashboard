from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional

from ..data_sources.news_feed import NewsFeedService
from .flow_analyzer import FlowAnalyzer
from ..ai_engine import LLMClient, PromptBuilder

logger = logging.getLogger(__name__)

@dataclass
class MarketIntelligenceReport:
    """市場全維情報報告實體 (包含異常警報、時效驗證新聞與 AI/規則推論總結)"""
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    verified_news: List[Dict[str, Any]] = field(default_factory=list)
    ai_analysis: Dict[str, Any] = field(default_factory=dict)
    verified_news_count: int = 0
    stocks_summary: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alerts": self.alerts,
            "verified_news": self.verified_news,
            "ai_analysis": self.ai_analysis,
            "verified_news_count": self.verified_news_count,
            "stocks_summary": self.stocks_summary
        }


class MarketIntelligence:
    """
    深模組：市場全維情報閉環引擎 (Market Intelligence Engine)
    
    【深模組介面 (Deep Seam)】
    produce_intelligence(analyzed_stocks, macro_sentiment, indices_data, adr_premiums, market_mode)
    
    【接縫後隱藏之內部實作】
    1. 24h 權威一手財經新聞抓取、去重與時效防偽
    2. 主力籌碼大幅度異動、美債殖利率跳升與極端恐慌警報掃描
    3. AI 反幻覺 Prompt Payload 結構化生成
    4. LLM 推理調用與網路異常 (503/404/逾時) 之自治降級 (Autonomous Fallback to Rule-based)
    """

    def __init__(
        self,
        news_service: Optional[NewsFeedService] = None,
        flow_analyzer: Optional[FlowAnalyzer] = None,
        ai_client: Optional[LLMClient] = None
    ):
        self.news_service = news_service or NewsFeedService()
        self.flow_analyzer = flow_analyzer or FlowAnalyzer()
        self.ai_client = ai_client or LLMClient()

    def produce_intelligence(
        self,
        analyzed_stocks: List[Dict[str, Any]],
        macro_sentiment: Dict[str, Any],
        indices_data: Optional[Dict[str, Any]] = None,
        adr_premiums: Optional[List[Dict[str, Any]]] = None,
        market_mode: str = "tw_post",
        market_mode_text: str = "每日財經日報",
        data_validation_report: Optional[Dict[str, Any]] = None
    ) -> MarketIntelligenceReport:
        """
        產出綜合市場情報 (新聞、主力異常警報與深度 AI/規則推理報告)
        """
        indices_data = indices_data or {}
        adr_premiums = adr_premiums or []
        data_validation_report = data_validation_report or {}

        # 1. 抓取 24 小時內一手已驗證權威新聞
        symbols_list = [s["symbol"] for s in analyzed_stocks]
        verified_news = self.news_service.fetch_verified_news(symbols_list)
        verified_news_count = len(verified_news)

        # 2. 主力籌碼與市場風險警報偵測
        alerts = self.flow_analyzer.analyze_market_alerts(
            stocks_analysis=analyzed_stocks,
            macro_data=macro_sentiment,
            adr_data=adr_premiums
        )

        # 3. 組裝供 AI/量化推論之標的摘要結構
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
                "levels": s["price_levels"],
                "tier": s.get("tier", "TIER_2_MOMENTUM")
            }
            for s in analyzed_stocks
        ]

        # 4. 構建 Prompt
        system_prompt = PromptBuilder.get_system_prompt()
        user_prompt = PromptBuilder.build_analysis_prompt(
            market_mode=market_mode,
            indices_data=indices_data,
            macro_data=macro_sentiment,
            adr_data=adr_premiums,
            stocks_summary=stocks_summary_for_ai,
            alerts=alerts,
            verified_news=verified_news
        )

        ai_context_data = {
            "indices": indices_data,
            "macro_sentiment": macro_sentiment,
            "adr_premiums": adr_premiums,
            "stocks": analyzed_stocks,
            "alerts": alerts,
            "verified_news": verified_news,
            "validation_report": data_validation_report
        }

        # 5. 自治化 AI/量化推論 (底層內建例外捕獲與自治降級)
        logger.info("啟動市場情報 AI/規則雙引擎推論...")
        ai_analysis = self.ai_client.generate_analysis(
            user_prompt,
            system_prompt,
            context_data=ai_context_data
        )

        return MarketIntelligenceReport(
            alerts=alerts,
            verified_news=verified_news,
            ai_analysis=ai_analysis,
            verified_news_count=verified_news_count,
            stocks_summary=stocks_summary_for_ai
        )
