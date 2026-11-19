"""把 autogenerate 出来的 DEFAULT (CURRENT_TIMESTAMP) 改成 MySQL / SQLite 都认的写法。

Alembic 在 SQLite 上反射出的默认值带括号，MySQL 的 DEFAULT 不允许这种写法，
所以生成迁移后统一修正一次。
"""

from __future__ import annotations

import sys
from pathlib import Path

OLD = "sa.text('(CURRENT_TIMESTAMP)')"
NEW = "sa.text('CURRENT_TIMESTAMP')"


def main() -> int:
    versions_dir = Path(__file__).resolve().parent.parent / "alembic" / "versions"
    files = sorted(versions_dir.glob("*.py"))
    if not files:
        print("没有找到迁移文件")
        return 1

    total = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        count = text.count(OLD)
        if count:
            path.write_text(text.replace(OLD, NEW), encoding="utf-8")
            total += count
        print(f"{path.name}: 修正 {count} 处")
    print(f"合计修正 {total} 处")
    return 0


if __name__ == "__main__":
    sys.exit(main())
