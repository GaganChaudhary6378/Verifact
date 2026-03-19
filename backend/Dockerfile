# Use Python 3.11 slim image
FROM python:3.11-slim

# Build arguments
ARG VERSION=latest

# Metadata labels
LABEL maintainer="VeriFact Team"
LABEL description="VeriFact Backend - Real-Time News Claim Verification System"
LABEL version="${VERSION}"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl --version

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Download NLTK data (required by ragas)
RUN python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('wordnet', quiet=True); nltk.download('omw-1.4', quiet=True)"

# Copy the entire backend source code and test script
COPY src/ ./src/
COPY test_structure.py .

# Create data directory and copy data files from src/data/ to data/
# This allows the data to be available both at src/data/ (for code) and data/ (for volume mounting)
RUN mkdir -p ./data && \
    if [ -d "./src/data" ] && [ "$(ls -A ./src/data 2>/dev/null)" ]; then \
        cp -r ./src/data/* ./data/; \
        echo "Data files copied from src/data/ to data/"; \
    else \
        echo "Warning: src/data directory not found or empty, creating empty data directory"; \
        touch ./data/.gitkeep; \
    fi

# Create a non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose the API port
EXPOSE 8000

# Health check (using Python since curl may not be available)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

