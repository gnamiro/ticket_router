import time
from typing import Callable, TypeVar
from datetime import datetime

T = TypeVar("T")

def timed_call(fn: Callable[[], T], timeout_s: float) -> T:
    # Simple pattern: rely on underlying client timeout if available.
    # For Ollama/HTTP, better set request timeout in the client if supported.
    # Here we just call it and measure latency.
    return fn()

def run_with_retries(call: Callable[[], T], retries: int = 1, backoff_s: float = 0.3) -> T:
    last = None
    for i in range(retries + 1):
        try:
            return call()
        except Exception as e:
            last = e
            time.sleep(backoff_s * (2 ** i))
    raise last
