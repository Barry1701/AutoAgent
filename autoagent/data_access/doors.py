# autoagent/data_access/doors.py
import os
import re
from typing import List, Dict, Optional
import pandas as pd

from .google_sheets import get_worksheet
from autoagent.utils.cache import ttl_cache

SHEET_ID = os.getenv("DOORS_SHEET_ID")

_STOPWORDS = {
    "where", "is", "are", "the", "a", "an", "of", "for", "to", "at", "in",
    "door", "reader", "location", "please", "tell", "me", "what", "which"
}

def _norm_text(x: str) -> str:
    if not isinstance(x, str):
        x = "" if pd.isna(x) else str(x)
    s = x.lower()
    s = re.sub(r"[^0-9a-z]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _extract_tokens(q: str) -> List[str]:
    raw = re.findall(r"[a-z0-9_]+", str(q).lower())
    toks = [t.replace("_", " ") for t in raw if t not in _STOPWORDS]
    flat: List[str] = []
    for t in toks:
        flat.extend([p for p in t.split() if p])
    return [t for t in flat if len(t) > 1]

def _pick_column(
    cols: List[str],
    *,
    exact: Optional[List[str]] = None,
    prefer_contains: Optional[List[str]] = None,
    allow_contains: Optional[List[str]] = None,
) -> Optional[str]:
    lc_map = {str(c).lower(): c for c in cols if isinstance(c, str)}
    if exact:
        for e in exact:
            if e.lower() in lc_map:
                return lc_map[e.lower()]
    if prefer_contains:
        for c in cols:
            cl = str(c).lower()
            if any(p in cl for p in prefer_contains):
                return c
    if allow_contains:
        for c in cols:
            cl = str(c).lower()
            if any(a in cl for a in allow_contains):
                return c
    return None

def _ws_to_df(tab: str) -> pd.DataFrame:
    ws = get_worksheet(SHEET_ID, tab)
    rows = ws.get_all_records()
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df.columns = [str(c).strip() for c in df.columns]
    cols = list(df.columns)

    # Główne pola
    col_door = _pick_column(
        cols,
        exact=["Door ID", "Reader ID", "Door", "Reader"],
        prefer_contains=["door id", "reader id", "door", "reader"],
    )
    col_desc = _pick_column(
        cols,
        exact=["Description PerC-Cure"],
        prefer_contains=["description per", "per-c", "perc"],
        allow_contains=["description"],
    )
    col_loc = _pick_column(
        cols,
        exact=["Location Description"],
        prefer_contains=["location description"],
        allow_contains=["location"],
    )

    # Kamery IN/OUT (obsługa wariantów nazw)
    col_in = _pick_column(
        cols,
        exact=["Cameras IN", "Camera IN", "Cameras In"],
        prefer_contains=["cameras in", "camera in", "in cameras", "in camera"],
    )
    col_out = _pick_column(
        cols,
        exact=["Cameras OUT", "Camera OUT", "Cameras Out"],
        prefer_contains=["cameras out", "camera out", "out cameras", "out camera"],
    )

    out = pd.DataFrame()
    out["door"] = df[col_door].astype(str).str.strip() if col_door else ""
    out["description"] = df[col_desc].astype(str).str.strip() if col_desc else ""
    out["location"] = df[col_loc].astype(str).str.strip() if col_loc else ""
    out["cameras_in"] = df[col_in].astype(str).str.strip() if col_in else ""
    out["cameras_out"] = df[col_out].astype(str).str.strip() if col_out else ""
    out["__tab__"] = tab

    # znormalizowane do wyszukiwania
    out["_door_norm"] = out["door"].map(_norm_text)
    out["_desc_norm"] = out["description"].map(_norm_text)
    out["_loc_norm"] = out["location"].map(_norm_text)

    return out

@ttl_cache(ttl_seconds=300)
def _load_all() -> pd.DataFrame:
    if not SHEET_ID:
        raise RuntimeError("Missing DOORS_SHEET_ID in .env")

    tabs_env = os.getenv("DOORS_TABS")
    if tabs_env:
        tabs = [t.strip() for t in tabs_env.split(",") if t.strip()]
    else:
        tabs = [
            os.getenv("DOORS_TAB_PPK1", "PPK1"),
            os.getenv("DOORS_TAB_PPK2", "PPK2"),
            os.getenv("DOORS_TAB_EXPANSION", "Expansion"),
        ]

    frames: List[pd.DataFrame] = []
    for tab in tabs:
        if not tab:
            continue
        try:
            frames.append(_ws_to_df(tab))
        except Exception:
            continue

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)

def invalidate_cache():
    _load_all.cache_clear()  # type: ignore[attr-defined]

def find_by_text(query: str, limit: int = 10) -> List[Dict]:
    df = _load_all()
    if df.empty:
        return []
    q = (query or "").strip()
    if not q:
        return []

    qn = _norm_text(q)
    mask = (
        df["_door_norm"].str.contains(qn, na=False)
        | df["_desc_norm"].str.contains(qn, na=False)
        | df["_loc_norm"].str.contains(qn, na=False)
    )
    hits = df[mask]
    if hits.empty:
        return []
    return hits[
        ["door", "description", "location", "cameras_in", "cameras_out", "__tab__"]
    ].head(limit).to_dict(orient="records")

def find_location(query: str, limit: int = 10) -> List[Dict]:
    df = _load_all()
    if df.empty:
        return []

    q_raw = (query or "").strip().lower()
    phrase_underscore = re.sub(r"\s+", "_", q_raw)
    phrase_spaces = re.sub(r"[_]+", " ", q_raw)
    tokens = _extract_tokens(q_raw)

    if not tokens:
        return find_by_text(query, limit=limit)

    def contains_all(text: str, toks: List[str]) -> bool:
        return all(t in text for t in toks)

    def count_hits(text: str, toks: List[str]) -> int:
        return sum(1 for t in toks if t in text)

    def row_match(row) -> bool:
        door = row["_door_norm"]
        desc = row["_desc_norm"]
        loc = row["_loc_norm"]
        combined = f"{door} {desc} {loc}"

        if phrase_underscore and phrase_underscore in combined:
            return True
        if phrase_spaces and phrase_spaces in combined:
            return True

        if contains_all(door, tokens) or contains_all(desc, tokens) or contains_all(loc, tokens):
            return True

        if count_hits(combined, tokens) >= max(2, len(tokens) - 1):
            return True

        return False

    hits = df[df.apply(row_match, axis=1)]
    if hits.empty:
        return []

    return hits[
        ["door", "description", "location", "cameras_in", "cameras_out", "__tab__"]
    ].head(limit).to_dict(orient="records")
