from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置。所有字段都可以通过环境变量或 .env 文件覆盖。"""

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------- 应用 ----------
    APP_NAME: str = "智企协同 Enterprise AI"
    APP_ENV: Literal["dev", "test", "prod"] = "dev"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # ---------- 安全 ----------
    SECRET_KEY: str = "dev-only-secret-change-me-0123456789abcdef"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_MIN_LENGTH: int = 8

    # ---------- 数据库 ----------
    DATABASE_URL: str = (
        "mysql+asyncmy://root:root@127.0.0.1:3306/enterprise_ai?charset=utf8mb4"
    )
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 1800
    AUTO_CREATE_TABLES: bool = False

    # ---------- 缓存 / 队列 ----------
    REDIS_URL: str | None = None

    # ---------- 跨域 ----------
    # NoDecode：禁止 pydantic-settings 把 .env 里的逗号串当 JSON 解析，
    # 交由下面的 field_validator 按逗号拆分，兼容 docs 中记录的写法。
    CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    # ---------- 注册 ----------
    # 是否允许企业自助注册；如需邀请制可置为 false
    ALLOW_SELF_REGISTRATION: bool = True

    # ---------- 初始化数据 ----------
    FIRST_ORG_NAME: str = "示例科技有限公司"
    FIRST_ORG_CODE: str = "demo"
    FIRST_SUPERUSER_USERNAME: str = "admin"
    FIRST_SUPERUSER_PASSWORD: str = "Admin@123456"
    FIRST_SUPERUSER_EMAIL: str = "admin@example.com"
    FIRST_SUPERUSER_REAL_NAME: str = "系统管理员"

    # ---------- AI 模型接入 ----------
    # 企业没配模型时回落到这里的平台级配置；provider 决定默认端点
    AI_DEFAULT_PROVIDER: str = "bailian"
    AI_CLOUD_BASE_URL: str | None = None
    AI_CLOUD_API_KEY: str | None = None
    AI_OLLAMA_BASE_URL: str = "http://127.0.0.1:11434/v1"
    AI_DEFAULT_MODEL: str = "qwen-plus"
    AI_EMBEDDING_MODEL: str = "text-embedding-v3"
    # 调用约束：防止单个请求把额度烧穿
    AI_TIMEOUT_SECONDS: float = 60.0
    AI_MAX_RETRIES: int = 2
    AI_MAX_TOKENS: int = 2048
    # 企业级 API Key 的加密密钥；留空则用 SECRET_KEY 派生（生产建议独立配置）
    AI_KEY_ENCRYPTION_KEY: str | None = None

    # ---------- 知识库 / RAG ----------
    # 每次送去向量化的切片数（百炼 embedding 接口对单次条数有上限，必须分批）
    EMBEDDING_BATCH_SIZE: int = 10
    # 召回条数与相似度下限：低于阈值的内容不塞进提示词，避免污染答案
    RAG_TOP_K: int = 5
    RAG_MIN_SCORE: float = 0.2
    # 混合检索里向量得分的权重（其余权重给关键词覆盖率）；1.0 = 退化为纯向量检索
    RAG_VECTOR_WEIGHT: float = 0.7
    # 上传文件落盘目录（容器内需挂载 volume，否则重建即丢）
    UPLOAD_DIR: str = "data/uploads"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        # 支持 CORS_ORIGINS=http://a,http://b 这种写法
        if isinstance(value, str) and not value.startswith("["):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_prod(self) -> bool:
        return self.APP_ENV == "prod"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
