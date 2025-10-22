# autoagent/data_access/cameras.py
import os
import re
from typing import List, Dict, Optional, Tuple, Set

import pandas as pd

from .google_sheets import get_worksheet
from autoagent.utils.cache import ttl_cache


# ========== Helpers do odczytu ==========

def _read_one(sheet_id: str, tab: str, site_label: str) -> pd.DataFrame:
    """Czyta zakładkę z Google Sheets, normalizuje nagłówki i dokleja etykietę site."""
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
    """
    Z listy nagłówków wybierz pierwszy pasujący do kandydata (case-insensitive).
    Kandydaci mogą być pełnymi nazwami lub podciągami.
    """
    lc_map = {c.lower(): c for c in cols if isinstance(c, str)}
    # najpierw dopasowanie pełne
    for cand in candidates:
        if cand.lower() in lc_map:
            return lc_map[cand.lower()]
    # potem dopasowanie jako podciąg
    for c in cols:
        cl = c.lower() if isinstance(c, str) else ""
        for cand in candidates:
            if cand.lower() in cl:
                return c
    return None


def _infer_number_and_name_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """Zgadnij najlepsze kolumny 'numer' i 'nazwa/opis'."""
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
    """Zwróć 'PPK1' lub 'PPK2', jeśli zapytanie o tym wspomina."""
    t = q.lower()
    if "ppk1" in t or "ppk 1" in t:
        return "PPK1"
    if "ppk2" in t or "ppk 2" in t:
        return "PPK2"
    return None


def _extract_cam_number(text: str) -> Optional[str]:
    """
    Wyciągnij 'numer kamery' z tekstu: np. '(204)' -> '204', '#204' -> '204', '... 204 ...' -> '204'.
    """
    if not text:
        return None
    m = re.search(r"(?:^|[^0-9])(#[ ]*\d{1,4}|\(\s*\d{1,4}\s*\)|\b\d{1,4}\b)", str(text))
    if not m:
        return None
    token = m.group(1)
    digits = re.sub(r"[^\d]", "", token)
    return digits or None


def _digits_from_query(q: str) -> Optional[str]:
    """Zwróć pierwszą 'gołą' liczbę z zapytania (np. '204'), jeżeli występuje."""
    m = re.search(r"\b(\d{1,6})\b", q)
    return m.group(1) if m else None


# ========== Dodatkowe helpers do 'miękkiego' dopasowania ==========

def _soft_norm(s: str) -> str:
    """lower, zamiana '-' i '_' na spacje, zbicie wielokrotnych spacji."""
    t = str(s or "").lower()
    t = t.replace("-", " ").replace("_", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _o0_swap_variants(s: str) -> set:
    """
    Zwraca warianty zapytania z zamianą 'o'↔'0' – pomaga w 'CO-92' vs 'C0-92'.
    """
    t = str(s or "").lower()
    return {t, t.replace("o", "0"), t.replace("0", "o")}


# ========== Cache: wczytanie arkuszy ==========

@ttl_cache(ttl_seconds=300)
def load_all() -> pd.DataFrame:
    """
    Wczytuje kamery z Google Sheets (PPK1 + PPK2), cache 5 minut.
    Env:
      CAM_PPK1_SHEET_ID, CAM_PPK1_SHEET_TAB (domyślnie PPK1)
      CAM_PPK2_SHEET_ID, CAM_PPK2_SHEET_TAB (domyślnie PPK2)  [opcjonalnie]
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

    df = pd.concat(dfs, ignore_index=True)

    # Zbuduj kolumnę znormalizowaną dla miękkiego dopasowania
    try:
        df["_norm_all"] = df.astype(str).agg(" ".join, axis=1).map(_soft_norm)
    except Exception:
        # awaryjnie – jakby coś nie dało się zrzutować
        df["_norm_all"] = df.apply(lambda r: _soft_norm(" ".join(map(str, r.values))), axis=1)

    return df


def invalidate_cache():
    """Ręczne czyszczenie cache (wywoływane np. przez refresh=1)."""
    load_all.cache_clear()  # type: ignore[attr-defined]


# ========== API wyszukiwania ==========

def search(query: str, limit: int = 10) -> List[Dict]:
    """
    Proste wyszukiwanie po numerze lub fragmencie nazwy/opisu.
    Kolejność:
      1) Opcjonalne zawężenie do PPK1/PPK2.
      2) Dopasowanie po kolumnach Number/Name (klasyczne contains).
      3) Miękkie dopasowanie na znormalizowanym tekście (_norm_all):
         - ignoruje '-' i '_'
         - sprawdza warianty 'o'↔'0'
      4) Fallback: scan dowolnej kolumny (klasyczne contains).
    Dodatkowo wyświetlany _number jest wymuszany na 'gołej liczbie' znalezionej w zapytaniu,
    aby nie łapać numerów z nawiasów w nagłówkach.
    """
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

    # --- 2) klasyczne dopasowanie po kolumnach number/name
    mask = pd.Series([False] * len(df), index=df.index)
    if col_num and df[col_num].notna().any():
        mask |= df[col_num].astype(str).str.lower().str.contains(ql, na=False)
    if col_name and df[col_name].notna().any():
        mask |= df[col_name].astype(str).str.lower().str.contains(ql, na=False)

    # --- 3) miękkie dopasowanie na znormalizowanych tekstach
    variants = { _soft_norm(v) for v in _o0_swap_variants(ql) }
    for v in variants:
        if v:
            mask |= df["_norm_all"].str.contains(v, na=False)

    hits = df[mask]

    # --- 4) fallback: skanowanie dowolnej kolumny (klasyczne contains), jeśli nadal pusto
    if hits.empty:
        any_mask = df.astype(str).apply(
            lambda row: row.str.lower().str.contains(ql, na=False).any(), axis=1
        )
        hits = df[any_mask]

    if hits.empty:
        return []

    # --- budowanie odpowiedzi
    out: List[Dict] = []
    seen: Set[Tuple[str, str, str]] = set()

    if col_num or col_name:
        for _, row in hits.iterrows():
            site_lbl = row.get("__site__", "")

            # numer do wyświetlenia
            if wanted_digits:
                cam_no = wanted_digits
            else:
                cam_no = None
                if col_num:
                    cam_no = _extract_cam_number(str(row.get(col_num, "")))
                if not cam_no and col_name:
                    cam_no = _extract_cam_number(str(row.get(col_name, "")))
                cam_no = cam_no or ""

            # nazwa/opis do wyświetlenia
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
        # nietypowy layout – iterujemy po nagłówkach jako potencjalnych tytułach
        for _, row in hits.iterrows():
            site_lbl = row.get("__site__", "")
            for header in hits.columns:
                val = row.get(header, "")
                h = str(header).strip()
                v = str(val).strip()
                if not h and not v:
                    continue
                if ql in h.lower() or ql in v.lower():
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
