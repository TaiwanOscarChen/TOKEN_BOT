@echo off
title SinoPac API Verification Assistant
echo ===============================================================
echo            SinoPac API Verification Assistant
echo         永豐金證券 API 測試啟用助手 (Shioaji & T4)
echo ===============================================================
echo.
echo Starting FastAPI backend server using Uvicorn...
echo The helper application will run at http://127.0.0.1:8000/
echo.
echo Launching default web browser...
start http://127.0.0.1:8000/
echo.
uvicorn server:app --host 127.0.0.1 --port 8000
pause
