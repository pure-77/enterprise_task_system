"""文件存储抽象层"""
import os
from pathlib import Path
from fastapi import UploadFile
from app.core.exceptions import BusinessError

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "uploads", "files")

# 文件大小限制: 100MB
MAX_FILE_SIZE = 100 * 1024 * 1024

# 允许的文件扩展名白名单
ALLOWED_EXTENSIONS = {
    # 文档
    ".txt", ".md", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".csv", ".rtf", ".odt", ".ods", ".odp",
    # 图片
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico",
    # 视频
    ".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv",
    # 音频
    ".mp3", ".wav", ".ogg", ".flac", ".aac",
    # 压缩包
    ".zip", ".rar", ".7z", ".tar", ".gz",
    # 代码/文本
    ".json", ".xml", ".yaml", ".yml", ".html", ".css", ".js", ".ts",
    ".py", ".java", ".cpp", ".c", ".go", ".rs", ".sql",
}


class LocalStorage:
    """本地文件存储"""

    def __init__(self, base_dir: str = None):
        self.base_dir = os.path.abspath(base_dir or UPLOAD_DIR)

    def _get_path(self, workspace_id: int, relative_path: str) -> str:
        """安全路径拼接 — 防止路径穿越攻击"""
        # 1. relative_path 必须是纯文件名（UUID生成），不能包含路径分隔符或..
        if not relative_path:
            raise BusinessError("文件名不能为空")

        # 取 basename，剥离任何路径成分
        safe_name = os.path.basename(relative_path)

        # 校验：basename 后必须与原值一致（防止 ../../etc/passwd）
        if safe_name != relative_path:
            raise BusinessError("非法的文件名")

        # 校验：不能包含 .. 或路径分隔符
        if ".." in relative_path or "/" in relative_path or "\\" in relative_path:
            raise BusinessError("非法的文件名")

        # 2. 拼接最终路径并校验是否在 base_dir 内
        full_path = os.path.abspath(
            os.path.join(self.base_dir, str(workspace_id), safe_name)
        )

        # 关键安全校验：最终路径必须在 base_dir 之下
        base_with_workspace = os.path.abspath(
            os.path.join(self.base_dir, str(workspace_id))
        )
        if not full_path.startswith(base_with_workspace + os.sep):
            raise BusinessError("非法的文件路径")

        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        return full_path

    def _validate_file(self, file: UploadFile, content: bytes):
        """校验文件大小和扩展名"""
        # 文件大小校验
        if len(content) > MAX_FILE_SIZE:
            raise BusinessError(f"文件大小超过限制（最大 {MAX_FILE_SIZE // 1024 // 1024}MB）")

        # 文件扩展名校验
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext and ext not in ALLOWED_EXTENSIONS:
            raise BusinessError(f"不支持的文件类型: {ext}")

    async def upload(self, file: UploadFile, workspace_id: int,
                     relative_path: str) -> int:
        """保存文件并返回大小 — 含安全校验"""
        full_path = self._get_path(workspace_id, relative_path)
        content = await file.read()
        self._validate_file(file, content)

        with open(full_path, "wb") as f:
            f.write(content)
        return len(content)

    def delete(self, workspace_id: int, relative_path: str):
        full_path = self._get_path(workspace_id, relative_path)
        if os.path.exists(full_path):
            os.remove(full_path)

    def get_url(self, workspace_id: int, relative_path: str) -> str:
        # URL 中使用 basename 防止路径穿越
        safe_name = os.path.basename(relative_path)
        return f"/uploads/files/{workspace_id}/{safe_name}"


storage = LocalStorage()
