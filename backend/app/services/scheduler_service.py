"""定时任务调度服务

基于 APScheduler BackgroundScheduler 实现任务的定时执行。
- 仅调度 is_scheduled=True 且 status='enabled' 的任务
- 每个 Task 对应一个 job，job_id 格式为 task_{id}
- 调度任务在独立线程中执行，使用独立的 DB Session
"""
import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore

from ..database import SessionLocal
from ..models import Task

logger = logging.getLogger(__name__)

# 单例调度器
_scheduler: Optional[BackgroundScheduler] = None


def _job_id(task_id: int) -> str:
    return f"task_{task_id}"


def _build_trigger(interval_value: int, interval_unit: str):
    """根据 interval_value / interval_unit 构造触发器

    - min:  IntervalTrigger(minutes=N)
    - hour: IntervalTrigger(hours=N)
    - day:  IntervalTrigger(days=N)
    - month: CronTrigger(day=1, month='*/N', hour=0, minute=0)  每隔 N 个月 1 号执行
    """
    n = max(1, int(interval_value or 1))
    if interval_unit == "min":
        return IntervalTrigger(minutes=n)
    if interval_unit == "hour":
        return IntervalTrigger(hours=n)
    if interval_unit == "day":
        return IntervalTrigger(days=n)
    if interval_unit == "month":
        # 每隔 N 个月，1 号 0 点执行
        return CronTrigger(day=1, month=f"*/{n}", hour=0, minute=0)
    raise ValueError(f"不支持的间隔单位: {interval_unit}")


def _run_scheduled_task(task_id: int):
    """调度器触发的执行入口：使用独立 Session 调用 run_task"""
    # 延迟导入避免循环依赖
    from .crawler_service import run_task
    db = SessionLocal()
    try:
        run_task(db, task_id)
        logger.info("定时任务执行完成 task_id=%s", task_id)
    except Exception as e:  # noqa: BLE001
        logger.exception("定时任务执行失败 task_id=%s: %s", task_id, e)
    finally:
        db.close()


def _should_schedule(task: Task) -> bool:
    """判断任务是否需要被调度"""
    return bool(task.is_scheduled and task.status == "enabled"
                and task.interval_value and task.interval_value > 0)


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        raise RuntimeError("调度器尚未初始化，请先调用 start_scheduler()")
    return _scheduler


def start_scheduler():
    """启动调度器并从数据库恢复所有定时任务"""
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(
        jobstores={"default": MemoryJobStore()},
        timezone="Asia/Shanghai",
    )
    _scheduler.start()
    logger.info("APScheduler 已启动")
    # 从数据库恢复已存在的定时任务
    db = SessionLocal()
    try:
        tasks = db.query(Task).filter(Task.is_scheduled.is_(True), Task.status == "enabled").all()
        for task in tasks:
            schedule_task(task)
        logger.info("已恢复 %d 个定时任务", len(tasks))
    finally:
        db.close()


def shutdown_scheduler():
    """关闭调度器"""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("APScheduler 已关闭")


def schedule_task(task: Task):
    """为单个任务注册或更新调度 job（若不满足调度条件则移除）"""
    if _scheduler is None:
        return
    job_id = _job_id(task.id)
    # 先移除已有 job
    if _scheduler.get_job(job_id) is not None:
        _scheduler.remove_job(job_id)

    if not _should_schedule(task):
        return

    trigger = _build_trigger(task.interval_value, task.interval_unit)
    _scheduler.add_job(
        _run_scheduled_task,
        trigger=trigger,
        args=[task.id],
        id=job_id,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info("已注册定时任务 task_id=%s interval=%s %s",
                task.id, task.interval_value, task.interval_unit)


def unschedule_task(task_id: int):
    """移除任务的调度 job"""
    if _scheduler is None:
        return
    job_id = _job_id(task_id)
    if _scheduler.get_job(job_id) is not None:
        _scheduler.remove_job(job_id)
        logger.info("已移除定时任务 task_id=%s", task_id)
