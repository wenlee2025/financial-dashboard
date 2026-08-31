import json
from typing import Any, Dict, List

class PromptBuilder:
    """專業投資研究與多空深度分析 Prompt 構建器"""

    @staticmethod
    def get_system_prompt() -> str:
        return (
            "你是一位頂級機構量化投研主管與資深首席市場策略師。"
            "請根據所提供的美股與台股最新盤後行情、技術指標、三大法人籌碼動向、宏觀數據、ADR 溢價率及量化評分，"
            "進行嚴謹、客觀且具備高度操作指導價值的深度分析。"
            "語言請一律使用繁體中文（Traditional Chinese），口吻專業、精準、具備機構投研水準，禁止含糊其詞。"
            "請嚴格輸出符合指定 JSON 格式的結構化內容。"
        )

    @staticmethod
    def build_analysis_prompt(
        market_mode: str,
        indices_data: Dict[str, Any],
        macro_data: Dict[str, Any],
        adr_data: List[Dict[str, Any]],
        stocks_summary: List[Dict[str, Any]],
        alerts: List[Dict[str, Any]]
    ) -> str:
        """構建發送給 LLM 的結構化輸入數據與指令"""
        
        mode_title = "台股盤後籌碼專報" if market_mode == "tw_post" else (
            "美股盤後暨全球晨報" if market_mode == "us_morning" else "每日美台財經全覽"
        )

        prompt = f"""
【任務目標】
請為今日「{mode_title}」產出結構化深度投研摘要與操作指引。

【市場最新數據快照】
1. 主要大盤指數：
{json.dumps(indices_data, ensure_ascii=False, indent=2)}

2. 宏觀與情緒指標（含 Fear & Greed, 10Y美債, 匯率）：
{json.dumps(macro_data, ensure_ascii=False, indent=2)}

3. ADR 折溢價率 (美股 ADR vs 台股現貨)：
{json.dumps(adr_data, ensure_ascii=False, indent=2)}

4. 核心自選與焦點個股量化指標（含多空評分、關鍵點位、籌碼買賣超）：
{json.dumps(stocks_summary, ensure_ascii=False, indent=2)}

5. 系統即時偵測之籌碼與市場警報：
{json.dumps(alerts, ensure_ascii=False, indent=2)}

---
【嚴格輸出 JSON 規範】
請務必直接回傳標準 JSON 物件，嚴禁附帶任何其他解說文字，格式如下：
{{
  "executive_summary": "1-2 句話精準定調今日市場核心結論與主線邏輯",
  "market_mood": "市場氛圍 (例如: 強勢多頭 / 震盪整理 / 偏空防守 / 觀望蓄勢)",
  "bullish_arguments": [
    "多方核心論據 1 (結合數據與均線/籌碼)",
    "多方核心論據 2",
    "多方核心論據 3"
  ],
  "bearish_risks": [
    "空方風險與警訊 1 (結合破線/外資賣超/宏觀擾動)",
    "空方風險與警訊 2",
    "空方風險與警訊 3"
  ],
  "catalysts": [
    "近期重大催化劑與關鍵行事曆 1 (如財報日、CPI、FOMC)",
    "重大催化劑 2",
    "重大催化劑 3"
  ],
  "action_checklist": [
    "操作檢查清單 1 (如部位建議比例 %)",
    "操作檢查清單 2 (如停損防守執行重點)",
    "操作檢查清單 3 (如選股進場條件)",
    "操作檢查清單 4 (如風險對沖策略)"
  ]
}}
"""
        return prompt
