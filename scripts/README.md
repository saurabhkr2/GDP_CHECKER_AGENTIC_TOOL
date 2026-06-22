# Scripts Documentation

This folder contains the startup scripts for the agentic (LangGraph + Human-in-the-Loop)
Document Quality Checker.

## Overview

The application runs two processes:
- **Agentic Backend** (Port 5003): LangGraph pipeline with human-in-the-loop comment approval
- **Frontend** (Port 5000): Serves the review web interface

## Scripts

### `start-agentic.bat` / `start-agentic.sh`
- Starts the agentic backend (port 5003) and the frontend (port 5000)
- Opens separate terminal windows (Windows) or runs in the background (Linux/macOS)
- Requires a `.env` file in the project root with Azure OpenAI credentials
- **Usage**:
  - Windows: `scripts\start-agentic.bat`
  - Linux/macOS: `chmod +x scripts/start-agentic.sh && ./scripts/start-agentic.sh`
- **Access**:
  - Backend health: http://localhost:5003/api/health
  - Review UI: http://localhost:5000/

## Quick Start

```bash
# 1. Configure credentials
copy .env.example .env       # Windows
cp .env.example .env         # macOS/Linux
# fill in your Azure OpenAI keys

# 2. Install backend dependencies
pip install -r backend/requirements.txt

# 3. Start everything
scripts\start-agentic.bat    # Windows
./scripts/start-agentic.sh   # macOS/Linux
```

## Stopping Servers

### Windows
- Close the terminal windows that were opened by the script, or press Ctrl+C in each.

### Linux/macOS
- Press Ctrl+C in the terminal running `start-agentic.sh` (it stops both processes).
- Or manually kill processes:
  ```bash
  pkill -f 'python agentic_api.py'
  pkill -f 'python app.py'
  ```

## Troubleshooting

### "Python is not installed"
- Install Python 3.8 or higher from https://www.python.org/ and ensure it is in your PATH.

### Port already in use
- Windows: `netstat -ano | findstr :5000` and `netstat -ano | findstr :5003`
- Linux/macOS: `lsof -i :5000` and `lsof -i :5003`
- Kill the conflicting process or change the ports via `AGENTIC_API_PORT` / `FRONTEND_PORT`.

### Backend not responding
- Check the agentic backend terminal for error messages.
- Verify that `.env` contains valid Azure OpenAI credentials.

### Frontend cannot connect to backend
- Ensure the agentic backend is running on port 5003.
- Check the browser console for API connection errors.

## Dependencies

- Backend: `backend/requirements.txt` - Flask, LangGraph, Azure OpenAI, python-docx, etc.
- Frontend: `frontend/requirements.txt` - Flask (for serving the UI)

See `backend/AGENTIC_ARCHITECTURE.md` for detailed technical documentation.
