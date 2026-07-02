"""任务中心"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..common import success, paginate
from ..database import get_db
from ..models import Task, TaskCrawler, Crawler, User
from ..schemas import TaskCreate, TaskUpdate, TaskOut
from ._filters import apply_filters
from ._owner import filter_by_owner, ensure_readable, ensure_editable, attach_owner_name
from ..security import get_current_user
from ..services.crawler_service import run_task
from ..services.export_service import build_export_response
from ..services.scheduler_service import schedule_task, unschedule_task

router = APIRouter()


def _to_out(db: Session, task: Task) -> dict:
    out = TaskOut.model_validate(task).model_dump()
    out["crawler_ids"] = [link.crawler_id for link in task.crawlers]
    out["crawler_names"] = [link.crawler.name for link in task.crawlers if link.crawler]
    return attach_owner_name(db, task, out)


def _filtered_query(db: Session, name, description, search_mode, status, start_time, end_time, user: User):
    q = db.query(Task)
    q = filter_by_owner(q, Task, user)
    return apply_filters(
        q, Task.name, Task.description, Task.status, Task.created_at,
        name, description, search_mode, status, start_time, end_time,
    ).order_by(Task.id.desc())


@router.get("")
def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=200),
    name: str = Query(None),
    description: str = Query(None),
    search_mode: str = Query("fuzzy", pattern="^(fuzzy|exact)$"),
    status: str = Query(None),
    start_time: str = Query(None),
    end_time: str = Query(None),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _filtered_query(db, name, description, search_mode, status, start_time, end_time, current)
    page_data = paginate(q, page, page_size)
    page_data["items"] = [_to_out(db, i) for i in page_data["items"]]
    return success(page_data)


@router.get("/export")
def export_tasks(
    format: str = Query("xlsx", pattern="^(json|csv|xlsx)$"),
    filename: str = Query("任务"),
    name: str = Query(None),
    description: str = Query(None),
    search_mode: str = Query("fuzzy", pattern="^(fuzzy|exact)$"),
    status: str = Query(None),
    start_time: str = Query(None),
    end_time: str = Query(None),
    ids: str = Query(None),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if ids:
        id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
        items = db.query(Task).filter(Task.id.in_(id_list)).order_by(Task.id.desc()).all()
        items = [i for i in items if ensure_readable(i, current) is None]
    else:
        q = _filtered_query(db, name, description, search_mode, status, start_time, end_time, current)
        items = q.all()
    rows = [_to_out(db, i) for i in items]
    return build_export_response(rows, filename=filename, fmt=format)


@router.get("/{task_id}")
def get_task(
    task_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(Task).filter(Task.id == task_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="任务不存在")
    ensure_readable(item, current)
    return success(_to_out(db, item))


@router.post("")
def create_task(
    payload: TaskCreate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude={"crawler_ids"})
    item = Task(**data, owner_id=current.id)
    db.add(item)
    db.flush()
    for cid in payload.crawler_ids:
        crawler = db.query(Crawler).filter(Crawler.id == cid).first()
        if not crawler:
            raise HTTPException(status_code=400, detail=f"爬虫不存在: {cid}")
        from ..security import can_access
        if not can_access(crawler, current):
            raise HTTPException(status_code=403, detail=f"无权使用爬虫: {crawler.name}")
        db.add(TaskCrawler(task_id=item.id, crawler_id=cid))
    db.commit()
    db.refresh(item)
    schedule_task(item)
    return success(_to_out(db, item), msg="创建成功")


@router.put("/{task_id}")
def update_task(
    task_id: int,
    payload: TaskUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(Task).filter(Task.id == task_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="任务不存在")
    ensure_editable(item, current)
    data = payload.model_dump(exclude_unset=True)
    crawler_ids = data.pop("crawler_ids", None)
    for k, v in data.items():
        setattr(item, k, v)
    if crawler_ids is not None:
        db.query(TaskCrawler).filter(TaskCrawler.task_id == task_id).delete()
        for cid in crawler_ids:
            crawler = db.query(Crawler).filter(Crawler.id == cid).first()
            if not crawler:
                raise HTTPException(status_code=400, detail=f"爬虫不存在: {cid}")
            from ..security import can_access
            if not can_access(crawler, current):
                raise HTTPException(status_code=403, detail=f"无权使用爬虫: {crawler.name}")
            db.add(TaskCrawler(task_id=task_id, crawler_id=cid))
    db.commit()
    db.refresh(item)
    schedule_task(item)
    return success(_to_out(db, item), msg="更新成功")


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(Task).filter(Task.id == task_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="任务不存在")
    ensure_editable(item, current)
    db.delete(item)
    db.commit()
    unschedule_task(task_id)
    return success(msg="删除成功")


@router.post("/{task_id}/run")
def run_task_now(
    task_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """立即执行任务"""
    item = db.query(Task).filter(Task.id == task_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="任务不存在")
    ensure_readable(item, current)
    try:
        result = run_task(db, task_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return success({"result_id": result.id, "status": result.status}, msg="执行完成")


@router.post("/{task_id}/schedule/start")
def start_schedule(
    task_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """启动定时：开启调度并按 interval 周期执行"""
    item = db.query(Task).filter(Task.id == task_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="任务不存在")
    ensure_editable(item, current)
    if not item.interval_value or item.interval_value < 1:
        raise HTTPException(status_code=400, detail="请先设置有效的定时间隔")
    item.is_scheduled = True
    item.status = "enabled"
    db.commit()
    db.refresh(item)
    schedule_task(item)
    return success(_to_out(db, item), msg="定时已启动")


@router.post("/{task_id}/schedule/pause")
def pause_schedule(
    task_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """暂停定时：临时停止调度，保留定时配置便于后续恢复"""
    item = db.query(Task).filter(Task.id == task_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="任务不存在")
    ensure_editable(item, current)
    item.status = "disabled"
    db.commit()
    db.refresh(item)
    schedule_task(item)
    return success(_to_out(db, item), msg="定时已暂停")


@router.post("/{task_id}/schedule/stop")
def stop_schedule(
    task_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """停止定时：关闭定时模式，回到手动执行"""
    item = db.query(Task).filter(Task.id == task_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="任务不存在")
    ensure_editable(item, current)
    item.is_scheduled = False
    db.commit()
    db.refresh(item)
    schedule_task(item)
    return success(_to_out(db, item), msg="定时已停止")
