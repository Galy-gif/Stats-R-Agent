from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Stats-R-Agent"
    google_api_key: str = ""
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection: str = "stats_r_knowledge"
    embed_model: str = "all-MiniLM-L6-v2"   # 本地 sentence-transformers 模型
    chat_model: str = "gemini-2.5-flash"
    retriever_k: int = 5

    class Config:
        env_file = ".env"


settings = Settings()
