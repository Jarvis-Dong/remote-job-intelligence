"""Fetch and normalize public remote-job feeds."""

from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable


SOURCES = {
    "arbeitnow": "https://www.arbeitnow.com/api/job-board-api",
    "jobicy": "https://jobicy.com/api/v2/remote-jobs",
    "remoteok": "https://remoteok.com/api",
    "himalayas": "https://himalayas.app/jobs/api",
}
SOURCE_META = {
    "arbeitnow": {"name": "Arbeitnow", "url": "https://www.arbeitnow.com/"},
    "jobicy": {"name": "Jobicy", "url": "https://jobicy.com/"},
    "remoteok": {"name": "Remote OK", "url": "https://remoteok.com/"},
    "himalayas": {"name": "Himalayas", "url": "https://himalayas.app/"},
}
USER_AGENT = "remote-job-intelligence/0.1 (+https://apify.com/)"
HTML_TAG = re.compile(r"<[^>]+>")
SPACE = re.compile(r"\s+")
NON_WORD = re.compile(r"[^a-z0-9]+")


def _text(value: Any) -> str:
    if value is None:
        return ""
    value = html.unescape(str(value))
    return SPACE.sub(" ", HTML_TAG.sub(" ", value)).strip()


def _list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [_text(value)] if _text(value) else []
    if isinstance(value, (list, tuple)):
        return [_text(item) for item in value if _text(item)]
    return [_text(value)] if _text(value) else []


def _timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    raw = str(value).strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).astimezone(timezone.utc)


def _iso(value: Any) -> str | None:
    parsed = _timestamp(value)
    return parsed.isoformat().replace("+00:00", "Z") if parsed else None


def _url(value: Any) -> str:
    raw = str(value or "").strip()
    parsed = urllib.parse.urlparse(raw)
    return raw if parsed.scheme in {"http", "https"} and parsed.netloc else ""


def _key(value: str) -> str:
    return NON_WORD.sub("-", value.lower()).strip("-")


def _salary(raw: dict[str, Any], source: str) -> dict[str, Any] | None:
    if source == "himalayas":
        minimum, maximum = raw.get("minSalary"), raw.get("maxSalary")
        currency, period = raw.get("currency"), raw.get("salaryPeriod")
    elif source == "remoteok":
        minimum, maximum = raw.get("salary_min"), raw.get("salary_max")
        currency, period = None, None
    else:
        return None
    if minimum in (None, "") and maximum in (None, ""):
        return None
    return {
        "min": minimum,
        "max": maximum,
        "currency": _text(currency) or None,
        "period": _text(period) or None,
    }


def normalize_job(raw: dict[str, Any], source: str, include_description: bool = False) -> dict[str, Any] | None:
    """Map one provider record to the stable public output shape."""
    if source == "arbeitnow":
        title, company, location = raw.get("title"), raw.get("company_name"), raw.get("location")
        tags, published, url, apply_url = raw.get("tags"), raw.get("created_at"), raw.get("url"), raw.get("url")
        remote = bool(raw.get("remote"))
        description = raw.get("description")
        source_id = raw.get("slug") or url
    elif source == "jobicy":
        title, company, location = raw.get("jobTitle"), raw.get("companyName"), raw.get("jobGeo")
        tags, published, url, apply_url = raw.get("jobIndustry"), raw.get("pubDate"), raw.get("url"), raw.get("url")
        remote = True
        description = raw.get("jobDescription") or raw.get("jobExcerpt")
        source_id = raw.get("id") or raw.get("jobSlug") or url
    elif source == "remoteok":
        title, company, location = raw.get("position"), raw.get("company"), raw.get("location")
        tags, published, url, apply_url = raw.get("tags"), raw.get("date") or raw.get("epoch"), raw.get("url"), raw.get("apply_url") or raw.get("url")
        remote = True
        description = raw.get("description")
        source_id = raw.get("id") or raw.get("slug") or url
    elif source == "himalayas":
        title, company, location = raw.get("title"), raw.get("companyName"), raw.get("locationRestrictions")
        tags, published, url, apply_url = raw.get("categories"), raw.get("pubDate"), raw.get("guid"), raw.get("applicationLink") or raw.get("guid")
        remote = True
        description = raw.get("description") or raw.get("excerpt")
        source_id = raw.get("guid") or f"{raw.get('companySlug', '')}:{title}"
    else:
        raise ValueError(f"unsupported source: {source}")

    canonical_url = _url(apply_url) or _url(url)
    if not _text(title) or not canonical_url or not _timestamp(published):
        return None
    location_values = _list(location)
    normalized = {
        "id": f"{source}:{_text(source_id) or canonical_url}",
        "source": source,
        "sourceName": SOURCE_META[source]["name"],
        "sourceUrl": SOURCE_META[source]["url"],
        "jobTitle": _text(title),
        "company": _text(company) or None,
        "locations": location_values,
        "remote": remote,
        "tags": _list(tags),
        "publishedAt": _iso(published),
        "url": canonical_url,
        "applyUrl": canonical_url,
        "salary": _salary(raw, source),
    }
    if include_description:
        normalized["jobDescription"] = _text(description)[:12000]
    return normalized


def _payload_items(payload: Any, source: str) -> list[dict[str, Any]]:
    if source == "arbeitnow":
        items = payload.get("data", []) if isinstance(payload, dict) else []
    elif source == "jobicy":
        items = payload.get("jobs", []) if isinstance(payload, dict) else []
    elif source == "remoteok":
        items = payload[1:] if isinstance(payload, list) else []
    else:
        items = payload.get("jobs", []) if isinstance(payload, dict) else []
    return [item for item in items if isinstance(item, dict)]


def _request_json(url: str, timeout: int = 25) -> Any:
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read())
        except (OSError, json.JSONDecodeError):
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
    raise RuntimeError("unreachable")


def _source_url(source: str, fetch_limit: int) -> str:
    if source == "jobicy":
        return f"{SOURCES[source]}?count={fetch_limit}"
    if source == "himalayas":
        return f"{SOURCES[source]}?limit={fetch_limit}&offset=0"
    return SOURCES[source]


def collect_jobs(
    sources: list[str] | None = None,
    keywords: list[str] | None = None,
    locations: list[str] | None = None,
    max_age_days: int = 14,
    limit: int = 50,
    include_description: bool = False,
    payloads: dict[str, Any] | None = None,
    fetcher: Callable[[str], Any] = _request_json,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Collect, filter, and deduplicate jobs; raise only when every source fails."""
    if sources is not None and (not isinstance(sources, list) or any(not isinstance(item, str) for item in sources)):
        raise ValueError("sources must be a list of strings")
    if keywords is not None and (not isinstance(keywords, list) or any(not isinstance(item, str) for item in keywords)):
        raise ValueError("keywords must be a list of strings")
    if locations is not None and (not isinstance(locations, list) or any(not isinstance(item, str) for item in locations)):
        raise ValueError("locations must be a list of strings")
    selected = list(SOURCES) if sources is None else sources
    if not selected or len(selected) != len(set(selected)):
        raise ValueError("sources must be a non-empty list without duplicates")
    unknown = [source for source in selected if source not in SOURCES]
    if unknown:
        raise ValueError(f"unsupported source: {unknown[0]}")
    if not isinstance(max_age_days, int) or isinstance(max_age_days, bool) or not 0 <= max_age_days <= 365:
        raise ValueError("maxAgeDays must be an integer between 0 and 365")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer between 1 and 100")
    if not isinstance(include_description, bool):
        raise ValueError("includeDescription must be a boolean")
    keywords = [_key(item) for item in (keywords or []) if _key(item)]
    locations = [_key(item) for item in (locations or []) if _key(item)]
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cutoff = now - timedelta(days=max_age_days)
    jobs: list[dict[str, Any]] = []
    failures = 0
    fetch_limit = min(100, max(20, limit * 3))
    for source in selected:
        try:
            payload = payloads[source] if payloads is not None and source in payloads else fetcher(_source_url(source, fetch_limit))
        except Exception:
            failures += 1
            continue
        for raw in _payload_items(payload, source):
            job = normalize_job(raw, source, include_description)
            if not job or not job["remote"]:
                continue
            published = _timestamp(job["publishedAt"])
            if published and published < cutoff:
                continue
            haystack = " ".join([job["jobTitle"], job["company"] or "", *job["tags"], *job["locations"]])
            if include_description:
                haystack += " " + job.get("jobDescription", "")
            haystack = _key(haystack)
            if keywords and not all(keyword in haystack for keyword in keywords):
                continue
            if locations and not any(location in _key(" ".join(job["locations"])) for location in locations):
                continue
            jobs.append(job)
    if not jobs and failures == len(selected):
        raise RuntimeError("all selected job sources were unavailable")

    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    unique: list[dict[str, Any]] = []
    for job in sorted(jobs, key=lambda item: item["publishedAt"] or "", reverse=True):
        title_key = _key(f"{job['company'] or ''}-{job['jobTitle']}")
        if job["url"] in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(job["url"])
        seen_titles.add(title_key)
        unique.append(job)
        if len(unique) >= limit:
            break
    return unique
