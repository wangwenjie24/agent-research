"""技能中间件：将技能描述注入系统提示词，实现渐进式披露。

通过 before_agent 钩子在每次 Agent 调用时动态加载技能列表到状态中，
wrap_model_call 从状态读取并注入系统提示词。
生产环境下替换 get_skills() 实现即可支持数据库、配置文件等动态数据源。
"""

from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import SystemMessage
from langgraph.runtime import Runtime
from typing_extensions import NotRequired

from langchain.agents import AgentState
from sql_assistant.prompts import SKILLS_ADDENDUM_TEMPLATE
from sql_assistant.skills import aget_skills, get_skills
from sql_assistant.tools import execute_sql, load_skill, validate_sql


class SkillState(AgentState):
    """扩展 Agent 状态，存储 before_agent 钩子动态加载的技能摘要。"""
    skills_summary: NotRequired[str]


class SkillMiddleware(AgentMiddleware):
    """将技能描述注入系统提示词的中间件。

    使用 before_agent 在每次调用时加载最新技能列表到状态，
    wrap_model_call 从状态中读取并追加到系统提示词。
    """

    state_schema = SkillState
    tools = [load_skill, validate_sql, execute_sql]

    def before_agent(self, state: SkillState, runtime: Runtime) -> dict[str, Any] | None:
        """在 Agent 启动前动态加载技能列表到状态中（同步版本）。"""
        skills = get_skills()
        lines = [f"- **{s['name']}**: {s['description']}" for s in skills]
        return {"skills_summary": "\n".join(lines)}

    async def abefore_agent(self, state: SkillState, runtime: Runtime) -> dict[str, Any] | None:
        """在 Agent 启动前动态加载技能列表到状态中（异步版本）。"""
        skills = await aget_skills()
        lines = [f"- **{s['name']}**: {s['description']}" for s in skills]
        return {"skills_summary": "\n".join(lines)}

    def _modify_request(self, request: ModelRequest) -> ModelRequest:
        skills_summary = request.state.get("skills_summary", "")
        if not skills_summary:
            return request
        addendum = SKILLS_ADDENDUM_TEMPLATE.format(skills_summary=skills_summary)
        new_content = list(request.system_message.content_blocks) + [
            {"type": "text", "text": addendum}
        ]
        return request.override(system_message=SystemMessage(content=new_content))

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """从状态中读取技能摘要，注入系统提示词。"""
        return handler(self._modify_request(request))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """异步：从状态中读取技能摘要，注入系统提示词。"""
        return await handler(self._modify_request(request))
