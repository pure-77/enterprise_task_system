"""文件管理模块 — API 路由"""
from fastapi import APIRouter, Depends, Query, UploadFile, File as FastAPIFile
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user
from app.core.permissions import get_workspace_member
from app.models.user import User
from app.modules.file.crud import file_crud
from app.modules.file.schemas import FolderCreate, FileMove

router = APIRouter()


# ===== Folder =====

@router.get("/folders")
async def get_folders(
    workspace_id: int = Query(None),
    parent_id: int = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_workspace_member(workspace_id, current_user.id, db)
    folders = file_crud.get_folders(db, workspace_id, parent_id)
    return [{"id": f.id, "name": f.name, "parent_id": f.parent_id,
             "created_at": f.created_at.isoformat() if f.created_at else None}
            for f in folders]


@router.post("/folders", status_code=201)
async def create_folder(
    body: FolderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_workspace_member(body.workspace_id, current_user.id, db)
    f = file_crud.create_folder(db, body.workspace_id, body.name, body.parent_id, current_user.id)
    return {"id": f.id, "name": f.name, "parent_id": f.parent_id}


@router.delete("/folders/{folder_id}")
async def delete_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    f = file_crud.get_folder(db, folder_id)
    get_workspace_member(f.workspace_id, current_user.id, db)
    file_crud.delete_folder(db, folder_id)
    return {"message": "文件夹已删除"}


# ===== File =====

@router.get("")
async def get_files(
    workspace_id: int = Query(None),
    folder_id: int = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_workspace_member(workspace_id, current_user.id, db)
    return file_crud.get_files(db, workspace_id, folder_id, page, page_size)


@router.post("/upload", status_code=201)
async def upload_file(
    workspace_id: int = Query(None),
    folder_id: int = Query(None),
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_workspace_member(workspace_id, current_user.id, db)
    # 限制大小 50MB
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        from app.core.exceptions import BusinessError
        raise BusinessError("文件大小不能超过 50MB")
    file.file.seek(0)  # 重置文件指针

    f = await file_crud.upload_file(db, workspace_id, current_user.id, file, folder_id)
    return {"id": f.id, "name": f.name, "size": f.size, "mime_type": f.mime_type}


@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    f = file_crud.get_file(db, file_id)
    get_workspace_member(f.workspace_id, current_user.id, db)
    file_crud.delete_file(db, file_id)
    return {"message": "文件已删除"}


@router.put("/{file_id}/move")
async def move_file(
    file_id: int,
    body: FileMove,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    f = file_crud.get_file(db, file_id)
    get_workspace_member(f.workspace_id, current_user.id, db)
    f = file_crud.move_file(db, file_id, body.folder_id)
    return {"id": f.id, "folder_id": f.folder_id}
