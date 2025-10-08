# autoagent/data_access/google_sheets.py
import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import gspread

# Wczytaj .env (lokalnie); w Codex zmienne są już w środowisku
load_dotenv()


def _client() -> gspread.Client:
    """
    Kolejność źródeł poświadczeń:
    1) GOOGLE_SA_JSON  – cały JSON serwisowego konta w jednej zmiennej (sekret)
    2) GOOGLE_APPLICATION_CREDENTIALS – ścieżka do pliku z JSON
    """
    sa_json = os.getenv("GOOGLE_SA_JSON")
    if sa_json:
        try:
            # Sekrety zwykle nie mają nowych linii -> zwykłe json.loads
            data = json.loads(sa_json)
        except Exception as e:
            raise RuntimeError(
                "GOOGLE_SA_JSON is set but is not valid JSON (cannot json.loads). "
                "Paste the *entire* service-account JSON as the value."
            ) from e

        try:
            # gspread ma wygodny helper do dict
            return gspread.service_account_from_dict(data)
        except Exception as e:
            raise RuntimeError(
                "Failed to initialize Google Sheets client from GOOGLE_SA_JSON dict."
            ) from e

    # Fallback: plik
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path:
        p = Path(cred_path)
        if not p.is_absolute():
            # plik w repo -> przelicz względem root projektu
            project_root = Path(__file__).resolve().parents[2]
            p = (project_root / cred_path).resolve()

        if not p.exists():
            raise RuntimeError(
                f"GOOGLE_APPLICATION_CREDENTIALS points to a non-existing file: {p}"
            )

        try:
            return gspread.service_account(filename=str(p))
        except Exception as e:
            raise RuntimeError(
                "Failed to initialise Google Sheets client from file credentials"
            ) from e

    # Jeśli nic nie ustawione:
    raise RuntimeError(
        "No Google credentials found. Set GOOGLE_SA_JSON (recommended) "
        "or GOOGLE_APPLICATION_CREDENTIALS (path to JSON file)."
    )


def get_worksheet(sheet_id: str, tab_name: Optional[str] = None):
    """
    Zwraca gspread.Worksheet dla danego arkusza/zakładki.
    - sheet_id: ID pliku Google Sheets (z URL)
    - tab_name: nazwa zakładki; jeśli None -> sheet1
    """
    gc = _client()
    sh = gc.open_by_key(sheet_id)
    return sh.worksheet(tab_name) if tab_name else sh.sheet1
