"""
app/agents/stats_agent.py
统计学 R 语言 Agent（LangGraph ReAct + Google Gemini）
含护栏机制：必须先确认前提假设，才能生成 R 代码。
"""

import logging
from functools import lru_cache

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from app.core.config import settings
from app.rag.retriever import retrieve

log = logging.getLogger(__name__)

# ── 系统提示词（护栏核心）────────────────────────────────────────────────────

SYSTEM_PROMPT = """你是一位严谨的统计学与 R 语言助教。你有一条不可违反的工作协议：

═══════════════════════════════════════════
【护栏协议】当用户提出统计分析需求时（如：T检验、ANOVA、线性回归、逻辑回归、相关分析等），
你必须严格按照以下步骤执行，不得跳过：

第一步：调用 check_statistical_prerequisites 工具，获取该分析方法的前提假设条件。

第二步：检查当前对话历史。判断用户是否已经明确说明了满足这些前提假设。
  - 如果用户已在之前的消息中确认了所有前提假设 → 跳转第四步。
  - 如果用户尚未确认 → 执行第三步。

第三步：向用户提出具体追问。
  格式要求：
  - 先简要说明为何需要确认（1句话）
  - 然后列出 2~4 个需要用户回答的具体问题（编号列表）
  - 结尾加一句："请回复确认后，我将为您生成完整的 R 代码。"
  - 此步骤完成后，立刻停止。绝对不能在追问的同时输出任何 R 代码。

第四步：用户确认前提假设后，调用 rag_search 工具检索代码示例，
  然后输出完整回答，格式如下：
  1. 简述该方法的核心原理（2~3句）
  2. 完整 R 代码（含前提检验代码 + 主分析代码 + 结果可视化），每行代码必须有中文注释
  3. 结果解读指南（说明如何看关键输出值）
═══════════════════════════════════════════

对于非统计分析类问题（如概念解释、方法选择建议、理论知识等），正常回答，无需走护栏协议。

所有回答使用中文。"""

# ── 前提假设知识库（兜底，确保关键方法有覆盖）────────────────────────────────

_PREREQUISITES: dict[str, list[str]] = {
    "t检验": [
        "数据是否来自正态分布总体（可用 Shapiro-Wilk 检验）",
        "两组样本是否相互独立",
        "两组方差是否齐性（可用 Levene 检验或 F 检验）",
        "样本量是否足够（建议每组 ≥ 30，或已验证正态性）",
    ],
    "anova": [
        "各组数据是否服从正态分布",
        "各组方差是否齐性（可用 Bartlett 或 Levene 检验）",
        "观测值是否相互独立",
        "是否存在离群值（可用箱线图初步判断）",
    ],
    "线性回归": [
        "因变量与自变量之间是否存在线性关系",
        "残差是否服从正态分布",
        "残差方差是否齐性（无异方差）",
        "观测值是否相互独立（无自相关）",
        "自变量之间是否存在严重多重共线性（VIF < 10）",
    ],
    "逻辑回归": [
        "因变量是否为二分类或多分类变量",
        "自变量与因变量 log-odds 之间是否存在线性关系",
        "观测值是否相互独立",
        "样本量是否足够（每个事件类别至少 10 个样本）",
        "自变量之间是否存在严重多重共线性",
    ],
    "相关分析": [
        "数据是否为连续变量（Pearson）或等级变量（Spearman）",
        "两个变量是否服从正态分布（Pearson 相关要求）",
        "变量之间的关系是否为线性（Pearson 适用）",
        "数据中是否存在显著离群值",
    ],
}


def _get_builtin_prerequisites(method: str) -> str | None:
    method_lower = method.lower()
    for key, items in _PREREQUISITES.items():
        if key in method_lower or any(alias in method_lower for alias in {
            "t-test": "t检验", "ttest": "t检验",
            "regression": "线性回归" if "logistic" not in method_lower else "逻辑回归",
            "correlation": "相关分析",
        }.get(key, key).split("|")):
            return f"【{key} 的前提假设条件】\n" + "\n".join(f"{i+1}. {p}" for i, p in enumerate(items))
    # 模糊匹配
    for key, items in _PREREQUISITES.items():
        if any(kw in method_lower for kw in key.split("|")):
            return f"【{key} 的前提假设条件】\n" + "\n".join(f"{i+1}. {p}" for i, p in enumerate(items))
    return None


# ── Tools ─────────────────────────────────────────────────────────────────────

@tool
def check_statistical_prerequisites(method: str) -> str:
    """【必须首先调用】检索指定统计方法的前提假设条件。
    在为用户生成任何 R 代码之前，必须先调用此工具确认前提假设。
    输入为统计分析方法名称，如：T检验、线性回归、ANOVA、逻辑回归、相关分析。"""
    builtin = _get_builtin_prerequisites(method)
    rag_result = retrieve(f"{method} 前提假设 使用条件 assumptions prerequisites")

    parts = []
    if builtin:
        parts.append(builtin)
    if rag_result and "尚未初始化" not in rag_result and "暂不可用" not in rag_result:
        parts.append(f"\n【知识库补充】\n{rag_result[:800]}")

    if parts:
        return "\n".join(parts)
    return f"未找到 '{method}' 的内置前提假设。请根据统计学通用原则判断：正态性、独立性、方差齐性。"


@tool
def rag_search(query: str) -> str:
    """从统计学与 R 语言知识库中检索代码示例和方法说明。
    仅在用户已确认前提假设后，用于获取 R 代码示例。
    输入应为具体的检索问题，如：'线性回归 R 代码示例'。"""
    return retrieve(query)


TOOLS = [check_statistical_prerequisites, rag_search]


# ── Agent 工厂 ─────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _build_agent():
    llm = ChatGoogleGenerativeAI(
        model=settings.chat_model,
        google_api_key=settings.google_api_key,
        temperature=0.3,
    )
    return create_react_agent(llm, TOOLS, prompt=SYSTEM_PROMPT)


def _extract_text(content) -> str:
    """将 Gemini 返回的 content（str 或 list[dict]）统一转为纯文本。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(p for p in parts if p)
    return ""


def run_agent(question: str, history: list[dict] | None = None) -> str:
    """
    对外入口：接收用户问题和对话历史，返回 Agent 最终答案。
    history 格式：[{"role": "user"/"assistant", "content": "..."}]
    """
    try:
        agent = _build_agent()

        # 构建消息列表：历史 + 当前问题
        messages = []
        for msg in (history or []):
            role = msg.get("role", "")
            content = msg.get("content", "")
            if not content:
                continue
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        messages.append(HumanMessage(content=question))

        result = agent.invoke({"messages": messages})

        # 取最后一条 AI 消息
        for msg in reversed(result.get("messages", [])):
            if isinstance(msg, AIMessage):
                text = _extract_text(msg.content)
                if text:
                    return text

        return "Agent 未返回有效答案。"
    except Exception as e:
        log.error("Agent 执行出错: %s", e, exc_info=True)
        return f"处理您的问题时发生错误：{e}"
