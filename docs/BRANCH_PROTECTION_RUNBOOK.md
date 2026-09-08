# Branch Protection Runbook (Rulesets)

> **Status for OrthoFlow right now:** **NOT enforced.** Define the ruleset in **Disabled**
> (or **Evaluate**) mode so we keep shipping fast. Flip to **Active** once a release schedule
> is in place. See "Enforcement staging" below.

This runbook is a **standard DevOps step for every deployable project repo**. Branch rulesets
are configured **per repository** (GitHub Settings → Rules → Rulesets) — they do not apply
across repos unless the repos live under a GitHub **organization** with org-level rulesets.

---

## When to enforce

- **Do NOT set Active** while the project needs fast, frequent direct changes and has **no
  release schedule** yet (current OrthoFlow state).
- **Set Active** once the project has a release cadence and the team is working through the
  `feature → develop → main → production` flow. Requires pktech_dev go-ahead.
- Until then: create the ruleset in **Disabled** (staged, does nothing) or **Evaluate** (logs
  what *would* be blocked, still doesn't block) so it's ready to activate in one click.

## Enforcement staging (the key setting)

GitHub rulesets have an **Enforcement status** with three values:

| Status | Effect | Use when |
|--------|--------|----------|
| **Disabled** | Ruleset exists, does nothing | Staging now — zero friction |
| **Evaluate** | Rules run + log to Insights, but do NOT block | Want visibility before enforcing |
| **Active** | Fully enforced (blocks non-compliant pushes/merges) | Release schedule in place |

**Now:** create it as **Disabled** (or Evaluate). **Later:** change Enforcement to **Active**.

## The standard ruleset

`GitHub → repo → Settings → Rules → Rulesets → New branch ruleset`

```
Name:               protected-branches
Enforcement status: Disabled        ← staged; change to Active when ready
Target branches:    include by pattern →  main   and   production
Bypass list:        Repository admin (Allow)     ← lets pktech_dev do escalated merges

Rules:
  ☑ Restrict deletions
  ☑ Block force pushes
  ☑ Require a pull request before merging
        Required approvals: 1
        ☑ Dismiss stale approvals when new commits are pushed
        ☑ Require review from Code Owners        (uses .github/CODEOWNERS)
  ☑ Require status checks to pass
        add check:  test        ← the CI job name in .github/workflows/ci.yml
        ☑ Require branches to be up to date before merging
  ☑ Require linear history   (optional — keeps history clean)
```

**Notes**
- Add the **`test`** check, NOT `build`. `build` only runs on `production`; requiring it on
  `main` PRs would deadlock them. The status check must have run at least once to appear.
- `develop` and `feature/*` are intentionally NOT targeted — agents move freely there. If you
  later want `develop` gated too, add a separate lighter ruleset (PR + 1 approval, no admin
  bypass needed).

## Activating later (one-time, when release schedule exists)

1. Settings → Rules → Rulesets → open `protected-branches`.
2. Change **Enforcement status** → **Active**.
3. Save. From this point, `main` and `production` are PR-only with required `test` + Code Owner
   review; direct pushes and force pushes are blocked (except admin bypass).

## Org-level option (future)

If OrthoFlow (and other projects) move under a GitHub **organization**, define this ruleset
**once at the org level** and target repos by pattern — it then auto-applies to every repo
instead of per-repo setup. Recommended once there are several deployable repos.
