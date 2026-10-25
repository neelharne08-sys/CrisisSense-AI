@echo off
setlocal
echo =====================================================================
echo  CrisisSense AI - Autonomous Decision Engine for Urban Cascades
echo  Starting FastAPI Streaming Server & Tactical Frontend UI...
echo =====================================================================
echo.
echo Launching Uvicorn on http://localhost:8000
echo Direct browser link: http://localhost:8000/
echo.

start "" "http://localhost:8000/"

python -m uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
