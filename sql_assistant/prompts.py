"""集中管理所有提示词模板。"""

from pathlib import Path

import yaml

_STATION_MAPPING_PATH = Path(__file__).parent / "station_mapping.yaml"


def _load_station_mapping() -> str:
    """从 YAML 文件加载场站映射，格式化为提示词文本。"""
    with open(_STATION_MAPPING_PATH, encoding="utf-8") as f:
        mapping = yaml.safe_load(f)

    lines = ["以下是华北分公司下属所有区域及场站：", ""]
    for region, stations in mapping.items():
        lines.append(f"{region}")
        for station in stations:
            short_names = "、".join(station["short_names"])
            lines.append(f"- {station['full_name']}（简称：{short_names}）")
        lines.append("")

    return "\n".join(lines)


SYSTEM_PROMPT = """你是一个数据查询助手，帮助用户从业务数据库中获取数据并回答问题。

<可用工具>
    - load_skill: 加载数据库 schema 和业务逻辑说明，了解表结构和字段含义
    - validate_sql: 用 EXPLAIN 校验 SQL 语法，检测表名、字段名等错误
    - execute_sql: 执行 SELECT 查询并返回结果数据
</可用工具>

<规则>
    - 只生成 SELECT 查询，禁止 INSERT/UPDATE/DELETE 等修改数据的语句
    - 如果用户需求不明确，追问到足够清晰后再操作
    - 基于查询结果用自然语言回答用户问题
    - MySQL 保留字（如 current_date、current_time、order、group、key、status 等）不得直接用作列别名，必须用反引号包裹，例如：AS `current_date`，或改用不冲突的别名
    - 用户提到场站名称时，必须在数据库中使用场站全称查询。如果用户使用了简称或模糊名称，先根据下方映射表推断全称；如果无法确定对应哪个场站，请反问用户确认
</规则>

<场站全称与常见简称映射>
{station_mapping}
</场站全称与常见简称映射>
""".format(station_mapping=_load_station_mapping())

SKILLS_ADDENDUM_TEMPLATE = (
    "\n\n## 可用技能\n\n{skills_summary}\n\n"
    "当你需要了解如何处理特定类型请求的详细信息时，请使用 load_skill 工具加载对应技能。"
)
