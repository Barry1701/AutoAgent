# autoagent/data_access/cameras.py
import os
import re
from typing import List, Dict, Optional, Tuple

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


# ---------- wydobywanie numeru ----------

_DIGIT_GROUP = re.compile(r"\d{1,6}")


def _first_digits(s: str) -> Optional[str]:
    """Pierwsza grupa cyfr 1–6 (używane do kolumny Number)."""
    if not s:
        return None
    m = _DIGIT_GROUP.search(str(s))
    return m.group(0) if m else None


def _extract_cam_number_from_name(name: str) -> Optional[str]:
    """
    Spróbuj znaleźć numer 1–4 cyfr w typowych formach:
      '(12)', '#12', '-12', 'E25', 'PTZ-204' itd.
    Preferujemy krótkie (1–4) cyfry; ignorujemy długie liczniki typu '(511)'
    jeśli jest lepszy kandydat.
    """
    if not name:
        return None
    s = str(name)

    # 1) mocno typowe formy
    for rx in (
        r"(?:^|[^0-9])#\s*(\d{1,4})(?!\d)",         # #12
        r"\(\s*(\d{1,4})\s*\)",                    # (12)
        r"(?:^|[^A-Za-z0-9])-(\d{1,4})(?!\d)",     # -12
        r"(?:^|[^A-Za-z])([Ee]\d{1,4})(?!\d)",     # E25 -> weźmiemy cyfry poniżej
        r"(?:^|[^A-Za-z0-9])([A-Za-z]{1,3}-?\d{1,4})(?!\d)",  # C1M-12, PTZ-204
    ):
        m = re.search(rx, s)
        if m:
            token = m.group(1)
            digits = re.search(r"\d{1,4}", token)
            if digits:
                return digits.group(0)

    # 2) zbierz wszystkie grupy 1–4 cyfr i wybierz tę, która wygląda najbardziej „kamerowo”
    groups = re.findall(r"\b(\d{1,4})\b", s)
    if groups:
        # preferuj te poprzedzone '-' lub w nawiasie
        for rx in (r"-\s*(\d{1,4})\b", r"\(\s*(\d{1,4})\s*\)"):
            m2 = re.search(rx, s)
            if m2:
                return m2.group(1)
        # fallback: pierwsza krótka grupa 1–3 cyfr
        for g in groups:
            if len(g) <= 3:
                return g
        # ostatnia deska: pierwsza z listy
        return groups[0]

    return None


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
        df["_norm_all"] = df.apply(
            lambda r: _soft_norm(" ".join(map(str, r.values))), axis=1
        )

    return df


def invalidate_cache():
    load_all.cache_clear()  # type: ignore[attr-defined]


# ========== Dodatkowe helpers do 'miękkiego' dopasowania ==========

def _soft_norm(s: str) -> str:
    t = str(s or "").lower()
    t = t.replace("-", " ").replace("_", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _o0_swap_variants(s: str) -> set:
    t = str(s or "").lower()
    return {t, t.replace("o", "0"), t.replace("0", "o")}


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
    wanted_digits_match = re.fullmatch(r"\d{1,6}", q.strip())
    wanted_digits = wanted_digits_match.group(0) if wanted_digits_match else None

    # 1) klasyczne dopasowanie (kolumny Number/Name/Description)
    mask = pd.Series([False] * len(df), index=df.index)
    if col_num and df[col_num].notna().any():
        mask |= df[col_num].astype(str).str.lower().str.contains(ql, na=False)
    if col_name and df[col_name].notna().any():
        mask |= df[col_name].astype(str).str.lower().str.contains(ql, na=False)

    # 2) miękkie dopasowanie po całym wierszu (_norm_all)
    for v in {_soft_norm(v) for v in _o0_swap_variants(ql)}:
        if v:
            mask |= df["_norm_all"].str.contains(v, na=False)

    hits = df[mask]

    # 3) fallback – cokolwiek w wierszu zawiera ql
    if hits.empty:
        any_mask = df.astype(str).apply(
            lambda row: row.str.lower().str.contains(ql, na=False).any(), axis=1
        )
        hits = df[any_mask]

    if hits.empty:
        return []

    # --- budowanie odpowiedzi z deduplikacją ---
    out_map: Dict[Tuple[str, str], Dict] = {}

    def better(a: str, b: str) -> str:
        a, b = _clean_name(a), _clean_name(b)
        if not a:
            return b
        if not b:
            return a
        a_bad = "nan" in a.lower()
        b_bad = "nan" in b.lower()
        if a_bad and not b_bad:
            return b
        if b_bad and not a_bad:
            return a
        return a if len(a) >= len(b) else b

    for _, row in hits.iterrows():
        site_lbl = row.get("__site__", "")

        # --- WYDOBĄDŹ NUMER ---
        row_no = ""
        if col_num:
            row_no = _first_digits(str(row.get(col_num, ""))) or ""
        if not row_no and col_name:
            row_no = _extract_cam_number_from_name(str(row.get(col_name, ""))) or ""

        # --- JEŚLI UŻYTKOWNIK PISAŁ GOŁĄ LICZBĘ (np. "16") ---
        if wanted_digits:
            # cały wiersz jako tekst
            whole_row_text = " ".join(str(v) for v in row.values)
            has_standalone = bool(
                re.search(rf"(?<!\d){wanted_digits}(?!\d)", whole_row_text)
            )

            if row_no:
                # jeśli mamy numer z kolumny i:
                # - jest inny niż szukany
                # - i nie ma w ogóle '16' jako osobnej liczby
                #   → odrzuć
                if row_no != wanted_digits and not has_standalone:
                    continue
                # jeśli w wierszu jest '16', ale row_no inny (np. 381),
                # traktujemy '16' jako ważniejszy numer
                if has_standalone and row_no != wanted_digits:
                    row_no = wanted_digits
            else:
                # nie umiemy wyciągnąć numeru z kolumn; jeśli w wierszu nie ma '16'
                # jako osobnej liczby, pomijamy
                if not has_standalone:
                    continue
                row_no = wanted_digits

        # --- NAZWA DO WYŚWIETLENIA ---
        name_val = ""
        if col_name:
            name_val = str(row.get(col_name, "")).strip()
        if not name_val and col_num:
            name_val = str(row.get(col_num, "")).strip()
        name_val = _clean_name(name_val)

        # --- KLUCZ DEDUPLIKACJI ---
        dedup_key = (site_lbl, row_no or name_val)

        candidate = {
            "__site__": site_lbl,
            "_number": row_no,   # prawdziwy numer z wiersza (albo "")
            "_name": name_val,
            "_row": dict(row),
        }

        if dedup_key not in out_map:
            out_map[dedup_key] = candidate
        else:
            prev = out_map[dedup_key]
            prev["_name"] = better(prev.get("_name", ""), name_val)
            out_map[dedup_key] = prev

    out = list(out_map.values())

    # posprzątaj puste nazwy
    for item in out:
        nm = _clean_name(item.get("_name", ""))
        if not nm:
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
