# Remote Jobs Aggregator API

Aggregate and deduplicate fresh remote-job listings from four public feeds in
one run. The normalized dataset includes source attribution, direct application
URLs, salary when published, employment type, seniority, timezone restrictions,
and categories for recruiter alerts, job boards, market research, and AI agents.

[Run the public daily software-jobs example](https://apify.com/ai-coding-radar/remote-job-intelligence/examples/daily-remote-software-jobs).

## Use cases

- **Remote jobs aggregator API:** power a niche job board, recruiter pipeline,
  or hiring-data product with one JSON/CSV/Excel feed instead of four scrapers.
- Build a daily remote-jobs digest with n8n, Make, Zapier, or the Actor API.
- Feed a job board or recruiter workflow with deduplicated listings.
- **Remote salary and hiring research:** compare the salary, seniority, category,
  and location signals that public sources expose.
- Export the Apify dataset as JSON, CSV, or Excel for research and reporting.
- Give an AI agent structured records without logging in to job sites.

## Automation recipes

- Import the [n8n webhook digest workflow](examples/n8n-remote-jobs-webhook.json)
  and connect its response to Slack, email, a database, or a job board.
- Follow the [Make scheduled-digest recipe](examples/README.md) for a
  scheduler, HTTP request, JSON parsing, and delivery modules.

Both recipes use the caller's own Apify API token; no token or private delivery
URL is stored in this repository.

## Sources

- Arbeitnow public job-board API (remote listings only)
- Jobicy public remote-jobs API
- Remote OK public API
- Himalayas public jobs API

The Actor does not log in, use cookies, bypass CAPTCHAs, submit applications,
or rewrite a source's description. Each output record includes an attribution
URL. Consumers must render that URL as a normal follow link and keep each
provider's source credit and API terms. Job descriptions are untrusted source
data; the default output omits them so downstream automation does not ingest
instructions hidden in a listing.

## Input

```json
{
  "sources": ["arbeitnow", "jobicy", "remoteok", "himalayas"],
  "keywords": ["software"],
  "keywordMatchMode": "all",
  "locations": [],
  "maxAgeDays": 7,
  "limit": 20,
  "includeDescription": false
}
```

`keywordMatchMode` defaults to `all`, preserving the strict legacy behavior. Set
it to `any` when a search should match at least one keyword. Every keyword is
matched against the job title, company, tags, locations, or (when requested)
the job description, so use one broad term for a strict daily alert or `any`
for a wider recruiter search.
`locations` match the normalized location and source location restrictions.
An empty filter means all matching remote listings. Results are deduplicated by
canonical application URL, then by a normalized company/title pair. When more
than one source is selected, the newest unique records are merged round-robin
by source so a high-volume feed does not hide the other selected feeds. The run
status reports a source warning when a public feed is unavailable.

Each row can include `salary`, `jobType`, `employmentType`, `seniority`,
`timezoneRestrictions`, and `categories`; fields remain empty when a source did
not publish them.

## Pricing note

The primary billable event is one returned job record. The launch price is
`$0.001` per record, plus `$0.00005` when a run starts. Platform usage is
included in that price. No revenue is claimed by this repository.

## Local checks

```sh
python3 -m unittest discover -s tests -v
python3 -m remote_job_intelligence --fixture tests/fixtures/sample.json
```

The fixture command is offline. A live run is only performed by the Apify
runtime and fails when every selected source is unavailable.
