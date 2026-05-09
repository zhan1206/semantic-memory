#!/usr/bin/env python3
"""
Semantic Memory — 统一日志模块
替换所有模块中的 print() 分散日志，实现集中管理
支持文件日志 + 控制台彩色输出 + 日志轮转
"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

# ─── 全局日志配置 ──────────────────────────────────────────
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
_QCLAW_BASE = os.path.normpath(os.path.join(SKILL_DIR, "..", "..", ".."))
LOG_DIR = os.path.join(os.environ.get("QCLAW_DATA", os.path.join(_QCLAW_BASE, "data")),
                       "semantic-memory", "logs")
LOG_FILE = os.path.join(LOG_DIR, "semantic-memory.log")
os.makedirs(LOG_DIR, exist_ok=True)

# ─── 颜色码 ────────────────────────────────────────────────
_COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "gray": "\033[90m",
}
_NO_COLOR = os.environ.get("NO_COLOR", "") or os.environ.get("TERM", "") == "dumb"


def _color(code, text):
    return f"{_COLORS.get(code, '')}{text}{_COLORS['reset']}" if not _NO_COLOR else text


# ─── 格式化器 ──────────────────────────────────────────────
class ColoredFormatter(logging.Formatter):
    """控制台：彩色输出"""

    LEVEL_COLORS = {
        "DEBUG": "gray",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red",
    }

    def format(self, record):
        level = record.levelname
        color = self.LEVEL_COLORS.get(level, "")
        record.levelname_colored = _color(color, f"[{level:>8}]")
        record.name_colored = _color("cyan", record.name)
        return super().format(record)


# ─── 初始化 ────────────────────────────────────────────────
_loggers: dict = {}


def get_logger(name: str = "semantic-memory", level: int = None) -> logging.Logger:
    """
    获取已配置的 logger 实例
    name: 模块名，如 "core", "memory_manager", "api_server"
    level: 日志级别，默认 INFO
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(level or logging.INFO)
    logger.propagate = False  # 不向上传播到 root logger

    # 避免重复添加 handler
    if logger.handlers:
        _loggers[name] = logger
        return logger

    # 文件 handler（轮转，最大 5MB，保留 3 个备份）
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(file_handler)
    except (OSError, IOError):
        pass  # 日志目录不可写时静默跳过

    # 控制台 handler（彩色）
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    fmt = "%(levelname_colored)s %(name_colored)s %(message)s"
    console_handler.setFormatter(ColoredFormatter(fmt))
    logger.addHandler(console_handler)

    _loggers[name] = logger
    return logger


# ─── 全局快捷函数 ──────────────────────────────────────────
def debug(msg, *args, **kwargs):
    get_logger().debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    get_logger().info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    get_logger().warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    get_logger().error(msg, *args, **kwargs)


def critical(msg, *args, **kwargs):
    get_logger().critical(msg, *args, **kwargs)


# ─── 进度条（用于批量操作）──────────────────────────────────
def progress_bar(iterable, total=None, desc="", width=40, file=None):
    """
    简单文本进度条（无需第三方库）
    用法:
        for item in progress_bar(items, desc="处理中"):
            process(item)
    """
    if file is None:
        file = sys.stderr

    iterator = iter(iterable)
    length = total or (getattr(iterable, "__len__", lambda: None)() or 0)
    filled = 0

    def _print_bar():
        pct = filled / max(length, 1)
        bar = "█" * int(width * pct) + "░" * (width - int(width * pct))
        prefix = f"\r{desc}: " if desc else ""
        file.write(f"{prefix}|{bar}| {filled}/{max(length, filled)} ({pct*100:.0f}%)")
        file.flush()

    _print_bar()
    for i, item in enumerate(iterator):
        yield item
        filled = i + 1
        _print_bar()

    file.write("\n")
    file.flush()


# ─── CLI 输出（run.py 专用彩色输出）─────────────────────────
class CLIOutput:
    """CLI 输出格式工具"""

    @staticmethod
    def ok(msg):
        print(_color("green", f"✓ {msg}"))

    @staticmethod
    def info(msg):
        print(_color("blue", f"ℹ {msg}"))

    @staticmethod
    def warn(msg):
        print(_color("yellow", f"⚠ {msg}"))

    @staticmethod
    def error(msg):
        print(_color("red", f"✗ {msg}"), file=sys.stderr)

    @staticmethod
    def header(msg):
        print(_color("bold", f"\n{'━' * 50}"))
        print(_color("bold", f"  {msg}"))
        print(_color("bold", f"{'━' * 50}"))

    @staticmethod
    def table(headers, rows, max_width=None):
        """简单表格输出"""
        cols = len(headers)
        widths = [len(h) for h in headers]

        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(str(cell)))

        if max_width:
            widths = [min(w, max_width) for w in widths]

        # 表头
        header_line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
        print(_color("bold", header_line))
        print(_color("gray", "  ".join("─" * w for w in widths)))

        # 数据行
        for row in rows:
            cells = [str(c)[:w] for c, w in zip(row, widths)]
            print("  ".join(cells))


# ─── 上下文管理器：临时静默 ─────────────────────────────────
import contextlib


@contextlib.contextmanager
def quiet():
    """临时抑制所有日志输出"""
    logger = get_logger()
    old_level = logger.level
    logger.setLevel(logging.CRITICAL + 1)
    try:
        yield
    finally:
        logger.setLevel(old_level)


if __name__ == "__main__":
    # 演示
    log = get_logger("demo")
    log.info("信息日志")
    log.warning("警告日志")
    log.error("错误日志")
    log.debug("调试日志（默认不显示）")

    CLIOutput.ok("安装成功")
    CLIOutput.warn("配置未找到，使用默认值")
    CLIOutput.error("模型下载失败")

    print("\n进度条演示:")
    for i in progress_bar(range(20), total=20, desc="下载"):
        import time
        time.sleep(0.05)
