from tools.llm import llm
from graph.state import ResearchState


def writer_agent(state: ResearchState) -> dict:
    """
    Writes (or rewrites) a structured professional report.
    On revision loops, includes previous human feedback.
    """
    revision = state.get("revision_count", 0)
    print(f"\n[Writer] {'Revising' if revision > 0 else 'Writing'} report (revision #{revision})...")

    insights_text = "\n\n".join(
        f"### {task}\n{insight}"
        for task, insight in state["analyzed_insights"].items()
    )

    # Build source list for citations
    all_sources = []
    for task, urls in state.get("sources", {}).items():
        all_sources.extend(urls)
    sources_text = "\n".join(f"- {u}" for u in sorted(set(all_sources)))

    # Include previous feedback if this is a revision
    feedback_section = ""
    if revision > 0 and state.get("human_feedback"):
        feedback_section = f"""
IMPORTANT: The human reviewer rejected the previous draft with this feedback:
\"\"\"{state['human_feedback']}\"\"\"
Address these concerns in your revision.
"""

    prompt = f"""Write a professional research report on the topic below.
{feedback_section}
Topic: {state['topic']}

Research Insights:
{insights_text}

Sources:
{sources_text}

Structure the report with these sections:
1. Executive Summary
2. Key Findings (with specific data points)
3. Analysis
4. Risks & Challenges
5. Recommendations
6. Conclusion
7. References (list all source URLs)

Be factual, specific, and cite sources inline where relevant."""

    report = llm.invoke(prompt).content
    print("[Writer] Draft report generated.")
    return {
        "draft_report": report,
        "revision_count": revision + 1
    }