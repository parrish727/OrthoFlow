# OrthoFlow — Data Hosting & Locality

**Date:** 2026-11-20 · **Audience:** internal, and the basis for sales answers on "where is our data?"
Describes only what exists today. Open items that block some external claims are in §6.

## 1. Short answer

**Patient data is not stored in the practice's office.** It is stored on infrastructure that Melanin Technologies operates (a self-hosted server stack, not a shared public cloud). The practice uses OrthoFlow through a browser and does not host, back up or maintain anything.

We do **not** ship hardware to practices today. The office-side "edge appliance" is a planned imaging-capture device only (the receiving endpoint exists, the device does not). So "we provide the hardware and it calls our application" is a future option for imaging, not the current model.

## 2. Hosting models

| Model | What it is | Status |
|---|---|---|
| **A. OrthoFlow-operated hosting** | All practices run on our Docker stack (Postgres, Redis, MinIO) on self-hosted hardware, behind nginx. Each practice is isolated by `practice_id`. | **Live. This is the product.** |
| **B. Edge appliance (imaging)** | On-site device captures DICOM/ceph from imaging equipment and uploads to model A through `imaging_ingest.py`. Patient records stay on our stack. | Endpoint built. Device not built or shipped. |
| **C. Single-tenant / on-prem** | Enterprise tier lists "isolated infrastructure" (own DB, own containers, K8s namespace per client) and an on-prem option. | Documented in `TIER_SYSTEM.md`. No on-prem package is shipped. |

## 3. What "keeping data local" can truthfully mean today

1. **Not in a hyperscale cloud.** Data sits on hardware we run, in the U.S.
2. **Isolated per practice.** `practice_id` on every table and query, JWT-scoped access, no cross-practice access without that claim. Enterprise tier adds a separate database and K8s namespace.
3. **Encrypted.** TLS 1.2/1.3 in transit (HSTS), full-disk encryption on the host (FileVault), PHI fields encrypted at rest, MinIO server-side encryption, backups AES-256 before offsite transfer.
4. **Audited.** Append-only audit log of data access (user, IP, time, action). No PHI in logs.
5. **Practice-owned.** Full export on request. Offboarding deletes data within 30 days of termination (backups expire on their retention schedule: orthoflow DB 90 days).
6. **Scanned.** Uploaded files pass through ClamAV.

## 4. What leaves our servers (sub-processors)

| Service | Used for | Data involved |
|---|---|---|
| Anthropic (Claude API) | AI letters, note summaries, denial/appeal drafting, ceph auto-landmarking (image), CBCT interpretation | Task context. AI letters include the patient's name. Ceph images are sent to the vision model. |
| Stedi (clearinghouse) | Eligibility; claims and ERA | Subscriber/claim data. Live claim submission is off until a production key is set (`STEDI_LIVE_CLAIMS=False`); eligibility runs against Stedi test mode today. |
| Twilio | SMS (MFA, reminders, bundle messages) | Phone number, message text |
| Plaid | Bank linking / ACH | Bank-link tokens |
| QuickBooks Online | AP sync | Vendor/invoice data |
| Cloudflare | DNS and proxy in front of the site | Traffic metadata; see §6 item 3 |
| Offsite backup provider | Encrypted backups | Encrypted backup files |
| Dental Monitoring (only if built and enabled) | Remote monitoring | Scan data. Held on DM's platform. |

The earlier GTM line "no data sent to third-party cloud AI" was false and has been removed.

## 5. Data flow

```
Practice browser / MyOrthoChart ──TLS──> Cloudflare ──> nginx ──> OrthoFlow API (FastAPI)
                                                                     │
                      ┌───────────────┬──────────────┬───────────────┤
                      ▼               ▼              ▼               ▼
              PostgreSQL (PHI,   MinIO (documents,  Redis        Ollama (local
              practice_id)       images, ClamAV)    (cache/queue) embeddings only)
                                                                     │
        Outbound only, per feature:  Anthropic · Stedi · Twilio · Plaid · QuickBooks
        Edge appliance (future, imaging only) ──TLS──> imaging_ingest endpoint
```

## 6. Open items before making external claims

1. **Single host.** Production is one Mac Pro. The SLA target is 99.9% (about 43 minutes of unplanned downtime a month). One machine is a single point of failure for every practice. Confirm the backup restore test and a recovery-time estimate (`dr-test-procedure.md`) before quoting recovery commitments.
2. **BAAs with sub-processors.** `baa-policy.md` lists the clearinghouse and the offsite backup provider as needing a BAA, but does not list Anthropic, Twilio or Plaid. Anthropic receives patient names and images. Confirm each BAA is signed before saying "HIPAA compliant" in sales material. Say "BAA provided before go-live" instead.
3. **Cloudflare mode conflict.** `baa-policy.md` says Cloudflare is DNS-only with no PHI access. Shared security and PRD docs say the orange-cloud proxy is on. A proxy terminates TLS and can see traffic. Confirm the real setting and fix whichever document is wrong.
4. **Stale parent docs.** `docs/CLIENT_MANIFEST.md` (parent folder) says "self-hosted LLM, no data leaves your network" and a managed-cloud AI upgrade path. Both are wrong. `OrthoFlow_Architecture_and_Roadmap.md` is similarly stale. Neither was edited here (separate repo).
5. **Edge appliance.** Do not describe it as available.

## 7. Approved wording

> OrthoFlow runs on U.S. infrastructure operated by Melanin Technologies, not a shared public cloud. Every practice's data is isolated, encrypted, audit-logged and exportable on request. A BAA is signed before go-live. AI features send each task's context (for example the patient's name on a letter) to our AI provider, and staff review every AI output before anything leaves the practice.

Do not say: "data never leaves our network", "no third-party AI", "HIPAA certified", "data stays in your office".
