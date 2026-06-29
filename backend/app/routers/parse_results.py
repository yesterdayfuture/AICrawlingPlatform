"""解析结果管理"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..common import success, paginate
from ..database import get_db
from ..models import ParseResult, LLMModel, Prompt, TaskResult, User
from ..schemas import ParseResultOut, ParseResultDetailOut, ParseResultUpdate, ParseResultCreate
from ._filters import apply_filters
from ._owner import filter_by_owner, ensure_readable, ensure_editable, attach_owner_name
from ..security import get_current_user
from ..services.export_service import build_export_response

router = APIRouter()


def _parse_extracted_apis(raw: str) -> list:
    """把 extracted_apis 字段从 JSON 字符串解析为 list，失败返回空列表"""
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, ValueError):
        return []


def _to_dict(p: ParseResult, db: Session) -> dict:
    out = ParseResultOut.model_validate(p).model_dump()
    out["task_result_name"] = p.task_result.name if p.task_result else ""
    out["model_name"] = p.model.name if p.model else ""
    out["prompt_name"] = ""
    if p.prompt_id:
        pr = db.query(Prompt).filter(Prompt.id == p.prompt_id).first()
        if pr:
            out["prompt_name"] = pr.name
    return attach_owner_name(db, p, out)


def _filtered_query(db: Session, name, description, search_mode, status, start_time, end_time, task_result_id, user: User):
    q = db.query(ParseResult)
    q = filter_by_owner(q, ParseResult, user)
    q = apply_filters(
        q, ParseResult.name, ParseResult.description, ParseResult.status, ParseResult.created_at,
        name, description, search_mode, status, start_time, end_time,
    )
    if task_result_id:
        q = q.filter(ParseResult.task_result_id == task_result_id)
    return q.order_by(ParseResult.id.desc())


@router.get("")
def list_parse_results(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=200),
    name: str = Query(None),
    description: str = Query(None),
    search_mode: str = Query("fuzzy", pattern="^(fuzzy|exact)$"),
    status: str = Query(None),
    task_result_id: int = Query(None),
    start_time: str = Query(None),
    end_time: str = Query(None),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _filtered_query(db, name, description, search_mode, status, start_time, end_time, task_result_id, current)
    page_data = paginate(q, page, page_size)
    page_data["items"] = [_to_dict(p, db) for p in page_data["items"]]
    return success(page_data)


@router.get("/export")
def export_parse_results(
    format: str = Query("xlsx", pattern="^(json|csv|xlsx)$"),
    filename: str = Query("解析结果"),
    name: str = Query(None),
    description: str = Query(None),
    search_mode: str = Query("fuzzy", pattern="^(fuzzy|exact)$"),
    status: str = Query(None),
    task_result_id: int = Query(None),
    start_time: str = Query(None),
    end_time: str = Query(None),
    ids: str = Query(None, description="逗号分隔的 ID 列表，多选导出时使用"),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if ids:
        id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
        items = db.query(ParseResult).filter(ParseResult.id.in_(id_list)).order_by(ParseResult.id.desc()).all()
        items = [i for i in items if ensure_readable(i, current) is None]
    else:
        items = _filtered_query(db, name, description, search_mode, status, start_time, end_time, task_result_id, current).all()
    rows = [_to_dict(p, db) for p in items]
    return build_export_response(rows, filename=filename, fmt=format)


@router.get("/{parse_id}")
def get_parse_result(
    parse_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(ParseResult).filter(ParseResult.id == parse_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="解析结果不存在")
    ensure_readable(item, current)
    out = ParseResultDetailOut.model_validate(item).model_dump()
    out["task_result_name"] = item.task_result.name if item.task_result else ""
    out["model_name"] = item.model.name if item.model else ""
    out["prompt_name"] = ""
    if item.prompt_id:
        pr = db.query(Prompt).filter(Prompt.id == item.prompt_id).first()
        if pr:
            out["prompt_name"] = pr.name
    out = attach_owner_name(db, item, out)
    # 将 extracted_apis JSON 字符串解析为数组返回，方便前端直接渲染
    out["extracted_apis"] = _parse_extracted_apis(item.extracted_apis or "")
    return success(out)


@router.post("")
def create_parse_result(
    payload: ParseResultCreate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = ParseResult(**payload.model_dump(), owner_id=current.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return success(_to_dict(item, db), msg="创建成功")


@router.put("/{parse_id}")
def update_parse_result(
    parse_id: int,
    payload: ParseResultUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(ParseResult).filter(ParseResult.id == parse_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="解析结果不存在")
    ensure_editable(item, current)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return success(_to_dict(item, db), msg="更新成功")


@router.delete("/{parse_id}")
def delete_parse_result(
    parse_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(ParseResult).filter(ParseResult.id == parse_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="解析结果不存在")
    ensure_editable(item, current)
    db.delete(item)
    db.commit()
    return success(msg="删除成功")
