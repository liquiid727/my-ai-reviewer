"""Safe external web access adapters."""

from backend.infrastructure.web.safe_fetcher import SafeWebFetcher, SafeWebFetchError

__all__ = ["SafeWebFetchError", "SafeWebFetcher"]
