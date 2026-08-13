import unittest
from datetime import datetime, timezone

from remote_job_intelligence.core import collect_jobs, normalize_job


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


if __name__ == "__main__":
    unittest.main()
