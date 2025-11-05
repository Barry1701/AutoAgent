# autoagent/agents/doors_agent.py
# Agent do wyszukiwania drzwi (PPK1/PPK2/Expansion) z wyświetlaniem Cameras IN / OUT

from typing import Any, Dict, List, Optional
from autoagent.data_access import doors as doors_da


def _format_row(row: Dict[str, Any]) -> str:
    """
    Buduje jedną linijkę opisu drzwi:
    [PPK1] D-G26 — Opis — Location: ... — Cameras IN: ... — Cameras OUT: ...
    """
    site = (row.get("__tab__") or "").strip()
    door = (row.get("door") or "").strip()
    desc = (row.get("description") or "").strip()
    loc  = (row.get("location") or "").strip()
    cin  = (row.get("cameras_in") or "").strip()
    cout = (row.get("cameras_out") or "").strip()

    parts: List[str] = []
    head = f"[{site}] {door}".strip()
    if desc:
        head = f"{head} — {desc}"
    parts.append(head)

    if loc:
        parts.append(f"Location: {loc}")
    if cin:
        parts.append(f"Cameras IN: {cin}")
    if cout:
        parts.append(f"Cameras OUT: {cout}")

    return " — ".join(parts)


def doors_agent(query: str, context: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Zwraca PŁASKI payload (app.py doda agent/query):
    {
      "result": "<czytelny string listy>",
      "rows": [ {...}, ... ]
    }
    """
    try:
        refresh = 0
        if context and isinstance(context, dict):
            refresh = int(context.get("refresh", 0)) if context.get("refresh") is not None else 0

        if refresh:
            doors_da.invalidate_cache()

        rows = doors_da.find_location(query, limit=10)
        if not rows:
            rows = doors_da.find_by_text(query, limit=10)

        if not rows:
            return {
                "result": "No matching doors.",
                "rows": [],
            }

        lines = [_format_row(r) for r in rows]
        pretty = "\n".join(f"- {ln}" for ln in lines)

        # PŁASKO – BEZ podwójnej koperty
        return {
            "result": pretty,
            "rows": rows,
        }

    except Exception as e:
        return {
            "result": f"Error: {e}",
            "rows": [],
        }
