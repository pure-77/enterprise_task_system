"""IM 文件存储模块 — 复用文件管理的 LocalStorage"""
from app.modules.file.storage import LocalStorage, MAX_FILE_SIZE

storage = LocalStorage(base_dir=None)


ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico'}
ALLOWED_FILE_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                           '.txt', '.md', '.csv', '.zip', '.rar', '.mp4', '.mp3',
                           '.json', '.xml', '.html', '.css', '.js', '.py'}

IM_IMAGE_MAX_SIZE = 10 * 1024 * 1024
IM_FILE_MAX_SIZE = 50 * 1024 * 1024


def is_image(ext: str) -> bool:
    return ext.lower() in ALLOWED_IMAGE_EXTENSIONS


def is_file(ext: str) -> bool:
    return ext.lower() in ALLOWED_FILE_EXTENSIONS
