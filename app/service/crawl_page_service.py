"""
Service layer for crawl page domain operations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from uuid_utils import uuid7

import logging

from app.db.crawl_page_repository import CrawlPageRepository, get_crawl_page_repository
from app.domin.crawl_page import CrawlPage
from app.service.url_utils import normalize_url, should_skip_url

logger = logging.getLogger(__name__)


class CrawlPageService:
    def __init__(self, repository: CrawlPageRepository) -> None:
        self._repository = repository

    async def create(
        self,
        crawl_job_id: UUID,
        url: str,
        is_root: bool,
        html_content: str,
        markdown_content: str,
        summary_content: str,
        hash_content: str,
    ) -> CrawlPage:
        now = datetime.now(timezone.utc)
        crawl_page = CrawlPage(
            id=uuid7(),
            crawl_job_id=crawl_job_id,
            url=url,
            is_root=is_root,
            html_content=html_content,
            markdown_content=markdown_content,
            summary_content=summary_content,
            hash_content=hash_content,
            first_seen_at=now,
            last_seen_at=now,
            last_changed_at=now,
            version=0,
            created_at=now,
            updated_at=now,
        )
        return await self._repository.create(crawl_page)

    async def update(self, crawl_page: CrawlPage) -> CrawlPage:
        return await self._repository.update(crawl_page)

    async def process(
        self,
        crawl_job_id: UUID,
        url: str,
        is_root: bool,
        html_content: str,
        markdown_content: str,
        summary_content: str,
        hash_content: str,
    ) -> CrawlPage | None:
        if not markdown_content or not markdown_content.strip():
            return None

        if should_skip_url(url):
            logger.debug("Skipping URL by pattern: %s", url)
            return None

        normalized_url = normalize_url(url)
        existing = await self._repository.find_by_job_and_url(crawl_job_id, normalized_url)
        if existing is None:
            if await self._repository.exists_by_job_and_hash(crawl_job_id, hash_content):
                logger.info("Skipping duplicate page %s (hash %s already exists for job %s)", normalized_url, hash_content[:12], crawl_job_id)
                return None
            return await self.create(
                crawl_job_id=crawl_job_id,
                url=normalized_url,
                is_root=is_root,
                html_content=html_content,
                markdown_content=markdown_content,
                summary_content=summary_content,
                hash_content=hash_content,
            )

        if existing.hash_content == hash_content:
            existing.mark_as_seen()
            return await self.update(existing)

        existing.update(
            html_content=html_content,
            markdown_content=markdown_content,
            summary_content=summary_content,
            hash_content=hash_content,
        )
        return await self.update(existing)


def get_crawl_page_service(
    repository: CrawlPageRepository | None = None,
) -> CrawlPageService:
    repository = repository or get_crawl_page_repository()
    return CrawlPageService(repository)
