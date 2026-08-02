import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from io import BytesIO
from typing import List, Dict, Any

class ExcelExporter:
    """Excel导出器 - 面试考点：使用openpyxl生成Excel文件"""
    
    @staticmethod
    def export_tasks(tasks: List[Dict[str, Any]]) -> BytesIO:
        """导出任务列表到Excel - 面试考点：Excel文件生成"""
        # 创建工作簿
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "任务列表"
        
        # 定义表头
        headers = ["ID", "标题", "描述", "分类", "状态", "优先级", "截止日期", "创建时间", "更新时间"]
        
        # 设置表头样式
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="409EFF", end_color="409EFF", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        # 写入表头
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        # 写入数据
        for row, task in enumerate(tasks, 2):
            ws.cell(row=row, column=1, value=task.get("id", ""))
            ws.cell(row=row, column=2, value=task.get("title", ""))
            ws.cell(row=row, column=3, value=task.get("description", ""))
            ws.cell(row=row, column=4, value=task.get("category", ""))
            ws.cell(row=row, column=5, value=task.get("status", ""))
            ws.cell(row=row, column=6, value=task.get("priority", ""))
            ws.cell(row=row, column=7, value=task.get("due_date", ""))
            ws.cell(row=row, column=8, value=task.get("created_at", ""))
            ws.cell(row=row, column=9, value=task.get("updated_at", ""))
        
        # 调整列宽
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col)].auto_size = True
        
        # 保存到BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        return output


# 导出Excel文件的工具函数
def export_tasks_to_excel(tasks: List[Dict[str, Any]]) -> BytesIO:
    """导出任务到Excel - 面试考点：封装Excel导出功能"""
    return ExcelExporter.export_tasks(tasks)