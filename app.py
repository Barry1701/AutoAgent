# app.py — FastAPI dla AutoAgenta
import os
from typing import Optional, Union, Dict, List
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# <<< KLUCZOWE: importy zgodne z Twoim układem katalogów >>>
from autoagent.agents.operations_agent import operations_agent as operations_fn
from autoagent.agents.staff_directory_agent import staff_directory_agent as staff_fn
from autoagent.agents.camera_agent import camera_agent as camera_fn
from autoagent.agents.doors_agent import doors_agent as doors_fn
# <<< ---------------------------------------------------- >>>

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

app = FastAPI(title="AutoAgent API", version="0.1.0")

# ── CORS: localhost i każdy workspace Gitpod ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_origin_regex=r"^https://.*\.gitpod\.io$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AgentResponse(BaseModel):
    agent: str
    query: str
    result: Union[str, Dict, List, None]

def _ctx(refresh: bool) -> Dict[str, str]:
    return {"refresh": "1" if refresh else "0"}

@app.get("/api/health")
def health():
    return {"status": "ok"}

# ── Mały wrapper, żeby wszystkie endpointy były spójne i łapały wyjątki ──
def _call_agent(agent_name: str, fn, q: str, refresh_int: Optional[int]):
    refresh = bool(refresh_int)
    res = fn(q, context=_ctx(refresh))
    return AgentResponse(agent=agent_name, query=q, result=res)

@app.get("/api/ask", response_model=AgentResponse)
def api_ask(q: str = Query(...), refresh: Optional[int] = 0):
<<<<<<< HEAD
    res = operations_fn(q, context=_ctx(bool(refresh)))
    return AgentResponse(agent="operations_agent", query=q, result=res)

@app.get("/api/staff", response_model=AgentResponse)
def api_staff(q: str = Query(...), refresh: Optional[int] = 0):
    res = staff_fn(q, context=_ctx(bool(refresh)))
    return AgentResponse(agent="staff_directory_agent", query=q, result=res)

@app.get("/api/cameras", response_model=AgentResponse)
def api_cameras(q: str = Query(...), refresh: Optional[int] = 0):
    res = camera_fn(q, context=_ctx(bool(refresh)))
    return AgentResponse(agent="camera_agent", query=q, result=res)

@app.get("/api/doors", response_model=AgentResponse)
def api_doors(q: str = Query(...), refresh: Optional[int] = 0):
    res = doors_fn(q, context=_ctx(bool(refresh)))
    return AgentResponse(agent="doors_agent", query=q, result=res)
=======
    return _call_agent("operations_agent", operations_mod.operations_agent, q, refresh)

@app.get("/api/staff", response_model=AgentResponse)
def api_staff(q: str = Query(...), refresh: Optional[int] = 0):
    # UWAGA: wywołujemy funkcję z modułu staff_mod
    return _call_agent("staff_directory_agent", staff_mod.staff_directory_agent, q, refresh)

@app.get("/api/cameras", response_model=AgentResponse)
def api_cameras(q: str = Query(...), refresh: Optional[int] = 0):
    return _call_agent("camera_agent", camera_mod.camera_agent, q, refresh)

@app.get("/api/doors", response_model=AgentResponse)
def api_doors(q: str = Query(...), refresh: Optional[int] = 0):
    return _call_agent("doors_agent", doors_mod.doors_agent, q, refresh)
>>>>>>> 8ee3701 (add changes before pull)
