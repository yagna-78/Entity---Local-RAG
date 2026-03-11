@echo off
echo Starting Entity AI Backend...
echo Ensure Ollama is running in the background!
cd app
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
pause
