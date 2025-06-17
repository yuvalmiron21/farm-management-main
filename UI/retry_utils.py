import time
import random
import logging
import asyncio
from functools import wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Exceptions to retry by default
DEFAULT_EXCEPTIONS = (ConnectionError, TimeoutError, Exception)

# Synchronous version
def retry_with_backoff(
    func=None,
    *,
    max_attempts=5,
    max_delay=30,
    exceptions=DEFAULT_EXCEPTIONS,
    logger=logger
):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        logger.error(f"All {max_attempts} attempts failed: {e}")
                        raise
                    wait_time = min((2 ** attempt) + random.uniform(0, 0.1), max_delay)
                    logger.info(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time:.2f} seconds...")
                    time.sleep(wait_time)
        return wrapper
    if func:
        return decorator(func)
    return decorator

# Asynchronous version
def async_retry_with_backoff(
    func=None,
    *,
    max_attempts=5,
    max_delay=30,
    exceptions=DEFAULT_EXCEPTIONS,
    logger=logger
):
    def decorator(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await f(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        logger.error(f"All {max_attempts} attempts failed: {e}")
                        raise
                    wait_time = min((2 ** attempt) + random.uniform(0, 0.1), max_delay)
                    logger.info(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time:.2f} seconds...")
                    await asyncio.sleep(wait_time)
        return wrapper
    if func:
        return decorator(func)
    return decorator 