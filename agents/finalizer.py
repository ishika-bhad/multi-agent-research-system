from graph.state import ResearchState


def finalizer_agent(state: ResearchState) -> dict:
    """
    Assembles the final deliverable from the approved draft + fact-check report.

    FIX: the original f-string had a literal newline inside the expression
         `state.get("revision_count", 1)` which is a SyntaxError in Python < 3.12
         and produces garbled output in all versions.
    """
    # revision_count is how many times the writer ran; rejections are tracked
    # separately in rejection_count.  Show whichever gives useful context.
    rejection_count = state.get("rejection_count", 0)
    revision_label = (
        "no revisions — approved on first review"
        if rejection_count == 0
        else f"{rejection_count} revision(s)"
    )

    final = (
        f"{state['draft_report']}\n\n"
        f"{'=' * 50}\n"
        f"FACT-CHECK REPORT\n"
        f"{'=' * 50}\n\n"
        f"{state.get('fact_check_report', 'N/A')}\n\n"
        f"{'=' * 50}\n"
        f"Approved after {revision_label}.\n"
    )

    return {"final_report": final}