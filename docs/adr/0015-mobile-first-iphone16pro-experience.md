# ADR 0015: 行動優先 iPhone 16 Pro 極致體驗架構 (Mobile-First iPhone 16 Pro Architecture)

## 狀態
Accepted (已採納，確立 iPhone 16 Pro 為第一優先、桌面為第二優先之響應式規範)

## 上下文 (Context)
使用者核心使用情境發生於手機端（首要設備為 iPhone 16 Pro，邏輯 Viewport 寬度 393~402px，長寬比 ~19.5:9，具備動態島與底部 Home Bar），次要設備為電腦端。
過去介面採用桌面優先（Desktop-First）思維，在手機端存在以下體驗瓶頸：
1. 頂部雙層 Sticky Header 佔據超過 110px，扣除動態島與瀏覽器網址列後，可視內容高度僅剩不到 75%。
2. 頂部 Tab 切換位於大拇指單手盲區，違反 Apple Human Interface Guidelines (HIG)。
3. 指數卡片垂直雙欄堆疊，導致首屏無法看見核心定調與重點個股。
4. 個股 4 欄點位在 393px 下過於狹窄，數字易折行且觸控熱區小於 44px。
5. 手指上下滑動時易遭 ECharts 圖表手勢攔截。

## 決策 (Decision)

經設計樹推演與共識審查，確立以下六大行動優先架構決策：

### 1. 手機底部大拇指導航列 (Bottom Navigation Bar)
- 手機端（`< sm`）將三大核心分頁（📊 今日戰情 / 🎯 勝率榜 / 📚 知識庫）下移至螢幕底部浮動毛玻璃導航列。
- 自動適配 iOS `env(safe-area-inset-bottom)`，提供大拇指單手秒級盲操。
- 電腦端（`>= sm`）維持頂部優雅次導航列，保持跨平台一致性。

### 2. 指數與產業標籤橫向吸附滾動 (Horizontal Snap Carousel)
- 手機端將 10 檔大盤指數與產業標籤重構為 CSS Scroll Snap 橫向平滑滾動列。
- 支援手指原生流暢滑動，將直向頁面長度縮短 60% 以上，確保核心定調第一時間映入眼簾。

### 3. 個股 2×2 關鍵點位磁貼與 44px 觸控熱區 (Key Metric Tiles & HIG Compliance)
- 在 393px 寬度下，個股點位由 4 欄並排改為 2×2 大字磁貼（停損/支撐/進場/停利），數字清晰無折行。
- 所有可交互按鈕、展開抽屜之點擊區域均嚴格達到 Apple HIG 規範之 ≥ 44×44px。

### 4. 圖表觸控手勢透傳保護 (ECharts Touch Passthrough)
- 手機端雷達圖鎖定內部滾動縮放，確保全域上下滾動不被 canvas 事件攔截卡頓。
- 寬高自適應手機螢幕黃金比例（高約 280~320px）。

### 5. 控制器緊湊化與卡片體驗鎖定
- 手機端隱藏不適配窄螢幕之 12 欄清單表切換按鈕，預設鎖定為最佳卡片視圖。
- 搜尋與過濾選項緊湊整合，避免佔滿手機垂直螢幕。

### 6. PWA 與 iOS 原生沉浸式配置 (iOS Native Immersion)
- Viewport 配置 `viewport-fit=cover`，自動對齊動態島與邊緣。
- 消除 `-webkit-tap-highlight-color` 點擊灰框，啟用 `-webkit-overflow-scrolling: touch` 彈性滾動。
- 加入 Apple Web App 沉浸式 meta 宣告，支援「加入主畫面」後以獨立無框 App 體驗啟動。

## 後果與價值 (Consequences)
- **iPhone 16 Pro 極致體驗**：單手單指即可順暢瀏覽全部 50 檔標的、激辯細節與雷達對比。
- **桌機無縫相容**：大螢幕維持完整橫向矩陣與卡片/表格雙視圖，零體驗退化。
