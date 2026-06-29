"""总览：统计卡片 + 时间折线图"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from ..common import success, parse_time_range
from ..database import get_db
from ..models import Crawler, LLMModel, Prompt, Task, TaskResult, ParseResult, User
from ..security import get_current_user
from ..services.export_service import build_export_response

router = APIRouter()


def _stats_dict(db: Session, s, e, user: User):
    def _count(model):
        q = db.query(func.count(model.id))
        # 普通用户仅统计自己 + 公开数据
        if user.role != "admin":
            q = q.filter(or_(model.owner_id == user.id, model.is_public.is_(True)))
        if s:
            q = q.filter(model.created_at >= s)
        if e:
            q = q.filter(model.created_at <= e)
        return q.scalar() or 0

    base_q = db.query(func.count(TaskResult.id))
    base_q_p = db.query(func.count(ParseResult.id))
    if user.role != "admin":
        base_q = base_q.filter(or_(TaskResult.owner_id == user.id, TaskResult.is_public.is_(True)))
        base_q_p = base_q_p.filter(or_(ParseResult.owner_id == user.id, ParseResult.is_public.is_(True)))

    return {
        "crawler_count": _count(Crawler),
        "model_count": _count(LLMModel),
        "prompt_count": _count(Prompt),
        "task_count": _count(Task),
        "task_result_count": _count(TaskResult),
        "parse_result_count": _count(ParseResult),
        "task_result_success": base_q.filter(TaskResult.status == "success").scalar() or 0,
        "task_result_failed": base_q.filter(TaskResult.status == "failed").scalar() or 0,
        "parse_result_success": base_q_p.filter(ParseResult.status == "success").scalar() or 0,
        "parse_result_failed": base_q_p.filter(ParseResult.status == "failed").scalar() or 0,
    }


@router.get("/stats")
def stats(
    start_time: str = Query(None),
    end_time: str = Query(None),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """各类信息统计卡片"""
    s, e = parse_time_range(start_time, end_time)
    return success(_stats_dict(db, s, e, current))


@router.get("/export")
def export_stats(
    format: str = Query("xlsx", pattern="^(json|csv|xlsx)$"),
    filename: str = Query("总览统计"),
    start_time: str = Query(None),
    end_time: str = Query(None),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s, e = parse_time_range(start_time, end_time)
    data = _stats_dict(db, s, e, current)
    rows = [{"指标": k, "数量": v} for k, v in data.items()]
    return build_export_response(rows, filename=filename, fmt=format)


@router.get("/trend")
def trend(
    days: int = Query(7, ge=1, le=90),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """按天聚合的折线图数据"""
    end = datetime.utcnow()
    start = end - timedelta(days=days - 1)
    buckets = []
    cur = start
    while cur <= end:
        buckets.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)

    def _series(model):
        rows = db.query(
            func.strftime("%Y-%m-%d", model.created_at).label("d"),
            func.count(model.id).label("c"),
        ).filter(model.created_at >= start, model.created_at <= end)
        if current.role != "admin":
            rows = rows.filter(or_(model.owner_id == current.id, model.is_public.is_(True)))
        rows = rows.group_by("d").all()
        m = {r.d: r.c for r in rows}
        return [m.get(b, 0) for b in buckets]

    return success({
        "dates": buckets,
        "crawlers": _series(Crawler),
        "models": _series(LLMModel),
        "prompts": _series(Prompt),
        "tasks": _series(Task),
        "task_results": _series(TaskResult),
        "parse_results": _series(ParseResult),
    })
