"""Seed demo data for patient flow, today's schedule, and staff messaging.
Run via: docker compose exec backend python -m app.seeds.demo_flow
"""
import asyncio
import uuid
from datetime import datetime, date, time, timezone, timedelta
from decimal import Decimal

from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.models import User, Practice
from app.models.clinical import Patient, Appointment, Chair, DentalAssistant
from app.models.workflow import PatientVisitStatus
from app.models.messaging import ChatRoom, ChatRoomMember
from app.models.communications import MessageLog
from app.models.portal import PortalAccount, PortalForm, PortalMessage

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

DEMO_PRACTICE_ID = uuid.UUID("82fe9d87-6250-4b15-ac7d-26de094a4be8")
# Use Eastern time for "today" since the practice is in US Eastern timezone
_eastern_offset = timedelta(hours=-4)  # EDT
_now_eastern = datetime.now(timezone(_eastern_offset))
TODAY = _now_eastern.date()

# Demo patients for the visit tracker
DEMO_PATIENTS = [
    {"first_name": "Priscilla", "last_name": "Knowles", "dob": date(1992, 4, 15), "phone": "(414) 555-0200", "email": "priscilla.knowles@melanin-tech.com", "phase": "active", "middle_name": "Marie", "gender": "female", "responsible_party": None, "address": "742 Evergreen Terrace, Milwaukee, WI 53202"},
    {"first_name": "Marcus", "last_name": "Johnson", "dob": date(2010, 3, 15), "phone": "(414) 555-0101", "email": "marcus.j@example.com", "phase": "active"},
    {"first_name": "Aaliyah", "last_name": "Washington", "dob": date(2008, 7, 22), "phone": "(414) 555-0102", "email": "aaliyah.w@example.com", "phase": "bonding"},
    {"first_name": "Devon", "last_name": "Brooks", "dob": date(2012, 11, 8), "phone": "(414) 555-0103", "email": "devon.b@example.com", "phase": "observation_1"},
    {"first_name": "Jasmine", "last_name": "Carter", "dob": date(2009, 5, 30), "phone": "(414) 555-0104", "email": "jasmine.c@example.com", "phase": "finishing"},
    {"first_name": "Tyler", "last_name": "Robinson", "dob": date(2011, 1, 12), "phone": "(414) 555-0105", "email": "tyler.r@example.com", "phase": "active"},
    {"first_name": "Imani", "last_name": "Williams", "dob": date(2007, 9, 3), "phone": "(414) 555-0106", "email": "imani.w@example.com", "phase": "retention"},
    {"first_name": "Elijah", "last_name": "Davis", "dob": date(2013, 4, 18), "phone": "(414) 555-0107", "email": "elijah.d@example.com", "phase": "consultation"},
    {"first_name": "Zara", "last_name": "Thompson", "dob": date(2010, 12, 25), "phone": "(414) 555-0108", "email": "zara.t@example.com", "phase": "active"},
    {"first_name": "Kai", "last_name": "Anderson", "dob": date(2014, 6, 7), "phone": "(414) 555-0109", "email": "kai.a@example.com", "phase": "records"},
    {"first_name": "Nia", "last_name": "Harris", "dob": date(2009, 2, 14), "phone": "(414) 555-0110", "email": "nia.h@example.com", "phase": "active"},
]

# Chairs for the practice
DEMO_CHAIRS = [
    {"name": "Chair 1", "color": "#3B82F6", "sort_order": 1},
    {"name": "Chair 2", "color": "#10B981", "sort_order": 2},
    {"name": "Chair 3", "color": "#F59E0B", "sort_order": 3},
    {"name": "Chair 4", "color": "#8B5CF6", "sort_order": 4},
]

# Dental assistants
DEMO_DAS = [
    {"first_name": "Mike", "last_name": "Torres", "color": "#10B981"},
    {"first_name": "Keisha", "last_name": "Brown", "color": "#F59E0B"},
]

# Today's appointment schedule
DEMO_APPOINTMENTS = [
    {"patient_idx": 1, "start": time(8, 0), "end": time(8, 20), "duration": 20, "type": "Adjustment", "status": "completed", "chair_idx": 0, "da_idx": 0},
    {"patient_idx": 2, "start": time(8, 30), "end": time(9, 30), "duration": 60, "type": "Bonding", "status": "in_progress", "chair_idx": 1, "da_idx": 1},
    {"patient_idx": 3, "start": time(9, 0), "end": time(9, 20), "duration": 20, "type": "Observation", "status": "checked_in", "chair_idx": None, "da_idx": None},
    {"patient_idx": 4, "start": time(9, 30), "end": time(9, 50), "duration": 20, "type": "Adjustment", "status": "checked_in", "chair_idx": None, "da_idx": 0},
    {"patient_idx": 5, "start": time(10, 0), "end": time(10, 20), "duration": 20, "type": "Adjustment", "status": "scheduled", "chair_idx": 2, "da_idx": 0},
    {"patient_idx": 6, "start": time(10, 30), "end": time(10, 50), "duration": 20, "type": "Retainer Check", "status": "scheduled", "chair_idx": 3, "da_idx": 1},
    {"patient_idx": 7, "start": time(11, 0), "end": time(11, 45), "duration": 45, "type": "Ortho Consultation", "status": "scheduled", "chair_idx": 0, "da_idx": None},
    {"patient_idx": 8, "start": time(13, 0), "end": time(13, 20), "duration": 20, "type": "Adjustment", "status": "scheduled", "chair_idx": 1, "da_idx": 0},
    {"patient_idx": 9, "start": time(13, 30), "end": time(14, 30), "duration": 60, "type": "Records Appointment", "status": "scheduled", "chair_idx": 2, "da_idx": 1},
    {"patient_idx": 0, "start": time(14, 30), "end": time(14, 50), "duration": 20, "type": "Adjustment", "status": "scheduled", "chair_idx": 3, "da_idx": 0},
    {"patient_idx": 10, "start": time(15, 0), "end": time(15, 20), "duration": 20, "type": "Adjustment", "status": "scheduled", "chair_idx": 0, "da_idx": 1},
]

# Visit statuses for the Patient Flow board
# patient_idx, status, minutes_ago_checked_in, minutes_ago_seated
DEMO_VISITS = [
    (1, "dismissed", 90, 75),   # Marcus — already done
    (2, "seated", 45, 30),  # Aaliyah — in chair being bonded
    (3, "lobby", 15, None),     # Devon — lobby, waiting
    (4, "lobby", 5, None),      # Jasmine — lobby, just arrived
]


# ═══════════════════════════════════════════════════════════════════════════════
# SEED FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


async def seed_chairs(db) -> list:
    """Create demo chairs (idempotent)."""
    chairs = []
    for ch in DEMO_CHAIRS:
        result = await db.execute(
            select(Chair).where(
                Chair.practice_id == DEMO_PRACTICE_ID,
                Chair.name == ch["name"],
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            chairs.append(existing)
        else:
            chair = Chair(
                id=uuid.uuid4(),
                practice_id=DEMO_PRACTICE_ID,
                name=ch["name"],
                color=ch["color"],
                sort_order=ch["sort_order"],
                is_active=True,
            )
            db.add(chair)
            chairs.append(chair)
    await db.flush()
    print(f"  ✅ Chairs: {len(chairs)} ready")
    return chairs


async def seed_dental_assistants(db) -> list:
    """Create demo DAs (idempotent)."""
    das = []
    for da_data in DEMO_DAS:
        result = await db.execute(
            select(DentalAssistant).where(
                DentalAssistant.practice_id == DEMO_PRACTICE_ID,
                DentalAssistant.first_name == da_data["first_name"],
                DentalAssistant.last_name == da_data["last_name"],
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            das.append(existing)
        else:
            da = DentalAssistant(
                id=uuid.uuid4(),
                practice_id=DEMO_PRACTICE_ID,
                first_name=da_data["first_name"],
                last_name=da_data["last_name"],
                color=da_data["color"],
                is_active=True,
            )
            db.add(da)
            das.append(da)
    await db.flush()
    print(f"  ✅ Dental Assistants: {len(das)} ready")
    return das


async def seed_patients(db) -> list:
    """Create demo patients (idempotent by first_name + last_name + practice)."""
    patients = []
    for p_data in DEMO_PATIENTS:
        result = await db.execute(
            select(Patient).where(
                Patient.practice_id == DEMO_PRACTICE_ID,
                Patient.first_name == p_data["first_name"],
                Patient.last_name == p_data["last_name"],
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            # Update demographic fields if seed has new data the DB doesn't
            if p_data.get("middle_name") and not existing.middle_name:
                existing.middle_name = p_data["middle_name"]
            if p_data.get("gender") and not existing.gender:
                existing.gender = p_data["gender"]
            if p_data.get("address") and not existing.address:
                existing.address = p_data["address"]
            if p_data.get("responsible_party") and not existing.responsible_party:
                existing.responsible_party = p_data["responsible_party"]
            patients.append(existing)
        else:
            patient = Patient(
                id=uuid.uuid4(),
                practice_id=DEMO_PRACTICE_ID,
                first_name=p_data["first_name"],
                middle_name=p_data.get("middle_name"),
                last_name=p_data["last_name"],
                date_of_birth=p_data["dob"],
                gender=p_data.get("gender"),
                phone=p_data["phone"],
                email=p_data["email"],
                address=p_data.get("address"),
                responsible_party=p_data.get("responsible_party"),
                status="active",
                treatment_phase=p_data["phase"],
            )
            db.add(patient)
            patients.append(patient)
    await db.flush()
    print(f"  ✅ Patients: {len(patients)} ready")
    return patients


async def seed_appointments(db, patients: list, chairs: list, das: list) -> list:
    """Create today's appointment schedule (idempotent by patient + date + time)."""
    # Get a user to use as created_by
    result = await db.execute(
        select(User).where(User.practice_id == DEMO_PRACTICE_ID, User.role == "front_desk")
    )
    front_desk_user = result.scalar_one_or_none()
    created_by = front_desk_user.id if front_desk_user else None

    appointments = []
    for appt_data in DEMO_APPOINTMENTS:
        patient = patients[appt_data["patient_idx"]]

        # Check if appointment already exists for this patient at this time today
        result = await db.execute(
            select(Appointment).where(
                Appointment.practice_id == DEMO_PRACTICE_ID,
                Appointment.patient_id == patient.id,
                Appointment.appointment_date == TODAY,
                Appointment.start_time == appt_data["start"],
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            appointments.append(existing)
        else:
            chair_id = chairs[appt_data["chair_idx"]].id if appt_data["chair_idx"] is not None else None
            da_id = das[appt_data["da_idx"]].id if appt_data["da_idx"] is not None else None

            appt = Appointment(
                id=uuid.uuid4(),
                practice_id=DEMO_PRACTICE_ID,
                patient_id=patient.id,
                chair_id=chair_id,
                da_id=da_id,
                appointment_date=TODAY,
                start_time=appt_data["start"],
                end_time=appt_data["end"],
                duration_minutes=appt_data["duration"],
                status=appt_data["status"],
                appointment_type=appt_data["type"],
                created_by=created_by,
            )
            db.add(appt)
            appointments.append(appt)

    await db.flush()
    print(f"  ✅ Appointments: {len(appointments)} on today's schedule")
    return appointments


async def seed_visit_statuses(db, patients: list, appointments: list, chairs: list) -> None:
    """Populate the patient flow board with visit statuses."""
    now = datetime.now(timezone.utc)

    for patient_idx, visit_status, mins_checkin, mins_seated in DEMO_VISITS:
        patient = patients[patient_idx]
        # Find matching appointment
        matching_appt = None
        for appt in appointments:
            if appt.patient_id == patient.id:
                matching_appt = appt
                break
        if not matching_appt:
            continue

        # Check if visit status already exists for this appointment
        result = await db.execute(
            select(PatientVisitStatus).where(
                PatientVisitStatus.appointment_id == matching_appt.id,
            )
        )
        if result.scalar_one_or_none():
            continue

        checked_in_at = now - timedelta(minutes=mins_checkin)
        seated_at = (now - timedelta(minutes=mins_seated)) if mins_seated else None
        checked_out_at = (now - timedelta(minutes=5)) if visit_status == "dismissed" else None

        # Assign a chair for seated/in_treatment/checked_out patients
        chair_id = None
        if visit_status in ("seated", "checked_out", "dismissed"):
            chair_id = chairs[patient_idx % len(chairs)].id

        visit = PatientVisitStatus(
            id=uuid.uuid4(),
            practice_id=DEMO_PRACTICE_ID,
            patient_id=patient.id,
            appointment_id=matching_appt.id,
            status=visit_status,
            chair_id=chair_id,
            checked_in_at=checked_in_at,
            seated_at=seated_at,
            checked_out_at=checked_out_at,
            created_at=checked_in_at,
        )
        db.add(visit)

    await db.flush()
    print(f"  ✅ Visit statuses: {len(DEMO_VISITS)} patients on flow board")


async def seed_staff_messaging(db) -> None:
    """Create staff chat rooms with demo conversations."""
    # Get demo users
    result = await db.execute(
        select(User).where(User.practice_id == DEMO_PRACTICE_ID)
    )
    users = result.scalars().all()
    if len(users) < 3:
        print("  ⚠️  Not enough demo users for messaging seed (need 3+)")
        return

    user_map = {u.role: u for u in users}
    doctor = user_map.get("doctor") or user_map.get("owner")
    manager = user_map.get("office_manager")
    da = user_map.get("dental_assistant")
    front_desk = user_map.get("front_desk")

    if not all([doctor, manager, da]):
        print("  ⚠️  Missing required roles for messaging seed")
        return

    # Check if demo rooms already exist
    result = await db.execute(
        select(ChatRoom).where(
            ChatRoom.practice_id == DEMO_PRACTICE_ID,
            ChatRoom.name == "Morning Huddle",
        )
    )
    if result.scalar_one_or_none():
        print("  ✅ Staff messaging: already seeded")
        return

    # Create chat rooms
    now = datetime.now(timezone.utc)

    # Room 1: Morning Huddle (all staff)
    huddle_room = ChatRoom(
        id=uuid.uuid4(),
        practice_id=DEMO_PRACTICE_ID,
        name="Morning Huddle",
        room_type="group",
        created_by=manager.id,
        created_at=now - timedelta(hours=2),
    )
    db.add(huddle_room)
    await db.flush()

    all_staff = [u for u in [doctor, manager, da, front_desk] if u]
    for user in all_staff:
        db.add(ChatRoomMember(
            id=uuid.uuid4(),
            room_id=huddle_room.id,
            user_id=user.id,
            joined_at=now - timedelta(hours=2),
        ))

    # Room 2: Doctor + DA direct
    da_room = ChatRoom(
        id=uuid.uuid4(),
        practice_id=DEMO_PRACTICE_ID,
        name="Dr. Williams & Mike",
        room_type="direct",
        created_by=doctor.id,
        created_at=now - timedelta(days=1),
    )
    db.add(da_room)
    await db.flush()

    for user in [doctor, da]:
        db.add(ChatRoomMember(
            id=uuid.uuid4(),
            room_id=da_room.id,
            user_id=user.id,
            joined_at=now - timedelta(days=1),
        ))

    await db.flush()
    print("  ✅ Staff messaging: 2 rooms ready (AI auto-reply active for demo)")


async def seed_patient_messages(db, patients: list) -> None:
    """Seed outbound/inbound patient communication logs for demo."""
    now = datetime.now(timezone.utc)

    # Check if messages already exist
    result = await db.execute(
        select(MessageLog).where(
            MessageLog.practice_id == DEMO_PRACTICE_ID,
        ).limit(1)
    )
    if result.scalar_one_or_none():
        print("  ✅ Patient messages: already seeded")
        return

    messages_data = [
        # (patient_idx, direction, channel, to_address, subject, body, status, hours_ago)
        (0, "outbound", "sms", "(414) 555-0101", None,
         "Hi Marcus! This is a reminder for your orthodontic appointment tomorrow at 8:00 AM. Reply Y to confirm.", "delivered", 24),
        (0, "inbound", "sms", "(414) 555-0101", None,
         "Y", "received", 23),
        (1, "outbound", "email", "aaliyah.w@example.com", "Appointment Reminder — Brightsmile Orthodontics",
         "Dear Aaliyah, This is a reminder for your bonding appointment tomorrow at 8:30 AM. Please arrive 10 minutes early. We're excited for your big day! — Brightsmile Team",
         "delivered", 24),
        (1, "outbound", "sms", "(414) 555-0102", None,
         "Aaliyah — reminder: bonding appointment tomorrow 8:30 AM! Please don't eat anything sticky beforehand 🦷",
         "delivered", 20),
        (2, "outbound", "sms", "(414) 555-0103", None,
         "Hi! Devon has an observation appointment tomorrow at 9:00 AM with Dr. Williams. Reply Y to confirm.",
         "delivered", 24),
        (2, "inbound", "sms", "(414) 555-0103", None,
         "Y confirmed! His mom wants to talk about when braces start",
         "received", 22),
        (3, "outbound", "sms", "(414) 555-0104", None,
         "Jasmine — reminder: adjustment appointment tomorrow at 9:30 AM. See you soon!",
         "delivered", 24),
        (5, "outbound", "sms", "(414) 555-0106", None,
         "Hi Imani! Time for your retainer check. Your appointment is scheduled for today at 10:30 AM.",
         "delivered", 4),
        (6, "outbound", "email", "elijah.d@example.com", "Welcome to Brightsmile Orthodontics!",
         "Dear Elijah's family, We're looking forward to meeting you for your consultation appointment today at 11:00 AM. Please bring any dental records or x-rays you may have. — Dr. Williams & Team",
         "delivered", 18),
        (7, "outbound", "sms", "(414) 555-0108", None,
         "Zara — your 1:00 PM adjustment is confirmed for today. See you this afternoon!",
         "delivered", 3),
    ]

    for patient_idx, direction, channel, to_addr, subject, body, msg_status, hours_ago in messages_data:
        patient = patients[patient_idx]
        db.add(MessageLog(
            id=uuid.uuid4(),
            practice_id=DEMO_PRACTICE_ID,
            patient_id=patient.id,
            direction=direction,
            channel=channel,
            to_address=to_addr,
            subject=subject,
            body=body,
            status=msg_status,
            delivered_at=(now - timedelta(hours=hours_ago)) if msg_status == "delivered" else None,
            created_at=now - timedelta(hours=hours_ago),
        ))

    await db.flush()
    print(f"  ✅ Patient messages: {len(messages_data)} communication log entries")


async def seed_portal_forms(db) -> list:
    """Create intake, consent, and health history forms for MyOrthoChart."""
    result = await db.execute(
        select(PortalForm).where(PortalForm.practice_id == DEMO_PRACTICE_ID).limit(1)
    )
    if result.scalar_one_or_none():
        print("  ✅ Portal forms: already seeded")
        return []

    forms_data = [
        {
            "name": "New Patient Intake Form",
            "form_type": "intake",
            "description": "Required for all new patients before their first appointment",
            "is_required_new_patient": True,
            "fields": [
                {"name": "patient_name", "label": "Patient Full Name", "type": "text", "required": True},
                {"name": "date_of_birth", "label": "Date of Birth", "type": "date", "required": True},
                {"name": "parent_guardian", "label": "Parent/Guardian Name (if minor)", "type": "text", "required": False},
                {"name": "address", "label": "Home Address", "type": "textarea", "required": True},
                {"name": "phone", "label": "Phone Number", "type": "tel", "required": True},
                {"name": "email", "label": "Email Address", "type": "email", "required": True},
                {"name": "emergency_contact", "label": "Emergency Contact Name", "type": "text", "required": True},
                {"name": "emergency_phone", "label": "Emergency Contact Phone", "type": "tel", "required": True},
                {"name": "insurance_provider", "label": "Insurance Provider", "type": "text", "required": False},
                {"name": "insurance_id", "label": "Insurance ID Number", "type": "text", "required": False},
                {"name": "referred_by", "label": "How did you hear about us?", "type": "select", "required": False,
                 "options": ["Google", "Referral from dentist", "Friend/Family", "Social Media", "Other"]},
            ],
        },
        {
            "name": "Medical & Dental History",
            "form_type": "health_history",
            "description": "Please provide your complete medical and dental history",
            "is_required_new_patient": True,
            "fields": [
                {"name": "general_dentist", "label": "General Dentist Name", "type": "text", "required": False},
                {"name": "last_dental_visit", "label": "Date of Last Dental Visit", "type": "date", "required": False},
                {"name": "allergies", "label": "Known Allergies (medications, latex, etc.)", "type": "textarea", "required": False},
                {"name": "medications", "label": "Current Medications", "type": "textarea", "required": False},
                {"name": "medical_conditions", "label": "Medical Conditions", "type": "checkbox_group", "required": False,
                 "options": ["Asthma", "Diabetes", "Heart condition", "Seizures", "Bleeding disorder", "None"]},
                {"name": "previous_ortho", "label": "Have you had orthodontic treatment before?", "type": "select", "required": True,
                 "options": ["No", "Yes - braces", "Yes - Invisalign", "Yes - other"]},
                {"name": "chief_concern", "label": "What brings you in today? (chief concern)", "type": "textarea", "required": True},
                {"name": "habits", "label": "Does the patient have any of these habits?", "type": "checkbox_group", "required": False,
                 "options": ["Thumb sucking", "Mouth breathing", "Nail biting", "Teeth grinding", "None"]},
            ],
        },
        {
            "name": "Informed Consent for Treatment",
            "form_type": "consent",
            "description": "Consent for orthodontic examination and treatment",
            "is_required_new_patient": True,
            "fields": [
                {"name": "consent_exam", "label": "I consent to an orthodontic examination including x-rays and photographs", "type": "checkbox", "required": True},
                {"name": "consent_treatment", "label": "I understand that treatment results cannot be guaranteed and that treatment time is an estimate", "type": "checkbox", "required": True},
                {"name": "consent_risks", "label": "I have been informed of the risks of orthodontic treatment including root resorption, decalcification, and gum disease", "type": "checkbox", "required": True},
                {"name": "consent_cooperation", "label": "I understand that my cooperation (wearing elastics, keeping appointments, oral hygiene) directly affects treatment outcome", "type": "checkbox", "required": True},
                {"name": "consent_financial", "label": "I understand my financial responsibility as outlined in the treatment agreement", "type": "checkbox", "required": True},
                {"name": "signature", "label": "Patient/Guardian Signature", "type": "signature", "required": True},
                {"name": "signature_date", "label": "Date", "type": "date", "required": True},
            ],
        },
        {
            "name": "Financial Agreement",
            "form_type": "financial",
            "description": "Payment plan agreement and financial policy acknowledgment",
            "is_required_new_patient": False,
            "fields": [
                {"name": "responsible_party", "label": "Financially Responsible Party Name", "type": "text", "required": True},
                {"name": "relationship", "label": "Relationship to Patient", "type": "select", "required": True,
                 "options": ["Self", "Parent", "Guardian", "Spouse", "Other"]},
                {"name": "payment_method", "label": "Preferred Payment Method", "type": "select", "required": True,
                 "options": ["Monthly auto-pay", "Pay in full", "Insurance + monthly", "Third-party financing"]},
                {"name": "acknowledge_policy", "label": "I acknowledge and agree to the office financial policy including cancellation fees and missed appointment charges", "type": "checkbox", "required": True},
                {"name": "signature", "label": "Signature", "type": "signature", "required": True},
            ],
        },
    ]

    forms = []
    for f_data in forms_data:
        form = PortalForm(
            id=uuid.uuid4(),
            practice_id=DEMO_PRACTICE_ID,
            name=f_data["name"],
            form_type=f_data["form_type"],
            description=f_data["description"],
            fields=f_data["fields"],
            is_active=True,
            is_required_new_patient=f_data["is_required_new_patient"],
            version=1,
        )
        db.add(form)
        forms.append(form)

    await db.flush()
    print(f"  ✅ Portal forms: {len(forms)} created (intake, health history, consent, financial)")
    return forms


async def seed_portal_accounts(db, patients: list) -> list:
    """Create MyOrthoChart patient portal accounts for demo patients."""
    from app.core.auth import hash_password

    result = await db.execute(
        select(PortalAccount).where(PortalAccount.practice_id == DEMO_PRACTICE_ID).limit(1)
    )
    if result.scalar_one_or_none():
        print("  ✅ Portal accounts: already seeded")
        return []

    # Create portal accounts for the first 6 patients (representing active portal users)
    # First patient (Marcus) gets the branded demo login for client presentations
    DEMO_PATIENT_EMAIL = "priscilla.knowles@melanin-tech.com"
    DEMO_PATIENT_PASSWORD = "Demo2026!"

    accounts = []
    for i, patient in enumerate(patients[:6]):
        if not patient.email:
            continue

        email = DEMO_PATIENT_EMAIL if i == 0 else patient.email
        password = DEMO_PATIENT_PASSWORD if i == 0 else "Patient2026!"

        account = PortalAccount(
            id=uuid.uuid4(),
            practice_id=DEMO_PRACTICE_ID,
            patient_id=patient.id,
            email=email,
            password_hash=hash_password(password),
            is_active=True,
            is_verified=True,
            last_login=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.add(account)
        accounts.append(account)

    await db.flush()
    print(f"  ✅ Portal accounts: {len(accounts)} patients can log into MyOrthoChart")
    print(f"     Demo patient login: {DEMO_PATIENT_EMAIL} / {DEMO_PATIENT_PASSWORD}")
    return accounts


async def seed_portal_messages(db, patients: list) -> None:
    """Seed MyOrthoChart inbox with patient↔office conversations."""
    result = await db.execute(
        select(PortalMessage).where(PortalMessage.practice_id == DEMO_PRACTICE_ID).limit(1)
    )
    if result.scalar_one_or_none():
        print("  ✅ Portal messages: already seeded")
        return

    # Get a staff user for sent_by_staff
    result = await db.execute(
        select(User).where(User.practice_id == DEMO_PRACTICE_ID, User.role == "office_manager")
    )
    manager = result.scalar_one_or_none()
    staff_id = manager.id if manager else None

    now = datetime.now(timezone.utc)

    conversations = [
        # Priscilla — asking about treatment timeline
        (0, [
            ("from_patient", "Treatment timeline question", "Hi! I was wondering how much longer I have in my active treatment phase. My teeth are looking great and I'm hoping to be done by the holidays. Is that realistic?", 36),
            ("to_patient", "Re: Treatment timeline question", "Hi Priscilla! You're making excellent progress. Based on your last visit, I'd estimate 3-4 more months of active treatment before we move to retention. The holidays are definitely a realistic goal! We'll confirm at your next adjustment.", 34),
            ("from_patient", "Re: Treatment timeline question", "That's amazing news! Thank you so much, I can't wait 😊", 33),
        ]),
        # Marcus — asking about elastics
        (1, [
            ("from_patient", "Elastics question", "Hi! My elastics keep snapping — am I supposed to double them up or just replace with a new one?", 48),
            ("to_patient", "Re: Elastics question", "Hi Marcus! Just replace with a fresh elastic — no need to double up. If they're snapping more than 2-3 times a day, try opening your mouth a bit less wide when yawning. See you at your next adjustment!", 46),
            ("from_patient", "Re: Elastics question", "Got it, thanks! See you next week 👍", 45),
        ]),
        # Aaliyah — excited about bonding day
        (2, [
            ("to_patient", "Your bonding appointment tomorrow!", "Hi Aaliyah! Just a reminder that your bonding appointment is tomorrow at 8:30 AM. Please brush well before coming in, and avoid eating anything sticky. This is an exciting day — you're officially starting your smile journey! 🎉", 24),
            ("from_patient", "Re: Your bonding appointment tomorrow!", "Thank you!! I'm so excited!! My mom and I will be there early. Quick question — can I still play flute with braces?", 22),
            ("to_patient", "Re: Your bonding appointment tomorrow!", "Great question! Yes, you can absolutely still play flute. It might feel a little different for the first week or two, but you'll adapt quickly. Some patients find orthodontic wax helpful on the front brackets while playing. See you tomorrow!", 20),
        ]),
        # Devon — mom asking about timing
        (3, [
            ("from_patient", "When will Devon need braces?", "Hi Dr. Williams, Devon's mom here. He's been in observation for a while now and I'm wondering when you think he'll be ready for braces. His front teeth are really crooked and kids at school are starting to notice.", 72),
            ("to_patient", "Re: When will Devon need braces?", "Hi Mrs. Brooks! Great question. Devon's growth is tracking well and I want to discuss timing with you at tomorrow's observation appointment. The good news is his jaw growth is favorable — we just want to make sure we start at the optimal time for the best result. Let's chat tomorrow!", 70),
        ]),
        # Jasmine — retainer concern
        (4, [
            ("from_patient", "Retainer feels tight", "My retainer feels really tight when I put it in at night. Is that normal? I haven't worn it for about a week because I forgot to bring it on vacation.", 36),
            ("to_patient", "Re: Retainer feels tight", "Hi Jasmine! It's normal for the retainer to feel tight after not wearing it for a few days — your teeth shift slightly. Please wear it as much as possible for the next few days (not just at night) to get things back on track. If it's painful or doesn't seat fully, call us and we'll get you in. Consistency is key! 😊", 34),
            ("from_patient", "Re: Retainer feels tight", "Ok I'll wear it all day today and tomorrow. It went in ok just felt snug. Thank you!", 33),
        ]),
    ]

    msg_count = 0
    for patient_idx, messages in conversations:
        if patient_idx >= len(patients):
            continue
        patient = patients[patient_idx]
        for direction, subject, body, hours_ago in messages:
            msg = PortalMessage(
                id=uuid.uuid4(),
                practice_id=DEMO_PRACTICE_ID,
                patient_id=patient.id,
                direction=direction,
                subject=subject,
                body=body,
                is_read=True,
                read_at=now - timedelta(hours=hours_ago - 1),
                sent_by_staff=staff_id if direction == "to_patient" else None,
                created_at=now - timedelta(hours=hours_ago),
            )
            db.add(msg)
            msg_count += 1

    await db.flush()
    print(f"  ✅ Portal messages: {msg_count} messages across {len(conversations)} patient conversations")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════


async def seed_insurance_and_claims(db, patients: list) -> None:
    """Seed insurance subscriber records and demo claims for Priscilla Knowles."""
    from app.models.finance import InsuranceSubscriber
    from app.models.claims import InsuranceClaim

    # Find Priscilla
    priscilla = next((p for p in patients if p.first_name == "Priscilla"), None)
    if not priscilla:
        print("  ⚠️ Priscilla not found, skipping insurance seed")
        return

    # Check if already seeded
    existing = await db.execute(
        select(InsuranceSubscriber).where(InsuranceSubscriber.patient_id == priscilla.id)
    )
    if existing.scalar_one_or_none():
        print("  ✅ Insurance: already seeded")
        return

    # Create insurance subscriber
    subscriber = InsuranceSubscriber(
        id=uuid.uuid4(),
        practice_id=DEMO_PRACTICE_ID,
        patient_id=priscilla.id,
        payer_name="Delta Dental of Wisconsin",
        payer_id="DELTA-WI",
        subscriber_id="DDW-9204150001",
        group_number="GRP-MELANIN-2026",
        subscriber_first_name="Priscilla",
        subscriber_last_name="Knowles",
        relationship="self",
        effective_date=date(2025, 1, 1),
        plan_type="PPO",
        plan_name="Delta Dental PPO Plus",
        coverage_type="primary",
    )
    db.add(subscriber)

    # Create demo claims
    demo_claims = [
        {
            "patient_name": "Priscilla Knowles",
            "subscriber_id": "DDW-9204150001",
            "payer_id": "DELTA-WI",
            "payer_type": "commercial",
            "claim_number": "CLM-2026-00142",
            "status": "paid",
            "cdt_codes": [{"code": "D8080", "description": "Comprehensive orthodontic treatment", "fee": 275.00}],
            "total_billed": Decimal("275.00"),
            "total_allowed": Decimal("250.00"),
            "total_paid": Decimal("200.00"),
            "patient_responsibility": Decimal("75.00"),
            "rendering_provider_npi": "1234567890",
            "billing_provider_npi": "1234567890",
            "service_date": date.today() - timedelta(days=30),
            "submission_date": datetime.now(timezone.utc) - timedelta(days=28),
        },
        {
            "patient_name": "Priscilla Knowles",
            "subscriber_id": "DDW-9204150001",
            "payer_id": "DELTA-WI",
            "payer_type": "commercial",
            "claim_number": "CLM-2026-00187",
            "status": "submitted",
            "cdt_codes": [{"code": "D8670", "description": "Periodic orthodontic visit", "fee": 185.00}],
            "total_billed": Decimal("185.00"),
            "total_allowed": None,
            "total_paid": None,
            "patient_responsibility": None,
            "rendering_provider_npi": "1234567890",
            "billing_provider_npi": "1234567890",
            "service_date": date.today() - timedelta(days=5),
            "submission_date": datetime.now(timezone.utc) - timedelta(days=3),
        },
        {
            "patient_name": "Priscilla Knowles",
            "subscriber_id": "DDW-9204150001",
            "payer_id": "DELTA-WI",
            "payer_type": "commercial",
            "claim_number": "CLM-2026-00195",
            "status": "denied",
            "cdt_codes": [{"code": "D0330", "description": "Panoramic radiographic image", "fee": 125.00}],
            "total_billed": Decimal("125.00"),
            "total_allowed": Decimal("0.00"),
            "total_paid": Decimal("0.00"),
            "patient_responsibility": Decimal("125.00"),
            "rendering_provider_npi": "1234567890",
            "billing_provider_npi": "1234567890",
            "service_date": date.today() - timedelta(days=14),
            "submission_date": datetime.now(timezone.utc) - timedelta(days=12),
            "denial_reason": "Service not covered under current plan benefit period",
            "denial_codes": ["CO-96"],
        },
    ]

    for claim_data in demo_claims:
        claim = InsuranceClaim(
            id=uuid.uuid4(),
            practice_id=DEMO_PRACTICE_ID,
            patient_id=str(priscilla.id),
            **claim_data,
        )
        db.add(claim)

    await db.flush()
    print("  ✅ Insurance: 1 subscriber + 3 claims (paid, submitted, denied)")


async def seed_invoices(db) -> None:
    """Seed demo invoices showing AI classification capabilities."""
    from app.models.models import Invoice

    # Check if already seeded
    existing = await db.execute(
        select(Invoice).where(Invoice.practice_id == DEMO_PRACTICE_ID)
    )
    if existing.scalars().first():
        print("  ✅ Invoices: already seeded")
        return

    demo_invoices = [
        {"vendor_name": "Henry Schein Dental", "invoice_number": "INV-87342", "total_amount": 1247.50, "status": "approved", "raw_text": "Ortho brackets (3M Unitek) x20, Arch wires .016 NiTi x10, Elastics mixed bag x5", "coded_json": '{"category": "Clinical Supplies", "gl_code": "5100", "vendor_type": "dental_supply"}', "confidence_score": 0.987, "days_ago": 5},
        {"vendor_name": "Patterson Dental", "invoice_number": "INV-29041", "total_amount": 892.00, "status": "approved", "raw_text": "Composite resin A2 x3, Bonding agent x2, Curing light tips x5", "coded_json": '{"category": "Clinical Supplies", "gl_code": "5100", "vendor_type": "dental_supply"}', "confidence_score": 0.994, "days_ago": 3},
        {"vendor_name": "Benco Dental", "invoice_number": "INV-11205", "total_amount": 3450.00, "status": "pending", "raw_text": "Digital sensor replacement, Phosphor plates x4, Lead aprons x2", "coded_json": '{"category": "Equipment", "gl_code": "5200", "vendor_type": "equipment"}', "confidence_score": 0.972, "days_ago": 1},
        {"vendor_name": "Ormco Corporation", "invoice_number": "INV-55891", "total_amount": 2180.00, "status": "approved", "raw_text": "Damon Q2 brackets upper/lower, Copper NiTi wires assorted, Ligature ties", "coded_json": '{"category": "Orthodontic Supplies", "gl_code": "5110", "vendor_type": "ortho_supply"}', "confidence_score": 0.991, "days_ago": 7},
        {"vendor_name": "Staples Business", "invoice_number": "INV-40221", "total_amount": 156.80, "status": "approved", "raw_text": "Printer paper x5 reams, Toner cartridge HP, Sticky notes, Pens", "coded_json": '{"category": "Office Supplies", "gl_code": "5300", "vendor_type": "office"}', "confidence_score": 0.998, "days_ago": 2},
        {"vendor_name": "Dentsply Sirona", "invoice_number": "INV-77012", "total_amount": 4800.00, "status": "paid", "raw_text": "Primescan AC quarterly maintenance, Calibration service", "coded_json": '{"category": "Equipment Service", "gl_code": "5210", "vendor_type": "equipment_service"}', "confidence_score": 0.985, "days_ago": 10},
    ]

    now = datetime.now(timezone.utc)
    for inv in demo_invoices:
        invoice = Invoice(
            id=uuid.uuid4(),
            practice_id=DEMO_PRACTICE_ID,
            vendor_name=inv["vendor_name"],
            invoice_number=inv["invoice_number"],
            invoice_date=now - timedelta(days=inv["days_ago"]),
            due_date=now + timedelta(days=30 - inv["days_ago"]),
            total_amount=inv["total_amount"],
            status=inv["status"],
            raw_text=inv["raw_text"],
            coded_json=inv["coded_json"],
            confidence_score=inv["confidence_score"],
            created_at=now - timedelta(days=inv["days_ago"]),
        )
        db.add(invoice)

    await db.flush()
    print("  ✅ Invoices: 6 demo invoices (AI classified, 97-99% confidence)")


async def seed_demo_flow():
    """Run all demo flow seeds in order."""
    print("\n🌱 Seeding OrthoFlow demo data...\n")

    # Seed CDT codes and appointment types (independent of practice)
    from app.seeds import seed_cdt_codes, seed_appointment_types
    await seed_cdt_codes()
    await seed_appointment_types()

    async with SessionLocal() as db:
        # Verify practice exists
        result = await db.execute(select(Practice).where(Practice.id == DEMO_PRACTICE_ID))
        practice = result.scalar_one_or_none()
        if not practice:
            print("❌ Demo practice not found. Run demo_accounts seed first.")
            return

        print(f"  Practice: {practice.name}")

        # Clean up stale date-dependent data (appointments/visits from previous days)
        from sqlalchemy import delete, and_
        from app.models.clinical import Appointment
        # First find the stale appointment IDs we're about to delete
        stale_appt_ids_result = await db.execute(
            select(Appointment.id).where(
                and_(
                    Appointment.practice_id == DEMO_PRACTICE_ID,
                    Appointment.appointment_date < TODAY,
                    Appointment.appointment_date > TODAY - timedelta(days=3),
                )
            )
        )
        stale_appt_ids = [row[0] for row in stale_appt_ids_result.fetchall()]

        # Delete visit statuses referencing those appointments first (FK order)
        stale_visits_deleted = 0
        if stale_appt_ids:
            stale_visits = await db.execute(
                delete(PatientVisitStatus).where(
                    PatientVisitStatus.appointment_id.in_(stale_appt_ids)
                )
            )
            stale_visits_deleted = stale_visits.rowcount
            await db.flush()

        # Now safe to delete the appointments
        from app.models.clinical import Appointment as ApptModel
        past_demo_appts = await db.execute(
            delete(ApptModel).where(
                and_(
                    ApptModel.practice_id == DEMO_PRACTICE_ID,
                    ApptModel.appointment_date < TODAY,
                    ApptModel.appointment_date > TODAY - timedelta(days=3),
                )
            )
        )
        if stale_visits_deleted or past_demo_appts.rowcount:
            await db.flush()
            print(f"  🧹 Cleaned {stale_visits_deleted} stale visits, {past_demo_appts.rowcount} old appointments")

        # Seed in dependency order
        chairs = await seed_chairs(db)
        das = await seed_dental_assistants(db)
        patients = await seed_patients(db)
        appointments = await seed_appointments(db, patients, chairs, das)
        await seed_visit_statuses(db, patients, appointments, chairs)
        await seed_staff_messaging(db)
        await seed_patient_messages(db, patients)
        await seed_portal_forms(db)
        await seed_portal_accounts(db, patients)
        await seed_portal_messages(db, patients)

        # ── Insurance & Claims Demo Data ──
        await seed_insurance_and_claims(db, patients)
        await seed_invoices(db)

        await db.commit()

    print("\n✅ Demo data seeding complete!\n")
    print("  Patient Flow Board:")
    print("    • 1 patient checked out (Marcus)")
    print("    • 1 patient in treatment (Aaliyah)")
    print("    • 2 patients in lobby (Devon, Jasmine)")
    print(f"  Today's Schedule: {len(DEMO_APPOINTMENTS)} appointments")
    print("  Staff Chat: 2 rooms (AI auto-reply responds to demo messages)")
    print("  Patient Comms: 10 SMS/email messages in log")
    print("  MyOrthoChart: 4 forms, 6 patient accounts, 5 conversations")
    print()


if __name__ == "__main__":
    asyncio.run(seed_demo_flow())
