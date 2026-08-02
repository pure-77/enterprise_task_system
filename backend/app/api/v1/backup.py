import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.task import Task
from app.models.category import Category
from app.models.tag import Tag
from app.api.v1.task import get_current_user_id
from app.utils.excel_exporter import export_tasks_to_excel
from fastapi.responses import StreamingResponse
import json
from io import BytesIO
from app.tasks.excel_tasks import export_tasks_to_excel_async, import_tasks_from_json_async

router = APIRouter()


@router.get("/export/json")
async def export_tasks_json(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """导出任务为JSON - 面试考点：数据备份"""
    # 获取用户的所有任务
    tasks = db.query(Task).filter(
        Task.user_id == user_id,
        Task.is_active == True
    ).all()
    
    # 获取分类和标签信息
    categories = db.query(Category).filter(
        Category.user_id == user_id,
        Category.is_active == True
    ).all()
    
    tags = db.query(Tag).filter(
        Tag.user_id == user_id,
        Tag.is_active == True
    ).all()
    
    # 构建导出数据
    export_data = {
        "tasks": [],
        "categories": [],
        "tags": [],
        "export_time": None
    }
    
    # 添加任务数据
    for task in tasks:
        task_data = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "status": task.status,
            "priority": task.priority,
            "category_id": task.category_id,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "tags": [tag.id for tag in task.tags]
        }
        export_data["tasks"].append(task_data)
    
    # 添加分类数据
    for category in categories:
        category_data = {
            "id": category.id,
            "name": category.name,
            "color": category.color,
            "created_at": category.created_at.isoformat()
        }
        export_data["categories"].append(category_data)
    
    # 添加标签数据
    for tag in tags:
        tag_data = {
            "id": tag.id,
            "name": tag.name,
            "color": tag.color,
            "created_at": tag.created_at.isoformat()
        }
        export_data["tags"].append(tag_data)
    
    # 添加导出时间
    from datetime import datetime
    export_data["export_time"] = datetime.now().isoformat()
    
    # 转换为JSON字符串
    json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
    
    # 返回JSON文件
    return StreamingResponse(
        BytesIO(json_str.encode('utf-8')),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=tasks_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        }
    )


@router.get("/export/excel")
async def export_tasks_excel(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """导出任务到Excel - 面试考点：文件导出接口"""
    from app.crud.statistics import statistics
    
    # 异步处理Excel导出
    task = export_tasks_to_excel_async.delay(user_id)
    
    # 返回任务ID，前端可以通过此ID查询任务状态
    return {
        "message": "Excel 导出任务已启动",
        "task_id": task.id,
    }


@router.post("/import")
async def import_tasks(
    file: UploadFile = File(..., description="备份文件"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """导入任务数据 - 面试考点：数据恢复"""
    # 验证文件类型
    if not file.filename.endswith('.json'):
        raise HTTPException(
            status_code=400,
            detail="只支持JSON格式的备份文件"
        )
    
    # 读取文件内容
    content = await file.read()
    try:
        import_data = json.loads(content.decode('utf-8'))
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="文件格式错误"
        )
    
    # 验证数据结构
    if not isinstance(import_data, dict) or 'tasks' not in import_data:
        raise HTTPException(
            status_code=400,
            detail="备份文件格式不正确"
        )
    
    # 异步处理数据导入
    file_content = content.decode('utf-8')
    task = import_tasks_from_json_async.delay(user_id, file_content)
    
    # 返回任务ID，前端可以通过此ID查询任务状态
    return {
        "message": "数据导入任务已启动",
        "task_id": task.id
    }


@router.get("/task/{task_id}")
async def get_task_status(
    task_id: str,
    user_id: int = Depends(get_current_user_id)
):
    """获取异步任务状态"""
    from app.core.celery_config import celery_app
    # 获取任务的状态
    task = celery_app.AsyncResult(task_id)

    response = {"status": task.state.lower() if task.state else "pending"}

    if task.state == 'PENDING':
        response["message"] = "任务正在处理中"
    elif task.state == 'SUCCESS':
        result = task.get()
        response["message"] = result.get("message", "任务处理成功")
        response["result"] = result
        if result.get("file_path"):
            response["download_url"] = f"/api/v1/backup/download/{task_id}"
    elif task.state == 'FAILURE':
        response["message"] = "任务处理失败"
        response["error"] = str(task.result)
    else:
        response["message"] = f"任务状态: {task.state}"

    return response


@router.get("/download/{task_id}")
async def download_export_file(
    task_id: str,
    user_id: int = Depends(get_current_user_id)
):
    """下载异步导出的文件"""
    from app.core.celery_config import celery_app

    task = celery_app.AsyncResult(task_id)

    if task.state != 'SUCCESS':
        raise HTTPException(status_code=400, detail="文件尚未生成，请等待任务完成")

    result = task.get()
    file_path = result.get('file_path')
    file_name = result.get('file_name', 'export.xlsx')

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在或已过期")

    def iterfile():
        with open(file_path, 'rb') as f:
            yield from f
        try:
            os.remove(file_path)
        except OSError:
            pass

    return StreamingResponse(
        iterfile(),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename={file_name}'}
    )