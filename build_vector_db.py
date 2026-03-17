"""
build_vector_db.py
读取 data/knowledge_base 下的 Markdown 文件，
按「MarkdownHeader → RecursiveCharacter」两级切分，
用 Google Gemini text-embedding-004 向量化后存入本地 ChromaDB。
"""

import os
import sys
import logging
from pathlib import Path

from dotenv import load_dotenv
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma

load_dotenv(Path("backend/.env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ── 配置 ──────────────────────────────────────────────────────────────────────

KB_DIR = Path("data/knowledge_base")
CHROMA_DIR = Path("backend/chroma_db")
COLLECTION_NAME = "stats_r_knowledge"
EMBED_MODEL = "all-MiniLM-L6-v2"  # 本地 sentence-transformers 模型，无需 API Key

CHUNK_SIZE = 800        # RecursiveCharacterTextSplitter 目标 chunk 大小
CHUNK_OVERLAP = 100     # 相邻 chunk 重叠字符数

# Markdown 按哪些标题级别做第一级切割
HEADERS_TO_SPLIT = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
]

# ── 检查 API Key ───────────────────────────────────────────────────────────────

def check_api_key() -> str:
    # embedding 使用本地模型，无需 API Key；此函数仅作占位保留
    return ""

# ── 加载 Markdown 文件 ────────────────────────────────────────────────────────

def load_markdown_files() -> list[tuple[str, str]]:
    """返回 [(文件名, 文本内容), ...]"""
    md_files = sorted(KB_DIR.glob("*.md"))
    if not md_files:
        log.error("data/knowledge_base 目录下没有找到 .md 文件")
        sys.exit(1)
    log.info("找到 %d 个 Markdown 文件", len(md_files))
    docs = []
    for f in md_files:
        text = f.read_text(encoding="utf-8")
        if len(text) < 100:
            log.warning("跳过内容过短的文件: %s", f.name)
            continue
        docs.append((f.name, text))
        log.info("  ✅ %s (%d 字符)", f.name, len(text))
    return docs

# ── 两级切分 ──────────────────────────────────────────────────────────────────

def split_documents(raw_docs: list[tuple[str, str]]):
    """
    第一级：MarkdownHeaderTextSplitter —— 按标题层级切出语义块
    第二级：RecursiveCharacterTextSplitter —— 控制每块不超过 CHUNK_SIZE
    """
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT,
        strip_headers=False,        # 保留标题行，让 chunk 携带上下文
    )
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", ".", " ", ""],
    )

    all_chunks = []
    for filename, text in raw_docs:
        # 第一级：按标题切分
        header_docs = header_splitter.split_text(text)

        # 为每个 header-doc 补充来源元数据
        for doc in header_docs:
            doc.metadata["source"] = filename

        # 第二级：对每个 header-doc 做字符级细切
        fine_chunks = char_splitter.split_documents(header_docs)
        all_chunks.extend(fine_chunks)
        log.info("  %s -> %d header-blocks -> %d fine-chunks",
                 filename, len(header_docs), len(fine_chunks))

    log.info("切分完成，共 %d 个 chunk", len(all_chunks))
    return all_chunks

# ── 构建 ChromaDB ─────────────────────────────────────────────────────────────

def build_vector_db(chunks, api_key: str):
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

    log.info("开始向量化并写入 ChromaDB（共 %d 个 chunk，请稍候…）", len(chunks))

    # 如果已有同名 collection，先删除再重建（避免重复写入）
    import chromadb
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    existing = [c.name for c in client.list_collections()]
    if COLLECTION_NAME in existing:
        log.info("检测到已有 collection '%s'，先清空再重建", COLLECTION_NAME)
        client.delete_collection(COLLECTION_NAME)

    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(CHROMA_DIR),
    )

    count = vectordb._collection.count()
    log.info("✅ 数据库构建成功，共存入 %d 个向量", count)
    print(f"\n{'='*50}")
    print(f"  数据库构建成功，共存入 {count} 个向量")
    print(f"  Collection : {COLLECTION_NAME}")
    print(f"  存储路径   : {CHROMA_DIR.resolve()}")
    print(f"{'='*50}\n")
    return vectordb

# ── 主流程 ────────────────────────────────────────────────────────────────────

def main():
    api_key = check_api_key()
    raw_docs = load_markdown_files()
    chunks = split_documents(raw_docs)
    build_vector_db(chunks, api_key)

if __name__ == "__main__":
    main()
