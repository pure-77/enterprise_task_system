"""Office文档转PDF转换服务"""
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class OfficeConverter:
    """Office文档转PDF转换器"""

    # 支持的Office文件扩展名
    OFFICE_EXTENSIONS = {'.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'}

    def __init__(self, libreoffice_path: Optional[str] = None):
        """
        初始化转换器

        Args:
            libreoffice_path: LibreOffice可执行文件路径，如果为None则自动检测
        """
        self.libreoffice_path = libreoffice_path or self._find_libreoffice()

    def _find_libreoffice(self) -> str:
        """自动检测LibreOffice安装路径"""
        # 尝试常见的命令名称
        for cmd in ['libreoffice', 'soffice', 'soffice.exe']:
            path = shutil.which(cmd)
            if path:
                logger.info(f"找到LibreOffice: {path}")
                return path

        # Windows常见安装路径
        windows_paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]

        for path in windows_paths:
            if os.path.exists(path):
                logger.info(f"找到LibreOffice: {path}")
                return path

        raise RuntimeError(
            "未找到LibreOffice。请安装LibreOffice或指定libreoffice_path参数。\n"
            "下载地址: https://www.libreoffice.org/download/download/"
        )

    def is_office_file(self, filename: str) -> bool:
        """判断文件是否为Office文档"""
        ext = Path(filename).suffix.lower()
        return ext in self.OFFICE_EXTENSIONS

    def convert_to_pdf(
        self,
        input_path: str,
        output_dir: Optional[str] = None
    ) -> str:
        """
        将Office文档转换为PDF

        Args:
            input_path: 输入文件路径
            output_dir: 输出目录，如果为None则使用临时目录

        Returns:
            生成的PDF文件路径

        Raises:
            FileNotFoundError: 输入文件不存在
            RuntimeError: 转换失败
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"输入文件不存在: {input_path}")

        # 确定输出目录
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="office_pdf_")

        os.makedirs(output_dir, exist_ok=True)

        # 生成输出文件名（保持原文件名，扩展名改为.pdf）
        input_name = Path(input_path).stem
        output_path = os.path.join(output_dir, f"{input_name}.pdf")

        # 构建LibreOffice命令
        cmd = [
            self.libreoffice_path,
            '--headless',  # 无界面模式
            '--convert-to', 'pdf',
            '--outdir', output_dir,
            input_path
        ]

        try:
            logger.info(f"开始转换: {input_path} -> {output_path}")

            # 执行转换
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2分钟超时
                encoding='utf-8',
                errors='ignore'
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                logger.error(f"LibreOffice转换失败: {error_msg}")
                raise RuntimeError(f"文档转换失败: {error_msg}")

            # 验证输出文件是否存在
            if not os.path.exists(output_path):
                raise RuntimeError(f"转换后PDF文件未生成: {output_path}")

            logger.info(f"转换成功: {output_path}")
            return output_path

        except subprocess.TimeoutExpired:
            raise RuntimeError("文档转换超时（超过2分钟）")
        except Exception as e:
            logger.error(f"转换过程出错: {e}")
            raise


class CachedOfficeConverter(OfficeConverter):
    """带缓存的Office文档转换器"""

    def __init__(self, cache_dir: str = "uploads/pdf_cache", **kwargs):
        super().__init__(**kwargs)
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_path(self, file_id: int, original_name: str) -> str:
        """获取缓存文件路径"""
        cache_name = f"{file_id}_{Path(original_name).stem}.pdf"
        return os.path.join(self.cache_dir, cache_name)

    def convert_to_pdf_cached(
        self,
        input_path: str,
        file_id: int,
        original_name: str
    ) -> str:
        """
        带缓存的PDF转换

        Args:
            input_path: 输入文件路径
            file_id: 文件ID
            original_name: 原始文件名

        Returns:
            PDF文件路径
        """
        cache_path = self._get_cache_path(file_id, original_name)

        # 如果缓存存在且比源文件新，直接返回缓存
        if os.path.exists(cache_path):
            input_mtime = os.path.getmtime(input_path)
            cache_mtime = os.path.getmtime(cache_path)
            if cache_mtime > input_mtime:
                logger.info(f"使用缓存PDF: {cache_path}")
                return cache_path

        # 转换并缓存
        pdf_path = self.convert_to_pdf(input_path, self.cache_dir)

        # 重命名为带文件ID的缓存文件
        if pdf_path != cache_path:
            if os.path.exists(cache_path):
                os.remove(cache_path)
            os.rename(pdf_path, cache_path)

        return cache_path


# 全局转换器实例（带缓存）
converter = CachedOfficeConverter()
