import re
from urllib.parse import urlparse

_URL_PATTERN = re.compile(r'https?://[^\s<>"\'`，。、；：！？》）】\)]+')
_MD_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
_THINK_BLOCK_PATTERN = re.compile(r"<think>.*?</think>", re.DOTALL)
_TOOL_CALL_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:browse_page|web_search|\[WebSearch\]|\[WebFetch\])\s*"
    r"(?:\{[^}]*\})?[^\n]*",
    re.MULTILINE,
)
_CITATION_ID_PATTERN = re.compile(r"<citation_id:\d+>")


def clean_answer(text: str) -> str:
    """Strip <think> blocks, internal tool calls, and citation IDs from Grok output."""
    if not text:
        return ""
    text = _THINK_BLOCK_PATTERN.sub("", text)
    text = _TOOL_CALL_PATTERN.sub("", text)
    text = _CITATION_ID_PATTERN.sub("", text)
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def title_from_url(url: str) -> str:
    """Generate a human-readable title from a URL."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    # Remove common prefixes
    for prefix in ("www.", "docs.", "wiki.", "en.", "zh."):
        if host.startswith(prefix):
            host = host[len(prefix):]
    # Use path for more specific titles
    path = parsed.path.strip("/")
    if path:
        last_segment = path.split("/")[-1]
        last_segment = last_segment.replace("-", " ").replace("_", " ")
        # Remove common extensions
        for ext in (".html", ".htm", ".php", ".asp", ".md"):
            if last_segment.lower().endswith(ext):
                last_segment = last_segment[:-len(ext)]
        if last_segment and last_segment.lower() not in ("index", "main", "home"):
            return f"{last_segment} - {host}"
    return host


def extract_unique_urls(text: str) -> list[str]:
    """Extract all unique URLs from text, in order of first appearance."""
    seen: set[str] = set()
    urls: list[str] = []
    for m in _URL_PATTERN.finditer(text):
        url = m.group().rstrip('.,;:!?')
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def extract_sources_from_text(text: str) -> list[dict]:
    """Extract sources (title + url) from Markdown links and bare URLs in cleaned text."""
    # Clean internal noise first so tool-call URLs are not extracted
    cleaned = clean_answer(text) if text else ""
    sources: list[dict] = []
    seen: set[str] = set()

    for title, url in _MD_LINK_PATTERN.findall(cleaned):
        url = (url or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        title = (title or "").strip()
        entry: dict = {"link": url}
        entry["title"] = title if title else title_from_url(url)
        sources.append(entry)

    for url in extract_unique_urls(cleaned):
        if url in seen:
            continue
        seen.add(url)
        sources.append({"link": url, "title": title_from_url(url)})

    return sources


search_prompt = """You are a web search assistant. Search the web and provide accurate, well-sourced answers.

Guidelines:
- Search thoroughly before answering. Use multiple searches if needed.
- Always cite your sources with URLs. Include the source URL for every claim.
- List all reference URLs at the end of your response under a "Sources" heading.
- Be direct and factual. Lead with the answer, then provide details.
- Use Markdown formatting for readability.
- Prefer authoritative sources (official docs, Wikipedia, academic sources).
"""
