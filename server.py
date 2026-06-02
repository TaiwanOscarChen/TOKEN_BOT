# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import ctypes
import os
import time
import traceback

app = FastAPI(title="SinoPac API Verification Assistant")

class ShioajiTestRequest(BaseModel):
    api_key: str
    secret_key: str
    ca_path: str = None
    ca_passwd: str = None
    stock_code: str = "2890"
    futures_code: str = "TXFR1"

class T4TestRequest(BaseModel):
    login_id: str
    login_pass: str
    user_id: str
    stock_branch: str
    stock_account: str
    futures_branch: str
    futures_account: str
    stock_code: str = "2890"
    stock_price: str = "15.0"
    futures_code: str = "TXFD3"
    futures_price: str = "16000.0"

@app.get("/", response_class=HTMLResponse)
def read_index():
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/test-shioaji")
def test_shioaji(req: ShioajiTestRequest):
    import shioaji as sj
    from shioaji.constant import Action, StockPriceType, OrderType, FuturesPriceType, FuturesOCType
    
    logs = []
    try:
        logs.append("Initializing Shioaji API in simulation mode...")
        api = sj.Shioaji(simulation=True)
        
        logs.append("Attempting login...")
        accounts = api.login(api_key=req.api_key, secret_key=req.secret_key)
        logs.append(f"Login successful. Accounts retrieved: {[acc.account_id for acc in accounts]}")
        
        if req.ca_path and req.ca_passwd:
            logs.append(f"Activating CA certificate from: {req.ca_path}...")
            api.activate_ca(ca_path=req.ca_path, ca_passwd=req.ca_passwd)
            logs.append("CA certificate activated successfully.")
        else:
            logs.append("Note: CA certificate not provided, proceeding with simulation order...")
            
        # 1. Stock Order Test
        logs.append(f"Fetching stock contract for symbol '{req.stock_code}'...")
        stock_contract = api.Contracts.Stocks[req.stock_code]
        ref_price = stock_contract.reference
        logs.append(f"Found stock contract: {stock_contract.code} ({stock_contract.name}), Reference price: {ref_price}")
        
        stock_order = sj.order.StockOrder(
            action=Action.Buy,
            price=ref_price,
            quantity=1,
            price_type=StockPriceType.LMT,
            order_type=OrderType.ROD,
            account=api.stock_account
        )
        logs.append("Placing simulation stock order...")
        stock_trade = api.place_order(contract=stock_contract, order=stock_order)
        logs.append(f"Stock order placed. Trade object: {stock_trade}")
        
        # Update status
        api.update_status()
        logs.append(f"Current Stock Order Status: {stock_trade.status.status}")
        
        # Wait 1.5 seconds to separate stock and futures tests to follow SinoPac rules
        logs.append("Waiting 1.5 seconds before starting futures test...")
        time.sleep(1.5)
        
        # 2. Futures Order Test
        logs.append(f"Fetching futures contract for symbol '{req.futures_code}'...")
        futures_contract = api.Contracts.Futures[req.futures_code]
        fut_ref_price = futures_contract.reference
        logs.append(f"Found futures contract: {futures_contract.code} ({futures_contract.name}), Reference price: {fut_ref_price}")
        
        futures_order = sj.order.FuturesOrder(
            action=Action.Buy,
            price=fut_ref_price,
            quantity=1,
            price_type=FuturesPriceType.LMT,
            order_type=OrderType.ROD,
            octype=FuturesOCType.Auto,
            account=api.futopt_account
        )
        logs.append("Placing simulation futures order...")
        futures_trade = api.place_order(contract=futures_contract, order=futures_order)
        logs.append(f"Futures order placed. Trade object: {futures_trade}")
        
        # Update status
        api.update_status()
        logs.append(f"Current Futures Order Status: {futures_trade.status.status}")
        
        logs.append("Logging out...")
        api.logout()
        logs.append("Logout complete.")
        
        return {
            "status": "success",
            "logs": logs,
            "stock_status": str(stock_trade.status.status),
            "futures_status": str(futures_trade.status.status)
        }
        
    except Exception as e:
        err_msg = str(e)
        tb = traceback.format_exc()
        logs.append(f"Error occurred: {err_msg}")
        logs.append(f"Details:\n{tb}")
        try:
            api.logout()
        except:
            pass
        return {
            "status": "failed",
            "logs": logs,
            "error": err_msg
        }

@app.post("/api/test-t4")
def test_t4(req: T4TestRequest):
    # Locate the T4 64-bit DLL and its directory
    dll_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "T4_SDK", "T4_10142", "VBA"))
    dll_path = os.path.join(dll_dir, "t4x64.dll")
    
    if not os.path.exists(dll_path):
        raise HTTPException(status_code=500, detail=f"T4 DLL not found at: {dll_path}")
        
    try:
        # Load T4 library (WinDLL for StdCall)
        t4 = ctypes.WinDLL(dll_path)
        
        t4.init_t4.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        t4.init_t4.restype = ctypes.c_char_p
        
        t4.exam1st.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        t4.exam1st.restype = ctypes.c_char_p
        
        t4.log_out.argtypes = []
        t4.log_out.restype = ctypes.c_int
        
        # 1. Initialize
        # The execution path must end with a backslash
        exec_path = (dll_dir + "\\").encode('cp950')
        init_res_bytes = t4.init_t4(
            req.login_id.encode('cp950'),
            req.login_pass.encode('cp950'),
            exec_path
        )
        init_res = init_res_bytes.decode('cp950', errors='ignore')
        
        # Check if initialization was successful.
        # "下單帳號取得失敗" is expected if accounts are not verified yet.
        is_ready = "初始化成功" in init_res or "下單帳號取得失敗" in init_res
        
        if not is_ready:
            t4.log_out()
            return {
                "status": "failed",
                "message": f"Initialization failed: {init_res}",
                "init_message": init_res
            }
            
        # 2. Formulate 12-item content string:
        # 1. Stock BS (B/S)
        # 2. Stock Code (e.g. 2890)
        # 3. Stock Price (e.g. 15.0)
        # 4. Stock Qty (1)
        # 5. Stock PriceType (LMT)
        # 6. Stock OrderType (ROD)
        # 7. Futures BS (S/B)
        # 8. Futures Code (e.g. TXFD3)
        # 9. Futures Price (e.g. 16000.0)
        # 10. Futures Qty (1)
        # 11. Futures PriceType (MKT)
        # 12. Futures OrderType (IOC)
        content_str = f"B,{req.stock_code},{req.stock_price},1,LMT,ROD,S,{req.futures_code},{req.futures_price},1,MKT,IOC"
        
        # 3. Run Stock Test
        stock_res_bytes = t4.exam1st(
            req.user_id.encode('cp950'),
            req.stock_branch.encode('cp950'),
            req.stock_account.encode('cp950'),
            content_str.encode('cp950')
        )
        stock_res = stock_res_bytes.decode('cp950', errors='ignore')
        
        # Wait 1.5 seconds to separate stock and futures tests
        time.sleep(1.5)
        
        # 4. Run Futures Test
        fut_res_bytes = t4.exam1st(
            req.user_id.encode('cp950'),
            req.futures_branch.encode('cp950'),
            req.futures_account.encode('cp950'),
            content_str.encode('cp950')
        )
        fut_res = fut_res_bytes.decode('cp950', errors='ignore')
        
        # 5. Logout and cleanup
        t4.log_out()
        
        # Combine messages
        combined_res = f"證券測試回應: {stock_res}\n期貨測試回應: {fut_res}"
        
        # Check if both succeeded (message typically contains "已交付測試" or "交付成功")
        success = "已交付測試" in stock_res and "已交付測試" in fut_res
        
        return {
            "status": "success" if success else "failed",
            "message": combined_res,
            "init_message": init_res
        }
        
    except Exception as e:
        try:
            t4.log_out()
        except:
            pass
        return {
            "status": "failed",
            "message": f"Exception occurred: {str(e)}\n{traceback.format_exc()}",
            "init_message": "Error loading/executing T4 DLL"
        }
