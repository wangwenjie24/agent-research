"""SQL 助手的工具定义。"""

import os
import re

import pymysql
from langchain.tools import tool

from sql_assistant.skills import get_skills

# 禁止的 SQL 关键字（DML / DDL / 其他写操作）
_BLOCKED_KEYWORDS = frozenset({
    "INSERT", "UPDATE", "DELETE", "REPLACE",
    "DROP", "ALTER", "CREATE", "TRUNCATE", "RENAME",
    "GRANT", "REVOKE",
    "LOAD", "CALL", "SET", "LOCK", "UNLOCK",
})


def _strip_comments(sql: str) -> str:
    """剥离 SQL 开头的 -- 单行注释和空行，返回实际语句。"""
    while "\n" in sql:
        first_line, rest = sql.split("\n", 1)
        stripped = first_line.strip()
        if stripped.startswith("--") or stripped == "":
            sql = rest.strip()
        else:
            break
    # 单行以 -- 开头的兜底
    if sql.lstrip().startswith("--"):
        sql = "\n".join(
            line for line in sql.split("\n")
            if not line.strip().startswith("--")
        ).strip()
    return sql


def _is_read_only(sql: str) -> bool:
    """检查 SQL 是否为只读查询。

    反向思维：不枚举允许的写法，而是拦截所有写操作关键字。
    """
    sql = _strip_comments(sql.strip().rstrip(";"))
    if not sql:
        return False
    # 防注入：禁止多语句（中间含分号）
    if ";" in sql:
        return False
    # 提取第一个关键字
    match = re.match(r"\s*(\w+)", sql)
    if not match:
        return False
    return match.group(1).upper() not in _BLOCKED_KEYWORDS


def _get_mysql_config() -> dict:
    """从环境变量读取 MySQL 连接配置。"""
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", ""),
    }


@tool
def load_skill(skill_name: str) -> str:
    """按需加载技能的完整内容到 agent 上下文中。

    当需要了解如何处理特定类型请求的详细信息时使用此工具。
    它将提供全面的指令、策略和指南。

    Args:
        skill_name: 要加载的技能名称（如 "sales_analytics", "inventory_management"）
    """
    skills = get_skills()
    for skill in skills:
        if skill["name"] == skill_name:
            return f"Loaded skill: {skill_name}\n\n{skill['content']}"

    available = ", ".join(s["name"] for s in skills)
    return f"Skill '{skill_name}' not found. Available skills: {available}"


@tool
def validate_sql(sql: str) -> str:
    """使用 EXPLAIN 校验 SQL 语句是否能被 MySQL 正确解析和执行。

    通过 EXPLAIN 预执行检测语法错误、表不存在、字段不存在等问题，
    不会实际修改数据。生成 SQL 后应调用此工具进行校验。

    Args:
        sql: 需要校验的 SQL 语句
    """
    sql = sql.strip().rstrip(";")
    if not _is_read_only(sql):
        return "仅允许执行只读查询（SELECT），不允许修改数据。"

    try:
        conn = pymysql.connect(**_get_mysql_config())
    except pymysql.Error as e:
        return f"数据库连接失败: {e}"

    try:
        with conn.cursor() as cursor:
            cursor.execute(f"EXPLAIN {sql}")
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
        return f"SQL 校验通过。执行计划:\n{result}"
    except pymysql.Error as e:
        return f"SQL 校验失败:\n{e}"
    finally:
        conn.close()


@tool
def execute_sql(sql: str) -> str:
    """执行 SELECT 查询并返回结果。

    仅允许执行 SELECT 语句，用于获取查询结果数据。
    执行前应先用 validate_sql 校验语法。

    Args:
        sql: 要执行的 SELECT 查询语句
    """
    sql = sql.strip().rstrip(";")
    if not _is_read_only(sql):
        return "仅允许执行只读查询（SELECT），不允许修改数据。"

    try:
        conn = pymysql.connect(**_get_mysql_config())
    except pymysql.Error as e:
        return f"数据库连接失败: {e}"

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            if not rows:
                return "查询结果为空。"

            # 格式化为 Markdown 表格
            header = "| " + " | ".join(columns) + " |"
            separator = "| " + " | ".join(["---"] * len(columns)) + " |"
            data_rows = []
            for row in rows:
                data_rows.append("| " + " | ".join(str(v) for v in row) + " |")

            return f"{header}\n{separator}\n" + "\n".join(data_rows)
    except pymysql.Error as e:
        return f"查询执行失败:\n{e}"
    finally:
        conn.close()
