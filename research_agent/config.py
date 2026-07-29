"""全局配置：从 .env 读取（pydantic-settings）。

切换模型或网关只改 .env，不动代码。
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ---- 智谱 GLM（OpenAI 兼容）----
    glm_api_key: str = ""
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4/"
    glm_model: str = "glm-5.2"
    # 无 key 时是否用启发式 mock（未配 key 也会自动回退）
    llm_mock: bool = False

    # ---- 服务 ----
    host: str = "127.0.0.1"
    port: int = 8000
    app_base_url: str = "http://127.0.0.1:8080"

    # ---- MongoDB ----
    # 本地开发默认连本机；docker-compose 会注入 mongodb://mongo:27017
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "research_agent"

    @property
    def use_mock(self) -> bool:
        """没有配置 API Key 时自动进入 mock 模式，保证离线可跑通。"""
        return self.llm_mock or not self.glm_api_key.strip()


settings = Settings()
