def operations_agent(query: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Jeden punkt wejścia:
      - rozpoznaje intencję (staff / camera / doors)
      - wywołuje właściwego agenta
      - zwraca spójny payload:

      {
        "agent": "staff" | "camera" | "doors",
        "query": "<oryginalne zapytanie>",
        "result": "<czytelny tekst>",
        "rows": [ {...}, ... ]  # opcjonalne
      }
    """
    q = (query or "").strip()
    ctx = context or {}

    def _with_meta(agent_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "agent": agent_name,
            "query": q,
            "result": payload.get("result", ""),
            "rows": payload.get("rows", []),
        }

    lower = q.lower()

    # 1) Prefiksy wymuszające
    if lower.startswith("staff:"):
        sub_q = q.split(":", 1)[1].strip()
        return _with_meta("staff", _staff_payload(sub_q, ctx))

    if lower.startswith("camera:") or lower.startswith("cameras:"):
        sub_q = q.split(":", 1)[1].strip()
        return _with_meta("camera", camera_agent(sub_q, context=ctx))

    if lower.startswith("door:") or lower.startswith("doors:"):
        sub_q = q.split(":", 1)[1].strip()
        return _with_meta("doors", doors_agent(sub_q, context=ctx))

    # 2) Heurystyki intencji
    if _looks_like_door_query(q):
        return _with_meta("doors", doors_agent(q, context=ctx))

    if _looks_like_camera_query(q):
        return _with_meta("camera", camera_agent(q, context=ctx))

    if _looks_like_staff_query(q):
        return _with_meta("staff", _staff_payload(q, ctx))

    # 3) Fallback – spróbujmy po kolei
    doors_payload = doors_agent(q, context=ctx)
    if doors_payload.get("rows"):
        return _with_meta("doors", doors_payload)

    camera_payload = camera_agent(q, context=ctx)
    if camera_payload.get("rows"):
        return _with_meta("camera", camera_payload)

    staff_payload = _staff_payload(q, ctx)
    # jak staff zwróci jakiś sensowny tekst zamiast "nie znam", uznajemy za sukces
    if "couldn't find a matching employee" not in staff_payload["result"].lower():
        return _with_meta("staff", staff_payload)

    # 4) Nic nie złapało
    return {
        "agent": "unknown",
        "query": q,
        "result": (
            "I couldn't determine what you need. "
            "Try e.g. 'psa John Smith', '204', or '052A'."
        ),
        "rows": [],
    }
