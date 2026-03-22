"""
Service layer for crawl job domain operations.
"""
from __future__ import annotations

from app.db.crawl_job_repository import CrawlJobRepository, get_crawl_job_repository
from app.domin.crawl_job import CrawlJob


class CrawlJobService:
    def __init__(self, repository: CrawlJobRepository) -> None:
        self._repository = repository

    async def mark_as_crawling(self, crawl_job: CrawlJob) -> CrawlJob:
        crawl_job.mark_as_crawling()
        return await self._repository.update(crawl_job)

    async def mark_as_crawled(self, crawl_job: CrawlJob) -> CrawlJob:
        crawl_job.mark_as_crawled()
        return await self._repository.update(crawl_job)

    async def mark_as_failed(self, crawl_job: CrawlJob) -> CrawlJob:
        crawl_job.mark_as_failed()
        return await self._repository.update(crawl_job)


def get_crawl_job_service(
    repository: CrawlJobRepository | None = None,
) -> CrawlJobService:
    repository = repository or get_crawl_job_repository()
    return CrawlJobService(repository)
