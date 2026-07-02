"""操作日志管理（仅管理员）"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..common import success, paginate, parse_time_range
from ..database import get_db
from ..models import OperationLog, User
from ..schemas import OperationLogOut
from ..security import require_admin

router = APIRouter()


def _to_dict(log: OperationLog) -> dict:
    out = OperationLogOut.model_validate(log).model_dump()
    # created_at 序列化为 ISO 字符串
    if log.created_at:
        out["created_at"] = log.created_at.strftime("%Y-%m-%d %H:%M:%S")
    return out


@router.get("")
def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=200),
    keyword: str = Query(None, description="关键词，搜索 username/module/action/path"),
    search_mode: str = Query("fuzzy", pattern="^(fuzzy|exact)$"),
    username: str = Query(None, description="按用户名筛选"),
    module: str = Query(None, description="按模块筛选"),
    action: str = Query(None, description="按动作筛选"),
    status: str = Query(None, description="success / failed"),
    start_time: str = Query(None),
    end_time: str = Query(None),
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(OperationLog)

    # 关键词：跨字段搜索
    if keyword:
        if search_mode == "exact":
            # 精准匹配：username 或 module 或 action 或 path 中任一字段完全相等
            q = q.filter(or_(
                OperationLog.username == keyword,
                OperationLog.module == keyword,
                OperationLog.action == keyword,
                OperationLog.path == keyword,
            ))
        else:
            # 模糊匹配：四个字段任一包含
            kw = f"%{keyword}%"
            q = q.filter(or_(
                OperationLog.username.like(kw),
                OperationLog.module.like(kw),
                OperationLog.action.like(kw),
                OperationLog.path.like(kw),
            ))

    # 独立字段筛选
    if username:
        if search_mode == "exact":
            q = q.filter(OperationLog.username == username)
        else:
            q = q.filter(OperationLog.username.like(f"%{username}%"))
    if module:
        q = q.filter(OperationLog.module == module)
    if action:
        q = q.filter(OperationLog.action == action)
    if status:
        q = q.filter(OperationLog.status == status)

    s, e = parse_time_range(start_time, end_time)
    if s:
        q = q.filter(OperationLog.created_at >= s)
    if e:
        q = q.filter(OperationLog.created_at <= e)

    q = q.order_by(OperationLog.id.desc())
    page_data = paginate(q, page, page_size)
    page_data["items"] = [_to_dict(l) for l in page_data["items"]]
    return success(page_data)


@router.get("/filters")
def list_log_filters(
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取日志筛选可选项：模块列表、动作列表、用户名列表"""
    modules = [r[0] for r in db.query(OperationLog.module).distinct().all() if r[0]]
    actions = [r[0] for r in db.query(OperationLog.action).distinct().all() if r[0]]
    usernames = [r[0] for r in db.query(OperationLog.username).distinct().all() if r[0]]
    return success({
        "modules": sorted(modules),
        "actions": sorted(actions),
        "usernames": sorted(usernames),
    })


@router.get("/{log_id}")
def get_log(
    log_id: int,
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    log = db.query(OperationLog).filter(OperationLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    return success(_to_dict(log))


@router.delete("/{log_id}")
def delete_log(
    log_id: int,
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    log = db.query(OperationLog).filter(OperationLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    db.delete(log)
    db.commit()
    return success(msg="删除成功")


@router.delete("")
def clear_logs(
    before_days: int = Query(0, ge=0, description="清理多少天前的日志，0 表示清空全部"),
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """批量清理日志：before_days=0 清空全部，>0 仅清理 N 天前"""
    from datetime import timedelta
    from ..tz import now_cst
    q = db.query(OperationLog)
    if before_days > 0:
        cutoff = now_cst() - timedelta(days=before_days)
        q = q.filter(OperationLog.created_at < cutoff)
    count = q.count()
    q.delete(synchronize_session=False)
    db.commit()
    return success({"deleted": count}, msg=f"已清理 {count} 条日志")
