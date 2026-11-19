from __future__ import annotations

from sqlalchemy import Integer, Text
from sqlalchemy.dialects import mysql


def bigint_unsigned():
    """MySQL 使用 BIGINT UNSIGNED；SQLite（测试）退化为 INTEGER 以便自增主键工作。"""
    return mysql.BIGINT(unsigned=True).with_variant(Integer(), "sqlite")


def long_text():
    """MySQL 使用 LONGTEXT；SQLite 使用 TEXT。"""
    return mysql.LONGTEXT().with_variant(Text(), "sqlite")
