import { Readability } from '@mozilla/readability';
import type { SourceContext, GeoData, NetworkContext, PageMetadata, WebpageContent } from '../types';

export async function gatherSourceContext(text: string, url: string, title: string, tabId?: number): Promise<SourceContext> {
    console.log("Gathering enriched context for claim:", text);

    const [geoData, webpageData] = await Promise.all([
        getGeoData(),
        getWebpageData(tabId)
    ]);

    return {
        page_metadata: {
            url,
            page_title: title,
            selected_at: new Date().toISOString(),
            language: navigator.language || 'en-US',
            description: webpageData.page_metadata.description || '',
            author: webpageData.page_metadata.author || '',
            published_date: webpageData.page_metadata.published_date || '',
            site_name: webpageData.page_metadata.site_name || ''
        },
        webpage_content: webpageData.webpage_content,
        geo_data: geoData,
        network_context: await getNetworkContext(),
        browser_info: {
            user_agent: navigator.userAgent,
            platform: navigator.platform,
            screen_resolution: `${window.screen.width}x${window.screen.height}`
        },
        search_stack: {
            preferred_engine: 'google',
            safe_search: true
        }
    };
}

/** Minimum length to consider Readability result good; below this we try iframes or body fallback */
const MIN_READABILITY_LENGTH = 200;

async function getWebpageData(providedTabId?: number): Promise<{ page_metadata: Partial<PageMetadata>, webpage_content: WebpageContent }> {
    try {
        let tabId: number;
        if (providedTabId != null && providedTabId > 0) {
            tabId = providedTabId;
        } else {
            const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
            if (!tab?.id) throw new Error("No active tab found");
            tabId = tab.id;
        }

        // Script that runs in each frame: return HTML and raw body text for that frame
        const getFrameContent = () => {
            const html = document.documentElement.outerHTML;
            const bodyText = document.body?.innerText?.trim() ?? '';
            return { html, bodyText };
        };

        // Main-frame script also collects meta (for page_metadata)
        const getMainFrameContent = () => {
            const getMeta = (property: string) => {
                const el = document.querySelector(`meta[property="${property}"], meta[name="${property}"]`);
                return el ? el.getAttribute('content') : '';
            };
            const metaTags: Record<string, string> = {};
            document.querySelectorAll('meta').forEach(meta => {
                const name = meta.getAttribute('name') || meta.getAttribute('property');
                const content = meta.getAttribute('content');
                if (name && content) metaTags[name] = content;
            });
            const structuredData: any[] = [];
            document.querySelectorAll('script[type="application/ld+json"]').forEach(script => {
                try {
                    structuredData.push(JSON.parse(script.textContent || '{}'));
                } catch (e) { }
            });
            return {
                html: document.documentElement.outerHTML,
                bodyText: document.body?.innerText?.trim() ?? '',
                description: getMeta('description') || getMeta('og:description'),
                author: getMeta('author') || getMeta('article:author'),
                published_date: getMeta('published_date') || getMeta('article:published_time'),
                site_name: getMeta('og:site_name') || window.location.hostname,
                raw_meta_tags: metaTags,
                structured_data: structuredData,
                og_tags: {
                    title: getMeta('og:title') || document.title,
                    image: getMeta('og:image') || '',
                    type: getMeta('og:type') || 'website'
                }
            };
        };

        type FrameInfo = { frameId: number; url?: string };
        let frames: FrameInfo[] = [{ frameId: 0 }];

        try {
            if (chrome.webNavigation?.getAllFrames) {
                const allFrames = await chrome.webNavigation.getAllFrames({ tabId });
                if (allFrames?.length) {
                    frames = allFrames.map((f: { frameId: number; url?: string }) => ({ frameId: f.frameId, url: f.url }));
                }
            }
        } catch (_) {
            // Permission or API not available; use main frame only
        }

        const htmlsAndFallbacks: { html: string; bodyText: string }[] = [];
        let metaPayload: {
            description: string;
            author: string;
            published_date: string;
            site_name: string;
            raw_meta_tags: Record<string, string>;
            structured_data: any[];
            og_tags: { title: string; image: string; type: string };
        } = {
            description: '',
            author: '',
            published_date: '',
            site_name: '',
            raw_meta_tags: {},
            structured_data: [],
            og_tags: { title: '', image: '', type: '' }
        };

        for (const { frameId } of frames) {
            try {
                const target = frameId === 0
                    ? { tabId }
                    : { tabId, frameIds: [frameId] };
                const isMain = frameId === 0;
                const results = await chrome.scripting.executeScript({
                    target,
                    func: isMain ? getMainFrameContent : getFrameContent,
                });
                const raw = results[0]?.result as Record<string, unknown> & { html: string; bodyText: string };
                if (!raw || typeof raw.html !== 'string') continue;
                htmlsAndFallbacks.push({
                    html: raw.html,
                    bodyText: typeof raw.bodyText === 'string' ? raw.bodyText : '',
                });
                if (isMain && raw.description !== undefined) {
                    metaPayload = {
                        description: String(raw.description ?? ''),
                        author: String(raw.author ?? ''),
                        published_date: String(raw.published_date ?? ''),
                        site_name: String(raw.site_name ?? ''),
                        raw_meta_tags: (raw.raw_meta_tags as Record<string, string>) ?? {},
                        structured_data: (raw.structured_data as unknown[]) ?? [],
                        og_tags: (raw.og_tags as { title: string; image: string; type: string }) ?? { title: '', image: '', type: '' },
                    };
                }
            } catch (e) {
                // Cross-origin or inaccessible frame; skip
                continue;
            }
        }

        let fullText = '';
        for (const { html, bodyText } of htmlsAndFallbacks) {
            let candidate = '';
            try {
                const doc = new DOMParser().parseFromString(html, 'text/html');
                const reader = new Readability(doc);
                const article = reader.parse();
                candidate = article?.textContent?.trim() ?? '';
            } catch (_) { }
            if (candidate.length < MIN_READABILITY_LENGTH && bodyText.length > candidate.length) {
                candidate = bodyText;
            }
            if (candidate.length > fullText.length) {
                fullText = candidate;
            }
        }

        return {
            page_metadata: {
                description: metaPayload.description,
                author: metaPayload.author,
                published_date: metaPayload.published_date,
                site_name: metaPayload.site_name
            },
            webpage_content: {
                full_text: fullText,
                raw_meta_tags: metaPayload.raw_meta_tags,
                structured_data: metaPayload.structured_data,
                og_tags: metaPayload.og_tags
            }
        };
    } catch (error) {
        console.error("Failed to gather webpage data", error);
        return {
            page_metadata: {},
            webpage_content: {
                full_text: '',
                raw_meta_tags: {},
                structured_data: [],
                og_tags: { title: '', image: '', type: '' }
            }
        };
    }
}

async function getGeoData(): Promise<GeoData> {
    return new Promise((resolve) => {
        if (!navigator.geolocation) {
            resolve(getDefaultGeo());
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (pos) => {
                resolve({
                    country: 'Unknown',
                    city: 'Unknown',
                    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                    timezone_offset: new Date().getTimezoneOffset(),
                    coordinates: {
                        lat: pos.coords.latitude,
                        lon: pos.coords.longitude,
                        accuracy: pos.coords.accuracy
                    }
                });
            },
            () => resolve(getDefaultGeo()),
            { timeout: 5000 }
        );
    });
}

function getDefaultGeo(): GeoData {
    return {
        country: 'Unknown',
        city: 'Unknown',
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        timezone_offset: new Date().getTimezoneOffset(),
        coordinates: { lat: 0, lon: 0, accuracy: 0 }
    };
}

async function getNetworkContext(): Promise<NetworkContext> {
    const conn = (navigator as any).connection;
    return {
        ip_address: '0.0.0.0',
        connection_type: conn ? conn.effectiveType : 'unknown',
        is_vpn_detected: false
    };
}
