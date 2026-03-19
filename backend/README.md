# VeriFact Backend - Real-Time News Claim Verification System

Agentic RAG system for real-time news claim verification with multi-source credibility scoring, RAGAS evaluation, and self-growing knowledge base.

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

The easiest way to run the entire backend with Redis Stack:

```bash
cd week-1/backend

# Copy environment template
cp .env.example .env
# Edit .env and add your API keys

# Start everything with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop everything
docker-compose down
```

This will start:
- **Redis Stack** on port `6379` (Redis) and `8001` (Redis Insight GUI)
- **Backend API** on port `8000`

Access:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Redis Insight: http://localhost:8001

## 🚀 Deployment to EC2

For production deployment to AWS EC2 using Terraform:

```bash
# See the infrastructure directory for automated deployment
cd ../infra
cat README.md
```

The Terraform setup will:
- Provision EC2 instance with proper sizing
- Configure security groups and networking
- Install Docker and Docker Compose automatically
- Deploy backend + Redis Stack containers
- Provide outputs for easy access

**See [`../infra/README.md`](../infra/README.md) for complete deployment guide.**

### Option 2: Local Development

### Prerequisites

- Python 3.10-3.12
- Docker (for Redis Stack)
- API Keys (see below)

### 1. Start Redis Stack

```bash
# Start Redis Stack using Docker
docker run -d \
  --name verifact-redis-stack \
  -p 6379:6379 \
  -p 8001:8001 \
  redis/redis-stack-server:latest
```

Verify Redis is running:
```bash
docker ps
# Should show verifact-redis-stack on ports 6379, 8001
```

Access Redis Insight GUI: http://localhost:8001

### 2. Setup Python Environment

```bash
cd week-1/backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Download NLP Models

```bash
# NLTK data
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('averaged_perceptron_tagger')"

# SpaCy model
python -m spacy download en_core_web_sm
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your API keys
```

Required API keys:
- **ANTHROPIC_API_KEY**: Claude 3.5 Sonnet (primary LLM)
- **OPENAI_API_KEY**: GPT-4o (fallback LLM)
- **EXA_API_KEY**: Web search (Exa API)
- **COHERE_API_KEY**: Reranking
- **NEWS_API_KEY**: News articles (optional)

Get keys:
- Anthropic: https://console.anthropic.com/
- OpenAI: https://platform.openai.com/
- Exa: https://exa.ai/ (free tier available, no credit card required)
- Cohere: https://dashboard.cohere.com/ (free tier available)
- NewsAPI: https://newsapi.org/ (free tier: 100/day)

### 4. Index Knowledge Base

```bash
python -m src.scripts.index_knowledge_base
```

This will index sample documents to Redis Stack.

### 5. Start API Server

```bash
# Development mode
uvicorn src.api.main:app --reload --port 8000

# Or using the installed command
cd ..
verifact
```

The API will be available at: http://localhost:8000

API Documentation: http://localhost:8000/docs

## 📡 WebSocket API

### Endpoint

```
ws://localhost:8000/api/v1/ws/verify/{user_id}
```

### Request Format

```json
{
  "action": "START_VERIFICATION",
  "payload": {
    "claim_text": "The Earth is flat",
    "source_context": {
      "url": "https://example.com/article",
      "page_title": "Example Article",
      "selected_at": "2026-02-10T12:00:00Z",
      "language": "en-US",
      "geo_data": {
        "country": "US",
        "city": "San Francisco",
        "timezone": "America/Los_Angeles",
        "timezone_offset": -480
      }
    }
  }
}
```

### Response Format

**Progress Updates:**
```json
{
  "type": "AGENT_STEP",
  "payload": {
    "step_id": 1,
    "label": "Claim Processing",
    "detail": "Normalizing and analyzing claim structure"
  }
}
```

**Final Verdict:**
```json
{
  "type": "FINAL_VERDICT",
  "payload": {
    "request_id": "uuid",
    "verdict": "TRUE | FALSE | MISLEADING | NOT ENOUGH EVIDENCE",
    "confidence_score": 0.98,
    "reasoning_summary": "Verification logic processed...",
    "citations": [
      {
        "source_name": "Reuters",
        "url": "https://reuters.com/...",
        "relevance_snippet": "Scientists confirm...",
        "trust_score": 0.95
      }
    ]
  }
}
```

## 🏗️ Architecture

### System Components

1. **Claim Processing Layer**
   - Text normalization
   - Entity extraction (LLM-based)
   - Claim classification (LLM)
   - Sub-claim decomposition

2. **Agentic Orchestrator (LangGraph)**
   - Query planning
   - Route selection (KB/Web/Both)
   - Parallel retrieval coordination

3. **Retrieval Layer**
   - **Knowledge Base**: Redis VSS (vector search)
   - **Web Search**: Exa API
   - **Fact Checkers**: Snopes, PolitiFact, etc.
   - **Reranking**: Cohere Rerank v3

4. **Scoring Engine** (Innovation 🌟)
   - **Credibility Scorer**: Domain-based trust scores
   - **Stance Detector**: LLM-based (GPT-4o-mini)
   - **Consensus Calculator**: Weighted voting
   - **Threshold Evaluator**: Verdict classification

5. **Quality Layer**
   - **RAGAS Evaluation**: Faithfulness, Context Precision, Answer Correctness
   - **Quality Gates**: Pass/fail logic
   - **Caching**: High-quality verdicts cached with TTL

6. **API Layer**
   - WebSocket for real-time updates
   - Progress streaming
   - Cache-first retrieval

### Tech Stack

| Component | Technology |
|-----------|------------|
| Orchestration | LangGraph |
| Vector DB + Cache | Redis Stack (RediSearch VSS) |
| Embeddings | OpenAI (`text-embedding-3-small`) |
| Primary LLM | Claude 3.5 Sonnet |
| Fallback LLM | GPT-4o |
| Stance Detection | GPT-4o-mini |
| Reranking | Cohere Rerank v3 |
| Evaluation | RAGAS |
| API Server | FastAPI + WebSocket |
| Web Search | Exa API |

## 📊 Project Structure

```
backend/
├── src/
│   ├── config/              # Settings and constants
│   ├── models/              # Pydantic models
│   ├── core/                # Core infrastructure
│   │   ├── embeddings.py    # OpenAI embedding manager
│   │   ├── llm.py           # LLM client with fallback
│   │   └── redis_client.py  # Redis Stack client
│   ├── retrieval/           # Retrieval layer
│   │   ├── knowledge_base.py
│   │   ├── web_search.py
│   │   ├── fact_checkers.py
│   │   └── reranker.py
│   ├── scoring/             # Scoring engine
│   │   ├── credibility.py
│   │   ├── stance_detector.py
│   │   ├── consensus.py
│   │   └── thresholds.py
│   ├── agents/              # LangGraph workflow
│   │   ├── graph.py
│   │   └── nodes/
│   ├── evaluation/          # Quality layer
│   │   ├── ragas_metrics.py
│   │   └── quality_gate.py
│   ├── cache/               # Caching layer
│   │   ├── claim_cache.py
│   │   └── deduplication.py
│   ├── api/                 # FastAPI app
│   │   ├── main.py
│   │   └── schemas/
│   ├── data/                # Data files
│   │   ├── source_credibility.json
│   │   ├── fact_check_sources.json
│   │   └── test_claims.json
│   └── scripts/             # Utility scripts
│       ├── index_knowledge_base.py
│       └── run_evaluation.py
├── .env.example
└── README.md
```

## 🧪 Testing

### Run Evaluation

```bash
python -m src.scripts.run_evaluation
```

This will:
1. Load test claims
2. Run verification for each
3. Evaluate with RAGAS
4. Output metrics and save results

### Manual Testing

Use a WebSocket client (e.g., Postman, wscat):

```bash
npm install -g wscat
wscat -c ws://localhost:8000/api/v1/ws/verify/test_user

# Send:
{"action":"START_VERIFICATION","payload":{"claim_text":"The Earth is flat","source_context":{"url":"https://example.com","page_title":"Test","selected_at":"2026-02-10T12:00:00Z","language":"en-US"}}}
```

## 🎯 Key Features

### 1. Multi-Source Credibility Scoring
- 35+ pre-scored domains
- Weighted consensus algorithm
- Bias-aware source selection

### 2. RAGAS Quality Gates
- Faithfulness ≥ 0.85
- Context Precision ≥ 0.75
- Answer Correctness ≥ 0.80
- Auto-override to "NOT ENOUGH EVIDENCE" if fail

### 3. Self-Growing Knowledge Base
- Verified claims cached with embeddings
- Vector similarity deduplication (threshold: 0.95)
- TTL-based expiry (default: 24 hours)

### 4. Geospatial Awareness
- Uses geo_data from frontend
- Localized web search results
- Timezone-aware source filtering

### 5. Transparent Reasoning
- Full citation trail
- Credibility scores displayed
- Stance detection confidence

## 🔧 Configuration

Key settings in `.env`:

```bash
# Thresholds
SUPPORTED_SCORE_THRESHOLD=75
REFUTED_SCORE_THRESHOLD=-50
MIN_CONSENSUS_PERCENTAGE=70
MIN_SOURCES_COUNT=3

# RAGAS Quality Gates
MIN_FAITHFULNESS=0.85
MIN_CONTEXT_PRECISION=0.75
MIN_ANSWER_CORRECTNESS=0.80

# Cache
CACHE_TTL_SECONDS=86400
CACHE_SIMILARITY_THRESHOLD=0.95
```

## 📝 API Endpoints

### HTTP Endpoints

- `GET /health` - Health check
- `GET /docs` - API documentation (Swagger UI)

### WebSocket Endpoint

- `WS /api/v1/ws/verify/{user_id}` - Claim verification

## 🐛 Troubleshooting

### Redis Connection Error

```bash
# Check Redis is running
docker ps

# Restart Redis
docker-compose restart redis-stack
```

### Embedding Model Download

No longer needed! The system now uses OpenAI's embedding API, which doesn't require downloading models.

### Named Entity Recognition

Ensure all required API keys are set in `.env`:
- ANTHROPIC_API_KEY (required)
- OPENAI_API_KEY (fallback, recommended)
- EXA_API_KEY (required for web search)

## 📄 License

MIT License

## 👥 Team

VeriFact Team - AI League #1 Hackathon 2026

---

**Built with ❤️ using LangGraph, Redis Stack, and Claude 3.5 Sonnet**

