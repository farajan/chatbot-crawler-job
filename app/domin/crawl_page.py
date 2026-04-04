"""
Domain objects representing core crawler entities.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID


@dataclass
class CrawlPage:
    id: UUID
    crawl_job_id: UUID
    url: str
    is_root: bool
    html_content: str
    markdown_content: str
    content_summary: str
    hash_content: str
    first_seen_at: datetime
    last_seen_at: datetime
    last_changed_at: datetime
    version: int
    created_at: datetime
    updated_at: datetime

    def update(self, html_content: str, markdown_content: str, content_summary: str, hash_content: str) -> None:
        now = datetime.now(timezone.utc)
        self.html_content = html_content
        self.markdown_content = markdown_content
        self.content_summary = content_summary
        self.hash_content = hash_content
        self.last_seen_at = now
        self.last_changed_at = now
        self.updated_at = now
        self.version += 1

    def mark_as_seen(self) -> None:
        now = datetime.now(timezone.utc)
        self.last_seen_at = now
        self.updated_at = now
        self.version += 1
