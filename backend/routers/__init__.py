# routers/__init__.py
# InsureMind AI — Routers Module

from routers.soap    import router as soap_router
from routers.agent   import router as agent_router
from routers.analyze import router as analyze_router
from routers.form    import router as form_router
from routers.submit  import router as submit_router

__all__ = [
    "soap_router",
    "agent_router",
    "analyze_router",
    "form_router",
    "submit_router",
]