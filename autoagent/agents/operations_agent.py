# autoagent/agents/operations_agent.py
import re
from typing import Dict, Any

# Wykorzystujemy istniejących „specjalistów”
from .staff_directory_agent import staff_directory_agent
from .camera_agent import camera_agent
from .doors_agent import doors_agent

STAFF_KEYWORDS = [
    "psa", "contact", "pin", "ldap", "l-dap", "first aid", "safepass",
    "badge", "earpiece", "emergency", "licence", "license", "expiry", "expiration"
]
CAMERA_KEYWORDS = [
    "camera", "cctv", "flir", "ppk1", "ppk 1", "ppk2", "ppk 2"
]
DOOR_KEYWORDS = [
    "door", "reader", "badge reader", "c-cure", "ccure", "ccure 900", "access"
]

# wzorce typowe dla zapytań drzwiowych (np. 032E, 052A, 2–4 cyfry + litera)
RE_DOOR_CODE = re.compile(r"\b\d{2,4}[A-Z]\b", re.IGNORECASE)
# wzorzec „goły numer” – zwykle kamery (np. 204)
RE_PURE_NUMBER = re.compile(r"^\D*(\d{2,6})\D*$")


def _looks_like_door_query(q: str) -> bool:
    t = q.lower()
    if any(k in t for k in DOOR_KEYWORDS):
        return True
    if RE_DOOR_CODE.search(q):
        return True
    return False


def _looks_like_camera_query(q: str) -> bool:
    t = q.lower()
    if any(k in t for k in CAMERA_KEYWORDS):
        return True
    # Krótkie zapytanie z numerem (np. „204”) traktujemy jako kamerę
    m = RE_PURE_NUMBER.match(q)
    if m and len(m.group(1)) <= 4:
        return True
    return False


def _looks_like_staff_query(q: str) -> bool:
    t = q.lower()
    if any(k in t for k in STAFF_KEYWORDS):
        return True
    # heurystyka: zawiera „for <Name>” albo dwa „słowa” z wielkiej litery (imię + nazwisko)
    if re.search(r"\bfor\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+", q):
        return True
    cap_words = re.findall(r"\b[A-Z][a-z]+", q)
    if len(cap_words) >= 2:
        return True
    return False


def operations_agent(query: str, context: Dict[str, Any] = {}) -> str:
    """
    Jeden punkt wejścia:
      - rozpoznaje intencję (staff / camera / doors)
      - wywołuje właściwego agenta
      - przekazuje context (np. refresh=1)
    Przykłady:
      - "psa Bartosz Stanczuk"
      - "What is the PSA Licence expiry date for Bartosz Stanczuk?"
      - "204" / "ppk2 389"
      - "032E" / "Which camera is near door 052A?"
    """
    q = (query or "").strip()
    ctx = context or {}

    # 1) Twarde prefiksy (użytkownik może wymusić)
    lower = q.lower()
    if lower.startswith("staff:"):
        return staff_directory_agent(q.split(":", 1)[1].strip(), context=ctx)
    if lower.startswith("camera:") or lower.startswith("cameras:"):
        return camera_agent(q.split(":", 1)[1].strip(), context=ctx)
    if lower.startswith("door:") or lower.startswith("doors:"):
        return doors_agent(q.split(":", 1)[1].strip(), context=ctx)

    # 2) Heurystyki intencji
    if _looks_like_door_query(q):
        return doors_agent(q, context=ctx)
    if _looks_like_camera_query(q):
        return camera_agent(q, context=ctx)
    if _looks_like_staff_query(q):
        return staff_directory_agent(q, context=ctx)

    # 3) Fallback – kolejność: doors -> cameras -> staff
    # (jeśli chcesz odwrotnie, przestaw)
    resp_doors = doors_agent(q, context=ctx)
    if resp_doors and "No matching doors" not in resp_doors:
        return resp_doors

    resp_cams = camera_agent(q, context=ctx)
    if resp_cams and resp_cams.strip() not in ("[]", "No matching cameras.", "[] # —"):
        return resp_cams

    resp_staff = staff_directory_agent(q, context=ctx)
    if resp_staff and "couldn't find a matching employee" not in resp_staff.lower():
        return resp_staff

    return "I couldn't determine what you need. Try e.g. 'psa John Smith', '204', or '052A'."
