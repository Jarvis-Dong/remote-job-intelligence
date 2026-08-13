"""Normalize public remote-job feeds for the Apify runtime."""

from .core import collect_jobs, normalize_job

__all__ = ["collect_jobs", "normalize_job"]
