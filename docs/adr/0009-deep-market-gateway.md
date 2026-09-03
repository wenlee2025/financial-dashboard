# ADR 0009: 深市場數據閘道架構 (Deep Market Gateway)

## 狀態
Accepted (已採納)

## 上下文與決策 (Context & Decision)

在代碼架構審查中，原系統的數據採集層高度零散：
- `StockUniverseAnalyzer` 必須手動劃分 `tw_stocks` 與 `us_stocks`，並行調用兩個 fetcher。
- 調用端被迫手動提取 TWSE 三大法人 T86 表，並手動遍歷股票逐一查詢月營收年增率。
- `pipeline.py` 需手動依賴並調度淺模組 `scanner.py`。
- 測試端在測試分析器時，需 Mock 至少 4 個數據源對象。

### 核心重構決策：
1. **建立深模組 `MarketGateway` (`src/data_sources/market_gateway.py`)**：
   - 封閉台美市場分流、OTC 上櫃代碼路由（`.TWO`）、多執行緒批次抓取、TWSE T86 籌碼查表、以及月營收自動關聯。
   - 對外暴露單一深介面：`fetch_universe_bundles(items, date_str) -> Dict[str, StockMarketBundle]`。
2. **吸收淺模組 `MarketScanner`**：
   - 在 `MarketGateway` 內建 `scan_focus_stocks`，消除管線的多餘依賴；保留 `src/data_sources/scanner.py` 作為向後相容轉發器（通過 Deletion Test）。
3. **宏觀情資一站式獲取**：
   - 提供 `get_macro_sentiment_bundle`，單次調用直接打包 Fear & Greed、VIX、台指期淨未平倉合約與 ADR 溢價率。
4. **調用端與測試端徹底簡化**：
   - `StockUniverseAnalyzer` 前 50 行採集編排代碼完全消除，調用端僅需面向單一 `MarketGateway` 介面。
   - 新增端到端單元測試 `tests/test_market_gateway.py`，全套 36 個單元測試通過。

## 後果與價值 (Consequences)
- **槓桿 (Leverage)**：調用端不再需要理解台美分流與查表細節，介面簡潔且語義高度清晰。
- **局部性 (Locality)**：所有數據來源（Yahoo Finance, FinMind, TWSE, TAIFEX, FRED）的抓取協同集中於閘道內部。
- **維護性 (Maintainability)**：未來更換數據供應商（如從 TWSE 爬蟲換成付費 API）時，僅需修改 `MarketGateway`，整個分析管線不受任何波及。
