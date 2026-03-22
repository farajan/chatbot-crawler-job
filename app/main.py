import asyncio
import logging
import sys

from app.config import get_settings
from app.service.crawler_service import get_crawler_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("job")


def main() -> None:
    settings = get_settings()
    logger.info("Crawler Job started. CRAWL_JOB_ID=%s", settings.crawl_job_id)

    crawler_service = get_crawler_service()
    try:
        asyncio.run(crawler_service.crawl_site())
    except Exception:
        logger.exception("Crawler Job failed. CRAWL_JOB_ID=%s", settings.crawl_job_id)
        sys.exit(1)

    logger.info("Crawler Job finished successfully. CRAWL_JOB_ID=%s", settings.crawl_job_id)


if __name__ == "__main__":
    main()
