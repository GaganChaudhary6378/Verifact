#!/bin/bash

echo "=================================="
echo "VeriFact Backend Setup"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version || { echo "Python 3 not found!"; exit 1; }

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv .venv

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -e ..

# Download NLP models
echo ""
echo "Downloading NLP models..."
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('averaged_perceptron_tagger')"
python -m spacy download en_core_web_sm

# Copy env file
echo ""
echo "Setting up environment file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✓ Created .env file (please edit with your API keys)"
else
    echo "✓ .env file already exists"
fi

# Start Redis Stack
echo ""
echo "Starting Redis Stack..."
cd ..
docker-compose up -d
cd backend

echo ""
echo "=================================="
echo "✓ Setup complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys"
echo "2. Index knowledge base: python -m src.scripts.index_knowledge_base"
echo "3. Start server: uvicorn src.api.main:app --reload"
echo ""
echo "Redis Insight GUI: http://localhost:8001"
echo "API Documentation: http://localhost:8000/docs"
echo ""
