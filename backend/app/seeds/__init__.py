"""Seed script for CDT codes and appointment type templates.
Run via: docker compose exec backend python -m app.seeds.cdt_seed
"""
import asyncio
import uuid

from app.core.database import SessionLocal
from app.models.cdt_codes import CDTCode, AppointmentTypeTemplate


# ═══════════════════════════════════════════════════════════════════════════════
# CDT CODES — Curated set of most commonly used codes per specialty
# ═══════════════════════════════════════════════════════════════════════════════

CDT_CODES = [
    # ── D0000-D0999: Diagnostic ───────────────────────────────────────────────
    ("D0120", "diagnostic", "clinical oral evaluations", "Periodic oral evaluation – established patient", "Periodic Exam", "general", True, 5200, False, False),
    ("D0140", "diagnostic", "clinical oral evaluations", "Limited oral evaluation – problem focused", "Limited Exam", "general", True, 7500, False, False),
    ("D0145", "diagnostic", "clinical oral evaluations", "Oral evaluation for a patient under three years of age", "Infant Exam", "general", False, 5500, False, False),
    ("D0150", "diagnostic", "clinical oral evaluations", "Comprehensive oral evaluation – new or established patient", "Comp Exam", "general", True, 9500, False, False),
    ("D0210", "diagnostic", "radiographs", "Intraoral – complete series of radiographic images", "Full Mouth X-rays", "general", True, 15000, False, False),
    ("D0220", "diagnostic", "radiographs", "Intraoral – periapical first radiographic image", "PA X-ray", "general", True, 3500, True, False),
    ("D0230", "diagnostic", "radiographs", "Intraoral – periapical each additional radiographic image", "PA Additional", "general", False, 2900, True, False),
    ("D0272", "diagnostic", "radiographs", "Bitewings – two radiographic images", "2 Bitewings", "general", True, 5500, False, False),
    ("D0274", "diagnostic", "radiographs", "Bitewings – four radiographic images", "4 Bitewings", "general", True, 7000, False, False),
    ("D0330", "diagnostic", "radiographs", "Panoramic radiographic image", "Panoramic", "general", True, 13000, False, False),
    ("D0340", "diagnostic", "radiographs", "2D cephalometric radiographic image", "Ceph X-ray", "ortho", True, 13500, False, False),
    ("D0350", "diagnostic", "radiographs", "2D oral/facial photographic image", "Clinical Photo", "general", False, 3000, False, False),
    ("D0470", "diagnostic", "tests and examinations", "Diagnostic casts", "Study Models", "ortho", True, 8000, False, False),

    # ── D1000-D1999: Preventive ───────────────────────────────────────────────
    ("D1110", "preventive", "dental prophylaxis", "Prophylaxis – adult", "Adult Cleaning", "general", True, 10500, False, False),
    ("D1120", "preventive", "dental prophylaxis", "Prophylaxis – child", "Child Cleaning", "general", True, 7500, False, False),
    ("D1206", "preventive", "topical fluoride", "Topical application of fluoride varnish", "Fluoride Varnish", "general", True, 4000, False, False),
    ("D1208", "preventive", "topical fluoride", "Topical application of fluoride – excluding varnish", "Fluoride Treatment", "general", False, 3500, False, False),
    ("D1351", "preventive", "sealants", "Sealant – per tooth", "Sealant", "general", True, 5500, True, False),
    ("D1510", "preventive", "space maintenance", "Space maintainer – fixed, unilateral", "Space Maintainer", "general", False, 35000, True, False),

    # ── D2000-D2999: Restorative ──────────────────────────────────────────────
    ("D2140", "restorative", "amalgam restorations", "Amalgam – one surface, primary or permanent", "Amalgam 1 Surface", "general", True, 17500, True, True),
    ("D2150", "restorative", "amalgam restorations", "Amalgam – two surfaces, primary or permanent", "Amalgam 2 Surface", "general", True, 22500, True, True),
    ("D2160", "restorative", "amalgam restorations", "Amalgam – three surfaces, primary or permanent", "Amalgam 3 Surface", "general", False, 27500, True, True),
    ("D2330", "restorative", "resin-based composite", "Resin-based composite – one surface, anterior", "Composite 1 Surf Ant", "general", True, 19500, True, True),
    ("D2331", "restorative", "resin-based composite", "Resin-based composite – two surfaces, anterior", "Composite 2 Surf Ant", "general", True, 25000, True, True),
    ("D2332", "restorative", "resin-based composite", "Resin-based composite – three surfaces, anterior", "Composite 3 Surf Ant", "general", False, 30000, True, True),
    ("D2391", "restorative", "resin-based composite", "Resin-based composite – one surface, posterior", "Composite 1 Surf Post", "general", True, 20500, True, True),
    ("D2392", "restorative", "resin-based composite", "Resin-based composite – two surfaces, posterior", "Composite 2 Surf Post", "general", True, 27000, True, True),
    ("D2393", "restorative", "resin-based composite", "Resin-based composite – three surfaces, posterior", "Composite 3 Surf Post", "general", False, 32000, True, True),
    ("D2740", "restorative", "crowns – single restorations", "Crown – porcelain/ceramic substrate", "Porcelain Crown", "cosmetic", True, 130000, True, False),
    ("D2750", "restorative", "crowns – single restorations", "Crown – porcelain fused to high noble metal", "PFM Crown", "general", True, 125000, True, False),
    ("D2950", "restorative", "other restorative services", "Core buildup, including any pins when required", "Core Buildup", "general", True, 35000, True, False),
    ("D2954", "restorative", "other restorative services", "Prefabricated post and core in addition to crown", "Post & Core", "general", False, 45000, True, False),

    # ── D3000-D3999: Endodontics ──────────────────────────────────────────────
    ("D3310", "endodontics", "pulp therapy", "Endodontic therapy, anterior tooth", "Root Canal Anterior", "general", True, 85000, True, False),
    ("D3320", "endodontics", "pulp therapy", "Endodontic therapy, premolar tooth", "Root Canal Premolar", "general", True, 100000, True, False),
    ("D3330", "endodontics", "pulp therapy", "Endodontic therapy, molar tooth", "Root Canal Molar", "general", True, 125000, True, False),

    # ── D4000-D4999: Periodontics ─────────────────────────────────────────────
    ("D4341", "periodontics", "surgical services", "Periodontal scaling and root planing – four or more teeth per quadrant", "SRP 4+ Teeth/Quad", "perio", True, 30000, False, False),
    ("D4342", "periodontics", "surgical services", "Periodontal scaling and root planing – one to three teeth per quadrant", "SRP 1-3 Teeth/Quad", "perio", True, 22000, False, False),
    ("D4355", "periodontics", "non-surgical services", "Full mouth debridement", "Full Mouth Debridement", "perio", True, 20000, False, False),
    ("D4910", "periodontics", "non-surgical services", "Periodontal maintenance", "Perio Maintenance", "perio", True, 16000, False, False),
    ("D4346", "periodontics", "non-surgical services", "Scaling in presence of generalized moderate or severe gingival inflammation", "Scaling Gingivitis", "perio", False, 15000, False, False),

    # ── D5000-D5999: Prosthodontics ───────────────────────────────────────────
    ("D5110", "prosthodontics", "complete dentures", "Complete denture – maxillary", "Complete Denture Upper", "general", False, 180000, False, False),
    ("D5120", "prosthodontics", "complete dentures", "Complete denture – mandibular", "Complete Denture Lower", "general", False, 180000, False, False),
    ("D5213", "prosthodontics", "partial dentures", "Maxillary partial denture – cast metal framework", "Partial Denture Upper", "general", False, 195000, False, False),
    ("D6010", "prosthodontics", "implant services", "Surgical placement of implant body – endosteal implant", "Implant Placement", "surgery", True, 225000, True, False),
    ("D6065", "prosthodontics", "implant services", "Implant supported porcelain/ceramic crown", "Implant Crown", "cosmetic", True, 175000, True, False),

    # ── D7000-D7999: Oral Surgery ─────────────────────────────────────────────
    ("D7140", "oral_surgery", "extractions", "Extraction, erupted tooth or exposed root", "Simple Extraction", "surgery", True, 22000, True, False),
    ("D7210", "oral_surgery", "extractions", "Extraction, erupted tooth requiring removal of bone", "Surgical Extraction", "surgery", True, 38000, True, False),
    ("D7220", "oral_surgery", "extractions", "Removal of impacted tooth – soft tissue", "Impacted Soft Tissue", "surgery", True, 40000, True, False),
    ("D7230", "oral_surgery", "extractions", "Removal of impacted tooth – partially bony", "Impacted Partial Bony", "surgery", True, 50000, True, False),
    ("D7240", "oral_surgery", "extractions", "Removal of impacted tooth – completely bony", "Impacted Full Bony", "surgery", False, 60000, True, False),
    ("D7953", "oral_surgery", "bone grafts", "Bone replacement graft for ridge preservation – per site", "Bone Graft", "surgery", True, 65000, True, False),

    # ── D8000-D8999: Orthodontics ─────────────────────────────────────────────
    ("D8010", "orthodontics", "limited treatment", "Limited orthodontic treatment of the primary dentition", "Limited Ortho Primary", "ortho", False, 250000, False, False),
    ("D8020", "orthodontics", "limited treatment", "Limited orthodontic treatment of the transitional dentition", "Limited Ortho Trans", "ortho", False, 350000, False, False),
    ("D8040", "orthodontics", "limited treatment", "Limited orthodontic treatment of the adult dentition", "Limited Ortho Adult", "ortho", True, 450000, False, False),
    ("D8070", "orthodontics", "comprehensive treatment", "Comprehensive orthodontic treatment of the transitional dentition", "Comp Ortho Trans", "ortho", True, 550000, False, False),
    ("D8080", "orthodontics", "comprehensive treatment", "Comprehensive orthodontic treatment of the adolescent dentition", "Comp Ortho Adolescent", "ortho", True, 600000, False, False),
    ("D8090", "orthodontics", "comprehensive treatment", "Comprehensive orthodontic treatment of the adult dentition", "Comp Ortho Adult", "ortho", True, 650000, False, False),
    ("D8660", "orthodontics", "other services", "Pre-orthodontic treatment examination", "Ortho Exam", "ortho", True, 25000, False, False),
    ("D8670", "orthodontics", "other services", "Periodic orthodontic treatment visit", "Ortho Adjustment", "ortho", True, 0, False, False),
    ("D8680", "orthodontics", "other services", "Orthodontic retention", "Retention", "ortho", True, 0, False, False),
    ("D8999", "orthodontics", "other services", "Unspecified orthodontic procedure, by report", "Ortho Other", "ortho", False, 0, False, False),

    # ── D9000-D9999: Adjunctive / Cosmetic ────────────────────────────────────
    ("D2962", "cosmetic", "veneers", "Labial veneer (porcelain laminate) – laboratory", "Porcelain Veneer", "cosmetic", True, 150000, True, False),
    ("D9972", "cosmetic", "whitening", "External bleaching – per arch", "Whitening Per Arch", "cosmetic", True, 30000, False, False),
    ("D9975", "cosmetic", "whitening", "External bleaching for home application, per arch; includes materials and fabrication of custom trays", "Take-Home Whitening", "cosmetic", True, 25000, False, False),
    ("D9110", "adjunctive", "emergency", "Palliative treatment of dental pain – minor procedure", "Emergency/Palliative", "general", True, 12000, False, False),
    ("D9215", "adjunctive", "anesthesia", "Local anesthesia in conjunction with operative or surgical procedures", "Local Anesthesia", "general", True, 5000, False, False),
    ("D9230", "adjunctive", "anesthesia", "Inhalation of nitrous oxide/anxiolysis", "Nitrous Oxide", "general", True, 6000, False, False),
    ("D9310", "adjunctive", "consultation", "Consultation – diagnostic service provided by dentist other than requesting dentist", "Specialist Consult", "general", False, 10000, False, False),
    ("D9944", "adjunctive", "occlusal guards", "Occlusal guard – hard appliance, full arch", "Night Guard", "general", True, 50000, False, False),
]

# ═══════════════════════════════════════════════════════════════════════════════
# APPOINTMENT TYPE TEMPLATES — Multi-specialty
# ═══════════════════════════════════════════════════════════════════════════════

APPOINTMENT_TYPES = [
    # General / Preventive
    ("New Patient Exam", "general", "diagnostic", 60, "D0150,D0210", "#3B82F6", True, False, False),
    ("Periodic Exam", "general", "diagnostic", 30, "D0120,D0274", "#3B82F6", True, False, False),
    ("Adult Cleaning", "general", "preventive", 60, "D1110,D0120", "#10B981", True, False, True),
    ("Child Cleaning", "general", "preventive", 45, "D1120,D0120", "#10B981", True, False, True),
    ("Deep Cleaning (SRP)", "perio", "treatment", 90, "D4341", "#EF4444", True, True, False),
    ("Perio Maintenance", "perio", "preventive", 60, "D4910", "#F97316", True, False, True),
    ("Emergency Visit", "general", "diagnostic", 30, "D9110,D0140", "#DC2626", True, False, False),

    # Restorative
    ("Filling", "general", "restorative", 45, "D2391", "#8B5CF6", True, True, False),
    ("Crown Prep", "general", "restorative", 60, "D2750", "#8B5CF6", True, True, False),
    ("Crown Seat", "general", "restorative", 30, "D2750", "#8B5CF6", True, True, False),
    ("Root Canal", "general", "restorative", 90, "D3330", "#6366F1", True, True, False),
    ("Extraction", "surgery", "treatment", 30, "D7140", "#DC2626", True, True, False),
    ("Surgical Extraction", "surgery", "treatment", 60, "D7210", "#DC2626", True, True, False),
    ("Implant Placement", "surgery", "treatment", 90, "D6010", "#6366F1", True, True, False),
    ("Bone Graft", "surgery", "treatment", 45, "D7953", "#6366F1", True, True, False),

    # Cosmetic
    ("Veneer Prep", "cosmetic", "restorative", 90, "D2962", "#EC4899", True, True, False),
    ("Veneer Delivery", "cosmetic", "restorative", 60, "D2962", "#EC4899", True, True, False),
    ("Teeth Whitening", "cosmetic", "treatment", 60, "D9972", "#F59E0B", True, False, False),
    ("Smile Consultation", "cosmetic", "consultation", 45, "D0150", "#EC4899", True, False, False),

    # Orthodontic
    ("Ortho Consultation", "ortho", "consultation", 45, "D8660", "#0D9488", True, False, False),
    ("Records Appointment", "ortho", "diagnostic", 60, "D0340,D0330,D0470", "#0D9488", True, True, False),
    ("Bonding", "ortho", "treatment", 90, "D8080", "#0D9488", True, True, False),
    ("Adjustment", "ortho", "treatment", 20, "D8670", "#0D9488", True, True, False),
    ("Deband", "ortho", "treatment", 60, "D8680", "#0D9488", True, True, False),
    ("Invisalign Start", "ortho", "treatment", 45, "D8040", "#7C3AED", True, True, False),
    ("Invisalign Check", "ortho", "treatment", 15, "D8670", "#7C3AED", True, False, False),
    ("Retainer Check", "ortho", "treatment", 15, "D8680", "#0D9488", True, False, False),
    ("Retainer Delivery", "ortho", "treatment", 20, "D8680", "#0D9488", True, True, False),
]


async def seed_cdt_codes():
    """Seed the CDT code library (idempotent — skips existing codes)."""
    async with SessionLocal() as db:
        for row in CDT_CODES:
            code, category, subcategory, description, short_desc, specialty, is_common, avg_fee, tooth_specific, surface_specific = row
            # Check if code already exists
            from sqlalchemy import select
            existing = await db.execute(select(CDTCode).where(CDTCode.code == code))
            if existing.scalar_one_or_none():
                continue
            db.add(CDTCode(
                code=code, category=category, subcategory=subcategory,
                description=description, short_description=short_desc,
                specialty=specialty, is_common=is_common, avg_fee=avg_fee,
                tooth_specific=tooth_specific, surface_specific=surface_specific,
            ))
        await db.commit()
        print(f"✅ Seeded {len(CDT_CODES)} CDT codes")


async def seed_appointment_types():
    """Seed appointment type templates (idempotent — skips existing)."""
    async with SessionLocal() as db:
        for i, row in enumerate(APPOINTMENT_TYPES):
            name, specialty, category, duration, cdt_codes, color, requires_chair, requires_da, is_hygiene = row
            from sqlalchemy import select
            existing = await db.execute(
                select(AppointmentTypeTemplate).where(AppointmentTypeTemplate.name == name)
            )
            if existing.scalar_one_or_none():
                continue
            db.add(AppointmentTypeTemplate(
                name=name, specialty=specialty, category=category,
                default_duration_minutes=duration, default_cdt_codes=cdt_codes,
                color=color, requires_chair=requires_chair, requires_da=requires_da,
                is_hygiene=is_hygiene, sort_order=i,
            ))
        await db.commit()
        print(f"✅ Seeded {len(APPOINTMENT_TYPES)} appointment type templates")


async def main():
    await seed_cdt_codes()
    await seed_appointment_types()


if __name__ == "__main__":
    asyncio.run(main())
