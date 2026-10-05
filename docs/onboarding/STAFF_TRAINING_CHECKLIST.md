# OrthoFlow — Staff Training Checklist

**Purpose:** Role-based training so each team member can do their daily job in OrthoFlow on day one,
plus a patient-facing MyOrthoChart orientation. Run during onboarding (see
`FIRST_CLIENT_ONBOARDING_GUIDE.md`). Check items off as each person demonstrates them.
Only covers functionality that exists today.

**Format:** `[ ]` trainee can perform it unaided. Train in role order; everyone does the Common Basics.

---

## Common Basics (everyone)
- [ ] Log in with your account + complete SMS-OTP MFA
- [ ] Navigate the top nav; find Dashboard, Schedule, Patients, Ledger
- [ ] Open a patient chart; read the clinical overview + emergency medical alerts
- [ ] Use patient search to jump to a patient
- [ ] Read the Dashboard AI "needs attention" items
- [ ] Log out; understand session timeout / why MFA matters (HIPAA)

## Front Desk / Scheduling Coordinator
- [ ] Read the daily Schedule board (chairs, DAs, confirmation status, balance, owes flag)
- [ ] Move a patient through the Patient Flow board (lobby → seated → checked-out)
- [ ] Schedule, reschedule, and cancel an appointment
- [ ] Confirm an appointment and see it sync to the patient (MyOrthoChart)
- [ ] Use "Today's Notes" (daily huddle) — add and remove a note
- [ ] Check the monthly calendar for appointment volume
- [ ] Send/receive a patient message

## Financial Coordinator / Bookkeeper (first-client priority)
- [ ] Open the Ledger roster; read charges / paid / balance per patient
- [ ] Read the **Aging** badge and the **90+ Days Delinquent** summary card
- [ ] Apply the **90+ filter** to triage long-tail delinquency
- [ ] Add and save an inline **AR/collections note** on a patient ("mom will pay Friday"); confirm
      the note indicator appears on the row
- [ ] Expand a patient's transactions; identify a **declined/failed auto-pay** (red) vs resolved
- [ ] Post a charge / payment / adjustment to a ledger
- [ ] Run the "Patients Who Owe" report and the AR Aging report
- [ ] Send an SMS payment link (touchpoint automation)
- [ ] Add an insurance subscriber + run an eligibility check
- [ ] Create a claim (draft) and follow it through the claims workflow
- [ ] Post an insurance payment / ERA and see contractual adjustment on the ledger
- [ ] Generate a TC proposal and a contract

## Clinical / Dental Assistant
- [ ] Read and update the tooth chart
- [ ] Write a treatment note
- [ ] Upload an image (pano / ceph / CBCT / photo) with the right record type
- [ ] Track an appliance and an Invisalign case
- [ ] Use the DA assignment on the schedule board
- [ ] Use the Time Clock (clock in/out)

## Doctor / Owner / Admin
- [ ] High-level dashboard review (remote access from home)
- [ ] Review AI insights (recoverable revenue, unbilled claims, overdue-for-visit patients)
- [ ] Generate an AI Letter (e.g. referral thank-you) and send via email
- [ ] Review reports (production, collections, provider productivity, AR aging)
- [ ] Create staff accounts + assign roles/permissions
- [ ] Review practice settings (hours, branding, reminder timing)
- [ ] Understand what requires a BAA / HIPAA posture before real PHI

## Secure Document Exchange (financial coordinator + front desk + clinical)
- [ ] Upload a document to a patient from the chart (office → patient)
- [ ] Open a presigned document download; understand links expire (security)
- [ ] See the notification when a patient uploads a document (patient → office)
- [ ] Understand accepted types (PDF, PNG, JPG, HEIC) and that files are virus-scanned before saving

## Patient Orientation — MyOrthoChart (for staff to explain to patients)
- [ ] Patient registers / verifies their MyOrthoChart account (email matches the chart)
- [ ] Patient views + confirms/reschedules/cancels an appointment
- [ ] Patient sees treatment progress
- [ ] Patient messages the office
- [ ] Patient completes an intake/consent form
- [ ] Patient views billing
- [ ] Patient **uploads** a document (insurance card / consent / photo) and gets an email confirmation
- [ ] Patient **opens** a document the office shared (secure link)
- [ ] Patient reads notifications

---

## Sign-off
| Role | Trainee | Trainer | Date | Complete |
|------|---------|---------|------|----------|
| Front Desk | | | | ☐ |
| Financial Coordinator | | | | ☐ |
| Clinical / DA | | | | ☐ |
| Doctor / Admin | | | | ☐ |

**Training is complete when each role has signed off and the pre-live Functional Verification in
`ONBOARDING_CHECKLIST.md` passes.**
