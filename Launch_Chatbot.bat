@echo off
title Entity AI Launcher
echo ==================================================
echo      Starting Entity AI Context-Aware Chatbot
echo ==================================================
echo.

REM Check if Ollama is running
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [Check] Ollama is already running.
) else (
    echo [Check] Starting Ollama...
    start "Ollama" /min ollama serve
    timeout /t 5 >nul
)

REM 1. Start the Backend Server
echo [1/3] Launching Backend Server (minimized)...
cd app
start "Entity_Backend" /min python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
cd ..

REM 2. Start the Frontend Development Server
echo [2/3] Launching Frontend Server (minimized)...
cd frontend
start "Entity_Frontend" /min npm run dev
cd ..

REM 3. Wait for services to initialize
echo [3/3] Waiting for services to initialize...
timeout /t 8 /nobreak >nul

REM 4. Open the Interface
echo Opening Entity AI in your browser!
start http://localhost:5173

echo.
echo ==================================================
echo                 Done! 
echo    (Close the minimized windows to stop services)
echo ==================================================
timeout /t 5 >nul
exit
