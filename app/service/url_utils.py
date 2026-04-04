"""
URL normalization and filtering utilities for the crawler.

Two layers of defense against duplicate / junk pages:

1. **normalize_url** — canonical form so that cosmetic URL variants
   (query-param reordering, tracking params, fragments, …) collapse
   to a single key before we hit the database.

2. **should_skip_url** — return True for URLs that should never be
   crawled at all (login pages, feeds, print views, …).
"""
from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode, unquote


# ---------------------------------------------------------------------------
# Query parameters that are safe to strip — they never change page content.
# ---------------------------------------------------------------------------
TRACKING_PARAMS: frozenset[str] = frozenset({
    # UTM / marketing trackers
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    # Ad-click identifiers
    "fbclid", "gclid", "gad_source", "mc_cid", "mc_eid", "msclkid",
    # Google Analytics
    "_ga", "_gl",
    # Referrer / affiliate
    "ref", "referer", "referrer",
    # Session / auth tokens (value is per-user, content is identical)
    "sid", "session_id", "jsessionid", "token", "phpsessid",
    # Cache busting
    "ver", "_", "timestamp", "t", "cb", "nocache",
})

# Content-equivalent variants — same content, different presentation.
# Stripped by default for knowledge-base dedup, but separated so callers
# can opt out (e.g. if they intentionally want sorted/paginated variants).
DEDUP_PARAMS: frozenset[str] = frozenset({
    "sort", "order", "orderby", "display", "view", "layout",
    "per_page", "limit",
    # Language / CMS display toggles (Czech CMS specifics)
    "lang", "mapa-webu", "zmena-vzhledu",
})

# Union of both sets — used by normalize_url by default.
JUNK_QUERY_PARAMS: frozenset[str] = TRACKING_PARAMS | DEDUP_PARAMS

# ---------------------------------------------------------------------------
# URL path patterns to skip entirely (never crawl these).
# ---------------------------------------------------------------------------
_SKIP_PATH_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Auth / admin
    re.compile(r"/(login|signin|sign-in|register|signup|sign-up|logout|auth|oauth)(/|$)", re.IGNORECASE),
    re.compile(r"/(admin|wp-admin|dashboard)(/|$)", re.IGNORECASE),
    # Search
    re.compile(r"/search(/|$|\?)", re.IGNORECASE),
    # Feeds / technical
    re.compile(r"/(feed|rss|atom)(/|$)", re.IGNORECASE),
    re.compile(r"/sitemap\.xml$", re.IGNORECASE),
    re.compile(r"/robots\.txt$", re.IGNORECASE),
    re.compile(r"/wp-json(/|$)", re.IGNORECASE),
    # Print / calendar / export views
    re.compile(r"/(print|calendar|ical)(/|$)", re.IGNORECASE),
)

# Patterns matched against *parsed query string keys* (not the raw URL).
_SKIP_QUERY_KEYS: frozenset[str] = frozenset({
    "s",              # WordPress search
    "q",              # generic search
    "replytocom",     # comment reply
    "print",          # print view
    "ical",           # calendar export
})

_SKIP_FRAGMENT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^#comment", re.IGNORECASE),
)


def normalize_url(
    url: str,
    *,
    strip_params: frozenset[str] | None = None,
) -> str:
    """
    Produce a canonical URL suitable for deduplication.

    Parameters
    ----------
    url : str
        Raw URL to normalize.
    strip_params : frozenset[str] | None
        Query params to remove.  Defaults to ``JUNK_QUERY_PARAMS``
        (tracking + dedup).  Pass ``TRACKING_PARAMS`` to keep
        sort/order/per_page etc.

    Transformations applied (in order):
    1. Decode percent-encoding for UTF-8 characters.
    2. Lowercase the entire URL.
    3. Normalize scheme to ``https``.
    4. Strip ``www.`` prefix for canonical non-www form.
    5. Remove default port (``:443`` for https).
    6. Collapse path segments (``/./``, ``/../``, ``//``).
    7. Strip trailing slash (except bare domain ``/``).
    8. Remove fragment (``#…``).
    9. Remove junk query parameters (tracking, dedup).
    10. Sort remaining query parameters for deterministic order.
    """
    if strip_params is None:
        strip_params = JUNK_QUERY_PARAMS

    # Decode percent-encoding first so /caf%C3%A9 == /café
    url = unquote(url)

    parsed = urlparse(url.lower())

    # --- scheme ---
    scheme = "https"

    # --- netloc: strip www., strip default port ---
    netloc = parsed.hostname or ""
    if netloc.startswith("www."):
        netloc = netloc.removeprefix("www.")
    port = parsed.port
    if port and port != 443:
        netloc = f"{netloc}:{port}"

    # --- path ---
    path = _collapse_path(parsed.path)
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    # --- query ---
    query = _clean_query(parsed.query, strip_params)

    # --- fragment: always drop ---
    return urlunparse((scheme, netloc, path, "", query, ""))


def should_skip_url(url: str) -> bool:
    """
    Return ``True`` if the URL matches a pattern that should never be crawled.
    """
    parsed = urlparse(url)

    # Path-based skips
    for pattern in _SKIP_PATH_PATTERNS:
        if pattern.search(parsed.path):
            return True

    # Query-key-based skips (parsed, no false positives from path)
    if parsed.query:
        query_keys = {k.lower() for k in parse_qs(parsed.query, keep_blank_values=True)}
        if query_keys & _SKIP_QUERY_KEYS:
            return True

    # Fragment-based skips (e.g. #comment-123)
    if parsed.fragment:
        frag_with_hash = f"#{parsed.fragment}"
        for pattern in _SKIP_FRAGMENT_PATTERNS:
            if pattern.search(frag_with_hash):
                return True

    return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean_query(query: str, strip_params: frozenset[str]) -> str:
    """Remove junk params and return a sorted, deterministic query string."""
    if not query:
        return ""
    params = parse_qs(query, keep_blank_values=True)
    filtered = {
        k: v for k, v in params.items()
        if k.lower() not in strip_params
    }
    if not filtered:
        return ""
    return urlencode(sorted(filtered.items()), doseq=True)


def _collapse_path(path: str) -> str:
    """Resolve ``.``, ``..`` and collapse duplicate ``/`` in a URL path."""
    segments: list[str] = []
    for seg in path.split("/"):
        if seg == "." or seg == "":
            continue
        if seg == "..":
            if segments:
                segments.pop()
        else:
            segments.append(seg)
    return "/" + "/".join(segments)
