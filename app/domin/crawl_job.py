"""
Domain object representing a crawl job.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import UUID


class CrawlJobState(str, Enum):
    PENDING = "PENDING"
    CRAWLING = "CRAWLING"
    CRAWLED = "CRAWLED"
    PENDING_FAILED = "PENDING_FAILED"
    CRAWLING_FAILED = "CRAWLING_FAILED"
    CRAWLED_FAILED = "CRAWLED_FAILED"
    CONTENT_SIZE_EXCEEDED = "CONTENT_SIZE_EXCEEDED"
    NO_CONTENT = "NO_CONTENT"
    DONE = "DONE"


@dataclass
class CrawlJob:
    id: UUID
    url: str
    state: CrawlJobState
    version: int
    failed_count: int
    next_refresh_at: datetime
    created_at: datetime
    updated_at: datetime

    def mark_as_crawling(self) -> None:
        self.state = CrawlJobState.CRAWLING
        self.updated_at = datetime.now(timezone.utc)
        self.version += 1

    def mark_as_crawled(self) -> None:
        self.state = CrawlJobState.CRAWLED
        self.updated_at = datetime.now(timezone.utc)
        self.failed_count = 0
        self.version += 1

    def mark_as_failed(self) -> None:
        current_time = datetime.now(timezone.utc)

        self.state = CrawlJobState.CRAWLING_FAILED
        self.updated_at = current_time
        self.failed_count += 1
        self.next_refresh_at = current_time + timedelta(hours=1)
        self.version += 1
