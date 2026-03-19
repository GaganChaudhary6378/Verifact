import { useEffect, useRef } from "react";

interface TransparencyViewProps {
    logs: string[];
    isLoading: boolean;
}

export function TransparencyView({ logs, isLoading }: TransparencyViewProps) {
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <div className="bg-black/30 rounded-xl p-4 border border-gray-800 backdrop-blur-sm">
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Agent Reasoning</h3>
                {isLoading && <span className="animate-pulse h-2 w-2 rounded-full bg-blue-500"></span>}
            </div>

            <div
                ref={scrollRef}
                className="h-32 overflow-y-auto space-y-2 text-sm font-mono scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent pr-2"
            >
                {logs.map((log, i) => (
                    <div key={i} className="text-gray-300 border-l-2 border-gray-700 pl-2 py-0.5 animate-in fade-in slide-in-from-left-1 duration-300">
                        <span className="text-gray-500 opacity-50 mr-2">
                            {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </span>
                        {log}
                    </div>
                ))}
                {isLoading && (
                    <div className="text-blue-400 animate-pulse pl-2 border-l-2 border-blue-500/50">
                        Thinking...
                    </div>
                )}
            </div>
        </div>
    );
}
