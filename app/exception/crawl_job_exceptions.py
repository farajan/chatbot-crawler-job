"""
Exceptions related to crawl job operations.
"""
from __future__ import annotations

from uuid import UUID


class CrawlerJobNotFoundException(Exception):
    def __init__(self, crawl_job_id: UUID) -> None:
        self.job_id = crawl_job_id
        message = f"Crawl job {crawl_job_id} not found"
        super().__init__(message)
