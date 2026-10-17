"""腾讯云COS配置"""
from pydantic_settings import BaseSettings


class COSConfig(BaseSettings):
    """COS配置"""
    # 腾讯云密钥
    COS_SECRET_ID: str = ""
    COS_SECRET_KEY: str = ""

    # COS存储桶配置
    COS_BUCKET: str = ""  # 存储桶名称，例如：my-bucket
    COS_REGION: str = ""  # 地域，例如：ap-guangzhou
    COS_APPID: str = ""   # APPID

    class Config:
        env_file = ".env"
        extra = "allow"

    @property
    def bucket_name(self) -> str:
        """完整的Bucket名称"""
        if self.COS_APPID:
            return f"{self.COS_BUCKET}-{self.COS_APPID}"
        return self.COS_BUCKET

    @property
    def is_configured(self) -> bool:
        """检查COS是否已配置"""
        return all([
            self.COS_SECRET_ID,
            self.COS_SECRET_KEY,
            self.COS_BUCKET,
            self.COS_REGION,
            self.COS_APPID
        ])

    def get_cos_client(self):
        """获取COS客户端"""
        from qcloud_cos import CosConfig, CosS3Client

        config = CosConfig(
            Region=self.COS_REGION,
            SecretId=self.COS_SECRET_ID,
            SecretKey=self.COS_SECRET_KEY,
        )
        return CosS3Client(config)


# 全局配置实例
cos_config = COSConfig()
