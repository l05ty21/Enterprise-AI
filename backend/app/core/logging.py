from __future__ import annotations

import logging
import sys

from app.core.config import settings

try:  # structlog 在测试环境可能未安装，缺失时退回标准 logging
    import structlog
except ImportError:  # pragma: no cover
    structlog = None  # type: ignore[assignment]


def configure_logging(level: str | None = None) -> None:
    log_level = (level or settings.LOG_LEVEL).upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric_level)

    # SQLAlchemy 的连接池日志太吵，默认压到 WARNING
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DB_ECHO else logging.WARNING
    )
    logging.getLogger("aiomysql").setLevel(logging.WARNING)
    logging.getLogger("asyncmy").setLevel(logging.WARNING)

    if structlog is not None:
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(ensure_ascii=False)
                if settings.is_prod
                else structlog.dev.ConsoleRenderer(colors=False),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )


def get_logger(name: str = "app"):
    if structlog is not None:
        return structlog.get_logger(name)
    return logging.getLogger(name)
