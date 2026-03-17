"""
app/rag/retriever.py
封装 ChromaDB 检索逻辑，使用 Google Gemini Embedding。
"""

import logging
from functools import lru_cache
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

from app.core.config import settings

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_vectordb() -> Chroma | None:
    persist_dir = Path(settings.chroma_persist_dir)
    if not persist_dir.exists():
        log.warning("ChromaDB 目录不存在: %s，请先运行 build_vector_db.py", persist_dir.resolve())
        return None

    embeddings = HuggingFaceEmbeddings(model_name=settings.embed_model)
    db = Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )
    log.info("ChromaDB 已加载，共 %d 个向量", db._collection.count())
    return db


def get_retriever():
    db = _load_vectordb()
    if db is None:
        return None
    return db.as_retriever(
        search_type="mmr",
        search_kwargs={"k": settings.retriever_k, "fetch_k": settings.retriever_k * 3},
    )


def retrieve(query: str) -> str:
    retriever = get_retriever()
    if retriever is None:
        return "知识库尚未初始化，请先运行 build_vector_db.py 构建向量数据库。"

    try:
        docs = retriever.invoke(query)
    except Exception as e:
        log.warning("检索时出错（将跳过知识库）: %s", e)
        return "知识库检索暂不可用，请根据自身知识回答。"
    if not docs:
        return "未在知识库中找到相关内容。"

    parts = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "unknown")
        headers = {k: v for k, v in doc.metadata.items() if k.startswith("h")}
        header_str = " > ".join(headers.values()) if headers else ""
        parts.append(
            f"[{i}] 来源: {source}"
            + (f" | {header_str}" if header_str else "")
            + f"\n{doc.page_content}"
        )
    return "\n\n---\n\n".join(parts)
