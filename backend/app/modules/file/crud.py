"""文件管理模块 — CRUD"""
import os
from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.modules.file.models import FileFolder, File
from app.modules.file.storage import storage
from app.core.exceptions import ResourceNotFoundError, BusinessError


class FileCRUD:

    # ===== Folder =====

    def get_folders(self, db: Session, workspace_id: int, parent_id: int = None) -> list[FileFolder]:
        return db.query(FileFolder).filter(
            FileFolder.workspace_id == workspace_id,
            FileFolder.parent_id == parent_id,
            FileFolder.is_active == True
        ).order_by(FileFolder.name).all()

    def get_folder(self, db: Session, folder_id: int) -> FileFolder:
        f = db.query(FileFolder).filter(
            FileFolder.id == folder_id, FileFolder.is_active == True
        ).first()
        if not f:
            raise ResourceNotFoundError(resource="文件夹")
        return f

    def create_folder(self, db: Session, workspace_id: int, name: str,
                      parent_id: int = None, created_by: int = None) -> FileFolder:
        f = FileFolder(workspace_id=workspace_id, name=name,
                       parent_id=parent_id, created_by=created_by)
        db.add(f)
        db.commit()
        db.refresh(f)
        return f

    def delete_folder(self, db: Session, folder_id: int):
        f = self.get_folder(db, folder_id)
        # 检查文件夹是否为空
        has_files = db.query(File).filter(
            File.folder_id == folder_id, File.is_active == True
        ).count()
        has_subfolders = db.query(FileFolder).filter(
            FileFolder.parent_id == folder_id, FileFolder.is_active == True
        ).count()
        if has_files > 0 or has_subfolders > 0:
            raise BusinessError("文件夹不为空，无法删除")
        f.is_active = False
        db.commit()

    # ===== File =====

    def get_files(self, db: Session, workspace_id: int, folder_id: int = None,
                  page: int = 1, page_size: int = 50) -> dict:
        q = db.query(File).filter(
            File.workspace_id == workspace_id,
            File.is_active == True
        )
        if folder_id is not None:
            q = q.filter(File.folder_id == folder_id)

        total = q.count()
        items = q.order_by(File.created_at.desc()).offset(
            (page - 1) * page_size).limit(page_size).all()

        return {
            "items": [{
                "id": f.id, "name": f.name, "size": f.size,
                "mime_type": f.mime_type, "version": f.version,
                "folder_id": f.folder_id,
                "uploader_name": f.uploader.nickname if f.uploader else None,
                "url": f"/uploads/files/{f.workspace_id}/{f.path}",
                "created_at": f.created_at.isoformat() if f.created_at else None,
            } for f in items],
            "total": total, "page": page, "page_size": page_size
        }

    async def upload_file(self, db: Session, workspace_id: int, uploader_id: int,
                          file: UploadFile, folder_id: int = None) -> File:
        # 生成存储路径
        import uuid
        ext = os.path.splitext(file.filename or "unknown")[1]
        relative_path = f"{uuid.uuid4().hex}{ext}"

        size = await storage.upload(file, workspace_id, relative_path)

        f = File(workspace_id=workspace_id, folder_id=folder_id,
                uploader_id=uploader_id, name=file.filename or "unknown",
                size=size, mime_type=file.content_type,
                path=relative_path)
        db.add(f)
        db.commit()
        db.refresh(f)
        return f

    def get_file(self, db: Session, file_id: int) -> File:
        f = db.query(File).filter(
            File.id == file_id, File.is_active == True
        ).first()
        if not f:
            raise ResourceNotFoundError(resource="文件")
        return f

    def delete_file(self, db: Session, file_id: int):
        f = self.get_file(db, file_id)
        storage.delete(f.workspace_id, f.path)
        f.is_active = False
        db.commit()

    def move_file(self, db: Session, file_id: int, folder_id: int = None):
        f = self.get_file(db, file_id)
        if folder_id:
            self.get_folder(db, folder_id)  # 验证目标文件夹存在
        f.folder_id = folder_id
        db.commit()
        db.refresh(f)
        return f


file_crud = FileCRUD()
