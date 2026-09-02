# ADR 0006: 深度模組重構 (Deep Modules, Clean Seams & Unified Notifier Architecture)

## 狀態
Accepted (已採納)

## 上下文與決策 (Context & Decision)
為貫徹《Codebase Design》的深模組設計原則（Small Interface, Deep Implementation, High Locality, High Leverage），本重構針對四大核心模組進行解耦與深化：

### 1. 抽取單一技術指標引擎 (`TechnicalsEngine`)
- **檔案**：`src/analytics/technicals.py`
- **決策**：將原本散落於台股與美股獲取器中的技術指標公式（MA、週均線、成交總值5MA、RSI、MACD、ATR、布林通道）收斂至 `TechnicalsEngine`，提供標準化 DataFrame 運算與零 NaN 保證。

### 2. 封裝全市場標的分析器 (`StockUniverseAnalyzer`)
- **檔案**：`src/analytics/stock_universe_analyzer.py`
- **決策**：在流水線（Pipeline）與多個子模組（行情抓取、法人籌碼、營收、多週期評分、關鍵點位、產業鏈圖譜、數據驗證）之間設立乾淨接縫（Clean Seam）。
- **介面**：`analyze_universe(stocks_to_analyze, date_str)` 一站式完成批次並行採集、多維度分析與驗證，使流水線調度代碼大幅簡化。

### 3. 多型推播調度器 (`BaseNotifier` & `NotificationDispatcher`)
- **檔案**：`src/notifiers/base.py`
- **決策**：定義統一抽象介面 `BaseNotifier`，各通訊渠道（Telegram, Discord, LINE, Slack, Email）實作 `send(title, markdown_content, html_content=None)` 方法。`NotificationDispatcher` 採插件式（Plugin-based）管理已啟用的適配器，消除大量 `if/else` 硬編碼。
