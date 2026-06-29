"""数据库连接与会话管理"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI 依赖：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库表"""
    from . import models  # noqa: F401  确保模型已注册
    Base.metadata.create_all(bind=engine)
    _seed_default_prompts()


def _seed_default_prompts():
    """首次启动时写入默认提示词（仅当提示词表为空时）"""
    from .models import Prompt
    db = SessionLocal()
    try:
        if db.query(Prompt).count() > 0:
            return
        defaults = [
            {
                "name": "新闻摘要提取",
                "description": "从新闻网页内容中提取标题、摘要、发布时间、作者等关键信息，输出 JSON 格式",
                "system_prompt": "你是一个专业的新闻信息提取助手。请从给定的网页内容中提取结构化的新闻信息，严格以 JSON 格式输出，不要包含多余的解释文字。",
                "user_prompt": "请从以下网页内容中提取新闻信息，输出 JSON 格式，包含字段：title（标题）、summary（摘要）、publish_time（发布时间）、author（作者）、source（来源）。\n\n网页内容：\n{content}",
            },
            {
                "name": "商品信息提取",
                "description": "从电商商品页面提取商品名称、价格、规格、描述等信息，输出 JSON 格式",
                "system_prompt": "你是一个电商商品信息提取专家。请从给定的商品页面内容中提取结构化商品信息，严格以 JSON 格式输出。",
                "user_prompt": "请从以下商品页面内容中提取商品信息，输出 JSON 格式，包含字段：product_name（商品名称）、price（价格）、currency（货币）、specs（规格）、description（描述）、stock（库存状态）。\n\n页面内容：\n{content}",
            },
            {
                "name": "文章正文提取",
                "description": "从网页中提取文章正文内容，去除导航、广告、页脚等无关信息",
                "system_prompt": "你是一个网页正文提取助手。请从给定的 HTML/文本内容中识别并提取文章正文，去除导航栏、侧边栏、广告、页脚等非正文内容，输出纯文本。",
                "user_prompt": "请从以下网页内容中提取文章正文，去除广告和导航等无关信息，仅输出正文文本。\n\n网页内容：\n{content}",
            },
            {
                "name": "通用结构化数据提取",
                "description": "通用的结构化数据提取提示词，可根据需求调整输出字段，适用于多种网页类型",
                "system_prompt": "你是一个结构化数据提取专家。请分析给定的网页内容，提取其中的关键信息并以 JSON 格式输出。字段名称使用英文，值使用原文语言。",
                "user_prompt": "请分析以下网页内容，提取其中的关键信息并输出为 JSON 格式。如果没有明确的结构化信息，请输出空对象 {}。\n\n网页内容：\n{content}",
            },
            {
                "name": "社交媒体帖子提取",
                "description": "从社交媒体页面提取帖子内容、作者、点赞数、评论数等信息",
                "system_prompt": "你是一个社交媒体信息提取助手。请从给定内容中提取帖子结构化信息，以 JSON 格式输出。",
                "user_prompt": "请从以下社交媒体页面内容中提取帖子信息，输出 JSON 格式，包含字段：author（作者）、content（帖子内容）、likes（点赞数）、comments（评论数）、shares（转发数）、post_time（发布时间）。\n\n页面内容：\n{content}",
            },
            {
                "name": "全文本信息提取(Markdown)",
                "description": "从返回结果中提取所有文字信息，以 Markdown 格式输出，保留结构与层级",
                "system_prompt": "你是一个专业的网页文本提取助手。请从给定的网页内容中提取所有有意义的文字信息，去除 HTML 标签、脚本、样式、广告、导航等无关内容，将提取到的文字信息以 Markdown 格式输出。请保留原文的标题层级、段落、列表、表格等结构，不要遗漏任何正文文字。",
                "user_prompt": "请从以下网页内容中提取所有文字信息，以 Markdown 格式输出。要求：\n1. 保留原文的标题层级（# ## ###）\n2. 保留段落、列表、表格等结构\n3. 去除导航、广告、页脚等无关内容\n4. 不要添加任何解释或总结，直接输出提取到的 Markdown 文本\n\n网页内容：\n{content}",
            },
        ]
        for item in defaults:
            # 默认提示词设为公开，所有用户可见可用
            db.add(Prompt(**item, is_public=True))
        db.commit()
    finally:
        db.close()
