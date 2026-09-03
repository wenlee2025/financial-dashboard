# ADR 0008: 深投資評價引擎架構 (Deep Equity Evaluation Engine)

## 狀態
Accepted (已採納)

## 上下文與決策 (Context & Decision)

在代碼架構審查中，原系統將「量化評分 (`quant_scoring.py`)」與「點位規劃 (`price_levels.py`)」拆分為兩個獨立淺模組。調用端（`StockUniverseAnalyzer`）必須進行「兩步呼叫舞步（Two-Step Dance）」：
```python
score_info = self.scorer.score_stock(...)
price_levels = self.level_calc.calculate_levels(stock_data, score_info)
```
此結構導致中介資料字典在模組間游移洩漏，且調用端需深度知曉評分與點位間的相依性。

### 核心重構決策：
1. **建立深模組 `EquityEvaluator` (`src/analytics/equity_evaluator.py`)**：
   - 將市場體制自適應調節、技術籌碼基本面多因子、Forward PE/PEG 前瞻估值、期貨大盤防護、以及雙軌金字塔/ATR點位全部收斂至接縫內部。
   - 對外暴露單一深介面：`evaluate(stock_data, inst_data, revenue_data, macro_sentiment) -> EquityEvaluationResult`。
2. **輸出兼顧強型別與向後相容**：
   - `EquityEvaluationResult` 提供強型別屬性存取，並內建 `.to_dict()` 產出包含 `score_info` 與 `price_levels` 的結構，使前端 Jinja2 範本與外部 JSON 導出零中斷相容。
3. **既有模組轉化為純轉發適配器**：
   - `QuantScorer` 與 `PriceLevelCalculator` 轉為輕量代理，確保外部歷史引用不受影響。
4. **測試表面收斂**：
   - 新增 `tests/test_equity_evaluator.py`，跨越單一接縫即可完整斷言整條投資決策鏈。

## 後果與價值 (Consequences)
- **槓桿 (Leverage)**：調用端從繁複的二階段數據拼裝簡化為單行調用。
- **局部性 (Locality)**：所有估值打分、體制加權與交易執行規則集中於同一模組，未來邏輯調整無需跨多檔修改。
- **可測試性 (Testability)**：單元測試不再需要人工 mock 中介的 `score_info` 字典，測試直接對齊真實投資意圖。
