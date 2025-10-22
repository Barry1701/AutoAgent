# autoagent/agents/doors_agent.py
from typing import Dict, Any, List
from autoagent.data_access import doors as doors_da

def _format_row(r: Dict[str, Any]) -> str:
    site = r.get("__tab__", "") or ""
    door = r.get("door", "") or ""
    desc = r.get("description", "") or ""
    loc  = r.get("location", "") or ""
    cin  = (r.get("cameras_in") or "").strip()
    cout = (r.get("cameras_out") or "").strip()

    parts: List[str] = []
    # główna linia (jak było)
    head = f"[{site}] {door} — {desc}".strip(" —")
    parts.append(head)

    # location jeśli jest
    if loc:
        parts.append(f"Location: {loc}")

    # cameras in/out jeśli są
    if cin:
        parts.append(f"Cameras IN: {cin}")
    if cout:
        parts.append(f"Cameras OUT: {cout}")

    return " — ".join(parts)

def handle(query: str, refresh: int = 0) -> Dict[str, Any]:
    if refresh:
        doors_da.invalidate_cache()

    # spróbuj dopasowania „gdzie jest…”
    rows = doors_da.find_location(query, limit=10)
    if not rows:
        rows = doors_da.find_by_text(query, limit=10)

    if not rows:
        return {
            "agent": "doors_agent",
            "query": query,
            "result": "No matching doors.",
        }

    lines = [_format_row(r) for r in rows]
    return {
        "agent": "doors_agent",
        "query": query,
        # zostawiamy „result” jako string – frontend nic nie musi zmieniać
        "result": "\n".join(f"- {ln}" for ln in lines),
        # jakbyś chciał w przyszłości w UI ładniej renderować tabelkę:
        "rows": rows,  # <— pełne dane strukturalne
    }
