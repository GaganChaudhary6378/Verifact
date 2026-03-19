import { cn } from "../lib/utils";
import type { Verdict } from "../types";

const badgeColors: Record<Verdict, string> = {
    TRUE: "bg-green-500/10 text-green-500 border-green-500/20",
    FALSE: "bg-red-500/10 text-red-500 border-red-500/20",
    MISLEADING: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
    'NOT ENOUGH EVIDENCE': "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
    Unverified: "bg-gray-500/10 text-gray-500 border-gray-500/20",
};

interface VerdictBadgeProps {
    verdict: Verdict;
    className?: string;
}

export function VerdictBadge({ verdict, className }: VerdictBadgeProps) {
    return (
        <div
            className={cn(
                "px-3 py-1 rounded-full border text-sm font-medium inline-flex items-center gap-2",
                badgeColors[verdict],
                className
            )}
        >
            <span className="relative flex h-2 w-2">
                <span className={cn("animate-ping absolute inline-flex h-full w-full rounded-full opacity-75", badgeColors[verdict].split(" ")[1].replace("text-", "bg-"))}></span>
                <span className={cn("relative inline-flex rounded-full h-2 w-2", badgeColors[verdict].split(" ")[1].replace("text-", "bg-"))}></span>
            </span>
            {verdict.toUpperCase()}
        </div>
    );
}
