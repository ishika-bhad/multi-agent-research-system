from concurrent.futures import ThreadPoolExecutor, as_completed

from tools.llm import llm


from graph.state import ResearchState


def analyzer_agent(state: ResearchState) -> dict:
    """
    Summarizes raw scraped content into 3-4 key insights per subtask.
    Runs in parallel to save time.
    """
    print(f"\n[Analyzer] Summarizing {len(state['raw_research'])} research results...")

    def _summarize(task: str, raw: str) -> tuple:
        prompt = f"""Summarize the following research into 3-4 concrete, factual insights.
Be specific. Include numbers, statistics, or dates where present.
Do NOT invent information not present in the source.

Subtask: {task}

Research Content:
{raw[:4000]}

Insights:"""
        summary = llm.invoke(prompt).content.strip()
        return task, summary

    insights = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(_summarize, task, raw): task
            for task, raw in state["raw_research"].items()
        }
        for future in as_completed(futures):
            task, summary = future.result()
            insights[task] = summary
            print(f"  ✅ Analyzed: {task[:70]}")

    print("[Analyzer] All insights ready.")
    return {"analyzed_insights": insights}