import type { MessagePayload, Verdict, Evidence } from '../types';

export interface VerificationResponse {
    verdict: Verdict;
    supporting: Evidence[];
    contradicting: Evidence[];
}

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export async function mockVerifyClaim(
    payload: MessagePayload,
    onLog: (log: string) => void
): Promise<VerificationResponse> {
    console.log("Verifying claim for:", payload);
    onLog("Searching trusted fact-checking databases...");
    await delay(1000);

    onLog("Cross-referencing with news sources...");
    await delay(1500);

    onLog("Analyzing sentiment and bias...");
    await delay(1000);

    // Mock Result Determination
    const isTrue = Math.random() > 0.5;
    const isNotEnoughEvidence = Math.random() > 0.8;

    if (isNotEnoughEvidence) {
        onLog("Insufficient data points found.");
        return {
            verdict: 'Unverified',
            supporting: [],
            contradicting: []
        };
    } else {
        if (isTrue) {
            onLog("Consensus found: Claim appears accurate.");
            return {
                verdict: 'TRUE',
                supporting: [
                    { title: "Trusted News Report", url: "https://example.com", snippet: "The event did occur as described...", source: "Example News" },
                    { title: "Official Statement", url: "https://example.org", snippet: "Confirmed by spokesperson...", source: "Gov Widget" }
                ],
                contradicting: []
            };
        } else {
            onLog("Contradiction detected in multiple sources.");
            return {
                verdict: 'FALSE',
                supporting: [],
                contradicting: [
                    { title: "Fact Check: Debunked", url: "https://factcheck.org", snippet: "This claim has been proven false...", source: "FactCheck" }
                ]
            };
        }
    }
}
