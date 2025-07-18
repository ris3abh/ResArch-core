#!/bin/bash

echo "🚀 Starting Spinscribe Backend Services"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r backend/requirements.txt

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd):$(pwd)/backend"
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/spinscribe"
export REDIS_URL="redis://localhost:6379"
export QDRANT_URL="http://localhost:6333"

# Create database tables
echo "🗄️ Setting up database..."
cd backend
python -c "
import asyncio
from database.database import create_tables
asyncio.run(create_tables())
"

# Run database migrations
echo "�� Running migrations..."
alembic upgrade head

# Start the server
echo "🌐 Starting FastAPI server..."
cd ..
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
