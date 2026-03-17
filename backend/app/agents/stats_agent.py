"""
app/agents/stats_agent.py
统计学 R 语言 Agent（LangGraph ReAct + Google Gemini）
"""

import logging
from functools import lru_cache

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from app.core.config import settings
from app.rag.retriever import retrieve

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位专业的统计学与 R 语言助教，擅长解释统计方法原理并提供 R 代码示例。

回答时请包含：
1. 统计方法的核心原理（2-3 句话）
2. R 代码示例（用代码块格式）
3. 关键参数或输出结果的解读

请优先使用 rag_search 工具检索知识库，再结合自身知识给出完整答案。回答使用中文。"""


@tool
def rag_search(query: str) -> str:
    """从统计学与 R 语言知识库中检索相关内容。
    适用于：统计方法原理、R 代码示例、参数解读、模型选择等问题。
    输入应为简洁的检索关键词或完整问题。"""
    return retrieve(query)


@tool
def r_code_hint(topic: str) -> str:
    """返回在 R 中运行统计分析的基础代码提示。
    适用于：用户询问如何在 R 中执行某类分析时。
    输入为统计方法名称，如 t-test、ANOVA、linear regression。"""
    hints = {
        "t-test": "使用 `t.test(x, y)` 进行独立样本 T 检验，`t.test(x, mu=0)` 进行单样本检验。",
        "anova": "使用 `aov(y ~ group, data=df)` 建模，`summary()` 查看结果，`TukeyHSD()` 做事后检验。",
        "linear regression": "使用 `lm(y ~ x1 + x2, data=df)` 建立线性模型，`summary()` 查看系数与 R²。",
        "logistic regression": "使用 `glm(y ~ x, data=df, family=binomial)` 建立逻辑回归，`exp(coef())` 得到 OR 值。",
        "correlation": "使用 `cor(x, y)` 计算 Pearson 相关系数，`cor.test(x, y)` 获得显著性检验。",
    }
    key = topic.lower().strip()
    for k, v in hints.items():
        if k in key:
            return v
    return f"关于 '{topic}' 的 R 代码，请参考 CRAN 文档：https://cran.r-project.org/manuals.html"


TOOLS = [rag_search, r_code_hint]


@lru_cache(maxsize=1)
def _build_agent():
    llm = ChatGoogleGenerativeAI(
        model=settings.chat_model,
        google_api_key=settings.google_api_key,
        temperature=0.2,
    )
    return create_react_agent(llm, TOOLS, prompt=SYSTEM_PROMPT)


def run_agent(question: str) -> str:
    try:
        agent = _build_agent()
        result = agent.invoke({"messages": [HumanMessage(content=question)]})
        messages = result.get("messages", [])
        for msg in reversed(messages):
            content = getattr(msg, "content", None)
            if not content:
                continue
            # Gemini 有时返回 list[dict]，需拼接为纯文本
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        parts.append(block)
                text = "\n".join(p for p in parts if p)
                if text:
                    return text
            elif isinstance(content, str):
                return content
        return "Agent 未返回有效答案。"
    except Exception as e:
        log.error("Agent 执行出错: %s", e, exc_info=True)
        return f"处理您的问题时发生错误：{e}"
