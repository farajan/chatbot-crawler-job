"""
Repository for managing CrawlJob domain objects.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from app.db.db import _generate_uuid, database
from app.domin.crawl_job import CrawlJob, CrawlJobState


class CrawlJobRepository:
    def __init__(self, db=database) -> None:
        self._db = db

    async def create(self, crawl_job: CrawlJob) -> CrawlJob:
        pool = await self._db.connect()
        crawl_job_id = crawl_job.id or _generate_uuid()
        query = """
            INSERT INTO crawl_job (
                id,
                url,
                state,
                created_at,
                updated_at,
                version
            )
            VALUES ($1, $2, $3, $4, $5, $6)
        """
        await pool.execute(
            query,
            crawl_job_id,
            crawl_job.url,
            crawl_job.state.value if isinstance(crawl_job.state, CrawlJobState) else crawl_job.state,
            crawl_job.created_at,
            crawl_job.updated_at,
            crawl_job.version,
        )
        crawl_job.id = crawl_job_id
        return crawl_job

    async def update(self, crawl_job: CrawlJob) -> CrawlJob:
        pool = await self._db.connect()
        query = """
            UPDATE crawl_job
            SET url = $1, state = $2, failed_count = $3, next_refresh_at = $4, updated_at = $5, version = $6
            WHERE id = $7
        """
        await pool.execute(
            query,
            crawl_job.url,
            crawl_job.state.value if isinstance(crawl_job.state, CrawlJobState) else crawl_job.state,
            crawl_job.failed_count,
            crawl_job.next_refresh_at,
            crawl_job.updated_at,
            crawl_job.version,
            crawl_job.id,
        )
        return crawl_job

    async def get_by_id_and_state(self, job_id: UUID, state: CrawlJobState) -> Optional[CrawlJob]:
        pool = await self._db.connect()
        query = """
            SELECT id, url, state, version, failed_count, next_refresh_at, created_at, updated_at
            FROM crawl_job
            WHERE id = $1 and state = $2
        """
        state_value = state.value if isinstance(state, CrawlJobState) else str(state)
        row = await pool.fetchrow(query, job_id, state_value)
        if not row:
            return None
        return CrawlJob(
            id=row["id"],
            url=row["url"],
            state=CrawlJobState(row["state"]),
            version=row["version"],
            failed_count=row["failed_count"],
            next_refresh_at=row["next_refresh_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def get_crawl_job_repository() -> CrawlJobRepository:
    return CrawlJobRepository()
