# Remote Job Intelligence

An independent Apify Actor that normalizes current remote-job listings from
public feeds. It keeps the original source and application URL so a consumer
can verify every record.

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
  "keywords": ["python", "ai"],
  "locations": [],
  "maxAgeDays": 14,
  "limit": 50,
  "includeDescription": false
}
```

`keywords` match the job title, company, tags, and (when requested) job description.
`locations` match the normalized location and source location restrictions.
An empty filter means all matching remote listings. Results are deduplicated by
canonical application URL, then by a normalized company/title pair.

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
