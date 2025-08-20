# autoagent/agents/doors_agent.py
from typing import Dict, Any
from autoagent.data_access.doors import find_by_text

def doors_agent(query: str, context: Dict[str, Any] = {}) -> str:
    rows = find_by_text(query, limit=10)
    if not rows:
        return "No matching doors."

    out_lines = []
    for r in rows:
        cams = []
        if r.get("cameras_in") and r["cameras_in"].lower() != "n/a":
            cams.append(f"IN: {r['cameras_in']}")
        if r.get("cameras_out") and r["cameras_out"].lower() != "n/a":
            cams.append(f"OUT: {r['cameras_out']}")
        cams_s = " | ".join(cams) if cams else "Cameras: —"

        out_lines.append(
            f"[{r.get('site','?')}] {r.get('door_id','?')} — {r.get('description','').strip()} "
            f"(Location: {r.get('location','').strip()}) — {cams_s}"
        )
    return "\n".join(out_lines)
