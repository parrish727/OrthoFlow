# AI De-identification Layer

**Date:** 2026-11-20 · **Status:** In code. 135 backend tests pass, plus an end-to-end check of 7 real AI routes against a throwaway database with 20 identifiers planted (names, guardian, grandmother, staff name, DOB, five date formats, phones, email, member id, claim number, prior auth): zero reached the provider payload.

## Why
No BAA exists with the AI provider. So no identifier may leave our servers. The model works on placeholders; we put the real values back locally. Letters, appeals and notes come back accurate.

## How it works
1. A route creates a `DeidSession` and registers the patient, guardian and claim identifiers.
2. All prompts go through `services/anthropic_gateway.py`, the only code allowed to call the provider (a test enforces it).
3. The gateway scrubs the prompt, then **verifies** nothing identifying is left and refuses the request if anything is.
4. The model sees `[PATIENT_NAME]`, `[DATE_2]`, `[CLAIM_NO_1]` and a system note to reproduce placeholders exactly.
5. The answer is restored with real values before staff see it. The map lives in memory for one request only and is never stored or logged.

## What is replaced
| Data | Treatment |
|---|---|
| Patient, guardian, family names | Placeholders |
| Date of birth | Placeholder, plus age in years (age 90+ shown as "90 or older") |
| Dates in notes and appointments | Relative text ("42 days ago") when only timing matters, restorable placeholders when the answer needs the real date |
| Claim number, subscriber id, prior auth, ERA reference | Placeholders |
| SSN, email, phone, long ID numbers, "Mrs. Smith" style names | Placeholders |
| Staff-typed letter text, saved sample letters, typed context | Every proper noun tokenized (aggressive mode), restored after |
| Ceph images | Metadata stripped (EXIF, PNG text chunks) before sending; switchable with `CEPH_AI_CLOUD_ENABLED` |

Kept as is, because they are not identifiers: diagnoses, CDT codes, wire sizes, measurements, treatment phase, money amounts.

## Accuracy safeguards
Timeline-dependent reasoning gets explicit numbers (months in treatment, days from service to submission) instead of dates, so denial "timely filing" analysis still works. Restoration is an exact reverse.

## Known limits (be honest with practices and auditors)
- **Free-text clinical notes** can contain a name we never registered (a teacher, a friend). We catch registered family names, honorific names and patterns. Fully meeting HIPAA Safe Harbor for free text needs an NER pass or expert determination.
- **Images:** text burned into the film (a name on the ceph) cannot be removed. Turn off `CEPH_AI_CLOUD_ENABLED` where that is a concern; the long-term answer is self-hosted analysis.
- The model could refuse or reword a placeholder; staff always review output, and unresolved placeholders stay visible.

## Adding an AI feature
Create a `DeidSession`, register identifiers, call `gateway.complete(...)`. Never call the provider directly (the test will fail the build). Add the new route to the end-to-end leak check.

## Still true
The provider offers a self-serve BAA. Security recommends signing it and keeping this layer (defense in depth). Until then, do not claim "no patient data goes to the AI provider" without the limits above.
