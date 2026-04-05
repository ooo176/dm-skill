#!/usr/bin/env python3
"""
只读执行达梦 SQL：校验通过后连接并输出 JSON。
禁止 INSERT/UPDATE/DELETE/DDL 等写操作。
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sys
from typing import Any


def _is_arm_architecture() -> bool:
    """当前进程所在机器是否为 ARM/AArch64（dmPython 暂无官方 ARM 包时，连库查询不可用）。"""
    machine = (platform.machine() or "").lower()
    processor = (platform.processor() or "").lower()
    if "aarch64" in machine or "aarch64" in processor:
        return True
    if "arm64" in machine or "arm64" in processor:
        return True
    if machine.startswith("arm") or "armv" in machine:
        return True
    return False


def _exit_arm_no_dmpython() -> None:
    print(
        json.dumps(
            {
                "ok": False,
                "error": "当前为 ARM 架构，暂不支持通过本脚本的 dmPython 连接达梦（官方未提供对应 ARM 的 dmPython 包）。"
                "请改用 x86_64/amd64 环境，或使用达梦 JDBC 等 Java 客户端在 ARM 上查询；仅校验 SQL 仍可使用 --validate-only。",
                "machine": platform.machine() or "",
            },
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )
    sys.exit(2)


def _strip_sql_comments(sql: str) -> str:
    """移除块注释与行注释（不处理字符串内注释的边界情况，复杂 SQL 请避免在字符串中含 -- 或 /*）。"""
    s = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    s = re.sub(r"--[^\n]*", " ", s)
    return s


_FORBIDDEN = re.compile(
    r"\b("
    r"INSERT|UPDATE|DELETE|MERGE|REPLACE|"
    r"DROP|CREATE|ALTER|TRUNCATE|RENAME|"
    r"GRANT|REVOKE|COMMIT|ROLLBACK|SAVEPOINT|"
    r"CALL|EXECUTE|EXEC"
    r")\b",
    re.IGNORECASE,
)

_ALLOWED_START = frozenset(
    {"SELECT", "WITH", "EXPLAIN", "SHOW", "DESC", "DESCRIBE"}
)


def validate_readonly_sql(sql: str) -> str:
    raw = sql.strip()
    if not raw:
        raise ValueError("SQL 为空")
    cleaned = _strip_sql_comments(raw).strip()
    if not cleaned:
        raise ValueError("去掉注释后 SQL 为空")
    parts = [p.strip() for p in cleaned.split(";") if p.strip()]
    if len(parts) > 1:
        raise ValueError("不允许一次执行多条语句（多个分号分隔）")
    stmt = parts[0] if parts else cleaned.rstrip(";").strip()
    if _FORBIDDEN.search(stmt):
        m = _FORBIDDEN.search(stmt)
        raise ValueError(f"只读模式禁止关键字: {m.group(1) if m else '?'}")
    first = re.match(r"^\s*(\w+)", stmt)
    if not first:
        raise ValueError("无法解析 SQL 首关键字")
    kw = first.group(1).upper()
    if kw not in _ALLOWED_START:
        raise ValueError(
            f"只读模式仅允许以以下关键字开头: {', '.join(sorted(_ALLOWED_START))}"
        )
    return raw.rstrip().rstrip(";")


def _connect():
    try:
        import dmPython  # type: ignore
    except ImportError as e:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "未安装 dmPython。请: pip install dmPython 或从达梦安装目录安装对应 whl",
                    "detail": str(e),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        sys.exit(2)

    dsn = os.environ.get("DM_DSN")
    if dsn:
        return dmPython.connect(dsn)

    user = os.environ.get("DM_USER")
    password = os.environ.get("DM_PASSWORD")
    server = os.environ.get("DM_HOST", "localhost")
    port = int(os.environ.get("DM_PORT", "5236"))
    if not user or password is None:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "请设置环境变量 DM_DSN 或 DM_USER + DM_PASSWORD（可选 DM_HOST、DM_PORT、DM_SCHEMA）",
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        sys.exit(2)

    kwargs: dict[str, Any] = {
        "user": user,
        "password": password,
        "server": server,
        "port": port,
    }
    schema = os.environ.get("DM_SCHEMA")
    if schema:
        kwargs["schema"] = schema
    return dmPython.connect(**kwargs)


def _rows_to_json(
    columns: list[str] | None, rows: list[tuple[Any, ...]], max_rows: int
) -> dict[str, Any]:
    cols = columns or []
    limited = rows[:max_rows]
    dict_rows = [dict(zip(cols, row)) for row in limited]
    return {
        "columns": cols,
        "row_count": len(rows),
        "returned": len(dict_rows),
        "truncated": len(rows) > max_rows,
        "rows": dict_rows,
    }


def run_query(sql: str, max_rows: int) -> dict[str, Any]:
    validated = validate_readonly_sql(sql)
    if _is_arm_architecture():
        _exit_arm_no_dmpython()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(validated)
        if cur.description:
            columns = [d[0] for d in cur.description]
            rows = list(cur.fetchall())
            payload = _rows_to_json(columns, rows, max_rows)
        else:
            payload = {
                "columns": [],
                "row_count": cur.rowcount if cur.rowcount is not None else 0,
                "returned": 0,
                "truncated": False,
                "rows": [],
                "note": "无结果集（可能为仅 EXPLAIN/SHOW 等，依驱动行为而定）",
            }
        return {"ok": True, "sql": validated, **payload}
    finally:
        conn.close()


def main() -> None:
    p = argparse.ArgumentParser(description="达梦只读 SQL 查询，输出 JSON")
    p.add_argument("--sql", help="SQL 字符串")
    p.add_argument("--file", "-f", help="从文件读取 SQL")
    p.add_argument(
        "--max-rows",
        type=int,
        default=int(os.environ.get("DM_MAX_ROWS", "500")),
        help="最多返回行数（默认 500，可用环境变量 DM_MAX_ROWS）",
    )
    p.add_argument(
        "--validate-only",
        action="store_true",
        help="仅校验 SQL，不连接数据库",
    )
    args = p.parse_args()

    if bool(args.sql) == bool(args.file):
        print(
            json.dumps(
                {"ok": False, "error": "请指定其一: --sql 或 --file"},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    sql = args.sql if args.sql else open(args.file, encoding="utf-8").read()

    if args.validate_only:
        try:
            v = validate_readonly_sql(sql)
            print(json.dumps({"ok": True, "validated": v}, ensure_ascii=False))
        except ValueError as e:
            print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
            sys.exit(1)
        return

    try:
        out = run_query(sql, max(1, args.max_rows))
        print(json.dumps(out, ensure_ascii=False, default=str))
    except ValueError as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(1)
    except Exception as e:
        print(
            json.dumps({"ok": False, "error": "执行失败", "detail": str(e)}, ensure_ascii=False),
            file=sys.stderr,
        )
        sys.exit(3)


if __name__ == "__main__":
    main()
