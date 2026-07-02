"""认证路由：登录、登出、获取当前用户、修改个人信息、修改密码"""
import time
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..common import success
from ..database import get_db
from ..models import User
from ..tz import now_cst
from ..schemas import (
    LoginRequest, LoginResponse, UserOut,
    UserSelfUpdate, ChangePasswordRequest,
)
from ..security import (
    hash_password, verify_password, create_access_token,
    get_current_user,
)
from ..services.operation_log_service import write_log

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    start = time.time()
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        # 登录失败：记录日志（用户名已知，user_id 可能未知）
        write_log(
            user_id=user.id if user else None,
            username=payload.username,
            module="认证", action="登录",
            method="POST", path="/api/auth/login",
            status="failed", status_code=401,
            ip=request.client.host if request.client else "",
            user_agent=request.headers.get("user-agent", ""),
            error_msg="用户名或密码错误",
            duration_ms=int((time.time() - start) * 1000),
        )
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        write_log(
            user_id=user.id,
            username=user.username,
            module="认证", action="登录",
            method="POST", path="/api/auth/login",
            status="failed", status_code=403,
            ip=request.client.host if request.client else "",
            user_agent=request.headers.get("user-agent", ""),
            error_msg="账户已被禁用",
            duration_ms=int((time.time() - start) * 1000),
        )
        raise HTTPException(status_code=403, detail="账户已被禁用，请联系管理员")
    user.last_login_at = now_cst()
    db.commit()
    token = create_access_token(user.id, user.username, user.role)
    write_log(
        user_id=user.id,
        username=user.username,
        module="认证", action="登录",
        method="POST", path="/api/auth/login",
        status="success", status_code=200,
        ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        duration_ms=int((time.time() - start) * 1000),
    )
    return {"token": token, "user": UserOut.model_validate(user).model_dump()}


@router.get("/me")
def get_me(current: User = Depends(get_current_user)):
    return success(UserOut.model_validate(current).model_dump())


@router.put("/me")
def update_me(
    payload: UserSelfUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(current, k, v)
    db.commit()
    db.refresh(current)
    return success(UserOut.model_validate(current).model_dump(), msg="资料已更新")


@router.put("/password")
def change_password(
    payload: ChangePasswordRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.old_password, current.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码长度不能少于 6 位")
    current.password_hash = hash_password(payload.new_password)
    db.commit()
    return success(msg="密码已修改")
