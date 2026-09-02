# 財經儀表板 (Financial Dashboard)

本地端運行的跨市場（美股、台股）量化分析、多空評分、關鍵點位計算與儀表板視覺化系統。

## Language

**財經儀表板 (Financial Dashboard)**:
在本地生成並呈現美股與台股量化多空指標、關鍵點位、宏觀情緒與風險警報的單頁/多頁響應式 HTML 應用。
_Avoid_: 炒股軟體, 交易終端

**多空評分 (Bull/Bear Quant Score)**:
基於技術面（40%）、籌碼面（35%）與基本面（25%）多因子綜合計算出的 0-100 分量化指標，劃分為 5 階評級（強力做多、偏多震盪、中立觀望、偏空防守、避險做空）。
_Avoid_: 漲跌預測, 股票明牌

**關鍵點位 (Key Price Levels)**:
包含支撐位（S1 第一防守線、S2 核心強支撐）、阻力位（R1 第一目標、R2 突破目標）、停損防守點（SL）與停利目標（TP）的量化價格區間，並計算風險報酬比（R:R Ratio）。
_Avoid_: 買賣點

**主力籌碼流向 (Smart Money Flows)**:
台股三大法人（外資、投信、自營商）買賣超張數、融資融券增減與土洋對作等異常流向指標。
_Avoid_: 內線資金, 莊家動作

**成交總值 5MA (5-Day Turnover MA / Dollar Volume MA)**:
近 5 個交易日每日成交總金額（股價 × 成交量）之移動平均線，反映實質市場資金之平均承接與換手力道，避免高低價股張數失真。
_Avoid_: 成交量5MA, 張數均線

**成交金額量比 (Turnover Ratio)**:
當日成交總值相對於成交總值 5MA 之比率（$\text{Turnover} / \text{Turnover 5MA}$），用於精確識別實質大資金放量或量縮籌碼沉澱。
_Avoid_: 爆量倍數

**資金動能策略 (Capital Momentum Strategy)**:
結合股價 5MA 位階與成交總值 5MA 斜率之 4 階量化狀態（強勢主升、動能衰竭、量縮築底、爆量出貨）。
_Avoid_: 主力操盤法

**雙源交叉驗證 (Dual-Source Cross Validation)**:
核心財務與行情指標必須同時自至少兩個獨立數據源（如 TWSE 官方 vs yfinance）獲取並計算誤差率（$|\text{Source}_1 - \text{Source}_2| / \text{Source}_1 \times 100\%$），誤差 $\le 1\%$ 方可採信。
_Avoid_: 單源取數, 估計值

**時效性驗證公式 (Freshness Verification Gate)**:
行情與新聞數據之時間戳校驗機制（$\text{Age} = T_{\text{current}} - T_{\text{published}} \le T_{\text{max}}$），防止系統引用陳舊過期資料或離線訓練集殘留記憶。
_Avoid_: 歷史回測資料代替即時

**一手信源溯源 (Primary Source Provenance Grounding)**:
所有新聞、催化劑與事件必須強制綁定官方一手源（公開資訊觀測站 MOPS、SEC EDGAR、權威財經通訊社）之精確發布時間、媒體名稱與原文連結，嚴防 AI 憑空生成幻覺新聞。
_Avoid_: 據傳, 未經證實小道消息

**NaN 數據清洗防護閥門 (NaN Sanitization Guard)**:
在歷史行情採集端強制執行 `dropna(subset=['Close'])` 與 `min_periods=1` 均線平滑，徹底過濾休市/換日交界之未開盤空占位行，杜絕計算鏈 NaN 蔓延。
_Avoid_: 容忍缺值, 填充假均價

**零 NaN 前端渲染保證 (Zero-NaN Rendering Guarantee)**:
前端 UI 與 Markdown 報表全面具備 NaN 容錯過濾，遇無效或尚未開盤之價格、點位與成交量時，一律優雅呈現 `"-"` 或 `"暫無報價"`，100% 杜絕輸出 `$nan` 或 `+nan%`。
_Avoid_: nan字樣展示, 崩潰報錯

**產業鏈上下游連動 (Supply Chain Catalyst Mapping)**:
將美股科技權值母鏈（如 NVDA、AAPL、MSFT）之重大財報或技術突破，自動對齊至台股晶圓代工、散熱模組、伺服器代工與 CoWoS 供應鏈，形成跨市場立體催化視角。
_Avoid_: 孤立分析, 忽略跨市場傳導

**板塊標籤過濾 (Sector Filter Tabs)**:
前端提供秒級動態板塊過濾標籤（如 AI 伺服器與散熱、半導體與 IC 設計、PCB 與載板、美股科技巨頭），支援卡片與表格雙視圖即時聯動篩選。
_Avoid_: 扁平單一清單, 缺乏族群分類

**週日多週期共振 (Multi-Timeframe Trend Resonance)**:
結合週線（中長線大趨勢）與日線（短線進出場點）之技術排列；當週線維持多頭且日線拉回量縮測試支撐時，觸發高勝率波段共振買點。
_Avoid_: 單一週期死角, 忽略大級別趨勢

**並行行情採集 (Parallel Data Ingestion)**:
採用多執行緒執行緒池（ThreadPoolExecutor）並行抓取全市場數十檔標的之歷史行情與技術指標，將採集延遲由分鐘級壓縮至數秒級。
_Avoid_: 循序單線阻塞

**自選股清單管理器 (Watchlist Manager)**:
提供命令列（CLI）、互動式終端（Interactive Menu）與代碼層 API，支援動態新增、批次匯入、刪除、搜尋股票標的，並自動安全同步寫回 `config/watchlist.yaml`。
_Avoid_: 手動修改YAML出錯, 格式損毀

**ADR 折溢價率 (ADR Premium/Discount)**:
台積電美股 ADR（TSM）與台股現貨（2330）按 1:5 換股比率及即時匯率折算之價差百分比。
_Avoid_: 美股聯動
