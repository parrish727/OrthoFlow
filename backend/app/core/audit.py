"""HIPAA audit logging — every data access and modification must be logged."""
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import AuditLog


async def audit_log(
    db: AsyncSession,
    practice_id: str,
    user_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: str | None = None,
    ip_address: str | None = None,
) -> None:
    """Write an audit log entry. Call this on every data access/modification.

    Actions should follow the pattern: "resource.verb"
    Examples: "invoice.view", "invoice.approve", "invoice.upload", "user.login", "user.login_failed"
    """
    entry = AuditLog(
        practice_id=practice_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(entry)
    # Flush immediately so audit log is persisted even if the main transaction fails
    await db.flush()
