# autoagent/agents/doors_agent.py
from typing import Dict, List
from autoagent.data_access.doors import (
    find_by_text,
    find_location,
    invalidate_cache as doors_invalidate,
)


def _wants_location(q: str) -> bool:
    t = (q or "").lower()
    return ("where is" in t) or ("location" in t) or (t.startswith("where "))


def doors_agent(query: str, context: Dict = {}) -> str:
    """
    Examples:
      - 'D0-19' / '032E' / 'UNSECURE_CORRIDOR_NO6'
      - 'where is UNSECURE_CORRIDOR_NO6'
    """
    # allow cache refresh: ... refresh=1
    refresh = str(context.get("refresh", "")).lower()
    if refresh in ("1", "true", "yes"):
        doors_invalidate()

    # jeśli pytamy o lokalizację -> spróbuj specjalnego find_location()
    if _wants_location(query):
        rows: List[Dict] = find_location(query, limit=10)
        if not rows:
            return "No matching doors (location) found."

        r = rows[0]
        tab = r.get("__tab__", "")
        door = r.get("door", "")
        loc = r.get("location") or r.get("description") or ""
        return f"[{tab}] {door}: {loc}" if loc else f"[{tab}] {door}: (no location available)"

    # w innym wypadku używamy ogólnego wyszukiwania
    rows: List[Dict] = find_by_text(query, limit=10)
    if not rows:
        return "No matching doors found."

    lines: List[str] = []
    for r in rows:
        tab = r.get("__tab__", "")
        door = r.get("door", "")
        desc = r.get("description", "")
        loc = r.get("location", "")
        if loc:
            lines.append(f"[{tab}] {door} — {desc} — {loc}")
        else:
            lines.append(f"[{tab}] {door} — {desc}")
    return "\n".join(lines)
