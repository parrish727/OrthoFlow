# Vendor Security Architecture: Cloudflare, Twilio, Plaid, Stedi, AI Provider

**Date:** 2026-11-20 · **Prepared by:** Security research (web sources, primary vendor pages where available) plus a review of the contract folder.
This is research, not legal advice. Counsel should review every agreement. Items marked UNVERIFIED could not be confirmed.

## 1. BAA status by vendor
| Vendor | Signs a HIPAA BAA? | Conditions | Source |
|---|---|---|---|
| Cloudflare | Yes, **Enterprise only**, before PHI flows | HIPAA report covers WAF, DDoS, SSL/TLS, API Shield, rate limiting, CDN, DNS, Access, Tunnel, Zero Trust, Spectrum, Logs | cloudflare.com/trust-hub/compliance-resources/hipaa |
| Twilio | Yes, **HIPAA-eligible products only**, on Security or Enterprise Edition | Programmable SMS announced eligible in 2020; current product list UNVERIFIED (Verify, short codes, 10DLC) | twilio.com/docs/iam/twilio-editions/hippa |
| Plaid | **UNVERIFIED / not found** | Legal pages are GLBA and consumer oriented. Plaid's policy allows using data to train AI and develop insights | plaid.com/legal |
| Stedi | Yes, on upgrade from sandbox to a paid plan; MFA required | SOC 2 Type II and HIPAA eligibility announced 2023; current report UNVERIFIED | stedi.com/docs/providers/providers-account-setup |
| Anthropic | **Yes, self-serve BAA** (Claude Console) or negotiated via sales | Separate org for HIPAA work; Batch API, Files API, code execution and MCP connector not eligible; flagged content may be retained up to 2 years | platform.claude.com/docs (API and data retention) |

## 2. Recommended architecture
**Cloudflare.** The orange-cloud proxy puts Cloudflare in the PHI path (verified: `app`, `api` and both apex domains are proxied). Either sign an Enterprise BAA, or take PHI paths off the proxy: make `api.*` DNS-only and keep `app.*` proxied only for static assets, or use Tunnel plus Access (also Enterprise). If staying proxied: no-cache on API paths, restrict Logpush fields, Authenticated Origin Pulls (mTLS), allow only Cloudflare IPs at the origin, Full (strict) TLS, no PHI in URLs.

**Twilio SMS.** SMS is not end-to-end encrypted. Keep text generic. **Done:** collections reminders no longer carry a name, practice name, amount or day count; they only point to the signed-in portal. Keep links free of PHI and require sign-in. No third-party link shorteners. Sign the BAA and confirm each product used is on the eligible list.

**Plaid.** Bank numbers and balances are generally not PHI, but "this person pays an orthodontist" can reveal healthcare. Send no practice, procedure or claim fields; use an opaque `client_user_id` (we use the patient UUID); keep Plaid tokens out of clinical tables. Get Plaid's HIPAA position in writing. **Contract finding:** the draft reseller agreement covers Auth, Identity and Balance only. It does not cover Plaid Transfer, so the ACH debit path we scaffolded is outside the agreement, and money movement needs an originating bank and processor arrangement (Nacha obligations UNVERIFIED). The Oct 23 memo recommends "conditional go, negotiate first" because indemnity for every practice's data misuse is uncapped.

**Stedi.** Cleanest covered path. Keep eligibility, claims and ERA only on Stedi under the BAA. MFA, scoped keys, IP allowlist, and keep webhook payloads out of general logs.

**AI provider.** De-identification is in code now (`AI_DEIDENTIFICATION.md`). Research recommends BAA **and** de-identification as defense in depth. Free text and images are the weak spots; see that document.

## 3. Contract checklist
| Item | Cloudflare | Twilio | Plaid | Stedi | Anthropic |
|---|---|---|---|---|---|
| BAA before PHI | Required (Enterprise) | Required | Ask, or prove no PHI | Required | Optional while de-identified |
| Breach notice | ask 72h or less | 72h or less | 72h or less | 72h or less | 72h or less |
| Subprocessor flow-down | yes | yes | yes | yes | yes |
| Retention and deletion | logs, caches | message bodies | token deletion on disconnect | transaction retention | retention window |
| Audit evidence | HIPAA report (NDA) | security portal | SOC 2 | trust center | trust center |
HIPAA gives business associates up to 60 days to notify a covered entity. Practices usually demand much less, so vendor windows must be shorter than what we promise practices.

**OrthoFlow to practice:** BAA, MSA, security exhibit (encryption, MFA, audit logs, backups, breach window, deletion on termination) and a published subprocessor list with change notice. **None of these exist in the contract folder yet.**

## 4. Top controls to evidence (owner)
1 Vendor BAAs and inventory (Security) · 2 Risk analysis and register (Security) · 3 MFA, role-based access, quarterly review (Engineering) · 4 Tamper-resistant audit logs, reviewed (Engineering) · 5 Encryption and key management (DevOps) · 6 Backups with tested restore, offsite under BAA (DevOps) · 7 Incident plan, breach runbook and tabletop (Security) · 8 Vulnerability and patch management, image scanning (DevOps) · 9 AI de-identification with test evidence (AI/Backend) · 10 Training, sanctions, change management with PR approval (Owner).

**PCI DSS:** ACH only, so out of card scope. Never accept card numbers; mask card-like strings in free text and logs; if cards are added, use a hosted payment page.

## 5. Priority actions
1. **Critical:** Cloudflare, sign Enterprise BAA or take PHI paths off the proxy.
2. **Critical:** BAAs with Twilio, Stedi and the backup provider before PHI flows.
3. **High:** Decide on the Anthropic BAA (self-serve exists).
4. **High:** Plaid written HIPAA position; resolve ACH origination (the Plaid agreement does not cover Transfer).
5. **High:** Practice-facing BAA, MSA, security exhibit and subprocessor list.
6. **Medium:** Tabletop, backup restore test, evidence the top controls.

## Confidence and gaps
High confidence: Cloudflare Enterprise-only BAA, Anthropic self-serve BAA and feature limits, Twilio edition requirement, Stedi BAA on paid plan. Medium: Stedi SOC 2 currency. UNVERIFIED: Plaid HIPAA stance, Twilio current eligible list, Nacha/ODFI obligations, Safe Harbor details (HHS page unreachable), vendor breach windows.
