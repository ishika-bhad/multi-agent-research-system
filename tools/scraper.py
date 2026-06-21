def combine_search_results(results):
    scraped_parts = []
    urls = []

    if isinstance(results, list):
        for r in results:
            url = r.get("url", "")
            content = r.get("raw_content") or r.get("content", "")

            if url:
                urls.append(url)

            if content:
                scraped_parts.append(
                    f"[Source: {url}]\n{content[:1500]}"
                )

    return "\n\n---\n\n".join(scraped_parts), urls