# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

SQL 查询助手 — 基于 LangGraph + LangChain 构建的 Agent，使用渐进式披露（Progressive Disclosure）技能系统。用户提问时，系统先展示技能摘要，Agent 按需调用 `load_skill` 工具加载完整 Schema 和业务逻辑。

## 常用命令

```bash
# 安装依赖（使用 uv）
uv sync

# 启动开发服务器（LangGraph Studio）
uv run langgraph dev

# 添加依赖
uv add <package>
```

## 架构

```
sql_assistant/
├── agent.py       # 入口：graph 定义，langgraph.json 引用 graph 变量
├── middleware.py   # SkillMiddleware：拦截请求，将技能描述注入系统提示词
├── skills.py      # 技能注册表：Skill TypedDict + SKILLS 列表（轻量描述 + 完整内容）
└── tools.py       # Agent 工具：load_skill 按名加载技能完整内容
```

### 渐进式披露流程

1. `SkillMiddleware.wrap_model_call()` 在每次请求的系统提示词末尾追加所有技能的 **name + description**
2. Agent 判断需要哪个技能，调用 `load_skill(skill_name)` 工具
3. `load_skill` 从 `SKILLS` 列表中返回完整的 schema + 业务逻辑 + 示例查询
4. Agent 基于完整上下文生成 SQL

### 关键依赖

- **langgraph** — Graph 编排框架，`langgraph.json` 定义了 graph 入口和 Python 版本
- **langchain** — Agent 抽象层（`create_agent`、中间件、工具）
- **langchain-openai** — 兼容 OpenAI API 的模型调用（当前使用 GLM-5.1）
- **LangSmith** — 追踪和可观测性（通过 `LANGSMITH_*` 环境变量配置）

## 扩展技能

在 `sql_assistant/skills.py` 的 `SKILLS` 列表中添加新的 `Skill` 字典即可。中间件和工具会自动发现新技能，无需修改其他文件。

## 环境配置

复制 `.env.example` 为 `.env`，填写 `OPENAI_API_KEY`。LangSmith 追踪为可选配置。
