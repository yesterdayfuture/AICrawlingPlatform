"""FastAPI 应用入口"""
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db, SessionLocal
from .models import User
from .security import hash_password
from .services.operation_log_service import resolve_module_action, log_from_request
from .services.scheduler_service import start_scheduler, shutdown_scheduler


def seed_admin():
    """首次启动时创建默认管理员账户"""
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == settings.default_admin_username).first()
        if not admin:
            admin = User(
                username=settings.default_admin_username,
                nickname="系统管理员",
                email="admin@crawler.local",
                role="admin",
                is_active=True,
                password_hash=hash_password(settings.default_admin_password),
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_admin()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="智能爬取系统 API",
    description="支持爬虫管理、大模型解析、任务调度的智能爬取系统",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 操作日志中间件：记录写操作（POST/PUT/DELETE），登录路由由 auth.py 内部手动记录
@app.middleware("http")
async def operation_log_middleware(request: Request, call_next):
    method = request.method
    path = request.url.path
    # 跳过 GET、健康检查、OpenAPI 文档、登录（登录由路由内部手动记录以拿到用户名）
    if method == "GET" or path in ("/api/health", "/docs", "/openapi.json", "/redoc") or path == "/api/auth/login":
        return await call_next(request)
    # 仅记录在路径映射表中的请求
    if not resolve_module_action(method, path)[0]:
        return await call_next(request)

    start = time.time()
    status_code = 200
    error_msg = ""
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception as e:
        status_code = 500
        error_msg = f"{type(e).__name__}: {str(e)}"
        raise
    finally:
        duration_ms = int((time.time() - start) * 1000)
        log_from_request(request, status_code, error_msg, duration_ms)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# 注册路由
from .routers import (  # noqa: E402
    dashboard, crawlers, models, prompts, tasks, task_results, parse_results,
    auth, users, operation_logs,
)

app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/users", tags=["用户管理"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["总览"])
app.include_router(crawlers.router, prefix="/api/crawlers", tags=["爬虫地址"])
app.include_router(models.router, prefix="/api/models", tags=["大模型"])
app.include_router(prompts.router, prefix="/api/prompts", tags=["提示词"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["任务中心"])
app.include_router(task_results.router, prefix="/api/task-results", tags=["任务结果"])
app.include_router(parse_results.router, prefix="/api/parse-results", tags=["解析结果"])
app.include_router(operation_logs.router, prefix="/api/operation-logs", tags=["操作日志"])

