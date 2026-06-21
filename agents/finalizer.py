def finalizer_agent(state):

    final = f"""
{state["draft_report"]}

==================================================
FACT CHECK REPORT
==================================================

{state["fact_check_report"]}

==================================================
Approved after
{state.get("revision_count",1)}
revision(s)
"""

    return {
        "final_report": final
    }