import time
import functools
import asyncio
from typing import Callable, Any


def timeit(log_func: Callable[[str], None] = print,
           msg: str = "Function {func_name} took {elapsed_time:.2f} seconds"):
    """
    Decorator to measure and log the execution time of a function (sync or async).

    Args:
        log_func: Logging function, e.g., logging.info.
        msg: Message format, supports {func_name} and {elapsed_time}.

    Returns:
        Decorated function with timing.
    """

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                start = time.time()
                result = await func(*args, **kwargs)
                elapsed = time.time() - start
                if log_func:
                    log_func(
                        msg.format(func_name=func.__name__, elapsed_time=elapsed))
                return result

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                start = time.time()
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                if log_func:
                    log_func(
                        msg.format(func_name=func.__name__,
                                   elapsed_time=elapsed))
                return result

            return sync_wrapper

    return decorator
