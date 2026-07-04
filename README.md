# 🔍 Multi-Agent Research & Report System

An automated research pipeline that takes a single research question, decomposes it, searches the web, analyzes findings, writes a full report, fact-checks its own claims, pauses for human review, and exports the approved result as a PDF — all orchestrated as a LangGraph state machine with a Streamlit front end.

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the App](#running-the-app)
- [Usage Walkthrough](#usage-walkthrough)
- [The Human Review Loop](#the-human-review-loop)
- [Exporting the Report](#exporting-the-report)
- [Troubleshooting](#troubleshooting)
- [Known Limitations](#known-limitations)

---

## Overview

Given a topic like *"What are the latest trends in AI agents?"*, the system runs six specialized agents in sequence:

| Agent | Role |
|---|---|
| **Orchestrator** | Breaks the topic into 4–6 focused sub-questions |
| **Researcher** | Searches the web for each sub-question in parallel (via Tavily) |
| **Analyst** | Summarizes raw research into concrete, factual insights per sub-question |
| **Writer** | Drafts a full report section-by-section (Executive Summary → Conclusion) |
| **Fact-Checker** | Extracts every factual claim from the draft and verifies it against the raw sources |
| **Human Gate** | Pauses the pipeline and waits for a human to approve or reject the draft |
| **Finalizer** | Assembles the approved draft + fact-check report into the final deliverable |

The result can then be downloaded as a formatted PDF directly from the browser.

---

## How It Works

The pipeline is a [LangGraph](https://langchain-ai.github.io/langgraph/) `StateGraph` with a built-in interrupt for human-in-the-loop review:

```
START
  │
  ▼
orchestrator ──► research ──► analyzer ──► writer ──► fact_checker ──► human_gate
                                              ▲                            │
                                              │                            ├── approved ──► finalizer ──► END
                                              └────────── rejected ────────┘
                                                     (up to 3 revisions)
```

- **State** (`graph/state.py`) is a single `TypedDict` (`ResearchState`) that flows through every node — subtasks, raw research, insights, the draft, fact-check verdicts, human feedback, and the final report all live here.
- **Checkpointing**: the graph uses an in-memory checkpointer (`MemorySaver`), so each browser session/thread can pause at the human review step and resume later without losing state.
- **Human-in-the-loop**: `human_gate.py` uses LangGraph's `interrupt()` to pause execution until the UI sends back an `approve` or `reject: <feedback>` command. Rejections route back to the **writer**, which regenerates the draft using the human's feedback, and the cycle repeats — capped at 3 revisions, after which the report is finalized regardless.

---

## Project Structure

```
.
├── streamlit_app.py        # Streamlit UI — drives the graph, shows progress, handles review & export
├── export_utils.py         # Converts the final Markdown report into a downloadable PDF
├── graph/
│   ├── workflow.py         # Builds and compiles the LangGraph StateGraph
│   ├── state.py            # ResearchState TypedDict — the shared state schema
│   └── human_gate.py       # Human-in-the-loop approval node + routing logic
├── agents/
│   ├── orchestrator.py     # Decomposes the topic into sub-questions
│   ├── researcher.py       # Parallel web search per sub-question
│   ├── analyst.py          # Summarizes raw research into insights
│   ├── writer.py           # Drafts the report section-by-section
│   ├── fact_checker.py     # Extracts and verifies factual claims
│   └── finalizer.py        # Assembles the final deliverable
├── tools/
│   ├── llm.py               # Shared ChatAnthropic (Claude) client
│   ├── tavily_search.py     # Tavily search tool configuration
│   └── scraper.py           # Helper for combining search results into text
└── .env                     # API keys (not committed — see Configuration)
```

---

## Prerequisites

- **Python 3.10+**
- An **Anthropic API key** ([console.anthropic.com](https://console.anthropic.com))
- A **Tavily API key** ([tavily.com](https://tavily.com)) for web search

> PDF export uses [reportlab](https://pypi.org/project/reportlab/), a pure-Python library — no external binaries or Node.js required.

---

## Installation

1. **Clone the project** and move into it:

   ```bash
   git clone https://github.com/ishika-bhad/multi-agent-research-system
   cd multi-agent-research-system
   ```

2. **Create a virtual environment** (recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate      # macOS/Linux
   venv\Scripts\activate         # Windows
   ```

3. **Install dependencies**:

   ```bash
   pip install streamlit langgraph langchain-anthropic langchain-tavily python-dotenv reportlab
   ```

   Or, if you maintain a `requirements.txt`:

   ```txt
   streamlit
   langgraph
   langchain-anthropic
   langchain-tavily
   python-dotenv
   reportlab
   ```

   ```bash
   pip install -r requirements.txt
   ```

---

## Configuration

Create a `.env` file in the project root with your API keys:

```env
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
```

These are loaded by `tools/llm.py` and `tools/tavily_search.py` respectively via `python-dotenv`. Never commit this file — add it to `.gitignore`.

---

## Running the App

From the project root:

```bash
streamlit run streamlit_app.py
```

Streamlit will open the app in your browser (default: `http://localhost:8501`).

---

## Usage Walkthrough

1. **Enter a research question** in the text box (e.g. *"What is the current state of quantum computing commercialization?"*) and click **Generate Report**.
2. The pipeline runs automatically through orchestration, research, analysis, writing, and fact-checking. Progress is shown live as each agent completes.
3. Once the draft and its fact-check report are ready, the pipeline **pauses** and presents the **Human Review** section.
4. **Approve** the draft, or **Reject** it with written feedback — the writer will revise the report accordingly and the fact-checker will re-verify it. This can repeat up to 3 times.
5. Once approved (or the revision cap is hit), the **Final Report** is displayed along with a **Download PDF** button.
6. Click **Start New Research** at any time to reset and begin a new topic.

---

## The Human Review Loop

- Every rejection increments a `rejection_count` in the shared state (independent from the writer's internal `revision_count`).
- Feedback you provide is passed directly into the writer's next prompt so it can target the specific concerns you raised.
- After **3 rejections**, the pipeline automatically finalizes the current draft regardless of approval status, to prevent infinite revision loops.
- Each browser tab gets its own session (`thread_id`), so multiple people can run independent research sessions against the same running app.

---

## Exporting the Report

The final report (draft + fact-check summary) is rendered into a styled PDF using `reportlab`:

- Headings, bullet points, and inline **bold**/*italic* markdown are preserved.
- The PDF is generated once per finished report and cached for the session — clicking Download again won't regenerate it unless the underlying report changes.

---

## Troubleshooting

**`PDF generation failed: No module named 'reportlab'`**
`reportlab` isn't installed in the environment running Streamlit. Run:
```bash
pip install reportlab
```
Make sure you're installing into the same virtual environment / interpreter that's running `streamlit run`.

**Pipeline seems stuck after clicking "Generate Report"**
Check your terminal for errors — this usually means an invalid or missing `ANTHROPIC_API_KEY` or `TAVILY_API_KEY` in `.env`.

**Orchestrator or fact-checker throws a JSON parsing error**
These agents ask Claude to return raw JSON. This is rare but can happen if the model wraps its response in unexpected text. Re-running the step (or the whole pipeline) typically resolves it.

---

## Known Limitations

- **In-memory checkpointing**: session state (`MemorySaver`) lives only in the running process's memory — restarting the Streamlit server clears all in-progress sessions.
- **Single export format**: only PDF export is currently supported.
- **Claim verification is LLM-based**, not a ground-truth database lookup — treat fact-check verdicts as a helpful review aid, not a legal guarantee of accuracy.
- **Revision cap**: after 3 rejected drafts, the report is finalized automatically even without approval, to avoid unbounded loops.
