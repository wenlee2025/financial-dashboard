# ADR 0005: 跨市場產業鏈圖譜、板塊篩選、多週期共振與並行採集架構

## 狀態
Accepted (已採納)

## 上下文與決策 (Context & Decision)
為全面升級儀表板的分析深度、族群可讀性與執行效能，本架構決策實施四項核心升級：

### 1. 跨市場產業鏈圖譜 (Supply Chain Catalyst Mapping)
- 建立 `src/analytics/supply_chain.py` 產業鏈映射字典與催化關聯器。
- 將台股 37+ 檔自選標的依核心產業鏈進行分組（如 `AI 伺服器與散熱`、`半導體與先進封裝`、`IC 設計與矽智財`、`PCB 與銅箔基板`、`光通訊與網通`、`被動元件與其他`）。
- 當美股母鏈龍頭（如 NVDA、AAPL、MSFT、AVGO）或同產業龍頭出現大漲/催化事件時，自動在關聯台股標的標註「美股母鏈連動」並提供跨市場連動分析。

### 2. 前端動態板塊標籤切換列 (Industry Sector Tabs)
- 在 `templates/dashboard_template.html` 標的區塊頂部新增板塊標籤列：
  - `[ 🌐 全部 ]`
  - `[ 🔥 主力焦點 ]`
  - `[ 🤖 AI 伺服器與散熱 ]`
  - `[ ⚡ 半導體與IC設計 ]`
  - `[ 📦 PCB與載板 ]`
  - `[ 🇺🇸 美股科技巨頭 ]`
- 透過 JavaScript 即時過濾卡片視圖與表格視圖，支援與既有的市場/評級/關鍵字搜尋進行聯動篩選。

### 3. 週日多週期趨勢共振評分 (Weekly + Daily Trend Resonance)
- 在 `_calculate_technicals` 中根據日 K 線數據計算週級別均線（如 週 5MA、週 20MA），或重採樣為週 K 線評估中長線大趨勢。
- 當「週線多頭排列」且「日線拉回測試 20MA 月線」時，在 `QuantScorer` 給予 `+8` 分「週日多週期共振加分」，並在信號清單中標註「✓ 週日雙週期共振：大趨勢向上且短線拉回守穩」。

### 4. 行情並行採集加速 (Parallel Data Ingestion)
- 在 `TWMarketFetcher` 與 `USMarketFetcher` 中提供 `get_batch_stock_data()` 方法，透過 `concurrent.futures.ThreadPoolExecutor(max_workers=10)` 並行拉取數據。
- 將原本 48 檔標的串行抓取的 60~90 秒大幅壓縮至 10~15 秒內完成。
