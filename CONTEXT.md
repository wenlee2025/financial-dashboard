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

**上櫃證券路由映射 (TPEx OTC Symbol Routing)**:
台灣櫃買中心（OTC）上櫃標的自動路由對應機制（將 `6223`, `1785`, `5274` 等代碼精準映射為 Yahoo Finance `.TWO` 與 TPEx 官方端點），徹底消除 delisted 假性下市與歷史 K 線缺漏。
_Avoid_: 統一使用.TW, 忽略上櫃上市差異

**台指期大盤防護網 (TX Futures Macro Guard)**:
監控外資在台灣期貨交易所（TAIFEX）之台指期淨未平倉合約口數（Net Open Interest）。當外資淨空單超過 35,000 口警戒值時，全局啟動期貨壓盤風險防護，對現貨權值股實施估值與突破打分扣減，嚴防結算殺盤。
_Avoid_: 現貨期貨脫鉤, 盲目追多權值股

**預估動態本益比與 PEG (Forward PE & PEG Ratio)**:
採用未來四季機構共識預估每股盈餘（$\text{Price} / \text{Forward EPS}$）取代歷史落後 TTM EPS，並計算本益成長比（$\text{PEG} = \text{Forward PE} / \text{Expected Growth Rate}$）。當 PEG $< 1.0$ 時，判定具備實質低估之高成長性價比，動態豁免歷史 PE 扣分。
_Avoid_: 後照鏡估值, 歷史PE一刀切

**市場體制自適應調節 (Regime-Adaptive Quant Weighting)**:
量化評分權重隨恐慌貪婪指數（Fear & Greed）與 VIX 波動率自適應切換演算法：在恐慌防守體制下提升籌碼權重至 50%（風控優先），在主升動能體制下提升技術動量至 50%（進攻優先）。
_Avoid_: 固定權重死板化, 忽視市場牛熊環境

**特許與動量雙軌執行 (Two-Tier Core vs Momentum Execution)**:
將標的劃分為「👑 波克夏特許核心 (Tier 1 Core)」與「⚡ 戰術動量 (Tier 2 Momentum)」。核心資產享有左側金字塔分批加碼權（上限 20%）並豁免短線 ATR 停損；動量資產嚴守右側 ATR 停損與 5MA 出清線。
_Avoid_: 所有股票無差別停損, 缺乏資產分級

**深投資評價引擎 (Equity Evaluation Engine)**:
將多因子方向性評分、體制加權、前瞻估值與雙軌交易點位收斂為單一深接縫之評價模組。單次調用直接產出完整投資決策實體（`EquityEvaluationResult`），杜絕評分與點位兩階段中介數據傳遞。
_Avoid_: 分拆打分與點位, 兩步呼叫舞步

**深市場數據閘道 (Market Gateway)**:
統一管理全市場（台美股、OTC 上櫃路由、TWSE T86 籌碼、月營收與宏觀情資）之深數據中樞。對外提供 `fetch_universe_bundles` 一站式產出強型別 `StockMarketBundle`，並內建籌碼焦點股掃描，封閉所有網路並行線程與跨表關聯實作。
_Avoid_: 調用端手動劃分台美股, 手動查表關聯籌碼與營收

**深市場情報引擎 (Market Intelligence Engine)**:
將 24 小時一手新聞採集、市場異常籌碼警報與 AI 深度邏輯推論融為一體的深模組。對外提供 `produce_intelligence` 單一介面產出 `MarketIntelligenceReport`，接縫內部自治消化 LLM 網路異常（503/404/逾時）並無縫降級為量化規則推理。
_Avoid_: 流水線手動組裝 Prompt, 流水線手動捕捉 AI 逾時與降級邏輯

**波克夏戰略防腐橋接器 (Berkshire Strategic Bridge)**:
連接 AI Berkshire（上游戰略大腦）與 財經儀表板（下游戰術執行）的型別化防腐層（Anticorruption Layer）。以 `BerkshireAssetContract` 嚴格約束資產等級（限定 `TIER_1_CORE` 或 `TIER_2_MOMENTUM`）與金字塔加碼上限（不超過 20%），杜絕欄位變更導致的 YAML 結構破壞與靜默故障。
_Avoid_: 直接手動覆寫 YAML, 缺乏型別契約校驗之跨專案拷貝

**決策矩陣 (Decision Matrix)**:
將中長線方向性指標（評級：強力做多至避險做空）與極短線大資金換手力道（資金動能策略：強勢主升至爆量出貨）進行二維交叉映射，產出直覺明確的操作指引。
_Avoid_: 只有評分沒有動作, 脫離量能盲目追高

**實戰決策原型 (Action Archetypes)**:
決策矩陣收斂之 5 大標準交易動作：
1. **🚀 順勢進攻 (Attack)**：做多評級 ＋ 強勢主升。順勢重倉、抱牢主升段。
2. **⏳ 耐心等待 (Wait for Pullback)**：做多評級 ＋ 動能衰竭。高檔量縮背離、切忌急追、等回踩 S1/月線支撐再接。
3. **☕ 逢低潛伏 (Lurk & Accumulate)**：做多評級 ＋ 量縮築底或常態整理。浮額沉澱、支撐上方分批低接。
4. **🚨 警戒撤退 (Alert & Exit)**：任何評級 ＋ 爆量出貨。假突破真倒貨、反彈減碼防守。
5. **🛡️ 嚴禁進場 (Capital Defense)**：偏空/做空評級 ＋ 動能不足或常態整理。無量陰跌、嚴防接刀套牢、空手觀望。
_Avoid_: 模糊的操作建議, 單一維度判斷
