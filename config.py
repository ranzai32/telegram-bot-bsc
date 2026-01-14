from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    api_base_url: str = "http://localhost:8080"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
