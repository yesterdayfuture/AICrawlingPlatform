"""时区工具

项目所有业务时间戳统一使用北京时间（UTC+8）的 naive datetime 存储，
便于 SQLite 直接存储、前端 dayjs 按本地时区解析后无需额外转换。

注意：
- 业务表时间字段（created_at / updated_at / started_at 等）必须用 now_cst()
- JWT exp 仍用 datetime.utcnow()，符合 JWT 标准（pyjwt 会转为 UTC 时间戳比较）
- 调度器时区已固定为 Asia/Shanghai，与本工具保持一致
"""
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

# 北京时间 UTC+8
CST = timezone(timedelta(hours=8))


def now_cst() -> datetime:
    """返回当前北京时间（naive datetime，无时区信息）

    返回 naive datetime 的原因：
    1. SQLite 不支持带时区的 datetime，存的是字符串
    2. 前端 dayjs 解析无时区字符串时按本地时区处理，正好显示北京时间
    3. 与原有 datetime.utcnow() 的 naive 行为一致，避免 SQLAlchemy 报错
    """
    # return datetime.now(CST).replace(tzinfo=None)
    return datetime.now(ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)
