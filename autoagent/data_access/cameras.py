# autoagent/data_access/cameras.py
import os
from typing import List, Dict, Optional, Tuple, Set
import re
import pandas as pd

from .google_sheets import get_worksheet
from autoagent.utils.cache import ttl_cache


# ========== Helpers ==========

def _read_one(sheet_id: str, tab: str, site_label: str) -> pd.DataFrame:
    """Read one worksheet into a DataFrame, normalize headers & add site label."""
    ws = get_worksheet(sheet_id, tab)
    rows = ws.get_all_records()
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # strip spaces in headers
    new_cols = {}
    for c in df.columns:
        if isinstance(c, str):
            new_cols[c] = c.strip()
    if new_cols:
        df.rename(columns=new_cols, inplace=True)

    df["__site__"] = site_label
    return df


def _pick_column(cols: List[str], *candidates: str) -> Optional[str]:
    """
    From a list of column names, return the first that matches any candidate
    (case-insensitive). Candidates can be exact names or substrings.
    """
    lc_map = {c.lower(): c for c in cols if isinstance(c, str)}
    # exact match first
    for cand in candidates:
        if cand.lower() in lc_map:
            return lc_map[cand.lower()]

    # then substring match
    for c in cols:
        cl = c.lower() if isinstance(c, str) else ""
        for cand in candidates:
            if cand.lower() in cl:
                return c
    return None


def _infer_number_and_name_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """Try to infer the best 'number' and 'name/description' columns."""
    cols = list(df.columns)

    # Number-like
    col_num = _pick_column(
        cols,
        "Camera Number", "Number", "#", "ID",
        "Cam Number", "Cam No", "Camera #", "Camera ID"
    )

    # Name/description-like
    col_name = _pick_column(
        cols,
        "Camera Name", "Name", "Description", "Camera Description",
        "Cam Name", "Cam Description", "Title"
    )
    return col_num, col_name


def _parse_site_from_query(q: str) -> Optional[str]:
    """Return 'PPK1' or 'PPK2' if the query mentions it, else None."""
    t = q.lower()
    if "ppk1" in t or "ppk 1" in t:
        return "PPK1"
    if "ppk2" in t or "ppk 2" in t:
        return "PPK2"
    return None


# --- precyzyjny wyciąg numeru z tekstu ---

_end_paren_digits = re.compile(r"\((\d{1,6})\)\s*$")        # ... (123)  ← tylko na końcu
_hash_digits      = re.compile(r"(?:^|[^0-9])#\s*(\d{1,6})") # #123  lub  foo # 123

def _extract_cam_number_precise(text: str) -> Optional[str]:
    """
    Zwraca numer kamery tylko gdy:
      - na KOŃCU tekstu są nawiasy z samymi cyframi: ... (123)
      - lub gdzieś występuje #123
    NIE łapie '(G11)', '(F01)' itp.
    """
    if not text:
        return None
    s = str(text)
    m = _end_paren_digits.search(s)
    if m:
        return m.group(1)
    m = _hash_digits.search(s)
    if m:
        return m.group(1)
    return None


def _digits_from_query(q: str) -> Optional[str]:
    """Return the first pure number from the query (e.g. '204'), if any."""
    m = re.search(r"\b(\d{1,6})\b", q)
    return m.group(1) if m else None


# ========== Load & cache ==========

@ttl_cache(ttl_seconds=300)
def load_all() -> pd.DataFrame:
    """
    Load cameras from Google Sheets (PPK1 + PPK2), cached for 5 minutes.
    Requires in .env:
      CAM_PPK1_SHEET_ID, CAM_PPK1_SHEET_TAB (default: PPK1)
      CAM_PPK2_SHEET_ID, CAM_PPK2_SHEET_TAB (default: PPK2)  [optional]
    """
    sheet1 = os.getenv("CAM_PPK1_SHEET_ID")
    tab1 = os.getenv("CAM_PPK1_SHEET_TAB", "PPK1")
    sheet2 = os.getenv("CAM_PPK2_SHEET_ID")
    tab2 = os.getenv("CAM_PPK2_SHEET_TAB", "PPK2")

    if not sheet1:
        raise RuntimeError("Missing CAM_PPK1_SHEET_ID in .env")

    dfs = []
    dfs.append(_read_one(sheet1, tab1, "PPK1"))
    if sheet2:
        dfs.append(_read_one(sheet2, tab2, "PPK2"))

    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


def invalidate_cache():
    """Manual cache clear (used when passing refresh=1 in agent context)."""
    load_all.cache_clear()  # type: ignore[attr-defined]


# ========== Public search API ==========

def search(query: str, limit: int = 10) -> List[Dict]:
    """
    Proste wyszukiwanie po numerze kamery lub fragmencie nazwy/opisu.
    Logika:
      1) Zawężamy do PPK1/PPK2 jeśli w pytaniu jest wzmianka.
      2) Jeśli w pytaniu występuje numer (np. '118'), traktujemy go jako
         główny klucz wyszukiwania (zamiast pełnego tekstu 'camera 118').
      3) Najpierw próbujemy po kolumnach 'number' i 'name/description',
         a potem fallback: dowolna kolumna zawiera klucz.
    """
    df = load_all()
    if df.empty:
        return []

    q = str(query or "").strip()
    if not q:
        return []

    # zawężenie do PPK1/PPK2
    site = _parse_site_from_query(q)
    if site:
        df = df[df["__site__"] == site]

    col_num, col_name = _infer_number_and_name_columns(df)

    # klucze do szukania
    ql = q.lower()
    wanted_digits = _digits_from_query(q)              # np. "118" z "camera 118"
    effective_term = (wanted_digits or ql)             # <-- NAJWAŻNIEJSZE: szukamy już po samych cyfrach, jeśli są

    # ---- primary: number/name
    mask = pd.Series(False, index=df.index)
    if col_num and df[col_num].notna().any():
        mask |= df[col_num].astype(str).str.lower().str.contains(effective_term, na=False)
    if col_name and df[col_name].notna().any():
        mask |= df[col_name].astype(str).str.lower().str.contains(effective_term, na=False)

    hits = df[mask]

    # ---- fallback: każda kolumna
    if hits.empty:
        # najpierw spróbujmy po 'effective_term' (czyli po cyfrach, jeśli są),
        # bo to unifikuje zachowanie '118' == 'camera 118'
        any_mask = df.astype(str).apply(
            lambda row: row.str.lower().str.contains(effective_term, na=False).any(),
            axis=1
        )
        hits = df[any_mask]

    if hits.empty:
        return []

    # ---- budowa wyników
    out: List[Dict] = []
    seen: Set[Tuple[str, str, str]] = set()

    if col_num or col_name:
        for _, row in hits.iterrows():
            site_lbl = row.get("__site__", "")

            # jeśli w pytaniu był numer – pokażemy ten numer;
            # inaczej spróbujemy wyciągnąć z danych
            if wanted_digits:
                cam_no = wanted_digits
            else:
                cam_no = None
                if col_num:
                    cam_no = _extract_cam_number(str(row.get(col_num, "")))
                if not cam_no and col_name:
                    cam_no = _extract_cam_number(str(row.get(col_name, "")))
                cam_no = cam_no or ""

            name_val = ""
            if col_name:
                name_val = str(row.get(col_name, "")).strip()
            if not name_val and col_num:
                name_val = str(row.get(col_num, "")).strip()

            key = (site_lbl, cam_no, name_val)
            if key in seen:
                continue
            seen.add(key)

            out.append({
                "__site__": site_lbl,
                "_number": cam_no,
                "_name": name_val,
                "_row": dict(row),
            })
    else:
        # nietypowy układ (np. tylko jedna kolumna z długim opisem)
        for _, row in hits.iterrows():
            site_lbl = row.get("__site__", "")
            for header in hits.columns:
                h = str(header).strip()
                v = str(row.get(header, "")).strip()
                if not h and not v:
                    continue

                # dopasowanie po effective_term (czyli po cyfrach, jeśli są)
                if effective_term in h.lower() or effective_term in v.lower():
                    if wanted_digits:
                        cam_no = wanted_digits
                    else:
                        cam_no = _extract_cam_number(h) or _extract_cam_number(v) or ""

                    disp = h if len(h) >= len(v) else v
                    key = (site_lbl, cam_no, disp)
                    if key in seen:
                        continue
                    seen.add(key)

                    out.append({
                        "__site__": site_lbl,
                        "_number": cam_no,
                        "_name": disp,
                        "_row": dict(row),
                    })

    return out[: max(1, limit)]
