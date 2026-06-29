"""通用查询过滤：名称/描述、模糊/精准、状态、时间范围"""
from typing import Optional
from sqlalchemy.orm import Query
from sqlalchemy import Column

from ..common import parse_time_range


def apply_filters(
    query: Query,
    name_col: Column,
    desc_col: Column,
    status_col: Column,
    time_col: Column,
    name: Optional[str],
    description: Optional[str],
    search_mode: str,
    status: Optional[str],
    start_time: Optional[str],
    end_time: Optional[str],
) -> Query:
    """统一应用查询过滤条件"""
    if name:
        if search_mode == "exact":
            query = query.filter(name_col == name)
        else:
            query = query.filter(name_col.like(f"%{name}%"))
    if description:
        if search_mode == "exact":
            query = query.filter(desc_col == description)
        else:
            query = query.filter(desc_col.like(f"%{description}%"))
    if status:
        query = query.filter(status_col == status)
    s, e = parse_time_range(start_time, end_time)
    if s:
        query = query.filter(time_col >= s)
    if e:
        query = query.filter(time_col <= e)
    return query
