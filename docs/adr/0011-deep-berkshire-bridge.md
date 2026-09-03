# ADR 0011: 波克夏跨專案型別化同步契約架構 (Deep Berkshire Bridge)

## 狀態
Accepted (已採納)

## 上下文與決策 (Context & Decision)

在雙專案架構中：
- `AI Berkshire` 負責長線護城河、商業模式、四大家投資哲學（巴菲特、芒格、段永平、李錄）與季度論文重審。
- `財經儀表板` 負責每日高頻籌碼追蹤、5MA 資金動能與技術點位風報比執行。

過去兩者缺乏型態化合約，下游若要獲取上游的標的分級與掛單規則，通常依賴臨時腳本直接讀寫 `config/watchlist.yaml`。若上游欄位定義調整或格式不符，極易導致 YAML 結構被破壞或產生靜默錯誤。

### 核心重構決策：
1. **建立深防腐層模組 `BerkshireBridge` (`src/bridge/berkshire_bridge.py`)**：
   - 建立強型別傳輸契約 `BerkshireAssetContract`，在接縫處嚴格檢驗以下不變量：
     - `tier` 必須為 `TIER_1_CORE` 或 `TIER_2_MOMENTUM`。
     - 核心資產自動產生標準半凱利金字塔掛單階梯（-10%, -20%, -30%）。
     - 金字塔總加碼部位上限保護（不得超過 20%）。
     - 任何校驗失敗立即阻斷寫入，保證 `watchlist.yaml` 絕對完整性。
2. **單向戰略注入 (Unidirectional Ingestion)**：
   - 由 `BerkshireBridge` 唯讀掃描 `D:/AI Berkshire`（包括 `股票清單.xlsx` 與 `实盘记录`），格式化為合約後原子化（Atomic）注入 `config/watchlist.yaml`。
3. **提供極簡 CLI 槓桿**：
   - 整合至 `manage_watchlist.py --sync-berkshire` 與互動式選單選項 6，支援一鍵即時同步 37 檔波克夏核心資產。
4. **測試表面收斂**：
   - 新增端到端單元測試 `tests/test_berkshire_bridge.py`，全套 42 個單元測試通過。

## 後果與價值 (Consequences)
- **隔絕與安全 (Anticorruption & Safety)**：上游專案的資料異動在防腐層被嚴格過濾與轉換，絕不破壞下游設定檔。
- **維護性 (Maintainability)**：上游護城河評分若有更新，僅需執行一行指令即可自動對齊全市場清單。
- **一致性 (Consistency)**：確保波克夏長線戰略與儀表板戰術執行 100% 邏輯一致。
