"""按当前用户做数据可见性过滤"""
from sqlalchemy.orm import Query
from sqlalchemy import or_

from ..models import User
from ..security import can_access, can_modify


def filter_by_owner(q: Query, model, user: User) -> Query:
    """对列表查询应用可见性过滤：管理员全部可见，普通用户只能看自己 + 公开数据"""
    if user.role == "admin":
        return q
    return q.filter(or_(model.owner_id == user.id, model.is_public.is_(True)))


def ensure_readable(item, user: User):
    if not can_access(item, user):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="无权访问该数据")


def ensure_editable(item, user: User):
    if not can_modify(item, user):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="无权修改该数据")


def attach_owner_name(db, item, out_dict: dict) -> dict:
    """为 Out schema 补充 owner_name"""
    owner_id = getattr(item, "owner_id", None)
    if owner_id:
        owner = db.query(User).filter(User.id == owner_id).first()
        out_dict["owner_name"] = owner.nickname or owner.username if owner else ""
    else:
        out_dict["owner_name"] = ""
    return out_dict
