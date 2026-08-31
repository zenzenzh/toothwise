"""
Shared rate limiter (slowapi, in-memory backend). Keyed by client IP.

In-memory storage is fine for this deployment (single uvicorn process, no
horizontal scaling) - if this ever runs behind multiple worker processes
or instances, switch slowapi's storage_uri to a shared Redis instance so
limits are enforced across all of them, not per-process.

Applied to authentication endpoints (login, patient login, patient
register) to slow down credential-stuffing / brute-force attempts. Not
applied blanket across every route - most endpoints are already behind
JWT auth, so the meaningful brute-force surface is specifically the
unauthenticated auth endpoints themselves.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
