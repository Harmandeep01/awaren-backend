from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Postgres asyncpg URL. Example:
    # postgresql+asyncpg://user:password@localhost:5432/healthbotdb
    database_url: str = "postgresql+asyncpg://postgres:root@localhost:5432/healthbotdb"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    google_cloud_project: str = ""
    google_cloud_location: str = ""
    mem0_api_key: str = ""
    vertex_model_name: str = "gemini-2.5-flash"
    google_genai_use_vertexai: bool
    aws_region: str ="eu-north-1"

    class Config:
        env_file = ".env"

settings = Settings()
