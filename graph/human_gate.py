from langgraph.types import interrupt


def human_approval_gate(state):

    human_input = interrupt(
        "approve or reject"
    )

    decision = str(
        human_input
    ).strip().lower()

    approved = decision.startswith(
        "approve"
    )

    feedback = (
        "Approved"
        if approved
        else decision.replace(
            "reject:",
            ""
        ).strip()
    )

    return {
        "approved": approved,
        "human_feedback": feedback
    }


def route_after_human(state):

    if state.get("approved"):
        return "finalize"

    if (
        state.get(
            "revision_count",
            0
        ) >= 3
    ):
        return "finalize"

    return "revise"