# Stats-R-Agent

一个基于 RAG + LangGraph Agent 的统计学与 R 语言问答系统。

用户输入统计学问题，Agent 优先从本地知识库中检索相关内容，再结合 Gemini 大模型生成包含**原理 + R 代码 + 参数解读**的结构化回答。

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
│   │   ├── main.py              # FastAPI 入口
│   │   ├── core/config.py       # 配置（模型名、路径等）
│   │   ├── api/routes/chat.py   # POST /api/chat 路由
│   │   ├── agents/stats_agent.py # LangGraph ReAct Agent
│   │   └── rag/retriever.py     # ChromaDB 检索封装
│   ├── requirements.txt
│   └── .env                     # GOOGLE_API_KEY（不提交）
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api/chat.js          # axios 封装
│   │   └── components/ChatWindow.jsx
│   ├── package.json
│   └── vite.config.js           # /api 代理到 :8000
├── data/knowledge_base/         # 抓取的统计学 Markdown 文档
├── fetch_real_docs.py           # 知识库爬虫脚本
└── build_vector_db.py           # 向量库构建脚本
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
{ "question": "什么是 T 检验？" }

// 响应
{
  "question": "什么是 T 检验？",
  "answer": "T 检验是一种用于比较两个样本均值的统计方法..."
}
```

### `GET /health`

```json
{ "status": "ok" }
```
