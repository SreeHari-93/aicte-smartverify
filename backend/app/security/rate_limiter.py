import time
from collections import defaultdict
from threading import Lock
from typing import Tuple


class InMemoryRateLimiter:
    """
    Sliding window rate limiter for IP and Account attempts.
    Tracks timestamps of attempts in memory with a lock for concurrency safety.
    """

    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        self.lock = Lock()

    def is_rate_limited(self, key: str) -> Tuple[bool, int]:
        """
        Check if key has exceeded allowed rate.
        Returns: (is_limited, retry_after_seconds)
        """
        now = time.time()
        window_start = now - self.window_seconds

        with self.lock:
            # Clean up old timestamps
            timestamps = [ts for ts in self.requests[key] if ts > window_start]
            self.requests[key] = timestamps

            if len(timestamps) >= self.max_requests:
                earliest = timestamps[0]
                retry_after = max(1, int(earliest + self.window_seconds - now))
                return True, retry_after

            # Add current attempt
            self.requests[key].append(now)
            return False, 0

    def reset(self, key: str):
        """Reset rate limit history for a key"""
        with self.lock:
            if key in self.requests:
                del self.requests[key]


# Global rate limiter instances
ip_limiter = InMemoryRateLimiter(max_requests=5, window_seconds=60)
account_limiter = InMemoryRateLimiter(max_requests=5, window_seconds=60)

