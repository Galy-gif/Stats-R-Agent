"""
app/api/routes/feedback.py
POST /api/feedback —— 接收用户评价，追加写入 feedback_logs.jsonl
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

LOG_FILE = Path("feedback_logs.jsonl")


class FeedbackRequest(BaseModel):
    user_query: str = Field(..., min_length=1, max_length=2000)
    agent_response: str = Field(..., min_length=1)
    rating: int = Field(..., description="1 = 有用，-1 = 无用")

    def model_post_init(self, __context):
        if self.rating not in (1, -1):
            raise ValueError("rating 只能为 1 或 -1")


@router.post("")
async def feedback(req: FeedbackRequest):
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rating": req.rating,
        "user_query": req.user_query,
        "agent_response": req.agent_response[:500],  # 截断，避免日志过大
    }
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        log.info("反馈已记录: rating=%d query=%s", req.rating, req.user_query[:40])
    except Exception as e:
        log.error("写入反馈日志失败: %s", e)

    return {"status": "ok"}
