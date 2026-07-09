"""
OrthoFlow — Phase 1 Clinical Seed Data for QA Testing

Generates realistic orthodontic practice data:
  - 4 chairs / operatories
  - 3 dental assistants
  - 25 patients in various treatment phases
  - ~60 appointments (past + today + future)
  - Treatment notes per patient
  - Tooth charts for active patients

Usage:
  # Against local dev database (requires running backend with DB)
  python -m scripts.seed_clinical

  # Or via Docker:
  docker exec orthoflow-backend-1 python -m scripts.seed_clinical

  # Clear seeded data:
  python -m scripts.seed_clinical --clear

Prerequisite:
  - Migration 002_phase1_clinical must be applied
  - A practice and user must already exist (from registration)
"""
import os
import sys
import uuid
import random
from datetime import date, time, timedelta, datetime, timezone

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from sqlalchemy import text, select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://orthoflow:orthoflow_dev@localhost:5433/orthoflow"
)

# ── Mock Data Pools ───────────────────────────────────────────────────────────

FIRST_NAMES = [
    "Sophia", "Liam", "Olivia", "Noah", "Emma", "Aiden", "Ava", "Jackson",
    "Isabella", "Lucas", "Mia", "Caden", "Harper", "Mason", "Amelia", "Elijah",
    "Evelyn", "Logan", "Abigail", "James", "Ella", "Ethan", "Scarlett",
    "Carter", "Madison",
]

LAST_NAMES = [
    "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson",
    "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee",
    "Perez", "Thompson", "White", "Harris", "Sanchez",
]

REFERRING_DOCTORS = [
    "Dr. Sarah Mitchell (General Dentistry)",
    "Dr. James Park (Pediatric Dentistry)",
    "Dr. Lisa Chen (General Dentistry)",
    "Dr. Marcus Reed (Oral Surgery)",
    None, None, None,  # some patients are self-referred
]

APPOINTMENT_TYPES = [
    "Consultation", "Records", "Bonding", "Adjustment", "Wire Change",
    "Emergency - Bracket", "Emergency - Wire", "Deband", "Retainer Check",
    "IPR", "Elastic Check", "Progress Photos", "Mid-Treatment Records",
]

TREATMENT_PHASES = ["consultation", "records", "bonding", "active", "finishing", "retention", "complete"]
PATIENT_STATUSES = ["active", "active", "active", "active", "inactive", "prospective"]  # weighted toward active

NOTE_TEMPLATES = [
    "Patient presenting for routine adjustment. Upper and lower archwires advanced. Good oral hygiene.",
    "Bracket rebonded on #{tooth}. Patient reports discomfort resolved after previous adjustment.",
    "Wire change: upper from 16 NiTi to 18 SS. Lower remains 16 NiTi. Spacing closing well.",
    "Mid-treatment records taken. Ceph and pano look good. Class I molars achieved bilaterally.",
    "Patient compliant with elastics. Overjet reduced from 5mm to 2mm. Continue 3/16\" medium.",
    "Deband today. Upper and lower Essix retainers delivered. Wear instructions given.",
    "Retainer check: upper Essix intact. Lower showing slight relapse #25. Discussed options.",
    "IPR performed on 12-22 (0.2mm each). Space created for alignment of lateral incisors.",
    "Consultation: Class II Div 1 malocclusion. Deep bite, 7mm overjet. Treatment plan discussed.",
    "Emergency visit: bracket loose on #14. Rebonded with light cure. No wire issues.",
    "Progress photos taken. Comparing to initial — significant improvement in alignment.",
    "Elastic check: patient reports wearing 22hrs/day. Midlines improving. Continue current elastics.",
]

CHAIR_NAMES = ["Chair 1", "Chair 2", "Chair 3", "Chair 4"]
CHAIR_COLORS = ["#4F46E5", "#059669", "#D97706", "#DC2626"]

DA_DATA = [
    ("Maria", "Santos", "#8B5CF6"),
    ("Jasmine", "Williams", "#EC4899"),
    ("Tyler", "Chen", "#06B6D4"),
]

WIRE_OPTIONS = [
    "14 NiTi", "16 NiTi", "18 NiTi", "16x22 NiTi",
    "18 SS", "16x22 SS", "19x25 SS", "19x25 TMA",
]

BRACKET_TYPES = ["Standard", "Self-Ligating", "Ceramic", "Lingual"]
TOOTH_CONDITIONS = ["Healthy", "Healthy", "Healthy", "Healthy", "Crown", "Missing"]  # weighted healthy


# ── Seed Logic ────────────────────────────────────────────────────────────────

async def get_practice_and_user(session: AsyncSession) -> tuple[str, str]:
    """Get the first practice and user from the existing database."""
    result = await session.execute(text("SELECT id FROM practices LIMIT 1"))
    practice_row = result.fetchone()
    if not practice_row:
        raise RuntimeError("No practice found. Register a user first (POST /api/v1/auth/register).")

    result = await session.execute(text("SELECT id FROM users LIMIT 1"))
    user_row = result.fetchone()
    if not user_row:
        raise RuntimeError("No user found.")

    return str(practice_row[0]), str(user_row[0])


async def clear_clinical_data(session: AsyncSession, practice_id: str):
    """Remove all seeded clinical data for the practice."""
    await session.execute(text("DELETE FROM tooth_charts WHERE practice_id = :pid"), {"pid": practice_id})
    await session.execute(text("DELETE FROM treatment_notes WHERE practice_id = :pid"), {"pid": practice_id})
    await session.execute(text("DELETE FROM appointments WHERE practice_id = :pid"), {"pid": practice_id})
    await session.execute(text("DELETE FROM dental_assistants WHERE practice_id = :pid"), {"pid": practice_id})
    await session.execute(text("DELETE FROM chairs WHERE practice_id = :pid"), {"pid": practice_id})
    await session.execute(text("DELETE FROM patients WHERE practice_id = :pid"), {"pid": practice_id})
    await session.commit()
    print("✅ Cleared all clinical seed data.")


async def seed(session: AsyncSession):
    practice_id, user_id = await get_practice_and_user(session)
    print(f"Seeding for practice: {practice_id}, user: {user_id}")

    # ── Chairs ────────────────────────────────────────────────────────────────
    chair_ids = []
    for i, (name, color) in enumerate(zip(CHAIR_NAMES, CHAIR_COLORS)):
        cid = str(uuid.uuid4())
        chair_ids.append(cid)
        await session.execute(text("""
            INSERT INTO chairs (id, practice_id, name, color, is_active, sort_order, created_at)
            VALUES (:id, :pid, :name, :color, true, :sort, NOW())
            ON CONFLICT DO NOTHING
        """), {"id": cid, "pid": practice_id, "name": name, "color": color, "sort": i})
    print(f"  ✓ {len(chair_ids)} chairs created")

    # ── Dental Assistants ─────────────────────────────────────────────────────
    da_ids = []
    for first, last, color in DA_DATA:
        did = str(uuid.uuid4())
        da_ids.append(did)
        await session.execute(text("""
            INSERT INTO dental_assistants (id, practice_id, first_name, last_name, color, is_active, created_at)
            VALUES (:id, :pid, :first, :last, :color, true, NOW())
            ON CONFLICT DO NOTHING
        """), {"id": did, "pid": practice_id, "first": first, "last": last, "color": color})
    print(f"  ✓ {len(da_ids)} dental assistants created")

    # ── Patients ──────────────────────────────────────────────────────────────
    patient_ids = []
    for i in range(25):
        pid = str(uuid.uuid4())
        patient_ids.append(pid)
        dob = date(2000 + random.randint(-15, 12), random.randint(1, 12), random.randint(1, 28))
        phase = random.choice(TREATMENT_PHASES)
        status = random.choice(PATIENT_STATUSES)
        first = FIRST_NAMES[i]
        last = LAST_NAMES[i]
        phone = f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}"
        email = f"{first.lower()}.{last.lower()}@email.com"
        referring = random.choice(REFERRING_DOCTORS)

        await session.execute(text("""
            INSERT INTO patients (id, practice_id, first_name, last_name, date_of_birth, email, phone, status, treatment_phase, referring_doctor, created_at, updated_at)
            VALUES (:id, :pid, :first, :last, :dob, :email, :phone, :status, :phase, :ref, NOW(), NOW())
        """), {
            "id": pid, "pid": practice_id, "first": first, "last": last,
            "dob": dob.isoformat(), "email": email, "phone": phone,
            "status": status, "phase": phase, "ref": referring,
        })
    print(f"  ✓ {len(patient_ids)} patients created")

    # ── Appointments ──────────────────────────────────────────────────────────
    today = date.today()
    appointment_count = 0

    # Past appointments (last 14 days)
    for day_offset in range(-14, 0):
        appt_date = today + timedelta(days=day_offset)
        if appt_date.weekday() >= 5:  # skip weekends
            continue
        num_appts = random.randint(6, 12)
        hour = 8
        for _ in range(num_appts):
            if hour >= 17:
                break
            duration = random.choice([15, 30, 30, 45, 60])
            start = time(hour, random.choice([0, 15, 30, 45]))
            end_hour = hour + (duration // 60)
            end_min = (start.minute + duration) % 60
            if (start.minute + duration) >= 60:
                end_hour += 1
            if end_hour > 17:
                break
            end = time(min(end_hour, 17), end_min)

            aid = str(uuid.uuid4())
            await session.execute(text("""
                INSERT INTO appointments (id, practice_id, patient_id, chair_id, da_id, appointment_date, start_time, end_time, duration_minutes, status, appointment_type, created_by, created_at, updated_at)
                VALUES (:id, :pid, :patient, :chair, :da, :appt_date, :start, :end, :dur, :status, :type, :user, NOW(), NOW())
            """), {
                "id": aid, "pid": practice_id,
                "patient": random.choice(patient_ids),
                "chair": random.choice(chair_ids),
                "da": random.choice(da_ids),
                "appt_date": appt_date.isoformat(),
                "start": start.isoformat(), "end": end.isoformat(),
                "dur": duration,
                "status": "completed",
                "type": random.choice(APPOINTMENT_TYPES),
                "user": user_id,
            })
            appointment_count += 1
            hour = end_hour + (1 if end_min > 30 else 0)

    # Today's appointments
    num_today = random.randint(8, 14)
    hour = 8
    today_appt_ids = []
    for _ in range(num_today):
        if hour >= 17:
            break
        duration = random.choice([15, 30, 30, 45, 60])
        start = time(hour, random.choice([0, 15, 30]))
        end_hour = hour + (duration // 60)
        end_min = (start.minute + duration) % 60
        if (start.minute + duration) >= 60:
            end_hour += 1
        if end_hour > 17:
            break
        end = time(min(end_hour, 17), end_min)

        current_hour = datetime.now().hour
        if hour < current_hour - 1:
            status = "completed"
        elif hour < current_hour:
            status = "in_progress"
        elif hour == current_hour:
            status = "checked_in"
        else:
            status = "scheduled"

        aid = str(uuid.uuid4())
        today_appt_ids.append(aid)
        await session.execute(text("""
            INSERT INTO appointments (id, practice_id, patient_id, chair_id, da_id, appointment_date, start_time, end_time, duration_minutes, status, appointment_type, created_by, created_at, updated_at)
            VALUES (:id, :pid, :patient, :chair, :da, :appt_date, :start, :end, :dur, :status, :type, :user, NOW(), NOW())
        """), {
            "id": aid, "pid": practice_id,
            "patient": random.choice(patient_ids),
            "chair": random.choice(chair_ids),
            "da": random.choice(da_ids) if random.random() > 0.1 else None,  # 10% unassigned
            "appt_date": today.isoformat(),
            "start": start.isoformat(), "end": end.isoformat(),
            "dur": duration,
            "status": status,
            "type": random.choice(APPOINTMENT_TYPES),
            "user": user_id,
        })
        appointment_count += 1
        hour = end_hour + (1 if end_min > 30 else 0)

    # Future appointments (next 7 days)
    for day_offset in range(1, 8):
        appt_date = today + timedelta(days=day_offset)
        if appt_date.weekday() >= 5:
            continue
        num_appts = random.randint(6, 12)
        hour = 8
        for _ in range(num_appts):
            if hour >= 17:
                break
            duration = random.choice([15, 30, 30, 45, 60])
            start = time(hour, random.choice([0, 15, 30]))
            end_hour = hour + (duration // 60)
            end_min = (start.minute + duration) % 60
            if (start.minute + duration) >= 60:
                end_hour += 1
            if end_hour > 17:
                break
            end = time(min(end_hour, 17), end_min)

            aid = str(uuid.uuid4())
            # Some unassigned to chair (for the unassigned sidebar)
            chair = random.choice(chair_ids) if random.random() > 0.15 else None

            await session.execute(text("""
                INSERT INTO appointments (id, practice_id, patient_id, chair_id, da_id, appointment_date, start_time, end_time, duration_minutes, status, appointment_type, created_by, created_at, updated_at)
                VALUES (:id, :pid, :patient, :chair, :da, :appt_date, :start, :end, :dur, 'scheduled', :type, :user, NOW(), NOW())
            """), {
                "id": aid, "pid": practice_id,
                "patient": random.choice(patient_ids),
                "chair": chair,
                "da": random.choice(da_ids) if chair else None,
                "appt_date": appt_date.isoformat(),
                "start": start.isoformat(), "end": end.isoformat(),
                "dur": duration,
                "type": random.choice(APPOINTMENT_TYPES),
                "user": user_id,
            })
            appointment_count += 1
            hour = end_hour + (1 if end_min > 30 else 0)

    print(f"  ✓ {appointment_count} appointments created (past + today + future)")

    # ── Treatment Notes ───────────────────────────────────────────────────────
    note_count = 0
    for pid in patient_ids[:18]:  # notes for 18 of 25 patients
        num_notes = random.randint(2, 6)
        for j in range(num_notes):
            note_template = random.choice(NOTE_TEMPLATES)
            note_text = note_template.replace("{tooth}", str(random.randint(3, 30)))
            nid = str(uuid.uuid4())
            created_at = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 90))

            await session.execute(text("""
                INSERT INTO treatment_notes (id, practice_id, patient_id, author_id, note_text, note_type, created_at)
                VALUES (:id, :pid, :patient, :author, :note, :type, :created)
            """), {
                "id": nid, "pid": practice_id, "patient": pid,
                "author": user_id, "note": note_text,
                "type": random.choice(["clinical", "clinical", "clinical", "progress", "referral"]),
                "created": created_at.isoformat(),
            })
            note_count += 1
    print(f"  ✓ {note_count} treatment notes created")

    # ── Tooth Charts ──────────────────────────────────────────────────────────
    chart_count = 0
    # Only for patients in active/finishing/retention phases
    active_patients = patient_ids[:15]
    for pid in active_patients:
        import json
        teeth_data = {}
        for tooth in range(1, 33):
            if random.random() > 0.3:  # 70% of teeth have data
                condition = random.choice(TOOTH_CONDITIONS)
                if condition == "Missing":
                    teeth_data[str(tooth)] = {"condition": "Missing"}
                else:
                    teeth_data[str(tooth)] = {
                        "bracket_type": random.choice(BRACKET_TYPES) if random.random() > 0.2 else None,
                        "condition": condition,
                        "band": random.random() > 0.85,  # 15% have bands
                    }

        upper_wire = random.choice(WIRE_OPTIONS)
        lower_wire = random.choice(WIRE_OPTIONS)
        wire_date = (today - timedelta(days=random.randint(1, 30))).isoformat()

        appliances = []
        if random.random() > 0.7:
            appliances.append({"name": "RPE (Rapid Palatal Expander)", "placed_date": (today - timedelta(days=random.randint(30, 180))).isoformat()})
        if random.random() > 0.85:
            appliances.append({"name": "Lower Lingual Holding Arch", "placed_date": (today - timedelta(days=random.randint(10, 90))).isoformat()})

        cid = str(uuid.uuid4())
        await session.execute(text("""
            INSERT INTO tooth_charts (id, practice_id, patient_id, teeth_data, upper_wire, lower_wire, upper_wire_date, lower_wire_date, appliances, updated_at, updated_by)
            VALUES (:id, :pid, :patient, :teeth::jsonb, :uw, :lw, :uwd, :lwd, :app::jsonb, NOW(), :user)
            ON CONFLICT (patient_id) DO UPDATE SET teeth_data = :teeth::jsonb, upper_wire = :uw, lower_wire = :lw, updated_at = NOW()
        """), {
            "id": cid, "pid": practice_id, "patient": pid,
            "teeth": json.dumps(teeth_data),
            "uw": upper_wire, "lw": lower_wire,
            "uwd": wire_date, "lwd": wire_date,
            "app": json.dumps(appliances),
            "user": user_id,
        })
        chart_count += 1
    print(f"  ✓ {chart_count} tooth charts created")

    await session.commit()
    print(f"\n✅ Clinical seed complete!")
    print(f"   Patients: 25 | Chairs: 4 | DAs: 3")
    print(f"   Appointments: {appointment_count} | Notes: {note_count} | Charts: {chart_count}")
    print(f"\n   Login with your existing credentials and navigate to /schedule or /patients")


async def main():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        if "--clear" in sys.argv:
            practice_id, _ = await get_practice_and_user(session)
            await clear_clinical_data(session, practice_id)
        else:
            await seed(session)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
