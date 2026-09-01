from dataclasses import dataclass
from time import sleep

import httpx

DEFAULT_HTTP_TIMEOUT_SECONDS = 10.0
DEFAULT_HTTP_RETRIES = 1
DEFAULT_HTTP_BACKOFF_SECONDS = 0.25
DEFAULT_USER_AGENT = "NewsIntelligenceBot/0.1"


class HttpFetchError(Exception):
    pass


@dataclass(frozen=True)
class HttpFetchResponse:
    url: str
    status_code: int
    content_type: str | None
    text: str


def fetch_url(
    url: str,
    *,
    timeout_seconds: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
    retries: int = DEFAULT_HTTP_RETRIES,
    backoff_seconds: float = DEFAULT_HTTP_BACKOFF_SECONDS,
) -> HttpFetchResponse:
    last_error: Exception | None = None
    headers = {"User-Agent": DEFAULT_USER_AGENT}

    for attempt in range(retries + 1):
        try:
            with httpx.Client(
                timeout=timeout_seconds,
                follow_redirects=True,
                headers=headers,
            ) as client:
                response = client.get(url)

            if response.status_code >= 500 and attempt < retries:
                sleep(backoff_seconds * (2**attempt))
                continue

            return HttpFetchResponse(
                url=str(response.url),
                status_code=response.status_code,
                content_type=response.headers.get("content-type"),
                text=response.text,
            )
        except httpx.RequestError as exc:
            last_error = exc
            if attempt < retries:
                sleep(backoff_seconds * (2**attempt))
                continue

    raise HttpFetchError(str(last_error) if last_error else f"Failed to fetch {url}")
