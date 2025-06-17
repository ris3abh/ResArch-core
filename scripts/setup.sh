#!/bin/bash
# SpinScribe Setup Script

echo "Setting up SpinScribe..."

# Install Python dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Create storage directories
mkdir -p storage/database storage/documents storage/chat_attachments storage/vector_db
touch storage/database/.keep storage/documents/.keep storage/chat_attachments/.keep storage/vector_db/.keep

# Run database migrations
alembic upgrade head

echo "Setup complete! Run 'python -m app.main' to start the server."

