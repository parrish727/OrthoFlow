# MyOrthoChart — Patient-Facing Mobile App

## Product Vision

MyOrthoChart is the patient-facing companion app for OrthoFlow, similar to how Epic provides MyChart for healthcare offices. It gives patients a single portal to interact with their orthodontic/dental practice — and if their practice uses OrthoFlow, patients get MyOrthoChart automatically.

**Relationship to OrthoFlow:** MyOrthoChart is an extension of OrthoFlow, not a standalone product. Each practice on the OrthoFlow platform automatically provides MyOrthoChart access to their patients. Patients can have multiple office logins if they visit multiple OrthoFlow-network practices (same concept as MyChart supporting multiple provider logins).

## Target Users

- Orthodontic and dental patients (and parents/guardians for minors)
- Any practice on the OrthoFlow platform

## Core Features

### Phase 1 — Web (Browser-First)
1. **Pre-Visit Sign-In** — Complete intake forms, consent documents, and health history before arriving at the office
2. **Appointment Management** — View, schedule, reschedule, and cancel appointments
3. **Treatment Journey** — Visual progress tracker showing where they are in their orthodontic treatment (observation → bonding → active → finishing → retention → complete)
4. **Secure Messaging** — Message the office with questions; office staff can reply from OrthoFlow
5. **Medication Tracking** — View and track prescribed medications (pain management, antibiotics, etc.)
6. **Treatment Plan** — View current treatment plan details, estimated timeline, and next steps
7. **Document Access** — View signed forms, treatment agreements, and insurance documents
8. **Payment & Billing** — View balance, make payments, see insurance coverage
9. **Multi-Office Login** — Single app, multiple OrthoFlow-network practice accounts

### Phase 2 — Mobile Native (iOS + Android)
- Publish to Apple App Store and Google Play Store
- Push notifications (appointment reminders, message alerts, payment due)
- Biometric login (Face ID / fingerprint)
- Offline access to treatment timeline and documents
- Camera integration (upload photos for virtual check-ins)

## Architecture

```
┌──────────────────────────────────────────────┐
│              MyOrthoChart App                  │
│         (React PWA → React Native)            │
├──────────────────────────────────────────────┤
│                                              │
│  Browser (Phase 1)    │   Native (Phase 2)   │
│  - React + Vite       │   - React Native     │
│  - PWA-capable        │   - iOS + Android    │
│  - Responsive mobile  │   - Push notif       │
│                                              │
├──────────────────────────────────────────────┤
│            OrthoFlow Backend API              │
│          /api/v1/portal/* endpoints           │
│         (already exists, extend as needed)    │
├──────────────────────────────────────────────┤
│         OrthoFlow Practice Instance           │
│     (each practice = tenant in the system)    │
└──────────────────────────────────────────────┘
```

## Differentiation from OrthoFlow Staff UI

| Feature | OrthoFlow (Staff) | MyOrthoChart (Patient) |
|---------|-------------------|------------------------|
| Schedule | Full schedule, all patients | My appointments only |
| Messaging | Reply to all patients | Message my office |
| Treatment | Edit plans, notes, charts | View my progress |
| Billing | Manage ledgers, claims | View my balance, pay |
| Forms | Create forms, review submissions | Fill out my forms |
| Multi-tenant | One practice login | Multiple practice logins |

## Naming & Branding

- **Product name:** MyOrthoChart
- **Tagline:** "Your smile journey, in your pocket"
- **URL (web):** app.orthoflowsolutions.com/portal (already exists as patient portal)
- **Future URL:** myorthochart.com (when standalone app launches)
- **App Store name:** MyOrthoChart
- **Provided by:** OrthoFlow Solutions

## Rollout Strategy

1. **Now:** Patient portal at /portal (existing) — rebrand UI to "MyOrthoChart"
2. **Next:** Optimize messaging (MyOrthoChart-style inbox — in progress on feat/mychart-messaging)
3. **Then:** Add remaining features (medication tracking, treatment journey visualization)
4. **Finally:** Package as PWA → publish native apps to App Store / Play Store

## Technical Notes

- Patient auth: JWT + SMS OTP MFA (already implemented)
- Data scope: patient can only see their own data within a practice
- HIPAA compliant: audit logging on all data access, encrypted at rest
- The existing `/api/v1/portal/*` endpoints serve as the API layer
- Multi-office: patient account links to multiple practice portal_accounts
