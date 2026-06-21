import json
import re

from graph.state import ResearchState
from tools.llm import llm


def orchestrator_agent(state: ResearchState) -> dict:
    """
    Decomposes the research topic into 4-6 independent subtasks.
    Each subtask will be searched in parallel by the research agent.
    """
    print(f"\n{'='*60}")
    print(f"[Orchestrator] Topic: {state['topic']}")
    print(f"{'='*60}")

    prompt = f"""Break this research topic into 4-6 focused, independent sub-questions.
Each sub-question should cover a distinct aspect of the topic.

Topic: {state['topic']}

Return ONLY a valid JSON array of strings. No explanation, no markdown.
Example: ["question 1", "question 2", "question 3"]"""

    raw = llm.invoke(prompt).content.strip()

    # Strip markdown fences if LLM wraps output in ```json ... ```
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.DOTALL).strip()

    match = re.search(r'\[.*\]', cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"Orchestrator returned invalid JSON. Got:\n{raw}")

    subtasks = json.loads(match.group())

    print(f"[Orchestrator] Generated {len(subtasks)} subtasks:")
    for i, t in enumerate(subtasks, 1):
        print(f"  {i}. {t}")

    return {
        "subtasks": subtasks,
        "revision_count": 0
    }