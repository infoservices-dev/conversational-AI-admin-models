import os
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    server_name: str = Field(default="clairai-admin-mcp", description="MCP Server name")
    server_version: str = Field(default="1.0.0", description="Server version")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8080, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    
    backend_api_url: str = Field(
        default="https://backend.clairai.cloud",
        description="Backend API base URL"
    )
    bearer_token: str | None = Field(default=None, description="Bearer token for API auth")
    api_timeout: int = Field(default=30, description="API request timeout in seconds")
    
    aws_region: str = Field(default="us-east-1", description="AWS region")
    
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    
    rate_limit_requests: int = Field(default=100, description="Max requests per minute")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")
    
    class Config:
        env_prefix = ""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
