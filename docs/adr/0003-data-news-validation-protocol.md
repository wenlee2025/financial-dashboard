# ADR 0003: 數據雙源交叉驗證與新聞時效防幻覺架構

## 狀態
Accepted (已採納)

## 上下文與決策 (Context & Decision)
在金融投研與每日推播系統中，AI 幻覺（捏造未發生的事件或數字）與陳舊資料（引用歷史舊財報/過期新聞）是致命問題。為確保所有呈現與推論 100% 真實可信，系統建立嚴格的**三重數據驗證公式與新聞溯源機制**：

1. **時效性時間戳校驗公式 (Freshness Gate)**：
   $$\text{Age}_{\text{Data}} = T_{\text{now}} - T_{\text{timestamp}} \le \text{Max\_Allowed\_Age}$$
   - 台股盤後：收盤資料時間戳必須為當日（交易日）。
   - 新聞與催化劑：發布時間戳 $\Delta t \le 24\text{h}$（盤前晨報/盤後快訊僅採用近 24 小時內發布之新聞）。

2. **雙源交叉驗證公式 (Dual-Source Cross-Validation)**：
   $$\text{Discrepancy Rate} = \frac{|\text{Source}_1 - \text{Source}_2|}{\text{Source}_1} \times 100\%$$
   - 誤差 $\le 1\%$：判定為可信一致（✅）。
   - $1\% < \text{誤差} \le 5\%$：標記差異預警（⚠️）。
   - 誤差 $> 5\%$：直接阻斷採信，強制回退至官方一手數據源（TWSE/MOPS/SEC EDGAR）。

3. **新聞一手信源溯源白名單 (News Provenance Grounding)**：
   - 每一則新聞與催化劑必須包含：`來源媒體名稱`、`精確發布時間 (YYYY-MM-DD HH:MM)`、`原文連結 URL`、`受影響標的代碼`。
   - 嚴格禁止 LLM 無信源憑空編造新聞。所有新聞必須直接由已驗證之新聞 Feed 管道注入。
