"""用户管理路由（管理员）"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..common import success, paginate
from ..database import get_db
from ..models import User
from ..schemas import UserCreate, UserUpdate, UserOut
from ..security import hash_password, require_admin

router = APIRouter()


@router.get("")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=200),
    name: str = Query(None),         # 匹配 username 或 nickname
    status: str = Query(None),       # active / disabled
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(User)
    if name:
        kw = f"%{name}%"
        q = q.filter(or_(User.username.like(kw), User.nickname.like(kw), User.email.like(kw)))
    if status == "active":
        q = q.filter(User.is_active.is_(True))
    elif status == "disabled":
        q = q.filter(User.is_active.is_(False))
    q = q.order_by(User.id.asc())
    page_data = paginate(q, page, page_size)
    page_data["items"] = [UserOut.model_validate(u).model_dump() for u in page_data["items"]]
    return success(page_data)


@router.post("")
def create_user(
    payload: UserCreate,
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=payload.username,
        nickname=payload.nickname or payload.username,
        email=payload.email,
        role=payload.role,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return success(UserOut.model_validate(user).model_dump(), msg="创建成功")


@router.put("/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdate,
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    data = payload.model_dump(exclude_unset=True)
    # 单独处理密码重置
    new_pwd = data.pop("password", None)
    for k, v in data.items():
        setattr(user, k, v)
    if new_pwd:
        user.password_hash = hash_password(new_pwd)
    db.commit()
    db.refresh(user)
    return success(UserOut.model_validate(user).model_dump(), msg="更新成功")


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_id == current.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.role == "admin":
        admin_count = db.query(User).filter(User.role == "admin", User.is_active.is_(True)).count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="系统至少保留一个管理员账户")
    db.delete(user)
    db.commit()
    return success(msg="删除成功")


@router.put("/{user_id}/toggle-status")
def toggle_user_status(
    user_id: int,
    current: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_id == current.id:
        raise HTTPException(status_code=400, detail="不能禁用自己")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.role == "admin" and not user.is_active:
        raise HTTPException(status_code=400, detail="不能禁用管理员账户")
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return success(UserOut.model_validate(user).model_dump(), msg="状态已更新")
