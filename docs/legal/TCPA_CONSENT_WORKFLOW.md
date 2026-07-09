# OrthoFlow — TCPA Consent Workflow
## For Legal Review

**Prepared:** 2026-07-09
**Status:** SMS DISABLED until legal approval
**Reviewer:** [Legal Team]
**Product:** OrthoFlow AI — Patient Communications Module

---

## 1. Overview

OrthoFlow sends automated text messages (SMS) to patients for:
- Appointment reminders (24 hours and 2 hours before)
- Appointment confirmation requests ("Reply YES to confirm")
- Recall reminders (patients due for follow-up)
- Optional: birthday messages

All SMS is transmitted via Twilio (BAA executed). Messages are practice-branded and sent from the practice's designated phone number.

---

## 2. What We Collect

| Data Point | Purpose | Storage |
|---|---|---|
| Mobile phone number | SMS delivery | Encrypted in PostgreSQL |
| Consent status (yes/no) | TCPA compliance gate | `communication_preferences.tcpa_consent` |
| Consent date/time | Audit trail | `communication_preferences.tcpa_consent_date` |
| Consent method | Proof of consent | `communication_preferences.tcpa_consent_method` |
| Opt-out date/time | Compliance record | `communication_preferences.tcpa_opt_out_date` |
| Message history | Delivery verification | `message_log` table (retained 3 years) |

---

## 3. How Patients Opt In

### Method A: Electronic (during registration/check-in)
- Patient registers on OrthoFlow patient portal or checks in on tablet
- Consent checkbox displayed with the following language:

> **Text Message Consent**
>
> By checking this box, I consent to receive automated text messages from [Practice Name] regarding appointment reminders, confirmations, and practice communications at the mobile number provided. Message frequency varies. Message and data rates may apply. Reply STOP at any time to opt out. Reply HELP for assistance. This consent is not a condition of receiving treatment.

- Timestamp and method ("electronic") recorded on consent

### Method B: Written (paper form)
- Practice collects signed consent form during intake
- Staff records consent in OrthoFlow: `POST /api/v1/communications/preferences/{patient_id}/consent`
- Method recorded as "written"

### Method C: SMS Keyword (double opt-in)
- Practice provides number, patient texts "START" or "JOIN"
- System responds with consent confirmation message:

> "[Practice Name]: You've opted in to appointment reminders. Msg frequency varies. Msg&data rates may apply. Reply STOP to cancel, HELP for help."

- Method recorded as "sms_keyword"

---

## 4. What Messages Say

### Appointment Reminder (24hr)
> "Hi {patient_name}, this is {office_name}. Reminder: you have an appointment tomorrow at {appointment_time}. Reply YES to confirm or call {office_phone} to reschedule."

### Appointment Reminder (2hr)
> "{office_name}: Your appointment is in 2 hours at {appointment_time}. See you soon! Reply STOP to opt out."

### Confirmation Request
> "{office_name}: Can you confirm your appointment on {appointment_date} at {appointment_time}? Reply YES to confirm or CANCEL to cancel."

### Recall Reminder
> "Hi {patient_name}, {office_name} here. You're due for your next orthodontic visit. Call {office_phone} or reply to schedule. Reply STOP to opt out."

---

## 5. How Patients Opt Out

### STOP Keyword (Primary Method)
- Patient replies **STOP** to any message
- System immediately:
  1. Sets `sms_enabled = false`
  2. Records `tcpa_opt_out_date = NOW()`
  3. Cancels all pending scheduled SMS for this patient
  4. Sends final confirmation: "You've been unsubscribed from {office_name} text messages. You will not receive further texts. Reply START to re-subscribe."
  5. No further SMS is sent under any circumstance

### Also recognized opt-out keywords:
- STOP, UNSUBSCRIBE, CANCEL, END, QUIT

### Staff-initiated opt-out:
- Staff can opt a patient out via `POST /api/v1/communications/preferences/{patient_id}/opt-out`
- Same immediate effect as STOP keyword

### Opt-out is permanent until re-consent:
- Patient must explicitly re-consent (text START or provide new written consent)
- Staff cannot override a patient opt-out without new consent documentation

---

## 6. HELP Response

When patient texts **HELP**:
> "{office_name} appointment reminders. For help, call {office_phone}. Msg frequency varies. Msg&data rates may apply. Reply STOP to cancel."

---

## 7. Data Retention

| Data | Retention Period | Justification |
|---|---|---|
| Consent records | 5 years after last interaction | TCPA statute of limitations (4 years) + 1 year buffer |
| Message log (sent/received) | 3 years | Dispute resolution |
| Opt-out records | Permanent (never deleted) | Must never re-message an opted-out patient |
| Phone numbers | Until patient requests deletion or 2 years after last visit | Minimum necessary |

---

## 8. Technical Safeguards

| Control | Implementation |
|---|---|
| No SMS without consent | `tcpa_consent = true` is checked before every send |
| Quiet hours enforced | No messages sent between `quiet_start` and `quiet_end` (default 9PM-8AM) |
| Immediate STOP processing | Handled at the webhook level before any business logic |
| Rate limiting | Max 3 messages per patient per day |
| Audit trail | Every message logged with timestamp, delivery status, and patient response |
| Consent proof | Date, time, method, and IP (for electronic) stored permanently |

---

## 9. Questions for Legal

1. Is the electronic consent language (Section 3, Method A) sufficient for TCPA express written consent under current FCC rules?
2. Should we require separate consent for appointment reminders vs. marketing messages?
3. Is the 3-year message retention period adequate, or should it align with the 5-year consent retention?
4. Do we need to include the practice's physical address in any messages?
5. For Method C (double opt-in via SMS keyword) — is the confirmation message sufficient, or do we need a follow-up written consent?
6. Are there state-specific requirements beyond federal TCPA we should address (e.g., Florida, California)?

---

## 10. To Enable SMS After Approval

Once legal approves the consent workflow:
1. Set `SMS_ENABLED=true` in the OrthoFlow `.env` file
2. Rebuild the backend container
3. Ensure Twilio credentials are configured (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`)
4. Practices must collect consent from patients before sending first message

---

*This document is for legal review only. SMS functionality is disabled in production until written approval is received.*
