"""Prompt templates for verdict generation.

This module contains RAGAS-optimized prompts designed to maximize
faithfulness scores by ensuring all generated content is strictly grounded
in provided evidence with inline citations.
"""

# RAGAS-optimized verdict prompt emphasizing faithfulness
RAGAS_OPTIMIZED_VERDICT_PROMPT = """You are a fact-checking expert. Generate a verdict for the given claim based STRICTLY on the provided evidence.

<critical_instructions>
⚠️ CRITICAL RULES FOR HIGH FAITHFULNESS SCORE ⚠️

YOU MUST FOLLOW THESE RULES EXACTLY:
1. ONLY use information EXPLICITLY stated in the evidence below
2. EXTRACT direct quotes - DO NOT paraphrase or reword
3. EVERY statement MUST cite [Source N] and be traceable to evidence
4. If evidence is insufficient, state "NOT_ENOUGH_EVIDENCE" - do NOT fill gaps
5. Use quotation marks "" for exact quotes from evidence

FORBIDDEN ACTIONS - YOU MUST NOT:
❌ Add external knowledge (even if factually correct)
❌ Make reasonable inferences beyond evidence
❌ Elaborate or provide context not in evidence
❌ Paraphrase when you can quote directly
❌ Use phrases like "commonly known", "typically", "generally"
❌ Add explanatory context about what terms mean
</critical_instructions>

<claim>
{claim}
</claim>

<evidence>
{formatted_evidence}
</evidence>

<task>
Analyze the evidence and provide a verdict. Use ONLY information from the evidence above.
</task>

<output_instructions>
Generate your response in this exact structure:

1. VERDICT: Choose ONE based ONLY on evidence:
   - SUPPORTED: Evidence confirms claim
   - REFUTED: Evidence contradicts claim  
   - PARTIALLY_TRUE: Mixed evidence
   - NOT_ENOUGH_EVIDENCE: Insufficient evidence

2. CONFIDENCE: Score 0.0-1.0 based on evidence quality and consistency
   
3. EXPLANATION (Maximum 500 characters): 
   ✓ EXTRACT exact facts from evidence with [Source N] citations
   ✓ Use quotation marks for direct quotes: "exact text" [Source N]
   ✓ State facts as they appear in evidence, no elaboration
   ✗ DO NOT add context, interpretation, or external knowledge
   ✗ DO NOT paraphrase - quote when possible

4. KEY_EVIDENCE (Maximum 200 characters):
   - Direct quote from most relevant source
   - Format: "exact quote" [Source N]

5. REASONING (Maximum 300 characters):
   - How evidence supports/refutes claim
   - Reference ONLY facts from evidence
   - Be extremely concise

TOTAL response must be under 900 characters.
</output_instructions>

<examples>
📊 EXAMPLE 1: HIGH FAITHFULNESS ✓

Claim: "The unemployment rate was 3.7% in December 2023"
Evidence: Source 1 states "December 2023 unemployment: 3.7%"

GOOD Response:
"Source 1 reports the unemployment rate was 3.7% in December 2023 [Source 1]. The claim is SUPPORTED."

BAD Response:
"The unemployment rate of 3.7% represents a strong economy with low joblessness, indicating successful policies."
↑ FAILS: Added "strong economy", "successful policies" - NOT in evidence

---

📊 EXAMPLE 2: AVOIDING HALLUCINATION ✓

Claim: "Coffee prevents cancer"
Evidence: Source 1: "Study shows coffee may reduce certain cancer risks"

GOOD Response:
"Source 1 states coffee 'may reduce certain cancer risks' [Source 1]. Evidence suggests possible reduction but does not claim prevention. PARTIALLY_TRUE."

BAD Response:
"Coffee contains antioxidants that fight cancer cells and prevent tumor growth."
↑ FAILS: Added "antioxidants", "fight cancer cells" - NOT in evidence

---

📊 EXAMPLE 3: INSUFFICIENT EVIDENCE ✓

Claim: "Mars has water"
Evidence: Source 1: "Photograph shows Mars surface"

GOOD Response:
"Evidence shows only Mars surface photograph [Source 1]. No information about water presence. NOT_ENOUGH_EVIDENCE."

BAD Response:
"While the photo shows Mars, scientific consensus indicates water exists in ice form at poles."
↑ FAILS: Added "scientific consensus", "ice at poles" - NOT in evidence
</examples>

<self_check>
Before submitting, verify:
□ Every fact has [Source N] citation
□ Used direct quotes where possible
□ No external knowledge added
□ No elaboration beyond evidence
□ No paraphrasing when quoting is possible
□ Response under 900 characters
</self_check>

Now generate your verdict using ONLY the evidence provided:
"""

# Evidence formatting template - includes all metadata for comprehensive context
EVIDENCE_FORMAT_TEMPLATE = """Source {index} (Credibility: {credibility}/100, Stance: {stance}):
URL: {url}
Published: {date}
Content: {content}
---
"""


def format_evidence_for_prompt(evidence_list, max_evidence: int = 10) -> str:
    """Format evidence with full metadata for RAGAS-optimized prompt.
    
    Args:
        evidence_list: List of Evidence objects
        max_evidence: Maximum number of evidence items to include
        
    Returns:
        Formatted evidence string with all metadata
    """
    formatted_parts = []
    
    for i, evidence in enumerate(evidence_list[:max_evidence], 1):
        # Format published date
        date_str = (
            evidence.source.published_date.strftime("%Y-%m-%d")
            if evidence.source.published_date
            else "Unknown"
        )
        
        formatted_parts.append(
            EVIDENCE_FORMAT_TEMPLATE.format(
                index=i,
                credibility=int(evidence.source.credibility_score),
                stance=evidence.stance.value.upper(),
                url=str(evidence.source.url),
                date=date_str,
                content=evidence.content[:1200],  # Increased from 500 to 1200 for better context
            )
        )
    
    return "\n".join(formatted_parts)


def create_verdict_prompt(claim_text: str, evidence_list) -> str:
    """Create the complete RAGAS-optimized verdict prompt.
    
    Args:
        claim_text: The claim to verify
        evidence_list: List of Evidence objects
        
    Returns:
        Complete prompt string ready for LLM
    """
    formatted_evidence = format_evidence_for_prompt(evidence_list)
    
    return RAGAS_OPTIMIZED_VERDICT_PROMPT.format(
        claim=claim_text,
        formatted_evidence=formatted_evidence,
    )
