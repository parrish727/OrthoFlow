# OrthoFlow — Data Hosting & Locality

**Date:** 2026-11-20 · **Audience:** internal, and the basis for sales answers on "where is our data?"
Describes only what exists today. Open items that block some external claims are in §6.

## 1. Short answer

**Patient data is not stored in the practice's office.** It is stored on infrastructure that Melanin Technologies operates (a self-hosted server stack, not a shared public cloud). The practice uses OrthoFlow through a browser and does not host, back up or maintain anything.

We do **not** ship hardware to practices today. An office-side edge appliance (a small machine such as a Mac mini that calls our application) is the planned option. Today only its receiving endpoint exists (`imaging_ingest.py`, for imaging capture); the device and its software do not. "Hosted by us" is the current and only model. See `docs/onboarding/WHERE_YOUR_DATA_LIVES.md` for the practice-facing explanation.

Our hosting today is one Mac Pro. The plan is to move it to a server rack. Until that happens, treat the single-host risk in §6 as open.

## 2. Hosting models

| Model | What it is | Status |
|---|---|---|
| **A. OrthoFlow-operated hosting** | All practices run on our Docker stack (Postgres, Redis, MinIO) on self-hosted hardware, behind nginx. Each practice is isolated by `practice_id`. | **Live. This is the product.** |
| **B. Edge appliance (office device, e.g. Mac mini)** | On-site device that talks to our application. First job: capture DICOM/ceph from imaging equipment and upload to model A through `imaging_ingest.py`. Patient records stay on our stack unless a later design adds local caching. | Endpoint built. Device image, install and support process not built. |
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
| Anthropic (Claude API) | AI letters, referrals, timelines, claim/appeal drafting, clinical summaries, ceph auto-landmarking (image), CBCT interpretation | **Patient names in prompts today** (7 route files; DOB in referrals). Ceph images go to the vision model. See §4a. |
| Stedi (clearinghouse) | Eligibility; claims and ERA | Subscriber/claim data. Live claim submission is off until a production key is set (`STEDI_LIVE_CLAIMS=False`); eligibility runs against Stedi test mode today. |
| Twilio | SMS (MFA, reminders, bundle messages) | Phone number, message text |
| Plaid | Bank linking / ACH | Bank-link tokens |
| QuickBooks Online | AP sync | Vendor/invoice data |
| Cloudflare (proxy) | Proxies `orthoflowsolutions.com`, `www`, `app`, `api`. TLS terminates at Cloudflare's edge and again at our nginx. | All traffic to the app and API, including PHI in transit. `hud.melanin-tech.com` is DNS-only. Verified 2026-11-20. |
| Offsite backup provider | Encrypted backups | Encrypted backup files |
| Dental Monitoring (only if built and enabled) | Remote monitoring | Scan data. Held on DM's platform. |

The earlier GTM line "no data sent to third-party cloud AI" was false and has been removed.

### 4a. AI and patient identifiers (policy vs. code)
Policy intent: patient identifiers must not reach the AI provider. **The code does not meet that yet.** Verified 2026-11-20 in the prompts of `ai_letters.py` (patient name), `ai_assistant.py` (name), `ai_referrals.py` (name and date of birth), `ai_timeline.py`, `ai_intelligence.py` (name, plus a patient list with names), `ai_claims.py` and `appeal_automation.py` (claim patient name). Ceph auto-trace sends the image itself. `services/llm.py` also still contains a managed-cloud provider path that violates the no-cloud rule and should be deleted.

Fix options, in order of effort:
1. **Placeholder substitution:** send `[PATIENT]` or an opaque id, fill the real name back in locally after the response. Small change per route; removes direct identifiers. Free-text clinical notes can still contain names, so this is risk reduction, not de-identification.
2. **Full de-identification** (HIPAA Safe Harbor: names, dates, contact data, free-text scrubbing, stripping image metadata and burned-in text). Larger project.
3. **Sign the provider BAA** and keep sending what is needed. Required if (1) or (2) are not complete, since identifiers are being sent now.

Until one of these is done, do not say "no patient data is sent to the AI provider".

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
2. **BAAs with sub-processors.** `baa-policy.md` previously listed only the clearinghouse and the offsite backup provider (the governance PR adds Cloudflare, Anthropic, Twilio and Plaid/Stedi rows). Anthropic receives patient names and images today (§4a). Confirm each BAA is signed before saying "HIPAA compliant" in sales material. Say "BAA provided before go-live" instead.
3. **Cloudflare.** Resolved in the docs: the proxy is on for the OrthoFlow and Melanin domains (governance policies corrected, PR in the MelaninTech repo). Open question that follows: Cloudflare can see PHI in transit, so decide the BAA or conduit position and document it.
4. **Stale parent docs.** `docs/CLIENT_MANIFEST.md` (parent folder) says "self-hosted LLM, no data leaves your network" and a managed-cloud AI upgrade path. Both are wrong. `OrthoFlow_Architecture_and_Roadmap.md` is similarly stale. Neither was edited here (separate repo).
5. **Edge appliance.** Do not describe it as available.

## 7. Approved wording

> OrthoFlow runs on U.S. infrastructure operated by Melanin Technologies, not a shared public cloud. Every practice's data is isolated, encrypted, audit-logged and exportable on request. A BAA is signed before go-live. AI features send each task's context (for example the patient's name on a letter) to our AI provider, and staff review every AI output before anything leaves the practice.

Do not say: "data never leaves our network", "no third-party AI", "no patient data goes to the AI provider" (until §4a is fixed), "HIPAA certified", "data stays in your office".
