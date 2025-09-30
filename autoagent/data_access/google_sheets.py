# autoagent/data_access/google_sheets.py
import os
import json
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import gspread

# Wczytaj zmienne z .env
load_dotenv()

def _client() -> gspread.Client:
    # 1) Najpierw spróbuj z Secret JSON w ENV
    google_sa_json = os.getenv("GOOGLE_SA_JSON")
    if google_sa_json:
        try:
            creds_dict = json.loads(google_sa_json)
            return gspread.service_account_from_dict(creds_dict)
        except Exception as e:
            raise RuntimeError(f"Nie udało się załadować GOOGLE_SA_JSON: {e}")

    # 2) Fallback: plik ścieżką z GOOGLE_APPLICATION_CREDENTIALS
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path:
        raise RuntimeError("Brak GOOGLE_SA_JSON i GOOGLE_APPLICATION_CREDENTIALS w .env")

    p = Path(cred_path)
    if not p.is_absolute():
        project_root = Path(__file__).resolve().parents[2]
        p = (project_root / cred_path).resolve()

    if not p.exists():
        raise RuntimeError(f"GOOGLE_APPLICATION_CREDENTIALS wskazuje na nieistniejący plik: {p}")

    return gspread.service_account(filename=str(p))

def get_worksheet(sheet_id: str, tab_name: Optional[str] = None):
    gc = _client()
    sh = gc.open_by_key(sheet_id)
    return sh.worksheet(tab_name) if tab_name else sh.sheet1
