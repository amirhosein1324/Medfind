"""Shared rate limiter instance.

Kept in its own module (rather than main.py) so routers can import and
apply @limiter.limit(...) to individual endpoints without a circular
import back to the app object.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
