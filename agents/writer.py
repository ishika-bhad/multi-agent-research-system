import re

from tools.llm import llm
from graph.state import ResearchState


def writer_agent(state: ResearchState) -> dict:
    """
    Writes report section-by-section.
    This gives progressive updates instead of one huge generation.
    """

    revision = state.get("revision_count", 0)

    print(
        f"\n[Writer] "
        f"{'Revising' if revision > 0 else 'Writing'} "
        f"report (revision #{revision})..."
    )

    insights_text = "\n\n".join(
        f"### {task}\n{insight}"
        for task, insight in state["analyzed_insights"].items()
    )

    all_sources = []
    for task, urls in state.get("sources", {}).items():
        all_sources.extend(urls)

    sources_text = "\n".join(
        f"- {u}"
        for u in sorted(set(all_sources))
    )

    feedback_section = ""

    if revision > 0 and state.get("human_feedback"):
        feedback_section = f"""
IMPORTANT: The human reviewer rejected the previous draft.

Feedback:
{state['human_feedback']}

Address all concerns.
"""

    sections = [
        "Executive Summary",
        "Key Findings",
        "Analysis",
        "Risks & Challenges",
        "Recommendations",
        "Conclusion"
    ]

    report_parts = []

    base_context = f"""
{feedback_section}

Topic:
{state['topic']}

Research Insights:
{insights_text}

Sources:
{sources_text}
"""

    for section in sections:

        print(f"[Writer] Generating: {section}")

        prompt = f"""
Write ONLY the "{section}" section of a professional research report.

{base_context}

Requirements:
- Be factual
- Use data where available
- Do not repeat previous sections
- Use markdown formatting
- Do NOT include a title or heading for this section (no "# {section}",
  no "## {section}", etc). The heading is added separately — start your
  response directly with the body content.
"""

        section_content = llm.invoke(
            prompt
        ).content.strip()

        # FIX: even when told not to, the model sometimes still echoes the
        # section title back as its own heading line (e.g. "# Executive
        # Summary"). Since we always prepend our own "# {section}" heading
        # below, that produced a duplicated heading in the final report.
        # Defensively strip a leading heading line if it matches this
        # section's title.
        first_line, _, rest = section_content.partition("\n")
        if re.match(rf"^#{{1,3}}\s*{re.escape(section)}\s*$", first_line.strip(), re.IGNORECASE):
            section_content = rest.lstrip("\n")

        report_parts.append(
            f"# {section}\n\n{section_content}"
        )

    references = "# References\n\n" + "\n".join(
        f"- {u}"
        for u in sorted(set(all_sources))
    )

    report_parts.append(references)

    report = "\n\n".join(report_parts)

    print("[Writer] Draft report generated.")

    return {
        "draft_report": report,
        "revision_count": revision + 1
    }