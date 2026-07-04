from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from graph.state import ResearchState
from agents.orchestrator import orchestrator_agent
from agents.researcher import research_agent
from agents.analyst import analyzer_agent
from agents.writer import writer_agent
from agents.fact_checker import fact_checker_agent
from agents.finalizer import finalizer_agent
from graph.human_gate import human_approval_gate, route_after_human

memory = MemorySaver()

builder = StateGraph(ResearchState)

# ── Nodes ──────────────────────────────────────────────────────────────────────
builder.add_node("orchestrator", orchestrator_agent)
builder.add_node("research",     research_agent)
builder.add_node("analyzer",     analyzer_agent)
builder.add_node("writer",       writer_agent)
builder.add_node("fact_checker", fact_checker_agent)
builder.add_node("human_gate",   human_approval_gate)
builder.add_node("finalizer",    finalizer_agent)

# ── Edges ──────────────────────────────────────────────────────────────────────
builder.add_edge(START,          "orchestrator")
builder.add_edge("orchestrator", "research")
builder.add_edge("research",     "analyzer")
builder.add_edge("analyzer",     "writer")
builder.add_edge("writer",       "fact_checker")
builder.add_edge("fact_checker", "human_gate")

# FIX: edge map keys must exactly match strings returned by route_after_human.
# Previously "finalize" was used here but the node is named "finalizer" → KeyError.
builder.add_conditional_edges(
    "human_gate",
    route_after_human,
    {
        "finalizer": "finalizer", 
        "revise":    "writer",
    },
)

builder.add_edge("finalizer", END)

graph = builder.compile(checkpointer=memory)