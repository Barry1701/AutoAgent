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
    lc_map = {c.lower(): c for c in cols if isinstance(c, str)]
    for cand in candidates:
        if cand.lower() in lc_map:
            return lc_map[cand.lower()]
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


def _soft_norm(s: str) -> str:
    t = str(s or "").lower()
    t = t.replace("-", " ").replace("_", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _o0_swap_variants(s: str) -> set:
    t = str(s or "").lower()
    return {t, t.replace("o", "0"), t.replace("0", "o")}


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


def _tokenize(q: str) -> List[str]:
    toks = re.findall(r"[a-z0-9]+", q.lower())
    return [t for t in toks if t]


# --------- NEW: wybór najlepszego "tytułu" z dowolnej kolumny ---------
_META_COLS = {"__site__", "_norm_all"}

def _best_name_from_row(row: pd.Series, want_tokens: List[str]) -> str:
    """
    Gdy brak klasycznej kolumny 'Name/Description', wybierz najlepszą wartość
    z dowolnej kolumny wiersza: ta o największej liczbie trafień tokenów,
    przy remisie — najdłuższa.
    """
    best = ""
    best_hits = -1
    tokens = [t for t in want_tokens if t]

    for col, val in row.items():
        if col in _META_COLS:
            continue
        s = str(val or "").strip()
        if not s:
            continue
        norm = _soft_norm(s)
        hits = 0
        for t in tokens:
            matched = False
            for v in _o0_swap_variants(t):
                if v and v in norm:
                    matched = True
                    break
            if matched:
                hits += 1
        # wybór: najpierw po liczbie trafień, potem po długości
        if hits > best_hits or (hits == best_hits and len(s) > len(best)):
            best_hits = hits
            best = s

    # jeżeli nic nie pasuje tokenami, wybierz najdłuższą niepustą wartość
    if not best:
        longest = ""
        for col, val in row.items():
            if col in _META_COLS:
                continue
            s = str(val or "").strip()
            if len(s) > len(longest):
                longest = s
        best = longest

    return best
# ----------------------------------------------------------------------


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

    try:
        df["_norm_all"] = df.astype(str).agg(" ".join, axis=1).map(_soft_norm)
    except Exception:
        df["_norm_all"] = df.apply(lambda r: _soft_norm(" ".join(map(str, r.values))), axis=1)

    return df


def invalidate_cache():
    load_all.cache_clear()  # type: ignore[attr-defined]


# ========== API wyszukiwania ==========

def search(query: str, limit: int = 10) -> List[Dict]:
    """
    Wyszukiwanie 'miękkie':
      - AND po wszystkich tokenach tekstowych (np. "warehouse 35"),
      - liczba w zapytaniu (np. 35) traktowana jako numer (bonus),
      - tolerancja O<->0,
      - sortowanie po score,
      - zawsze wybieramy czytelny tytuł: klasyczna kolumna 'Name' lub fallback
        ze skanowania całego wiersza (_best_name_from_row).
    """
    df = load_all()
    if df.empty:
        return []

    q_raw = str(query or "").strip()
    if not q_raw:
        return []

    site = _parse_site_from_query(q_raw)
    if site:
        df = df[df["__site__"] == site]
        if df.empty:
            return []

    col_num, col_name = _infer_number_and_name_columns(df)

    q_norm = _soft_norm(q_raw)
    tokens = _tokenize(q_norm)
    digit_token = _digits_from_query(q_norm)
    text_tokens = [t for t in tokens if not t.isdigit()]

    def row_score(row) -> int:
        text = str(row["_norm_all"])
        score = 0

        # 1) cała fraza (warianty O<->0)
        for v in _o0_swap_variants(q_norm):
            if v and v in text:
                score += 2
                break

        # 2) AND po tokenach tekstowych
        for t in text_tokens:
            matched = False
            for v in _o0_swap_variants(t):
                if v in text:
                    matched = True
                    break
            if matched:
                score += 1
            else:
                return -1  # odrzut – brak jednego z tokenów

        # 3) bonus za liczbę
        if digit_token:
            if col_num:
                num_val = str(row.get(col_num, "")).strip()
                if re.search(rf"(?:^|[^\d]){re.escape(digit_token)}(?:[^\d]|$)", num_val):
                    score += 5
            for v in _o0_swap_variants(digit_token):
                if re.search(rf"(?:^|[^\d]){re.escape(v)}(?:[^\d]|$)", text):
                    score += 3
                    break

        return score

    scored = []
    for idx, row in df.iterrows():
        s = row_score(row)
        if s >= 0:
            scored.append((s, row))

    if not scored:
        return []

    scored.sort(key=lambda x: (x[0], str(x[1].get("__site__", ""))), reverse=True)

    out: List[Dict] = []
    seen: Set[Tuple[str, str, str]] = set()

    for score, row in scored:
        site_lbl = row.get("__site__", "")

        # numer do wyświetlenia
        cam_no = ""
        if digit_token:
            cam_no = digit_token
        else:
            if col_num:
                cam_no = _extract_cam_number(str(row.get(col_num, ""))) or ""
            if not cam_no and col_name:
                cam_no = _extract_cam_number(str(row.get(col_name, ""))) or ""

        # nazwa/opis – najpierw klasyczna kolumna, potem fallback z całego wiersza
        name_val = ""
        if col_name:
            name_val = str(row.get(col_name, "")).strip()
        if not name_val:
            # użyj tokenów (tekstowych + liczbowego, jeśli był)
            want_tokens = list(text_tokens)
            if digit_token:
                want_tokens.append(digit_token)
            name_val = _best_name_from_row(row, want_tokens)

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

        if len(out) >= max(1, limit):
            break

    return out
