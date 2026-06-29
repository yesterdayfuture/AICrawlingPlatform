"""任务执行结果管理"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..common import success, paginate
from ..database import get_db
from ..models import TaskResult, Task, User
from ..schemas import (
    TaskResultOut, TaskResultDetailOut, ParseRequest, TaskResultItemOut,
)
from ._filters import apply_filters
from ._owner import filter_by_owner, ensure_readable, ensure_editable, attach_owner_name
from ..security import get_current_user
from ..services.llm_service import parse_task_result
from ..services.export_service import build_export_response

router = APIRouter()


def _to_out(db: Session, r: TaskResult) -> dict:
    out = TaskResultOut.model_validate(r).model_dump()
    out["task_name"] = r.task.name if r.task else ""
    out["item_count"] = len(r.items)
    return attach_owner_name(db, r, out)


def _filtered_query(db: Session, name, description, search_mode, status, start_time, end_time, task_id, user: User):
    q = db.query(TaskResult)
    q = filter_by_owner(q, TaskResult, user)
    q = apply_filters(
        q, TaskResult.name, TaskResult.description, TaskResult.status, TaskResult.created_at,
        name, description, search_mode, status, start_time, end_time,
    )
    if task_id:
        q = q.filter(TaskResult.task_id == task_id)
    return q.order_by(TaskResult.id.desc())


@router.get("")
def list_results(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=200),
    name: str = Query(None),
    description: str = Query(None),
    search_mode: str = Query("fuzzy", pattern="^(fuzzy|exact)$"),
    status: str = Query(None),
    task_id: int = Query(None),
    start_time: str = Query(None),
    end_time: str = Query(None),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _filtered_query(db, name, description, search_mode, status, start_time, end_time, task_id, current)
    page_data = paginate(q, page, page_size)
    page_data["items"] = [_to_out(db, i) for i in page_data["items"]]
    return success(page_data)


@router.get("/export")
def export_results(
    format: str = Query("xlsx", pattern="^(json|csv|xlsx)$"),
    filename: str = Query("任务结果"),
    name: str = Query(None),
    description: str = Query(None),
    search_mode: str = Query("fuzzy", pattern="^(fuzzy|exact)$"),
    status: str = Query(None),
    task_id: int = Query(None),
    start_time: str = Query(None),
    end_time: str = Query(None),
    ids: str = Query(None, description="逗号分隔的 ID 列表，多选导出时使用"),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if ids:
        id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
        items = db.query(TaskResult).filter(TaskResult.id.in_(id_list)).order_by(TaskResult.id.desc()).all()
        items = [i for i in items if ensure_readable(i, current) is None]
    else:
        items = _filtered_query(db, name, description, search_mode, status, start_time, end_time, task_id, current).all()
    rows = []
    for r in items:
        d = _to_out(db, r)
        if r.items:
            for it in r.items:
                row = {**d}
                row["item_crawler"] = it.crawler_name
                row["item_url"] = it.url
                row["item_method"] = it.method
                row["item_status_code"] = it.status_code
                row["item_success"] = it.success
                row["item_error"] = it.error_message
                row["item_duration"] = it.duration
                row["item_content_preview"] = (it.content or "")[:500]
                rows.append(row)
        else:
            rows.append(d)
    return build_export_response(rows, filename=filename, fmt=format)


@router.get("/{result_id}")
def get_result(
    result_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(TaskResult).filter(TaskResult.id == result_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="任务结果不存在")
    ensure_readable(item, current)
    out = TaskResultDetailOut.model_validate(item).model_dump()
    out["task_name"] = item.task.name if item.task else ""
    out["item_count"] = len(item.items)
    out["items"] = [TaskResultItemOut.model_validate(i).model_dump() for i in item.items]
    out = attach_owner_name(db, item, out)
    return success(out)


@router.put("/{result_id}")
def update_result(
    result_id: int,
    payload: dict,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(TaskResult).filter(TaskResult.id == result_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="任务结果不存在")
    ensure_editable(item, current)
    for k in ("name", "description", "status", "is_public"):
        if k in payload:
            setattr(item, k, payload[k])
    db.commit()
    db.refresh(item)
    return success(_to_out(db, item), msg="更新成功")


@router.delete("/{result_id}")
def delete_result(
    result_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(TaskResult).filter(TaskResult.id == result_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="任务结果不存在")
    ensure_editable(item, current)
    db.delete(item)
    db.commit()
    return success(msg="删除成功")


@router.post("/{result_id}/parse")
def parse_result(
    result_id: int,
    payload: ParseRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """对任务结果发起解析"""
    if result_id != payload.task_result_id:
        raise HTTPException(status_code=400, detail="结果ID不一致")
    item = db.query(TaskResult).filter(TaskResult.id == result_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="任务结果不存在")
    ensure_readable(item, current)
    try:
        parse = parse_task_result(
            db,
            task_result_id=result_id,
            model_id=payload.model_id,
            prompt_id=payload.prompt_id,
            name=payload.name,
            description=payload.description,
            item_ids=payload.item_ids,
            owner_id=current.id,
            extract_apis_flag=payload.extract_apis,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return success({"parse_id": parse.id, "status": parse.status}, msg="解析完成")
