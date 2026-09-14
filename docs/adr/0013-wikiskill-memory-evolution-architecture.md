# ADR 0013: WikiSkill 記憶復盤與策略演化架構 (WikiSkill Co-Evolution Architecture)

## 狀態
Accepted (已採納，基於 arXiv:2608.27454 論文架構)

## 上下文與決策 (Context & Decision)

目前的財經儀表板每天進行全市場 50 檔標的的量化評分與點位預算，並將快照存檔於 `docs/data/YYYY-MM-DD_full.json`。然而，系統過去缺乏「事後驗證與持續自我迭代機制」：
1. 每天分析完即歸檔，未曾自動回溯 $T$ 日之推薦在 $T+5 \sim T+20$ 日後的真實走勢。
2. 缺乏對「失敗案例（如主力假突破出貨、財報前融資誘多）」的系統性記憶，導致相同盲點在未來週期可能重複出現。
3. 策略規則（均線權重、量能閾值、AI Prompt）若要調優，缺乏客觀量化的防過度擬合驗證機制。

為此，本專案引進 **WikiSkill (Compiling Agent Experience into Persistent Knowledge for Skill Evolution, arXiv:2608.27454)** 框架，建立專屬的金融記憶復盤與技能共演化閉環。

### 核心架構決策：

1. **三層知識架構 (Three-Layer Knowledge Architecture)**：
   - **原始軌跡層 (`raw_traces/`)**：不可變歷史快照，保存當時完整的市場行情、三大法人籌碼、技術指標、AI 推理鏈與點位預測，作為復盤評判的 Ground Truth 原始證據鏈。
   - **持久知識庫層 (`market_wiki/`)**：永久累積、**永不回滾**的結構化知識庫：
     - `patterns/failure_modes/`：失敗模式庫（如假突破倒貨、法說會誘多、融資斷頭破線）。
     - `patterns/success_archetypes/`：成功範式庫（如法人波段鎖碼連買、量縮築底突破）。
     - `logs.md`：歷次復盤演化日誌。
     - `skill_impact.md`：策略與參數修改歷史及其對應勝率/夏普值的審計表。
   - **可執行規則層 (`skills/` 與 `config/rules.json`)**：可執行的參數配置與 AI 分析 Prompt。所有技能皆附帶 `PURPOSE.md` 嚴格溯源對應的 Wiki 模式。

2. **客觀點位觸及評判機制 (TP vs SL First-Hit Metric)**：
   - 以交易日 $T+5 \sim T+20$ 內真實價格「先觸及 TP 目標價」或「先觸及 SL 停損價」作為客觀 Pass / Fail 判定基準。
   - 精確產出勝率（Win Rate）、盈虧比（Payoff Ratio）與未觸及處理，杜絕主觀事後諸葛。

3. **雙軌演化體系 (Dual-Track Evolution)**：
   - **軌道一（量化參數演化）**：微調 `config/rules.json` 中的因子權重、ATR 倍數與 5MA 量比閾值。
   - **軌道二（AI 推理手冊演化）**：演化 `src/ai_engine/` 之市場情報 Prompt Chain，在推論時強制注入歷史「地雷清單與必查要項」。

4. **綜合評分卡驗證閘門與安全回退 (Scorecard Walk-Forward Gating & Rollback)**：
   - 候選策略必須在多體制（牛市、熊市、盤整震盪）歷史切片中同時通過綜合評分卡驗證（MDD 不擴大、勝率與 Sharpe 提升、指定錯誤模式修復率達標）。
   - 一旦指標退化，系統強制執行代碼回滾（Rollback），但 **Wiki 記憶永不刪除**，確保長期避免重蹈覆轍。

5. **執行排程與工作流分流 (Execution Cadence & Workflow Decoupling)**：
   - **週間每日 15:30**：執行輕量滾動驗證，僅比對 $T-5 \sim T-20$ 標的是否達標，保持發布秒級響應。
   - **週末批次演化**：週六/日啟動 Wiki Maintainer 模式提煉與 Skill Proposer 策略演化，並跑完整回測閘門。

6. **歷史數據冷啟動回補 (Historical Backfill Bootstrapping)**：
   - 建立回放回補腳本，以過去 1 年日 K 線資料庫模擬運算，快速生成約 200 個交易日、數千筆點位推薦與觸及結果，作為初始驗證集與 Wiki 種子模式。

7. **前端雙視圖儀表板增強 (Frontend Transparency & Dual-View)**：
   - 於 GitHub Pages 頂部新增「🎯 實戰勝率榜」與「📚 避坑知識庫」頁籤，以視覺化圖表公開各決策原型的真實勝率曲線與歷次 Wiki 失敗避坑模式。

## 後果與價值 (Consequences)
- **告別策略死板與盲目迭代**：量化模型具備自我查錯、總結模式並提出修復提案的自主演化能力。
- **防止金融過度擬合**：嚴格的驗證閘門與回滾機制確保只有真正具備跨週期穩健性的策略才能上線。
- **決策完全可審計**：每一項參數或 Prompt 的更動，均能在 `market_wiki/skill_impact.md` 與 `PURPOSE.md` 找到原始失敗案例與回測收益驗證。
- **透明度與公信力大增**：透過實戰勝率榜與避坑 Wiki 頁籤，讓使用者與朋友清晰理解策略的歷史戰績與風控防線。

