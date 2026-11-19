from datetime import datetime, timezone


def now_naive() -> datetime:
    """数据库统一存 UTC 的 naive DATETIME，避免 MySQL/SQLite 时区行为差异。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)
