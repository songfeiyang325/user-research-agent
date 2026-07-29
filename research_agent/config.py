"""全局配置：从 .env 读取（pydantic-settings）。

所有 LLM/服务/存储参数集中在这里，切换模型或网关只改 .env，不动代码。
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
    # 无 key 时是否用启发式 mock（未配 key 也会自动回退，见 llm/client.py）
    llm_mock: bool = False

    # ---- 服务 ----
    host: str = "127.0.0.1"
    port: int = 8000
    app_base_url: str = "http://127.0.0.1:8000"

    # ---- 存储 ----
    db_path: str = "data/app.db"

    @property
    def use_mock(self) -> bool:
        """没有配置 API Key 时自动进入 mock 模式，保证离线可跑通。"""
        return self.llm_mock or not self.glm_api_key.strip()

    @property
    def sqlite_url(self) -> str:
        return f"sqlite:///{self.db_path}"


settings = Settings()
