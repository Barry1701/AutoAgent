# app.py — FastAPI dla AutoAgenta (imports z autoagent/agents/)
import os
from typing import Optional
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

# 🔹 TESTOWO pozwalamy na wszystkie hosty (żeby Gitpod nie blokował)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <- każdy host dozwolony
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AgentResponse(BaseModel):
    agent: str
    query: str
    result: str | dict | list | None

def _ctx(refresh: bool) -> dict:
    # Twoje agenty używają context={"refresh": "1"/"0"}
    return {"refresh": "1" if refresh else "0"}

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/ask", response_model=AgentResponse)
def api_ask(q: str = Query(...), refresh: Optional[int] = 0):
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
