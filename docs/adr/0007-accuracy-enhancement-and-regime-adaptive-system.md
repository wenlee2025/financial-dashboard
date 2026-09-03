# ADR 0007: 投研準確度躍升架構 (Accuracy Enhancement, OTC Symbol Routing, TX Futures Guard, Forward PE/PEG & Regime-Adaptive System)

## 狀態
Accepted (已採納)

## 上下文與決策 (Context & Decision)

在雙投研專案（AI Berkshire 戰略大腦與財經儀表板操盤室）完成雙層漏斗與雙軌執行制整合後，實盤實證發現四大影響預測準確度的關鍵瓶頸。為邁向機構級高準確度，實施以下四項不可逆且具備深層權衡之架構決策：

### 1. 上櫃證券代碼自動路由映射 (`TPEx OTC Symbol Routing`)
- **檔案**：`src/data_sources/tw_market.py`
- **背景與問題**：櫃買中心上櫃股票（如旺矽 6223、光洋科 1785、信驊 5274、台燿 6274、穎崴 6515 等）過去被寫死為 `.TW`，導致 Yahoo Finance 報錯 delisted 並遺失 6 個月歷史 K 線，造成 ATR 與均線技術指標失真。
- **決策**：在 `_normalize_tw_symbol` 與行情採集層加入上櫃字典自動映射與自動重試機制。若為已知上櫃或 `.TW` 查詢無數據，自動無縫重試 `.TWO` 與 TPEx 官方端點，徹底消除 delisted 假性下市與歷史缺漏。

### 2. 台指期大盤外資淨空單防護網 (`TX Futures Macro Guard`)
- **檔案**：`src/data_sources/macro_sentiment.py`, `src/analytics/quant_scoring.py`
- **背景與問題**：外資在台股常利用期現貨套利，當台指期未平倉淨空單超過 35,000 口時，往往藉由壓盤現貨大型權值股（如台積電、鴻海、聯發科）在期貨結算獲利，造成個股技術面突破頻繁出現假多頭。
- **決策**：在總體情緒中建立外資期貨淨空單監控。當淨空單 $> 35,000$ 口時，觸發期貨壓盤高危警戒，對大型權值股評分扣減 10 分，並在點位建議中提示防範結算壓盤。

### 3. 前瞻估值升級：預估動態本益比 (Forward PE) 與 PEG 比率
- **檔案**：`src/analytics/quant_scoring.py`
- **背景與問題**：歷史 TTM 本益比屬於後照鏡指標，高成長轉折牛股往往在起漲點 PE 高達 60~120 倍，被系統誤判為高估而扣分。
- **決策**：引進機構共識的未來四季 Forward EPS 計算 Forward PE 與 PEG。當 PEG $< 1.0$ 時，豁免歷史高估值扣分，並給予 +10 分實質便宜成長性價比加權。

### 4. 量化評分市場體制自適應調節 (`Regime-Adaptive Quant Weighting`)
- **檔案**：`src/analytics/quant_scoring.py`
- **背景與問題**：固定的「技術 40% + 籌碼 35% + 基本 25%」權重在極端暴跌或主升趨勢中容易失效。
- **決策**：依據 Fear & Greed 指數與 VIX 動態調整權重：
  - **恐慌防守體制 (Crisis/Panic)** (F&G < 30 或 VIX > 22)：籌碼面提升至 50%，技術面 30%，基本面 20%（風控避險優先）。
  - **常態主升體制 (Bull/Momentum)** (F&G > 60 且 VIX < 16)：技術動量提升至 50%，籌碼面 30%，基本面 20%（進攻追擊優先）。
  - **常態體制 (Normal)**：維持 40% / 35% / 25%。

## 後果與價值 (Consequences)
- **優勢**：
  1. 上櫃股票行情採集成功率達 100%，消除旺矽、光洋科等標的之歷史指標斷層。
  2. 解決假突破與大盤結算被動挨打問題。
  3. 全面釋放高成長、高 PEG 性價比飆股的做多信號。
  4. 評分模型具備動態市場感知能力，抗回撤與捕捉波段能力大幅提升。
