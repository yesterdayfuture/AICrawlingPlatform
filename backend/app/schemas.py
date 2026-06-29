"""Pydantic 数据模型"""
from typing import Optional, List, Any, Dict
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# ============ 通用 ============
class PageQuery(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=200)
    name: Optional[str] = None
    description: Optional[str] = None
    search_mode: str = Field("fuzzy", pattern="^(fuzzy|exact)$")  # fuzzy / exact
    status: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


# ============ 用户 ============
class LoginRequest(BaseModel):
    username: str
    password: str


class UserBase(BaseModel):
    username: str
    nickname: str = ""
    email: str = ""


class UserCreate(UserBase):
    password: str
    role: str = Field("user", pattern="^(admin|user)$")


class UserUpdate(BaseModel):
    """管理员修改用户"""
    nickname: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = Field(None, pattern="^(admin|user)$")
    is_active: Optional[bool] = None
    password: Optional[str] = None  # 重置密码


class UserSelfUpdate(BaseModel):
    """用户修改自己的资料"""
    nickname: Optional[str] = None
    email: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    nickname: str = ""
    email: str = ""
    role: str = "user"
    is_active: bool = True
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class LoginResponse(BaseModel):
    token: str
    user: UserOut


# ============ 爬虫 ============
class CrawlerBase(BaseModel):
    name: str
    description: str = ""
    url: str
    method: str = Field("GET", pattern="^(GET|POST)$")
    headers: Dict[str, Any] = Field(default_factory=dict)
    params: Dict[str, Any] = Field(default_factory=dict)
    body: Dict[str, Any] = Field(default_factory=dict)
    status: str = "enabled"
    is_public: bool = False


class CrawlerCreate(CrawlerBase):
    pass


class CrawlerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    method: Optional[str] = Field(None, pattern="^(GET|POST)$")
    headers: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    is_public: Optional[bool] = None


class CrawlerOut(CrawlerBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_id: Optional[int] = None
    owner_name: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ============ 大模型 ============
class LLMModelBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    name: str
    description: str = ""
    provider: str = "openai"
    base_url: str = ""
    api_key: str = ""
    model_name: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 2048
    status: str = "enabled"
    is_public: bool = False


class LLMModelCreate(LLMModelBase):
    pass


class LLMModelUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    name: Optional[str] = None
    description: Optional[str] = None
    provider: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    status: Optional[str] = None
    is_public: Optional[bool] = None


class LLMModelOut(LLMModelBase):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    id: int
    owner_id: Optional[int] = None
    owner_name: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ============ 提示词 ============
class PromptBase(BaseModel):
    name: str
    description: str = ""
    system_prompt: str = ""
    user_prompt: str = ""
    status: str = "enabled"
    is_public: bool = False


class PromptCreate(PromptBase):
    pass


class PromptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    status: Optional[str] = None
    is_public: Optional[bool] = None


class PromptOut(PromptBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_id: Optional[int] = None
    owner_name: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ============ 任务 ============
class TaskBase(BaseModel):
    name: str
    description: str = ""
    status: str = "enabled"
    is_scheduled: bool = False
    interval_value: int = 0
    interval_unit: str = Field("min", pattern="^(min|hour|day|month)$")
    crawler_ids: List[int] = Field(default_factory=list)
    is_public: bool = False


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    is_scheduled: Optional[bool] = None
    interval_value: Optional[int] = None
    interval_unit: Optional[str] = Field(None, pattern="^(min|hour|day|month)$")
    crawler_ids: Optional[List[int]] = None
    is_public: Optional[bool] = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str = ""
    status: str = "enabled"
    is_scheduled: bool = False
    interval_value: int = 0
    interval_unit: str = "min"
    last_run_at: Optional[datetime] = None
    crawler_ids: List[int] = Field(default_factory=list)
    crawler_names: List[str] = Field(default_factory=list)
    is_public: bool = False
    owner_id: Optional[int] = None
    owner_name: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ============ 任务结果 ============
class TaskResultItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    crawler_id: Optional[int] = None
    crawler_name: str = ""
    url: str = ""
    method: str = "GET"
    status_code: Optional[int] = None
    success: bool = True
    content: str = ""
    error_message: str = ""
    duration: float = 0.0
    created_at: Optional[datetime] = None


class TaskResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str = ""
    task_id: Optional[int] = None
    task_name: str = ""
    status: str = "success"
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration: float = 0.0
    error_message: str = ""
    item_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    is_public: bool = False
    owner_id: Optional[int] = None
    owner_name: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TaskResultDetailOut(TaskResultOut):
    items: List[TaskResultItemOut] = Field(default_factory=list)


class ParseRequest(BaseModel):
    """对任务结果发起解析"""
    model_config = ConfigDict(protected_namespaces=())
    name: str
    description: str = ""
    task_result_id: int
    model_id: int
    prompt_id: int
    item_ids: Optional[List[int]] = None  # 为空则解析全部 items
    extract_apis: bool = False  # 是否在解析后自动从原始文本中提取 API 接口信息


# ============ 解析结果 ============
class ParseResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    id: int
    name: str
    description: str = ""
    task_result_id: Optional[int] = None
    task_result_name: str = ""
    model_id: Optional[int] = None
    model_name: str = ""
    prompt_id: Optional[int] = None
    prompt_name: str = ""
    status: str = "success"
    parsed_content: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    speed: float = 0.0
    duration: float = 0.0
    error_message: str = ""
    extract_apis_enabled: bool = False  # 是否启用了 API 接口信息自动提取
    is_public: bool = False
    owner_id: Optional[int] = None
    owner_name: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ParseResultDetailOut(ParseResultOut):
    raw_input: str = ""
    raw_output: str = ""
    extracted_apis: str = ""


class ParseResultCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    name: str
    description: str = ""
    task_result_id: int
    model_id: int
    prompt_id: int
    status: str = "success"
    raw_input: str = ""
    raw_output: str = ""
    parsed_content: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    speed: float = 0.0
    duration: float = 0.0
    error_message: str = ""


class ParseResultUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    is_public: Optional[bool] = None


# ============ 操作日志 ============
class OperationLogOut(BaseModel):
    """操作日志输出"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: Optional[int] = None
    username: str = ""
    module: str = ""
    action: str = ""
    method: str = ""
    path: str = ""
    params: str = ""
    status: str = "success"
    status_code: int = 0
    ip: str = ""
    user_agent: str = ""
    error_msg: str = ""
    duration_ms: int = 0
    created_at: Optional[datetime] = None

