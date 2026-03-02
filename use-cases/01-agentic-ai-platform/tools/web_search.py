"""Web search tool - uses DuckDuckGo HTML search (no API key needed)."""

import aiohttp
import re


async def _web_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo HTML."""
    url = "https://html.duckduckgo.com/html/"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; AgenticAI/1.0)"}
    data = {"q": query}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return f"Search failed with status {resp.status}"
                html = await resp.text()

        # Extract results from DuckDuckGo HTML
        results = []
        # Find result snippets
        snippets = re.findall(
            r'class="result__snippet">(.*?)</a>',
            html, re.DOTALL
        )
        titles = re.findall(
            r'class="result__a"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )
        urls = re.findall(
            r'class="result__url"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )

        for i in range(min(max_results, len(titles))):
            title = re.sub(r'<[^>]+>', '', titles[i]).strip() if i < len(titles) else ""
            snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else ""
            link = urls[i].strip() if i < len(urls) else ""
            results.append(f"{i+1}. {title}\n   URL: {link}\n   {snippet}")

        if not results:
            return f"No results found for: {query}"
        return "\n\n".join(results)

    except Exception as e:
        return f"Search error: {e}"


web_search_tool = {
    "definition": {
        "name": "web_search",
        "description": "Search the web for information using a query string. Returns titles, URLs, and snippets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    "handler": _web_search
}
