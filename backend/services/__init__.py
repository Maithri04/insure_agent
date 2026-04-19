# services/__init__.py
# InsureMind AI — Services Module Exports

from services.soap_service import generate_soap_note

from services.audit_service import (
    save_audit_log,
    mark_submitted,
    get_history,
    get_by_request_id,
    get_stats,
)

__all__ = [
    # SOAP
    "generate_soap_note",
    # Audit
    "save_audit_log",
    "mark_submitted",
    "get_history",
    "get_by_request_id",
    "get_stats",
]