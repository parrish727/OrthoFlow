# Subprocessors and Vendor Inventory

**Date:** 2026-11-20 · Maintained by Security. "Confirmed" means we saw it in a document. Everything else is a gap to close.

| Vendor | Purpose | Patient data involved | Agreement status | Notes |
|---|---|---|---|---|
| Cloudflare | DNS and proxy for orthoflowsolutions.com and melanin-tech.com (hud.melanin-tech.com is DNS-only) | All traffic to app and API, including PHI in transit | **No BAA.** Cloudflare signs BAAs for Enterprise only | Decide: Enterprise BAA, or take PHI paths off the proxy |
| Twilio | SMS (MFA, reminders, collections reminders) | Phone number, message text | **Not confirmed** | BAA needs HIPAA-eligible products on Security or Enterprise Edition. Text is now generic |
| Stedi | Eligibility, claims, ERA | Full claim and subscriber PHI | **Not confirmed in contract folder** | Stedi accepts a BAA on paid upgrade; confirm executed |
| Plaid | Bank connections, patient ACH | Bank account data; payee relationship to a healthcare provider | Draft reseller agreement (2026-10-23) has **no HIPAA/BAA language**; covers Auth, Identity, Balance, **not Plaid Transfer** | Countersignature status unknown. Get written HIPAA position |
| Anthropic | AI drafting | **None by design**: prompts are de-identified | No BAA; self-serve BAA is available | Keep de-identification regardless |
| Backup provider | Offsite encrypted backups | Encrypted PHI | **Not chosen** | Choose only a provider that signs a BAA |
| Twilio/Stedi/Plaid/Cloudflare sub-subprocessors | | | Collect lists | Needed for the practice subprocessor notice |

## Practice-facing documents (gap)
`BusinessDocs/Contracts` holds a banking resolution, NDA templates and the Plaid agreement. It has **no BAA template, MSA, security exhibit or subprocessor notice for practices.** These need to be drafted with counsel before real PHI flows. See `VENDOR_SECURITY_ARCHITECTURE_2026-11-20.md` §3 for what each must contain.
