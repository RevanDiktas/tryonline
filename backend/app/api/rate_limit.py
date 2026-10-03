"""
Per-client rate limiting.

Behind Vercel's /api rewrite and Railway's proxy, request.client.host is a proxy address,
so keying on it put every shopper and brand into one shared bucket. Key on the first
X-Forwarded-For hop instead (the original client as Vercel reports it), falling back to
the socket address for direct/local calls.

We deliberately do NOT key on the bearer token's user id: the limiter runs before auth,
so the id would be unverified and a caller could mint a fresh one per request to dodge it.
"""
from fastapi import HTTPException, Request
from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter
from slowapi.util import get_remote_address

# One dashboard range click fires 18 analytics calls; 300/min leaves room for ~16 clicks a
# minute per client (several staff behind one office IP included) while still capping abuse.
ANALYTICS_LIMIT = parse("300/minute")

# In-memory, like the existing slowapi limiters: correct for the single Railway instance.
_storage = MemoryStorage()
_limiter = MovingWindowRateLimiter(_storage)


def client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for") or ""
    first_hop = forwarded.split(",")[0].strip()
    return first_hop or get_remote_address(request)


def analytics_rate_limit(request: Request) -> None:
    """Router-level dependency for /api/analytics/*: 429 past ANALYTICS_LIMIT per client."""
    if not _limiter.hit(ANALYTICS_LIMIT, "analytics", client_key(request)):
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
