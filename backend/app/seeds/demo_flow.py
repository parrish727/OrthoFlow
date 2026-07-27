"""Seed demo data for patient flow, today's schedule, and staff messaging.
Run via: docker compose exec backend python -m app.seeds.demo_flow
"""
import asyncio
import uuid
import random
from datetime import datetime, date, time, timezone, timedelta

from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.models import User, Practice
from app.models.clinical import Patient, Appointment, Chair, DentalAssistant
from app.models.workflow import PatientVisitStatus
from app.models.messaging import ChatRoom, ChatRoomMember, ChatMessage
from app.models.communications import MessageLog

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

DEMO_PRACTICE_ID = uuid.UUID("82fe9d87-6250-4b15-ac7d-26de094a4be8")
TODAY = date.today()

# Demo patients for the visit tracker
DEMO_PATIENTS = [
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
    {"patient_idx": 0, "start": time(8, 0), "end": time(8, 20), "duration": 20, "type": "Adjustment", "status": "completed", "chair_idx": 0, "da_idx": 0},
    {"patient_idx": 1, "start": time(8, 30), "end": time(9, 30), "duration": 60, "type": "Bonding", "status": "in_progress", "chair_idx": 1, "da_idx": 1},
    {"patient_idx": 2, "start": time(9, 0), "end": time(9, 20), "duration": 20, "type": "Observation", "status": "checked_in", "chair_idx": None, "da_idx": None},
    {"patient_idx": 3, "start": time(9, 30), "end": time(9, 50), "duration": 20, "type": "Adjustment", "status": "checked_in", "chair_idx": None, "da_idx": 0},
    {"patient_idx": 4, "start": time(10, 0), "end": time(10, 20), "duration": 20, "type": "Adjustment", "status": "scheduled", "chair_idx": 2, "da_idx": 0},
    {"patient_idx": 5, "start": time(10, 30), "end": time(10, 50), "duration": 20, "type": "Retainer Check", "status": "scheduled", "chair_idx": 3, "da_idx": 1},
    {"patient_idx": 6, "start": time(11, 0), "end": time(11, 45), "duration": 45, "type": "Ortho Consultation", "status": "scheduled", "chair_idx": 0, "da_idx": None},
    {"patient_idx": 7, "start": time(13, 0), "end": time(13, 20), "duration": 20, "type": "Adjustment", "status": "scheduled", "chair_idx": 1, "da_idx": 0},
    {"patient_idx": 8, "start": time(13, 30), "end": time(14, 30), "duration": 60, "type": "Records Appointment", "status": "scheduled", "chair_idx": 2, "da_idx": 1},
    {"patient_idx": 9, "start": time(14, 0), "end": time(14, 20), "duration": 20, "type": "Adjustment", "status": "scheduled", "chair_idx": 3, "da_idx": 0},
]

# Visit statuses for the Patient Flow board
# patient_idx, status, minutes_ago_checked_in, minutes_ago_seated
DEMO_VISITS = [
    (0, "checked_out", 90, 75),   # Marcus — already done
    (1, "in_treatment", 45, 30),  # Aaliyah — in chair being bonded
    (2, "waiting", 15, None),     # Devon — lobby, waiting
    (3, "waiting", 5, None),      # Jasmine — lobby, just arrived
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
            patients.append(existing)
        else:
            patient = Patient(
                id=uuid.uuid4(),
                practice_id=DEMO_PRACTICE_ID,
                first_name=p_data["first_name"],
                last_name=p_data["last_name"],
                date_of_birth=p_data["dob"],
                phone=p_data["phone"],
                email=p_data["email"],
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
        checked_out_at = (now - timedelta(minutes=5)) if visit_status == "checked_out" else None

        # Assign a chair for seated/in_treatment/checked_out patients
        chair_id = None
        if visit_status in ("seated", "in_treatment", "checked_out"):
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

    # ── Huddle Room Messages ──────────────────────────────────────────────────
    huddle_messages = [
        (manager, "Good morning team! 🌅 Today's schedule is full — 10 patients on the books.", -95),
        (front_desk, "Marcus Johnson is here for his 8am adjustment. Checked in!", -90),
        (da, "Chair 1 prepped and ready. I'll grab his chart.", -88),
        (doctor, "Thanks Mike. Let's make sure we check his lower wire — it was loose last visit.", -85),
        (da, "Noted. I'll have the NiTi wires set out just in case. 🦷", -83),
        (manager, "Reminder: Aaliyah Washington's bonding is at 8:30 — it's her big day! Make it special.", -75),
        (front_desk, "Her mom confirmed they're on their way. ETA 5 minutes.", -70),
        (doctor, "Perfect. Keisha, can you set up Chair 2 for bonding? Full kit.", -65),
        (da, "On it! Brackets, adhesive, and bite turbos ready to go. ✅", -60),
        (manager, "Devon Brooks (9am observation) — reminder his mom wants to discuss phase 1 timing.", -50),
        (front_desk, "Devon just checked in. Mom has questions about when braces start.", -15),
        (doctor, "I'll take extra time with them. His growth is on track — we can discuss timing after I review the latest ceph.", -12),
    ]

    for sender, content, mins_ago in huddle_messages:
        db.add(ChatMessage(
            id=uuid.uuid4(),
            room_id=huddle_room.id,
            sender_id=sender.id,
            content=content,
            message_type="text",
            created_at=now + timedelta(minutes=mins_ago),
        ))

    # ── DA Room Messages ──────────────────────────────────────────────────────
    da_messages = [
        (doctor, "Mike, can you pull up Marcus's panoramic from last month?", -87),
        (da, "Got it on screen 2. The lower right looks good — wire seats fully now.", -86),
        (doctor, "Great. Let's keep current wire and reassess next visit.", -85),
        (da, "Sounds good doc. Moving him to checkout after you sign off.", -80),
        (doctor, "Signed. Tell Sarah to schedule him 6 weeks out.", -78),
        (da, "Done ✅ Next appointment set for 6 weeks.", -76),
    ]

    for sender, content, mins_ago in da_messages:
        db.add(ChatMessage(
            id=uuid.uuid4(),
            room_id=da_room.id,
            sender_id=sender.id,
            content=content,
            message_type="text",
            created_at=now + timedelta(minutes=mins_ago),
        ))

    await db.flush()
    print(f"  ✅ Staff messaging: 2 rooms, {len(huddle_messages) + len(da_messages)} messages")


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


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════


async def seed_demo_flow():
    """Run all demo flow seeds in order."""
    print("\n🌱 Seeding OrthoFlow demo data...\n")

    async with SessionLocal() as db:
        # Verify practice exists
        result = await db.execute(select(Practice).where(Practice.id == DEMO_PRACTICE_ID))
        practice = result.scalar_one_or_none()
        if not practice:
            print("❌ Demo practice not found. Run demo_accounts seed first.")
            return

        print(f"  Practice: {practice.name}")

        # Seed in dependency order
        chairs = await seed_chairs(db)
        das = await seed_dental_assistants(db)
        patients = await seed_patients(db)
        appointments = await seed_appointments(db, patients, chairs, das)
        await seed_visit_statuses(db, patients, appointments, chairs)
        await seed_staff_messaging(db)
        await seed_patient_messages(db, patients)

        await db.commit()

    print("\n✅ Demo data seeding complete!\n")
    print("  Patient Flow Board:")
    print("    • 1 patient checked out (Marcus)")
    print("    • 1 patient in treatment (Aaliyah)")
    print("    • 2 patients in lobby (Devon, Jasmine)")
    print(f"  Today's Schedule: {len(DEMO_APPOINTMENTS)} appointments")
    print("  Staff Chat: 2 rooms with active conversations")
    print("  Patient Comms: 10 SMS/email messages in log")
    print()


if __name__ == "__main__":
    asyncio.run(seed_demo_flow())
