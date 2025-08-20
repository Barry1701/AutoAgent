# autoagent/data_access/doors.py

from __future__ import annotations

import os
import re
from typing import List, Dict, Optional

import pandas as pd

from autoagent.data_access.google_sheets import get_worksheet

# ===== Konfiguracja środowiska (.env) =====
DOORS_SHEET_ID = os.getenv("DOORS_SHEET_ID", "").strip()
TAB_PPK1 = os.getenv("DOORS_TAB_PPK1", "PPK1").strip()
TAB_PPK2 = os.getenv("DOORS_TAB_PPK2", "PPK2").strip()
TAB_EXP  = os.getenv("DOORS_TAB_EXPANSION", "Expansion").strip()

# ===== Stałe kolumn kanonicznych =====
COL_DOOR_ID = "door_id"
COL_DESC    = "description"
COL_LOC     = "location"
COL_CAM_IN  = "cameras_in"
COL_CAM_OUT = "cameras_out"
COL_SITE    = "site"

REQUIRED_COLS = [COL_DOOR_ID, COL_DESC, COL_LOC, COL_CAM_IN, COL_CAM_OUT]

# ===== Normalizacja i aliasy nagłówków =====
def _norm_header(s: str) -> str:
    """Ujednolica nagłówek: lower, usuwa NBSP, zwija znaki do a-z0-9 i pojedynczych spacji."""
    s = (s or "").replace("\u00A0", " ").strip().lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)        # wszystko co nie a-z0-9 -> spacja
    s = re.sub(r"\s+", " ", s).strip()
    return s

HEADER_ALIASES = {
    # Door ID
    "door id": COL_DOOR_ID,
    "door_id": COL_DOOR_ID,

    # Description (różne warianty z arkuszy)
    "description per ccure": COL_DESC,      # najczęstszy wariant w PPK2
    "description percure": COL_DESC,
    "description per cure": COL_DESC,
    "description per c cure": COL_DESC,
    "description": COL_DESC,

    # Location
    "location description": COL_LOC,
    "location": COL_LOC,

    # Cameras
    "cameras in": COL_CAM_IN,
    "cameras in ": COL_CAM_IN,              # czasem z dodatkowymi spacjami
    "cameras out": COL_CAM_OUT,
    "cameras out ": COL_CAM_OUT,
}

# ===== Pobranie i ujednolicenie jednego arkusza =====
def _ws_to_df(tab_name: str, site_label: str) -> pd.DataFrame:
    """Czyta zakładkę z Google Sheets, normalizuje nagłówki i zwraca DF w kanonicznym układzie."""
    if not DOORS_SHEET_ID:
        raise RuntimeError("Brak DOORS_SHEET_ID w .env")

    ws = get_worksheet(DOORS_SHEET_ID, tab_name)
    values = ws.get_all_values()
    if not values:
        return pd.DataFrame(columns=REQUIRED_COLS + [COL_SITE])

    raw_headers = values[0]
    norm_headers = [_norm_header(h) for h in raw_headers]
    df = pd.DataFrame(values[1:], columns=norm_headers)

    # zastosuj aliasy -> kanoniczne nazwy kolumn
    rename_map = {h: HEADER_ALIASES.get(h, h) for h in df.columns}
    df = df.rename(columns=rename_map)

    # dołóż brakujące kolumny jeśli jakieś nie zostały rozpoznane
    for c in REQUIRED_COLS:
        if c not in df.columns:
            df[c] = ""

    df = df[REQUIRED_COLS].copy()
    df[COL_SITE] = site_label

    # czyszczenie treści i usuwanie NBSP
    for c in df.columns:
        df[c] = df[c].astype(str).str.replace("\u00A0", " ", regex=False).str.strip()

    # Usuń puste wiersze bez ID i opisu, żeby nie śmieciły
    mask_nonempty = (df[COL_DOOR_ID].astype(str).str.strip() != "") | \
                    (df[COL_DESC].astype(str).str.strip()    != "") | \
                    (df[COL_LOC].astype(str).str.strip()     != "")
    df = df[mask_nonempty].reset_index(drop=True)

    return df

# ===== Ładowanie wszystkich zakładek i łączenie =====
def _load_all() -> pd.DataFrame:
    """Łączy PPK1, PPK2, Expansion w jeden DataFrame z kolumną 'site'."""
    frames = [
        _ws_to_df(TAB_PPK1, "PPK1"),
        _ws_to_df(TAB_PPK2, "PPK2"),
        _ws_to_df(TAB_EXP,  "Expansion"),
    ]
    df = pd.concat(frames, ignore_index=True)

    # Usuwanie duplikatów po (site, door_id, description, location, cameras)
    df = df.drop_duplicates(
        subset=[COL_SITE, COL_DOOR_ID, COL_DESC, COL_LOC, COL_CAM_IN, COL_CAM_OUT],
        keep="first"
    ).reset_index(drop=True)

    return df

# ===== Formatowanie jednej pozycji do czytelnego stringa =====
def format_row(row: Dict) -> str:
    site = row.get(COL_SITE, "")
    door_id = row.get(COL_DOOR_ID, "")
    desc = row.get(COL_DESC, "")
    loc = row.get(COL_LOC, "")
    cam_in = row.get(COL_CAM_IN, "")
    cam_out = row.get(COL_CAM_OUT, "")
    cam = []
    if cam_in:
        cam.append(f"IN: {cam_in}")
    if cam_out:
        cam.append(f"OUT: {cam_out}")
    cams = " | ".join(cam) if cam else "No cameras listed"

    base = f"[{site}] {door_id} — {desc}"
    if loc:
        base += f" — {loc}"
    base += f" — {cams}"
    return base

# ===== Wyszukanie po tekście (ID / opis / lokalizacja) =====
def find_by_text(query: str, limit: int = 10) -> List[Dict]:
    """
    Szuka po:
      - exact/partial door_id (np. 'D0-17', '032E', 'D0')
      - fragmentach w description lub location (case-insensitive)
    Zwraca listę słowników (max limit).
    """
    q = (query or "").strip()
    if not q:
        return []

    df = _load_all()

    # dopasowanie po ID (case-insensitive, substring)
    id_hit = df[COL_DOOR_ID].astype(str).str.contains(q, case=False, regex=False)

    # dopasowanie po description i location (substring, case-insensitive)
    desc_hit = df[COL_DESC].astype(str).str.contains(q, case=False, regex=False)
    loc_hit  = df[COL_LOC].astype(str).str.contains(q, case=False, regex=False)

    hit = id_hit | desc_hit | loc_hit
    if not hit.any():
        return []

    cols = [COL_SITE, COL_DOOR_ID, COL_DESC, COL_LOC, COL_CAM_IN, COL_CAM_OUT]
    out = df.loc[hit, cols].head(limit).to_dict(orient="records")
    return out

# ===== Wyszukanie po dokładnym ID =====
def find_by_id(door_id: str, limit: int = 10) -> List[Dict]:
    """Dokładne dopasowanie ID drzwi (bez częściowych)."""
    d = (door_id or "").strip()
    if not d:
        return []
    df = _load_all()
    hit = df[COL_DOOR_ID].astype(str).str.lower() == d.lower()
    if not hit.any():
        return []
    cols = [COL_SITE, COL_DOOR_ID, COL_DESC, COL_LOC, COL_CAM_IN, COL_CAM_OUT]
    return df.loc[hit, cols].head(limit).to_dict(orient="records")
