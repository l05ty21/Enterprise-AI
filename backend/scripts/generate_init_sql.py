"""根据 ORM 模型生成 MySQL 8.0 的 init.sql。

用法：
    python scripts/generate_init_sql.py
输出：
    backend/sql/init.sql
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateIndex, CreateTable

from app import models  # noqa: F401  注册全部模型
from app.db.base import Base

HEADER = """-- =====================================================================
--  智企协同 Enterprise AI · 数据库 V1.0
--  由 scripts/generate_init_sql.py 依据 ORM 模型自动生成，请勿手工修改。
--  重新生成：python scripts/generate_init_sql.py
-- =====================================================================

CREATE DATABASE IF NOT EXISTS enterprise_ai
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE enterprise_ai;

SET NAMES utf8mb4;

"""

FOOTER = """
-- =====================================================================
--  初始数据请使用种子脚本写入（会自动加密密码、绑定内置角色）：
--      alembic upgrade head
--      python -m app.db.seed
-- =====================================================================
"""


def main() -> int:
    dialect = mysql.dialect()
    chunks: list[str] = [HEADER]

    for table in Base.metadata.sorted_tables:
        chunks.append(f"-- ---------- {table.name} ----------\n")
        chunks.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";\n")
        for index in sorted(table.indexes, key=lambda item: item.name or ""):
            chunks.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ";\n")
        chunks.append("\n")

    chunks.append(FOOTER)

    output = Path(__file__).resolve().parent.parent / "sql" / "init.sql"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(chunks), encoding="utf-8")
    print(f"已生成 {output}（{len(Base.metadata.tables)} 张表）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
