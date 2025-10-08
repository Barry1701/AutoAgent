# autoagent/data_access/staff_tracker.py
import os
import time
from functools import lru_cache

import pandas as pd
from autoagent.data_access.google_sheets import get_worksheet

STAFF_TRACKER_CSV = os.path.join(os.path.dirname(__file__), "../data/Staff Tracker.csv")
TTL_SECONDS = 300


@lru_cache(maxsize=64)
def _load_df_cached_gsheet(sheet_id: str, tab_name: str, time_bucket: int) -> pd.DataFrame:
    ws = get_worksheet(sheet_id, tab_name or None)
    return pd.DataFrame(ws.get_all_records()).fillna("")


@lru_cache(maxsize=64)
def _load_df_cached_csv(path: str, time_bucket: int) -> pd.DataFrame:
    return pd.read_csv(path).fillna("")


def load_staff_df() -> pd.DataFrame:
    """Uniwersalny loader: Google Sheets jeśli STAFF_SOURCE=google; inaczej CSV."""
    source = (os.getenv("STAFF_SOURCE") or "csv").lower()
    bucket = int(time.time() // TTL_SECONDS)

    if source == "google":
        sheet_id = os.getenv("STAFF_SHEET_ID")
        tab = os.getenv("STAFF_SHEET_TAB") or "Sheet1"
        if not sheet_id:
            raise RuntimeError("STAFF_SOURCE=google, ale brak STAFF_SHEET_ID w .env")
        return _load_df_cached_gsheet(sheet_id, tab, bucket)

    return _load_df_cached_csv(STAFF_TRACKER_CSV, bucket)
