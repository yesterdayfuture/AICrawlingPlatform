"""爬虫地址管理"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..common import success, paginate
from ..database import get_db
from ..models import Crawler, User
from ..schemas import CrawlerCreate, CrawlerUpdate, CrawlerOut
from ._filters import apply_filters
from ._owner import filter_by_owner, ensure_readable, ensure_editable, attach_owner_name
from ..security import get_current_user
from ..services.export_service import build_export_response

router = APIRouter()


def _filtered_query(db: Session, name, description, search_mode, status, start_time, end_time, user: User):
    q = db.query(Crawler)
    q = filter_by_owner(q, Crawler, user)
    return apply_filters(
        q, Crawler.name, Crawler.description, Crawler.status, Crawler.created_at,
        name, description, search_mode, status, start_time, end_time,
    ).order_by(Crawler.id.desc())


def _to_dict(db, i):
    d = CrawlerOut.model_validate(i).model_dump()
    return attach_owner_name(db, i, d)


@router.get("")
def list_crawlers(
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
    page_data["items"] = [_to_dict(db, i) for i in page_data["items"]]
    return success(page_data)


@router.get("/export")
def export_crawlers(
    format: str = Query("xlsx", pattern="^(json|csv|xlsx)$"),
    filename: str = Query("爬虫地址"),
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
        items = db.query(Crawler).filter(Crawler.id.in_(id_list)).order_by(Crawler.id.desc()).all()
        items = [i for i in items if ensure_readable(i, current) is None]
    else:
        q = _filtered_query(db, name, description, search_mode, status, start_time, end_time, current)
        items = q.all()
    rows = [_to_dict(db, i) for i in items]
    return build_export_response(rows, filename=filename, fmt=format)


@router.get("/all")
def list_all_crawlers(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """不分页获取全部（用于任务创建时的多选下拉）"""
    q = db.query(Crawler).filter(Crawler.status == "enabled")
    q = filter_by_owner(q, Crawler, current)
    items = q.order_by(Crawler.id.desc()).all()
    return success([{"id": i.id, "name": i.name, "url": i.url, "method": i.method} for i in items])


@router.get("/{crawler_id}")
def get_crawler(
    crawler_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(Crawler).filter(Crawler.id == crawler_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="爬虫不存在")
    ensure_readable(item, current)
    return success(_to_dict(db, item))


@router.post("")
def create_crawler(
    payload: CrawlerCreate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = Crawler(**payload.model_dump(), owner_id=current.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return success(_to_dict(db, item), msg="创建成功")


@router.put("/{crawler_id}")
def update_crawler(
    crawler_id: int,
    payload: CrawlerUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(Crawler).filter(Crawler.id == crawler_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="爬虫不存在")
    ensure_editable(item, current)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return success(_to_dict(db, item), msg="更新成功")


@router.delete("/{crawler_id}")
def delete_crawler(
    crawler_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(Crawler).filter(Crawler.id == crawler_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="爬虫不存在")
    ensure_editable(item, current)
    db.delete(item)
    db.commit()
    return success(msg="删除成功")
