import time
import threading
from typing import Dict, Any, Optional, Callable


class CircuitBreakerOpenException(Exception):
    """Raised when calls to an authority are blocked because its circuit breaker is OPEN."""
    pass


class SourceUnavailableException(Exception):
    """Raised when an external authority is unreachable after retries or is disabled."""
    pass


class AuthorityCircuitBreaker:
    """
    In-memory Circuit Breaker with thread-safe failure counting,
    timeout handling, and state transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED).
    """

    def __init__(self, failure_threshold: int = 3, reset_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._lock = threading.Lock()
        self._states: Dict[str, Dict[str, Any]] = {}

    def _get_entry(self, authority: str) -> Dict[str, Any]:
        key = authority.upper().strip()
        if key not in self._states:
            self._states[key] = {
                "state": "CLOSED",
                "failure_count": 0,
                "last_failure_time": 0.0,
            }
        return self._states[key]

    def can_execute(self, authority: str) -> bool:
        with self._lock:
            entry = self._get_entry(authority)
            now = time.time()
            if entry["state"] == "OPEN":
                if now - entry["last_failure_time"] >= self.reset_timeout:
                    # Transition to HALF_OPEN to allow trial
                    entry["state"] = "HALF_OPEN"
                    return True
                return False
            return True

    def record_success(self, authority: str) -> None:
        with self._lock:
            entry = self._get_entry(authority)
            entry["state"] = "CLOSED"
            entry["failure_count"] = 0
            entry["last_failure_time"] = 0.0

    def record_failure(self, authority: str) -> None:
        with self._lock:
            entry = self._get_entry(authority)
            entry["failure_count"] += 1
            entry["last_failure_time"] = time.time()
            if entry["failure_count"] >= self.failure_threshold:
                entry["state"] = "OPEN"

    def get_state(self, authority: str) -> str:
        with self._lock:
            entry = self._get_entry(authority)
            now = time.time()
            if entry["state"] == "OPEN" and now - entry["last_failure_time"] >= self.reset_timeout:
                return "HALF_OPEN"
            return entry["state"]

    def reset(self, authority: Optional[str] = None) -> None:
        with self._lock:
            if authority:
                key = authority.upper().strip()
                if key in self._states:
                    self._states[key] = {
                        "state": "CLOSED",
                        "failure_count": 0,
                        "last_failure_time": 0.0,
                    }
            else:
                self._states.clear()


# Global circuit breaker singleton
circuit_breaker = AuthorityCircuitBreaker(failure_threshold=3, reset_timeout=60.0)


def execute_with_resilience(
    authority: str,
    operation: Callable[[], Any],
    max_retries: int = 3,
    backoff_factor: float = 0.05,
    timeout_seconds: float = 5.0,
) -> Any:
    """
    Executes an operation protected by circuit breaker and 3 retries with backoff.
    Raises CircuitBreakerOpenException or SourceUnavailableException on failure.
    """
    if not circuit_breaker.can_execute(authority):
        raise CircuitBreakerOpenException(
            f"Circuit breaker is OPEN for authority '{authority}'. Service temporarily unavailable."
        )

    last_error: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            result = operation()
            circuit_breaker.record_success(authority)
            return result
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                # Exponential backoff
                sleep_time = backoff_factor * (2 ** (attempt - 1))
                time.sleep(sleep_time)

    # All retries exhausted
    circuit_breaker.record_failure(authority)
    raise SourceUnavailableException(
        f"Authority '{authority}' unavailable after {max_retries} attempts: {last_error}"
    ) from last_error

