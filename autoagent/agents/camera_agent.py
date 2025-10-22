# autoagent/agents/camera_agent.py
from typing import Dict, Any, List
from autoagent.data_access import cameras


def camera_agent(query: str, context: Dict[str, str] | None = None) -> Dict[str, Any]:
    """
    Zwraca listę kamer w formacie zgodnym z frontem:
    {
      "agent": "camera_agent",
      "query": "...",
      "result": {
        "result": "<czytelny_tekst>",
        "rows": [
          {
            "__site__": "PPK1" | "PPK2",
            "_number": "204",
            "_name": "IE-DUB-DAT3 ....",
            "_row": { ... }     # pełen wiersz z arkusza (opcjonalnie)
          },
          ...
        ]
      }
    }
    """
    ctx = context or {}
    if str(ctx.get("refresh", "0")) in ("1", "true", "True"):
        cameras.invalidate_cache()

    rows: List[Dict[str, Any]] = cameras.search(query, limit=10)

    # Tekstowa, skrócona lista (używane jako fallback / kopia do logów)
    if rows:
        lines = [
            f"- [{r.get('__site__','?')}] #{r.get('_number','?')} — {r.get('_name','').strip()}"
            for r in rows
        ]
        text = "Matches:\n" + "\n".join(lines)
    else:
        text = "No matching cameras."

    return {
        "agent": "camera_agent",
        "query": query,
        "result": {
            "result": text,
            "rows": rows,
        },
    }
