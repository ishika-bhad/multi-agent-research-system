"""
main.py — CLI runner for the Multi-Agent Research & Report System.

FIX: the original only handled ONE approval cycle.  If the user rejected
and the writer re-ran, the graph would pause at human_gate a second time
but main.py had already moved past the input() call → graph hung forever.

This version loops until the graph reaches END.
"""

import uuid
from graph.workflow import graph
from langgraph.types import Command

THREAD_CONFIG = {
    "configurable": {
        # Use a fresh thread ID each run so MemorySaver never replays old state.
        "thread_id": str(uuid.uuid4()),
    }
}


def _is_waiting_for_human(config: dict) -> bool:
    """Returns True when the graph is paused at the human_gate interrupt."""
    snapshot = graph.get_state(config)
    return bool(snapshot.next) and "human_gate" in snapshot.next


def _show_draft(config: dict) -> None:
    """Prints the current draft + fact-check report so the user can review."""
    state = graph.get_state(config).values
    draft = state.get("draft_report", "")
    fact  = state.get("fact_check_report", "")

    print("\n" + "=" * 60)
    print("DRAFT REPORT")
    print("=" * 60)
    print(draft or "(no draft)")
    if fact:
        print("\n" + "=" * 60)
        print("FACT-CHECK REPORT")
        print("=" * 60)
        print(fact)
    print("=" * 60 + "\n")


def main():
    topic = input("Enter research topic: ").strip()
    if not topic:
        print("No topic provided — exiting.")
        return

    # ── First run: orchestrator → research → analyzer → writer →
    #              fact_checker → human_gate (pauses here)
    print("\nStarting research pipeline …\n")
    graph.invoke({"topic": topic, "rejection_count": 0}, config=THREAD_CONFIG)

    # ── Approval loop ──────────────────────────────────────────────────────────
    cycle = 0
    while _is_waiting_for_human(THREAD_CONFIG):
        cycle += 1
        _show_draft(THREAD_CONFIG)

        print(f"Review cycle #{cycle}")
        print('  Type "approve"              to finalise.')
        print('  Type "reject: <feedback>"   to request revisions.')
        decision = input("Your decision: ").strip()

        if not decision:
            print("Empty input — please type approve or reject.")
            continue

        # Resume the graph with the user's decision.
        # LangGraph will run: human_gate → (finalizer | writer → fact_checker → human_gate)
        graph.invoke(Command(resume=decision), config=THREAD_CONFIG)

    # ── Done ───────────────────────────────────────────────────────────────────
    final_state = graph.get_state(THREAD_CONFIG).values
    final_report = final_state.get("final_report", "")

    print("\n" + "=" * 60)
    print("FINAL REPORT")
    print("=" * 60)
    print(final_report)


if __name__ == "__main__":
    main()