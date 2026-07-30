# OrthoFlow AI — Product Requirements Document

**Version:** 1.0  
**Date:** July 28, 2026  
**Author:** Melanin Technologies Inc.  
**Status:** Production (Live at app.orthoflowsolutions.com)

---

## 1. Executive Summary

OrthoFlow AI is a comprehensive, AI-powered practice management system purpose-built for orthodontic and dental practices. Developed by Melanin Technologies Inc. (Black-owned software consulting firm, Wisconsin), it delivers a full-spectrum solution covering scheduling, patient records, clinical documentation, insurance claims, financial management, communications, and AI-assisted revenue cycle optimization — all within a HIPAA-compliant, self-hosted infrastructure.

The platform serves small to mid-size practices (1–10 providers) and includes MyOrthoChart, a patient-facing portal modeled after Epic's MyChart, providing patients with direct access to appointments, messaging, forms, treatment progress, and billing.

OrthoFlow is live in production, processing real clinical workflows with five role-based access tiers, multi-tenant practice isolation, and AI features powered by Anthropic Claude for denial analysis, appeal generation, clinical note summarization, and predictive intelligence.

---

## 2. Problem Statement

### Industry Pain Points

1. **Fragmented Software Stacks** — Practices juggle 4–7 separate systems for scheduling, charting, billing, imaging, and communications. Integration gaps cause data loss and staff inefficiency.

2. **Denial Revenue Leakage** — Orthodontic practices lose 5–12% of revenue to insurance denials that go uncontested due to time constraints and lack of expertise in writing appeals.

3. **Manual Administrative Burden** — Front desk and office managers spend 60%+ of their time on phone calls, paper forms, manual claim entry, and appointment coordination that could be automated.

4. **Legacy PMS Lock-in** — Dominant systems (Dolphin, OrthoTrac, Cloud 9) are expensive, inflexible, and owned by private equity. Practices have no negotiating power and limited customization.

5. **Patient Engagement Gap** — Patients expect the same digital experience they get from Epic MyChart (messaging, online forms, appointment management) but dental/ortho practices lack equivalent tooling.

6. **HIPAA Compliance Complexity** — Small practices cannot afford dedicated compliance staff. They need software that enforces HIPAA controls by design rather than relying on manual processes.

### Market Opportunity

- 10,500+ orthodontic practices in the US
- 200,000+ general/specialty dental practices
- Average practice spends $500–$2,000/month on combined software
- Growing mandate for electronic claims and digital patient engagement
- No dominant AI-native PMS exists in the orthodontic/dental space

---

## 3. Target Users

### Practice Staff (OrthoFlow)

| Role | Responsibilities | Key Features Used |
|------|-----------------|-------------------|
| **Owner** | Full system access, financials, staff management, configuration | All modules, reports, team management, time tracking |
| **Doctor** | Clinical workflows, treatment planning, notes, imaging | Patient records, clinical notes, tooth charts, imaging, AI intelligence |
| **Office Manager** | Scheduling, insurance, claims, communications, reports | Scheduling, insurance, claims, finance, reports, communications |
| **Dental Assistant** | Patient flow, chair-side charting, appointment prep | Patient flow board, clinical notes, appliance tracking |
| **Front Desk** | Check-in/out, scheduling, patient intake, payments | Scheduling, patient flow, communications, payment posting |

### Patients (MyOrthoChart)

| Segment | Needs |
|---------|-------|
| **Adult patients** | Self-service scheduling, secure messaging, payment, treatment visibility |
| **Parents/Guardians** | Child's treatment progress, form completion, appointment management |
| **Multi-office patients** | Unified portal across multiple OrthoFlow-network practices |

### Practice Profile

- **Size:** 1–10 providers
- **Specialties:** Orthodontics (primary), general dentistry. Future: periodontics, pediatric dentistry (backlog)
- **Geography:** United States
- **Tech maturity:** Varies (OrthoFlow handles migration from legacy systems)

---

## 4. Product Vision

**One platform. Every workflow. AI that earns its keep.**

OrthoFlow replaces the fragmented stack with a single, intelligent system that handles the entire practice lifecycle — from patient intake through treatment completion and final payment collection. AI is embedded at decision points where it delivers measurable ROI: denial recovery, clinical documentation, appointment optimization, and predictive analytics.

The patient experience mirrors what patients already expect from hospital systems: MyOrthoChart provides a clean, professional portal for self-service interactions, reducing phone volume and improving satisfaction.

### Design Principles

1. **Practice-scoped isolation** — Every data access is filtered by practice_id. No cross-tenant data leakage is architecturally possible.
2. **AI at the point of decision** — AI features activate where staff make choices (approve/deny, schedule, document) rather than requiring separate workflows.
3. **Progressive complexity** — Front desk sees a simple view; owners see everything. The same system serves all roles without overwhelming any single user.
4. **Offline-resilient** — Critical workflows (patient flow, scheduling) function with minimal latency regardless of AI service availability.
5. **Data ownership** — Practices own their data. Self-hosted infrastructure means no vendor lock-in or data hostage situations.

---

## 5. Feature Inventory

### 5.1 Practice Management Core

#### Multi-Tenant Architecture
- Practice creation and configuration
- JWT-based practice scoping (every API call filtered by practice_id)
- Practice-level settings: business hours, appointment types, chair configuration
- Demo environment with 5 role-based accounts (env-gated via `VITE_SHOW_DEMO_LOGIN`)

#### Role-Based Access Control (RBAC)
- Five roles: Owner, Doctor, Office Manager, Dental Assistant, Front Desk
- Granular permissions per module
- Role assignment and modification by Owner/Office Manager
- Session management with JWT + refresh tokens

#### Team Management
- Staff invitation (email-based onboarding)
- Role assignment and reassignment
- Account deactivation (soft delete, preserves audit trail)
- Staff directory with contact information

---

### 5.2 Patient Records

#### Demographics
- Full patient profile: name, DOB, contact, address, emergency contact
- Responsible party and guarantor tracking
- Patient status lifecycle management
- Search and filtering across patient database

#### Treatment Phases
- Orthodontic phase tracking: Observation → Pending → Active → Finishing → Retention → Complete
- Phase transition history with timestamps
- Multi-phase support (Phase 1, Phase 2 orthodontic treatment)
- Custom status support (Observation 1–4, Pending)

#### Tooth Charts
- Interactive dental chart (adult and pediatric numbering)
- Per-tooth condition tracking
- Treatment notation overlay
- Historical chart comparison

#### Alerts & Flags
- Patient-level alerts (allergies, medical conditions, behavioral notes)
- System-generated alerts (overdue appointments, outstanding balance)
- Priority levels and dismissal tracking

#### Document Management
- Upload and categorize patient documents
- Version tracking
- Signed form storage (intake, consent, financial agreements)
- MinIO-backed HIPAA-compliant file storage

---

### 5.3 Scheduling

#### Chair-Based Calendar
- Visual calendar with chair/operatory assignment
- Day, week, and month views
- Color-coded appointment types
- Provider and assistant assignment per appointment

#### Appointment Management
- Drag-and-drop scheduling
- Appointment type configuration (duration, required resources, CDT codes)
- DA (Dental Assistant) assignment to appointments
- Cancel, reschedule, and no-show tracking
- Schedule Next workflow (from checkout)

#### Patient Flow Board
- Real-time drag-and-drop board: Lobby → Seated → Checkout → Dismissed
- Visual patient status at a glance
- Timestamp tracking per stage
- Today's Huddle view (morning overview of the day's schedule)

#### Next Visit Planning
- Next Visit dropdown integrated with appointment types
- Suggested next visit based on treatment phase
- Recall scheduling for hygiene and follow-up

---

### 5.4 Clinical Documentation

#### Clinical Notes
- Per-patient, per-appointment note entry
- Rich text formatting
- Template-based note creation
- Historical note timeline

#### AI-Assisted Dictation Summary
- Voice-to-text transcription input
- AI summarization of clinical observations (Anthropic Claude)
- Structured output: chief complaint, findings, procedures, next steps
- One-click insertion into patient record

---

### 5.5 CDT Code Library

- 69 orthodontic and dental CDT codes loaded
- Full-text search by code number or description
- Category-based browsing (Diagnostic, Preventive, Restorative, Orthodontic, etc.)
- Fee schedule display per code
- Code-to-appointment-type mapping
- Used in claims, treatment plans, and scheduling

---

### 5.6 Insurance & Claims

#### Insurance Plan Management
- Patient insurance plan entry and verification
- Primary and secondary insurance support
- Subscriber information tracking
- Coverage details and benefit limits

#### Claim Lifecycle
- Claim creation from appointment/procedure
- CDT code mapping to claim line items
- Status tracking: Created → Submitted → Pending → Paid/Denied
- Batch claim review and submission

#### Prior Authorization
- Prior auth request creation
- Tracking and follow-up workflow
- Approval/denial status management
- Link to associated treatment plan

#### AI Denial Review
- Automated analysis of denial reason codes
- Recommended action per denial (appeal, resubmit, write off, call)
- Success probability scoring based on payer patterns
- Batch review for multiple denials simultaneously

#### AI Appeal Generation
- Professional appeal letter creation with clinical justification
- Auto-populated patient demographics, procedure details, and clinical rationale
- Payer-specific formatting and argumentation
- One-click generation, staff review before submission

#### Denial Pattern Analysis
- Payer-level denial trend visualization
- Common denial reasons by code and payer
- Historical approval/denial rates
- Actionable recommendations to reduce future denials

---

### 5.7 Finance

#### Patient Ledger
- Per-patient financial record
- Charge posting (linked to procedures/CDT codes)
- Payment posting (patient pay, insurance pay)
- Adjustment tracking (write-offs, discounts, credits)
- Running balance calculation

#### Payment Posting
- Manual payment entry (cash, check, card)
- ERA (Electronic Remittance Advice) import and auto-posting
- Batch payment processing
- Payment allocation to specific charges

#### Insurance Plan Tracking
- Benefit utilization tracking
- Annual maximum and remaining balance
- Deductible tracking
- Coordination of benefits for dual coverage

---

### 5.8 Communications

#### SMS & Email
- Appointment reminder automation (configurable timing)
- Template-based messaging (appointment confirmations, recalls, custom)
- Scheduled message delivery
- Delivery tracking and status (sent, delivered, failed)
- TCPA consent workflow compliance

#### Staff Messaging
- Real-time WebSocket-based chat rooms
- Practice-scoped messaging channels
- AI auto-reply capability (active for demo environments)
- Message history and search

#### Patient Messages (MyOrthoChart Style)
- Threaded inbox interface (staff ↔ patient)
- Conversation history per patient
- Staff can reply from within OrthoFlow
- Patient can message from MyOrthoChart portal
- Read receipts and notification delivery

---

### 5.9 MyOrthoChart Patient Portal

#### Patient Authentication
- Secure login with JWT + SMS OTP MFA
- Patient-scoped data access (own records only)
- Multi-office login support (multiple practice accounts)

#### Patient Dashboard
- Upcoming appointments overview
- Unread messages indicator
- Treatment progress summary
- Outstanding balance display

#### Appointments
- View scheduled appointments
- Request scheduling/rescheduling
- Appointment details (provider, location, type)

#### Messaging
- Secure messaging to practice staff
- Threaded conversations
- Attachment support

#### Forms
- Digital intake forms
- Health history questionnaire
- Consent documents (electronic signature)
- Financial agreement forms
- Pre-visit completion workflow

#### Treatment Progress
- Visual treatment journey tracker
- Current phase indication
- Estimated timeline and milestones

---

### 5.10 Imaging

#### Image Management
- Upload dental/orthodontic images (X-rays, photos, scans)
- Image viewing with zoom and annotation
- Categorization by type and date
- Patient-linked image library

#### AI Imaging Reasoning
- AI-assisted image analysis observations
- Flagging potential findings for doctor review
- Structured reasoning output for clinical context

#### Imaging Alerts
- Overdue imaging notifications
- Missing required images for treatment phase
- Quality flags on uploaded images

---

### 5.11 Reports & Analytics

#### Production Reports
- Daily/weekly/monthly production totals
- Production by provider
- Production by procedure/CDT code
- Goal tracking and variance analysis

#### Collections Reports
- Collections vs. production comparison
- Collection rate trending
- Outstanding AR summary

#### Accounts Receivable Aging
- 30/60/90/120+ day aging buckets
- By payer and by patient
- Follow-up prioritization

#### Provider Productivity
- Appointments per day/week
- Production per provider
- Chair utilization rates

---

### 5.12 Time Tracking & Payroll

#### Clock In/Out
- Staff time clock with punch-in/punch-out
- Break tracking
- Overtime calculation

#### Staff Hours
- Weekly hour summaries per staff member
- Historical timesheet records
- Edit and approval workflow

#### Payroll Summary
- Pay period calculations
- Pay rate configuration per staff member
- Export-ready payroll data

---

### 5.13 Data Migration

- Import tool for migrating from other PMS systems
- Patient record mapping
- Historical data preservation
- Validation and error reporting during import

---

### 5.14 Appliance Tracking (Orthodontic)

- Orthodontic appliance inventory and lifecycle
- Per-patient appliance assignment
- Status tracking: Ordered → Received → Placed → Adjusted → Removed
- Appointment association for placement/adjustment

---

### 5.15 Multi-Specialty Support

#### Periodontal Charting
- Full-mouth perio charting (6-point probing depths)
- Bleeding on probing, recession, furcation
- Historical comparison and trend visualization

#### Hygiene Recall
- Automated recall scheduling
- Recall due list and follow-up tracking
- Configurable recall intervals per patient

#### Restorative
- Restorative treatment tracking
- Procedure-specific documentation
- CDT code integration for restorative procedures

---

### 5.16 AI Intelligence Suite

#### Batch Insights
- Practice-wide performance analysis
- AI-generated observations on trends and anomalies
- Actionable recommendations for operational improvement

#### Treatment Timeline Prediction
- AI-estimated treatment completion dates
- Phase duration predictions based on historical data
- Alert when treatment is tracking behind schedule

#### Benchmarks
- Practice performance compared to industry benchmarks
- Identification of areas exceeding or underperforming norms
- Drill-down into specific metrics

#### Next Visit Intelligence
- AI-suggested next appointment type based on treatment phase
- Optimal scheduling window recommendations
- Resource requirement predictions

---

## 6. Technical Architecture

### System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  Client Layer                                                         │
│  ├── OrthoFlow Staff UI (React + Vite + Tailwind + TypeScript)       │
│  └── MyOrthoChart Portal (React + Vite, /portal routes)              │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ HTTPS (TLS 1.2+)
┌──────────────────────────▼───────────────────────────────────────────┐
│  API Layer — FastAPI Backend                                          │
│  ├── /api/v1/auth         — JWT + SMS OTP MFA                        │
│  ├── /api/v1/practices    — Multi-tenant management                  │
│  ├── /api/v1/patients     — Patient CRUD + search                    │
│  ├── /api/v1/scheduling   — Calendar + appointments                  │
│  ├── /api/v1/clinical     — Notes, charting, imaging                 │
│  ├── /api/v1/insurance    — Claims, denials, appeals                 │
│  ├── /api/v1/finance      — Ledger, payments, ERA                    │
│  ├── /api/v1/comms        — SMS, email, messaging                    │
│  ├── /api/v1/portal       — MyOrthoChart patient API                 │
│  ├── /api/v1/reports      — Analytics + exports                      │
│  ├── /api/v1/ai           — Intelligence endpoints                   │
│  └── /health              — Readiness/liveness probes                │
└────┬──────────┬──────────┬──────────┬──────────┬─────────────────────┘
     │          │          │          │          │
┌────▼───┐ ┌───▼────┐ ┌───▼───┐ ┌───▼────┐ ┌───▼─────────┐
│Postgres│ │ Redis  │ │ MinIO │ │ Ollama │ │  Anthropic  │
│16 +    │ │(cache/ │ │ (S3-  │ │(local  │ │  Claude API │
│pgvector│ │ queue) │ │ compat│ │ embed) │ │  (AI feat.) │
│+PgBoun.│ │        │ │ store)│ │        │ │             │
└────────┘ └────────┘ └───────┘ └────────┘ └─────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React + Vite + TypeScript (strict) + Tailwind CSS | Staff and patient UI |
| UI Components | Lucide React (icons), Framer Motion (animation) | Consistent design system |
| Backend | FastAPI + Pydantic (Python 3.11+) | API server with type safety |
| Database | PostgreSQL 16 + pgvector | Relational data + semantic search |
| Connection Pool | PgBouncer | Connection management, performance |
| Cache/Queue | Redis | Session cache, background job queue |
| File Storage | MinIO (S3-compatible) | HIPAA-compliant document/image storage |
| Local LLM | Ollama (nomic-embed-text) | Embeddings for semantic search |
| Production AI | Anthropic Claude (claude-haiku-4-5) | Denial review, appeals, notes, intelligence |
| Real-time | WebSocket | Staff messaging, patient flow updates |
| Auth | JWT + SMS OTP MFA | Authentication and session management |

### Infrastructure

| Component | Specification |
|-----------|--------------|
| Host | Mac Pro (16-core, 32GB RAM) |
| Containerization | Docker Compose |
| CI/CD | GitHub → GHCR → Watchtower (auto-deploy on image push) |
| DNS | Cloudflare (DDNS update every 5 min) |
| TLS | Let's Encrypt (auto-renewing) |
| Reverse Proxy | nginx (rate limiting, caching, TLS termination) |
| Network | Google Fiber (1Gbps symmetric) |
| Monitoring | Health checks, container restart policies, SRE agent |

### Data Architecture

- **Multi-tenant isolation:** Every table includes `practice_id` foreign key. ORM-level query filtering prevents cross-tenant access.
- **Audit logging:** All data access logged with user ID, IP, timestamp, action, and affected resource.
- **Encryption at rest:** AES-256 for PHI fields, MinIO server-side encryption for stored files.
- **Encryption in transit:** TLS 1.2+ on all connections (external and internal where PHI flows).
- **Backups:** PostgreSQL automated backups with point-in-time recovery.

### AI Architecture

```
Patient/Staff Action → FastAPI Endpoint → Anthropic Claude API (direct httpx)
                                        ↓
                              Structured Response → UI Display
```

- **Direct integration:** OrthoFlow calls Anthropic Claude directly (no intermediary proxy)
- **Model:** claude-haiku-4-5 for all client-facing AI (fast, cost-effective)
- **Local embeddings:** Ollama nomic-embed-text for semantic search (duplicate detection, similarity)
- **Fallback:** AI features gracefully degrade if API is unreachable (non-blocking)
- **No PHI storage by Anthropic:** Data in transit only, not retained

---

## 7. Security & Compliance

### HIPAA Compliance Controls

| HIPAA Requirement | Implementation |
|-------------------|---------------|
| Access Control (§164.312(a)) | JWT + RBAC with practice-scoped claims; MFA for patient portal |
| Audit Controls (§164.312(b)) | Comprehensive audit logging on all PHI access |
| Integrity (§164.312(c)) | Immutable audit records, versioned document storage |
| Transmission Security (§164.312(e)) | TLS 1.2+ enforced on all endpoints, HSTS preload |
| Encryption at Rest | AES-256 for PHI fields, MinIO server-side encryption |
| Minimum Necessary | Role-based field visibility (e.g., front desk cannot access full clinical notes) |
| Unique User Identification | Individual accounts required, no shared credentials |
| Automatic Logoff | Session timeout with JWT expiration |

### Authentication & Access

- **Staff:** Email/password + JWT session tokens
- **Patients:** Email/phone + SMS OTP MFA
- **Demo accounts:** Environment-gated, non-production credentials
- **Session management:** Short-lived access tokens + refresh token rotation

### Network Security

- HSTS preload on all public domains
- fail2ban active (10 failed attempts → 1-hour ban)
- Rate limiting via nginx (30 requests/minute general, 5 requests/minute forms)
- Internal services on isolated Docker bridge network (no public port exposure)
- Cloudflare proxy for DDoS mitigation

### Data Protection

- Patient data scoped to practice (architectural isolation, not just row-level filtering)
- No cross-practice queries possible at ORM level
- File storage encrypted at rest (MinIO + AES-256)
- Database connections encrypted (TLS between services)
- No PHI in logs, error messages, or client-side storage

### Compliance Documentation

- TCPA consent workflow for SMS communications
- Medicare/Medicaid billing compliance specification
- SLA and uptime guarantee documentation
- Data retention and destruction policies

---

## 8. Success Metrics

### Business Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Denial recovery rate | 40%+ of denied claims recovered via AI appeals | Claims recovered / total denials |
| Practice onboarding time | < 2 weeks from signup to production use | First patient record to first claim submitted |
| Monthly active practices | Growth month-over-month | Unique practice logins per month |
| Staff time saved | 10+ hours/week per practice on admin tasks | Before/after workflow timing |

### Product Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| System uptime | 99.9% (< 43 min/month downtime) | Health check monitoring |
| API response time (p95) | < 2 seconds | k6 load testing, production monitoring |
| Error rate | < 5% | Failed requests / total requests |
| Patient portal adoption | 60%+ of active patients registered | Portal accounts / active patients |
| AI feature usage | 80%+ of eligible denials reviewed by AI | AI reviews / total denials |

### Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Appeal letter accuracy | Clinical justification accepted by payer 70%+ | Successful appeals / total appeals sent |
| Appointment no-show rate | Reduce by 30% via automated reminders | No-shows with reminders vs. without |
| Form completion (pre-visit) | 50%+ of patients complete forms before arrival | Pre-visit completions / total new patients |

---

## 9. Roadmap

### Currently In Development

| Feature | Status | Target |
|---------|--------|--------|
| Stedi clearinghouse integration | In development | Electronic claim submission + same-day appeals |
| MyOrthoChart native mobile app | In development | iOS and Android via React Native |

### Planned (Backlog, Not Started)

| Feature | Priority | Description |
|---------|----------|-------------|
| Virtual visits | Backlog | Video call infrastructure (evaluating Daily.co, LiveKit, Twilio Video) |
| On-call routing | Backlog | Emergency virtual visit routing |
| Fully local AI | Backlog | Replace Anthropic with Mistral Small 24B local (zero API cost) |

### Completed (Production)

All features listed in Section 5 (Feature Inventory) are deployed and operational as of July 2026.

---

## 10. Competitive Landscape

### Direct Competitors

| Competitor | Strengths | Weaknesses | OrthoFlow Advantage |
|-----------|-----------|-----------|---------------------|
| **Dolphin Imaging** | Market leader in ortho, imaging focus | Expensive, legacy architecture, no AI | AI-native, modern UI, lower cost |
| **Cloud 9 Ortho** | Cloud-based, ortho-specific | PE-owned, limited customization, no AI claims | Self-hosted option, AI denial recovery, data ownership |
| **OrthoTrac (Carestream)** | Large install base | Desktop-only, end-of-life trajectory | Web-native, mobile-ready, actively developed |
| **Dentrix (Henry Schein)** | Dominant in general dentistry | Expensive, complex, not ortho-focused | Ortho-first design, simpler onboarding |
| **Open Dental** | Open source, affordable | Requires local server, limited AI, dated UI | Modern AI features, cloud-ready, patient portal |

### Differentiators

1. **AI-Native Revenue Cycle** — Denial review, appeal generation, and pattern analysis built into the claims workflow (not a bolt-on add-on).
2. **MyOrthoChart Patient Portal** — MyChart-equivalent experience that dental/ortho patients expect but don't currently get.
3. **Multi-Specialty in One System** — Orthodontics, perio, hygiene, and restorative in a single platform with shared patient records.
4. **Data Ownership** — Self-hosted infrastructure means practices own their data with no vendor lock-in.
5. **Modern Developer Experience** — React + FastAPI + PostgreSQL stack enables rapid feature development (vs. competitors on legacy .NET/Java).
6. **Transparent Pricing** — No per-seat gouging, no surprise fees, no PE-driven price increases.
7. **Black-Owned Business** — Minority-owned enterprise bringing diversity to a market dominated by large corporations.

### Market Position

OrthoFlow occupies the intersection of:
- **AI-powered** (vs. legacy systems with no intelligence)
- **Ortho-first** (vs. general dental systems adapted for ortho)
- **Practice-owned data** (vs. cloud-only vendors who hold data hostage)
- **Modern UX** (vs. dated interfaces that require days of training)

---

## Appendix A: Glossary

| Term | Definition |
|------|-----------|
| CDT | Current Dental Terminology — standardized procedure codes |
| DA | Dental Assistant |
| ERA | Electronic Remittance Advice — electronic payment explanation from insurance |
| JWT | JSON Web Token — authentication mechanism |
| MFA | Multi-Factor Authentication |
| OTP | One-Time Password (SMS-based) |
| PgBouncer | PostgreSQL connection pooler |
| pgvector | PostgreSQL extension for vector similarity search |
| PHI | Protected Health Information (HIPAA-defined) |
| PMS | Practice Management System |
| RBAC | Role-Based Access Control |

## Appendix B: Demo Environment

| Account | Role | Email |
|---------|------|-------|
| Owner | Practice Owner (full access) | demo@orthoflowsolutions.com |
| Doctor | Clinical Provider | demo-doctor@orthoflowsolutions.com |
| Office Manager | Administrative Lead | demo-manager@orthoflowsolutions.com |
| Dental Assistant | Clinical Support | demo-da@orthoflowsolutions.com |
| Front Desk | Reception | demo-frontdesk@orthoflowsolutions.com |

Demo practice: Brightsmile Orthodontics  
Demo login accessible when `VITE_SHOW_DEMO_LOGIN=true` (non-production environments)

## Appendix C: Production URLs

| Service | URL |
|---------|-----|
| OrthoFlow App (Staff) | https://app.orthoflowsolutions.com |
| OrthoFlow API | https://api.orthoflowsolutions.com |
| MyOrthoChart Portal | https://app.orthoflowsolutions.com/portal |
| Marketing Site | https://orthoflowsolutions.com |

---

*This document reflects the production state of OrthoFlow AI as of July 28, 2026. It does not contain aspirational features or unbuilt capabilities.*
