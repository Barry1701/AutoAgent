# app.py — FastAPI dla AutoAgenta (zabezpieczony)
import os
from typing import Optional, Union, Dict, List

from fastapi import FastAPI, Query, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# ==== Importy agentów ====
from autoagent.agents.operations_agent import operations_agent as operations_fn
from autoagent.agents.staff_directory_agent import staff_directory_agent as staff_fn
from autoagent.agents.camera_agent import camera_agent as camera_fn
from autoagent.agents.doors_agent import doors_agent as doors_fn
# =========================

# --- Konfiguracja środowiska i bezpieczeństwa ---
ENV = os.getenv("ENV", "prod").lower()  # dev / prod
API_TOKEN = os.getenv("API_TOKEN", "").strip()

# Ukryj dokumentację w produkcji (Heroku)
openapi_kwargs = {} if ENV == "dev" else {"docs_url": None, "redoc_url": None, "openapi_url": None}
app = FastAPI(title="AutoAgent API", version="0.2-secure", **openapi_kwargs)

# --- CORS ---
_front_single = os.getenv("FRONTEND_ORIGIN", "").strip()
_front_multi = [o.strip() for o in os.getenv("FRONTEND_ORIGINS", "").split(",") if o.strip()]

ALLOW_ORIGINS = []
if _front_single:
    ALLOW_ORIGINS.append(_front_single)
ALLOW_ORIGINS.extend(_front_multi)

# Dopuszczamy Gitpod / Heroku tylko po HTTPS (regex)
ALLOW_ORIGIN_REGEX = r"^https://.*\.gitpod\.io$|^https://.*\.herokuapp\.com$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS or ["http://localhost:5173"],
    allow_origin_regex=r"^https://.*\.gitpod\.io$|^https://.*\.herokuapp\.com$",
    allow_credentials=True,
    allow_methods=["*"],   # GET/POST/OPTIONS itd.
    allow_headers=["*"],   # <- kluczowe: pozwól na wszystkie nagłówki (w tym sec-ch-ua)
)

# --- Bearer Auth (dla wszystkich endpointów /api/* poza /api/health) ---
bearer_scheme = HTTPBearer(auto_error=False)

def require_bearer_token(cred: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """
    Weryfikacja nagłówka Authorization: Bearer <token>.
    Jeśli token nie jest ustawiony lub nie pasuje — zwraca 401.
    """
    if not API_TOKEN:
        # jeśli brak tokenu w ENV — tylko w DEV pozwalamy działać bez niego
        if ENV != "dev":
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail="API is not configured properly (missing API_TOKEN).")
        return  # w dev przepuszczamy

    if cred is None or cred.scheme.lower() != "bearer" or not cred.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    if cred.credentials != API_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token")

    # token poprawny — przepuszczamy


# --- Modele ---
class AgentResponse(BaseModel):
    agent: str
    query: str
    result: Union[str, Dict, List, None]


def _ctx(refresh: bool) -> Dict[str, str]:
    """Kontekst do cache refresh"""
    return {"refresh": "1" if refresh else "0"}


# --- Endpointy ---
@app.get("/api/health")
def health():
    """Endpoint health-check (bez autoryzacji, potrzebny Heroku)"""
    return {"status": "ok"}


def _call_agent(agent_name: str, fn, q: str, refresh_int: Optional[int]):
    """Helper do wywoływania agentów"""
    refresh = bool(refresh_int)
    res = fn(q, context=_ctx(refresh))
    return AgentResponse(agent=agent_name, query=q, result=res)


# --- Endpointy zabezpieczone tokenem ---
@app.get("/api/ask", response_model=AgentResponse, dependencies=[Depends(require_bearer_token)])
def api_ask(q: str = Query(...), refresh: Optional[int] = 0):
    return _call_agent("operations_agent", operations_fn, q, refresh)


@app.get("/api/staff", response_model=AgentResponse, dependencies=[Depends(require_bearer_token)])
def api_staff(q: str = Query(...), refresh: Optional[int] = 0):
    return _call_agent("staff_directory_agent", staff_fn, q, refresh)


@app.get("/api/cameras", response_model=AgentResponse, dependencies=[Depends(require_bearer_token)])
def api_cameras(q: str = Query(...), refresh: Optional[int] = 0):
    return _call_agent("camera_agent", camera_fn, q, refresh)


@app.get("/api/doors", response_model=AgentResponse, dependencies=[Depends(require_bearer_token)])
def api_doors(q: str = Query(...), refresh: Optional[int] = 0):
    return _call_agent("doors_agent", doors_fn, q, refresh)
