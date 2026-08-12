# backend/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "sqlite:///./cryptonews.db"
    firebase_credentials_path: str = "./firebase-service-account.json"
    top_n_coins: int = 30


settings = Settings()
