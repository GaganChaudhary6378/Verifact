import { useState } from "react";
import type { Evidence } from "../types";
import { cn } from "../lib/utils";

interface EvidenceTabsProps {
    supporting: Evidence[];
    contradicting: Evidence[];
}

export function EvidenceTabs({ supporting, contradicting }: EvidenceTabsProps) {
    const [activeTab, setActiveTab] = useState<"supporting" | "contradicting">("supporting");

    const activeEvidence = activeTab === "supporting" ? supporting : contradicting;

    const getStanceBadge = (stance?: string) => {
        if (!stance) return null;

        const stanceConfig = {
            supports: { color: 'bg-green-500/20 text-green-400 border-green-500/30', label: 'Supports' },
            refutes: { color: 'bg-red-500/20 text-red-400 border-red-500/30', label: 'Refutes' },
            neutral: { color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30', label: 'Neutral' },
        };

        const config = stanceConfig[stance as keyof typeof stanceConfig];
        if (!config) return null;

        return (
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${config.color}`}>
                {config.label}
            </span>
        );
    };

    return (
        <div className="flex flex-col h-full">
            <div className="flex border-b border-gray-700">
                <button
                    onClick={() => setActiveTab("supporting")}
                    className={cn(
                        "flex-1 py-2 text-sm font-medium transition-colors border-b-2",
                        activeTab === "supporting"
                            ? "border-green-500 text-green-500 bg-green-500/5"
                            : "border-transparent text-gray-400 hover:text-gray-200"
                    )}
                >
                    Supporting ({supporting.length})
                </button>
                <button
                    onClick={() => setActiveTab("contradicting")}
                    className={cn(
                        "flex-1 py-2 text-sm font-medium transition-colors border-b-2",
                        activeTab === "contradicting"
                            ? "border-red-500 text-red-500 bg-red-500/5"
                            : "border-transparent text-gray-400 hover:text-gray-200"
                    )}
                >
                    Contradicting ({contradicting.length})
                </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {activeEvidence.length === 0 ? (
                    <div className="text-center text-gray-500 py-8">
                        No {activeTab} evidence found.
                    </div>
                ) : (
                    activeEvidence.map((item, idx) => (
                        <div key={idx} className="p-3 bg-gray-800/50 rounded-lg border border-gray-700 hover:border-gray-600 transition-all">
                            <div className="flex items-start justify-between gap-2 mb-2">
                                <a href={item.url} target="_blank" rel="noopener noreferrer" className="text-sm font-semibold text-blue-400 hover:underline flex-1">
                                    {item.title}
                                </a>
                                {getStanceBadge(item.stance)}
                            </div>

                            <div className="flex items-center gap-3 mb-2">
                                <div className="text-xs text-gray-500 truncate flex-1">{item.source}</div>
                                {item.relevance_score !== undefined && (
                                    <div className="flex items-center gap-1">
                                        <span className="text-xs text-gray-500">Relevance:</span>
                                        <span className="text-xs font-semibold text-blue-400">
                                            {(item.relevance_score * 100).toFixed(0)}%
                                        </span>
                                    </div>
                                )}
                            </div>

                            <p className="text-sm text-gray-300 line-clamp-3">"{item.snippet}"</p>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
