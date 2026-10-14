@echo off
title ToothWise
cd /d "%~dp0"

start "ToothWise backend :8000" cmd /k "cd backend && .venv\Scripts\python.exe -m uvicorn app.main:app --reload"
start "ToothWise frontend :3000" cmd /k "cd frontend && npm start"

echo Backend  http://localhost:8000
echo Frontend http://localhost:3000
