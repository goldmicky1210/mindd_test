from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    embedding_model: str = Field(default="sentence-transformers", env="EMBEDDING_MODEL")
    st_model_name: str = Field(default="all-MiniLM-L6-v2", env="ST_MODEL_NAME")
    openai_chat_model: str = Field(default="gpt-4o-mini", env="OPENAI_CHAT_MODEL")
    retrieval_top_k: int = Field(default=5, env="RETRIEVAL_TOP_K")
    storage_dir: str = Field(default="storage", env="STORAGE_DIR")
    data_dir: str = Field(default="data/startups", env="DATA_DIR")
    db_url: str = Field(default="sqlite:///storage/mindd.db", env="DB_URL")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def indexes_dir(self) -> Path:
        return Path(self.storage_dir) / "indexes"

    @property
    def use_openai_embeddings(self) -> bool:
        return self.embedding_model == "openai" and bool(self.openai_api_key)

    @property
    def llm_available(self) -> bool:
        return bool(self.openai_api_key)


settings = Settings()
