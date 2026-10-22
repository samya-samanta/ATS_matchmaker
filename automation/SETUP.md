# Daily search and résumé workflow

## Status

This is the agreed specification, not a running service. `workflow-config.json` records the user's preferences; the current application does not consume it. The existing Remotive-only scheduler does not implement this workflow. No hosting, email sender, company-source connectors, or two-agent production scheduler has been configured.

## Daily outputs

Use `America/Chicago` every day, including weekends, following College Station daylight-saving changes. Prepare work before the reporting deadlines; do not begin the entire search at 10 AM or all tailoring at 5 PM.

- **10 AM:** Email a table of up to 10 verified open positions, company, title, location, posting date, employer link, initial estimated match score, fit rationale, and authorization/sponsorship evidence or uncertainty. Report any shortfall honestly.
- **5 PM:** Email the same shortlist, ranked by final estimated match score, with Word/PDF links for jobs initially scoring strictly above 50. Include before/after scores, evidence, gaps, and any jobs not tailored or failed. Target above 90 without fabricating experience; deliver the honest achievable score if below target.

Search the U.S., Canada, Europe, and Singapore, with relocation allowed. Prioritize the chemistry areas in the configuration. Include postdocs and exclude contract jobs; distinguish ordinary fixed-term university postdoctoral appointments from staffing-agency/consulting contracts. Exclude explicit permanent-U.S.-authorization requirements and jobs explicitly incompatible with OPT. Prioritize documented future sponsorship; silence is not proof of OPT acceptance. Label unknown eligibility. Assess other countries' requirements separately.

Only include postings demonstrably no older than 10 days and still open. Store employer requisition IDs/canonical links and reporting history to avoid cross-source and daily duplicates. If fewer than 10 new qualifying jobs exist, report fewer. Never substitute old, duplicate, or unverifiable listings to meet the quota.

## Sources and LinkedIn Premium

User-provided employer career URLs will be added to `search.company_websites`. Prefer original employer postings for full descriptions, dates, and application status. Use permitted feeds/APIs where available. Save retrieval timestamps and source evidence.

LinkedIn Premium does not itself provide a job-search API or authorize automated account browsing. LinkedIn saved-search alerts and user-shared job links can supply leads, followed by employer-site verification. Automated alert ingestion would require a separately configured mailbox/forwarding integration. Do not request a LinkedIn password or session cookie, bypass access controls, or claim access merely because Premium is available. Company URLs can be supplied in plain text; no credentials are needed for public listings.

## Recommended hosting and email

**Hosting** means a computer in the cloud that keeps working when the user's laptop and this chat are closed. Use a small paid, always-on managed background worker (for example Render), with persistent storage for the scheduler and duplicate history. Keep the initial workflow email-based; add a private authenticated dashboard later if wanted. A temporary coding session is not the host. GitHub stores code and generated files; merely pushing code there does not run the agents.

**Email** needs an authorized sending service. Recommended: an email API such as Resend, using a sender domain the user owns and verifies. Messages can go to the requested Gmail address; the recipient does not need an account with that provider. If the user has no domain and prefers sending from Gmail, use a Gmail OAuth integration instead, with its separate setup and token handling. No sender is currently connected.

A developer must still implement the two jobs, source adapters, evidence-based scoring/tailoring, persistent scheduler, document rendering, repository uploads, and email delivery. The existing Docker image is not a finished worker for this design. Use timezone-aware scheduling, durable per-day job IDs, retries that avoid duplicate emails, status logs, and failure notifications. Exact inbox arrival cannot be guaranteed by hosting or email providers.

### Account and setup checklist

1. Choose a monthly operating budget before provisioning paid services. Hosting, model API usage, any paid job-data feed, and possibly a sender domain are separate costs; confirm current provider prices. A ChatGPT subscription should not be assumed to cover model API charges.
2. Create the managed-host account and connect this GitHub repository. Deploy only after the worker is implemented and tested. Provision persistent storage and keep one scheduler instance active.
3. Configure a model API key for résumé analysis/tailoring and any permitted job-source API credentials needed. Use official employer feeds when available; do not assume every company website supports unattended collection.
4. Configure the email service and verified sender, or Gmail OAuth. Store credentials only in the host's secret settings, never in chat, source control, or résumé files.
5. Give the hosted worker a scoped GitHub App installation or fine-grained token limited to the required repository and file-writing permissions. This coding session's GitHub access will not automatically transfer to the host. Save generated documents under `resumes/daily/YYYY-MM-DD/`, with stable job IDs in filenames.
6. Confirm the approved master résumé/CV and preserve the formatting/publication requirements in `AGENTS.md`. Generated files in a public repository will be public; use private storage/repository if that visibility is unsuitable.
7. Before enabling daily runs, verify a live search, evidence and eligibility filters, duplicate handling, actual two-page PDF rendering, Word formatting, GitHub links, delivery to the specified email address, retry behavior, and Chicago daylight-saving scheduling. Mark the service active only after deployment and end-to-end verification.

## Disclosed scoring approach

Scores are estimated job alignment, never an employer's ATS result or a hiring probability. Proposed default rubric: required technical experience 40, demonstrated research/work relevance 25, education and seniority 15, preferred skills 15, and document clarity/parsing 5. Publish the job-specific criteria and weights before scoring. Give credit only for evidence from the résumé/CV, with partial credit explained. Use identical criteria and weights before and after tailoring; keyword repetition earns no additional credit. Evaluate work authorization as a separate eligibility gate, not a cosmetic score penalty. Tailoring may improve how existing evidence is expressed; it cannot erase substantive experience gaps.

## Scope boundary

Only two agents are requested now: search and résumé tailoring. Do not submit applications, create candidate accounts, accept application attestations, or contact recruiters. The user may commission a separate application agent later; that is not current authorization.
