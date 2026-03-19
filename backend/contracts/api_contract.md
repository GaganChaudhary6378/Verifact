# **API Contract Specification: Agentic Truth Checker (WebSocket Edition)**

This document defines the real-time communication protocol for the AI League #1 Hackathon, connecting the Chrome Extension (Frontend) to the FastAPI Agentic RAG Backend.

---

## **1. Data Collection Categories (The "Whereabouts" Spectrum)**

To provide "Definitive" verification, the extension gathers the following data points to populate the `source_context`:

| Category | Data Point | Technical Source | Accuracy |
| :--- | :--- | :--- | :--- |
| **Explicit** | Precise Coordinates | `navigator.geolocation` (GPS/Wi-Fi) | < 50m |
| **Network** | Public IP Address | Backend-detected or WebRTC leakage | City/Region |
| **System** | Timezone & Offset | `Intl.DateTimeFormat().resolvedOptions()` | Regional |
| **Locale** | Browser Language | `navigator.language` | Country-level |
| **Webpage** | Full DOM/Meta Data | `document.documentElement.outerHTML` | Page-specific |
| **Semantic** | JSON-LD / Microdata | `document.querySelectorAll('script[type="application/ld+json"]')` | High (Structured) |

---

## **2. WebSocket Connection**

**Endpoint:** `ws://<backend-url>/api/v1/ws/verify/{user_id}`

### **A. Initial Request (Enriched Context)**
Sent immediately after the user triggers "Verify Claim".

```json
{
  "action": "START_VERIFICATION",
  "payload": {
    "claim_text": "string",
    "source_context": {
      "page_metadata": {
        "url": "string",
        "page_title": "string",
        "selected_at": "ISO8601",
        "language": "en-US",
        "description": "string", 
        "author": "string",      
        "published_date": "string",
        "site_name": "string"    
      },
      "webpage_content": {
        "full_text": "string",   
        "raw_meta_tags": {},     
        "structured_data": [],   
        "og_tags": {             
          "title": "string",
          "image": "string",
          "type": "string"
        }
      },
      "geo_data": {
        "country": "string",
        "city": "string",
        "timezone": "string",
        "timezone_offset": -480,
        "coordinates": { 
          "lat": 0.0, 
          "lon": 0.0,
          "accuracy": 15.0 
        }
      },
      "network_context": {
        "ip_address": "string",
        "connection_type": "4g | wifi",
        "is_vpn_detected": false
      },
      "browser_info": {
        "user_agent": "string",
        "platform": "string",
        "screen_resolution": "1920x1080"
      },
      "search_stack": {
        "preferred_engine": "google | bing | duckduckgo",
        "safe_search": true
      }
    }
  }
}
```

### **B. Progress Stream (Backend → Frontend)**
The Agentic loop uses the page content to detect bias or satirical context (e.g., "Analyzing page tone: Satirical detected").

```json
{
  "type": "AGENT_STEP",
  "payload": {
    "step_id": 1,
    "label": "Semantic Parsing",
    "detail": "Analyzing structured JSON-LD data from [Source_Domain] to verify authorship.",
    "timestamp": "ISO8601"
  }
}
```

### **C. Final Response (Backend → Frontend)**

```json
{
  "type": "FINAL_VERDICT",
  "payload": {
    "request_id": "uuid",
    "verdict": "TRUE | FALSE | MISLEADING | NOT ENOUGH EVIDENCE",
    "confidence_score": 0.98,
    "reasoning_summary": "Verification logic processed through localized RAG and page context analysis...",
    "citations": [
      {
        "source_name": "string",
        "url": "string",
        "relevance_snippet": "string",
        "trust_score": 0.95
      }
    ]
  }
}
```

---

## **3. Implementation Details for Data Capture**

1.  **Meta & OG Tags**: Iterate through `document.getElementsByTagName('meta')` to extract property (for OG) and name attributes.
2.  **Structured Data**: Use `JSON.parse()` on any `<script type="application/ld+json">` content to give the RAG agent machine-readable context about the article (e.g., `datePublished`, `factCheckBy`).
3.  **Full Text**: Use a library like `Readability.js` (common in extensions) or simply `document.body.innerText` (cleaned) to provide the "rest of the article" to the RAG backend for better chunking and retrieval.
