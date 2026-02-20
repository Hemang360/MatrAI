"""
db/supabase_client.py
---------------------
Initializes and exposes a singleton Supabase client for use across the app.

Usage:
    from db.supabase_client import get_supabase_client

    supabase = get_supabase_client()
    response = supabase.table("users").select("*").execute()
"""

from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


@lru_cache()
def get_supabase_client() -> Client:
    """
    Return a cached Supabase client instance.

    The client is created once and reused for the lifetime of the process.
    Credentials are pulled from the app settings (loaded from .env).

    Returns:
        supabase.Client: An authenticated Supabase client.

    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY are not set.
    """
    settings = get_settings()

    if not settings.supabase_url or not settings.supabase_key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY must be set in your .env file."
        )

    client: Client = create_client(settings.supabase_url, settings.supabase_key)
    return client
