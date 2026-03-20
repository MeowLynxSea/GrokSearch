import httpx
import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_random_exponential
from tenacity.wait import wait_base
from ..utils import search_prompt
from ..logger import logger
from ..config import config


def get_local_time_info() -> str:
    try:
        local_tz = datetime.now().astimezone().tzinfo
        local_now = datetime.now(local_tz)
    except Exception:
        local_now = datetime.now(timezone.utc)

    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday = weekdays[local_now.weekday()]

    return (
        f"[Current Time Context]\n"
        f"- Date: {local_now.strftime('%Y-%m-%d')} ({weekday})\n"
        f"- Time: {local_now.strftime('%H:%M:%S')}\n"
        f"- Timezone: {local_now.tzname() or 'Local'}\n"
    )


RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def _is_retryable_exception(exc) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError, httpx.RemoteProtocolError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_STATUS_CODES
    return False


class _WaitWithRetryAfter(wait_base):
    """Wait strategy: prefer Retry-After header, fallback to exponential backoff."""

    def __init__(self, multiplier: float, max_wait: int):
        self._base_wait = wait_random_exponential(multiplier=multiplier, max=max_wait)
        self._protocol_error_base = 3.0

    def __call__(self, retry_state):
        if retry_state.outcome and retry_state.outcome.failed:
            exc = retry_state.outcome.exception()
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
                retry_after = self._parse_retry_after(exc.response)
                if retry_after is not None:
                    return retry_after
            if isinstance(exc, httpx.RemoteProtocolError):
                return self._base_wait(retry_state) + self._protocol_error_base
        return self._base_wait(retry_state)

    def _parse_retry_after(self, response: httpx.Response) -> Optional[float]:
        header = response.headers.get("Retry-After")
        if not header:
            return None
        header = header.strip()

        if header.isdigit():
            return float(header)

        try:
            retry_dt = parsedate_to_datetime(header)
            if retry_dt.tzinfo is None:
                retry_dt = retry_dt.replace(tzinfo=timezone.utc)
            delay = (retry_dt - datetime.now(timezone.utc)).total_seconds()
            return max(0.0, delay)
        except (TypeError, ValueError):
            return None


class SearchResponse:
    """Holds both the text content and any citations from the Grok API response."""
    __slots__ = ("content", "citations")

    def __init__(self, content: str = "", citations: list[dict] | None = None):
        self.content = content
        self.citations = citations or []


class GrokSearchProvider:
    def __init__(self, api_url: str, api_key: str, model: str = "grok-4-fast"):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model

    async def search(self, query: str, platform: str = "") -> SearchResponse:
        """Execute AI-driven search via Grok. Returns SearchResponse with content + citations."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        platform_prompt = ""
        if platform:
            platform_prompt = (
                "\n\nYou should search the web for the information you need, "
                "and focus on these platform: " + platform + "\n"
            )

        time_context = get_local_time_info() + "\n"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": search_prompt},
                {"role": "user", "content": time_context + query + platform_prompt},
            ],
            "stream": True,
        }

        logger.debug("Grok search query: %s", query + platform_prompt)
        return await self._execute_stream_with_retry(headers, payload)

    async def _parse_streaming_response(self, response) -> SearchResponse:
        content = ""
        citations: list[dict] = []
        full_body_buffer = []

        async for line in response.aiter_lines():
            line = line.strip()
            if not line:
                continue

            full_body_buffer.append(line)

            if line.startswith("data:"):
                if line in ("data: [DONE]", "data:[DONE]"):
                    continue
                try:
                    json_str = line[5:].lstrip()
                    data = json.loads(json_str)
                    choices = data.get("choices", [])
                    if choices and len(choices) > 0:
                        choice = choices[0]
                        delta = choice.get("delta", {})
                        if "content" in delta:
                            content += delta["content"]
                        # Capture citations from streaming chunks
                        self._extract_citations(choice, citations)
                        self._extract_citations(data, citations)
                except (json.JSONDecodeError, IndexError):
                    continue

        # Fallback: try parsing as a single non-streaming JSON response
        if not content and full_body_buffer:
            try:
                full_text = "".join(full_body_buffer)
                data = json.loads(full_text)
                if "choices" in data and len(data["choices"]) > 0:
                    choice = data["choices"][0]
                    message = choice.get("message", {})
                    content = message.get("content", "")
                    self._extract_citations(choice, citations)
                    self._extract_citations(message, citations)
                    self._extract_citations(data, citations)
            except json.JSONDecodeError:
                pass

        logger.debug("Grok response length: %d chars, citations: %d", len(content), len(citations))
        return SearchResponse(content=content, citations=citations)

    @staticmethod
    def _extract_citations(obj: dict, out: list[dict]) -> None:
        """Extract citation entries from any dict that may contain them."""
        seen = {c.get("url") for c in out if c.get("url")}
        for key in ("citations", "web_search_results", "sources", "references", "search_results"):
            items = obj.get(key)
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict):
                    url = item.get("url") or item.get("link") or item.get("href") or ""
                    if url and url not in seen:
                        seen.add(url)
                        entry: dict = {"url": url}
                        title = item.get("title") or item.get("name") or ""
                        if title:
                            entry["title"] = title
                        snippet = item.get("snippet") or item.get("description") or item.get("content") or ""
                        if snippet:
                            entry["snippet"] = snippet[:500]
                        out.append(entry)
                elif isinstance(item, str) and item.startswith("http"):
                    if item not in seen:
                        seen.add(item)
                        out.append({"url": item})

    async def _execute_stream_with_retry(self, headers: dict, payload: dict) -> SearchResponse:
        """Execute streaming HTTP request with retry."""
        timeout = httpx.Timeout(connect=6.0, read=120.0, write=10.0, pool=None)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(config.retry_max_attempts + 1),
                wait=_WaitWithRetryAfter(config.retry_multiplier, config.retry_max_wait),
                retry=retry_if_exception(_is_retryable_exception),
                reraise=True,
            ):
                with attempt:
                    async with client.stream(
                        "POST",
                        f"{self.api_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    ) as response:
                        response.raise_for_status()
                        return await self._parse_streaming_response(response)
