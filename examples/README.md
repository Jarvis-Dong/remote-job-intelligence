# Automation recipes

These examples call the public Apify Actor API with the caller's own API token.
They do not contain a token, cookie, browser session, or private webhook URL.
Each run uses the caller's Apify account and is subject to the Actor's current
Store price.

## Three purchase-intent recipes

Choose the input that matches the product you are building. Each recipe uses
only public feeds and keeps the source and application links in the result.

### 1. Remote jobs aggregator API for recruiters and job boards

Use a broad role term and `any` matching when a pipeline should find either
keyword. The output is a deduplicated feed with salary and hiring metadata when
the source publishes it.

```json
{
  "sources": ["arbeitnow", "jobicy", "remoteok", "himalayas"],
  "keywords": ["python", "backend"],
  "keywordMatchMode": "any",
  "locations": [],
  "maxAgeDays": 7,
  "limit": 50,
  "includeDescription": false
}
```

### 2. Daily remote job alerts with n8n, Make, or Zapier

Use one broad term with the strict default for a predictable daily digest. The
workflow can deliver the normalized rows to Slack, email, a database, or a job
board that you control.

```json
{
  "keywords": ["software"],
  "keywordMatchMode": "all",
  "maxAgeDays": 7,
  "limit": 20,
  "includeDescription": false
}
```

### 3. Remote salary and hiring research

Query sources that commonly publish compensation or hiring metadata, then
export the dataset for analysis. Missing salary is a valid value; it is never
inferred.

```json
{
  "sources": ["jobicy", "remoteok", "himalayas"],
  "keywords": ["engineer"],
  "keywordMatchMode": "any",
  "locations": [],
  "maxAgeDays": 30,
  "limit": 100,
  "includeDescription": false
}
```

## n8n: webhook to a remote-job digest

Import [`n8n-remote-jobs-webhook.json`](./n8n-remote-jobs-webhook.json) in n8n.
The workflow accepts a request, runs the Actor's synchronous dataset endpoint,
and returns both `digestText` and the normalized `jobs` array. Connect the
response to Slack, email, a database, or an internal job board in your own
workflow.

### One-time setup

1. On **Receive remote jobs request**, create/select an n8n **Header Auth**
   credential. The imported workflow requires this credential so an exposed
   webhook cannot spend your Apify balance without authorization. Send the
   credential's header on each request.
2. Set `APIFY_API_TOKEN` in the n8n runtime and restart n8n. If your n8n
   installation blocks environment variables in expressions, configure the
   supported Header Auth credential instead and replace the `Authorization`
   header on **Run Remote Jobs Actor**. Never commit the token to the workflow
   export.
3. Activate the workflow and copy the **Production URL** shown by the
   **Receive remote jobs request** node.
4. POST a request such as:

   ```sh
   curl -X POST 'https://YOUR_N8N_HOST/webhook/remote-jobs' \
     -H 'X-Webhook-Key: YOUR_PRIVATE_VALUE' \
     -H 'content-type: application/json' \
     -d '{"keywords":["software"],"keywordMatchMode":"all","maxAgeDays":7,"limit":20}'
   ```

   `sources`, `keywordMatchMode`, `locations`, `maxAgeDays`, `limit`, and `includeDescription`
   follow the Actor input schema. Omitted values default to all four sources,
   `software`, seven days, 20 records, and no descriptions.

The endpoint is deliberately a webhook rather than a hard-coded destination:
you can call it from a scheduler, Make, or another n8n workflow and keep your
delivery channel private.

## Make: scheduled digest recipe

Create a new scenario with these modules:

1. **Scheduler**: run once each morning (or choose the cadence your use case
   needs).
2. **HTTP > Make a request**:
   - Method: `POST`
   - URL: `https://api.apify.com/v2/acts/ai-coding-radar~remote-job-intelligence/run-sync-get-dataset-items?clean=1`
   - Header: `Authorization: Bearer YOUR_APIFY_API_TOKEN` stored in a Make
     connection or secret field, not in a public template.
   - Header: `Accept: application/json`
   - Body type: `application/json`
   - Body:

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

3. **JSON > Parse JSON**: map the HTTP response array. Keep `url` or
   `applyUrl` as the normal follow link and retain `sourceName`/`sourceUrl` as
   attribution.
4. **Array aggregator** (optional): build a short digest from `jobTitle`,
   `company`, `locations`, `salary`, and `url`.
5. **Slack, email, Notion, or HTTP**: deliver the digest to a destination you
   control. Add deduplication in Make if the same jobs are intentionally sent
   on more than one cadence.

Make's HTTP module may return an empty array when no matching listing is
available; treat that as a valid result, not a failed run. A 401 or 402 response
means the token is missing/invalid or the account cannot authorize the paid
run. The Actor never submits applications or rewrites source descriptions.
