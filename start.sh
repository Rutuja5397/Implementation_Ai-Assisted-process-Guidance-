#!/bin/bash

# Crane AI - Process Guidance Tool Startup Script

echo "========================================"
echo "  Crane AI - Process Guidance Tool"
echo "========================================"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "[WARNING] .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "[ACTION REQUIRED] Please edit .env and add your ANTHROPIC_API_KEY"
    echo "  Then re-run this script."
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is required but not found."
    exit 1
fi

# Install dependencies
echo ""
echo "[1/3] Installing dependencies..."
pip install -r requirements.txt -q

# Create data directories
mkdir -p data/knowledge_base
mkdir -p chroma_db

# Seed knowledge base if needed
echo ""
echo "[2/3] Initializing knowledge base..."
python3 -c "
import sys, os
sys.path.insert(0, '.')
os.environ.setdefault('ANTHROPIC_API_KEY', 'placeholder')
from backend.rag_system import RAGSystem
rag = RAGSystem()
rag.initialize()
print('  Knowledge base ready.')
"

# Start backend
echo ""
echo "[3/3] Starting services..."
echo ""
echo "  Backend  → http://localhost:8000"
echo "  Frontend → http://localhost:8501"
echo ""

# Start FastAPI backend in background
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"

# Wait for backend to be ready
sleep 3

# Start Streamlit frontend
streamlit run frontend/app.py --server.port 8501 --server.headless true &
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID"

echo ""
echo "  Both services running. Press Ctrl+C to stop."
echo ""

# Wait for both
wait $BACKEND_PID $FRONTEND_PID
