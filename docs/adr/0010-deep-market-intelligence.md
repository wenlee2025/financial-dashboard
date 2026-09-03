# ADR 0010: 深市場情報引擎架構 (Deep Market Intelligence Engine)

## 狀態
Accepted (已採納)

## 上下文與決策 (Context & Decision)

在原系統流水線（`src/pipeline.py`）中，市場情報與推論生成由三個分離的步驟手動編排：
- 調用 `news_service.fetch_verified_news` 獲取即時新聞。
- 調用 `flow_analyzer.analyze_market_alerts` 偵測籌碼異常與市場警報。
- 手動遍歷 `analyzed_stocks` 拼裝 Prompt payload，調用 `ai_client.generate_analysis`。
- 流水線必須承擔 LLM API 故障、HTTP 503/404 或連線逾時的例外處理與降級邏輯。

此結構破壞了流水線的純粹調度職責，讓主流程高度耦合了新聞抓取、警報偵測與 AI 提示詞細節。

### 核心重構決策：
1. **建立深模組 `MarketIntelligence` (`src/analytics/market_intelligence.py`)**：
   - 將新聞時效驗證、市場風險警報偵測、Prompt 結構化組裝、以及 LLM 推論與自治降級（Autonomous Fallback）完整收斂進單一模組。
   - 對外暴露單一深介面：`produce_intelligence(...) -> MarketIntelligenceReport`。
2. **強保證與自治降級**：
   - 接縫內部封裝所有 LLM 例外，當 Gemini API 發生 503 尖峰或 45s 逾時時，自動無縫啟用本機量化規則推理引擎（Rule-based Synthesis），對調用端保證「永遠回傳有效且反幻覺的報告」。
3. **消除流水線三步編排**：
   - 流水線主流程減少 50+ 行程式碼，以單次調用直接獲取包含新聞、警報與 AI 觀點的完整情報實體。
4. **測試表面收斂**：
   - 新增端到端單元測試 `tests/test_market_intelligence.py`，全套 38 個單元測試通過。

## 後果與價值 (Consequences)
- **槓桿 (Leverage)**：主流程徹底擺脫 AI 例外處理與字串拼接，情報獲取與推論一體化。
- **局部性 (Locality)**：Prompt 模板、LLM 降級策略與異常過濾邏輯完全隔離在情報模組內。
- **穩健性 (Robustness)**：LLM 服務中斷不再對流水線造成任何破壞性衝擊。
