import type { QualityMetrics } from '../types';

interface QualityMetricsProps {
    metrics: QualityMetrics;
    confidenceScore: number;
}

export function QualityMetricsDisplay({ metrics, confidenceScore }: QualityMetricsProps) {
    const getScoreColor = (score: number) => {
        if (score >= 0.8) return 'text-green-400';
        if (score >= 0.6) return 'text-yellow-400';
        return 'text-red-400';
    };

    const getBarColor = (score: number) => {
        if (score >= 0.8) return 'bg-green-500';
        if (score >= 0.6) return 'bg-yellow-500';
        return 'bg-red-500';
    };

    return (
        <div className="space-y-3">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Quality Assessment</h3>

            <div className="bg-gray-800 rounded-lg border border-gray-700 p-4 space-y-4">
                {/* Confidence Score */}
                <div className="space-y-2">
                    <div className="flex justify-between items-center text-sm">
                        <span className="text-gray-400">Confidence</span>
                        <span className={`font-semibold ${getScoreColor(confidenceScore)}`}>
                            {(confidenceScore * 100).toFixed(1)}%
                        </span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
                        <div
                            className={`${getBarColor(confidenceScore)} h-full rounded-full transition-all duration-500`}
                            style={{ width: `${confidenceScore * 100}%` }}
                        />
                    </div>
                </div>

                {/* Faithfulness Score */}
                {metrics.faithfulness !== undefined && (
                    <div className="space-y-2">
                        <div className="flex justify-between items-center text-sm">
                            <span className="text-gray-400">Faithfulness</span>
                            <span className={`font-semibold ${getScoreColor(metrics.faithfulness)}`}>
                                {(metrics.faithfulness * 100).toFixed(1)}%
                            </span>
                        </div>
                        <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
                            <div
                                className={`${getBarColor(metrics.faithfulness)} h-full rounded-full transition-all duration-500`}
                                style={{ width: `${metrics.faithfulness * 100}%` }}
                            />
                        </div>
                        <p className="text-xs text-gray-500 italic">How well the verdict aligns with evidence</p>
                    </div>
                )}

                {/* Context Precision */}
                {metrics.context_precision !== undefined && (
                    <div className="space-y-2">
                        <div className="flex justify-between items-center text-sm">
                            <span className="text-gray-400">Context Precision</span>
                            <span className={`font-semibold ${getScoreColor(metrics.context_precision)}`}>
                                {(metrics.context_precision * 100).toFixed(1)}%
                            </span>
                        </div>
                        <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
                            <div
                                className={`${getBarColor(metrics.context_precision)} h-full rounded-full transition-all duration-500`}
                                style={{ width: `${metrics.context_precision * 100}%` }}
                            />
                        </div>
                        <p className="text-xs text-gray-500 italic">Precision of retrieved context</p>
                    </div>
                )}
            </div>
        </div>
    );
}
