"""
app/api/routes/chat.py
POST /api/chat  —— 接收用户问题，返回 Agent 答案
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.stats_agent import run_agent

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")


class ChatResponse(BaseModel):
    answer: str
    question: str


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    answer = run_agent(req.question)
    if not answer:
        raise HTTPException(status_code=500, detail="Agent 未返回有效答案")
    return ChatResponse(answer=answer, question=req.question)
