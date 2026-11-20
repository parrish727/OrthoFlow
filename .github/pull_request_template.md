## What and why

## Security and compliance gate (required if this touches patient data, AI prompts, messaging, payments, auth, logging or infrastructure)
- [ ] New or existing third party receives patient data? It is in `docs/compliance/SUBPROCESSORS.md` with a signed agreement.
- [ ] AI prompts go through `anthropic_gateway` with a `DeidSession`; new identifier types registered.
- [ ] No PHI in URLs, query strings, logs, errors or SMS text.
- [ ] No card numbers accepted or stored; bank data kept out of clinical tables.
- [ ] New data is practice-scoped and audit-logged.
- [ ] Docs and marketing claims touched by this change are still true.
- [ ] Security review requested (required for main and production).
