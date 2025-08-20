# autoagent/data_access/cameras.py
import os
import re
from typing import List, Dict
import pandas as pd

from .google_sheets import get_worksheet

CAMERA_COL = "camera"   # nazwa kolumny z pełną nazwą kamery
SITE_COL   = "site"     # PPK1 / PPK2
NAME_COL   = "name"     # kopia / przetworzona nazwa (opcjonalnie)
NUM_COL    = "number"   # numer z nawiasu na końcu

def _read_one(sheet_id: str, tab: str, site_label: str) -> pd.DataFrame:
    ws = get_worksheet(sheet_id, tab)
    values = ws.get_all_values()
    df = pd.DataFrame(values, columns=["raw"])
    # usuń puste
    df = df[df["raw"].str.strip().ne("")]
    df = df.rename(columns={"raw": CAMERA_COL})
    df[SITE_COL] = site_label

    # wyciągnij numer z końcówki "(1234)" → kolumna NUM_COL jako string
    m = df[CAMERA_COL].str.extract(r"\((\d+)\)\s*$")
    df[NUM_COL] = m[0].astype(str)

    # pomocnicza kopia do ewentualnych dalszych matchy
    df[NAME_COL] = df[CAMERA_COL]
    return df

def load_all() -> pd.DataFrame:
    # środowisko
    sheet1  = os.getenv("CAM_PPK1_SHEET_ID")
    tab1    = os.getenv("CAM_PPK1_SHEET_TAB")
    sheet2  = os.getenv("CAM_PPK2_SHEET_ID")
    tab2    = os.getenv("CAM_PPK2_SHEET_TAB")

    df1 = _read_one(sheet1, tab1, "PPK1")
    df2 = _read_one(sheet2, tab2, "PPK2")

    df = pd.concat([df1, df2], ignore_index=True)
    # deduplikacja po (site, number) – jeśli chcesz
    df = df.drop_duplicates(subset=[SITE_COL, NUM_COL]).reset_index(drop=True)
    return df

def search(query: str, limit: int = 10) -> List[Dict]:
    df = load_all()
    q = query.strip().lower()

    # 1) site + number: "ppk2 389" / "ppk1   123"
    m = re.match(r"^\s*(ppk\s*([12]))\s+(\d+)\s*$", q, flags=re.I)
    if m:
        site_num = m.group(2)          # "1" lub "2"
        cam_num  = m.group(3)          # "389"
        site_val = f"PPK{site_num}"
        hit = df[(df[SITE_COL] == site_val) & (df[NUM_COL] == cam_num)]
    else:
        # 2) tylko numer: "389"
        if re.fullmatch(r"\d+", q):
            hit = df[df[NUM_COL] == q]
        else:
            # 3) dowolny fragment nazwy (case-insensitive)
            hit = df[df[NAME_COL].str.lower().str.contains(q, na=False)]

    if hit.empty:
        return []

    cols = [SITE_COL, NUM_COL, NAME_COL, CAMERA_COL]
    return hit[cols].head(limit).to_dict(orient="records")
