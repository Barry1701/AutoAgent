# autoagent/data_access/cameras.py
import os
import re
from typing import List, Dict, Optional, Tuple, Set

import pandas as pd

from .google_sheets import get_worksheet
from autoagent.utils.cache import ttl_cache


# ========== Helpers do odczytu ==========

def _read_one(sheet_id: str, tab: str, site_label: str) -> pd.DataFrame:
    ws = get_worksheet(sheet_id, tab)
    rows = ws.get_all_records()
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # odetnij spacje z nagłówków
    new_cols = {}
    for c in df.columns:
        if isinstance(c, str):
            new_cols[c] = c.strip()
    if new_cols:
        df.rename(columns=new_cols, inplace=True)

    df["__site__"] = site_label
    return df


def _pick_column(cols: List[str], *candidates: str) -> Optional[str]:
    lc_map = {c.lower(): c for c in cols if isinstance(c, str)}
    # pełne dopasowanie
    for cand in candidates:
        if cand.lower() in lc_map:
            return lc_map[cand.lower()]
    # dopasowanie jako podciąg
    for c in cols:
        cl = c.lower() if isinstance(c, str) else ""
        for cand in candidates:
            if cand.lower() in cl:
                return c
    return None


def _infer_number_and_name_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    cols = list(df.columns)
    col_num = _pick_column(
        cols,
        "Camera Number", "Number", "#", "ID",
        "Cam Number", "Cam No", "Camera #", "Camera ID"
    )
    col_name = _pick_column(
        cols,
        "Camera Name", "Name", "Description", "Camera Description",
        "Cam Name", "Cam Description", "Title"
    )
    return col_num, col_name


def _parse_site_from_query(q: str) -> Optional[str]:
    t = q.lower()
    if "ppk1" in t or "ppk 1" in t:
        return "PPK1"
    if "ppk2" in t or "ppk 2" in t:
        return "PPK2"
    return None


def _extract_cam_number(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"(?:^|[^0-9])(#[ ]*\d{1,4}|\(\s*\d{1,4}\s*\)|\b\d{1,4}\b)", str(text))
    if not m:
        return None
    token = m.group(1)
    digits = re.sub(r"[^\d]", "", token)
    return digits or None


def _digits_from_query(q: str) -> Optional[str]:
    m = re.search(r"\b(\d{1,6})\b", q)
    return m.group(1) if m else None


# ========== Dodatkowe helpers do 'miękkiego' dopasowania ==========

def _soft_norm(s: str) -> str:
    t = str(s or "").lower()
    t = t.replace("-", " ").replace("_", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _o0_swap_variants(s: str) -> set:
    t = str(s or "").lower()
    return {t, t.replace("o", "0"), t.replace("0", "o")}


def _clean_name(val: str) -> str:
    """Usuwa 'nan/NaN/null/None' i zbędne spacje."""
    if val is None:
        return ""
    s = str(val)
    s = re.sub(r"\b(nan|NaN|null|None)\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ========== Cache: wczytanie arkuszy ==========

@ttl_cache(ttl_seconds=300)
def load_all() -> pd.DataFrame:
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

    df = pd.concat(dfs, ignore_index=True)

    # Znormalizowany tekst do 'miękkiego' dopasowania
    try:
        df["_norm_all"] = df.astype(str).agg(" ".join, axis=1).map(_soft_norm)
    except Exception:
        df["_norm_all"] = df.apply(lambda r: _soft_norm(" ".join(map(str, r.values))), axis=1)

    return df


def invalidate_cache():
    load_all.cache_clear()  # type: ignore[attr-defined]


# ========== API wyszukiwania ==========

def search(query: str, limit: int = 10) -> List[Dict]:
    df = load_all()
    if df.empty:
        return []

    q = str(query or "").strip()
    if not q:
        return []

    site = _parse_site_from_query(q)
    if site:
        df = df[df["__site__"] == site]
    if df.empty:
        return []

    col_num, col_name = _infer_number_and_name_columns(df)
    ql = q.lower()
    wanted_digits = _digits_from_query(q)

    # 2) klasyczne dopasowanie
    mask = pd.Series([False] * len(df), index=df.index)
    if col_num and df[col_num].notna().any():
        mask |= df[col_num].astype(str).str.lower().str.contains(ql, na=False)
    if col_name and df[col_name].notna().any():
        mask |= df[col_name].astype(str).str.lower().str.contains(ql, na=False)

    # 3) miękkie dopasowanie
    variants = {_soft_norm(v) for v in _o0_swap_variants(ql)}
    for v in variants:
        if v:
            mask |= df["_norm_all"].str.contains(v, na=False)

    hits = df[mask]

    # 4) fallback
    if hits.empty:
        any_mask = df.astype(str).apply(
            lambda row: row.str.lower().str.contains(ql, na=False).any(), axis=1
        )
        hits = df[any_mask]

    if hits.empty:
        return []

    # --- budowanie odpowiedzi z deduplikacją po (site, number) ---
    out_map: Dict[Tuple[str, str], Dict] = {}

    def better(a: str, b: str) -> str:
        """Wybierz lepszą nazwę: bez 'nan' i dłuższą."""
        a, b = _clean_name(a), _clean_name(b)
        if not a:
            return b
        if not b:
            return a
        # prefer name bez 'nan'
        a_bad = "nan" in a.lower()
        b_bad = "nan" in b.lower()
        if a_bad and not b_bad:
            return b
        if b_bad and not a_bad:
            return a
        # dłuższa wygrywa
        return a if len(a) >= len(b) else b

    for _, row in hits.iterrows():
        site_lbl = row.get("__site__", "")

        # numer
        if wanted_digits:
            cam_no = wanted_digits
        else:
            cam_no = None
            if col_num:
                cam_no = _extract_cam_number(str(row.get(col_num, "")))
            if not cam_no and col_name:
                cam_no = _extract_cam_number(str(row.get(col_name, "")))
            cam_no = cam_no or ""

        # jeśli user podał gołą liczbę – pilnuj dokładnego numeru
        if wanted_digits and cam_no and cam_no != wanted_digits:
            continue

        # nazwa
        name_val = ""
        if col_name:
            name_val = str(row.get(col_name, "")).strip()
        if not name_val and col_num:
            name_val = str(row.get(col_num, "")).strip()
        name_val = _clean_name(name_val)

        key = (site_lbl, cam_no)

        candidate = {
            "__site__": site_lbl,
            "_number": cam_no,
            "_name": name_val,
            "_row": dict(row),
        }

        if key not in out_map:
            out_map[key] = candidate
        else:
            # wybierz lepszą nazwę i zachowaj najbogatszy rekord
            prev = out_map[key]
            best_name = better(prev.get("_name", ""), name_val)
            prev["_name"] = best_name
            # (opcjonalnie) można też scalić _row jeśli chcesz
            out_map[key] = prev

    out = list(out_map.values())

    # posprzątaj jeszcze ewentualne puste nazwy
    for item in out:
        nm = _clean_name(item.get("_name", ""))
        if not nm:
            # spróbuj zbudować coś sensownego z _row (bez _norm_all)
            row = item.get("_row", {}) or {}
            candidates = []
            for k, v in row.items():
                if k == "_norm_all":
                    continue
                vs = _clean_name(v)
                if vs:
                    candidates.append(vs)
            if candidates:
                item["_name"] = max(candidates, key=len)

    return out[: max(1, limit)]
