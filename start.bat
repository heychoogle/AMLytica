@echo off

REM Activating virtual environment
call .\venv\Scripts\activate

REM Running ingest service
uvicorn services.ingest.main:app --reload