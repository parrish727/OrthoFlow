# OrthoFlow — Practice Onboarding Checklist

**Purpose:** Step-by-step checklist for onboarding a new orthodontic practice onto OrthoFlow.
Completed by Melanin Technologies during implementation. Each section gathers what we need from the practice to configure their environment.

---

## 1. Practice Information

| Item | Required | Notes |
|------|----------|-------|
| Practice name | ✅ | Displayed in app header |
| Practice address | ✅ | Used in communications + claim forms |
| Practice phone | ✅ | Used in patient messages |
| Practice NPI (Type 2) | ✅ | Required for insurance claims |
| Tax ID (EIN) | ✅ | Required for insurance claims |
| Practice logo | Optional | PNG/SVG for app branding |
| Business hours | ✅ | For quiet hours + scheduling |
| Time zone | ✅ | Appointment scheduling |

## 2. Provider Setup

| Item | Required | Notes |
|------|----------|-------|
| Doctor name(s) | ✅ | Rendering provider on claims |
| Doctor NPI(s) (Type 1) | ✅ | Required for insurance claims |
| Doctor license number + state | ✅ | Compliance |
| Dental assistant names | ✅ | DA assignment board |
| Number of chairs/operatories | ✅ | Schedule board columns |
| Chair names/colors | Optional | UI customization |

## 3. Account Setup

| Item | Required | Notes |
|------|----------|-------|
| Owner email | ✅ | Admin login |
| Owner password set | ✅ | Must meet complexity requirements |
| MFA enrolled (SMS OTP) | ✅ | Required for admin access |
| Staff accounts created | As needed | Role: manager, bookkeeper, DA |

## 4. Insurance & Clearinghouse

This determines which clearinghouse we integrate with for electronic claim submission.

### What the practice provides:

| Item | Required | Notes |
|------|----------|-------|
| Clearinghouse vendor name | ✅ | See options below |
| Clearinghouse login/credentials | ✅ | For API submission |
| Electronic submitter ID | ✅ | Assigned by clearinghouse |
| Payer enrollment list | ✅ | Which insurers they're enrolled to bill |
| BAA with clearinghouse | ✅ | Practice executes this (not us) |

### Recommended clearinghouses for orthodontics:

| Vendor | Strength | Ortho-Friendly |
|--------|----------|----------------|
| **Tesia (Vyne Dental)** | Dominant in dental, strong ERA/835 | ✅ |
| **DentalXChange** | Good dental focus, real-time eligibility | ✅ |
| **Availity** | Large payer network, free for basic | ⚠️ Medical-focused |
| **Office Ally** | Low cost ($35/mo), straightforward | ✅ |

### Why we need this:
- OrthoFlow generates the claim (837D format) and handles the workflow
- The clearinghouse transmits it to the insurance payer electronically
- They're the "postal service" for claims — we write the letter, they deliver it
- Each practice has their own enrollment because the clearinghouse validates their NPI + Tax ID

### If the practice doesn't have a clearinghouse:
- We recommend they enroll with Tesia or DentalXChange
- Enrollment takes 2-4 weeks (payer-specific)
- OrthoFlow claims can be created and tracked immediately — submission queues until enrollment completes

## 5. Imaging Setup (Optional — Phase 4b)

| Item | Required | Notes |
|------|----------|-------|
| X-ray machine make/model | If using auto-transfer | For DICOM config |
| Office network access | If using edge appliance | To install OrthoFlow Edge device |
| Current imaging software | Informational | What they're migrating from |

If using web upload only (Phase 4a): no setup needed — works immediately.

## 6. Data Migration (If Applicable)

| Item | Required | Notes |
|------|----------|-------|
| Current PMS vendor | Informational | Dentrix, Ortho2, Eaglesoft, Dolphin, etc. |
| Patient list export | If migrating | CSV or database export |
| Existing images | If migrating | DICOM export from current system |
| Historical claims | Optional | For reporting continuity |

## 7. Communications Setup

| Item | Required | Notes |
|------|----------|-------|
| Preferred reminder channel | ✅ | Email only until TCPA legal approved for SMS |
| SMTP credentials (if custom domain) | Optional | Otherwise uses OrthoFlow default sender |
| Reminder timing preference | ✅ | 24hr + 2hr default, customizable |
| Patient consent collection plan | ✅ | How they'll collect TCPA consent (once SMS enabled) |

## 8. QuickBooks Integration (If Using AP Module)

| Item | Required | Notes |
|------|----------|-------|
| QuickBooks Online account | ✅ | Not Desktop — must be QBO |
| Chart of accounts review | ✅ | Map ortho categories to GL codes |
| Authorize OrthoFlow OAuth | ✅ | One-click in Settings |

---

## Post-Onboarding Verification

- [ ] Practice can log in and see dashboard
- [ ] Chairs and DAs appear on schedule board
- [ ] Test patient created and visible
- [ ] Test image uploaded successfully
- [ ] Test appointment scheduled
- [ ] Email reminder delivered for test appointment
- [ ] Insurance plan added to test patient
- [ ] Eligibility check returns results
- [ ] Test claim created (draft status)
- [ ] QuickBooks connection verified (if applicable)

---

**Timeline:** Typical onboarding takes 1-2 weeks from kickoff to go-live, depending on clearinghouse enrollment status.
