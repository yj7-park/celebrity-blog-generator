"""
Thread-safe cancel tokens for long-running operations.

Usage pattern
-------------
# In the async router — reset before starting, check between steps:
    pipeline.reset()
    pipeline.check()          # raises InterruptedError if cancelled

# In the blocking thread — interruptible sleep + explicit check:
    naver.interruptible_sleep(2.5)   # wakes immediately on cancel
    naver.check()                    # raises InterruptedError

# Cancel endpoint sets the token:
    pipeline.cancel()
"""
from __future__ import annotations
import threading


class CancelToken:
    """Thread-safe cancel flag backed by a threading.Event."""

    def __init__(self):
        self._ev = threading.Event()

    # ── Control ───────────────────────────────────────────────────────────────

    def cancel(self):
        """Request cancellation (idempotent)."""
        self._ev.set()

    def reset(self):
        """Clear the flag — call before starting a new job."""
        self._ev.clear()

    # ── Query ─────────────────────────────────────────────────────────────────

    @property
    def cancelled(self) -> bool:
        return self._ev.is_set()

    def check(self, msg: str = "작업이 취소되었습니다."):
        """Raise InterruptedError immediately if cancellation was requested."""
        if self._ev.is_set():
            raise InterruptedError(msg)

    # ── Interruptible sleep ───────────────────────────────────────────────────

    def interruptible_sleep(self, seconds: float,
                            msg: str = "작업이 취소되었습니다."):
        """
        Sleep for *seconds* but return immediately (raising InterruptedError)
        if cancel is requested.  Replaces bare ``time.sleep()`` in threads.
        """
        if self._ev.wait(timeout=seconds):
            raise InterruptedError(msg)


# ── Module-level singletons ───────────────────────────────────────────────────

pipeline = CancelToken()   # for the data pipeline (SSE + step-by-step)
naver    = CancelToken()   # for the Naver Selenium writer
