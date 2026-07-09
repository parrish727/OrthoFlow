# Clearinghouse Vendor Guide

Guide for orthodontic practice owners setting up electronic claims submission with OrthoFlow.

## What Is a Clearinghouse?

A clearinghouse is a third-party intermediary that routes electronic insurance claims between your practice and insurance payers. It:

- Translates your claim data into the standardized HIPAA 837D format
- Validates claims before submission (catches errors that would cause rejections)
- Routes claims to the correct payer
- Returns Electronic Remittance Advice (ERA/835) with payment details
- Provides real-time eligibility verification

**Why you need one:** Insurance payers do not accept claims directly from practice software. A clearinghouse is the required bridge between OrthoFlow and every insurance company you bill.

## Recommended Vendors for Orthodontics

| Vendor | Strengths | Dental/Ortho Focus | Notes |
|--------|-----------|-------------------|-------|
| **Tesia** | High payer connectivity, fast ERA turnaround | Yes — dental-specific | Preferred for most ortho practices |
| **DentalXChange** | Large dental payer network, real-time eligibility | Yes — dental-only | Strong attachment support (X-rays, narratives) |
| **Vyne Dental (formerly Tesia)** | Enterprise features, multi-location support | Yes — dental-specific | Good for DSO/multi-practice groups |
| **Availity** | Broad payer network (medical + dental) | General (supports dental) | Best if you also bill medical codes |

All vendors above support HIPAA 837D (dental claim format) and ERA/835 (remittance).

## What You Need to Provide

| Item | What It Is | Where to Get It |
|------|-----------|-----------------|
| **NPI (Type 1)** | National Provider Identifier — individual dentist/orthodontist | NPPES registry (already have this) |
| **NPI (Type 2)** | Organization NPI — the practice entity | NPPES registry |
| **Tax ID (EIN)** | Federal Employer Identification Number | IRS assignment letter |
| **Payer Enrollments** | Approval from each insurance company to submit electronically | Via clearinghouse enrollment forms |
| **Electronic Submitter ID** | Assigned by payer after enrollment | Payer provides after approval |
| **Practice License** | State dental/ortho license number | State dental board |

## Business Associate Agreement (BAA)

A BAA is a HIPAA-required contract between two parties that handle Protected Health Information (PHI).

**You need a BAA with your clearinghouse** because they receive and transmit patient insurance data (subscriber IDs, diagnosis codes, treatment history) on your behalf.

**You do NOT need a BAA with OrthoFlow** because OrthoFlow is self-hosted on your infrastructure (or Melanin Technologies' managed infrastructure). The data never leaves the hosting environment to reach a third-party SaaS — OrthoFlow is the software, not a data processor.

| Relationship | BAA Required? | Reason |
|-------------|---------------|--------|
| Practice ↔ Clearinghouse | ✅ Yes | They transmit PHI to payers |
| Practice ↔ OrthoFlow | ❌ No | Self-hosted; no third-party data transfer |
| Practice ↔ Payers | ❌ No | Provider-payer relationship, not BA |

## CMS Compliance (Medicare/Medicaid Claims)

If your practice accepts Medicare or Medicaid, additional requirements apply:

### Format Requirements

| Requirement | Detail |
|-------------|--------|
| Claim format | HIPAA 837D (X12 5010 dental) |
| NPI validation | Required on all claims — validated against NPPES |
| Taxonomy code | 1223X0400X (Orthodontics and Dentofacial Orthopedics) |
| Place of service | 11 (Office) for most ortho |

### Filing & Compliance

| Rule | Detail |
|------|--------|
| Timely filing | Varies by payer: Medicare = 365 days from DOS, Medicaid = varies by state (typically 90–180 days) |
| Coordination of Benefits (COB) | Primary must adjudicate before secondary submission; OrthoFlow tracks COB order |
| Prior authorization | Required for most orthodontic treatment under government plans; must be obtained BEFORE treatment starts |
| Medical necessity | Orthodontic claims require documentation of malocclusion severity (HLD index for Medicaid) |
| Frequency limitations | Orthodontic benefits typically limited to one course of treatment per lifetime |

### OrthoFlow Handles

- HIPAA 837D claim generation from treatment records
- NPI validation (Luhn algorithm check)
- Timely filing deadline tracking and alerts
- COB order management
- Prior authorization status tracking

## Setup Steps

### Step 1: Choose a Clearinghouse Vendor

Select from the recommended vendors above based on your practice size and payer mix. Request a demo and pricing.

### Step 2: Enroll with Payers

After signing with your clearinghouse:
- Complete payer enrollment forms for each insurance company you bill
- Enrollment takes 2–6 weeks per payer
- Your clearinghouse provides the forms and submits them on your behalf
- You receive an Electronic Submitter ID from each payer upon approval

### Step 3: Execute BAA with Clearinghouse

- Sign the BAA provided by your clearinghouse (they all have a standard one)
- Keep a copy in your HIPAA compliance records
- BAA must be signed BEFORE any PHI is transmitted

### Step 4: Provide Credentials to OrthoFlow

Once enrolled, provide your OrthoFlow administrator:
- Clearinghouse API credentials (username, password, or API key)
- Submitter ID(s) for enrolled payers
- Practice NPI (Type 1 and Type 2)
- Tax ID

These are stored encrypted in OrthoFlow's configuration — never in plain text.

### Step 5: Test with a Sample Claim

- OrthoFlow submits a test claim (clearinghouses have test/sandbox modes)
- Verify the claim is accepted and routed correctly
- Confirm ERA response is received and parsed
- Move to production submission

## What OrthoFlow Does for You

Once your clearinghouse enrollment is complete, OrthoFlow handles all technical aspects:

| Task | Manual? |
|------|---------|
| Generate 837D claim from treatment data | Automatic |
| Validate claim before submission | Automatic |
| Submit to clearinghouse via API | Automatic |
| Receive and parse ERA/835 responses | Automatic |
| Post payments to patient ledger | Automatic |
| Detect claim denials | Automatic (AI) |
| Draft appeal letters for denials | Automatic (AI) |
| Track filing deadlines | Automatic (alerts) |
| Re-submit corrected claims | One-click |

**The practice just needs to be enrolled.** OrthoFlow handles the rest.
