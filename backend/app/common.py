"""统一响应与分页工具"""
from typing import Any, Optional, List
from datetime import datetime
from fastapi import HTTPException


def success(data: Any = None, msg: str = "success"):
    return {"code": 0, "msg": msg, "data": data}


def fail(msg: str = "error", code: int = -1, data: Any = None):
    return {"code": code, "msg": msg, "data": data}


def paginate(query, page: int = 1, page_size: int = 10):
    """对 SQLAlchemy query 执行分页，返回标准结构"""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 200:
        page_size = 10
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


def parse_time_range(start: Optional[str], end: Optional[str]):
    """解析时间范围参数，返回 datetime 对象"""
    s = None
    e = None
    if start:
        try:
            s = datetime.fromisoformat(start.replace("Z", ""))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"非法的起始时间格式: {start}")
    if end:
        try:
            e = datetime.fromisoformat(end.replace("Z", ""))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"非法的结束时间格式: {end}")
    return s, e
