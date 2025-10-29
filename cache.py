"""Redis cache helpers and historical snapshot utilities for NewsNow Neon."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

try:
    import redis  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    redis = None  # type: ignore

from .config import (
    CACHE_KEY,
    CACHE_TTL_SECONDS,
    HISTORICAL_CACHE_PREFIX,
    HISTORICAL_CACHE_TTL_SECONDS,
    REDIS_URL,
    is_historical_cache_enabled,
)
from .models import Headline, HeadlineCache, HistoricalSnapshot, RedisStatistics
from .utils import parse_iso8601_utc

logger = logging.getLogger(__name__)

_redis_client: Optional[Any] = None
_redis_lock = threading.Lock()


def get_redis_client() -> Optional[Any]:
    """Return a cached Redis client if available."""

    global _redis_client
    if redis is None or not REDIS_URL:
        return None
    if _redis_client is not None:
        return _redis_client
    with _redis_lock:
        if _redis_client is not None:
            return _redis_client
        try:
            _redis_client = redis.from_url(  # type: ignore[attr-defined]
                REDIS_URL, decode_responses=True
            )
        except Exception as exc:  # pragma: no cover - redis connection failure
            logger.warning("Unable to connect to Redis cache: %s", exc)
            _redis_client = None
    return _redis_client


def _build_historical_cache_key(reference: datetime) -> str:
    timestamp = reference.astimezone(timezone.utc)
    date_part = timestamp.strftime("%Y-%m-%d")
    time_part = timestamp.strftime("%H%M%S")
    prefix = HISTORICAL_CACHE_PREFIX.strip() or "news"
    return f"{prefix}:{date_part}:{time_part}"


def _persist_historical_snapshot(
    client: Any, payload: str, *, reference: Optional[datetime] = None
) -> None:
    if not is_historical_cache_enabled():
        return
    snapshot_time = reference or datetime.now(timezone.utc)
    key = _build_historical_cache_key(snapshot_time)
    try:
        client.setex(key, HISTORICAL_CACHE_TTL_SECONDS, payload)  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - redis failure
        logger.debug("Historical cache write failed for '%s': %s", key, exc)


def _collect_historical_keys(client: Any) -> List[str]:
    pattern = f"{HISTORICAL_CACHE_PREFIX.strip() or 'news'}:*"
    try:
        iterator = client.scan_iter(match=pattern)  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - redis failure
        logger.debug("Historical cache key scan failed: %s", exc)
        return []
    keys: List[str] = []
    for raw_key in iterator:
        key = raw_key.decode("utf-8") if isinstance(raw_key, bytes) else str(raw_key)
        if key:
            keys.append(key)
    return keys


def _parse_historical_snapshot_timestamp(key: str) -> Optional[datetime]:
    try:
        _prefix, date_part, time_part = key.rsplit(":", 2)
    except ValueError:
        return None
    try:
        timestamp = datetime.strptime(f"{date_part}{time_part}", "%Y-%m-%d%H%M%S")
    except ValueError:
        return None
    return timestamp.replace(tzinfo=timezone.utc)


def load_historical_snapshots(
    *,
    limit: Optional[int] = None,
    horizon: Optional[timedelta] = timedelta(hours=24),
) -> List[HistoricalSnapshot]:
    """Return recent historical cache snapshots for read-only inspection."""

    if not is_historical_cache_enabled():
        return []
    client = get_redis_client()
    if client is None:
        return []
    keys = _collect_historical_keys(client)
    if not keys:
        return []

    snapshots: List[HistoricalSnapshot] = []
    now_utc = datetime.now(timezone.utc)
    for key in sorted(keys, reverse=True):
        captured_at = _parse_historical_snapshot_timestamp(key)
        if captured_at is None:
            continue
        if horizon is not None and captured_at < (now_utc - horizon):
            continue
        try:
            raw_payload = client.get(key)  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - redis failure
            logger.debug("Unable to read historical snapshot '%s': %s", key, exc)
            continue
        if raw_payload is None:
            continue
        payload_text = raw_payload if isinstance(raw_payload, str) else str(raw_payload)
        if not payload_text.strip():
            continue
        try:
            payload = json.loads(payload_text)
        except Exception as exc:
            logger.debug(
                "Historical snapshot '%s' payload is not valid JSON: %s", key, exc
            )
            continue
        bundle = HeadlineCache.from_payload(payload)
        if bundle is None:
            continue
        snapshots.append(
            HistoricalSnapshot(
                key=key,
                captured_at=captured_at,
                cache=bundle,
                headline_count=len(bundle.headlines),
                summary_count=len(bundle.summaries),
            )
        )
        if limit is not None and len(snapshots) >= limit:
            break
    return snapshots


def collect_redis_statistics() -> RedisStatistics:
    """Return diagnostics about the Redis cache key and server."""

    cache_configured = bool(REDIS_URL)
    client = get_redis_client()
    if client is None:
        warnings: List[str] = []
        if cache_configured:
            warnings.append(
                "Redis URL is configured but the client could not be initialised."
            )
        else:
            warnings.append("Redis caching is disabled; set REDIS_URL to enable it.")
        return RedisStatistics(
            cache_configured=cache_configured,
            available=False,
            cache_key=CACHE_KEY,
            key_present=False,
            warnings=warnings,
        )

    warnings: List[str] = []
    try:
        client.ping()  # type: ignore[attr-defined]
    except Exception as exc:
        message = f"Redis ping failed: {exc}"
        warnings.append(message)
        return RedisStatistics(
            cache_configured=cache_configured,
            available=False,
            cache_key=CACHE_KEY,
            key_present=False,
            warnings=warnings,
            error=str(exc),
        )

    key_present = False
    try:
        key_present = bool(client.exists(CACHE_KEY))  # type: ignore[attr-defined]
    except Exception as exc:
        warnings.append(f"Unable to determine cache key existence: {exc}")
        key_present = False

    raw_payload: Optional[str] = None
    try:
        raw_payload = client.get(CACHE_KEY)  # type: ignore[attr-defined]
    except Exception as exc:
        warnings.append(f"Unable to read cache payload: {exc}")
        raw_payload = None
    else:
        if raw_payload is not None:
            key_present = True

    ttl_seconds: Optional[int] = None
    try:
        ttl_value = client.ttl(CACHE_KEY)  # type: ignore[attr-defined]
    except Exception as exc:
        warnings.append(f"Unable to fetch TTL for cache key: {exc}")
    else:
        if isinstance(ttl_value, (int, float)):
            ttl_int = int(ttl_value)
            if ttl_int >= 0:
                ttl_seconds = ttl_int
            elif ttl_int == -2 and raw_payload is None:
                key_present = False
            else:
                ttl_seconds = None

    payload_bytes: Optional[int] = (
        len(raw_payload.encode("utf-8")) if isinstance(raw_payload, str) else None
    )

    headline_count = 0
    summary_count = 0
    ticker_present = False
    sections: List[str] = []
    sources: List[str] = []
    latest_headline_time: Optional[datetime] = None
    latest_headline_title: Optional[str] = None
    latest_headline_source: Optional[str] = None

    if isinstance(raw_payload, str) and raw_payload.strip():
        try:
            payload = json.loads(raw_payload)
        except Exception as exc:
            warnings.append(f"Unable to parse cache payload: {exc}")
        else:
            bundle = HeadlineCache.from_payload(payload)
            if bundle is None:
                warnings.append("Cache payload is not in the expected format.")
            else:
                headline_count = len(bundle.headlines)
                summary_count = len(bundle.summaries)
                ticker_present = bool(
                    bundle.ticker_text and bundle.ticker_text.strip()
                )
                sections = sorted(
                    {
                        headline.section.strip()
                        for headline in bundle.headlines
                        if isinstance(headline.section, str)
                        and headline.section.strip()
                    }
                )
                sources = sorted(
                    {
                        headline.source.strip()
                        for headline in bundle.headlines
                        if isinstance(headline.source, str)
                        and headline.source.strip()
                    }
                )
                for headline in bundle.headlines:
                    timestamp = parse_iso8601_utc(headline.published_at)
                    if timestamp is None:
                        continue
                    if latest_headline_time is None or timestamp > latest_headline_time:
                        latest_headline_time = timestamp
                        latest_headline_title = headline.title
                        latest_headline_source = headline.source
                if latest_headline_time is None and bundle.headlines:
                    fallback = bundle.headlines[0]
                    latest_headline_title = fallback.title
                    latest_headline_source = fallback.source

    historical_keys = _collect_historical_keys(client)
    historical_snapshot_count = len(historical_keys)
    latest_snapshot_key = max(historical_keys) if historical_keys else None

    try:
        dbsize_raw = client.dbsize()  # type: ignore[attr-defined]
        dbsize = int(dbsize_raw)
    except Exception as exc:
        warnings.append(f"Unable to fetch Redis database size: {exc}")
        dbsize = None

    redis_version: Optional[str] = None
    connected_clients: Optional[int] = None
    used_memory_human: Optional[str] = None
    try:
        info = client.info()  # type: ignore[attr-defined]
    except Exception as exc:
        warnings.append(f"Unable to fetch Redis INFO metrics: {exc}")
        info = {}
    if isinstance(info, Mapping):
        version_raw = info.get("redis_version")
        if isinstance(version_raw, str):
            redis_version = version_raw
        clients_raw = info.get("connected_clients")
        if isinstance(clients_raw, (int, float)):
            connected_clients = int(clients_raw)
        memory_raw = info.get("used_memory_human")
        if isinstance(memory_raw, str):
            used_memory_human = memory_raw

    return RedisStatistics(
        cache_configured=cache_configured,
        available=True,
        cache_key=CACHE_KEY,
        key_present=key_present,
        headline_count=headline_count,
        summary_count=summary_count,
        ticker_present=ticker_present,
        sections=sections,
        section_count=len(sections),
        sources=sources,
        source_count=len(sources),
        ttl_seconds=ttl_seconds,
        payload_bytes=payload_bytes,
        latest_headline_time=latest_headline_time,
        latest_headline_title=latest_headline_title,
        latest_headline_source=latest_headline_source,
        historical_snapshot_count=historical_snapshot_count,
        latest_snapshot_key=latest_snapshot_key,
        dbsize=dbsize,
        redis_version=redis_version,
        connected_clients=connected_clients,
        used_memory_human=used_memory_human,
        warnings=warnings,
    )


def load_cached_headlines(
    max_items: Optional[int], *, require_headlines: bool = True
) -> Optional[HeadlineCache]:
    """Fetch cached headlines and related metadata from Redis if present."""

    client = get_redis_client()
    if client is None:
        return None
    try:
        raw = client.get(CACHE_KEY)  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - redis failure
        logger.warning("Redis cache read failed: %s", exc)
        return None
    if not raw:
        return None

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Cached headlines payload is not valid JSON.")
        return None

    bundle = HeadlineCache.from_payload(payload)
    if bundle is None:
        return None
    if require_headlines and not bundle.headlines:
        return None
    if max_items is not None:
        return bundle.limited(max_items)
    return bundle


def _store_cached_bundle(bundle: HeadlineCache) -> None:
    client = get_redis_client()
    if client is None:
        return
    try:
        payload = json.dumps(bundle.to_payload(), ensure_ascii=False)
        client.setex(CACHE_KEY, CACHE_TTL_SECONDS, payload)  # type: ignore[attr-defined]
        _persist_historical_snapshot(client, payload)
    except Exception as exc:  # pragma: no cover - redis failure
        logger.warning("Redis cache write failed: %s", exc)


def _load_full_cache() -> Optional[HeadlineCache]:
    return load_cached_headlines(None, require_headlines=False)


def persist_headlines_with_ticker(
    headlines: Sequence[Headline], ticker_text: Optional[str]
) -> None:
    """Merge fresh headlines and ticker text with any cached summaries."""

    bundle = _load_full_cache()
    summaries = dict(bundle.summaries) if bundle else {}
    previous_ticker = bundle.ticker_text if bundle else None
    final_ticker = ticker_text if ticker_text is not None else previous_ticker
    new_bundle = HeadlineCache(
        headlines=list(headlines),
        ticker_text=final_ticker,
        summaries=summaries,
    )
    _store_cached_bundle(new_bundle)


def _normalise_summary_title(title: Optional[str]) -> Optional[str]:
    if not isinstance(title, str):
        return None
    compact = re.sub(r"\s+", " ", title.strip().lower())
    return compact or None


def _summary_cache_keys(url: str, title: Optional[str]) -> List[str]:
    if not isinstance(url, str):
        return []
    stripped = url.strip()
    if not stripped:
        return []
    normalized = stripped.rstrip("/")
    url_candidates: List[str] = []
    for candidate in (stripped, normalized):
        if candidate and candidate not in url_candidates:
            url_candidates.append(candidate)

    keys: List[str] = []
    normalised_title = _normalise_summary_title(title)
    if normalised_title:
        digest = hashlib.sha256(normalised_title.encode("utf-8")).hexdigest()[:16]
        for candidate in url_candidates:
            keys.append(f"{candidate}#t:{digest}")

    keys.extend(url_candidates)

    deduplicated: List[str] = []
    seen: Set[str] = set()
    for key in keys:
        if key not in seen:
            deduplicated.append(key)
            seen.add(key)
    return deduplicated


def get_cached_article_summary(url: str, title: Optional[str]) -> Optional[str]:
    """Return a cached article summary for the given URL if available."""

    bundle = _load_full_cache()
    if bundle is None:
        return None
    for key in _summary_cache_keys(url, title):
        summary = bundle.summaries.get(key)
        if isinstance(summary, str) and summary.strip():
            return summary
    return None


def store_cached_article_summary(
    original_url: str, final_url: Optional[str], title: Optional[str], summary: str
) -> None:
    """Persist an article summary keyed by both the NewsNow link and final URL."""

    if not summary.strip():
        return
    bundle = _load_full_cache()
    summaries = dict(bundle.summaries) if bundle else {}
    urls: List[str] = []
    if isinstance(original_url, str):
        urls.append(original_url)
    if isinstance(final_url, str):
        urls.append(final_url)
    for candidate in urls:
        for key in _summary_cache_keys(candidate, title):
            summaries[key] = summary
    headlines = list(bundle.headlines) if bundle else []
    ticker_text = bundle.ticker_text if bundle else None
    new_bundle = HeadlineCache(
        headlines=headlines,
        ticker_text=ticker_text,
        summaries=summaries,
    )
    _store_cached_bundle(new_bundle)


def clear_cached_headlines() -> Tuple[bool, str]:
    """Remove cached headlines from Redis if the cache is configured."""

    client = get_redis_client()
    if client is None:
        logger.info("Redis cache not configured; nothing to clear.")
        return False, "Redis cache not configured."

    historical_removed = 0
    historical_keys: List[str] = []
    try:
        historical_keys = _collect_historical_keys(client)
        if historical_keys:
            historical_removed = client.delete(*historical_keys)  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - redis failure
        logger.warning("Unable to clear historical Redis cache keys: %s", exc)
        historical_removed = 0

    try:
        removed = client.delete(CACHE_KEY)  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - redis failure
        logger.warning("Unable to clear Redis cache: %s", exc)
        return False, "Failed to clear Redis cache. Check logs for details."

    if removed or historical_removed:
        fragments: List[str] = []
        if removed:
            fragments.append("primary key")
        if historical_removed:
            plural = "s" if historical_removed != 1 else ""
            fragments.append(f"{historical_removed} historical snapshot{plural}")
        detail = f" ({', '.join(fragments)})" if fragments else ""
        logger.info("Cleared Redis cache key '%s'%s.", CACHE_KEY, detail)
        message = "Redis cache cleared" + detail + "."
        return True, message

    logger.info("Redis cache key '%s' already empty.", CACHE_KEY)
    return True, "Redis cache already empty."


__all__ = [
    "collect_redis_statistics",
    "clear_cached_headlines",
    "get_cached_article_summary",
    "get_redis_client",
    "load_cached_headlines",
    "load_historical_snapshots",
    "persist_headlines_with_ticker",
    "store_cached_article_summary",
]
