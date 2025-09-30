# autoagent/data_access/google_sheets.py
import os
import json
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import gspread

# Load environment variables from a local .env if present. This mirrors the
# previous behaviour while still allowing deployment environments to inject the
# variables directly.
load_dotenv()


def _client() -> gspread.Client:
    """Return an authenticated gspread client.

    Preference is given to the GOOGLE_SA_JSON environment variable which is how
    the production environment exposes the service account credentials. If that
    is unavailable we fall back to GOOGLE_APPLICATION_CREDENTIALS which should
    point at a service account JSON file on disk. When neither option is
    configured we raise a clear error so the API does not fail silently.
    """

    google_sa_json = os.getenv("GOOGLE_SA_JSON")
    if google_sa_json:
        try:
            creds_dict = json.loads(google_sa_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Invalid JSON in GOOGLE_SA_JSON environment variable"
            ) from exc

        try:
            return gspread.service_account_from_dict(creds_dict)
        except Exception as exc:  # pragma: no cover - defensive: gspread may vary
            raise RuntimeError(
                "Failed to initialise Google Sheets client from GOOGLE_SA_JSON"
            ) from exc

    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path:
        raise RuntimeError(
            "Missing Google Sheets credentials: set GOOGLE_SA_JSON or "
            "GOOGLE_APPLICATION_CREDENTIALS"
        )

    p = Path(cred_path)
    if not p.is_absolute():
        project_root = Path(__file__).resolve().parents[2]
        p = (project_root / cred_path).resolve()

    if not p.exists():
        raise RuntimeError(
            "GOOGLE_APPLICATION_CREDENTIALS points to a non-existent file: "
            f"{p}"
        )

    try:
        return gspread.service_account(filename=str(p))
    except Exception as exc:  # pragma: no cover - defensive: gspread may vary
        raise RuntimeError(
            "Failed to initialise Google Sheets client from file credentials"
        ) from exc

def get_worksheet(sheet_id: str, tab_name: Optional[str] = None):
    gc = _client()
    sh = gc.open_by_key(sheet_id)
    return sh.worksheet(tab_name) if tab_name else sh.sheet1
