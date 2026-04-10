"""SQL 助手的技能定义。

技能以 Markdown 文件形式存储在 skills/ 目录中，
通过 YAML frontmatter 定义 name 和 description，
正文部分为完整技能内容（schema + 业务逻辑）。

get_skills() 每次调用都从磁盘读取，确保技能变更即时生效。
"""

from pathlib import Path
from typing import TypedDict

import yaml


class Skill(TypedDict):
    """可渐进式披露给 agent 的技能。"""
    name: str        # 唯一标识符
    description: str # 1-2 句描述，显示在系统提示词中
    content: str     # 完整技能内容（数据库 schema + 业务逻辑）


_SKILLS_DIR = Path(__file__).parent / "skills"


def _parse_skill_md(path: Path) -> Skill:
    """解析单个技能 Markdown 文件。

    文件格式：
    ---
    name: skill_name
    description: 技能描述
    ---
    技能正文内容...
    """
    text = path.read_text(encoding="utf-8")

    # 提取 YAML frontmatter
    if not text.startswith("---"):
        raise ValueError(f"技能文件 {path.name} 缺少 YAML frontmatter")

    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"技能文件 {path.name} frontmatter 格式错误")

    meta = yaml.safe_load(parts[1])
    content = parts[2].strip()

    return Skill(
        name=meta["name"],
        description=meta["description"],
        content=content,
    )


def get_skills() -> list[Skill]:
    """从 skills/ 目录读取所有 Markdown 技能文件。

    每次调用都重新扫描目录，新增、修改、删除技能文件后无需重启。
    注意：此函数包含同步文件 I/O，在 ASGI 环境中请使用 aget_skills()。
    """
    skills = []
    for path in sorted(_SKILLS_DIR.glob("*.md")):
        skills.append(_parse_skill_md(path))
    return skills


async def aget_skills() -> list[Skill]:
    """异步版本的 get_skills()，将阻塞文件 I/O 放到线程池执行。"""
    import asyncio
    return await asyncio.to_thread(get_skills)
