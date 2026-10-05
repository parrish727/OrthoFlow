# OrthoFlow — First-Client Onboarding Guide & FAQ

**Audience:** The first production practice (owner/doctor, office manager, financial coordinator,
front desk, clinical/DA staff) + the Melanin Technologies implementation lead.
**Purpose:** A single document that explains what OrthoFlow + MyOrthoChart are, how onboarding
works end to end, and answers the questions a practice is likely to ask before and during go-live.
Companion to `ONBOARDING_CHECKLIST.md` (data we collect) and `STAFF_TRAINING_CHECKLIST.md` (role
training). Only describes functionality that exists and runs today.

---

## 1. What OrthoFlow is

OrthoFlow is a cloud-based orthodontic practice platform covering the clinical, financial, and
front-office workflow, with an AI layer for the repetitive admin work. **MyOrthoChart** is the
patient-facing portal that pairs with it — the practice works in OrthoFlow; patients see their
appointments, documents, treatment progress, and messages in MyOrthoChart.

### Feature surface (today)
- **Scheduling:** daily schedule board (chairs/DAs), monthly calendar, Patient Flow board
  (lobby → seated → checked-out), appointment confirmations synced to the patient, "Today's Notes"
  daily huddle.
- **Patients & clinical:** patient records, tooth chart, treatment notes, clinical overview with
  emergency medical alerts, imaging (upload/store pano/ceph/CBCT/photos), appliance tracking,
  Invisalign tracking, CDT code browser.
- **Financial:** patient **Ledger** (charges, insurance payments, contractual adjustments, monthly
  card auto-charges, declined-payment flags) with **AR aging buckets (30/60/90/90–120/120+)**, a
  **90+ delinquency filter**, an inline **AR/collections note** per patient, and a **patient search**;
  invoices/AP, insurance subscribers + eligibility, claims workflow, payments, TC (treatment
  coordinator) proposals, contracts.
- **Communications:** appointment reminders, patient messages, staff messages, **AI Letters**
  (learns the practice's writing style; referral thank-yous, school notes, collections letters),
  secure **document exchange** both directions (office ⇄ patient, ClamAV-scanned, private storage).
- **Reporting & AI:** report builder, AR aging / collections / production / provider-productivity
  reports, dashboard AI insights (recoverable revenue from denied claims, unbilled totals, patients
  overdue for next visit), AI claim-denial analysis.
- **Admin:** staff accounts + roles/permissions, time clock, settings, practice portal admin.

### MyOrthoChart (patient portal)
Patients can: view/confirm/cancel/reschedule appointments, see treatment progress, message the
office, complete intake/consent forms, view billing, **upload documents** (insurance cards,
consents, photos — HEIC/PDF/JPG/PNG), **securely open documents** the office shares, and get
notifications + email confirmations. OrthoFlow is the source of truth; MyOrthoChart mirrors it.

---

## 2. How onboarding works (end to end)

1. **Kickoff & data collection** — we complete `ONBOARDING_CHECKLIST.md` (practice info, providers,
   accounts, clearinghouse, imaging, migration, communications, QuickBooks).
2. **Environment configuration** — practice created, chairs/DAs/providers set up, branding, hours,
   time zone; owner admin account + SMS-OTP MFA; staff accounts with roles.
3. **Insurance/clearinghouse wiring** — connect the practice's clearinghouse enrollment (claims flow
   out via the clearinghouse; eligibility via Stedi).
4. **Data migration (if any)** — patient list, images, historical claims as available.
5. **Staff training** — role-based, per `STAFF_TRAINING_CHECKLIST.md`.
6. **Pre-live verification** — the functional checklist (login, schedule, test patient, test claim,
   eligibility, reminder delivery, QuickBooks if used) + compliance gates (Anthropic BAA, HIPAA ack).
7. **Go-live** — typically 1–2 weeks from kickoff, gated mainly by clearinghouse enrollment timing.

---

## 3. FAQ — questions a practice is likely to ask

### Access, setup, and daily use
- **Is it cloud-based / can staff work from home?** Yes. OrthoFlow is web-based; staff log in from
  anywhere with their account + MFA. Doctors can review remotely.
- **How many clicks to the common screens?** The dashboard surfaces next-best actions; schedule,
  ledger, and a patient's chart are each one click from the top nav, and the ledger/dashboard have
  patient search + jump links.
- **Does it work on a tablet/phone?** The UI is responsive; the patient side (MyOrthoChart) is
  designed mobile-first.

### Financial / AR / delinquency (first-client focus)
- **Can it track patients who owe money?** Yes — the Ledger roster lists every patient with a
  balance, charges, payments, and an **aging bucket**. There's a "Patients Who Owe" report too.
- **Does it handle delinquency past 90 days?** Yes. Unlike systems that stop at 90 and dump to
  collections, OrthoFlow buckets **90–120 and 120+** and keeps tracking them, with a **90+ filter**
  and a per-patient **AR/collections note** (e.g. "mom will pay Friday") so the team doesn't
  re-contact or rebuild a spreadsheet each week.
- **Where do financial notes live?** Directly on the Ledger row (inline AR note) — no navigating to
  the chart, one place for financial-coordinator notes.
- **Does it automate payment collection?** Yes — monthly card auto-charges, declined-payment flags
  surfaced in red, and SMS payment-link touchpoints across the 30–90-day window.
- **Does it do insurance?** Insurance subscribers + benefits, eligibility checks (via Stedi
  clearinghouse), claims creation/workflow, ERA/payment posting, and AI denial analysis.

### Integrations
- **Do you integrate with OrthoFi?** Not yet — an OrthoFi ↔ OrthoFlow financial bridge is on the
  active roadmap (OrthoFi stops tracking at 120 days; OrthoFlow is designed to own the long tail).
  See the integration note below.
- **Do you integrate with TOPS?** TOPS is a closed ecosystem that states it does not integrate with
  third-party software. We're investigating any data-export/migration path; direct live integration
  is unlikely to be available from TOPS's side.
- **What clearinghouse do you use?** Stedi runs in the background for eligibility; claims submit via
  the practice's clearinghouse enrollment (Tesia/DentalXChange/Office Ally recommended for ortho).
- **QuickBooks?** QuickBooks Online (not Desktop) for the AP/invoice module via OAuth.

### Clinical & imaging
- **Can we upload X-rays/photos?** Yes — pano, ceph, CBCT, and intraoral/extraoral photos, stored
  securely. (Automated cephalometric tracing/analysis is on the roadmap, not yet live.)
- **Appliance / Invisalign tracking?** Yes, both.

### Patients (MyOrthoChart)
- **What can patients do?** View/confirm/reschedule appointments, see progress, message the office,
  complete forms, view billing, and upload/download documents securely. They get email confirmations.
- **Is patient data secure?** HIPAA controls: JWT + SMS-OTP MFA for staff, audit logging on data
  access, private encrypted document storage with virus scanning and short-lived access links, TLS.

### Security / compliance
- **Is a BAA needed?** Yes — Anthropic BAA before real PHI flows through AI features, and the
  practice signs a HIPAA acknowledgment. The practice executes its own BAA with its clearinghouse.
- **Where does AI run?** Anthropic Claude for language features (approved provider); no patient PHI
  is used to train models.

### Support & go-live
- **How long to go live?** 1–2 weeks typical, mostly gated by clearinghouse enrollment.
- **What if the clearinghouse isn't enrolled yet?** Claims can be created and tracked immediately;
  submission queues until enrollment completes.

---

## 4. OrthoFi integration (status note for the first client)
OrthoFi is used by a large share of ortho practices for digital new-patient paperwork, insurance
verification, benefit calculation, and contract setup — but it **stops tracking at 120 days**.
OrthoFlow's AR aging + 90+/120+ delinquency tracking is designed to own exactly that long tail. A
formal OrthoFi ↔ OrthoFlow financial bridge is on the active roadmap; until it ships, OrthoFlow runs
standalone for financials and the practice continues OrthoFi as-is for front-end intake if desired.

---

## 5. Related documents
- `ONBOARDING_CHECKLIST.md` — exactly what we collect to configure the environment.
- `STAFF_TRAINING_CHECKLIST.md` — role-based training (front desk, financial coordinator, clinical/
  DA, doctor/admin) + patient MyOrthoChart orientation.
- `docs/specs/MYORTHOCHART.md` — MyOrthoChart product spec.
- `docs/compliance/` — HIPAA / Medicaid / SLA references.
