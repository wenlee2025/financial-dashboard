# Coding Standards & Investment Guardrails (投資審查規範)

本規範為代碼審查 Agent (Reviewer) 與核心開發所共循之最高準則，旨在建構「使 Agent 處於成功之坑 (Pit of Success)」的防護體系。

## 1. 投資決策安全性 (Investment Safety & Anti-Hallucination)
- **剔除社群雜訊 (Social Noise Filter)**：社群討論（如 Reddit, StockTwits, PTT）僅可作為極端散戶情緒指標，**嚴禁**直接作為買賣依據或多空評分權重；決策必須立足於財報、一手權威新聞與交易所籌碼。
- **一手信源溯源 (Primary Source Grounding)**：所有催化劑、重要消息必須綁定精確信源（MOPS 公開資訊觀測站、SEC EDGAR、權威財經通訊社）與時間戳，杜絕 LLM 幻覺新聞。
- **逆勢左側接刀一票否決 (Downside Veto & Stop-Loss)**：
  - 戰術動量資產（Tier 2 Momentum）必須強制綁定右側 ATR 停損與 5MA 出清線。
  - 當外資期貨巨額空單壓盤（超過 35,000 口）或動態大盤破位時，觸發宏觀防護扣減，嚴禁盲目追多。
- **部位上限與凱利限制 (Position Sizing & Kelly Limit)**：單一標的持倉上限最高不超過 20%，金字塔加碼必須以估值安全邊際為前提。

## 2. 代碼架構與深模組設計 (Deep Module Design)
- **深模組設計 (Deep Modules)**：接口必須維持簡潔、高凝聚力，內部隱藏複雜度（如 `EquityEvaluator` 統一產出評估實體，避免評分與點位兩階段零散傳遞）。
- **零 NaN 保證 (Zero-NaN Rendering Guarantee)**：所有向前端 JSON 與 HTML 暴露之數值欄位，遇到缺值或非交易日必須優雅降級為 `"-"` 或 `"暫無報價"`，嚴禁輸出 `$nan` 或 `NaN%`。
- **無權宜之計 (No Workarounds Rule)**：禁止為修復單一 Bug 引入繞過既有管線的臨時 hardcode 邏輯；發現架構偏離必須主動重構根因。

## 3. 跨平台與運行效能 (Runtime Performance & Windows Compatibility)
- **Windows 編碼相容**：終端標準輸出避免未轉義之 Emoji 造成 CP950 崩潰；所有檔案讀寫強制指定 `encoding="utf-8"`。
- **多執行緒與快取防護**：行情數據採集必須透過 `ThreadPoolExecutor` 並行執行；歷史新聞與靜態財報實施時效性快取（Freshness Cache），防止無謂耗盡 API 額度。
