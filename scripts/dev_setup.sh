#!/bin/bash

echo "🔧 Setting up Spinscribe Development Environment"

# Check dependencies
echo "Checking dependencies..."

# Docker & Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose."
    exit 1
fi

# Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+."
    exit 1
fi

# Node.js (for frontend)
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 16+."
    exit 1
fi

echo "✅ All dependencies found!"

# Start infrastructure services
echo "🐳 Starting infrastructure services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
if ! docker-compose ps | grep -q "Up"; then
    echo "❌ Some services failed to start. Check docker-compose logs."
    exit 1
fi

echo "✅ Infrastructure services are running!"

# Create backend virtual environment
echo "🐍 Setting up Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

# Setup database
echo "🗄️ Setting up database..."
cd backend
python -c "
import asyncio
from database.database import create_tables
asyncio.run(create_tables())
"

# Create initial migration
if [ ! "$(ls -A alembic/versions)" ]; then
    echo "📋 Creating initial migration..."
    alembic revision --autogenerate -m "Initial migration"
fi

alembic upgrade head
cd ..

# Setup frontend (if needed)
echo "⚛️ Setting up frontend..."
if [ -f "frontend/package.json" ]; then
    cd frontend
    npm install
    cd ..
fi

echo "🎉 Development environment setup complete!"
echo ""
echo "🚀 To start the backend:"
echo "   ./scripts/start_backend.sh"
echo ""
echo "🌐 To start the frontend:"
echo "   cd frontend && npm run dev"
echo ""
echo "📊 Services running:"
echo "   PostgreSQL: localhost:5432"
echo "   Redis: localhost:6379"
echo "   Qdrant: localhost:6333"
