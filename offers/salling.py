import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode, urljoin, urlparse

import httpx
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)
_locks_guard = threading.Lock()
_locks = {}


class SallingError(Exception):
    retryable = True


class SallingConfigurationError(SallingError):
    retryable = False


class SallingAuthenticationError(SallingError):
    retryable = False


class SallingPermissionError(SallingError):
    retryable = False


class SallingInvalidResponseError(SallingError):
    retryable = False


class SallingRateLimitError(SallingError):
    def __init__(self, retry_after=None):
        super().__init__("Salling Group rate limit exceeded")
        self.retry_after = retry_after


@dataclass(frozen=True)
class SallingResult:
    items: list
    cache_hit: bool
    degraded: bool = False


def _lock_for(key):
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


def _decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise SallingInvalidResponseError("Unexpected numeric value") from error


def _datetime(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as error:
        raise SallingInvalidResponseError("Unexpected timestamp value") from error
    return parsed if parsed.tzinfo else timezone.make_aware(parsed)


def _retry_after(value):
    if not value:
        return None
    try:
        return max(0, int(value))
    except ValueError:
        try:
            return max(0, int((parsedate_to_datetime(value) - timezone.now()).total_seconds()))
        except (TypeError, ValueError):
            return None


class SallingClient:
    def __init__(self, *, token=None, base_url=None, transport=None, sleep=time.sleep):
        self.token = token if token is not None else settings.SALLING_GROUP_API_TOKEN
        self.base_url = (base_url or settings.SALLING_GROUP_API_BASE_URL).rstrip("/") + "/"
        self.transport = transport
        self.sleep = sleep
        if not self.token:
            raise SallingConfigurationError("Salling Group API token is not configured")
        if urlparse(self.base_url).scheme != "https":
            raise SallingConfigurationError("Salling Group API base URL must use HTTPS")

    def _cache_key(self, path, params):
        canonical = urlencode(sorted((key, str(value)) for key, value in params.items()))
        digest = hashlib.sha256(f"{path}?{canonical}".encode()).hexdigest()
        return f"salling:v1:{digest}"

    def _request_json(self, url, params=None):
        timeout = settings.SALLING_GROUP_REQUEST_TIMEOUT_MS / 1000
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        started = time.monotonic()
        with httpx.Client(timeout=timeout, transport=self.transport, follow_redirects=False) as client:
            for attempt in range(settings.SALLING_GROUP_MAX_RETRIES + 1):
                try:
                    response = client.get(url, params=params, headers=headers)
                except (httpx.TimeoutException, httpx.NetworkError) as error:
                    if attempt >= settings.SALLING_GROUP_MAX_RETRIES:
                        raise SallingError("Salling Group is temporarily unavailable") from error
                    self.sleep(min(2**attempt, 4))
                    continue
                retry_after = _retry_after(response.headers.get("Retry-After"))
                if response.status_code == 401:
                    raise SallingAuthenticationError("Salling Group authentication failed")
                if response.status_code == 403:
                    raise SallingPermissionError("Salling Group permission denied")
                if response.status_code == 429:
                    if attempt >= settings.SALLING_GROUP_MAX_RETRIES:
                        raise SallingRateLimitError(retry_after)
                    self.sleep(retry_after if retry_after is not None else min(2**attempt, 4))
                    continue
                if response.status_code in {408} or 500 <= response.status_code < 600:
                    if attempt >= settings.SALLING_GROUP_MAX_RETRIES:
                        raise SallingError(f"Salling Group returned status {response.status_code}")
                    self.sleep(retry_after if retry_after is not None else min(2**attempt, 4))
                    continue
                if response.status_code == 404:
                    return None, response
                if response.status_code >= 400:
                    raise SallingInvalidResponseError(
                        f"Salling Group rejected the request with status {response.status_code}"
                    )
                try:
                    payload = response.json()
                except json.JSONDecodeError as error:
                    raise SallingInvalidResponseError("Salling Group returned invalid JSON") from error
                logger.info(
                    "salling_request",
                    extra={
                        "event": "salling_request",
                        "endpoint": urlparse(str(response.url)).path,
                        "status": response.status_code,
                        "duration_ms": round((time.monotonic() - started) * 1000),
                    },
                )
                if retry_after:
                    self.sleep(retry_after)
                return payload, response
        raise SallingError("Salling Group request failed")

    def _cached(self, path, params, loader):
        key = self._cache_key(path, params)
        cached = cache.get(key)
        if cached is not None:
            return SallingResult(cached, cache_hit=True)
        with _lock_for(key):
            cached = cache.get(key)
            if cached is not None:
                return SallingResult(cached, cache_hit=True)
            stale_key = f"{key}:stale"
            try:
                items = loader()
            except SallingError:
                stale = cache.get(stale_key)
                if stale is not None:
                    logger.warning("salling_degraded_cache", extra={"event": "salling_degraded_cache"})
                    return SallingResult(stale, cache_hit=True, degraded=True)
                raise
            cache.set(key, items, settings.SALLING_GROUP_CACHE_TTL_SECONDS)
            cache.set(stale_key, items, settings.SALLING_GROUP_CACHE_TTL_SECONDS * 12)
            return SallingResult(items, cache_hit=False)

    def stores(self, **filters):
        allowed = {
            "zip",
            "city",
            "country",
            "street",
            "brand",
            "geo",
            "radius",
            "hourType",
            "fields",
            "per_page",
        }
        params = {key: value for key, value in filters.items() if key in allowed and value not in (None, "")}
        params.setdefault("per_page", 100)

        def load():
            items = []
            next_url = urljoin(self.base_url, "v2/stores")
            request_params = params
            pages = 0
            while next_url and pages < 100:
                payload, response = self._request_json(next_url, request_params)
                if not isinstance(payload, list):
                    raise SallingInvalidResponseError("Stores response must be a list")
                items.extend(normalize_store(item) for item in payload)
                next_url = _next_link(response.headers.get("Link", ""), self.base_url)
                request_params = None
                pages += 1
            return items

        return self._cached("v2/stores", params, load)

    def food_waste(self, *, zip_code=None, geo=None, radius=None, store_id=None):
        if store_id:
            path = f"v1/food-waste/{store_id}"
            params = {}
        else:
            path = "v1/food-waste/"
            params = {key: value for key, value in {"zip": zip_code, "geo": geo, "radius": radius}.items() if value}
            if not params.get("zip") and not params.get("geo"):
                raise SallingConfigurationError("Food waste requires a zip code, geolocation, or store ID")

        def load():
            payload, _response = self._request_json(urljoin(self.base_url, path), params)
            if payload is None:
                return []
            groups = payload if isinstance(payload, list) else [payload]
            if not all(isinstance(group, dict) for group in groups):
                raise SallingInvalidResponseError("Food waste response must contain store objects")
            return [
                normalize_clearance(group.get("store"), clearance)
                for group in groups
                for clearance in group.get("clearances", [])
            ]

        return self._cached(path, params, load)


def _next_link(header, base_url):
    for part in header.split(","):
        if 'rel="next"' not in part:
            continue
        candidate = part.split(";", 1)[0].strip().strip("<>")
        parsed = urlparse(candidate)
        base = urlparse(base_url)
        if parsed.scheme == "https" and parsed.netloc == base.netloc:
            return candidate
    return None


def normalize_store(item):
    if not isinstance(item, dict) or not item.get("id") or not item.get("name"):
        raise SallingInvalidResponseError("Store is missing required fields")
    address = item.get("address") if isinstance(item.get("address"), dict) else {}
    coordinates = item.get("coordinates") if isinstance(item.get("coordinates"), list) else []
    return {
        "external_id": str(item["id"]),
        "name": str(item["name"])[:150],
        "chain": str(item.get("brand") or "")[:150],
        "street": str(address.get("street") or "")[:250],
        "postal_code": str(address.get("zip") or "")[:20],
        "city": str(address.get("city") or "")[:100],
        "country": str(address.get("country") or "")[:2],
        "longitude": _decimal(coordinates[0]) if len(coordinates) >= 2 else None,
        "latitude": _decimal(coordinates[1]) if len(coordinates) >= 2 else None,
        "opening_hours": item.get("hours") if isinstance(item.get("hours"), list) else [],
        "raw_source_timestamp": _datetime(item.get("modified")),
    }


def normalize_clearance(store, clearance):
    if not isinstance(store, dict) or not isinstance(clearance, dict):
        raise SallingInvalidResponseError("Clearance is missing store data")
    product = clearance.get("product") if isinstance(clearance.get("product"), dict) else {}
    offer = clearance.get("offer") if isinstance(clearance.get("offer"), dict) else {}
    normalized_store = normalize_store(store)
    product_name = product.get("description")
    source_id = offer.get("ean") or product.get("ean")
    if not product_name or not source_id or offer.get("newPrice") is None:
        raise SallingInvalidResponseError("Clearance is missing required product or price fields")
    return {
        "source": "salling_group",
        "external_offer_id": f"{normalized_store['external_id']}:{source_id}",
        "external_product_id": str(product.get("ean") or ""),
        "product_name": str(product_name)[:250],
        "description": str(product.get("description") or "")[:5000],
        "brand": "",
        "category": "",
        "image_url": str(product.get("image") or "")[:500],
        "original_price": _decimal(offer.get("originalPrice")),
        "offer_price": _decimal(offer.get("newPrice")),
        "currency": str(offer.get("currency") or "DKK")[:3],
        "discount_amount": _decimal(offer.get("discount")),
        "discount_percentage": _decimal(offer.get("percentDiscount")),
        "quantity": _decimal(offer.get("stock")),
        "unit": str(offer.get("stockUnit") or "")[:50],
        "valid_from": _datetime(offer.get("startTime")),
        "valid_until": _datetime(offer.get("endTime")),
        "last_updated": timezone.now(),
        "raw_source_timestamp": _datetime(offer.get("lastUpdate")),
        "store": normalized_store,
    }
