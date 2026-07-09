# OrthoFlow — Service Level Agreement (SLA)

**Effective Date:** 2026-07-09
**Provider:** Melanin Technologies Inc.
**Service:** OrthoFlow AI Practice Management Platform

---

## 1. Uptime Guarantee

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Monthly Uptime** | 99.9% | Calendar month, measured at 1-minute intervals |
| **Planned Maintenance** | < 2 hours/month | Scheduled outside business hours (10PM–6AM ET) |
| **Max Consecutive Downtime** | 15 minutes (unplanned) | Before auto-escalation triggers |

**99.9% uptime = maximum 43 minutes of unplanned downtime per month.**

### What counts as downtime:
- API returns 5xx errors for >50% of requests in a 1-minute window
- Login page unreachable from external monitoring
- Patient data inaccessible (reads fail)

### What does NOT count as downtime:
- Planned maintenance (communicated 48 hours in advance)
- Force majeure (natural disasters, ISP outages affecting entire region)
- Client-side issues (browser, device, local network)
- Third-party service degradation (Twilio, clearinghouse)

---

## 2. Incident Severity Classification

| Severity | Definition | Examples |
|----------|-----------|----------|
| **P1 — Critical** | Service completely unavailable, all users affected | API down, database unreachable, TLS expired |
| **P2 — High** | Major feature unavailable, workaround exists | Claims submission broken, imaging upload failing |
| **P3 — Medium** | Minor feature degraded, most users unaffected | Slow report generation, AI features delayed |
| **P4 — Low** | Cosmetic issue or minor inconvenience | UI alignment bug, non-critical notification delay |

---

## 3. Response & Resolution Targets (MTTR)

| Severity | Initial Response | Communication Update | Target Resolution |
|----------|-----------------|---------------------|-------------------|
| **P1** | 15 minutes | Every 30 minutes | 1 hour |
| **P2** | 30 minutes | Every 2 hours | 4 hours |
| **P3** | 4 hours | Daily | 24 hours |
| **P4** | 1 business day | Weekly | 5 business days |

---

## 4. Incident Communication Process

### Notification Channels:
1. **Status Page** — status.orthoflowsolutions.com (planned, real-time updates)
2. **Email** — automated to all practice administrators within response window
3. **In-App Banner** — degradation warning shown at top of application
4. **Slack** — internal team notification (immediate)

### Communication Template:

**Initial Notification:**
> 🔴 **OrthoFlow Incident — [Severity]**
>
> **Status:** Investigating
> **Impact:** [What users are experiencing]
> **Started:** [Time UTC / ET]
> **Affected:** [All users / Specific feature]
>
> We are actively investigating. Next update in [X minutes].

**Update Notification:**
> 🟡 **OrthoFlow Incident Update**
>
> **Status:** Identified / Mitigating
> **Root Cause:** [Brief description]
> **ETA to Resolution:** [Time estimate]
> **Workaround:** [If applicable]

**Resolution Notification:**
> 🟢 **OrthoFlow Incident Resolved**
>
> **Duration:** [Start to end]
> **Root Cause:** [What happened]
> **Resolution:** [What we did]
> **Prevention:** [What we're doing to prevent recurrence]

---

## 5. Infrastructure Reliability

### Self-Healing Mechanisms (Always Active):
| Mechanism | What It Does |
|-----------|-------------|
| Container restart policies | Auto-restart on crash (unlimited retries with backoff) |
| Health check endpoints | Every 30s, container replaced if 3 consecutive failures |
| Watchtower | Auto-deploy fixes from CI/CD without manual intervention |
| fail2ban | Blocks malicious traffic automatically |
| Certbot | TLS certificates auto-renewed 30 days before expiry |
| Cloudflare | DDoS mitigation at edge before traffic reaches origin |
| Database WAL + streaming | Point-in-time recovery within 5 minutes |

### Monitoring Stack:
- **HUD Dashboard** — real-time container health, 5-minute snapshots, 1-year retention
- **SRE Agent** — automated health verification after every deploy
- **QA Agent** — automated functional testing after every deploy
- **Deploy Webhook** — CI failure → Slack alert within 60 seconds

---

## 6. Planned Maintenance Windows

| Day | Window (ET) | Notice Required |
|-----|-------------|-----------------|
| Any weekday | 10:00 PM – 6:00 AM | 48 hours advance email |
| Saturday | 10:00 PM – 10:00 AM Sunday | 48 hours advance email |
| Emergency patch | Any time | Best-effort 1 hour notice |

**During maintenance:**
- In-app banner displayed 30 minutes before
- Expected duration communicated upfront
- Status page updated in real-time

---

## 7. Data Protection & Recovery

| Protection | Implementation | RPO/RTO |
|---|---|---|
| Database backups | Continuous WAL archiving + daily full backup | RPO: 5 min, RTO: 30 min |
| Object storage (images) | MinIO with replication | RPO: 0 (synchronous), RTO: 15 min |
| Configuration | Git-versioned, rebuildable from scratch | RTO: 20 min |
| Complete rebuild | Docker Compose from git + backup restore | Full RTO: 45 min |

---

## 8. SLA Credits

If monthly uptime falls below guaranteed threshold:

| Monthly Uptime | Service Credit |
|----------------|---------------|
| 99.0% – 99.9% | 10% of monthly fee |
| 95.0% – 99.0% | 25% of monthly fee |
| < 95.0% | 50% of monthly fee |

Credits applied to next billing cycle. Must be requested within 30 days.

---

## 9. Exclusions

This SLA does not apply to:
- Free trial or beta features
- Features explicitly labeled "experimental"
- Issues caused by customer modifications outside of OrthoFlow
- Third-party integrations (clearinghouses, Twilio) — governed by their own SLAs

---

## 10. Contact

| Type | Channel | Response |
|------|---------|----------|
| Emergency (P1) | support@orthoflowsolutions.com + status page | 15 min |
| Support | support@orthoflowsolutions.com | 4 hours (business hours) |
| Account | account@orthoflowsolutions.com | 1 business day |

---

*This SLA is a commitment from Melanin Technologies Inc. to every OrthoFlow practice. We eat our own dogfood — our monitoring agents hold us accountable to these targets 24/7.*
