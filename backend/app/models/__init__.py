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
    PatientAlert,
    PatientFamily,
    AlignerTreatment,
    AlignerTrayLog,
    ElasticPrescription,
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

from app.models.communications import (  # noqa: F401
    CommunicationPreference,
    MessageTemplate,
    MessageLog,
    ScheduledMessage,
)

from app.models.imaging import (  # noqa: F401
    ImagingSeries,
    PatientImage,
    ImagingAlert,
)

from app.models.portal import (  # noqa: F401
    PortalAccount,
    PortalForm,
    PortalFormSubmission,
    PortalMessage,
    ReportSnapshot,
    MigrationJob,
    TeamInvite,
)

from app.models.timetracking import (  # noqa: F401
    TimeEntry,
    PayRate,
    PayrollPeriod,
)

from app.models.appliance_tracking import (  # noqa: F401
    Lab,
    AppliancePrescription,
    ApplianceStatusHistory,
    EasyRxIntegration,
)

from app.models.cdt_codes import (  # noqa: F401
    CDTCode,
    AppointmentTypeTemplate,
)

from app.models.restorative import (  # noqa: F401
    RestorativeChart,
    ToothRestoration,
)

from app.models.workflow import (  # noqa: F401
    PatientVisitStatus,
    RecentPatientSearch,
    PatientDocument,
)

from app.models.messaging import (  # noqa: F401
    ChatRoom,
    ChatRoomMember,
    ChatMessage,
)

from app.models.perio import (  # noqa: F401
    PerioExam,
    PerioReading,
)

from app.models.recall import HygieneRecall  # noqa: F401
