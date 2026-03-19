export type Verdict = 'TRUE' | 'FALSE' | 'MISLEADING' | 'NOT ENOUGH EVIDENCE' | 'Unverified';

export interface GeoData {
    country: string;
    city: string;
    timezone: string;
    timezone_offset: number;
    coordinates: {
        lat: number;
        lon: number;
        accuracy: number;
    };
}

export interface NetworkContext {
    ip_address: string;
    connection_type: string;
    is_vpn_detected: boolean;
}

export interface PageMetadata {
    url: string;
    page_title: string;
    selected_at: string;
    language: string;
    description: string;
    author: string;
    published_date: string;
    site_name: string;
}

export interface WebpageContent {
    full_text: string;
    raw_meta_tags: Record<string, string>;
    structured_data: any[];
    og_tags: {
        title: string;
        image: string;
        type: string;
    };
}

export interface SourceContext {
    page_metadata: PageMetadata;
    webpage_content: WebpageContent;
    geo_data: GeoData;
    network_context: NetworkContext;
    browser_info: {
        user_agent: string;
        platform: string;
        screen_resolution: string;
    };
    search_stack: {
        preferred_engine: string;
        safe_search: boolean;
    };
}

export interface AgentStep {
    step_id: number;
    label: string;
    detail: string;
    timestamp: string;
}

export interface Citation {
    source_name: string;
    url: string;
    relevance_snippet: string;
    trust_score: number;
    stance?: string; // 'supports' | 'refutes' | 'neutral'
    relevance_score?: number;
}

export interface QualityMetrics {
    faithfulness?: number;
    context_precision?: number;
    answer_correctness?: number;
}

export interface ConsensusInfo {
    supporting_sources: number;
    refuting_sources: number;
    neutral_sources: number;
    total_sources: number;
    consensus_percentage: number;
    stance_distribution?: {
        supports: number;
        refutes: number;
        neutral: number;
    };
}

export interface FinalVerdict {
    request_id: string;
    verdict: Verdict;
    confidence_score: number;
    reasoning_summary: string;
    citations: Citation[];
    quality_metrics?: QualityMetrics;
    consensus_info?: ConsensusInfo;
}

export interface MessagePayload {
    text: string;
    url: string;
    title: string;
    /** Tab ID from context menu; use this for scripting so we target the correct tab (e.g. from side panel). */
    tabId?: number;
}

export interface Evidence {
    url: string;
    title: string;
    snippet: string;
    source: string;
    stance?: string;
    relevance_score?: number;
}
