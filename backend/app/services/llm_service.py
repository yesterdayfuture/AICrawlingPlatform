"""大模型解析服务：基于 openai 库"""
import re
import time
import json
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from sqlalchemy.orm import Session

from ..config import settings
from ..models import LLMModel, Prompt, TaskResult, ParseResult, TaskResultItem


def _build_client(model: LLMModel):
    from openai import OpenAI
    kwargs = {"api_key": model.api_key or "EMPTY"}
    if model.base_url:
        kwargs["base_url"] = model.base_url
    kwargs["timeout"] = settings.llm_timeout
    return OpenAI(**kwargs)


# ============ API 接口信息提取 ============

# 匹配完整 URL（含 http/https）
_URL_RE = re.compile(
    r'https?://[A-Za-z0-9\-._~%:/?#\[\]@!$&\'()*+,;=]+',
    re.IGNORECASE,
)
# 匹配代码块中常见的 HTTP 方法声明，如 `GET /api/users`、`POST /v1/login`
_METHOD_PATH_RE = re.compile(
    r'\b(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(/[\w\-./{}:?=&%]+)',
    re.IGNORECASE,
)


def _looks_like_api_url(url: str) -> bool:
    """简单判断一个 URL 是否疑似 API 接口（而非静态资源/普通网页）"""
    if not url:
        return False
    parsed = urlparse(url)
    path = (parsed.path or "").lower()
    if not path or path == "/":
        return False
    # 排除明显的静态资源
    if re.search(r'\.(html?|css|js|png|jpe?g|gif|svg|ico|woff2?|ttf|mp4|pdf|zip)(\?|$)', path):
        return False
    # 含 /api/ /v1/ /v2/ 等版本号，或路径中有 .do / .action，或带查询参数，都视为 API
    if '/api' in path or re.search(r'/v\d+/', path) or parsed.query:
        return True
    # 路径片段数 >=2 时也倾向认为是接口
    segs = [s for s in path.split('/') if s]
    return len(segs) >= 2


def _extract_apis_from_text(text: str) -> list:
    """从文本中提取 API 接口信息，返回 list[dict]。

    每条 API 形如：
      {
        "method": "GET",
        "url": "https://example.com/api/users",
        "path": "/api/users",
        "query_params": {"page": ["1"]},
        "source": "url"   // url | method_path
      }
    """
    if not text:
        return []

    seen_paths = set()
    results = []

    # 1) 先匹配完整 URL
    for m in _URL_RE.finditer(text):
        url = m.group(0).rstrip('.,;)\"\'')
        if not _looks_like_api_url(url):
            continue
        parsed = urlparse(url)
        path = parsed.path or "/"
        key = (parsed.netloc.lower(), path.lower(), parsed.query.lower())
        if key in seen_paths:
            continue
        seen_paths.add(key)
        results.append({
            "method": "GET",  # URL 本身不携带方法，默认 GET
            "url": url,
            "path": path,
            "query_params": {k: v for k, v in parse_qs(parsed.query).items()},
            "source": "url",
        })

    # 2) 再匹配 `METHOD /path` 形式（常见于接口文档/代码块）
    for m in _METHOD_PATH_RE.finditer(text):
        method = m.group(1).upper()
        path = m.group(2)
        key = ("", path.lower(), "")
        if key in seen_paths:
            continue
        seen_paths.add(key)
        results.append({
            "method": method,
            "url": "",
            "path": path,
            "query_params": {},
            "source": "method_path",
        })

    return results


def extract_apis(raw_input: str, raw_output: str) -> list:
    """从解析的输入和输出文本中提取 API 信息。

    优先尝试把 LLM 输出当作 JSON 解析（若 LLM 已结构化输出），
    否则用正则从原始文本中提取。
    """
    apis = []

    # 1) 若 LLM 输出本身是 JSON / JSON 数组，尝试直接解析
    if raw_output:
        stripped = raw_output.strip()
        # 去掉 markdown 代码块包裹
        if stripped.startswith('```'):
            stripped = re.sub(r'^```(?:json)?\s*', '', stripped)
            stripped = re.sub(r'\s*```$', '', stripped).strip()
        try:
            data = json.loads(stripped)
            # 形如 [{"method":..,"url":..}, ...] 或 {"apis": [...]}
            if isinstance(data, list):
                candidates = data
            elif isinstance(data, dict):
                candidates = data.get("apis") or data.get("endpoints") or data.get("results") or []
                if isinstance(data, dict) and ("method" in data or "url" in data or "path" in data):
                    candidates = [data]
            else:
                candidates = []
            for it in candidates:
                if not isinstance(it, dict):
                    continue
                url = it.get("url") or it.get("endpoint") or ""
                path = it.get("path") or ""
                method = (it.get("method") or it.get("http_method") or "GET").upper()
                if url or path:
                    apis.append({
                        "method": method,
                        "url": url,
                        "path": path,
                        "query_params": it.get("query_params") or it.get("params") or {},
                        "source": "llm_json",
                        "description": it.get("description") or "",
                    })
        except (json.JSONDecodeError, ValueError):
            pass  # 非 JSON，走正则提取

    # 2) 正则补充提取（从输出 + 输入）
    if not apis:
        apis = _extract_apis_from_text(raw_output)
    # 输入文本里也可能有 API（爬虫抓取的接口列表页）
    for it in _extract_apis_from_text(raw_input):
        key = (it.get("url", "").lower(), it.get("path", "").lower())
        if any((x.get("url", "").lower(), x.get("path", "").lower()) == key for x in apis):
            continue
        apis.append(it)

    return apis


def parse_task_result(
    db: Session,
    task_result_id: int,
    model_id: int,
    prompt_id: int,
    name: str,
    description: str = "",
    item_ids=None,
    owner_id: int = None,
    extract_apis_flag: bool = False,
) -> ParseResult:
    """对一个任务结果发起 LLM 解析"""
    task_result = db.query(TaskResult).filter(TaskResult.id == task_result_id).first()
    if not task_result:
        raise ValueError(f"任务结果不存在: {task_result_id}")
    model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
    if not model:
        raise ValueError(f"大模型不存在: {model_id}")
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise ValueError(f"提示词不存在: {prompt_id}")

    query = db.query(TaskResultItem).filter(TaskResultItem.result_id == task_result.id)
    if item_ids:
        query = query.filter(TaskResultItem.id.in_(item_ids))
    items = query.all()

    raw_input_parts = []
    for idx, item in enumerate(items, 1):
        raw_input_parts.append(
            f"### 来源 {idx}: {item.crawler_name}\n"
            f"URL: {item.url}\n"
            f"状态: {'成功' if item.success else '失败'}\n"
            f"内容:\n{item.content or item.error_message}\n"
        )
    raw_input = "\n".join(raw_input_parts) if raw_input_parts else "(无内容)"

    parse = ParseResult(
        name=name,
        description=description,
        task_result_id=task_result.id,
        model_id=model.id,
        prompt_id=prompt.id,
        status="success",
        raw_input=raw_input,
        owner_id=owner_id,
        extract_apis_enabled=extract_apis_flag,
    )
    db.add(parse)
    db.flush()

    started = time.time()
    try:
        client = _build_client(model)
        messages = []
        if prompt.system_prompt:
            messages.append({"role": "system", "content": prompt.system_prompt})
        user_content = (prompt.user_prompt or "").replace("{content}", raw_input) if prompt.user_prompt else raw_input
        if "{content}" not in (prompt.user_prompt or ""):
            user_content = f"{prompt.user_prompt or ''}\n\n以下是待解析的内容：\n{raw_input}"
        messages.append({"role": "user", "content": user_content})

        resp = client.chat.completions.create(
            model=model.model_name,
            messages=messages,
            temperature=model.temperature,
            max_tokens=model.max_tokens,
        )
        raw_output = resp.choices[0].message.content or ""
        usage = resp.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0
        total_tokens = usage.total_tokens if usage else (input_tokens + output_tokens)
        duration = round(time.time() - started, 3)
        speed = round(total_tokens / duration, 2) if duration > 0 else 0.0

        parse.raw_output = raw_output
        parse.parsed_content = raw_output
        parse.input_tokens = input_tokens
        parse.output_tokens = output_tokens
        parse.total_tokens = total_tokens
        parse.speed = speed
        parse.duration = duration
        parse.status = "success"
    except Exception as e:  # noqa: BLE001
        duration = round(time.time() - started, 3)
        parse.status = "failed"
        parse.error_message = f"{type(e).__name__}: {str(e)}"
        parse.duration = duration
        parse.raw_output = ""

    # 仅当用户选择"自动提取 API 接口信息"时，才从输入/输出中提取
    if extract_apis_flag:
        try:
            apis = extract_apis(parse.raw_input or "", parse.raw_output or "")
            parse.extracted_apis = json.dumps(apis, ensure_ascii=False) if apis else ""
        except Exception as e:  # noqa: BLE001
            parse.extracted_apis = ""
    else:
        parse.extracted_apis = ""

    db.commit()
    db.refresh(parse)
    return parse
