import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from tools.llm import llm

from graph.state import ResearchState


def fact_checker_agent(state: ResearchState) -> dict:
    """
    1. Extracts individual factual claims from the draft report.
    2. Verifies each claim against the raw research sources.
    3. Returns a verdict for every claim: VERIFIED / UNVERIFIED / FALSE.
    """
    print("\n[FactChecker] Extracting claims from draft report...")

    # Step 1: Extract claims
    # FIX: the draft was hard-truncated to the first 6000 chars before
    # extraction, so claims made later in the report (Analysis, Risks,
    # Recommendations, Conclusion, etc.) were never even seen, let alone
    # checked. Chunk the full draft instead of slicing it away.
    def _chunks(text: str, size: int = 6000) -> list[str]:
        return [text[i:i + size] for i in range(0, len(text), size)] or [""]

    def _extract_claims(chunk: str) -> list[str]:
        extract_prompt = f"""Extract all specific factual claims from the report excerpt below.
A claim is a specific statement of fact (statistics, dates, comparisons, causal statements).
Return ONLY a JSON array of claim strings. No markdown fences. If there are no
factual claims in this excerpt, return an empty array [].

Report excerpt:
{chunk}

Claims JSON array:"""
        raw = llm.invoke(extract_prompt).content.strip()
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.DOTALL).strip()
        match = re.search(r'\[.*\]', cleaned, re.DOTALL)
        return json.loads(match.group()) if match else []

    claims: list[str] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(_extract_claims, c) for c in _chunks(state["draft_report"])]
        for future in as_completed(futures):
            claims.extend(future.result())

    # de-duplicate while preserving order
    seen = set()
    deduped_claims = []
    for c in claims:
        if c not in seen:
            seen.add(c)
            deduped_claims.append(c)
    claims = deduped_claims

    print(f"[FactChecker] Found {len(claims)} claims to verify.")

    # Step 2: Verify each claim against raw research
    all_sources_text = "\n\n".join(
        f"[{task}]:\n{content[:2000]}"
        for task, content in state["raw_research"].items()
    )

    def _verify_claim(claim: str) -> tuple:
        verify_prompt = f"""You are a fact-checker. Verify whether the following claim is
supported by the research sources provided.

Claim: {claim}

Sources:
{all_sources_text}

Respond with exactly one of:
- VERIFIED: (if the claim is clearly supported by sources)
- UNVERIFIED: (if sources don't mention it but it's not contradicted)
- FALSE: (if sources directly contradict this claim)

Then give a one-line reason.
Format: VERDICT: reason"""
        result = llm.invoke(verify_prompt).content.strip()
        return claim, result

    # Run verifications in parallel
    # FIX: previously capped at claims[:15], so any claims beyond the 15th
    # were silently never verified at all (not even marked UNVERIFIED — just
    # dropped). Now every extracted claim is checked. Also dropped the
    # [:5000] slice on the sources so verification isn't working off a
    # partial view of the research.
    claim_verdicts = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_verify_claim, c): c for c in claims}
        for future in as_completed(futures):
            claim, verdict = future.result()
            claim_verdicts[claim] = verdict

    # Step 3: Build summary report
    verified   = [c for c, v in claim_verdicts.items() if v.upper().startswith("VERIFIED")]
    unverified = [c for c, v in claim_verdicts.items() if v.upper().startswith("UNVERIFIED")]
    false_     = [c for c, v in claim_verdicts.items() if v.upper().startswith("FALSE")]

    fact_check_report = f"""FACT-CHECK REPORT
{'='*50}
Total claims: {len(claims)}
✅ Verified  : {len(verified)}
⚠️  Unverified: {len(unverified)}
❌ False     : {len(false_)}

{'='*50}
VERDICTS:
"""
    for claim, verdict in claim_verdicts.items():
        icon = "✅" if verdict.upper().startswith("VERIFIED") else \
               "❌" if verdict.upper().startswith("FALSE") else "⚠️"
        fact_check_report += f"{icon} {claim}\n   → {verdict}\n\n"

    # Pass only if no FALSE claims
    passed = len(false_) == 0
    print(f"[FactChecker] ✅ {len(verified)} verified | ⚠️ {len(unverified)} unverified | ❌ {len(false_)} false")
    print(f"[FactChecker] Passed: {passed}")

    return {
        "claims": claims,
        "claim_verdicts": claim_verdicts,
        "fact_check_report": fact_check_report,
        "fact_check_passed": passed
    }