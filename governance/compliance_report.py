"""Generate compliance reports from audit logs."""

from __future__ import annotations

from governance.audit_logger import AuditLogger


def generate_session_report(logger: AuditLogger) -> str:
    return logger.generate_compliance_report()
