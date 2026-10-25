"""Agent 模块 — Pydantic Schemas（请求/响应模型）"""
from pydantic import BaseModel, Field
from typing import Optional


# ==================== 请求模型 ====================

class AgentChatMessage(BaseModel):
    """单条对话消息"""
    role: str = Field(..., description="消息角色: user / assistant / system")
    content: str = Field(..., description="消息内容（文本或多模态描述）")
    # 多模态扩展：图片 URL 或 base64
    image_url: Optional[str] = Field(None, description="图片 URL（多模态输入）")


class AgentChatRequest(BaseModel):
    """Agent 对话请求"""
    message: str = Field(..., description="用户当前输入的消息")
    workspace_id: Optional[int] = Field(None, description="当前 workspace ID（工具调用需要）")
    session_id: Optional[str] = Field(None, description="会话 ID（不传则用 user_id 作为 key）")
    reset_memory: bool = Field(False, description="是否清空本次会话记忆")
    # 多模态扩展：图片 URL（传入后走 VL 模型，按 OpenAI content parts 格式组装）
    image_url: Optional[str] = Field(None, description="图片 URL（多模态输入，可选）")


# ==================== 响应模型 ====================

class AgentToolCall(BaseModel):
    """Agent 执行的工具调用记录"""
    tool_name: str
    arguments: dict
    result: Optional[str] = None
    success: bool = True
    error: Optional[str] = None


class AgentChatResponse(BaseModel):
    """Agent 对话响应"""
    model_config = {"protected_namespaces": ()}

    reply: str = Field(..., description="Agent 的自然语言回复")
    tool_calls: list[AgentToolCall] = Field(default_factory=list, description="本次对话执行的工具调用列表")
    thinking: Optional[str] = Field(None, description="思考过程（调试用，可展示给用户）")
    session_id: str = Field(..., description="当前会话 ID")
    model_used: str = Field(..., description="实际使用的模型名称")


# ==================== 任务规划（plan_tasks）确认模型 ====================

class PlanConfirmRequest(BaseModel):
    """任务计划确认请求：用户在前端卡片勾选后提交"""
    session_id: Optional[str] = Field(None, description="当前会话 key（用于把确认结果回写到同一会话）")
    task_indexes: Optional[list[int]] = Field(
        None,
        description="勾选要创建的任务下标（对应 plan_tasks 返回 tasks 中的 index）；不传或 null 表示全部",
    )


# ==================== 危险操作二次确认（danger 工具中断）模型 ====================

class ActionConfirmRequest(BaseModel):
    """危险操作确认请求：danger 级工具执行前被挂起，用户在前端卡片确认/取消后提交"""
    confirm_id: str = Field(..., description="待确认操作 ID（service 挂起危险工具时生成）")
    approved: bool = Field(..., description="true=确认执行；false=取消，不执行")
    session_id: Optional[str] = Field(None, description="当前会话 key（用于把确认结果回写到同一会话）")
