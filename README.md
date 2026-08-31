# 每日美股／台股財經分析推播系統與財經儀表板

> **完全免伺服器成本（Zero Server Cost）** 的跨市場量化投研暨 AI 深度分析推播系統。透過 **GitHub Actions** 於交易日自動定時排程，整合多源免費/公開數據與 Google Gemini 等 LLM 推論引擎，產出結構化現代深色「財經儀表板」，自動發布至 **GitHub Pages** 靜態站點，並透過 **Telegram / Discord / LINE / Slack / Email** 進行多通道即時推播。

---

## 🌟 核心特色

1. **零成本雲端全自動化**：
   - 採用 **GitHub Actions** 免費 CI/CD 算力定時排程（每個交易日自動觸發）。
   - 自動將分析日報與互動儀表板編譯為靜態 HTML 發布至 **GitHub Pages**。
2. **美股 + 台股雙市場深度整合**：
   - **台股**：整合 TWSE/TPEx 官方公開資料（三大法人外資/投信/自營商買賣超、融資融券、借券賣出）、FinMind 月營收 YoY、均線排列與技術動能。
   - **美股**：整合 yfinance 即時/歷史行情、52 週高低點、PE/PEG 估值、分析師共識、VIX 波動率。
   - **跨市場宏觀**：台美 ADR 折溢價率換算（如 TSM ADR vs 2330 台積電 1:5 換算比）、CNN 恐慌貪婪指數、FRED 10 年期美債殖利率、USD/TWD 匯率。
3. **多因子多空量化評分與關鍵點位**：
   - 0-100 分量化評分與 5 階評級（`強力做多` 🟢🟢、`偏多震盪` 🟢、`中立觀望` 🟡、`偏空防守` 🟠、`避險做空` 🔴）。
   - 動態計算第一支撐 S1、核心強支撐 S2、第一壓力 R1、突破目標 R2、分批進場區間、停損防守點 (SL)、停利目標 (TP) 與風險報酬比 (R:R Ratio)。
4. **AI 深度邏輯推理**：
   - 預設支援 **Google Gemini API**（提供免費額度且強大），亦支援 OpenAI / Claude 或系統內建之離線量化規則引擎。
   - 產出核心定調、多空主線論據、主力籌碼解讀、近期催化劑與交易執行前操作檢查清單。
5. **全市場動態焦點股掃描**：
   - 自動過濾排除現有自選股，動態掃描盤後外資與投信同步買超、量增突破之焦點個股。
6. **多通道即時廣播通知**：
   - 支援 Telegram Bot、Discord Webhook、LINE Messaging API、Slack Webhook。
   - 支援標準 SMTP (Gmail App Password / SendGrid 等) 自動發送 HTML 電子報。

---

## 🏛️ 系統架構

```
財經儀表板/
├── .github/
│   └── workflows/
│       ├── daily_report.yml          # GitHub Actions 雙排程與手動觸發日報生成
│       └── deploy_pages.yml          # GitHub Pages 自動發布靜態網站
├── config/
│   ├── watchlist.yaml                # 自選監控股票清單（美股、台股、大盤指數、ADR 對照）
│   └── settings.yaml                 # 系統參數（評分權重、風險閾值、AI 模型設定）
├── src/
│   ├── data_sources/                 # TWSE、yfinance、FinMind、FRED、CNN 數據獲取與掃描
│   ├── analytics/                    # 0-100 量化評分、S1/S2/R1/R2 點位計算、主力籌碼流向警報
│   ├── ai_engine/                    # Gemini / OpenAI 統一客戶端與 Prompt 模板
│   ├── generators/                   # HTML 儀表板、Markdown 摘要、Email 電子報產生器
│   ├── notifiers/                    # Telegram / Discord / LINE / Slack / SMTP 統一推播調度
│   └── pipeline.py                   # 主流程調度器
├── templates/
│   ├── dashboard_template.html       # 現代深色響應式儀表板前端模板 (Tailwind + ECharts)
│   └── email_template.html           # 響應式 HTML 郵件模板
├── docs/                             # GitHub Pages 發布目錄 (含 index.html 與 history/)
├── tests/                            # 單元與整合測試
├── main.py                           # 命令列進入點
├── requirements.txt                  # Python 依賴
└── .env.example                      # 環境變數與 GitHub Secrets 範本
```

---

## ⏰ 定時排程機制 (GitHub Actions)

系統在 `.github/workflows/daily_report.yml` 中配置了雙定時排程：

| 排程類型 | 觸發時間 (台灣時間 CST) | UTC 時間 | 核心任務 |
| :--- | :--- | :--- | :--- |
| **台股盤後專報** | 每週一至週五 **15:30** | `30 7 * * 1-5` | 抓取台股收盤行情、三大法人買賣超、融資券、月營收與技術點位，更新儀表板並推播 |
| **美股盤後晨報** | 每週一至週五 **06:30** | `30 22 * * 0-4` | 抓取美股收盤行情、ADR 折溢價率、美債殖利率、全球大盤走勢與今日開盤指引 |
| **手動一鍵觸發** | 隨時 (`workflow_dispatch`) | 手動 | 在 GitHub 網頁介面上隨時指定執行模式或自訂股票代碼分析 |

---

## 🚀 快速上手與部署教學

### 步驟 1：建立 GitHub 儲存庫並上傳代碼
1. 將本專案推送至您的 GitHub 儲存庫（公開 Public 或私有 Private 均可）。
2. 在 GitHub 儲存庫頁面點擊 **Settings** -> **Pages**：
   - **Source** 選擇 **GitHub Actions**。

### 步驟 2：配置 GitHub Secrets
進入儲存庫的 **Settings** -> **Secrets and variables** -> **Actions**，點擊 **New repository secret**，依需求填入以下變數（至少填入 `GEMINI_API_KEY`，推播通道依您使用的軟體選填）：

| Secret 名稱 | 說明 | 必填/選填 |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Google AI Studio 獲取之免費 Gemini API Key | 建議填寫 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token (向 @BotFather 申請) | 選填 (啟用 Telegram) |
| `TELEGRAM_CHAT_ID` | 接收訊息之 Telegram Chat ID 或頻道 ID | 選填 |
| `DISCORD_WEBHOOK_URL`| Discord 頻道的 Webhook URL | 選填 (啟用 Discord) |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging API Channel Access Token | 選填 (啟用 LINE) |
| `LINE_USER_ID` | LINE 接收者的 User ID 或 Group ID | 選填 |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL | 選填 (啟用 Slack) |
| `SMTP_SERVER` | SMTP 伺服器 (如 `smtp.gmail.com`) | 選填 (啟用 Email) |
| `SMTP_PORT` | SMTP 埠號 (如 `587`) | 選填 |
| `SMTP_USER` | SMTP 帳號 (如 `your_email@gmail.com`) | 選填 |
| `SMTP_PASSWORD` | Gmail 應用程式專用密碼 (App Password) | 選填 |
| `EMAIL_TO` | 接收日報之 Email (多個請用逗號分隔) | 選填 |
| `DASHBOARD_URL` | 您的 GitHub Pages 網址 (如 `https://user.github.io/repo/`) | 選填 |

### 步驟 3：測試排程與手動執行
進入 GitHub 儲存庫的 **Actions** 分頁：
1. 點擊 **每日財經分析推播與儀表板更新** 工作流。
2. 點擊 **Run workflow**，選擇模式（如 `full` 或 `tw_post`），點擊確認執行。
3. 執行完成後，靜態網頁將自動部署至您的 GitHub Pages，並推播摘要至您的通訊軟體與信箱！

---

## 💻 本地端開發與執行

### 1. 安裝環境與套件
```bash
# 建議使用 Python 3.10+
pip install -r requirements.txt
```

### 2. 設定環境變數
複製 `.env.example` 為 `.env` 並填入您的金鑰：
```bash
cp .env.example .env
```

### 3. 本地執行指令

```bash
# 執行台股盤後模式 (不推播訊息)
python main.py --mode tw_post --no-push

# 執行美股晨報模式
python main.py --mode us_morning --no-push

# 執行全量分析模式
python main.py --mode full --no-push

# 指定單獨分析特定自選標的
python main.py --symbols "NVDA,2330,TSLA" --no-push
```

### 4. 預覽生成的儀表板
```bash
# 啟動本地伺服器
python -m http.server 8000 --directory docs

# 開啟瀏覽器造訪 http://localhost:8000 查看深色現代儀表板
```

### 5. 執行自動化測試
```bash
pytest tests/ -v
```

---

## ⚙️ 自訂設定與擴充

- **修改自選股**：編輯 `config/watchlist.yaml`，自由新增或刪除關注的美股與台股代碼、產業標籤與關注理由。
- **調整評分權重與閾值**：編輯 `config/settings.yaml`，可自訂技術面、籌碼面、基本面的加權比例與評級分數級距。

---

## 📄 免責聲明
本專案所提供之數據分析、量化評分與 AI 推論結果僅供技術研究與量化投研參考，不代表任何形式的投資建議、買賣要約或獲利保證。市場有風險，投資需謹慎，使用者應審慎評估並自負投資風險與盈虧。
