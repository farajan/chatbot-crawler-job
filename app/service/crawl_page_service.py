"""
Service layer for crawl page domain operations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse
from uuid import UUID, uuid4

from app.db.crawl_page_repository import CrawlPageRepository, get_crawl_page_repository
from app.domin.crawl_page import CrawlPage


def normalize_url(url: str) -> str:
    """
    Normalize URL to ensure consistent storage and deduplication.

    - Converts entire URL to lowercase
    - Adds 'www.' prefix to hostname if not present
    - Normalizes scheme to 'https' (http and https treated as same)

    Examples:
        https://www.example.com -> https://www.example.com
        https://example.com -> https://www.example.com
        HTTP://EXAMPLE.COM -> https://www.example.com
        http://Example.Com/Path -> https://www.example.com/path
    """
    parsed = urlparse(url.lower())

    netloc = parsed.netloc
    if netloc and not netloc.startswith('www.'):
        netloc = f'www.{netloc}'

    scheme = 'https'

    return urlunparse((
        scheme,
        netloc,
        parsed.path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))


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
        hash_content: str,
    ) -> CrawlPage:
        now = datetime.now(timezone.utc)
        crawl_page = CrawlPage(
            id=uuid4(),
            crawl_job_id=crawl_job_id,
            url=url,
            is_root=is_root,
            html_content=html_content,
            markdown_content=markdown_content,
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
        hash_content: str,
    ) -> CrawlPage | None:
        if not markdown_content or not markdown_content.strip():
            return None

        normalized_url = normalize_url(url)
        existing = await self._repository.find_by_job_and_url(crawl_job_id, normalized_url)
        if existing is None:
            return await self.create(
                crawl_job_id=crawl_job_id,
                url=normalized_url,
                is_root=is_root,
                html_content=html_content,
                markdown_content=markdown_content,
                hash_content=hash_content,
            )

        if existing.hash_content == hash_content:
            existing.mark_as_seen()
            return await self.update(existing)

        existing.update(
            html_content=html_content,
            markdown_content=markdown_content,
            hash_content=hash_content,
        )
        return await self.update(existing)


def get_crawl_page_service(
    repository: CrawlPageRepository | None = None,
) -> CrawlPageService:
    repository = repository or get_crawl_page_repository()
    return CrawlPageService(repository)
