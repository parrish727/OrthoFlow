# Standard Operating Procedures: Claims & Appeals Workflow

**Product:** OrthoFlow AI  
**Audience:** Dental Office Staff (Front Desk, Office Manager, Billing)  
**Version:** 1.0  
**Date:** July 28, 2026  
**System:** app.orthoflowsolutions.com

---

## 1. Claim Submission

### When to Submit a Claim

Submit a claim after any billable appointment or procedure is completed and documented in OrthoFlow. Claims should be submitted the same day the service is rendered.

### What You Need

Before submitting, confirm the following is on file for the patient:

- Active insurance plan (primary and/or secondary)
- Subscriber information (name, ID, group number, DOB)
- CDT procedure codes for the rendered services
- Clinical documentation (progress notes, tooth chart updates)
- Prior authorization number (if applicable)

### How to Submit

1. Navigate to **Insurance & Claims** from the left sidebar.
2. Click **New Claim** or open the patient record and select the **Claims** tab.
3. Verify the system has auto-populated:
   - Patient demographics
   - Insurance plan details
   - CDT codes from the completed appointment
   - Provider (rendering and billing NPI)
4. Review all line items for accuracy. Correct any CDT codes or date-of-service errors.
5. Click **Validate** — OrthoFlow runs pre-submission checks against X12 5010 formatting rules. Fix any flagged issues before proceeding.
6. Click **Submit Claim**. The claim is electronically transmitted to the payer via our Stedi clearinghouse integration.
7. The claim status changes to **Submitted**. A confirmation with transaction ID appears on screen.

### Batch Submission

For end-of-day processing:

1. Go to **Insurance & Claims → Batch Review**.
2. Review all claims created during the day.
3. Select claims to submit (or use **Select All**).
4. Click **Batch Submit** to send all selected claims simultaneously.

---

## 2. Claim Status Monitoring

### Status Definitions

| Status | What It Means | Expected Timeline |
|--------|--------------|-------------------|
| **Created** | Claim is saved but not yet submitted to the payer | Submit same day |
| **Submitted** | Claim sent electronically; awaiting payer acknowledgment | Acknowledgment within 24–48 hours |
| **Pending** | Payer received and is processing the claim | 14–30 days for adjudication |
| **Paid** | Payer approved and issued payment (ERA received) | Payment posts within 5 business days of approval |
| **Denied** | Payer rejected the claim; denial reason code provided | See Section 3 below |
| **Appealed** | An appeal has been submitted for a denied claim | 30–45 days for appeal decision |
| **Resubmitted** | Claim was corrected and resubmitted | Restarts the 14–30 day adjudication window |
| **Written Off** | Claim balance has been written off per practice policy | Final — no further action |

### How to Monitor

1. Navigate to **Insurance & Claims → Status Dashboard**.
2. Use filters to view claims by status, date range, payer, or provider.
3. Claims approaching payer timely-filing deadlines are highlighted in yellow (60 days) and red (30 days remaining).
4. Review the **Aging Report** weekly to identify claims stuck in Pending status beyond 30 days.

### Real-Time Updates

OrthoFlow receives electronic status updates (277 transactions) from payers automatically. When a claim status changes, the dashboard updates in real time — no manual checking required.

---

## 3. Handling Denials

### Auto-Notification

When a denial is received:

1. OrthoFlow immediately updates the claim status to **Denied**.
2. A notification appears in-app (bell icon, top-right) for the assigned billing staff.
3. A Slack alert is sent to your practice's billing channel (if configured).
4. The denial reason code and payer explanation are attached to the claim record.

### AI Review (Automatic)

Within minutes of receiving a denial, OrthoFlow's AI engine:

1. Analyzes the denial reason code (e.g., CO-4, CO-16, CO-50, PR-1).
2. Reviews the original claim against the patient's clinical documentation.
3. Assigns a **recommended action**:
   - **Appeal** — strong case for overturn; AI drafts the letter
   - **Resubmit** — claim had a correctable error (missing info, wrong code)
   - **Call Payer** — issue requires human-to-human resolution
   - **Write Off** — low probability of overturn; not worth pursuing
4. Provides a **success probability score** (percentage) based on historical payer patterns.
5. Results appear on the denial detail screen within 5 minutes of denial receipt.

### Staff Review

The AI does NOT submit anything without your approval. After AI review completes:

1. Open the denied claim from the **Denials Queue** (Insurance & Claims → Denials).
2. Review the AI recommendation and success probability.
3. Choose one of the following actions:
   - **Approve Appeal** — proceeds to appeal generation (see Section 4)
   - **Modify Appeal** — edit the AI-drafted letter before submission
   - **Resubmit** — correct the claim and resubmit
   - **Call Payer** — mark for manual follow-up
   - **Write Off** — close with write-off adjustment

---

## 4. Appeal Process

### Same-Day Workflow

OrthoFlow is designed to turn around appeals the same day a denial is received. Target: less than 4 hours from denial receipt to appeal submission.

### Steps

1. **AI Generates Appeal Letter** (automatic after staff clicks Approve Appeal):
   - Professional letter with clinical justification
   - Auto-populated patient demographics and procedure details
   - Payer-specific formatting (each payer has preferred argumentation style)
   - Supporting clinical evidence attached (X-rays, photos, narratives from MinIO)

2. **Staff Reviews the Appeal**:
   - Open the generated appeal from the **Pending Appeals** queue.
   - Read the full letter. Verify clinical details are accurate.
   - Edit any section if needed (clinical narrative, procedure rationale).
   - Attach additional supporting documents if available.

3. **Staff Approves Submission**:
   - Click **Approve & Submit Appeal**.
   - The appeal is transmitted electronically to the payer via Stedi.
   - Claim status changes to **Appealed**.
   - Submission timestamp and transaction ID are logged.

4. **Track Appeal Outcome**:
   - Appeal decisions typically arrive within 30–45 days.
   - OrthoFlow receives the response electronically and updates the status.
   - If approved: payment posts automatically via ERA.
   - If denied again: AI recommends next steps (second-level appeal or write-off).

### Important Rules

- **Never submit an appeal without reading it first.** The AI drafts; you approve.
- **Appeals must be submitted within the payer's appeal filing deadline** (usually 60–180 days from denial). OrthoFlow tracks these deadlines and warns you.
- **All appeal activity is logged** in the audit trail for compliance purposes.

---

## 5. ERA Processing

### What Is an ERA?

An Electronic Remittance Advice (ERA / 835 transaction) is the electronic version of an Explanation of Benefits (EOB). It tells you what the payer paid, adjusted, or denied for each claim line.

### Auto-Posting

1. ERAs are received electronically from payers via webhook.
2. OrthoFlow automatically matches ERA line items to the corresponding claims.
3. Payments are posted to the patient ledger with the correct allocation:
   - Insurance payment applied to specific charges
   - Contractual adjustments posted
   - Patient responsibility (copay, deductible, coinsurance) calculated
4. The claim status updates to **Paid** (full payment) or triggers a follow-up if underpaid.

### Reconciliation

Perform ERA reconciliation weekly:

1. Navigate to **Finance → ERA Reconciliation**.
2. Review auto-posted payments for accuracy.
3. Flag any discrepancies:
   - Payment amount differs from expected contractual rate
   - Line items that didn't match a claim in the system
   - Duplicate payments
4. Resolve flagged items:
   - Adjust the posting if the ERA is correct but your records were off
   - Contact the payer if the ERA appears incorrect
5. Mark the ERA batch as **Reconciled** when all items are cleared.

### Manual Payment Posting

For payments received by paper check or patient payments:

1. Navigate to the patient's **Ledger** tab.
2. Click **Post Payment**.
3. Select payment type (cash, check, card, insurance check).
4. Enter amount and allocate to specific charges.
5. Save. The ledger balance updates immediately.

---

## 6. Compliance & Audit Reminders

### Audit Trail

Every claims action in OrthoFlow is automatically logged:

- Claim creation, submission, and resubmission
- Denial receipt and AI review results
- Appeal generation, staff edits, and submission
- ERA receipt and payment posting
- Write-offs and adjustments
- Who performed each action and when

**Retention:** All audit records are retained for 6 years per HIPAA requirements.

### Timely Filing

- Most payers require initial claims within **90–365 days** of date of service (varies by payer).
- Appeals must be filed within **60–180 days** of denial (varies by payer).
- OrthoFlow tracks these deadlines per payer and alerts you at 60 days and 30 days remaining.
- **Never let a claim expire.** Check the aging report weekly.

### HIPAA Compliance

- All claim data is transmitted via encrypted channels (TLS 1.2+).
- Patient information is visible only to staff with appropriate role permissions.
- Do not share claim details, appeal letters, or patient information via unsecured email or messaging.
- Use OrthoFlow's built-in communication tools for all claims-related correspondence.

### Weekly Checklist

| Task | Frequency | Who |
|------|-----------|-----|
| Review Denials Queue and act on AI recommendations | Daily | Billing staff |
| Check Pending Appeals for responses | Daily | Billing staff |
| Run Aging Report — follow up on claims >30 days Pending | Weekly | Office Manager |
| Reconcile ERA postings | Weekly | Office Manager |
| Review timely-filing warnings | Weekly | Billing staff |
| Audit write-off log for appropriateness | Monthly | Owner / Office Manager |
| Review Denial Pattern Analysis for payer trends | Monthly | Office Manager |

### Escalation

If you encounter any of the following, escalate to the Office Manager or Owner immediately:

- Payer consistently denying valid claims (pattern of bad faith)
- ERA payment amounts significantly below contracted rates
- System errors preventing claim submission or appeal generation
- Timely filing deadline within 7 days on an unresolved claim

---

## Questions?

Contact your OrthoFlow administrator or reach out to Melanin Technologies support for system-related issues.

---

*This document is maintained by Melanin Technologies Inc. Last updated: July 28, 2026.*
