import { VerdictBadge } from "./VerdictBadge";
import { EvidenceTabs } from "./EvidenceTabs";
import type { FinalVerdict, Evidence } from "../types";

interface VerdictViewProps {
    result: FinalVerdict;
    supporting: Evidence[];
    contradicting: Evidence[];
}

export function VerdictView({ result, supporting, contradicting }: VerdictViewProps) {
    const confidencePercentage = Math.round(result.confidence_score * 100);

    const formatMetric = (val: number | null | undefined) => {
        if (val === null || val === undefined) return "N/A";
        return `${Math.round(val * 100)}%`;
    };

    return (
        <div className="space-y-6 animate-in fade-in zoom-in-95 duration-500">
            {/* Verdict Header Card */}
            <div className="bg-gray-800/40 rounded-2xl border border-gray-700/50 p-5 overflow-hidden relative">
                {/* Background Glow */}
                <div className={`absolute -top-12 -right-12 w-32 h-32 blur-[64px] opacity-20 rounded-full ${result.verdict === 'TRUE' ? 'bg-green-500' :
                    result.verdict === 'FALSE' ? 'bg-red-500' : 'bg-yellow-500'
                    }`} />

                <div className="flex flex-col gap-4 relative z-0">
                    <div className="flex items-center justify-between">
                        <VerdictBadge verdict={result.verdict} className="py-1.5 px-4 text-sm scale-110 origin-left" />
                        <div className="text-right">
                            <div className="text-[10px] text-gray-500 uppercase font-bold tracking-widest mb-0.5">Confidence</div>
                            <div className="text-xl font-black font-mono text-gray-200">{confidencePercentage}%</div>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest">Reasoning Summary</h3>
                        <p className="text-sm text-gray-300 leading-relaxed italic border-l-2 border-gray-700 pl-4">
                            {result.reasoning_summary}
                        </p>
                    </div>

                    {/* Quality Metrics Row */}
                    {result.quality_metrics && (
                        <div className="grid grid-cols-3 gap-2 pt-2 border-t border-gray-700/50">
                            <div>
                                <div className="text-[9px] text-gray-500 uppercase font-bold tracking-tighter">Faithfulness</div>
                                <div className="text-xs font-mono font-bold text-blue-400">{formatMetric(result.quality_metrics.faithfulness)}</div>
                            </div>
                            <div>
                                <div className="text-[9px] text-gray-500 uppercase font-bold tracking-tighter">Precision</div>
                                <div className="text-xs font-mono font-bold text-purple-400">{formatMetric(result.quality_metrics.context_precision)}</div>
                            </div>
                            <div>
                                <div className="text-[9px] text-gray-500 uppercase font-bold tracking-tighter">Correctness</div>
                                <div className="text-xs font-mono font-bold text-green-400">{formatMetric(result.quality_metrics.answer_correctness)}</div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Consensus & Evidence Stance */}
            {result.consensus_info && result.consensus_info.stance_distribution && (
                <div className="bg-gray-800/20 rounded-xl border border-gray-800/50 p-4 space-y-3">
                    <div className="flex items-center justify-between">
                        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest">Global Consensus</h3>
                        <span className="text-[10px] font-mono text-gray-400">{result.consensus_info.total_sources} Sources Analyzed</span>
                    </div>

                    <div className="h-1.5 w-full bg-gray-700/50 rounded-full flex overflow-hidden">
                        <div
                            className="h-full bg-green-500 transition-all duration-1000"
                            style={{ width: `${(result.consensus_info.stance_distribution.supports / (result.consensus_info.total_sources || 1)) * 100}%` }}
                        />
                        <div
                            className="h-full bg-red-500 transition-all duration-1000"
                            style={{ width: `${(result.consensus_info.stance_distribution.refutes / (result.consensus_info.total_sources || 1)) * 100}%` }}
                        />
                        <div
                            className="h-full bg-gray-500 transition-all duration-1000"
                            style={{ width: `${(result.consensus_info.stance_distribution.neutral / (result.consensus_info.total_sources || 1)) * 100}%` }}
                        />
                    </div>

                    <div className="flex justify-between text-[10px] font-bold uppercase tracking-tighter">
                        <div className="text-green-500">Supports: {result.consensus_info.stance_distribution.supports}</div>
                        <div className="text-red-500">Refutes: {result.consensus_info.stance_distribution.refutes}</div>
                        <div className="text-gray-400">Neutral: {result.consensus_info.stance_distribution.neutral}</div>
                    </div>
                </div>
            )}

            {/* Evidence Section */}
            <div className="space-y-3">
                <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest px-1">Sources & Evidence</h3>
                <div className="bg-gray-800/30 rounded-2xl border border-gray-800 h-[400px] overflow-hidden">
                    <EvidenceTabs supporting={supporting} contradicting={contradicting} />
                </div>
            </div>
        </div>
    );
}
