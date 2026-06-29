"""数据库模型定义"""
import json
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float
)
from sqlalchemy.orm import relationship
from .database import Base


class TimestampMixin:
    """通用时间戳字段"""
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base, TimestampMixin):
    """用户"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False, default="")
    nickname = Column(String(64), default="")
    email = Column(String(128), default="")
    role = Column(String(20), default="user")        # admin / user
    is_active = Column(Boolean, default=True)        # 账户启用状态
    last_login_at = Column(DateTime, nullable=True)


class Crawler(Base, TimestampMixin):
    """爬虫地址"""
    __tablename__ = "crawlers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, index=True)
    description = Column(Text, default="")
    url = Column(String(512), nullable=False)
    method = Column(String(10), default="GET")  # GET / POST
    headers = Column(JSON, default=dict)        # 请求头
    params = Column(JSON, default=dict)         # GET 查询参数 / POST 表单参数
    body = Column(JSON, default=dict)           # POST JSON body
    status = Column(String(20), default="enabled")  # enabled / disabled
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    is_public = Column(Boolean, default=False)  # 管理员设置公开数据

    task_links = relationship("TaskCrawler", back_populates="crawler", cascade="all, delete-orphan")
    result_items = relationship("TaskResultItem", back_populates="crawler", cascade="all, delete-orphan")


class LLMModel(Base, TimestampMixin):
    """大模型信息"""
    __tablename__ = "llm_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, index=True)
    description = Column(Text, default="")
    provider = Column(String(64), default="openai")      # 兼容 openai 协议的服务商
    base_url = Column(String(256), default="")            # 例如 https://api.openai.com/v1
    api_key = Column(String(256), default="")
    model_name = Column(String(128), default="gpt-3.5-turbo")  # 实际模型名
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2048)
    status = Column(String(20), default="enabled")
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    is_public = Column(Boolean, default=False)

    parse_results = relationship("ParseResult", back_populates="model")


class Prompt(Base, TimestampMixin):
    """提示词信息"""
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, index=True)
    description = Column(Text, default="")
    system_prompt = Column(Text, default="")
    user_prompt = Column(Text, default="")
    status = Column(String(20), default="enabled")
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    is_public = Column(Boolean, default=False)


class Task(Base, TimestampMixin):
    """任务"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, index=True)
    description = Column(Text, default="")
    status = Column(String(20), default="enabled")
    is_scheduled = Column(Boolean, default=False)     # 是否定时
    interval_value = Column(Integer, default=0)       # 间隔数值
    interval_unit = Column(String(10), default="min")  # min/hour/day/month
    last_run_at = Column(DateTime, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    is_public = Column(Boolean, default=False)

    crawlers = relationship("TaskCrawler", back_populates="task", cascade="all, delete-orphan")
    results = relationship("TaskResult", back_populates="task", cascade="all, delete-orphan")


class TaskCrawler(Base):
    """任务与爬虫的多对多关系"""
    __tablename__ = "task_crawlers"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    crawler_id = Column(Integer, ForeignKey("crawlers.id", ondelete="CASCADE"), index=True)

    task = relationship("Task", back_populates="crawlers")
    crawler = relationship("Crawler", back_populates="task_links")


class TaskResult(Base, TimestampMixin):
    """任务执行结果"""
    __tablename__ = "task_results"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, index=True)
    description = Column(Text, default="")
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(20), default="success")  # success / failed / partial
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    duration = Column(Float, default=0.0)  # 秒
    error_message = Column(Text, default="")
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    is_public = Column(Boolean, default=False)

    task = relationship("Task", back_populates="results")
    items = relationship("TaskResultItem", back_populates="result", cascade="all, delete-orphan")
    parse_results = relationship("ParseResult", back_populates="task_result", cascade="all, delete-orphan")


class TaskResultItem(Base):
    """单个爬虫地址的抓取结果"""
    __tablename__ = "task_result_items"

    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(Integer, ForeignKey("task_results.id", ondelete="CASCADE"), index=True)
    crawler_id = Column(Integer, ForeignKey("crawlers.id", ondelete="SET NULL"), nullable=True)
    crawler_name = Column(String(128), default="")
    url = Column(String(512), default="")
    method = Column(String(10), default="GET")
    status_code = Column(Integer, nullable=True)
    success = Column(Boolean, default=True)
    content = Column(Text, default="")
    error_message = Column(Text, default="")
    duration = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    result = relationship("TaskResult", back_populates="items")
    crawler = relationship("Crawler", back_populates="result_items")


class ParseResult(Base, TimestampMixin):
    """解析结果"""
    __tablename__ = "parse_results"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, index=True)
    description = Column(Text, default="")
    task_result_id = Column(Integer, ForeignKey("task_results.id", ondelete="CASCADE"), index=True)
    model_id = Column(Integer, ForeignKey("llm_models.id", ondelete="SET NULL"), nullable=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), default="success")  # success / failed
    raw_input = Column(Text, default="")
    raw_output = Column(Text, default="")
    parsed_content = Column(Text, default="")
    extracted_apis = Column(Text, default="")  # JSON 字符串，存储从原始文本中提取的 API 接口信息
    extract_apis_enabled = Column(Boolean, default=False)  # 本次解析是否启用了 API 接口信息自动提取
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    speed = Column(Float, default=0.0)  # tokens/秒
    duration = Column(Float, default=0.0)  # 秒
    error_message = Column(Text, default="")
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    is_public = Column(Boolean, default=False)

    task_result = relationship("TaskResult", back_populates="parse_results")
    model = relationship("LLMModel", back_populates="parse_results")


class OperationLog(Base, TimestampMixin):
    """操作日志：记录用户的关键写操作"""
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(64), default="", index=True)        # 冗余存储，便于按用户名检索
    module = Column(String(64), default="", index=True)          # 模块（认证/用户管理/爬虫地址 等）
    action = Column(String(64), default="", index=True)          # 动作（登录/创建/更新/删除 等）
    method = Column(String(16), default="")                      # HTTP 方法
    path = Column(String(256), default="", index=True)           # 请求路径
    params = Column(Text, default="")                            # 请求参数（query/path，已脱敏）
    status = Column(String(16), default="success", index=True)   # success / failed
    status_code = Column(Integer, default=0)                     # HTTP 状态码
    ip = Column(String(64), default="")
    user_agent = Column(String(256), default="")
    error_msg = Column(Text, default="")
    duration_ms = Column(Integer, default=0)                     # 耗时（毫秒）
