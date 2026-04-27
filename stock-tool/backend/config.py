from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_password: str
    secret_key: str
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    notify_email: str = ""
    claude_api_key: str = ""
    database_url: str = "./data.db"

    class Config:
        env_file = ".env"


settings = Settings()
