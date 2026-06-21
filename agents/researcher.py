from concurrent.futures import ThreadPoolExecutor, as_completed

from graph.state import ResearchState
from tools.tavily_search import searchTool
from tools.scraper import combine_search_results

def _search_one_task(task: str) -> tuple:
    """
    Searches and scrapes a single subtask.
    Returns (task, scraped_text, urls).
    """
    results = searchTool.invoke(task)

    # results is a list of dicts with keys: url, content, raw_content, score
    scraped_parts = []
    urls = []

    if isinstance(results, list):
        for r in results:
            url = r.get("url", "")
            # Prefer raw_content (full scrape) over snippet
            content = r.get("raw_content") or r.get("content", "")
            if url:
                urls.append(url)
            if content:
                # Truncate each source to 1500 chars to stay within token budget
                scraped_parts.append(f"[Source: {url}]\n{content[:1500]}")
    else:
        # Fallback: stringify whatever came back
        scraped_parts.append(str(results)[:3000])

    combined = "\n\n---\n\n".join(scraped_parts)
    return task, combined, urls


def research_agent(state: ResearchState) -> dict:
    """
    Searches all subtasks IN PARALLEL using ThreadPoolExecutor.
    Collects raw scraped content and source URLs for each subtask.
    """
    print(f"\n[Research] Searching {len(state['subtasks'])} subtasks in parallel...")

    raw_research = {}
    sources = {}

    # Run all searches concurrently
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(_search_one_task, task): task
            for task in state["subtasks"]
        }
        for future in as_completed(futures):
            task, content, urls = future.result()
            raw_research[task] = content
            sources[task] = urls
            print(f"  ✅ Done: {task[:70]}")

    print(f"[Research] All searches complete. Total sources: {sum(len(v) for v in sources.values())}")
    return {
        "raw_research": raw_research,
        "sources": sources
    }