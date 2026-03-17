from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Stats-R-Agent"
    openai_api_key: str = ""
    chroma_persist_dir: str = "./chroma_db"

    class Config:
        env_file = ".env"


settings = Settings()
