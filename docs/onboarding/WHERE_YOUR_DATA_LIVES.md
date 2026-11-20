# Where Your Patient Data Lives (practice-facing)

A one-page workflow for practice owners, office managers and IT contacts. It answers: where is our data, who can see it, what is in our office, and what do I do if I want it moved or removed.

## The short version
Your patient data is stored on Melanin Technologies Inc. local infrastructure in the United States. It is not stored in your office and not on a shared public cloud. Your practice's records are kept separate from every other practice, encrypted, and every access is logged.

## Step 1: Pick your setup (done at onboarding)

| Option | What it means | Available |
|---|---|---|
| **Hosted by OrthoFlow** (default) | Everything runs on our servers. Your team uses a web browser. Nothing is installed in your office. | **Yes** |
| **Hosted + edge device / practice local server** | A small device sits in your office and connects to OrthoFlow. First use: capturing images from your imaging equipment and sending them to your OrthoFlow records. | Not yet. Ask us; it is planned. |
| **Fully on-site** | OrthoFlow runs entirely in your office. | Not available today. |

## Step 2: Know the path your data takes
1. Your team signs in at app.orthoflowsolutions.com. The connection is encrypted.
2. Traffic passes through Cloudflare (our network and security provider), then to our servers.
3. Records and files are stored on our servers, separated by practice.
4. Some features send information to partners to do their job: Stedi (insurance checks and claims), Plaid (bank connection for patient payments), our text-message provider (reminders and pay links), and our AI provider (letters and drafts your team reviews). We sign agreements with partners that handle patient information.

## Step 3: Your controls
- **Who sees what:** staff roles and permissions in Settings.
- **Automatic payment reminders:** on or off in Settings, chosen by the owner or doctor. Off by default.
- **Audit trail:** every access to patient data is logged. Ask us for a report.
- **Export:** ask us for a full export at any time.
- **Leaving:** after contract end your data is deleted within 30 days; backups age out on their schedule.

## Step 4: Who to contact
Questions about where data is, a copy of your Business Associate Agreement, or an export request: contact your OrthoFlow onboarding lead. Report anything that looks wrong right away.

*Internal source of truth for this page: `docs/specs/DATA_HOSTING_AND_LOCALITY.md`.*
