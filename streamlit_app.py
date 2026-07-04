"""
streamlit_app.py — Streamlit UI for the Multi-Agent Research & Report System.

Fixes applied
─────────────
1. human_gate detection: with stream_mode="updates" the graph pauses *before*
   emitting a human_gate update, so `elif node_name == "human_gate"` never fires.
   Fixed by checking graph.get_state() after streaming ends.

2. Multi-cycle approval: original only handled one approve/reject round.
   Now the UI re-enters the review section after every revision so the user
   can keep reviewing until they approve or the 3-rejection cap is hit.

3. Draft re-display on rejection: after a revision the new draft is streamed
   and shown before the review controls reappear.

4. Thread ID: use a per-session UUID so each browser tab gets its own graph run.
"""

import uuid
import streamlit as st
from langgraph.types import Command
from graph.workflow import graph
from export_utils import to_pdf

st.set_page_config(page_title="Multi-Agent Research System", layout="wide")
st.title("🔍 Multi-Agent Research & Report System")


# ── Session state initialisation ───────────────────────────────────────────────

def _init():
    defaults = {
        "thread_config": {"configurable": {"thread_id": str(uuid.uuid4())}},
        "waiting_for_approval": False,
        "draft_report": "",
        "fact_check_report": "",
        "final_report": "",
        "pipeline_started": False,
        "rejection_count": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()


# ── Helper: stream the graph until it pauses or finishes ──────────────────────

def _stream_until_interrupt(initial_input: dict | None, resume_command=None):
    """
    Streams graph events into the UI.
    Pass `initial_input` for the first run, `resume_command` for resumptions.
    Returns True if the graph is now waiting at human_gate, False if done.
    """
    progress_placeholder = st.empty()
    status_lines: list[str] = []

    stream_input = initial_input if initial_input else resume_command

    for event in graph.stream(
        stream_input,
        config=st.session_state.thread_config,
        stream_mode="updates",
    ):
        for node_name, node_output in event.items():
            if node_name == "__interrupt__":
                # Graph paused — stop streaming, handle below
                break

            status_lines.append(f"✅ {node_name} completed")
            progress_placeholder.code("\n".join(status_lines))

            if node_name == "writer":
                draft = node_output.get("draft_report", "")
                if draft:
                    st.session_state.draft_report = draft

            elif node_name == "fact_checker":
                fact = node_output.get("fact_check_report", "")
                if fact:
                    st.session_state.fact_check_report = fact

            elif node_name == "finalizer":
                final = node_output.get("final_report", "")
                if final:
                    st.session_state.final_report = final

    # FIX: check graph state *after* streaming to detect the interrupt
    snapshot = graph.get_state(st.session_state.thread_config)
    is_waiting = bool(snapshot.next) and "human_gate" in snapshot.next
    return is_waiting


# ── Topic input ────────────────────────────────────────────────────────────────

if not st.session_state.pipeline_started:
    topic = st.text_area(
        "Enter your research question",
        placeholder="E.g. What are the latest trends in AI agents?",
    )

    if st.button("Generate Report") and topic.strip():
        st.session_state.pipeline_started = True
        with st.spinner("Running multi-agent pipeline …"):
            waiting = _stream_until_interrupt(
                initial_input={"topic": topic.strip(), "rejection_count": 0}
            )
        st.session_state.waiting_for_approval = waiting
        if not waiting:
            # Finished without needing human review (shouldn't happen, but safe)
            st.success("Pipeline complete.")
        st.rerun()


# ── Show current draft ─────────────────────────────────────────────────────────

if st.session_state.draft_report:
    st.subheader("📄 Draft Report")
    st.markdown(st.session_state.draft_report)

if st.session_state.fact_check_report:
    with st.expander("🔍 Fact-Check Report", expanded=False):
        st.text(st.session_state.fact_check_report)


# ── Human review section ───────────────────────────────────────────────────────

if st.session_state.waiting_for_approval:
    rejection_count = st.session_state.rejection_count
    max_rejections = 3

    st.divider()
    st.subheader("🧑‍⚖️ Human Review")

    if rejection_count > 0:
        st.info(f"Revision {rejection_count}/{max_rejections} — please review the updated draft above.")

    decision = st.radio("Decision", ["Approve", "Reject"], key=f"decision_{rejection_count}")

    feedback = ""
    if decision == "Reject":
        remaining = max_rejections - rejection_count
        feedback = st.text_area(
            f"Revision feedback (you have {remaining} revision(s) left)",
            key=f"feedback_{rejection_count}",
        )

    if st.button("Submit Review", key=f"submit_{rejection_count}"):
        review_text = (
            "approve"
            if decision == "Approve"
            else f"reject: {feedback or 'Please revise.'}"
        )

        if decision == "Reject":
            st.session_state.rejection_count += 1

        with st.spinner("Processing review …"):
            waiting = _stream_until_interrupt(
                initial_input=None,
                resume_command=Command(resume=review_text),
            )

        st.session_state.waiting_for_approval = waiting
        st.rerun()


# ── Final report ───────────────────────────────────────────────────────────────

if st.session_state.final_report:
    st.divider()
    st.subheader("✅ Final Report")
    st.markdown(st.session_state.final_report)

    # ── Export options ────────────────────────────────────────────────────────
    st.divider()
    st.subheader("⬇️ Download Report")

    # Regenerate only when the report content actually changes (keyed off a
    # hash of it), so repeated reruns don't re-run PDF generation for nothing.
    report_key = hash(st.session_state.final_report)
    if st.session_state.get("export_report_key") != report_key:
        with st.spinner("Preparing PDF …"):
            try:
                st.session_state.pdf_bytes = to_pdf(st.session_state.final_report)
            except Exception as e:
                st.error(f"PDF generation failed: {e}")
                st.session_state.pdf_bytes = None
        st.session_state.export_report_key = report_key

    if st.session_state.get("pdf_bytes"):
        st.download_button(
            label="⬇️ Download PDF",
            data=st.session_state.pdf_bytes,
            file_name="research_report.pdf",
            mime="application/pdf",
            key="download_pdf_btn",
        )
    else:
        st.warning("PDF isn't available — see the error above.")

    # ── New research ──────────────────────────────────────────────────────────
    if st.button("🔄 Start New Research"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()