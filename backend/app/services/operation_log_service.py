"""操作日志服务：路径推断 module/action、写日志"""
import re
import json
from typing import Optional

from fastapi import Request

from ..database import SessionLocal
from ..models import OperationLog
from ..security import decode_token


# (method, path_regex, module, action) 映射表
# 只记录写操作和关键读操作；GET 列表默认不记录
_PATH_RULES = [
    # 认证
    ("POST", r"^/api/auth/login$", "认证", "登录"),
    ("PUT",  r"^/api/auth/me$", "认证", "修改个人资料"),
    ("PUT",  r"^/api/auth/password$", "认证", "修改密码"),
    # 用户管理
    ("POST",   r"^/api/users$", "用户管理", "创建用户"),
    ("PUT",    r"^/api/users/\d+$", "用户管理", "更新用户"),
    ("DELETE", r"^/api/users/\d+$", "用户管理", "删除用户"),
    ("PUT",    r"^/api/users/\d+/toggle-status$", "用户管理", "切换用户状态"),
    # 爬虫地址
    ("POST",   r"^/api/crawlers$", "爬虫地址", "创建爬虫"),
    ("PUT",    r"^/api/crawlers/\d+$", "爬虫地址", "更新爬虫"),
    ("DELETE", r"^/api/crawlers/\d+$", "爬虫地址", "删除爬虫"),
    # 大模型
    ("POST",   r"^/api/models$", "大模型", "创建模型"),
    ("PUT",    r"^/api/models/\d+$", "大模型", "更新模型"),
    ("DELETE", r"^/api/models/\d+$", "大模型", "删除模型"),
    # 提示词
    ("POST",   r"^/api/prompts$", "提示词", "创建提示词"),
    ("PUT",    r"^/api/prompts/\d+$", "提示词", "更新提示词"),
    ("DELETE", r"^/api/prompts/\d+$", "提示词", "删除提示词"),
    # 任务中心
    ("POST",   r"^/api/tasks$", "任务中心", "创建任务"),
    ("PUT",    r"^/api/tasks/\d+$", "任务中心", "更新任务"),
    ("DELETE", r"^/api/tasks/\d+$", "任务中心", "删除任务"),
    ("POST",   r"^/api/tasks/\d+/run$", "任务中心", "执行任务"),
    ("POST",   r"^/api/tasks/\d+/schedule/start$", "任务中心", "启动定时"),
    ("POST",   r"^/api/tasks/\d+/schedule/pause$", "任务中心", "暂停定时"),
    ("POST",   r"^/api/tasks/\d+/schedule/stop$", "任务中心", "停止定时"),
    # 任务结果
    ("PUT",    r"^/api/task-results/\d+$", "任务结果", "更新任务结果"),
    ("DELETE", r"^/api/task-results/\d+$", "任务结果", "删除任务结果"),
    ("POST",   r"^/api/task-results/\d+/parse$", "解析结果", "发起解析"),
    # 解析结果
    ("POST",   r"^/api/parse-results$", "解析结果", "创建解析结果"),
    ("PUT",    r"^/api/parse-results/\d+$", "解析结果", "更新解析结果"),
    ("DELETE", r"^/api/parse-results/\d+$", "解析结果", "删除解析结果"),
]

# 预编译缓存：(method, compiled_pattern, module, action)
_COMPILED = [(m, re.compile(p), mod, act) for (m, p, mod, act) in _PATH_RULES]


def resolve_module_action(method: str, path: str) -> tuple:
    """根据 HTTP 方法和路径推断 (module, action)，未匹配返回 ("", "")"""
    for meth, compiled, module, action in _COMPILED:
        if meth == method and compiled.match(path):
            return module, action
    return "", ""


# 敏感字段名（小写匹配）
_SENSITIVE_KEYS = {"password", "new_password", "old_password", "api_key", "token", "secret"}


def _mask_sensitive(data: dict) -> dict:
    """脱敏敏感字段"""
    if not isinstance(data, dict):
        return data
    masked = {}
    for k, v in data.items():
        if k.lower() in _SENSITIVE_KEYS:
            masked[k] = "***"
        else:
            masked[k] = v
    return masked


def write_log(
    user_id: Optional[int],
    username: str,
    module: str,
    action: str,
    method: str,
    path: str,
    params: str = "",
    status: str = "success",
    status_code: int = 200,
    ip: str = "",
    user_agent: str = "",
    error_msg: str = "",
    duration_ms: int = 0,
) -> None:
    """同步写入一条操作日志（用独立 db session，不影响业务事务）"""
    try:
        db = SessionLocal()
        try:
            log = OperationLog(
                user_id=user_id,
                username=username or "",
                module=module or "",
                action=action or "",
                method=method or "",
                path=path or "",
                params=params or "",
                status=status or "success",
                status_code=status_code or 0,
                ip=(ip or "")[:64],
                user_agent=(user_agent or "")[:256],
                error_msg=error_msg or "",
                duration_ms=duration_ms or 0,
            )
            db.add(log)
            db.commit()
        finally:
            db.close()
    except Exception:
        # 日志写入失败不应影响业务流程
        pass


def log_from_request(
    request: Request,
    status_code: int,
    error_msg: str,
    duration_ms: int,
    user_id_override: Optional[int] = None,
    username_override: str = "",
) -> None:
    """从 FastAPI Request 提取信息并写日志

    - 默认从 Authorization 头解析 token 拿 user_id/username
    - 可通过 user_id_override / username_override 显式覆盖（用于登录场景）
    """
    method = request.method
    path = request.url.path
    module, action = resolve_module_action(method, path)
    if not module:
        return  # 未匹配的路径不记录

    user_id = user_id_override
    username = username_override
    if user_id is None:
        auth = request.headers.get("authorization") or request.headers.get("Authorization") or ""
        if auth.startswith("Bearer "):
            payload = decode_token(auth[7:])
            if payload:
                user_id = payload.get("uid")
                username = payload.get("username", "") or ""

    # 仅记录 query 参数（body 已被路由消费，无法安全读取）
    params_dict = {}
    for k, v in request.query_params.items():
        params_dict[k] = v
    params = json.dumps(_mask_sensitive(params_dict), ensure_ascii=False) if params_dict else ""

    status = "success" if 200 <= status_code < 400 else "failed"
    write_log(
        user_id=user_id,
        username=username,
        module=module,
        action=action,
        method=method,
        path=path,
        params=params,
        status=status,
        status_code=status_code,
        ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        error_msg=error_msg,
        duration_ms=duration_ms,
    )
