"""应用配置

通过 pydantic-settings 从 .env 文件读取配置，字段名自动映射为大写下划线环境变量。
优先级：环境变量 > backend/.env > 代码默认值。
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 数据库配置：默认使用 SQLite，可切换 PostgreSQL
    # SQLite:    sqlite:///./crawler.db
    # Postgres:  postgresql+psycopg2://user:pass@localhost:5432/dbname
    database_url: str = "sqlite:///./crawler.db"

    # CORS 配置（多个来源用逗号分隔）
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # LLM 默认超时（秒）
    llm_timeout: int = 120

    # 爬虫默认超时（秒）
    crawler_timeout: int = 30

    # JWT 配置
    jwt_secret: str = "crawler-mgmt-secret-key-please-change-in-production-2024"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # 默认管理员账户（首次启动时自动创建）
    default_admin_username: str = "admin"
    default_admin_password: str = "admin123"

    @property
    def cors_origin_list(self) -> list:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
