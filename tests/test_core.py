import unittest
from datetime import datetime, timezone

from remote_job_intelligence.core import collect_jobs, collect_jobs_with_status, normalize_job


NOW = datetime(2026, 8, 14, 0, 0, tzinfo=timezone.utc)


def arbeitnow(slug, title, created_at, remote=True, company="Acme"):
    return {
        "slug": slug,
        "title": title,
        "company_name": company,
        "location": "Worldwide",
        "remote": remote,
        "tags": ["Python", "AI"],
        "created_at": created_at,
        "url": f"https://www.arbeitnow.com/jobs/{slug}",
        "description": "Build useful software.",
    }


class NormalizeTests(unittest.TestCase):
    def test_normalizes_html_and_epoch(self):
        result = normalize_job(
            {
                "id": "42",
                "position": "Data <b>Engineer</b>",
                "company": "Acme",
                "location": "Worldwide",
                "tags": ["python"],
                "epoch": 1786579200,
                "url": "https://remoteok.com/remote-jobs/42",
                "apply_url": "https://example.com/apply/42",
                "description": "<p>Build &amp; ship.</p>",
            },
            "remoteok",
            include_description=True,
        )
        self.assertEqual(result["jobTitle"], "Data Engineer")
        self.assertEqual(result["jobDescription"], "Build & ship.")
        self.assertEqual(result["applyUrl"], "https://example.com/apply/42")
        self.assertEqual(result["publishedAt"], "2026-08-13T00:00:00Z")
        self.assertEqual(result["sourceName"], "Remote OK")
        self.assertEqual(result["sourceUrl"], "https://remoteok.com/")

    def test_normalizes_jobicy_salary_and_metadata(self):
        result = normalize_job(
            {
                "id": 7,
                "jobTitle": "Python Engineer",
                "companyName": "Acme",
                "jobGeo": "Worldwide",
                "jobIndustry": ["Software Engineering"],
                "jobLevel": "Senior",
                "jobType": ["Full-Time"],
                "salaryMin": 120000,
                "salaryMax": 150000,
                "salaryCurrency": "USD",
                "salaryPeriod": "yearly",
                "pubDate": "2026-08-13T00:00:00Z",
                "url": "https://jobicy.com/jobs/7",
            },
            "jobicy",
        )
        self.assertEqual(result["salary"], {"min": 120000, "max": 150000, "currency": "USD", "period": "yearly"})
        self.assertEqual(result["jobType"], ["Full-Time"])
        self.assertEqual(result["employmentType"], "Full-Time")
        self.assertEqual(result["seniority"], ["Senior"])
        self.assertEqual(result["categories"], ["Software Engineering"])

    def test_normalizes_himalayas_metadata(self):
        result = normalize_job(
            {
                "guid": "https://himalayas.app/jobs/7",
                "title": "Data Engineer",
                "companyName": "Acme",
                "locationRestrictions": ["United States"],
                "categories": ["Data Engineering"],
                "parentCategories": ["Engineering"],
                "employmentType": "Full Time",
                "seniority": ["Mid-level"],
                "timezoneRestrictions": ["UTC-5"],
                "pubDate": "2026-08-13T00:00:00Z",
                "applicationLink": "https://example.com/apply/7",
                "minSalary": 100000,
                "maxSalary": 140000,
                "currency": "USD",
                "salaryPeriod": "annual",
            },
            "himalayas",
        )
        self.assertEqual(result["salary"]["currency"], "USD")
        self.assertEqual(result["jobType"], ["Full Time"])
        self.assertEqual(result["employmentType"], "Full Time")
        self.assertEqual(result["seniority"], ["Mid-level"])
        self.assertEqual(result["timezoneRestrictions"], ["UTC-5"])
        self.assertEqual(result["categories"], ["Data Engineering", "Engineering"])

    def test_uses_himalayas_slug_when_company_name_is_placeholder(self):
        result = normalize_job(
            {
                "guid": "https://himalayas.app/companies/bright-vision-technologies/jobs/data-engineer",
                "title": "Data Engineer",
                "companyName": "name",
                "companySlug": "bright-vision-technologies",
                "pubDate": "2026-08-13T00:00:00Z",
            },
            "himalayas",
        )
        self.assertEqual(result["company"], "Bright Vision Technologies")

    def test_rejects_record_without_http_url(self):
        self.assertIsNone(normalize_job({"title": "No link"}, "jobicy"))

    def test_rejects_record_without_timestamp(self):
        self.assertIsNone(normalize_job({"title": "No date", "url": "https://example.com/job"}, "jobicy"))


class CollectTests(unittest.TestCase):
    def test_filters_age_keywords_and_remote_flag(self):
        payloads = {
            "arbeitnow": {
                "data": [
                    arbeitnow("new", "Senior Python Engineer", 1786579200),
                    arbeitnow("old", "Python Engineer", 1785196800),
                    arbeitnow("office", "Python Engineer", 1786579200, remote=False),
                ]
            }
        }
        jobs = collect_jobs(
            ["arbeitnow"],
            keywords=["python"],
            locations=["worldwide"],
            max_age_days=14,
            limit=10,
            payloads=payloads,
            now=NOW,
        )
        self.assertEqual([job["id"] for job in jobs], ["arbeitnow:new"])

    def test_deduplicates_same_company_and_title(self):
        payloads = {
            "arbeitnow": {"data": [arbeitnow("a", "Python Engineer", 1786579200)]},
            "jobicy": {
                "jobs": [
                    {
                        "id": 7,
                        "jobTitle": "Python Engineer",
                        "companyName": "Acme",
                        "jobGeo": "Worldwide",
                        "pubDate": "2026-08-13T00:00:00Z",
                        "url": "https://jobicy.com/jobs/7",
                    }
                ]
            },
        }
        jobs = collect_jobs(
            ["arbeitnow", "jobicy"],
            max_age_days=14,
            limit=10,
            payloads=payloads,
            now=NOW,
        )
        self.assertEqual(len(jobs), 1)

    def test_continues_when_one_source_fails(self):
        payloads = {"arbeitnow": {"data": [arbeitnow("a", "Python Engineer", 1786579200)]}}

        def fetcher(url):
            if "jobicy" in url:
                raise OSError("rate limited")
            raise AssertionError(url)

        jobs = collect_jobs(
            ["arbeitnow", "jobicy"],
            payloads=payloads,
            fetcher=fetcher,
            now=NOW,
        )
        self.assertEqual(len(jobs), 1)

    def test_reports_partial_source_failure(self):
        payloads = {"arbeitnow": {"data": [arbeitnow("a", "Python Engineer", 1786579200)]}}

        def fetcher(url):
            if "jobicy" in url:
                raise OSError("rate limited")
            raise AssertionError(url)

        jobs, report = collect_jobs_with_status(
            ["arbeitnow", "jobicy"],
            payloads=payloads,
            fetcher=fetcher,
            now=NOW,
        )
        self.assertEqual(len(jobs), 1)
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["sources"]["jobicy"]["status"], "error")
        self.assertEqual(report["sources"]["arbeitnow"]["recordsReturned"], 1)
        self.assertEqual(report["warnings"], ["jobicy source unavailable"])

    def test_keyword_match_mode_defaults_to_all_and_supports_any(self):
        payloads = {
            "arbeitnow": {
                "data": [
                    {**arbeitnow("python", "Python Engineer", 1786579200), "tags": ["Python"]},
                    {**arbeitnow("ai", "AI Engineer", 1786579200), "tags": ["AI"]},
                    {**arbeitnow("both", "Python AI Engineer", 1786579200)},
                ]
            }
        }
        default_jobs = collect_jobs(
            ["arbeitnow"],
            keywords=["python", "ai"],
            payloads=payloads,
            now=NOW,
        )
        any_jobs = collect_jobs(
            ["arbeitnow"],
            keywords=["python", "ai"],
            keyword_match_mode="any",
            payloads=payloads,
            now=NOW,
        )
        self.assertEqual([job["id"] for job in default_jobs], ["arbeitnow:both"])
        self.assertEqual({job["id"] for job in any_jobs}, {"arbeitnow:python", "arbeitnow:ai", "arbeitnow:both"})

    def test_round_robin_keeps_sources_visible_at_limit(self):
        payloads = {
            "arbeitnow": {"data": [arbeitnow("a", "A", 1786579200), arbeitnow("a2", "A2", 1786579100)]},
            "jobicy": {
                "jobs": [
                    {
                        "id": 1,
                        "jobTitle": "B",
                        "companyName": "B Co",
                        "jobGeo": "Worldwide",
                        "pubDate": "2026-08-13T00:00:00Z",
                        "url": "https://jobicy.com/jobs/1",
                    },
                    {
                        "id": 2,
                        "jobTitle": "B2",
                        "companyName": "B Co",
                        "jobGeo": "Worldwide",
                        "pubDate": "2026-08-12T00:00:00Z",
                        "url": "https://jobicy.com/jobs/2",
                    },
                ]
            },
            "remoteok": [
                {"last_updated": "2026-08-13T00:00:00Z"},
                {
                    "id": 3,
                    "position": "C",
                    "company": "C Co",
                    "location": "Worldwide",
                    "date": "2026-08-10T00:00:00Z",
                    "url": "https://remoteok.com/jobs/3",
                },
            ],
        }
        jobs = collect_jobs(
            ["arbeitnow", "jobicy", "remoteok"],
            limit=3,
            payloads=payloads,
            now=NOW,
        )
        self.assertEqual([job["source"] for job in jobs], ["arbeitnow", "jobicy", "remoteok"])

    def test_raises_when_all_sources_fail(self):
        with self.assertRaisesRegex(RuntimeError, "all selected"):
            collect_jobs(["arbeitnow"], fetcher=lambda _: (_ for _ in ()).throw(OSError("down")), now=NOW)

    def test_validates_input(self):
        with self.assertRaisesRegex(ValueError, "unsupported source"):
            collect_jobs(["unknown"], payloads={})
        with self.assertRaisesRegex(ValueError, "maxAgeDays"):
            collect_jobs(["arbeitnow"], max_age_days=999, payloads={})
        with self.assertRaisesRegex(ValueError, "keywords"):
            collect_jobs(["arbeitnow"], keywords="python", payloads={})
        with self.assertRaisesRegex(ValueError, "includeDescription"):
            collect_jobs(["arbeitnow"], include_description="yes", payloads={})
        with self.assertRaisesRegex(ValueError, "keywordMatchMode"):
            collect_jobs(["arbeitnow"], keyword_match_mode="none", payloads={})
        with self.assertRaisesRegex(ValueError, "keywordMatchMode"):
            collect_jobs(["arbeitnow"], keyword_match_mode=[], payloads={})


if __name__ == "__main__":
    unittest.main()
