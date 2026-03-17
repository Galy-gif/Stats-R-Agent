"""
fetch_real_docs.py
抓取开源 R 语言统计教程，清洗后保存为 Markdown 到 data/knowledge_base/
数据源：r-statistics.co（MIT-friendly 开源教程，覆盖 T检验/ANOVA/回归等）
"""

import re
import time
import logging
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

OUTPUT_DIR = Path("data/knowledge_base")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# 目标页面：主题 -> URL
TARGETS = [
    {
        "topic": "statistical_tests_t_test_anova",
        "title": "Statistical Tests in R (T-test, ANOVA, Chi-square)",
        "url": "http://r-statistics.co/Statistical-Tests-in-R.html",
    },
    {
        "topic": "linear_regression",
        "title": "Linear Regression in R",
        "url": "http://r-statistics.co/Linear-Regression.html",
    },
    {
        "topic": "logistic_regression",
        "title": "Logistic Regression in R",
        "url": "http://r-statistics.co/Logistic-Regression-With-R.html",
    },
    {
        "topic": "time_series_analysis",
        "title": "Time Series Analysis in R",
        "url": "http://r-statistics.co/Time-Series-Analysis-With-R.html",
    },
]

# ── 工具函数 ──────────────────────────────────────────────────────────────────

def fetch(url: str, retries: int = 3, timeout: int = 20) -> requests.Response | None:
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            log.info("✅ 抓取成功 [%d] %s", resp.status_code, url)
            return resp
        except requests.RequestException as e:
            log.warning("⚠️  第 %d 次抓取失败 (%s): %s", attempt, url, e)
            if attempt < retries:
                time.sleep(2 * attempt)
    log.error("❌ 放弃抓取: %s", url)
    return None


def clean_text(text: str) -> str:
    """多余空行/空格清理"""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def tag_to_markdown(tag) -> str:
    """将单个 BS4 tag 转换为 Markdown 字符串"""
    name = tag.name

    if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(name[1])
        return "#" * level + " " + tag.get_text(strip=True)

    if name == "p":
        return tag.get_text(separator=" ", strip=True)

    if name in ("pre", "code"):
        code = tag.get_text()
        return f"```r\n{code.rstrip()}\n```"

    if name in ("ul", "ol"):
        items = []
        for li in tag.find_all("li", recursive=False):
            items.append("- " + li.get_text(separator=" ", strip=True))
        return "\n".join(items)

    if name == "blockquote":
        lines = tag.get_text(separator="\n", strip=True).splitlines()
        return "\n".join("> " + l for l in lines)

    if name == "table":
        return extract_table(tag)

    # 其余直接取文本
    text = tag.get_text(separator=" ", strip=True)
    return text if text else ""


def extract_table(tag) -> str:
    """将 HTML 表格转为 Markdown 表格"""
    rows = []
    for tr in tag.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all(["th", "td"])]
        rows.append(cells)
    if not rows:
        return ""
    col_count = max(len(r) for r in rows)
    # 对齐列数
    rows = [r + [""] * (col_count - len(r)) for r in rows]
    header = "| " + " | ".join(rows[0]) + " |"
    sep = "| " + " | ".join(["---"] * col_count) + " |"
    body = "\n".join("| " + " | ".join(r) + " |" for r in rows[1:])
    return "\n".join([header, sep, body])


def parse_page(html: str, title: str, url: str) -> str:
    """解析页面，返回 Markdown 字符串"""
    soup = BeautifulSoup(html, "html.parser")

    # r-statistics.co 内容在 .entry-content 或 article 或 #main
    content_el = (
        soup.select_one(".entry-content")
        or soup.select_one("article")
        or soup.select_one("#main")
        or soup.select_one("body")
    )

    if not content_el:
        log.warning("未找到内容容器，使用整个 body")
        content_el = soup.body

    # 移除导航、广告、脚本、样式
    for sel in ["nav", "header", "footer", ".sidebar", ".widget", "script", "style",
                 ".sharedaddy", ".jp-relatedposts", "#respond", ".navigation"]:
        for el in content_el.select(sel):
            el.decompose()

    BLOCK_TAGS = {"h1","h2","h3","h4","h5","h6","p","pre","code","ul","ol",
                  "blockquote","table","div","section"}

    lines = [f"# {title}", f"\n> 来源：{url}\n"]

    for tag in content_el.find_all(BLOCK_TAGS, recursive=True):
        # 跳过嵌套在已处理 tag 内的子元素（避免重复）
        if tag.parent and tag.parent.name in BLOCK_TAGS - {"div","section"}:
            continue
        md = tag_to_markdown(tag)
        if md:
            lines.append(md)

    return clean_text("\n\n".join(lines))


def save(topic: str, content: str) -> Path:
    path = OUTPUT_DIR / f"{topic}.md"
    path.write_text(content, encoding="utf-8")
    log.info("💾 已保存 -> %s (%d 字符)", path, len(content))
    return path


# ── 主流程 ────────────────────────────────────────────────────────────────────

def main():
    log.info("开始抓取，共 %d 个目标页面", len(TARGETS))
    success, failed = 0, 0

    for target in TARGETS:
        log.info("── 处理: %s", target["title"])
        resp = fetch(target["url"])
        if resp is None:
            failed += 1
            continue

        try:
            md = parse_page(resp.text, target["title"], target["url"])
            if len(md) < 500:
                log.warning("内容过短（%d 字符），可能解析有误", len(md))
            save(target["topic"], md)
            success += 1
        except Exception as e:
            log.error("解析/保存失败 [%s]: %s", target["topic"], e, exc_info=True)
            failed += 1

        time.sleep(1.5)  # 礼貌延迟

    log.info("完成：成功 %d / 失败 %d", success, failed)
    if failed:
        log.warning("请检查上方日志中的错误信息")


if __name__ == "__main__":
    main()
