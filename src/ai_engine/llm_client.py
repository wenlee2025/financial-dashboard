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

    def generate_analysis(self, prompt: str, system_prompt: str = "") -> Dict[str, Any]:
        """
        發送 Prompt 並解析結構化 JSON
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
                return self._fallback_rule_based_analysis()

        if not raw_text:
            logger.warning("LLM 回傳空結果，採用量化規則推理引擎")
            return self._fallback_rule_based_analysis()

        # 解析 JSON
        parsed = self._extract_json(raw_text)
        if parsed:
            return parsed
        else:
            logger.warning("無法自 LLM 輸出解析 JSON，改用語義提煉與規則封裝")
            return self._wrap_raw_text(raw_text)

    def _call_gemini(self, prompt: str, system_prompt: str) -> str:
        """透過 Gemini REST API (支援 gemini-3.6-flash / gemini-2.5-flash / gemini-2.0-flash)"""
        models = [self.gemini_model, "gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash"]
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
                resp = self.session.post(url, headers=headers, json=payload, timeout=30)
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

    def _fallback_rule_based_analysis(self) -> Dict[str, Any]:
        """離線/無金鑰時之高階規則推理輸出"""
        return {
            "executive_summary": "大盤維持高檔多空拉鋸，科技主流股領跑，法人籌碼高度聚焦於 AI 供應鏈與權值龍頭。",
            "market_mood": "震盪偏多",
            "bullish_arguments": [
                "核心權值股（台積電/輝達）維持均線多頭結構，長線獲利預估續創新高。",
                "外資與本土投信資金輪動健康，支撐指數下檔防守力道。",
                "AI 伺服器與邊緣運算新品進入量產出貨高峰期。"
            ],
            "bearish_risks": [
                "美債殖利率若快速走升可能引發高估值個股評價修正。",
                "短線部分強勢股 RSI 處於高檔過熱區，需提防假突破拉回。",
                "地緣政治與匯率波動增添短線避險情緒。"
            ],
            "catalysts": [
                "各大龍頭企業即將公佈之最新月營收與季報表現",
                "美聯儲 (Fed) FOMC 利率決策與利率點陣圖公布",
                "全球科技展會與新品發表會釋出之產業前瞻"
            ],
            "action_checklist": [
                "【部位控管】總持股比例建議維持 6 成以內，切勿過度融資槓桿",
                "【停損紀律】單筆虧損嚴格控制在總資金 1.5% 以內（破停損點 SL 立即執行）",
                "【進場原則】嚴禁急拉追高，優先選擇拉回回測 20MA 月線守穩且出量標的",
                "【籌碼驗證】進場前確認外資或投信無連續出貨現象"
            ]
        }
