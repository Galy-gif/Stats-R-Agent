# Stats-R-Agent

一个基于 RAG + LangGraph Agent 的统计学与 R 语言问答系统。

用户输入统计学问题，Agent 优先从本地知识库中检索相关内容，再结合 Gemini 大模型生成包含**原理 + R 代码 + 参数解读**的结构化回答。内置统计学护栏机制，确保分析前提假设得到确认，并支持用户对每条回复进行评价。

## 核心特性

- **RAG 检索增强**：本地 ChromaDB + sentence-transformers，无需 Embedding API
- **统计学护栏**：分析请求必须先确认前提假设，才会生成 R 代码
- **多轮追问**：完整的对话历史传递，Agent 能感知上下文
- **用户反馈**：每条回复可点击 👍 / 👎 评价，结果持久化到本地日志

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + Vite + Axios |
| 后端 | Python 3 + FastAPI + Uvicorn |
| Agent | LangGraph ReAct Agent + Gemini 2.5-flash |
| RAG | LangChain + ChromaDB + sentence-transformers |
| Embedding | `all-MiniLM-L6-v2`（本地，无需 API） |

## 项目结构

```
Stats-R-Agent/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI 入口
│   │   ├── core/config.py           # 配置（模型名、路径等）
│   │   ├── api/routes/
│   │   │   ├── chat.py              # POST /api/chat
│   │   │   └── feedback.py          # POST /api/feedback
│   │   ├── agents/stats_agent.py    # LangGraph ReAct Agent + 护栏逻辑
│   │   └── rag/retriever.py         # ChromaDB 检索封装
│   ├── requirements.txt
│   ├── feedback_logs.jsonl          # 用户反馈日志（自动生成）
│   └── .env                         # GOOGLE_API_KEY（不提交）
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api/chat.js              # axios 封装（chat + feedback）
│   │   └── components/
│   │       ├── ChatWindow.jsx       # 聊天 UI + 评价按钮
│   │       └── ChatWindow.css
│   ├── package.json
│   └── vite.config.js               # /api 代理到 :8000
├── data/knowledge_base/             # 抓取的统计学 Markdown 文档
├── fetch_real_docs.py               # 知识库爬虫脚本
└── build_vector_db.py               # 向量库构建脚本
```

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/Galy-gif/Stats-R-Agent.git
cd Stats-R-Agent
```

### 2. 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

创建 `.env` 文件并填入 Gemini API Key：

```
GOOGLE_API_KEY=AIza...
```

### 3. 构建向量知识库

首次运行前需要构建 ChromaDB（使用本地 embedding，无需额外 API）：

```bash
cd ..  # 回到项目根目录
python build_vector_db.py
# 输出：数据库构建成功，共存入 378 个向量
```

### 4. 启动后端

```bash
cd backend
PYTHONPATH=. .venv/bin/uvicorn app.main:app --reload
# 运行在 http://localhost:8000
```

### 5. 前端

```bash
cd frontend
npm install
npm run dev
# 运行在 http://localhost:5173
```

打开浏览器访问 http://localhost:5173 即可开始对话。

## 护栏机制说明

当用户提出统计分析需求（如 T 检验、回归分析等）时，Agent 强制执行以下流程：

```
用户请求分析
    ↓
检索该方法的前提假设条件
    ↓
用户是否已确认前提？
   ├── 否 → 向用户发起追问，等待确认（不输出任何代码）
   └── 是 → 输出完整 R 代码 + 结果解读
```

对于概念解释、方法选择等非分析类问题，直接回答，不走护栏流程。

## 用户反馈

每条 Agent 回复的右下角提供 👍 / 👎 评价按钮：

- 点击后按钮高亮（绿色/红色），同一条消息只可评价一次
- 评价结果异步发送至后端，不影响对话体验
- 后端追加写入 `backend/feedback_logs.jsonl`，每行一条记录

日志格式示例：

```jsonl
{"timestamp": "2026-03-19T13:30:47+00:00", "rating": 1, "user_query": "帮我做T检验", "agent_response": "请确认前提假设..."}
{"timestamp": "2026-03-19T13:31:12+00:00", "rating": -1, "user_query": "做线性回归分析", "agent_response": "您的数据是否满足..."}
```

分析日志：

```bash
# 查看所有反馈
cat backend/feedback_logs.jsonl | python3 -c "
import sys, json
for line in sys.stdin:
    r = json.loads(line)
    print(r['timestamp'], '👍' if r['rating']==1 else '👎', r['user_query'][:40])
"
```

## 知识库来源

知识库数据抓取自 [r-statistics.co](http://r-statistics.co/)，涵盖：

- T 检验、卡方检验、ANOVA
- 线性回归（含诊断、变量选择）
- 逻辑回归
- 时间序列分析

如需更新或扩充知识库，重新运行抓取和构建脚本：

```bash
python fetch_real_docs.py
python build_vector_db.py
```

## API

### `POST /api/chat`

```json
// 请求
{
  "question": "帮我做一个T检验",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}

// 响应
{
  "question": "帮我做一个T检验",
  "answer": "在进行 T 检验之前，请确认以下前提假设..."
}
```

### `POST /api/feedback`

```json
// 请求
{
  "user_query": "帮我做一个T检验",
  "agent_response": "在进行 T 检验之前...",
  "rating": 1
}

// 响应
{ "status": "ok" }
```

### `GET /health`

```json
{ "status": "ok" }
```
