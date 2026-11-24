"""权限点与内置角色的定义。种子脚本和前端菜单都以这里为准。"""

from __future__ import annotations

from typing import Final

SUPER_ADMIN_ROLE_CODE: Final[str] = "super_admin"

# (code, name, type) —— type: menu 菜单 / button 按钮 / api 接口
PERMISSION_DEFINITIONS: Final[list[tuple[str, str, str]]] = [
    ("menu:dashboard", "工作台", "menu"),
    ("menu:organization", "组织管理", "menu"),
    ("menu:user", "用户管理", "menu"),
    ("menu:role", "角色管理", "menu"),
    ("menu:department", "部门管理", "menu"),
    ("menu:knowledge", "知识库", "menu"),
    ("menu:ticket", "工单管理", "menu"),
    ("menu:approval", "审批管理", "menu"),
    ("menu:project", "项目管理", "menu"),
    ("menu:system", "系统管理", "menu"),
    ("user:read", "查看用户", "api"),
    ("user:create", "创建用户", "button"),
    ("user:update", "编辑用户", "button"),
    ("user:delete", "禁用用户", "button"),
    ("role:read", "查看角色", "api"),
    ("role:create", "创建角色", "button"),
    ("role:update", "编辑角色", "button"),
    ("role:delete", "删除角色", "button"),
    ("department:read", "查看部门", "api"),
    ("department:create", "创建部门", "button"),
    ("department:update", "编辑部门", "button"),
    ("department:delete", "删除部门", "button"),
    ("knowledge:read", "查看知识库", "api"),
    ("knowledge:create", "创建知识库", "button"),
    ("knowledge:update", "编辑知识库", "button"),
    ("knowledge:delete", "删除知识库", "button"),
    ("ticket:read", "查看工单", "api"),
    ("ticket:create", "创建工单", "button"),
    ("ticket:update", "处理工单", "button"),
    ("ticket:delete", "删除工单", "button"),
    ("approval:read", "查看审批", "api"),
    ("approval:create", "发起审批", "button"),
    ("approval:approve", "审批操作", "button"),
    ("project:read", "查看项目", "api"),
    ("project:manage", "管理项目", "button"),
    ("system:log:read", "查看审计日志", "api"),
    ("system:config", "系统配置", "api"),
    ("ai:chat", "AI 对话", "api"),
]

ALL_PERMISSION_CODES: Final[list[str]] = [code for code, _, _ in PERMISSION_DEFINITIONS]

# 内置角色。permissions 为 None 表示拥有全部权限。
ROLE_PRESETS: Final[dict[str, dict]] = {
    "super_admin": {
        "name": "超级管理员",
        "description": "拥有系统全部权限，可跨企业维护数据",
        "permissions": None,
    },
    "org_admin": {
        "name": "企业管理员",
        "description": "管理本企业的用户、角色、部门与业务数据",
        "permissions": None,
    },
    "dept_manager": {
        "name": "部门经理",
        "description": "查看本部门成员，处理工单与审批",
        "permissions": [
            "menu:dashboard",
            "menu:organization",
            "menu:user",
            "menu:department",
            "menu:ticket",
            "menu:approval",
            "menu:project",
            "menu:knowledge",
            "user:read",
            "department:read",
            "ticket:read",
            "ticket:create",
            "ticket:update",
            "approval:read",
            "approval:create",
            "approval:approve",
            "project:read",
            "project:manage",
            "knowledge:read",
            "ai:chat",
        ],
    },
    "employee": {
        "name": "普通员工",
        "description": "查看组织架构与同事，提交工单、发起审批、使用 AI 助手与知识库（组织管理只读）",
        "permissions": [
            "menu:dashboard",
            "menu:organization",
            "menu:user",
            "menu:department",
            "menu:ticket",
            "menu:approval",
            "menu:project",
            "menu:knowledge",
            # 组织管理只读：能看通讯录和部门树，但没有任何 create / update / delete
            "user:read",
            "department:read",
            "ticket:read",
            "ticket:create",
            "approval:read",
            "approval:create",
            "project:read",
            "knowledge:read",
            "ai:chat",
        ],
    },
}
