from langgraph.types import interrupt
from graph.state import ResearchState


def human_approval_gate(state: ResearchState) -> dict:
    """
    Pauses the graph and waits for the user to approve or reject the draft.

    To resume, call:
        graph.invoke(Command(resume="approve"), config=config)
        graph.invoke(Command(resume="reject: please add citations"), config=config)
    """
    human_input: str = interrupt("approve or reject")

    decision = str(human_input).strip().lower()
    approved = decision.startswith("approve")

    feedback = (
        "Approved"
        if approved
        else decision.replace("reject:", "").strip() or "Please revise."
    )

    # Increment rejection_count only on rejection so it stays independent
    # of writer's revision_count.
    rejection_count = state.get("rejection_count", 0)
    if not approved:
        rejection_count += 1

    return {
        "approved": approved,
        "human_feedback": feedback,
        "rejection_count": rejection_count,
    }


def route_after_human(state: ResearchState) -> str:
    """
    FIX: was returning "finalize" but the edge map key is "finalizer".
    Also now uses rejection_count (not revision_count) for the cap check.
    """
    if state.get("approved"):
        return "finalizer"                          # ← was "finalize" (KeyError)

    if state.get("rejection_count", 0) >= 3:
        return "finalizer"                          # ← was "finalize" (KeyError)

    return "revise"