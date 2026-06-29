"""安全工具：密码哈希、JWT 生成与校验、当前用户依赖"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# tokenUrl 仅用于 OpenAPI 文档展示，实际登录走 /api/auth/login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(raw: str) -> str:
    """对明文密码做哈希"""
    return pwd_context.hash(raw or "")


def verify_password(raw: str, hashed: str) -> bool:
    """校验明文密码与哈希是否匹配"""
    if not hashed:
        return False
    try:
        return pwd_context.verify(raw or "", hashed)
    except Exception:
        return False


def create_access_token(user_id: int, username: str, role: str) -> str:
    """签发 JWT"""
    expire = datetime.utcnow() + timedelta(hours=settings.jwt_expire_hours)
    payload = {
        "sub": str(user_id),
        "uid": user_id,
        "username": username,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[dict]:
    """解析 JWT，失败返回 None"""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """从请求头解析当前用户，未登录抛 401"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或登录已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录凭证无效",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("uid")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录凭证无效")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已被禁用")
    return user


def require_admin(current: User = Depends(get_current_user)) -> User:
    """要求当前用户是管理员"""
    if current.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current


def can_access(item, user: User) -> bool:
    """判断用户是否能读取某条数据：管理员 / 自己创建 / 公开数据"""
    if user.role == "admin":
        return True
    if getattr(item, "is_public", False):
        return True
    owner_id = getattr(item, "owner_id", None)
    return owner_id == user.id


def can_modify(item, user: User) -> bool:
    """判断用户是否能修改/删除某条数据：管理员 / 自己创建"""
    if user.role == "admin":
        return True
    owner_id = getattr(item, "owner_id", None)
    return owner_id == user.id
