"""Safe URL import boundary tests without making outbound network calls."""

from collections.abc import Callable

import httpx
import pytest

from backend.infrastructure.web.safe_fetcher import SafeWebFetcher, SafeWebFetchError


def _client_factory(
    handler: Callable[[httpx.Request], httpx.Response],
) -> Callable[[], httpx.AsyncClient]:
    return lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)


async def test_fetches_public_html_and_follows_checked_redirect() -> None:
    resolved: list[str] = []

    async def resolver(host: str, port: int) -> list[str]:
        resolved.append(f"{host}:{port}")
        return ["8.8.8.8"]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "/job"}, request=request)
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text="<html><body><h1>Backend Engineer</h1><p>Build reliable services.</p></body></html>",
            request=request,
        )

    text = await SafeWebFetcher(resolver=resolver, client_factory=_client_factory(handler)).fetch_text(
        "https://jobs.example.test/start"
    )

    assert "Backend Engineer" in text
    assert len(resolved) == 2


async def test_rejects_private_dns_result_before_request() -> None:
    async def resolver(host: str, port: int) -> list[str]:
        return ["127.0.0.1"]

    with pytest.raises(SafeWebFetchError, match="non-public"):
        await SafeWebFetcher(resolver=resolver).fetch_text("https://example.test/job")


@pytest.mark.parametrize(
    "address",
    [
        "10.0.0.1",
        "127.0.0.1",
        "169.254.1.1",
        "192.168.1.1",
        "0.0.0.0",
        "::1",
        "fe80::1",
        "fc00::1",
        "::",
    ],
)
async def test_rejects_non_global_ipv4_and_ipv6_destinations(address: str) -> None:
    async def resolver(host: str, port: int) -> list[str]:
        return [address]

    with pytest.raises(SafeWebFetchError, match="non-public"):
        await SafeWebFetcher(resolver=resolver).fetch_text("https://example.test/job")


async def test_validates_redirect_target_before_following_it() -> None:
    visited: list[str] = []

    async def resolver(host: str, port: int) -> list[str]:
        return ["8.8.8.8"] if host == "public.example.test" else ["::1"]

    def handler(request: httpx.Request) -> httpx.Response:
        visited.append(str(request.url))
        return httpx.Response(
            302,
            headers={"location": "https://internal.example.test/private"},
            request=request,
        )

    with pytest.raises(SafeWebFetchError, match="non-public"):
        await SafeWebFetcher(resolver=resolver, client_factory=_client_factory(handler)).fetch_text(
            "https://public.example.test/start"
        )

    assert visited == ["https://public.example.test/start"]


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.test/job",
        "https://user:password@example.test/job",
        "https://example.test:444/job",
    ],
)
def test_rejects_unsafe_url_shapes(url: str) -> None:
    with pytest.raises(SafeWebFetchError):
        SafeWebFetcher._validate_url(url)


async def test_rejects_body_larger_than_limit() -> None:
    async def resolver(host: str, port: int) -> list[str]:
        return ["8.8.8.8"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/plain"},
            content=b"x" * (SafeWebFetcher.max_body_bytes + 1),
            request=request,
        )

    with pytest.raises(SafeWebFetchError, match="too large"):
        await SafeWebFetcher(resolver=resolver, client_factory=_client_factory(handler)).fetch_text(
            "https://example.test/job"
        )


async def test_rejects_unsupported_content_type() -> None:
    async def resolver(host: str, port: int) -> list[str]:
        return ["8.8.8.8"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/pdf"},
            content=b"%PDF-1.7",
            request=request,
        )

    with pytest.raises(SafeWebFetchError, match="content type"):
        await SafeWebFetcher(resolver=resolver, client_factory=_client_factory(handler)).fetch_text(
            "https://example.test/job"
        )


async def test_maps_total_timeout_to_safe_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def timeout(_: SafeWebFetcher, __: str) -> str:
        raise TimeoutError

    monkeypatch.setattr(SafeWebFetcher, "_fetch_text", timeout)

    with pytest.raises(SafeWebFetchError, match="timed out"):
        await SafeWebFetcher().fetch_text("https://example.test/job")


async def test_maps_httpx_timeout_to_safe_error() -> None:
    async def resolver(host: str, port: int) -> list[str]:
        return ["8.8.8.8"]

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow response", request=request)

    with pytest.raises(SafeWebFetchError, match="timed out"):
        await SafeWebFetcher(resolver=resolver, client_factory=_client_factory(handler)).fetch_text(
            "https://example.test/job"
        )
