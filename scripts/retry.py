#!/usr/bin/env python3
"""
Semantic Memory — 重试机制模块
提供指数退避重试装饰器，用于保护 API 调用和记忆操作的稳定性
"""
import time
import functools
import logging
from typing import Callable, Type, Tuple, Optional, Any

logger = logging.getLogger("retry")


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    jitter: float = 0.1,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """
    指数退避重试装饰器

    参数:
        max_attempts: 最大尝试次数（含第一次）
        delay: 初始延迟（秒）
        backoff: 退避倍率
        jitter: 随机抖动幅度（相对于 delay）
        exceptions: 需要捕获的异常类型，默认捕获所有
        on_retry: 重试时调用的回调函数 (exception, attempt) -> None

    用法:
        @retry(max_attempts=3, delay=2.0)
        def unstable_api_call(text: str) -> dict:
            return api.request(text)

        @retry(max_attempts=5, delay=1.0, exceptions=(TimeoutError, ConnectionError))
        def fetch_model() -> None:
            _ensure_model("bge-small-zh-v1.5")
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"[retry] {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    # 计算延迟：delay * backoff^(attempt-1) + jitter
                    sleep_time = delay * (backoff ** (attempt - 1))
                    jitter_range = sleep_time * jitter
                    import random
                    sleep_time += random.uniform(-jitter_range, jitter_range)
                    sleep_time = max(0.1, sleep_time)  # 至少等 0.1 秒

                    logger.warning(
                        f"[retry] {func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {sleep_time:.1f}s..."
                    )

                    if on_retry:
                        on_retry(e, attempt)

                    time.sleep(sleep_time)

            # 不应该到达这里，但以防万一
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


# ─── 预置重试组合 ───────────────────────────────────────────

def retry_once(func: Callable) -> Callable:
    """重试一次，等 1 秒"""
    return retry(max_attempts=2, delay=1.0)(func)


def retry_thrice(func: Callable) -> Callable:
    """重试三次，指数退避 1s → 2s → 4s"""
    return retry(max_attempts=3, delay=1.0, backoff=2.0)(func)


def retry_api(func: Callable) -> Callable:
    """
    API 专用重试策略：
    - 最多 5 次（网络可能不稳定）
    - 初始 0.5s，快速失败
    - 抖动 ±20%，避免惊群效应
    """
    return retry(
        max_attempts=5,
        delay=0.5,
        backoff=2.0,
        jitter=0.2,
        exceptions=(ConnectionError, TimeoutError, OSError),
    )(func)


# ─── 异步版本（用于 FastAPI）────────────────────────────────
def retry_async(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    jitter: float = 0.1,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """异步版本的 retry 装饰器（用于 FastAPI endpoints）"""
    import asyncio
    import functools
    import random

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"[retry:async] {func.__name__} failed after {max_attempts}: {e}"
                        )
                        raise

                    sleep_time = delay * (backoff ** (attempt - 1))
                    sleep_time += random.uniform(-sleep_time * jitter, sleep_time * jitter)
                    sleep_time = max(0.1, sleep_time)

                    logger.warning(
                        f"[retry:async] {func.__name__} attempt {attempt}/{max_attempts} "
                        f"failed: {e}. Retrying in {sleep_time:.1f}s..."
                    )
                    await asyncio.sleep(sleep_time)

            if last_exception:
                raise last_exception

        return wrapper
    return decorator


if __name__ == "__main__":
    # 演示
    print("=== Retry Module Demo ===")

    @retry(max_attempts=3, delay=0.5, exceptions=(ValueError,))
    def flaky_function(attempt: int) -> str:
        if attempt < 3:
            raise ValueError(f"Simulated failure #{attempt}")
        return "Success after 3 retries!"

    result = flaky_function(attempt=1)
    print(f"Result: {result}")
