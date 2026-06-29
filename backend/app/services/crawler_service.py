"""爬虫执行服务：支持 GET / POST"""
import time
import httpx
from datetime import datetime
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Crawler, TaskResult, TaskResultItem


def execute_crawler(crawler: Crawler) -> dict:
    """执行单个爬虫请求，返回抓取结果字典"""
    started = time.time()
    result = {
        "crawler_id": crawler.id,
        "crawler_name": crawler.name,
        "url": crawler.url,
        "method": crawler.method,
        "status_code": None,
        "success": False,
        "content": "",
        "error_message": "",
        "duration": 0.0,
    }
    try:
        headers = crawler.headers or {}
        params = crawler.params or {}
        body = crawler.body or {}
        method = (crawler.method or "GET").upper()

        with httpx.Client(timeout=settings.crawler_timeout, follow_redirects=True) as client:
            if method == "GET":
                resp = client.get(crawler.url, headers=headers, params=params)
            else:
                # POST: 如果 body 非空则 json，否则用 params 作为表单
                if body:
                    resp = client.post(crawler.url, headers=headers, params=params, json=body)
                else:
                    resp = client.post(crawler.url, headers=headers, params=params, data=params)
            result["status_code"] = resp.status_code
            resp.raise_for_status()
            result["content"] = resp.text
            result["success"] = True
    except httpx.HTTPStatusError as e:
        result["error_message"] = f"HTTP {e.response.status_code}: {str(e)}"
    except httpx.RequestError as e:
        result["error_message"] = f"请求错误: {type(e).__name__}: {str(e)}"
    except Exception as e:  # noqa: BLE001
        result["error_message"] = f"未知错误: {type(e).__name__}: {str(e)}"
    result["duration"] = round(time.time() - started, 3)
    return result


def run_task(db: Session, task_id: int) -> TaskResult:
    """执行一个任务下挂载的所有爬虫"""
    from ..models import Task
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError(f"任务不存在: {task_id}")

    started_at = datetime.utcnow()
    start_ts = time.time()
    name = f"{task.name} - {started_at.strftime('%Y-%m-%d %H:%M:%S')}"
    result = TaskResult(
        name=name,
        description=task.description,
        task_id=task.id,
        status="success",
        started_at=started_at,
        owner_id=task.owner_id,        # 继承任务的 owner
        is_public=task.is_public,      # 继承任务的公开状态
    )
    db.add(result)
    db.flush()

    success_count = 0
    failed_count = 0
    overall_error = []

    for link in task.crawlers:
        crawler = link.crawler
        item_data = execute_crawler(crawler)
        item = TaskResultItem(
            result_id=result.id,
            crawler_id=crawler.id,
            crawler_name=crawler.name,
            url=item_data["url"],
            method=item_data["method"],
            status_code=item_data["status_code"],
            success=item_data["success"],
            content=item_data["content"],
            error_message=item_data["error_message"],
            duration=item_data["duration"],
        )
        db.add(item)
        if item_data["success"]:
            success_count += 1
        else:
            failed_count += 1
            overall_error.append(f"{crawler.name}: {item_data['error_message']}")

    if failed_count > 0 and success_count > 0:
        result.status = "partial"
        result.error_message = "; ".join(overall_error)
    elif failed_count > 0:
        result.status = "failed"
        result.error_message = "; ".join(overall_error)

    result.success_count = success_count
    result.failed_count = failed_count
    result.finished_at = datetime.utcnow()
    result.duration = round(time.time() - start_ts, 3)

    task.last_run_at = result.finished_at
    db.commit()
    db.refresh(result)
    return result
