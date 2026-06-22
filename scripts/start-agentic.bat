@echo off
REM Start the agentic LangGraph backend (port 5003) and frontend (port 5000).
REM Requires .env in the project root with Azure OpenAI credentials.

setlocal
cd /d %~dp0\..

if not exist .env (
    echo [WARN] No .env found. Copy .env.example to .env and fill in your keys.
)

start "agentic-backend" cmd /k "cd backend && python agentic_api.py"
start "frontend"        cmd /k "cd frontend && python app.py"

echo.
echo Backend (agentic):   http://localhost:5003/api/health
echo Frontend (review):   http://localhost:5000/
