"""
Repository for managing CrawlPage domain objects.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from app.db.db import _generate_uuid, database
from app.domin.crawl_page import CrawlPage


class CrawlPageRepository:
    def __init__(self, db=database) -> None:
        self._db = db

    async def create(self, crawl_page: CrawlPage) -> CrawlPage:
        pool = await self._db.connect()
        page_id = crawl_page.id or _generate_uuid()
        query = """
            INSERT INTO crawl_page (
                id,
                crawl_job_id,
                url,
                is_root,
                html_content,
                markdown_content,
                content_summary,
                hash_content,
                first_seen_at,
                last_seen_at,
                last_changed_at,
                version,
                created_at,
                updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        """
        await pool.execute(
            query,
            page_id,
            crawl_page.crawl_job_id,
            crawl_page.url,
            crawl_page.is_root,
            crawl_page.html_content,
            crawl_page.markdown_content,
            crawl_page.content_summary,
            crawl_page.hash_content,
            crawl_page.first_seen_at,
            crawl_page.last_seen_at,
            crawl_page.last_changed_at,
            crawl_page.version,
            crawl_page.created_at,
            crawl_page.updated_at,
        )
        crawl_page.id = page_id
        return crawl_page

    async def update(self, crawl_page: CrawlPage) -> CrawlPage:
        pool = await self._db.connect()
        query = """
            UPDATE crawl_page
            SET
                html_content = $1,
                markdown_content = $2,
                content_summary = $3,
                hash_content = $4,
                last_seen_at = $5,
                last_changed_at = $6,
                version = $7,
                updated_at = $8
            WHERE id = $9
        """
        await pool.execute(
            query,
            crawl_page.html_content,
            crawl_page.markdown_content,
            crawl_page.content_summary,
            crawl_page.hash_content,
            crawl_page.last_seen_at,
            crawl_page.last_changed_at,
            crawl_page.version,
            crawl_page.updated_at,
            crawl_page.id,
        )
        return crawl_page

    async def exists_by_job_and_hash(self, crawl_job_id: UUID, hash_content: str) -> bool:
        pool = await self._db.connect()
        query = """
            SELECT 1 FROM crawl_page
            WHERE crawl_job_id = $1 AND hash_content = $2
            LIMIT 1
        """
        row = await pool.fetchrow(query, crawl_job_id, hash_content)
        return row is not None

    async def find_by_job_and_url(self, crawl_job_id: UUID, url: str) -> Optional[CrawlPage]:
        pool = await self._db.connect()
        query = """
            SELECT id, crawl_job_id, url, is_root, html_content, markdown_content, content_summary, hash_content,
                   first_seen_at, last_seen_at, last_changed_at, version, created_at, updated_at
            FROM crawl_page
            WHERE crawl_job_id = $1 AND url = $2
        """
        row = await pool.fetchrow(query, crawl_job_id, url)
        if not row:
            return None
        return CrawlPage(
            id=row["id"],
            crawl_job_id=row["crawl_job_id"],
            url=row["url"],
            is_root=row["is_root"],
            html_content=row["html_content"],
            markdown_content=row["markdown_content"],
            content_summary=row["content_summary"],
            hash_content=row["hash_content"],
            first_seen_at=row["first_seen_at"],
            last_seen_at=row["last_seen_at"],
            last_changed_at=row["last_changed_at"],
            version=row["version"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def get_crawl_page_repository() -> CrawlPageRepository:
    return CrawlPageRepository()
