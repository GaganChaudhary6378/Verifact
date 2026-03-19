import type { ConsensusInfo } from '../types';

interface ConsensusInfoProps {
    consensusInfo: ConsensusInfo;
}

export function ConsensusInfoDisplay({ consensusInfo }: ConsensusInfoProps) {
    const { supporting_sources, refuting_sources, neutral_sources, total_sources, consensus_percentage } = consensusInfo;

    return (
        <div className="space-y-3">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Source Analysis</h3>

            <div className="bg-gray-800 rounded-lg border border-gray-700 p-4 space-y-4">
                {/* Consensus Percentage */}
                <div className="space-y-2">
                    <div className="flex justify-between items-center text-sm">
                        <span className="text-gray-400">Consensus</span>
                        <span className="text-gray-200 font-semibold">{consensus_percentage.toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
                        <div
                            className="bg-gradient-to-r from-blue-500 to-purple-500 h-full rounded-full transition-all duration-500"
                            style={{ width: `${consensus_percentage}%` }}
                        />
                    </div>
                </div>

                {/* Source Breakdown */}
                <div className="grid grid-cols-3 gap-3 text-center">
                    {/* Supporting */}
                    <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3">
                        <div className="text-2xl font-bold text-green-400">{supporting_sources}</div>
                        <div className="text-xs text-gray-400 mt-1">Supporting</div>
                    </div>

                    {/* Refuting */}
                    <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
                        <div className="text-2xl font-bold text-red-400">{refuting_sources}</div>
                        <div className="text-xs text-gray-400 mt-1">Refuting</div>
                    </div>

                    {/* Neutral */}
                    <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3">
                        <div className="text-2xl font-bold text-yellow-400">{neutral_sources}</div>
                        <div className="text-xs text-gray-400 mt-1">Neutral</div>
                    </div>
                </div>

                {/* Total Sources */}
                <div className="text-center pt-2 border-t border-gray-700">
                    <span className="text-xs text-gray-500">Total Sources Analyzed: </span>
                    <span className="text-sm text-gray-300 font-semibold">{total_sources}</span>
                </div>
            </div>
        </div>
    );
}
