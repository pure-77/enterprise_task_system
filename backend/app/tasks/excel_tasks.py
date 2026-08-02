import json
import os
from datetime import datetime
from io import BytesIO
from sqlalchemy.orm import Session
from app.db.session import get_db_session
from app.models.task import Task
from app.models.category import Category
from app.models.tag import Tag
from app.core.celery_config import celery_app
from app.utils.excel_exporter import export_tasks_to_excel
from app.crud.statistics import statistics

EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'temp_exports')


@celery_app.task
def export_tasks_to_excel_async(user_id: int):
    """异步导出任务到 Excel"""
    db = get_db_session()
    try:
        tasks = statistics.get_export_data(db, user_id)
        excel_file = export_tasks_to_excel(tasks)

        os.makedirs(EXPORT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'tasks_export_{user_id}_{timestamp}.xlsx'
        filepath = os.path.join(EXPORT_DIR, filename)

        with open(filepath, 'wb') as f:
            f.write(excel_file.getvalue())

        return {
            "status": "success",
            "message": "Excel 导出成功",
            "file_path": filepath,
            "file_name": filename,
            "file_size": excel_file.getbuffer().nbytes
        }
    finally:
        db.close()


@celery_app.task
def import_tasks_from_json_async(user_id: int, file_content: str):
    """异步导入任务数据"""
    db = get_db_session()
    try:
        import_data = json.loads(file_content)
        import_count = 0
        
        # 导入分类
        category_map = {}
        for category_data in import_data.get('categories', []):
            try:
                existing_category = db.query(Category).filter(
                    Category.user_id == user_id,
                    Category.name == category_data['name'],
                    Category.is_active == True
                ).first()
                
                if existing_category:
                    category_map[category_data['id']] = existing_category.id
                else:
                    new_category = Category(
                        name=category_data['name'],
                        color=category_data.get('color', '#409EFF'),
                        user_id=user_id
                    )
                    db.add(new_category)
                    db.commit()
                    db.refresh(new_category)
                    category_map[category_data['id']] = new_category.id
            except Exception as e:
                print(f"导入分类失败: {e}")
                continue
        
        # 导入标签
        tag_map = {}
        for tag_data in import_data.get('tags', []):
            try:
                existing_tag = db.query(Tag).filter(
                    Tag.user_id == user_id,
                    Tag.name == tag_data['name'],
                    Tag.is_active == True
                ).first()
                
                if existing_tag:
                    tag_map[tag_data['id']] = existing_tag.id
                else:
                    new_tag = Tag(
                        name=tag_data['name'],
                        color=tag_data.get('color', '#409EFF'),
                        user_id=user_id
                    )
                    db.add(new_tag)
                    db.commit()
                    db.refresh(new_tag)
                    tag_map[tag_data['id']] = new_tag.id
            except Exception as e:
                print(f"导入标签失败: {e}")
                continue
        
        # 导入任务
        for task_data in import_data.get('tasks', []):
            try:
                category_id = category_map.get(task_data.get('category_id'))
                if not category_id:
                    first_category = db.query(Category).filter(
                        Category.user_id == user_id,
                        Category.is_active == True
                    ).first()
                    category_id = first_category.id if first_category else None
                
                if not category_id:
                    continue
                
                new_task = Task(
                    title=task_data['title'],
                    description=task_data.get('description'),
                    due_date=task_data.get('due_date'),
                    status=task_data.get('status', 'pending'),
                    priority=task_data.get('priority', 'medium'),
                    user_id=user_id,
                    category_id=category_id
                )
                db.add(new_task)
                db.commit()
                db.refresh(new_task)
                
                # 添加标签关联
                for tag_id in task_data.get('tags', []):
                    mapped_tag_id = tag_map.get(tag_id)
                    if mapped_tag_id:
                        from app.models.task_tags import task_tags
                        db.execute(
                            task_tags.insert().values(
                                task_id=new_task.id,
                                tag_id=mapped_tag_id
                            )
                        )
                
                import_count += 1
            except Exception as e:
                print(f"导入任务失败: {e}")
                continue
        
        return {
            "status": "success",
            "message": "数据导入成功",
            "imported_tasks": import_count
        }
    finally:
        db.close()