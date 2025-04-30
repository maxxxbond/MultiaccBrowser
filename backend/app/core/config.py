from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_PORT: int = 8077
    DB_PATH: str = "user_data/profiles.db"

    class Config:
        env_file = ".env"

settings = Settings()
