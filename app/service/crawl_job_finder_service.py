"""
Service for retrieving crawl jobs.
"""
from __future__ import annotations

from uuid import UUID

from app.db.crawl_job_repository import CrawlJobRepository, get_crawl_job_repository
from app.domin.crawl_job import CrawlJob, CrawlJobState
from app.exception.crawl_job_exceptions import CrawlerJobNotFoundException


class CrawlJobFinderService:
    def __init__(self, repository: CrawlJobRepository) -> None:
        self._repository = repository

    async def get_by_id_and_state(self, crawl_job_id: UUID, state: CrawlJobState) -> CrawlJob:
        crawl_job = await self._repository.get_by_id_and_state(crawl_job_id, state)
        if crawl_job is None:
            raise CrawlerJobNotFoundException(crawl_job_id)
        return crawl_job


def get_crawl_job_finder_service(
    repository: CrawlJobRepository | None = None,
) -> CrawlJobFinderService:
    repository = repository or get_crawl_job_repository()
    return CrawlJobFinderService(repository)
