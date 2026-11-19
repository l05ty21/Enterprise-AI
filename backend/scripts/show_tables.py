"""打印 SQLite 库里的表和行数，用于本地自检。"""

from __future__ import annotations

import sqlite3
import sys


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "_tmp_alembic.db"
    conn = sqlite3.connect(path)
    tables = [
        row[0]
        for row in conn.execute(
            "select name from sqlite_master where type='table' order by name"
        ).fetchall()
    ]
    print(f"database : {path}")
    print(f"tables   : {len(tables)}")
    for name in tables:
        count = conn.execute(f'select count(*) from "{name}"').fetchone()[0]
        print(f"  - {name:24s} rows={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
