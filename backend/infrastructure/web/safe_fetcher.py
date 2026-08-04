"""Bounded public-web fetcher for untrusted JD import URLs."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable
from urllib.parse import urljoin

import httpx

from backend.infrastructure.parsers.html_parser import extract_visible_text

try:
    import trafilatura
except ImportError:  # pragma: no cover - fallback keeps the service usable during partial installs.
    trafilatura = None  # type: ignore[assignment]

Resolver = Callable[[str, int], Awaitable[list[str]]]


class SafeWebFetchError(ValueError):
    """A safe, user-displayable URL import failure."""


class SafeWebFetcher:
    """Fetch public HTML/plain text without trusting proxies or redirects."""

    max_redirects = 3
    max_body_bytes = 2 * 1024 * 1024
    allowed_content_types = {"text/html", "text/plain"}

    def __init__(
        self,
        *,
        resolver: Resolver | None = None,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self._resolver = resolver or self._resolve_host
        self._client_factory = client_factory or self._new_client

    @staticmethod
    def _new_client() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            trust_env=False,
            follow_redirects=False,
            timeout=httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0),
        )

    @staticmethod
    async def _resolve_host(host: str, port: int) -> list[str]:
        loop = asyncio.get_running_loop()
        records = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        return sorted({str(record[4][0]) for record in records})

    async def fetch_text(self, url: str) -> str:
        """Return cleaned visible text after validating every redirect hop."""
        try:
            async with asyncio.timeout(20):
                return await self._fetch_text(url)
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise SafeWebFetchError("URL fetch timed out") from exc
        except httpx.RequestError as exc:
            raise SafeWebFetchError("URL fetch failed") from exc

    async def _fetch_text(self, url: str) -> str:
        current = self._validate_url(url)
        async with self._client_factory() as client:
            for redirect_count in range(self.max_redirects + 1):
                await self._validate_destination(current)
                async with client.stream("GET", current) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            raise SafeWebFetchError("Redirect response did not provide a destination")
                        if redirect_count >= self.max_redirects:
                            raise SafeWebFetchError("URL exceeded the redirect limit")
                        current = self._validate_url(urljoin(str(current), location))
                        continue
                    if response.status_code < 200 or response.status_code >= 300:
                        raise SafeWebFetchError(f"URL returned HTTP {response.status_code}")

                    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower().strip()
                    if content_type not in self.allowed_content_types:
                        raise SafeWebFetchError("URL content type is not supported")
                    body = await self._read_limited(response)
                    encoding = response.encoding or "utf-8"
                    source = body.decode(encoding, errors="replace")
                    text = self._extract_text(source, content_type)
                    if not text.strip():
                        raise SafeWebFetchError("No readable job description content was found")
                    return text
        raise SafeWebFetchError("URL exceeded the redirect limit")

    @staticmethod
    def _validate_url(value: str) -> httpx.URL:
        try:
            url = httpx.URL(value)
        except httpx.InvalidURL as exc:
            raise SafeWebFetchError("URL is invalid") from exc
        if url.scheme not in {"http", "https"} or not url.host:
            raise SafeWebFetchError("Only public HTTP and HTTPS URLs are supported")
        if url.userinfo:
            raise SafeWebFetchError("URLs with credentials are not allowed")
        if url.port is not None and url.port not in {80, 443}:
            raise SafeWebFetchError("URL port is not allowed")
        return url

    async def _validate_destination(self, url: httpx.URL) -> None:
        assert url.host is not None
        port = url.port or (443 if url.scheme == "https" else 80)
        addresses = await self._resolver(url.host, port)
        if not addresses:
            raise SafeWebFetchError("URL host could not be resolved")
        for address in addresses:
            try:
                parsed = ipaddress.ip_address(address)
            except ValueError as exc:
                raise SafeWebFetchError("URL host resolved to an invalid address") from exc
            if not parsed.is_global:
                raise SafeWebFetchError("URL host resolves to a non-public address")

    async def _read_limited(self, response: httpx.Response) -> bytes:
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > self.max_body_bytes:
                raise SafeWebFetchError("URL response is too large")
            chunks.append(chunk)
        return b"".join(chunks)

    @staticmethod
    def _extract_text(source: str, content_type: str) -> str:
        if content_type == "text/plain":
            return source.strip()
        extracted = trafilatura.extract(source, include_comments=False, include_tables=True) if trafilatura else None
        return (extracted or extract_visible_text(source)).strip()
