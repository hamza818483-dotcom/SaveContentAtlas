#Github.com/Vasusen-code
# Persistent storage for thumbnail sample/photo file_ids using Supabase REST.
# Table: thumb_files (chat_id bigint, kind text, file_id text, created_at timestamptz default now())
import httpx
from decouple import config

SUPABASE_URL = config("SUPABASE_URL", default="").rstrip("/")
SUPABASE_KEY = config("SUPABASE_KEY", default="")

_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

def _table_url():
    return f"{SUPABASE_URL}/rest/v1/thumb_files"

async def add_file_id(chat_id, kind, file_id):
    """Insert a file_id row, return updated count for (chat_id, kind)."""
    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(
            _table_url(),
            headers=_HEADERS,
            json={"chat_id": chat_id, "kind": kind, "file_id": file_id},
        )
        ids = await _get_file_ids_async(chat_id, kind, client)
        return len(ids)

async def _get_file_ids_async(chat_id, kind, client):
    r = await client.get(
        _table_url(),
        headers=_HEADERS,
        params={
            "chat_id": f"eq.{chat_id}",
            "kind": f"eq.{kind}",
            "select": "file_id",
            "order": "created_at.asc",
        },
    )
    if r.status_code != 200:
        return []
    return [row["file_id"] for row in r.json()]

async def get_file_ids(chat_id, kind):
    async with httpx.AsyncClient(timeout=30) as client:
        return await _get_file_ids_async(chat_id, kind, client)

async def clear_file_ids(chat_id, kind=None):
    params = {"chat_id": f"eq.{chat_id}"}
    if kind:
        params["kind"] = f"eq.{kind}"
    async with httpx.AsyncClient(timeout=30) as client:
        await client.delete(_table_url(), headers=_HEADERS, params=params)
