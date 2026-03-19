"""FastAPI main application with WebSocket support for real-time fact verification.

This is the main entry point for the VeriFact backend API. It provides:
- Health check endpoints
- WebSocket endpoint for real-time claim verification
- CORS middleware for frontend/extension access
- Graceful error handling and logging
"""

import asyncio
import sys
from contextlib import asynccontextmanager
from typing import Dict
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from ..agents.graph import create_verification_graph
from ..cache.claim_cache import ClaimCache
from ..config.settings import get_settings
from ..core.embeddings import EmbeddingManager
from ..core.llm import LLMClient
from ..core.redis_client import RedisClient
from ..evaluation.quality_gate import QualityGate
from ..evaluation.ragas_metrics import RAGASEvaluator
from .schemas.request import VerifyRequest
from .schemas.response import Citation, VerifyResponse


# Configure asyncio to suppress harmless connection cleanup errors
def suppress_httpx_cleanup_errors(loop, context):
    """Suppress harmless HTTPX connection cleanup errors."""
    exception = context.get('exception')
    if exception:
        # Suppress "handler is closed" errors from HTTPX cleanup
        if isinstance(exception, RuntimeError) and 'handler is closed' in str(exception):
            logger.debug(f"Suppressed harmless cleanup error: {exception}")
            return
    # For other errors, use default handler
    loop.default_exception_handler(context)


# Set the exception handler for the event loop
try:
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(suppress_httpx_cleanup_errors)
except RuntimeError:
    # If no event loop exists yet, it will be set when uvicorn starts
    pass


# Global instances (initialized in lifespan)
redis_client: RedisClient = None
embedding_manager: EmbeddingManager = None
llm_client: LLMClient = None
verification_graph = None
claim_cache: ClaimCache = None
ragas_evaluator: RAGASEvaluator = None
quality_gate: QualityGate = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown.
    
    Handles initialization of all core components and cleanup on shutdown.
    """
    global redis_client, embedding_manager, llm_client, verification_graph
    global claim_cache, ragas_evaluator, quality_gate

    logger.info("=" * 60)
    logger.info("Starting VeriFact Backend...")
    logger.info("=" * 60)

    try:
        # Initialize core components
        settings = get_settings()
        
        # Log configuration status
        api_keys = settings.validate_api_keys()
        logger.info(f"API Keys configured: {sum(api_keys.values())}/{len(api_keys)}")
        for service, configured in api_keys.items():
            status_icon = "✓" if configured else "✗"
            logger.info(f"  {status_icon} {service}: {'configured' if configured else 'missing'}")

        # Initialize Redis
        logger.info("Initializing Redis client...")
        redis_client = RedisClient()
        
        # Initialize AI components
        logger.info("Initializing embedding manager...")
        embedding_manager = EmbeddingManager()
        
        logger.info("Initializing LLM client...")
        llm_client = LLMClient()

        # Create Redis indexes
        logger.info("Creating Redis indexes...")
        redis_client.create_knowledge_base_index()
        redis_client.create_verified_claims_index()

        # Create verification graph
        logger.info("Creating verification graph...")
        verification_graph = create_verification_graph(
            redis_client,
            embedding_manager,
            llm_client,
        )

        # Initialize cache and evaluation
        logger.info("Initializing cache and evaluation components...")
        claim_cache = ClaimCache(redis_client, embedding_manager)
        ragas_evaluator = RAGASEvaluator()
        quality_gate = QualityGate()

        logger.info("=" * 60)
        logger.info("✓ VeriFact backend started successfully")
        logger.info(f"✓ API server: http://{settings.api_host}:{settings.api_port}")
        logger.info(f"✓ Health check: http://{settings.api_host}:{settings.api_port}/health")
        logger.info("=" * 60)

        yield

    except Exception as e:
        logger.error(f"Failed to start VeriFact backend: {e}")
        raise
    
    finally:
        # Cleanup
        logger.info("Shutting down VeriFact backend...")
        if redis_client:
            redis_client.close()
        logger.info("✓ Shutdown complete")


# Create FastAPI app
settings = get_settings()
app = FastAPI(
    title="VeriFact API",
    description="Real-Time News Claim Verification System with AI-powered fact-checking",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,  # Disable docs in production
    redoc_url="/redoc" if not settings.is_production else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        """Accept WebSocket connection."""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket connected: {user_id}")

    def disconnect(self, user_id: str):
        """Remove WebSocket connection."""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected: {user_id}")

    async def send_message(self, user_id: str, message: dict):
        """Send message to specific user."""
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)


manager = ConnectionManager()


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers.
    
    Returns:
        Health status with service information
    """
    try:
        # Check Redis connectivity
        redis_ok = redis_client is not None and redis_client.client.ping()
        
        health_status = {
            "status": "healthy" if redis_ok else "degraded",
            "service": "verifact",
            "version": "1.0.0",
            "components": {
                "redis": "connected" if redis_ok else "disconnected",
                "llm": "ready" if llm_client else "not initialized",
                "embeddings": "ready" if embedding_manager else "not initialized",
            }
        }
        
        status_code = 200 if redis_ok else 503
        return JSONResponse(content=health_status, status_code=status_code)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e)},
            status_code=503
        )


@app.websocket("/api/v1/ws/verify/{user_id}")
async def websocket_verify_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for claim verification.

    Args:
        websocket: WebSocket connection
        user_id: User identifier
    """
    await manager.connect(user_id, websocket)

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()

            action = data.get("action")
            payload = data.get("payload", {})

            logger.info(f"📨 WebSocket message received from {user_id}")
            logger.info(f"   Action: {action}")
            logger.info(f"   Payload preview: {str(payload)[:200]}...")

            if action == "START_VERIFICATION":
                # Start verification in background
                asyncio.create_task(
                    process_verification(user_id, payload, websocket)
                )
            else:
                await websocket.send_json({
                    "type": "ERROR",
                    "payload": {"message": f"Unknown action: {action}"},
                })

    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(user_id)


async def process_verification(user_id: str, payload: dict, websocket: WebSocket):
    """
    Process claim verification asynchronously.

    Args:
        user_id: User identifier
        payload: Request payload
        websocket: WebSocket connection
    """
    request_id = str(uuid4())

    try:
        # Log full payload for debugging
        import json
        logger.info(f"[{request_id}] 📦 FULL PAYLOAD:")
        logger.info(f"{json.dumps(payload, indent=2)}")
        
        # Parse request
        verify_request = VerifyRequest(**payload)

        logger.info(f"[{request_id}] ============= VERIFICATION START =============")
        logger.info(f"[{request_id}] Claim: {verify_request.claim_text}")
        
        # Extract URL from nested structure
        source_url = "N/A"
        try:
            if verify_request.source_context and verify_request.source_context.page_metadata:
                source_url = verify_request.source_context.page_metadata.url
        except Exception:
            pass
        
        logger.info(f"[{request_id}] Source URL: {source_url}")
        logger.info(f"[{request_id}] =============================================")

        # Check cache first
        cached_verdict = claim_cache.get_cached_verdict(verify_request.claim_text)

        if cached_verdict:
            logger.info(f"[{request_id}] Cache hit!")

            # Reconstruct complete response from cache
            # Parse citations from JSON string
            cached_citations = []
            citations_json = cached_verdict.get("citations_json", "[]")
            try:
                citations_list = json.loads(citations_json) if isinstance(citations_json, str) else []
                for citation_data in citations_list:
                    cached_citations.append(Citation(**citation_data))
            except Exception as e:
                logger.warning(f"Failed to parse cached citations: {e}")

            # Parse quality metrics and consensus from JSON strings
            quality_metrics = None
            try:
                qm_json = cached_verdict.get("quality_metrics_json", "{}")
                quality_metrics = json.loads(qm_json) if isinstance(qm_json, str) else None
            except Exception:
                pass

            consensus_info = None
            try:
                ci_json = cached_verdict.get("consensus_info_json", "{}")
                consensus_info = json.loads(ci_json) if isinstance(ci_json, str) else None
            except Exception:
                pass
            
            # Build complete response with all cached data
            response = VerifyResponse(
                request_id=request_id,
                verdict=cached_verdict.get("verdict", "NOT ENOUGH EVIDENCE"),
                confidence_score=float(cached_verdict.get("confidence", 0.5)),
                reasoning_summary=cached_verdict.get("reasoning", "Cached result"),
                citations=cached_citations,
                quality_metrics=quality_metrics,
                consensus_info=consensus_info,
            )

            logger.info(f"[{request_id}] Returning cached verdict: {response.verdict} ({response.confidence_score:.0%})")
            logger.info(f"[{request_id}] Cached citations: {len(cached_citations)}")

            await websocket.send_json({
                "type": "FINAL_VERDICT",
                "payload": response.model_dump(),
            })
            return

        # Initialize state
        state = {
            "request_id": request_id,
            "raw_claim": verify_request.claim_text,
            "source_context": verify_request.source_context.model_dump(),
            "kb_evidence": [],
            "web_evidence": [],
            "fact_check_evidence": [],
            "all_evidence": [],
            "quality_passed": True,
            "current_step": "",
            "progress_messages": [],
        }

        # Run verification graph
        logger.info(f"[{request_id}] Running verification graph...")

        # Execute graph synchronously (LangGraph doesn't support async well)
        result_state = await asyncio.to_thread(verification_graph.invoke, state)

        # Send progress updates
        for progress_msg in result_state.get("progress_messages", []):
            await websocket.send_json({
                "type": "AGENT_STEP",
                "payload": progress_msg,
            })
            await asyncio.sleep(0.1)  # Small delay for UI updates

        # Get verdict
        verdict = result_state.get("verdict")

        if not verdict:
            raise Exception("Verification failed to produce verdict")

        # Evaluate with RAGAS
        logger.info(f"[{request_id}] Evaluating with RAGAS...")
        ragas_scores = ragas_evaluator.evaluate_verdict(
            verify_request.claim_text,
            result_state.get("all_evidence", []),
            verdict,
        )

        # Update verdict with quality metrics
        verdict.quality_metrics = ragas_scores

        # Check quality gate
        quality_passed = quality_gate.check(verdict, ragas_scores)

        if not quality_passed:
            verdict = quality_gate.override_verdict(verdict, quality_passed)

        # Prepare citations with enhanced information (moved before cache)
        citations = []
        supporting_count = 0
        refuting_count = 0
        neutral_count = 0
        
        for evidence in result_state.get("all_evidence", [])[:10]:  # Top 10 for better coverage
            # Count stances
            if evidence.stance.value == "supports":
                supporting_count += 1
            elif evidence.stance.value == "refutes":
                refuting_count += 1
            elif evidence.stance.value == "neutral":
                neutral_count += 1
            
            # Create enhanced citation
            citation = Citation(
                source_name=evidence.source.title[:50] + "..." if len(evidence.source.title) > 50 else evidence.source.title,
                url=str(evidence.source.url),
                relevance_snippet=evidence.content[:300] if evidence.content else evidence.source.snippet[:300],
                trust_score=min(1.0, evidence.source.credibility_score / 100.0),  # Normalize to 0-1
                stance=evidence.stance.value,
                relevance_score=evidence.relevance_score,
            )
            citations.append(citation)
        
        # Calculate consensus info
        total_sources = supporting_count + refuting_count + neutral_count
        consensus_info = {
            "supporting_sources": supporting_count,
            "refuting_sources": refuting_count,
            "neutral_sources": neutral_count,
            "total_sources": total_sources,
            "consensus_percentage": verdict.consensus_percentage,
        }

        # Cache if high quality (NOW citations and consensus_info are defined)
        if quality_gate.should_cache(verdict, ragas_scores):
            claim_cache.cache_verdict(
                verify_request.claim_text, 
                verdict,
                citations=citations,
                consensus_info=consensus_info,
            )
            logger.info(f"[{request_id}] ✅ Verdict cached with {len(citations)} citations")

        # Store verified claim in knowledge base if verdict is confident
        if verdict.verdict_type in ["TRUE", "FALSE"] and verdict.confidence_score >= 0.75:
            try:
                from datetime import datetime
                
                # Extract source URL safely
                kb_source_url = ""
                try:
                    if verify_request.source_context and verify_request.source_context.page_metadata:
                        kb_source_url = verify_request.source_context.page_metadata.url
                except Exception:
                    pass
                
                # Create document content
                sources_str = ', '.join([c.source_name for c in citations[:3]]) if citations else "N/A"
                doc_content = f"""Claim: {verify_request.claim_text}
Verdict: {verdict.verdict_type}
Confidence: {verdict.confidence_score:.2%}
Reasoning: {verdict.reasoning_summary}
Sources: {sources_str}
Verified: {datetime.now().strftime('%Y-%m-%d')}"""
                
                # Generate embedding
                embedding = embedding_manager.embed_text(doc_content)
                
                # Store in knowledge base (note: add_document doesn't take index_name)
                doc_id = f"verified_{request_id}"
                redis_client.add_document(
                    doc_id=doc_id,
                    doc_data={
                        "content": doc_content,
                        "content_vector": embedding,
                        "source": "VeriFact Verification",
                        "url": kb_source_url,
                        "category": "verified_claim",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                
                logger.info(f"[{request_id}] 💾 Stored verified claim in knowledge base (id: {doc_id})")
                
            except Exception as e:
                logger.warning(f"[{request_id}] Failed to store claim in KB: {e}")

        # Send final verdict with enhanced information
        response = VerifyResponse(
            request_id=request_id,
            verdict=verdict.verdict_type,
            confidence_score=verdict.confidence_score,
            reasoning_summary=verdict.reasoning_summary,
            citations=citations,
            quality_metrics=ragas_scores if ragas_scores else None,
            consensus_info=consensus_info,
        )

        logger.info(f"[{request_id}] ============= VERIFICATION END =============")
        logger.info(f"[{request_id}] Verdict: {verdict.verdict_type}")
        logger.info(f"[{request_id}] Confidence: {verdict.confidence_score:.2f}")
        logger.info(f"[{request_id}] Sources used: {len(citations)}")
        logger.info(f"[{request_id}] ============================================")

        await websocket.send_json({
            "type": "FINAL_VERDICT",
            "payload": response.model_dump(),
        })

        logger.info(f"[{request_id}] Verification complete: {verdict.verdict_type}")

    except Exception as e:
        logger.error(f"[{request_id}] Verification error: {e}")

        # Send error response
        await websocket.send_json({
            "type": "ERROR",
            "payload": {
                "request_id": request_id,
                "message": f"Verification failed: {str(e)}",
            },
        })


def run_server():
    """Run FastAPI server."""
    settings = get_settings()

    # Ensure the exception handler is set for the event loop
    def on_startup():
        """Set exception handler when server starts."""
        try:
            loop = asyncio.get_running_loop()
            loop.set_exception_handler(suppress_httpx_cleanup_errors)
            logger.info("✓ Asyncio exception handler configured")
        except Exception as e:
            logger.warning(f"Could not set exception handler: {e}")

    # Run with exception handler setup
    config = uvicorn.Config(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    
    # Set the exception handler before running
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.set_exception_handler(suppress_httpx_cleanup_errors)
        logger.info("✓ Asyncio exception handler configured for server")
    except Exception as e:
        logger.warning(f"Could not pre-configure exception handler: {e}")
    
    server.run()


if __name__ == "__main__":
    run_server()

