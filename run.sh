#!/usr/bin/env bash
set -e

echo "====================================================================="
echo " CrisisSense AI - Autonomous Decision Engine for Urban Cascades"
echo " Starting FastAPI Streaming Server & Tactical Frontend UI..."
echo "====================================================================="
echo ""
echo "Launching Uvicorn on http://localhost:8000"
echo "Direct browser link: http://localhost:8000/"
echo ""

# Attempt to open browser in background if supported
if command -v xdg-open > /dev/null; then
    (sleep 1 && xdg-open "http://localhost:8000/") &
elif command -v open > /dev/null; then
    (sleep 1 && open "http://localhost:8000/") &
fi

python3 -m uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
