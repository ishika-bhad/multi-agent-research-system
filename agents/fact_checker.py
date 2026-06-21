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
    extract_prompt = f"""Extract all specific factual claims from the report below.
A claim is a specific statement of fact (statistics, dates, comparisons, causal statements).
Return ONLY a JSON array of claim strings. No markdown fences.

Report:
{state['draft_report'][:6000]}

Claims JSON array:"""

    raw_claims = llm.invoke(extract_prompt).content.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_claims, flags=re.DOTALL).strip()
    match = re.search(r'\[.*\]', cleaned, re.DOTALL)
    claims = json.loads(match.group()) if match else []
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
{all_sources_text[:5000]}

Respond with exactly one of:
- VERIFIED: (if the claim is clearly supported by sources)
- UNVERIFIED: (if sources don't mention it but it's not contradicted)
- FALSE: (if sources directly contradict this claim)

Then give a one-line reason.
Format: VERDICT: reason"""
        result = llm.invoke(verify_prompt).content.strip()
        return claim, result

    # Run verifications in parallel
    claim_verdicts = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_verify_claim, c): c for c in claims[:15]}  # cap at 15 claims
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