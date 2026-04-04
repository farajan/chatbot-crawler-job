"""
Crawler service layer handling crawl orchestration and persistence.
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import DomainFilter, FilterChain, URLFilter, URLPatternFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.utils import normalize_url_for_deep_crawl

from app.config import get_settings
from app.service.url_utils import should_skip_url
from app.db.db import database
from app.domin.crawl_job import CrawlJobState
from app.service.crawl_job_finder_service import get_crawl_job_finder_service, CrawlJobFinderService
from app.service.crawl_job_service import CrawlJobService, get_crawl_job_service
from app.service.crawl_page_service import CrawlPageService, get_crawl_page_service


logger = logging.getLogger("crawler")

BLOCKED_ASSET_EXTENSIONS = (
    "jpg",
    "jpeg",
    "png",
    "gif",
    "bmp",
    "webp",
    "svg",
    "ico",
    "tiff",
    "tif",
    "avif",
    "heic",
    "mp4",
    "avi",
    "mov",
    "wmv",
    "flv",
    "webm",
    "mkv",
    "m4v",
    "3gp",
    "ogv",
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "txt",
    "rtf",
    "odt",
    "ods",
    "odp",
    "vcf",
    "mp3",
    "wav",
    "flac",
    "aac",
    "ogg",
    "wma",
    "m4a",
    "zip",
    "rar",
    "7z",
    "tar",
    "gz",
    "bz2",
    "xz",
    "cdr",
    "ai",
)

_asset_ext_pattern = "|".join(BLOCKED_ASSET_EXTENSIONS)
# Block if extension is on the path, inside a query value, or the endpoint name
# is a common binary handler (e.g., image.php?img=123 with no extension).
BLOCKED_ASSET_REGEX = re.compile(
    rf"(?ix)"  # Ignore case, allow verbose for clarity
    rf"("  # start group
    rf"(?:/|^)[^/?#]+\.({_asset_ext_pattern})(?:$|[?#])"  # direct path extension
    rf"|"  # or query param carries a filename with extension
    rf"=[^&#?]+\.({_asset_ext_pattern})(?:$|[&#])"
    rf"|"  # or binary-ish handler endpoints without extension
    rf"(?:^|/)[^/?#]*(?:image|img|photo|picture|vcard|evt_file)\.php(?:$|[?#])"
    rf"|"  # or query param clearly referencing an image id
    rf"[?&](?:img|image|photo|picture|vcard|vcf|file)=[^&#]+"
    rf")"
)


class SkipPatternFilter(URLFilter):
    """Reject URLs matching well-known junk patterns (login, feeds, search, …)."""

    def apply(self, url: str) -> bool:
        return not should_skip_url(url)


@dataclass(frozen=True)
class CrawlConfig:
    max_depth: int
    max_pages: int
    include_external: bool = False
    allowed_domains: Optional[List[str]] = None
    url_patterns: Optional[List[str]] = None
    stream: bool = True
    verbose: bool = False


def _normalize_html(html: str) -> str:
    """
    Remove dynamic/script content and collapse whitespace for stable storage/hash.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    normalized = re.sub(r"\s+", " ", str(soup))
    return normalized.strip()


def _build_filter_chain(
    url: str,
    crawl_config: CrawlConfig,
) -> Optional[FilterChain]:
    filters: List[URLFilter] = []

    # 1) Domain filtering (only if we don't want externals)
    if not crawl_config.include_external:
        seed_host = (urlparse(str(url)).hostname or "").lower()

        # If user provided allowed_domains explicitly, respect it as-is (but normalize)
        if crawl_config.allowed_domains:
            allowed_domains = [d.lower() for d in crawl_config.allowed_domains]
        else:
            # Otherwise derive allowlist from seed host and ALWAYS include both www/non-www variants
            allowed_domains_set = set()
            if seed_host:
                allowed_domains_set.add(seed_host)
                if seed_host.startswith("www."):
                    allowed_domains_set.add(seed_host.removeprefix("www."))
                else:
                    allowed_domains_set.add(f"www.{seed_host}")

            allowed_domains = sorted(allowed_domains_set) if allowed_domains_set else None

        if allowed_domains:
            filters.append(
                DomainFilter(
                    allowed_domains=allowed_domains,
                    blocked_domains=None,
                )
            )

    # 2) Optional URL patterns (allowlist/denylist by user config)
    if crawl_config.url_patterns:
        filters.append(URLPatternFilter(patterns=crawl_config.url_patterns))

    # 3) Skip well-known junk URLs (login, feeds, search, print views, …)
    filters.append(SkipPatternFilter())

    # 4) Always block obvious binary assets by extension/handlers
    # reverse=True => block matching patterns
    filters.append(URLPatternFilter(patterns=[BLOCKED_ASSET_REGEX], reverse=True))

    return FilterChain(filters) if filters else None


class CrawlerService:
    def __init__(
        self,
        crawl_job_service: CrawlJobService,
        crawl_job_finder_service: CrawlJobFinderService,
        crawl_page_service: CrawlPageService,
    ) -> None:
        self._crawl_job_service = crawl_job_service
        self._crawl_job_finder_service = crawl_job_finder_service
        self._crawl_page_service = crawl_page_service

    async def crawl_site(self) -> None:
        settings = get_settings()
        await database.connect()
        crawl_job = await self._crawl_job_finder_service.get_by_id_and_state(
            crawl_job_id=settings.crawl_job_id,
            state=CrawlJobState.PENDING,
        )
        await self._crawl_job_service.mark_as_crawling(crawl_job)

        crawl_config = CrawlConfig(
            max_depth=settings.max_depth,
            max_pages=settings.max_pages,
        )
        filter_chain = _build_filter_chain(url=crawl_job.url, crawl_config=crawl_config)
        strategy = BFSDeepCrawlStrategy(
            max_depth=crawl_config.max_depth,
            include_external=crawl_config.include_external,
            max_pages=crawl_config.max_pages,
            filter_chain=filter_chain,
        )
        config = CrawlerRunConfig(
            deep_crawl_strategy=strategy,
            stream=crawl_config.stream,
            verbose=crawl_config.verbose,
            check_robots_txt=True,
            user_agent="ChattyHubBot/1.0 (+https://chattyhub.ai; info@chattyhub.ai)",
            word_count_threshold=20,
            exclude_external_links=False,
            remove_overlay_elements=True,
            # css_selector="main, article, [role='main'], .content, #content",
            # excluded_tags=["nav", "header", "footer", "aside"],
            excluded_tags=["aside"],
            markdown_generator=DefaultMarkdownGenerator(
                content_filter=PruningContentFilter(
                    threshold=0.48,
                    threshold_type="dynamic",
                    min_word_threshold=5,
                ),
                options={"ignore_links": True},
            ),
        )

        total_pages = 0
        seed_url = str(crawl_job.url)
        normalized_seed_url = normalize_url_for_deep_crawl(seed_url, seed_url) or seed_url

        try:
            async with AsyncWebCrawler() as crawler:
                crawl_results = await crawler.arun(normalized_seed_url, config=config)

                async def process_result(result) -> None:
                    nonlocal total_pages
                    is_root = total_pages == 0
                    total_pages += 1
                    html_content = (
                        getattr(result, "html", None)
                        or getattr(result, "cleaned_html", "")
                        or ""
                    )
                    md_result = result.markdown
                    full_markdown = md_result.raw_markdown if md_result else ""
                    content_summary = md_result.fit_markdown if md_result else None
                    normalized_html = _normalize_html(html_content) if html_content else ""
                    hash_content = hashlib.sha256(normalized_html.encode("utf-8")).hexdigest()
                    depth = int(result.metadata.get("depth", 0)) if result.metadata else 0

                    await self._crawl_page_service.process(
                        crawl_job_id=crawl_job.id,
                        url=result.url,
                        is_root=is_root,
                        html_content=normalized_html,
                        markdown_content=full_markdown,
                        content_summary=content_summary,
                        hash_content=hash_content,
                    )
                    logger.info(
                        "Job %s | crawled %s -> status=%s depth=%s (len=%s)",
                        crawl_job.id,
                        result.url,
                        int(getattr(result, "status", 0)),
                        depth,
                        len(full_markdown),
                    )

                if crawl_config.stream:
                    async for page in crawl_results:
                        await process_result(page)
                else:
                    for page in crawl_results:
                        await process_result(page)

            await self._crawl_job_service.mark_as_crawled(crawl_job)
        except Exception:
            try:
                await self._crawl_job_service.mark_as_failed(crawl_job)
            except Exception:  # pragma: no cover - defensive logging
                logger.exception("Failed to update crawl_job %s after error", crawl_job.id)
            raise


def get_crawler_service(
    crawl_job_service: CrawlJobService | None = None,
    crawl_job_finder_service: CrawlJobFinderService | None = None,
    crawl_page_service: CrawlPageService | None = None,
) -> CrawlerService:
    return CrawlerService(
        crawl_job_service=crawl_job_service or get_crawl_job_service(),
        crawl_job_finder_service=crawl_job_finder_service or get_crawl_job_finder_service(),
        crawl_page_service=crawl_page_service or get_crawl_page_service(),
    )
