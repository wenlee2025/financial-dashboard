# 市場知識庫索引 (Market Wiki Index)

本知識庫遵循 **WikiSkill (arXiv:2608.27454)** 規範，編譯日常交易與量化分析中反覆出現的市場型態、失敗教訓與成功範式。
本知識庫具備「**永久累積、永不回滾 (Persistent Compounding)**」特性，即便量化規則回滾，此處記錄之教訓亦永久保存。

---

## 🚨 失敗模式庫 (Failure Modes Catalog)

收錄歷史上導致「停損觸發 (Hit SL)」或「量價嚴重背離」的經典陷阱，供推論引擎與投資人防禦避坑：

* [FM-001: 高檔爆量假突破出貨 (False Breakout on Heavy Volume)](patterns/failure_modes/false_breakout_heavy_volume.md) - 量比 > 2.2x 卻開高走低長黑 K，主力藉利多出貨。
* [FM-002: 動能衰竭急追被套 (Chasing into Momentum Decay)](patterns/failure_modes/momentum_decay_chasing.md) - 股價創新高但成交總值量比 < 0.8x 萎縮，未等回踩 S1 即追高。
* [FM-003: 外資期貨巨額空單壓盤 (TX Futures Heavy Short Pressure)](patterns/failure_modes/tx_futures_short_pressure.md) - 外資淨空單超過 35,000 口時，現貨突破大多為假突破。

---

## 🚀 成功範式庫 (Success Archetypes)

收錄高勝率、順利觸及停利目標價（Hit TP）的共振主升型態：

* [SA-001: 法人籌碼鎖碼共振突破 (Institutional Resonance Surge)](patterns/success_archetypes/institutional_resonance_surge.md) - 外資與投信連續 3 日同步買超，成交總值溫和放大突破 5MA。
* [SA-002: 浮額沉澱量縮築底起漲 (Consolidation Bottom Accumulation)](patterns/success_archetypes/consolidation_bottom_accumulation.md) - 連續 5 日量縮守穩季線與 S1，首根紅 K 帶量突破 5MA。

---

## 📊 策略演化與衝擊審計

* [演化日誌 (Evolution Logs)](logs.md) - 歷次復盤提煉與規則修訂摘要。
* [策略衝擊追蹤表 (Skill Impact Tracker)](skill_impact.md) - 歷史提案 Diff、驗證集得分與採納狀態。
