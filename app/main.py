from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.api import api_router

# Initialize all database tables (creates SQLite db and tables if they don't exist)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="量化交易策略反測與個股追蹤系統 (Quant Trading & Backtesting System)",
    description="基於 FastAPI 與 20MA 均線策略的量化交易回測與追蹤系統後端 API",
    version="1.0.0"
)

# Configure CORS (Cross-Origin Resource Sharing)
origins = [
    "https://service-688770512380.asia-east1.run.app", # 您的前端雲端網址
    "http://localhost:5173",                           # Vite 本地開發預設埠
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API endpoints with /api prefix
app.include_router(api_router, prefix="/api", tags=["trading"])

@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "Quant Trading Backend",
        "message": "Welcome! Please use /api/backtest/{symbol} to run backtests, or /api/signals/{symbol} to query signals."
    }
