# autoagent/agents/camera_agent.py
from typing import Dict, List
import pandas as pd

from autoagent.data_access.cameras import search as cameras_search, invalidate_cache


def _pick_col(cols: List[str], *cands: str):
    """Wybiera pierwszą kolumnę pasującą do kandydatów (najpierw exact, potem substring, case-insensitive)."""
    lc = {c.lower(): c for c in cols if isinstance(c, str)}

    # exact
    for cand in cands:
        real = lc.get(cand.lower())
        if real:
            return real

    # substring
    for c in cols:
        cl = c.lower() if isinstance(c, str) else ""
        for cand in cands:
            if cand.lower() in cl:
                return c
    return None


def _infer_cols(records: List[Dict]):
    """Zgadnij kolumny: numer kamery i nazwa/opis, bazując na kluczach pierwszego rekordu."""
    if not records:
        return None, None
    cols = list(records[0].keys())

    col_num = _pick_col(
        cols,
        "Camera Number", "Number", "#", "ID", "Cam Number", "Cam No", "Camera #", "Camera ID"
    )
    col_name = _pick_col(
        cols,
        "Camera Name", "Name", "Description", "Camera Description", "Cam Name", "Cam Description", "Title"
    )
    return col_num, col_name


def camera_agent(query: str, context: Dict = {}) -> str:
    """
    Przykłady:
      - '204'
      - 'ppk2 389'
      - 'ppk1 loading bay'
    Wspiera refresh=1 (czyści cache) przez context z CLI: ... refresh=1
    """
    # refresh cache?
    refresh_flag = str(context.get("refresh", "0")).lower() in {"1", "true", "yes"}
    if refresh_flag:
        invalidate_cache()

    hits: List[Dict] = cameras_search(query, limit=10)
    if not hits:
        return "No matching cameras."

    col_num, col_name = _infer_cols(hits)

    lines = []
    for rec in hits[:10]:
        site = rec.get("__site__", "")
        num = rec.get(col_num, "") if col_num else ""
        name = rec.get(col_name, "") if col_name else ""

        site_part = f"[{site}] " if site else ""
        num_part = f"#{num}" if str(num).strip() else ""
        sep = " — " if num_part and name else ""
        name_part = f"{name}" if str(name).strip() else ""

        if not (num_part or name_part):
            # awaryjnie pokaż cały rekord jako string
            lines.append(f"{site_part}{rec}")
        else:
            lines.append(f"{site_part}{num_part}{sep}{name_part}")

    # gdybyś chciał szybciej zawęzić:
    # podpowiedz: dopisz 'ppk1' lub 'ppk2' w zapytaniu.
    return "\n".join(lines)
