from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """全局配置类 - 面试考点：使用pydantic-settings进行配置管理，类型安全且支持环境变量"""
    
    # 数据库配置
    DATABASE_URL: str
    
    # Redis配置
    REDIS_URL: str
    
    # 邮件配置
    EMAIL_HOST: str
    EMAIL_PORT: int
    EMAIL_USERNAME: str
    EMAIL_PASSWORD: str
    EMAIL_FROM: str
    
    # JWT配置
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # 应用配置
    APP_NAME: str = "Personal Task System"
    DEBUG: bool = False
    
    # 验证码配置
    VERIFY_CODE_EXPIRE_SECONDS: int = 300  # 5分钟
    VERIFY_CODE_SEND_INTERVAL: int = 60    # 1分钟防刷
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例 - 面试考点：使用lru_cache缓存配置对象，避免重复读取"""
    return Settings()


settings = get_settings()
