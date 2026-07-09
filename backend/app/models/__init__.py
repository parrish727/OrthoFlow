"""OrthoFlow models — all tables must be imported here for Alembic to detect them."""
from app.models.models import (  # noqa: F401
    Practice,
    User,
    Invoice,
    LineItem,
    AuditLog,
    Integration,
    OtpCode,
)
from app.models.clinical import (  # noqa: F401
    Patient,
    Chair,
    DentalAssistant,
    Appointment,
    TreatmentNote,
    ToothChart,
)

# Also import claims if they exist
try:
    from app.models.claims import (  # noqa: F401
        InsuranceClaim,
        PriorAuthorization,
        PracticePayerConfig,
    )
except ImportError:
    pass

from app.models.finance import (  # noqa: F401
    InsuranceSubscriber,
    PatientLedgerEntry,
    ClaimLineItem,
    PaymentPosting,
)
