"""
Configuration settings for Monetx NCM SSH Emulator
"""

import os
from typing import List, Dict, Any

class Settings:
    # Application settings
    APP_NAME: str = "Monetx NCM SSH Emulator"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8001"))
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-jwt-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    
    # CORS settings
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # SSH settings
    SSH_TIMEOUT: int = int(os.getenv("SSH_TIMEOUT", "10"))
    SSH_MAX_SESSIONS: int = int(os.getenv("SSH_MAX_SESSIONS", "100"))
    SSH_SESSION_TIMEOUT: int = int(os.getenv("SSH_SESSION_TIMEOUT", "3600"))  # 1 hour
    
    # NMS Integration settings
    NMS_INTEGRATION_ENABLED: bool = os.getenv("NMS_INTEGRATION_ENABLED", "true").lower() == "true"
    NMS_BASE_URL: str = os.getenv("NMS_BASE_URL", "https://your-nms-domain.com")
    NMS_AUTH_ENDPOINT: str = os.getenv("NMS_AUTH_ENDPOINT", "/api/auth")
    NMS_API_KEY: str = os.getenv("NMS_API_KEY", "your-nms-api-key")
    
    # Database settings (for audit logs)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./audit.db")
    AUDIT_LOGS_ENABLED: bool = os.getenv("AUDIT_LOGS_ENABLED", "true").lower() == "true"
    
    # File upload settings
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    
    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "./logs/app.log")
    
    # UI settings
    UI_THEME: str = os.getenv("UI_THEME", "glass")
    LOGO_PATH: str = os.getenv("LOGO_PATH", "./static/monetx-logo.png")
    
    @classmethod
    def get_nms_config(cls) -> Dict[str, Any]:
        """Get NMS integration configuration"""
        return {
            "jwt_secret": cls.JWT_SECRET_KEY,
            "nms_base_url": cls.NMS_BASE_URL,
            "allowed_origins": cls.CORS_ORIGINS,
            "audit_log_enabled": cls.AUDIT_LOGS_ENABLED,
            "session_timeout": cls.SSH_SESSION_TIMEOUT,
            "max_sessions_per_user": 5
        }

# Development settings
class DevelopmentSettings(Settings):
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"

# Production settings
class ProductionSettings(Settings):
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    CORS_ORIGINS: List[str] = ["https://your-nms-domain.com"]

# Settings factory
def get_settings() -> Settings:
    """Get settings based on environment"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    elif env == "development":
        return DevelopmentSettings()
    else:
        return Settings()

# Global settings instance
settings = get_settings()
