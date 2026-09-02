# ADR 0004: NaN 缺失數據源頭清洗與全鏈路韌性架構

## 狀態
Accepted (已採納)

## 上下文與決策 (Context & Decision)
在非開盤時段、午夜跨日更新或國際休市交界時，行情數據來源（如 yfinance）常會自動生成未開盤之空占位行（`Close = NaN`），若未予清洗會導致整條量化計算鏈（均線、點位、風報比、評分）產生 `NaN` 蔓延，並在前端表格呈現 `$nan`、`+nan%` 等失真畫面。

本架構決策建立三層全鏈路防護：

1. **數據採集源頭清洗 (Ingestion Sanitization)**：
   - 抓取歷史 K 線後，強制執行：
     ```python
     df = df.dropna(subset=["Close", "Open", "High", "Low"])
     df = df[df["Close"] > 0]
     ```
   - 確保 `df.iloc[-1]` 永遠鎖定最新有效成交日。
   - 所有滾動均線（MA5/10/20/60）、成交總值（Turnover MA5）及 ATR 加入 `min_periods=1`，杜絕計算過程產生 NaN。

2. **量化與點位層安全守衛 (Analytics Safety Guard)**：
   - 導入 `_safe_float` 檢驗函數，對所有數值輸入檢驗 `math.isnan(val)`。
   - 若現價無效或 `<= 0`，自動回退安全結構化空點位字典（`entry_zone = "-"`，`s1 = 0.0`，`sl = 0.0`，`tp = 0.0`），永不在字典中傳播 `nan`。

3. **前端零 NaN 渲染防護 (Zero-NaN Frontend Guarantee)**：
   - 在 Jinja2 模板中對價格、漲跌幅、點位與成交量加入健全防護，任何非正數或 NaN 數值一律優雅顯示為 `"-"`，徹底杜絕畫面出現 `$nan` 字樣。
