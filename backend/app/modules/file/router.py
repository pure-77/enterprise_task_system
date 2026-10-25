"""文件管理模块 — API 路由"""
import os
import hmac
import hashlib
import time
import logging
from fastapi import APIRouter, Depends, Query, UploadFile, File as FastAPIFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.core.permissions import get_workspace_member
from app.models.user import User
from app.modules.file.crud import file_crud
from app.modules.file.schemas import FolderCreate, FileMove
from app.modules.file.storage import storage

router = APIRouter()

logger = logging.getLogger(__name__)


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
    background_tasks: BackgroundTasks,
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

    # RAG：后台异步索引进知识库（失败不影响上传结果）
    try:
        from app.modules.knowledge.indexer import index_source
        background_tasks.add_task(index_source, "file", f.id)
    except Exception as e:
        logger.warning(f"知识库索引进队失败（不影响上传）: {e}")

    return {"id": f.id, "name": f.name, "size": f.size, "mime_type": f.mime_type}


@router.delete("/{file_id}")
async def delete_file(
    background_tasks: BackgroundTasks,
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    f = file_crud.get_file(db, file_id)
    get_workspace_member(f.workspace_id, current_user.id, db)
    file_crud.delete_file(db, file_id)

    # RAG：后台异步清理该文件的向量与分片元数据
    try:
        from app.modules.knowledge.indexer import delete_source_index
        background_tasks.add_task(delete_source_index, "file", file_id)
    except Exception as e:
        logger.warning(f"知识库索引清理入队失败（不影响删除）: {e}")

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


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    mode: str = Query("inline", description="inline=预览, attachment=下载"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """文件下载/预览接口 — 带权限校验"""
    f = file_crud.get_file(db, file_id)
    get_workspace_member(f.workspace_id, current_user.id, db)

    full_path = storage._get_path(f.workspace_id, f.path)
    if not os.path.exists(full_path):
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(resource="文件")

    is_inline = mode == "inline"
    media_type = f.mime_type or "application/octet-stream"

    return FileResponse(
        path=full_path,
        filename=f.name,
        media_type=media_type,
        headers={
            "Content-Disposition": f'{"inline" if is_inline else "attachment"}; filename="{f.name}"'
        }
    )


@router.get("/{file_id}/preview-pdf")
async def preview_pdf(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Office文档预览 - 转换为PDF后返回"""
    from app.modules.file.converter import converter
    from pathlib import Path as PathLib
    import logging
    logger = logging.getLogger(__name__)

    f = file_crud.get_file(db, file_id)
    get_workspace_member(f.workspace_id, current_user.id, db)

    # 检查是否为Office文件
    if not converter.is_office_file(f.name):
        raise HTTPException(status_code=400, detail="仅支持Office文档转换")

    full_path = storage._get_path(f.workspace_id, f.path)
    if not os.path.exists(full_path):
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(resource="文件")

    try:
        # 使用带缓存的转换
        pdf_path = converter.convert_to_pdf_cached(full_path, file_id, f.name)

        # 返回PDF文件
        pdf_name = f"{PathLib(f.name).stem}.pdf"
        return FileResponse(
            path=pdf_path,
            filename=pdf_name,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{pdf_name}"'
            }
        )
    except Exception as e:
        logger.error(f"Office文档转换失败: {e}")
        raise HTTPException(status_code=500, detail=f"文档转换失败: {str(e)}")


@router.get("/{file_id}/preview-tencent")
async def preview_tencent(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """腾讯云数据万象文档预览"""
    from app.modules.file.cos_storage import cos_storage
    from app.core.cos_config import cos_config
    import logging
    logger = logging.getLogger(__name__)

    # 检查COS是否已配置
    if not cos_config.is_configured:
        raise HTTPException(status_code=500, detail="腾讯云COS未配置")

    f = file_crud.get_file(db, file_id)
    get_workspace_member(f.workspace_id, current_user.id, db)

    # 检查是否为Office文件
    from app.modules.file.converter import converter
    if not converter.is_office_file(f.name):
        raise HTTPException(status_code=400, detail="仅支持Office文档预览")

    full_path = storage._get_path(f.workspace_id, f.path)
    if not os.path.exists(full_path):
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(resource="文件")

    try:
        # 构建COS Key
        cos_key = f"files/{f.workspace_id}/{f.name}"

        # 上传文件到COS（如果已存在会覆盖）
        cos_storage.upload_file(full_path, cos_key, f.mime_type)

        # 获取预览URL
        preview_url = cos_storage.get_preview_url(cos_key, "html")

        return {
            "preview_url": preview_url,
            "file_name": f.name
        }

    except Exception as e:
        logger.error(f"腾讯云预览失败: {e}")
        raise HTTPException(status_code=500, detail=f"预览失败: {str(e)}")


# ===== 签名临时 URL（用于 Office 在线预览等需要免鉴权访问的场景） =====

def _sign_token(file_id: int, expires: int) -> str:
    """生成 HMAC 签名（用动态 JWT 密钥，与 JWT 签名同 key）"""
    from app.core.config import get_jwt_secret
    msg = f"{file_id}:{expires}".encode()
    return hmac.new(get_jwt_secret().encode(), msg, hashlib.sha256).hexdigest()


@router.get("/{file_id}/signed-url")
async def get_signed_url(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """生成带签名的临时下载 URL（10 分钟有效），用于 Office 在线预览等场景"""
    f = file_crud.get_file(db, file_id)
    get_workspace_member(f.workspace_id, current_user.id, db)

    expires = int(time.time()) + 600  # 10 分钟
    sig = _sign_token(file_id, expires)

    # 返回完整的相对路径 URL，前端拼接域名即可
    return {
        "url": f"/api/v1/files/preview/{file_id}?expires={expires}&sig={sig}",
        "expires": expires
    }


@router.get("/preview/{file_id}")
async def preview_file_signed(
    file_id: int,
    expires: int = Query(...),
    sig: str = Query(...),
    db: Session = Depends(get_db)
):
    """免鉴权的签名文件下载 — 仅供第三方文档预览服务调用"""
    # 验证签名
    expected = _sign_token(file_id, expires)
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=403, detail="签名无效")

    # 验证过期
    if int(time.time()) > expires:
        raise HTTPException(status_code=410, detail="链接已过期")

    f = file_crud.get_file(db, file_id)
    if not f:
        raise HTTPException(status_code=404, detail="文件不存在")

    full_path = storage._get_path(f.workspace_id, f.path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    media_type = f.mime_type or "application/octet-stream"
    return FileResponse(
        path=full_path,
        filename=f.name,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{f.name}"',
            "Access-Control-Allow-Origin": "*",
        }
    )
