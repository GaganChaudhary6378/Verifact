import { useState, useEffect, useRef } from 'react';
import { VerdictBadge } from './components/VerdictBadge';
import { VerdictView } from './components/VerdictView';
import { TransparencyView } from './components/TransparencyView';
import type { MessagePayload, Evidence, AgentStep, FinalVerdict } from './types';
import { gatherSourceContext } from './lib/context';
import { API_CONFIG } from './config/api';
import './App.css';

function App() {
  const [loading, setLoading] = useState(false);
  const [claim, setClaim] = useState<string | null>(null);
  const [finalResult, setFinalResult] = useState<FinalVerdict | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [supporting, setSupporting] = useState<Evidence[]>([]);
  const [contradicting, setContradicting] = useState<Evidence[]>([]);

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Listen for messages from background script
    const handleMessage = (message: any) => {
      if (message.type === 'VERIFY_CLAIM') {
        startVerification(message.payload);
      }
    };

    chrome.runtime.onMessage.addListener(handleMessage);

    // Check if there is a pending message stored (optional, for reliability)

    return () => {
      chrome.runtime.onMessage.removeListener(handleMessage);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // Development helper to trigger verification manually
  useEffect(() => {
    if (import.meta.env.DEV) {
      // console.log("Dev mode: ready to verify");
    }
  }, []);



  const startVerification = async (payload: MessagePayload) => {
    setLoading(true);
    setClaim(payload.text);
    setFinalResult(null);
    setLogs(["Gathering enriched context...", "Connecting to Truth Engine..."]);
    setSupporting([]);
    setContradicting([]);

    try {
      const sourceContext = await gatherSourceContext(payload.text, payload.url, payload.title, payload.tabId);

      // Connect to WebSocket using configured backend URL
      const userId = "user_" + Math.random().toString(36).substring(7);
      const wsUrl = API_CONFIG.getWebSocketUrl(userId);

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({
          action: "START_VERIFICATION",
          payload: {
            claim_text: payload.text,
            source_context: sourceContext
          }
        }));
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'AGENT_STEP') {
          const step = data.payload as AgentStep;
          addLog(`${step.label}: ${step.detail}`);
        } else if (data.type === 'FINAL_VERDICT') {
          const result = data.payload as FinalVerdict;
          handleFinalResult(result);
          ws.close();
          setLoading(false);
        }
      };

      ws.onerror = (err) => {
        console.error("WS Error", err);
        addLog("Connection error. Ensure backend is running.");
        setLoading(false);
      };

      ws.onclose = () => {
        console.log("WebSocket Closed");
        setLoading(false);
      };

    } catch (error) {
      console.error("Verification failed", error);
      addLog("Error during verification process.");
      setLoading(false);
    }
  };

  const handleFinalResult = (result: FinalVerdict) => {
    // Store the complete result
    setFinalResult(result);

    // Convert citations to Evidence format with enhanced fields
    const mappedEvidence: Evidence[] = result.citations.map(c => ({
      title: c.source_name,
      url: c.url,
      snippet: c.relevance_snippet,
      source: `Trust: ${Math.round(c.trust_score * 100)}%`,
      stance: c.stance,
      relevance_score: c.relevance_score
    }));

    // Categorize evidence by stance
    const supportingEvidence = mappedEvidence.filter(e => e.stance === 'supports' || e.stance === 'SUPPORTS');
    const refutingEvidence = mappedEvidence.filter(e => e.stance === 'refutes' || e.stance === 'REFUTES');
    const neutralEvidence = mappedEvidence.filter(e => e.stance === 'neutral' || e.stance === 'NEUTRAL');

    // Set supporting and contradicting based on verdict type
    if (result.verdict === 'TRUE') {
      setSupporting([...supportingEvidence, ...neutralEvidence]);
      setContradicting(refutingEvidence);
    } else if (result.verdict === 'FALSE' || result.verdict === 'MISLEADING') {
      setSupporting(supportingEvidence);
      setContradicting([...refutingEvidence, ...neutralEvidence]);
    } else {
      // For NOT ENOUGH EVIDENCE, show all evidence
      setSupporting(supportingEvidence);
      setContradicting(refutingEvidence);
    }

    addLog(`Final Verdict: ${result.verdict}`);
    addLog(result.reasoning_summary);
  };

  const addLog = (log: string) => {
    setLogs(prev => [...prev, log]);
  };

  return (
    <div className="w-full min-h-screen bg-gray-900 text-gray-100 font-sans flex flex-col">
      {/* Header */}
      <header className="p-4 border-b border-gray-800 bg-gray-900/50 backdrop-blur sticky top-0 z-10">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            AI Verifier
          </h1>
          <div className="flex items-center gap-3">
            {finalResult && (
              <>
                <div className="text-xs text-gray-400">
                  Confidence: <span className="font-semibold text-blue-400">{(finalResult.confidence_score * 100).toFixed(1)}%</span>
                </div>
                <VerdictBadge verdict={finalResult.verdict as any} />
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Claim Section */}
        {claim ? (
          <div className="space-y-2">
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Claim</h2>
            <div className="p-3 bg-gray-800 rounded-lg border border-gray-700 text-sm italic">
              "{claim}"
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-64 text-center p-6 space-y-4">
            <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <p className="text-gray-400 text-sm">
              Select text on any webpage, right-click, and choose <span className="text-blue-400 font-medium">"Verify Claim"</span> to start.
            </p>
          </div>
        )}

        {/* Transparency View */}
        {(loading || logs.length > 0) && (
          <TransparencyView logs={logs} isLoading={loading} />
        )}

        {/* Final Verdict Display - Using VerdictView component for all verdicts */}
        {finalResult && !loading && (
          <VerdictView 
            result={finalResult}
            supporting={supporting}
            contradicting={contradicting}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="p-3 border-t border-gray-800 text-center">
        <p className="text-xs text-gray-600">Powered by Agentic RAG</p>
      </footer>
    </div>
  );
}

export default App;
