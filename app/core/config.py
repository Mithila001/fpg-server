from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_URL: str = ""
    FPG_GENERATION_API_TIMEOUT: int = 120
    JOB_REGISTRY_CLEANUP_DELAY: int = 120

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
