from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    groq_api_key: str
    embedding_model: str = "all-MiniLM-L6-v2"
    model_name: str = "llama-3.3-70b-versatile"

    # Email (optional — only needed for send feature)
    smtp_host: str     = "smtp.gmail.com"
    smtp_port: int     = 465
    sender_email: str  = ""
    sender_password: str = ""
    company_name: str  = "Our Company"

    class Config:
        env_file = ".env"
        extra    = "ignore"

settings = Settings()