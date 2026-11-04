from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database connection string (defaults to local SQLite if neon postgres is offline)
    DATABASE_URL: str = f"sqlite:///{(Path(__file__).resolve().parents[1] / 'fractoes.db').as_posix()}"

    # Supabase project details (completely optional, falls back to inline base64)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_BUCKET: str = "xray-images"

    # JWT auth
    JWT_SECRET: str = "05c28859dbc280e191e168a1962f4d95f93b77908a4b925cd0b8350a2602f9de"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS origins
    ALLOWED_ORIGINS: str = (
        "https://fractoes.vercel.app,http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
    )

    @property
    def cors_origins(self) -> list[str]:
        raw = self.ALLOWED_ORIGINS.strip()
        if raw.startswith("[") and raw.endswith("]"):
            import json
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(o).strip() for o in parsed if str(o).strip()]
            except Exception:
                pass
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    # AI Vision APIs (Gemini, Groq, OpenAI, xAI Grok)
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GROK_API_KEY: Optional[str] = None
    GROK_API_URL: str = "https://api.x.ai/v1/chat/completions"
    GROK_MODEL: str = "grok-2-vision-1212"
    AI_TIMEOUT_SECONDS: float = 15.0

    # Gmail credentials for sending emails (optional)
    GMAIL_ADDRESS: Optional[str] = None
    GMAIL_APP_PASSWORD: Optional[str] = None


settings = Settings()
