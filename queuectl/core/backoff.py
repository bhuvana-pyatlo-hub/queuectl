import random
from typing import Optional

def exponential_backoff(attempts: int, base: int, cap: Optional[int] = None, jitter: bool = True) -> int:
    delay = max(1, base ** attempts)
    if cap is not None:
        delay = min(delay, cap)
    if jitter:
        factor = random.uniform(0.5, 1.5)
        delay = max(1, int(delay * factor))
    return int(delay)

def sleep_with_backoff(attempts: int, base: int, cap: Optional[int] = None) -> int:
    return exponential_backoff(attempts, base, cap)
