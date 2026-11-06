"""Agent 服务门面 — 按 AGENT_ENGINE 开关分发到具体引擎

对外签名与迁移前完全一致（router.py / 基线 runner 零改动）：
  - engine=legacy    → app.modules.agent.legacy.service.AgentService（原实现）
  - engine=langgraph → app.modules.agent.graph.runner.LangGraphAgentService（P2 新增）
"""
import logging
from typing import Optional

from app.models.user import User
from app.modules.agent.config_flags import get_engine
from app.modules.agent.schemas import AgentChatResponse

logger = logging.getLogger("agent.service.facade")


class AgentService:
    """Agent 核心服务门面 — 单次对话编排器的稳定入口"""

    def __init__(
        self,
        user: User,
        workspace_id: Optional[int] = None,
        session_id: Optional[str] = None,
    ):
        self.user = user
        self.workspace_id = workspace_id
        self.session_id = session_id
        self._engine_name = get_engine()
        if self._engine_name == "langgraph":
            from app.modules.agent.graph.runner import LangGraphAgentService
            self._impl = LangGraphAgentService(user, workspace_id, session_id)
        else:
            from app.modules.agent.legacy.service import AgentService as LegacyAgentService
            self._impl = LegacyAgentService(user, workspace_id, session_id)
        logger.info(
            f"[AgentFacade] engine={self._engine_name}, user={user.id}, ws={workspace_id}, session={session_id}"
        )

    async def chat_stream(self, user_message: str, image_url: Optional[str] = None):
        async for event in self._impl.chat_stream(user_message, image_url):
            yield event

    async def chat(self, user_message: str, image_url: Optional[str] = None) -> AgentChatResponse:
        return await self._impl.chat(user_message, image_url)

    async def resume_confirmation(self, approved: bool, thread_id: Optional[str] = None) -> dict:
        """P4: 危险操作确认恢复（仅 langgraph 引擎支持）"""
        impl = getattr(self._impl, "resume_confirmation", None)
        if impl is None:
            raise NotImplementedError(f"engine={self._engine_name} 不支持 interrupt 恢复")
        return await impl(approved, thread_id=thread_id)
