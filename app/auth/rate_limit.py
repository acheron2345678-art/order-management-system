import math
import time

from collections import (
    OrderedDict,
    deque,
)

from threading import RLock

from fastapi import Request

from app.core.config import (
    LOGIN_RATE_LIMIT_ACCOUNT_ATTEMPTS,
    LOGIN_RATE_LIMIT_IP_ATTEMPTS,
    LOGIN_RATE_LIMIT_WINDOW_SECONDS,
)


MAX_TRACKED_KEYS = 5000


_lock = RLock()


_ip_attempts = OrderedDict()
_account_attempts = OrderedDict()


def _normalize_username(
    username: str,
):
    return (
        username
        .strip()
        .lower()
    )


def _client_ip(
    request: Request,
):
    if (
        request.client
        and
        request.client.host
    ):
        return request.client.host

    return "unknown"


def _trim_store(
    store: OrderedDict,
):
    while len(store) > MAX_TRACKED_KEYS:
        store.popitem(
            last=False
        )


def _get_bucket(
    store: OrderedDict,
    key: str,
):
    bucket = store.get(
        key
    )

    if bucket is None:
        bucket = deque()
        store[key] = bucket
    else:
        store.move_to_end(
            key
        )

    _trim_store(
        store
    )

    return bucket


def _prune_bucket(
    bucket: deque,
    now: float,
):
    cutoff = (
        now
        -
        LOGIN_RATE_LIMIT_WINDOW_SECONDS
    )

    while (
        bucket
        and
        bucket[0] <= cutoff
    ):
        bucket.popleft()


def _retry_after_for_bucket(
    bucket: deque,
    limit: int,
    now: float,
):
    _prune_bucket(
        bucket,
        now,
    )

    if len(bucket) < limit:
        return 0

    remaining = (
        LOGIN_RATE_LIMIT_WINDOW_SECONDS
        -
        (
            now
            -
            bucket[0]
        )
    )

    return max(
        1,
        math.ceil(
            remaining
        ),
    )


def get_login_retry_after(
    request: Request,
    username: str,
):
    now = time.monotonic()

    ip_key = _client_ip(
        request
    )

    account_key = _normalize_username(
        username
    )

    with _lock:
        ip_bucket = _get_bucket(
            _ip_attempts,
            ip_key,
        )

        account_bucket = _get_bucket(
            _account_attempts,
            account_key,
        )

        ip_retry = _retry_after_for_bucket(
            ip_bucket,
            LOGIN_RATE_LIMIT_IP_ATTEMPTS,
            now,
        )

        account_retry = _retry_after_for_bucket(
            account_bucket,
            LOGIN_RATE_LIMIT_ACCOUNT_ATTEMPTS,
            now,
        )

    return max(
        ip_retry,
        account_retry,
    )


def record_failed_login(
    request: Request,
    username: str,
):
    now = time.monotonic()

    ip_key = _client_ip(
        request
    )

    account_key = _normalize_username(
        username
    )

    with _lock:
        ip_bucket = _get_bucket(
            _ip_attempts,
            ip_key,
        )

        account_bucket = _get_bucket(
            _account_attempts,
            account_key,
        )

        _prune_bucket(
            ip_bucket,
            now,
        )

        _prune_bucket(
            account_bucket,
            now,
        )

        ip_bucket.append(
            now
        )

        account_bucket.append(
            now
        )


def clear_account_login_failures(
    username: str,
):
    account_key = _normalize_username(
        username
    )

    with _lock:
        _account_attempts.pop(
            account_key,
            None,
        )
