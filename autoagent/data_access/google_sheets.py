# autoagent/data_access/google_sheets.py
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import gspread

# Wczytaj zmienne z .env (na wypadek uruchamiania bez `export`)
load_dotenv()

def _client() -> gspread.Client:
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path:
        raise RuntimeError("Brak GOOGLE_APPLICATION_CREDENTIALS w .env")

    p = Path(cred_path)
    if not p.is_absolute():
        # plik jest w autoagent/data_access/ -> root projektu = parents[2]
        project_root = Path(__file__).resolve().parents[2]
        p = (project_root / cred_path).resolve()

    if not p.exists():
        raise RuntimeError(f"GOOGLE_APPLICATION_CREDENTIALS wskazuje na nieistniejący plik: {p}")

    return gspread.service_account(filename=str(p))

def get_worksheet(sheet_id: str, tab_name: Optional[str] = None):
    gc = _client()
    sh = gc.open_by_key(sheet_id)
    return sh.worksheet(tab_name) if tab_name else sh.sheet1
