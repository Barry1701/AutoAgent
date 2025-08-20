# autoagent/agents/camera_agent.py
from typing import Dict, List
from autoagent.data_access.cameras import search as camera_search, CAMERA_COL

def camera_agent(query: str, context: Dict = {}) -> str:
    """
    Look up cameras by partial name/number/site (PPK1/PPK2).
    Returns up to 10 matches in a compact list.
    """
    hits: List[Dict] = camera_search(query, limit=10)
    if not hits:
        return "No matching cameras."

    lines = []
    for h in hits:
        site = h.get("site", "")
        number = h.get("number", "")
        name = h.get("name", "")
        raw = h.get(CAMERA_COL, "")
        lines.append(f"[{site}] #{number} — {name} — {raw}")

    return "\n".join(lines)
