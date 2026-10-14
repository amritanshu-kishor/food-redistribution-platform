@echo off
echo Starting Food Redistribution Platform Backend...
cd backend
python -m uvicorn app.main:app --reload --port 8000