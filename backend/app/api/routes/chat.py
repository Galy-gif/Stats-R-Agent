"""
app/api/routes/chat.py
POST /api/chat  —— 接收用户问题和对话历史，返回 Agent 答案
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.stats_agent import run_agent

router = APIRouter(prefix="/api/chat", tags=["chat"])


class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    history: list[HistoryMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    question: str


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    history = [{"role": m.role, "content": m.content} for m in req.history]
    answer = run_agent(req.question, history=history)
    if not answer:
        raise HTTPException(status_code=500, detail="Agent 未返回有效答案")
    return ChatResponse(answer=answer, question=req.question)
