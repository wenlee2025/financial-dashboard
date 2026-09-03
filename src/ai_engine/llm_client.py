import json
import logging
import re
from typing import Any, Dict, Optional
import requests

logger = logging.getLogger(__name__)

class LLMClient:
    """統一 AI 推論引擎客戶端 (預設支援 Gemini，具備 OpenAI / Claude 與離線容錯)"""

    def __init__(
        self,
        provider: str = "gemini",
        gemini_key: Optional[str] = None,
        openai_key: Optional[str] = None,
        anthropic_key: Optional[str] = None,
        gemini_model: str = "gemini-2.5-flash"
    ):
        self.provider = provider.lower()
        self.gemini_key = gemini_key
        self.openai_key = openai_key
        self.anthropic_key = anthropic_key
        self.gemini_model = gemini_model
        self.session = requests.Session()

    def generate_analysis(self, prompt: str, system_prompt: str = "", context_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        發送 Prompt 並解析結構化 JSON；若無 API 則使用動態量化推理
        """
        # 1. 根據配置選擇 Provider
        raw_text = ""
        if (self.provider == "gemini" or not self.provider) and self.gemini_key:
            raw_text = self._call_gemini(prompt, system_prompt)
        elif self.provider == "openai" and self.openai_key:
            raw_text = self._call_openai(prompt, system_prompt)
        elif self.provider == "claude" and self.anthropic_key:
            raw_text = self._call_claude(prompt, system_prompt)
        else:
            # 若無任何 API Key，嘗試自動偵測
            if self.gemini_key:
                raw_text = self._call_gemini(prompt, system_prompt)
            elif self.openai_key:
                raw_text = self._call_openai(prompt, system_prompt)
            else:
                logger.info("未偵測到任何 LLM API Key，啟用系統內建量化規則推理引擎")
                return self.synthesize_rule_based_analysis(context_data)

        if not raw_text:
            logger.warning("LLM 回傳空結果，採用量化規則推理引擎")
            return self.synthesize_rule_based_analysis(context_data)

        # 解析 JSON
        parsed = self._extract_json(raw_text)
        if parsed:
            return parsed
        else:
            logger.warning("無法自 LLM 輸出解析 JSON，改用語義提煉與規則封裝")
            return self._wrap_raw_text(raw_text)

    def _call_gemini(self, prompt: str, system_prompt: str) -> str:
        """透過 Gemini REST API (支援 gemini-2.5-flash / gemini-2.0-flash / gemini-1.5-flash-latest)"""
        models = list(dict.fromkeys([self.gemini_model, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-1.5-pro-latest"]))
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": f"{system_prompt}\n\n{prompt}"}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 4096,
                    "responseMimeType": "application/json"
                }
            }
            try:
                resp = self.session.post(url, headers=headers, json=payload, timeout=45)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                else:
                    logger.warning(f"Gemini API ({model}) 回應代碼 {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.warning(f"Gemini API ({model}) 調用例外: {e}")
        return ""

    def _call_openai(self, prompt: str, system_prompt: str) -> str:
        """透過 OpenAI REST API"""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_key}"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }
        try:
            resp = self.session.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                logger.warning(f"OpenAI API 回應代碼 {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"OpenAI API 調用例外: {e}")
        return ""

    def _call_claude(self, prompt: str, system_prompt: str) -> str:
        """透過 Claude REST API"""
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.anthropic_key or "",
            "anthropic-version": "2023-06-01"
        }
        payload = {
            "model": "claude-3-5-haiku-20241022",
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,
            "temperature": 0.2
        }
        try:
            resp = self.session.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                contents = data.get("content", [])
                if contents:
                    return contents[0].get("text", "")
        except Exception as e:
            logger.warning(f"Claude API 調用例外: {e}")
        return ""

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """自 LLM 輸出中安全提取 JSON"""
        text = text.strip()
        try:
            return json.loads(text)
        except Exception:
            pass

        # 嘗試利用正規表達式搜尋 ```json ... ``` 或 { ... }
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass

        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        return None

    def _wrap_raw_text(self, text: str) -> Dict[str, Any]:
        """純文字封裝"""
        return {
            "executive_summary": "市場維持結構性分化，聚焦權值股與外資籌碼動向。",
            "market_mood": "謹慎偏多",
            "bullish_arguments": [
                "AI 算力與伺服器供應鏈需求強勁，主流族群維持多頭排列。",
                "大盤守穩關鍵均線，下檔具備均線支撐動能。"
            ],
            "bearish_risks": [
                "高檔追高意願降低，注意短線獲利了結震盪。",
                "美債殖利率與匯率波動對評價面產生短線擾動。"
            ],
            "catalysts": [
                "即將發布之主要科技巨頭季報與法說會展望",
                "美國非農就業與 CPI 通膨數據公告"
            ],
            "action_checklist": [
                "持股水位控制於 50% - 70%，保留彈性現金",
                "嚴格遵循停損停利機制，破線標的不戀棧",
                "避免在開盤前 15 分鐘衝動追高，等待拉回量縮測試支撐"
            ],
            "raw_output": text
        }

    def synthesize_rule_based_analysis(self, context_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """根據真實行情數據動態合成深度多空投研結論 (100% 離線/免 API)"""
        if not context_data:
            return self._fallback_rule_based_analysis()

        macro = context_data.get("macro_sentiment", {})
        fg_score = macro.get("fear_and_greed", {}).get("score", 50.0)
        fg_zh = macro.get("fear_and_greed", {}).get("rating_zh", "中立")
        us10y = macro.get("macro", {}).get("us10y", {}).get("value", 0.0)
        stocks = context_data.get("stocks", [])
        adr_list = context_data.get("adr_premiums", [])
        alerts = context_data.get("alerts", [])

        # 統計多空廣度
        if stocks:
            avg_score = round(sum(s.get("score_info", {}).get("score", 50) for s in stocks) / len(stocks), 1)
            bull_count = sum(1 for s in stocks if s.get("score_info", {}).get("score", 50) >= 60)
            bear_count = sum(1 for s in stocks if s.get("score_info", {}).get("score", 50) < 42)
            top_bulls = sorted(stocks, key=lambda x: x.get("score_info", {}).get("score", 0), reverse=True)[:3]
            top_bears = sorted(stocks, key=lambda x: x.get("score_info", {}).get("score", 100))[:2]
            
            top_bull_names = "、".join([f"{s.get('name')}({s.get('score_info',{}).get('score')}分)" for s in top_bulls if s.get("score_info",{}).get("score",0) >= 60])
        else:
            avg_score = 50.0
            bull_count = 0
            bear_count = 0
            top_bull_names = "權值主流股"
            top_bulls = []
            top_bears = []

        # 判定市場氛圍
        if avg_score >= 70:
            market_mood = "強力多頭攻堅"
            exec_summary = f"監控池多頭動能強勁（平均評分 {avg_score} 分），{bull_count} 檔標的站上強勢多頭格局；{top_bull_names} 領軍表態，籌碼高度集中，建議順勢偏多操作。"
        elif avg_score >= 58:
            market_mood = "偏多震盪輪動"
            exec_summary = f"大盤與焦點股維持偏多架構（平均評分 {avg_score} 分），多頭標的佔 {bull_count}/{len(stocks)} 檔；資金輪動至 {top_bull_names}，拉回守穩支撐可分批佈局。"
        elif avg_score >= 45:
            market_mood = "區間分化整理"
            exec_summary = f"市場處於高檔震盪整理期（平均評分 {avg_score} 分），多空標的分化加劇（多方 {bull_count} 檔 / 空方 {bear_count} 檔），建議縮減追高部位，嚴守區間點位操作。"
        else:
            market_mood = "偏空防守觀望"
            exec_summary = f"市場走勢轉趨防守（平均評分 {avg_score} 分），破線避險標的增至 {bear_count} 檔，建議降低持股水位，嚴格執行停損防守。"

        # 動態多方論據
        bullish_args = []
        if top_bulls:
            b1 = top_bulls[0]
            sig = b1.get("score_info", {}).get("signals", ["均線維持多頭架構"])[0]
            bullish_args.append(f"主流領頭羊 {b1.get('name')} ({b1.get('symbol')}) 量化評分達 {b1.get('score_info',{}).get('score')} 分，{sig}。")
        if adr_list:
            adr = adr_list[0]
            if adr.get("premium_pct", 0) > 0:
                bullish_args.append(f"{adr.get('adr_symbol')} ADR 對現貨維持溢價 +{adr.get('premium_pct')}% (換算每股 TWD ${adr.get('adr_parity_twd')})，提供台股下檔堅實保護。")
        bullish_args.append(f"市場恐慌貪婪指數位於 {fg_score} 分 ({fg_zh})，市場情緒維持在健康區間未現恐慌拋售。")
        bullish_args.append("AI 伺服器、散熱、先進封裝等主流族群法人籌碼進駐意願強烈，產業趨勢明確。")

        # 動態空方風險
        bearish_risks = []
        if us10y > 4.0:
            bearish_risks.append(f"美債 10 年期殖利率徘徊於 {us10y}% 高檔，對高估值科技股本益比形成一定壓制。")
        if top_bears and top_bears[0].get("score_info", {}).get("score", 100) < 45:
            tb = top_bears[0]
            bearish_risks.append(f"部分弱勢標的（如 {tb.get('name')} {tb.get('symbol')}）技術面破線，評分降至 {tb.get('score_info',{}).get('score')} 分，防範補跌效應。")
        bearish_risks.append("盤面高檔換手加劇，爆量不漲個股需提防主力短線獲利了結與假突破風險。")
        bearish_risks.append("國際地緣政治與全球貿易政策不確定性，恐增添短線匯率與外資資金波動。")

        # 重大催化劑與一手驗證事件
        verified_news = context_data.get("verified_news", [])
        if verified_news:
            catalysts = [
                f"【{n.get('publisher')}】{n.get('title')} ({n.get('age_text', '最新')})"
                for n in verified_news[:4]
            ]
        else:
            catalysts = [
                "各大科技龍頭（台積電、輝達、聯發科）即將公布之最新月營收與季報表現",
                "美聯儲 (Fed) FOMC 利率決策會議與全球央行利率政策走向",
                "低軌衛星、GB200 AI 伺服器機櫃與液冷散熱模組量產出貨進度"
            ]

        # 操作檢查清單
        checklist = [
            f"【部位控管】總持股水位建議控制在 {'60%-75%' if avg_score >= 60 else '40%-55%'}，保留彈性現金",
            "【停損紀律】單筆部位嚴格設定於關鍵停損防守點 (SL)，跌破立即停損出場",
            "【進場原則】嚴禁急拉追高，優先選擇拉回回測第一支撐 (S1) 且量縮守穩之強勢股",
            "【籌碼檢驗】進場前確認外資與投信未出現連續性大額調節或土洋對作失衡"
        ]

        return {
            "executive_summary": exec_summary,
            "market_mood": market_mood,
            "bullish_arguments": bullish_args[:4],
            "bearish_risks": bearish_risks[:4],
            "catalysts": catalysts,
            "action_checklist": checklist
        }

    def _fallback_rule_based_analysis(self) -> Dict[str, Any]:
        """預設規則輸出"""
        return self.synthesize_rule_based_analysis(None)

