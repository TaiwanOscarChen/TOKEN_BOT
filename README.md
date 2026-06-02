# 量化交易均線策略與 Telegram 訊號提醒系統 (Quant Trading Alert System)

本專案是一個基於 **FastAPI** 與 **20MA 均線策略** 的量化交易回測與個股追蹤後端系統，並整合了 **Telegram Bot** 即時交易訊號推播功能。當有最新的買入（BUY）、賣出（SELL）或減碼（REDUCE）訊號觸發時，系統會自動估算建議股數並傳送至您的 Telegram。

---

## 📁 專案目錄結構

```text
├── app/
│   ├── api/
│   │   └── endpoints.py      # API 端點路由 (回測、價格上傳、訊號查詢)
│   ├── models/
│   │   └── stock.py          # SQLAlchemy 資料庫模型 (價格、訊號)
│   ├── schemas/
│   │   └── stock.py          # Pydantic 資料驗證結構
│   ├── strategies/
│   │   └── moving_average.py # 20MA 交易策略核心演算法
│   ├── utils/
│   │   └── notifier.py       # Telegram 訊息推播與股數精算模組
│   ├── config.py             # 設定管理器 (讀取環境變數)
│   ├── database.py           # SQLite 連線與 Session 管理
│   └── main.py               # FastAPI 啟動入口
├── .env                      # 本地環境變數設定檔 (已列入 .gitignore，防止外洩)
├── .gitignore                # 排除敏感檔案與快取
├── requirements.txt          # Python 依賴套件清單
└── Dockerfile                # 用於雲端部署 (如 Google Cloud Run) 的容器設定
```

---

## ⚙️ 本地環境設定

### 1. 建立環境變數檔案
請在專案根目錄下建立一個 `.env` 檔案（此檔案已被 `.gitignore` 排除，不會上傳到 GitHub）：
```env
TELEGRAM_TOKEN=您的_TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID=您的_TELEGRAM_CHAT_ID
DEFAULT_TRADE_BUDGET=100000  # 每次進場交易預算金額 (台幣/美金)
```

### 2. 安裝與執行 (本地)
1. **建立並啟用虛擬環境**：
   ```bash
   python -m venv .venv
   # Windows 啟用：
   .venv\Scripts\activate
   # Mac/Linux 啟用：
   source .venv/bin/activate
   ```
2. **安裝套件**：
   ```bash
   pip install -r requirements.txt
   ```
3. **啟動 FastAPI 服務**：
   ```bash
   uvicorn app.main:app --reload
   ```
   啟動後可開啟 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) 查看 Swagger API 互動式文件。

---

## 🚀 部署至 Google Cloud Run (適用您的系統環境)

由於本專案已附帶 [`Dockerfile`](./Dockerfile)，您可以非常輕鬆地將其部署至 **Google Cloud Run**。

### 1. 本地使用 gcloud 部署
如果您已安裝 Google Cloud SDK，可直接在根目錄執行：
```bash
gcloud run deploy token-bot-service \
  --source . \
  --region asia-east1 \
  --allow-unauthenticated
```

### 2. 設定環境變數 (Cloud Run)
部署完畢後，請務必在 Google Cloud Console 中的 **Cloud Run 變數設定** 頁面，新增以下環境變數，以確保 Telegram 通知能正常運作：
*   `TELEGRAM_TOKEN` = `您的_TELEGRAM_BOT_TOKEN`
*   `TELEGRAM_CHAT_ID` = `您的_TELEGRAM_CHAT_ID`
*   `DEFAULT_TRADE_BUDGET` = `100000`

---

## 📡 API 介面說明

### 1. 上傳歷史股價
*   **方法/路徑**：`POST /api/prices`
*   **用途**：批次上傳某檔股票的歷史日 K 線資料。

### 2. 執行策略回測並觸發通知
*   **方法/路徑**：`POST /api/backtest/{symbol}`
*   **用途**：執行該股的 20MA 策略回測，並自動將計算出的交易訊號寫入資料庫。
*   **通知機制**：若**最後一天（最新一日）**產生了 `BUY` / `SELL` / `REDUCE` 訊號，系統會即時發送通知至您的 Telegram。

### 3. 查詢歷史訊號
*   **方法/路徑**：`GET /api/signals/{symbol}`
*   **用途**：查詢該股在資料庫中已記錄的所有歷史交易訊號。
