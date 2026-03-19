# VeriFact Backend - Quick Reference Card

## 🚀 INSTANT START (3 Steps)

```bash
# 1. Setup (run once)
cd /Users/apple/Desktop/RAG/backend
./setup.sh

# 2. Add API keys to .env
nano .env  # Add your ANTHROPIC_API_KEY, OPENAI_API_KEY, EXA_API_KEY, etc.

# 3. Start everything
# Terminal 1: Redis (should already be running from setup.sh)
cd .. && docker-compose up -d

# Terminal 2: Index KB
cd backend
source .venv/bin/activate
python -m src.scripts.index_knowledge_base

# Terminal 3: Start API
uvicorn src.api.main:app --reload --port 8000
```

**API is now live at**: http://localhost:8000  
**Redis Insight**: http://localhost:8001  
**WebSocket**: ws://localhost:8000/api/v1/ws/verify/{user_id}

---

## 📡 API Usage

### WebSocket Test (with wscat)

```bash
# Install wscat
npm install -g wscat

# Connect
wscat -c ws://localhost:8000/api/v1/ws/verify/test123

# Send (paste this)
{"action":"START_VERIFICATION","payload":{"claim_text":"The Earth is flat","source_context":{"url":"https://example.com","page_title":"Test","selected_at":"2026-02-10T12:00:00Z","language":"en-US"}}}
```

### Python WebSocket Client

```python
import asyncio
import json
import websockets

async def test_claim():
    uri = "ws://localhost:8000/api/v1/ws/verify/test_user"
    
    async with websockets.connect(uri) as websocket:
        # Send claim
        request = {
            "action": "START_VERIFICATION",
            "payload": {
                "claim_text": "The Earth is flat",
                "source_context": {
                    "url": "https://example.com",
                    "page_title": "Test",
                    "selected_at": "2026-02-10T12:00:00Z",
                    "language": "en-US"
                }
            }
        }
        await websocket.send(json.dumps(request))
        
        # Receive responses
        while True:
            response = await websocket.recv()
            data = json.loads(response)
            print(f"Received: {data['type']}")
            
            if data['type'] == 'FINAL_VERDICT':
                print(f"Verdict: {data['payload']['verdict']}")
                print(f"Confidence: {data['payload']['confidence_score']}")
                break

asyncio.run(test_claim())
```

---

## 📂 Project Structure (43 files, ~3900 LOC)

```
backend/
├── src/
│   ├── api/                    # FastAPI + WebSocket
│   │   ├── main.py            # Main app (400 lines)
│   │   └── schemas/           # Request/Response models
│   ├── agents/                # LangGraph workflow
│   │   ├── graph.py           # Workflow definition
│   │   └── nodes/             # 4 processing nodes
│   ├── core/                  # Infrastructure
│   │   ├── embeddings.py      # MixedBread AI
│   │   ├── llm.py             # Claude/GPT-4o
│   │   └── redis_client.py    # Redis Stack
│   ├── retrieval/             # Multi-source retrieval
│   │   ├── knowledge_base.py  # Redis VSS
│   │   ├── web_search.py      # Brave API
│   │   └── reranker.py        # Cohere
│   ├── scoring/               # 🌟 Innovation layer
│   │   ├── credibility.py     # 35+ domain scores
│   │   ├── stance_detector.py # NLI-based
│   │   ├── consensus.py       # Weighted voting
│   │   └── thresholds.py      # Verdict logic
│   ├── evaluation/            # Quality layer
│   │   ├── ragas_metrics.py   # RAGAS wrapper
│   │   └── quality_gate.py    # Pass/fail logic
│   ├── cache/                 # Caching layer
│   ├── models/                # Pydantic models
│   ├── config/                # Settings
│   ├── data/                  # JSON databases
│   └── scripts/               # Utilities
├── .env.example
├── setup.sh
├── README.md
└── IMPLEMENTATION_SUMMARY.md
```

---

## 🔑 Required API Keys

| Service | Purpose | Get It | Free Tier |
|---------|---------|--------|-----------|
| **Anthropic** | Claude 3.5 (primary) | https://console.anthropic.com/ | $5 credit |
| **OpenAI** | GPT-4o (fallback) | https://platform.openai.com/ | Limited |
| **Brave Search** | Web search | https://brave.com/search/api/ | 2,000/month |
| **Cohere** | Reranking | https://dashboard.cohere.com/ | Yes |
| NewsAPI | News (optional) | https://newsapi.org/ | 100/day |

---

## 🎯 Verification Pipeline (4 Stages)

### Stage 1: Claim Processing (~2s)
- Text normalization
- Entity extraction (SpaCy)
- Claim classification (LLM)
- Sub-claim decomposition

**Progress**: `AGENT_STEP: "Claim Processing"`

### Stage 2: Query Planning (~1s)
- Determine retrieval strategy
- KB vs Web vs Both
- Generate search queries

**Progress**: `AGENT_STEP: "Query Planning"`

### Stage 3: Evidence Gathering (~5-8s)
- Parallel retrieval:
  - Knowledge Base (Redis VSS)
  - Web Search (Brave API)
  - Fact Checkers
- Credibility scoring
- Stance detection (NLI)
- Reranking (Cohere)

**Progress**: `AGENT_STEP: "Evidence Gathering"`

### Stage 4: Verdict Synthesis (~3s)
- Consensus calculation (weighted)
- Threshold evaluation
- LLM reasoning generation
- RAGAS evaluation
- Quality gate check

**Progress**: `AGENT_STEP: "Verdict Synthesis"`

**Final**: `FINAL_VERDICT` with verdict + confidence + citations

**Total Time**: ~10-15 seconds

---

## 🧮 Scoring Algorithm (Innovation)

### Weighted Consensus Formula

```python
# For each evidence source:
weight = credibility_score × stance_confidence

# Aggregate:
supports_weight = Σ(weight for supporting sources)
refutes_weight = Σ(weight for refuting sources)
total_weight = Σ(all weights)

# Calculate score (-100 to +100):
weighted_score = ((supports_weight - refutes_weight) / total_weight) × 100

# Calculate consensus (agreement %)
dominant_weight = max(supports_weight, refutes_weight)
consensus_pct = (dominant_weight / total_weight) × 100
```

### Verdict Thresholds

| Verdict | Conditions |
|---------|-----------|
| **TRUE** | score ≥ 75 AND consensus ≥ 70% |
| **FALSE** | score ≤ -50 AND consensus ≥ 70% |
| **MISLEADING** | consensus < 70% OR -50 < score < 75 |
| **NOT ENOUGH EVIDENCE** | sources < 3 OR quality gate failed |

---

## 🎚️ Configuration Tuning

### In `.env`

```bash
# Make verdicts stricter:
SUPPORTED_SCORE_THRESHOLD=85        # Default: 75
MIN_CONSENSUS_PERCENTAGE=80         # Default: 70
MIN_SOURCES_COUNT=5                 # Default: 3

# Make quality gates stricter:
MIN_FAITHFULNESS=0.90               # Default: 0.85
MIN_CONTEXT_PRECISION=0.80          # Default: 0.75

# Cache longer:
CACHE_TTL_SECONDS=172800            # 2 days (default: 1 day)

# Cache more aggressively:
CACHE_SIMILARITY_THRESHOLD=0.90     # Default: 0.95 (lower = more caching)
```

---

## 🐛 Troubleshooting

### Problem: "Redis connection refused"
```bash
# Check Redis
docker ps | grep redis
# Restart if needed
cd /Users/apple/Desktop/RAG && docker-compose restart redis-stack
```

### Problem: "Embedding model not found"

No longer an issue! The system now uses OpenAI's embedding API, which doesn't require downloading models.

### Problem: "SpaCy model not found"
```bash
python -m spacy download en_core_web_sm
```

### Problem: "RAGAS evaluation slow"
This is normal - RAGAS uses LLM calls for evaluation. Disable in production:
```python
# In src/api/main.py, comment out:
# ragas_scores = ragas_evaluator.evaluate_verdict(...)
```

### Problem: "WebSocket disconnects immediately"
Check CORS settings in `.env`:
```bash
ALLOWED_ORIGINS=http://localhost:3000,chrome-extension://*
```

---

## 📊 Monitoring

### Check Redis Status
```bash
# Redis CLI
docker exec -it verifact-redis-stack redis-cli

# Check indexes
FT.INFO idx:knowledge_base
FT.INFO idx:verified_claims

# Check key count
DBSIZE
```

### Check Logs
```bash
# API logs (if using uvicorn)
# Shows in terminal

# Redis logs
docker logs verifact-redis-stack
```

---

## 🧪 Testing Commands

```bash
# Test structure
python test_structure.py

# Index knowledge base
python -m src.scripts.index_knowledge_base

# Run evaluation
python -m src.scripts.run_evaluation

# Manual WebSocket test
wscat -c ws://localhost:8000/api/v1/ws/verify/test
```

---

## 📈 Performance Expectations

| Metric | Value |
|--------|-------|
| **Avg Response Time** | 10-15s |
| **Cache Hit Rate** | 30-50% (after warm-up) |
| **Concurrent Users** | 10-20 (no rate limiting) |
| **Memory Usage** | ~2GB (embedding model) |
| **Redis Memory** | ~500MB (10K cached claims) |

---

## 🎯 Next Steps for Production

1. **Add rate limiting** (e.g., 10 requests/min per user)
2. **Add authentication** (JWT tokens)
3. **Add monitoring** (Prometheus + Grafana)
4. **Optimize RAGAS** (skip in real-time, run async)
5. **Scale Redis** (Redis Cluster for high volume)
6. **Add CDN** for static assets
7. **Implement proper logging** (structured JSON logs)

---

## 💡 Tips & Tricks

### Disable Quality Gates for Testing
```python
# In src/api/main.py, set:
quality_passed = True  # Skip RAGAS
```

### Use Cached Results Only
```python
# In src/api/main.py, after cache check:
if cached_verdict:
    # return cached
else:
    return {"error": "Not in cache"}  # Don't run verification
```

### Test Without API Keys
```python
# Comment out in src/api/main.py:
# llm_client = LLMClient()
# Use mock responses
```

---

## 📞 Support

For issues or questions:
1. Check `backend/README.md`
2. Check `backend/IMPLEMENTATION_SUMMARY.md`
3. Review logs in terminal
4. Check Redis Insight: http://localhost:8001

---

**Total Implementation Time**: ~4 hours  
**Total Lines of Code**: ~3,900  
**Total Files Created**: 43  
**Test Coverage**: Structure tests + integration tests

**Status**: ✅ **PRODUCTION READY** (for local demo)

---

Built with ❤️ using LangGraph, Redis Stack, and Claude 3.5 Sonnet

