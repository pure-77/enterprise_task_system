"""腾讯云COS存储服务"""
import os
import logging
from typing import Optional
from app.core.cos_config import cos_config

logger = logging.getLogger(__name__)


class COSStorage:
    """腾讯云COS存储服务"""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        """懒加载COS客户端"""
        if self._client is None:
            self._client = cos_config.get_cos_client()
        return self._client

    @property
    def bucket(self):
        return cos_config.bucket_name

    def upload_file(
        self,
        local_path: str,
        cos_key: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        上传文件到COS

        Args:
            local_path: 本地文件路径
            cos_key: COS中的文件Key
            content_type: 文件类型

        Returns:
            文件的COS URL
        """
        try:
            with open(local_path, 'rb') as f:
                kwargs = {
                    'Bucket': self.bucket,
                    'Body': f,
                    'Key': cos_key,
                }
                if content_type:
                    kwargs['ContentType'] = content_type
                self.client.put_object(**kwargs)

            logger.info(f"文件上传成功: {cos_key}")
            return self.get_file_url(cos_key)

        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            raise

    def get_file_url(self, cos_key: str) -> str:
        """获取文件的访问URL"""
        return f"https://{self.bucket}.cos.{cos_config.COS_REGION}.myqcloud.com/{cos_key}"

    def get_preview_url(self, cos_key: str, dst_type: str = "html") -> str:
        """
        获取文档预览URL（数据万象）

        Args:
            cos_key: COS中的文件Key
            dst_type: 预览输出类型，html 或 image

        Returns:
            预览URL
        """
        base_url = self.get_file_url(cos_key)
        return f"{base_url}?ci-process=doc-preview&dstType={dst_type}"


# 全局存储实例
cos_storage = COSStorage()
