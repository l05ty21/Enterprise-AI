"""集中导入所有 ORM 模型。

Alembic 与 ``Base.metadata.create_all`` 都依赖这里的导入来发现全部表。
"""

from app.models.approval import ApprovalInstance, ApprovalTask, ApprovalTemplate
from app.models.attachment import Attachment
from app.models.chat import AIModelConfig, AIUsageLog, ChatMessage, Conversation
from app.models.knowledge import Document, DocumentChunk, KnowledgeBase
from app.models.organization import Department, Organization
from app.models.project import Project, Task, TaskComment
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.system import LoginLog, Notification, OperationLog
from app.models.ticket import Ticket, TicketComment, TicketHistory
from app.models.user import User

__all__ = [
    "Organization",
    "Department",
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    "KnowledgeBase",
    "Document",
    "DocumentChunk",
    "Conversation",
    "ChatMessage",
    "AIModelConfig",
    "AIUsageLog",
    "Ticket",
    "TicketComment",
    "TicketHistory",
    "ApprovalTemplate",
    "ApprovalInstance",
    "ApprovalTask",
    "Attachment",
    "Project",
    "Task",
    "TaskComment",
    "Notification",
    "OperationLog",
    "LoginLog",
]
