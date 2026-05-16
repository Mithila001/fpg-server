from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────
    DB_URL: str = ""

    # ── Job / SSE timeouts ───────────────────────────────────────────
    # Hard wall-clock limit for the whole generation job (seconds).
    FPG_GENERATION_API_TIMEOUT: int = 180
    # How long a finished job stays in the in-memory registry before purge.
    JOB_REGISTRY_CLEANUP_DELAY: int = 60

    # ── Optuna tunables ──────────────────────────────────────────────
    # Maximum number of Optuna trials per generation request.
    OPTUNA_TRIAL_COUNT: int = 20
    # Per-trial running timeout (seconds). Keep < FPG_GENERATION_API_TIMEOUT.
    OPTUNA_TRIAL_TIMEOUT: int = 170

    # ── Feature flags ────────────────────────────────────────────────
    # Set to False in production / cloud to skip all matplotlib saves.
    ENABLE_PLOT_SAVING: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
