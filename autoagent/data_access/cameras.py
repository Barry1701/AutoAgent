# autoagent/data_access/cameras.py
import os
import re
from typing import List, Dict, Optional, Tuple, Set

import pandas as pd

from .google_sheets import get_worksheet
from autoagent.utils.cache import ttl_cache


# ================= Helpers =================

def _read_one(sheet_id: str, tab: str, site_label: str) -> pd.DataFrame:
    """
    Czytanie arkusza jako 'gołe wartości' (bez nagłówków). Każdy wiersz łączymy w jednego str 'text'.
    Działa zarówno dla arkuszy jednokolumnowych jak i wielokolumnowych.
    """
    try:
        ws = get_worksheet(sheet_id, tab)
        values = ws.get_all_values() or []
    except Exception:
        # W razie chwilowego błędu Google – nie zabijamy całej ścieżki
        values = []

    # values: List[List[str]]
    rows: List[str] = []
    for row in values:
        # złącz tylko niepuste komórki
        text = " ".join(c.strip() for c in row if isinstance(c, str) and c.strip())
        if text:
            rows.append(text)

    if not rows:
        return pd.DataFrame(columns=["text", "__site__", "_num_end"])

    df = pd.DataFrame({"text": rows})
    df["__site__"] = site_label
    # numer na końcu w nawiasach: ... (118)
    df["_num_end"] = df["text"].str.extract(r"\((\d{1,6})\)\s*$")
    return df


def _parse_site_from_query(q: str) -> Optional[str]:
    t = q.lower()
    if "ppk1" in t or "ppk 1" in t:
        return "PPK1"
    if "ppk2" in t or "ppk 2" in t:
        return "PPK2"
    return None


def _digits_from_query(q: str) -> Optional[str]:
    m = re.search(r"\b(\d{1,6})\b", q)
    return m.group(1) if m else None


def _tokenize(q: str) -> List[str]:
    # proste tokeny alfa-num, bez krótkich „the”, itp. – ale nie przesadzamy
    return [t for t in re.findall(r"[a-z0-9]+", q.lower()) if t]


# ================= Load & cache =================

@ttl_cache(ttl_seconds=300)
def load_all() -> pd.DataFrame:
    """
    Ładuje PPK1 + (opcjonalnie) PPK2. Działa z jednokolumnowymi arkuszami.
    ENV:
      CAM_PPK1_SHEET_ID (wymagane), CAM_PPK1_SHEET_TAB (domyślnie PPK1)
      CAM_PPK2_SHEET_ID (opcjonalnie), CAM_PPK2_SHEET_TAB (domyślnie PPK2)
    """
    sheet1 = os.getenv("CAM_PPK1_SHEET_ID")
    tab1 = os.getenv("CAM_PPK1_SHEET_TAB", "PPK1")
    sheet2 = os.getenv("CAM_PPK2_SHEET_ID")
    tab2 = os.getenv("CAM_PPK2_SHEET_TAB", "PPK2")

    if not sheet1:
        # nie rozbijamy 500 – jasno powiemy w 200 z pustą listą
        return pd.DataFrame(columns=["text", "__site__", "_num_end"])

    dfs: List[pd.DataFrame] = []
    dfs.append(_read_one(sheet1, tab1, "PPK1"))
    if sheet2:
        dfs.append(_read_one(sheet2, tab2, "PPK2"))

    if not dfs:
        return pd.DataFrame(columns=["text", "__site__", "_num_end"])

    df = pd.concat(dfs, ignore_index=True)
    # sanity
    for col in ["text", "__site__", "_num_end"]:
        if col not in df.columns:
            df[col] = ""
    df["text"] = df["text"].astype(str)
    df["_num_end"] = df["_num_end"].astype(str)
    return df


def invalidate_cache():
    load_all.cache_clear()  # type: ignore[attr-defined]


# ================= Public search =================

def search(query: str, limit: int = 10) -> List[Dict]:
    """
    Szuka po numerze (jeśli jest w zapytaniu) albo po tekście.
    - Jeżeli są cyfry w zapytaniu, najpierw dopasowuje rekordy z numerem w końcowych nawiasach (…(118)).
      Jeśli nic nie znajdzie – zrobi regexp \b118\b po całym tekście (np. gdy nawiasów brak).
    - Jeśli cyfr nie ma, dopasowuje AND po tokenach; fallback to proste contains() na całość.
    Zwraca listę: { "__site__", "_number", "_name", "_row" }
    """
    df = load_all()
    if df.empty:
        return []

    q = (query or "").strip()
    if not q:
        return []

    site = _parse_site_from_query(q)
    if site:
        df = df[df["__site__"] == site]

    if df.empty:
        return []

    ql = q.lower()
    wanted_digits = _digits_from_query(ql)

    hits = pd.DataFrame([])

    if wanted_digits:
        # 1) twarde dopasowanie do numeru w końcowych nawiasach
        hits = df[df["_num_end"] == wanted_digits]

        # 2) fallback: \bNNN\b gdziekolwiek w tekście
        if hits.empty:
            pat = re.compile(rf"\b{re.escape(wanted_digits)}\b", flags=re.IGNORECASE)
            hits = df[df["text"].str.contains(pat)]

    else:
        # dopasowanie po tokenach (AND)
        tokens = _tokenize(ql)
        if tokens:
            mask = pd.Series(True, index=df.index)
            for t in tokens:
                mask &= df["text"].str.contains(re.escape(t), case=False, na=False)
            hits = df[mask]

        # fallback: prosty contains
        if hits.empty:
            hits = df[df["text"].str.contains(re.escape(ql), case=False, na=False)]

    if hits.empty:
        return []

    out: List[Dict] = []
    seen: Set[Tuple[str, str, str]] = set()

    for _, row in hits.head(max(1, limit)).iterrows():
        site_lbl = str(row.get("__site__", "")).strip()
        text_val = str(row.get("text", "")).strip()
        num_end = str(row.get("_num_end", "") or "").strip()

        cam_no = wanted_digits or num_end  # jeśli użytkownik podał numer – pokaż właśnie jego
        name_val = text_val

        key = (site_lbl, cam_no, name_val)
        if key in seen:
            continue
        seen.add(key)

        out.append({
            "__site__": site_lbl,
            "_number": cam_no,
            "_name": name_val,
            "_row": {
                "text": text_val,
                "__site__": site_lbl,
                "_num_end": num_end,
            },
        })

    return out
