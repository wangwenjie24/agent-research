"""SQL 助手 agent 入口 - LangGraph graph 定义。

langgraph.json 通过 ./sql_assistant/agent.py:graph 引用此变量。
使用 langgraph dev 启动开发服务器，LangSmith 追踪自动生效。
"""

from dotenv import load_dotenv

# 加载 .env 环境变量（langgraph dev 会自动加载，此处兜底本地调试）
load_dotenv()

from langchain.agents import create_agent  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402

from sql_assistant.middleware import SkillMiddleware  # noqa: E402
from sql_assistant.prompts import SYSTEM_PROMPT  # noqa: E402

model = ChatOpenAI(model="GLM-4.7")

graph = create_agent(
    model,
    system_prompt=SYSTEM_PROMPT,
    middleware=[SkillMiddleware()],
)
