-- =====================================================================
--  智企协同 Enterprise AI · 数据库 V1.0
--  由 scripts/generate_init_sql.py 依据 ORM 模型自动生成，请勿手工修改。
--  重新生成：python scripts/generate_init_sql.py
-- =====================================================================

CREATE DATABASE IF NOT EXISTS enterprise_ai
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE enterprise_ai;

SET NAMES utf8mb4;

-- ---------- organizations ----------
CREATE TABLE organizations (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	name VARCHAR(128) NOT NULL COMMENT '企业名称', 
	code VARCHAR(64) NOT NULL COMMENT '企业编码', 
	status SMALLINT NOT NULL COMMENT '1 启用 / 0 停用' DEFAULT '1', 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_organizations PRIMARY KEY (id), 
	CONSTRAINT uq_organizations_code UNIQUE (code)
);

-- ---------- permissions ----------
CREATE TABLE permissions (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	name VARCHAR(64) NOT NULL, 
	code VARCHAR(128) NOT NULL, 
	type VARCHAR(32) NOT NULL COMMENT 'menu / button / api', 
	parent_id BIGINT UNSIGNED, 
	path VARCHAR(255), 
	method VARCHAR(16), 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_permissions PRIMARY KEY (id), 
	CONSTRAINT uq_permissions_code UNIQUE (code), 
	CONSTRAINT fk_permissions_parent_id_permissions FOREIGN KEY(parent_id) REFERENCES permissions (id)
);

-- ---------- ai_model_configs ----------
CREATE TABLE ai_model_configs (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	organization_id BIGINT UNSIGNED NOT NULL, 
	model_name VARCHAR(128) NOT NULL, 
	provider VARCHAR(64) NOT NULL COMMENT 'openai / azure / ollama / qwen ...', 
	model_type VARCHAR(32) NOT NULL COMMENT 'llm / embedding / rerank', 
	base_url VARCHAR(512), 
	api_key_encrypted LONGTEXT, 
	is_default BOOL NOT NULL DEFAULT '0', 
	is_enabled BOOL NOT NULL DEFAULT '1', 
	parameters JSON, 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_ai_model_configs PRIMARY KEY (id), 
	CONSTRAINT fk_ai_model_configs_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id)
);
CREATE INDEX idx_ai_config_org ON ai_model_configs (organization_id);

-- ---------- approval_templates ----------
CREATE TABLE approval_templates (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	organization_id BIGINT UNSIGNED NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	business_type VARCHAR(64) NOT NULL, 
	flow_config JSON NOT NULL, 
	status SMALLINT NOT NULL DEFAULT '1', 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_approval_templates PRIMARY KEY (id), 
	CONSTRAINT fk_approval_templates_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id)
);

-- ---------- departments ----------
CREATE TABLE departments (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	organization_id BIGINT UNSIGNED NOT NULL, 
	parent_id BIGINT UNSIGNED COMMENT '上级部门', 
	name VARCHAR(128) NOT NULL, 
	leader_id BIGINT UNSIGNED, 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_departments PRIMARY KEY (id), 
	CONSTRAINT fk_departments_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_departments_parent_id_departments FOREIGN KEY(parent_id) REFERENCES departments (id)
);
CREATE INDEX idx_department_org ON departments (organization_id);

-- ---------- roles ----------
CREATE TABLE roles (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	organization_id BIGINT UNSIGNED NOT NULL, 
	name VARCHAR(64) NOT NULL, 
	code VARCHAR(64) NOT NULL, 
	description VARCHAR(255), 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_roles PRIMARY KEY (id), 
	CONSTRAINT uk_role_org_code UNIQUE (organization_id, code), 
	CONSTRAINT fk_roles_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id)
);

-- ---------- role_permissions ----------
CREATE TABLE role_permissions (
	role_id BIGINT UNSIGNED NOT NULL, 
	permission_id BIGINT UNSIGNED NOT NULL, 
	CONSTRAINT pk_role_permissions PRIMARY KEY (role_id, permission_id), 
	CONSTRAINT fk_role_permissions_role_id_roles FOREIGN KEY(role_id) REFERENCES roles (id), 
	CONSTRAINT fk_role_permissions_permission_id_permissions FOREIGN KEY(permission_id) REFERENCES permissions (id)
);

-- ---------- users ----------
CREATE TABLE users (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	organization_id BIGINT UNSIGNED NOT NULL, 
	department_id BIGINT UNSIGNED, 
	username VARCHAR(64) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	real_name VARCHAR(64), 
	email VARCHAR(128), 
	phone VARCHAR(32), 
	avatar VARCHAR(512), 
	status SMALLINT NOT NULL COMMENT '1 正常 / 0 禁用' DEFAULT '1', 
	last_login_at DATETIME, 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_users PRIMARY KEY (id), 
	CONSTRAINT uk_user_org_username UNIQUE (organization_id, username), 
	CONSTRAINT uk_user_org_email UNIQUE (organization_id, email), 
	CONSTRAINT fk_users_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_users_department_id_departments FOREIGN KEY(department_id) REFERENCES departments (id)
);
CREATE INDEX idx_user_department ON users (department_id);

-- ---------- ai_usage_logs ----------
CREATE TABLE ai_usage_logs (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	organization_id BIGINT UNSIGNED NOT NULL, 
	user_id BIGINT UNSIGNED NOT NULL, 
	model_name VARCHAR(128), 
	provider VARCHAR(64), 
	input_tokens INTEGER NOT NULL DEFAULT '0', 
	output_tokens INTEGER NOT NULL DEFAULT '0', 
	latency_ms INTEGER NOT NULL DEFAULT '0', 
	status VARCHAR(32), 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_ai_usage_logs PRIMARY KEY (id), 
	CONSTRAINT fk_ai_usage_logs_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_ai_usage_logs_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX idx_ai_usage_time ON ai_usage_logs (organization_id, created_at);

-- ---------- approval_instances ----------
CREATE TABLE approval_instances (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	organization_id BIGINT UNSIGNED NOT NULL, 
	template_id BIGINT UNSIGNED NOT NULL, 
	applicant_id BIGINT UNSIGNED NOT NULL, 
	business_type VARCHAR(64) NOT NULL, 
	business_data JSON, 
	status VARCHAR(32) NOT NULL DEFAULT 'pending', 
	current_node INTEGER NOT NULL DEFAULT '1', 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_approval_instances PRIMARY KEY (id), 
	CONSTRAINT fk_approval_instances_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_approval_instances_template_id_approval_templates FOREIGN KEY(template_id) REFERENCES approval_templates (id), 
	CONSTRAINT fk_approval_instances_applicant_id_users FOREIGN KEY(applicant_id) REFERENCES users (id)
);

-- ---------- conversations ----------
CREATE TABLE conversations (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	organization_id BIGINT UNSIGNED NOT NULL, 
	user_id BIGINT UNSIGNED NOT NULL, 
	title VARCHAR(255), 
	conversation_type VARCHAR(32) NOT NULL DEFAULT 'chat', 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_conversations PRIMARY KEY (id), 
	CONSTRAINT fk_conversations_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_conversations_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX idx_conversation_user ON conversations (user_id);

-- ---------- knowledge_bases ----------
CREATE TABLE knowledge_bases (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	organization_id BIGINT UNSIGNED NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	description LONGTEXT, 
	owner_id BIGINT UNSIGNED NOT NULL, 
	department_id BIGINT UNSIGNED, 
	visibility VARCHAR(32) NOT NULL COMMENT 'private / department / org' DEFAULT 'private', 
	status SMALLINT NOT NULL DEFAULT '1', 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_knowledge_bases PRIMARY KEY (id), 
	CONSTRAINT fk_knowledge_bases_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_knowledge_bases_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id), 
	CONSTRAINT fk_knowledge_bases_department_id_departments FOREIGN KEY(department_id) REFERENCES departments (id)
);
CREATE INDEX idx_kb_org ON knowledge_bases (organization_id);

-- ---------- login_logs ----------
CREATE TABLE login_logs (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	organization_id BIGINT UNSIGNED NOT NULL, 
	user_id BIGINT UNSIGNED, 
	ip_address VARCHAR(64), 
	user_agent LONGTEXT, 
	status VARCHAR(32), 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_login_logs PRIMARY KEY (id), 
	CONSTRAINT fk_login_logs_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_login_logs_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)
);

-- ---------- notifications ----------
CREATE TABLE notifications (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	organization_id BIGINT UNSIGNED NOT NULL, 
	user_id BIGINT UNSIGNED NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	content LONGTEXT, 
	type VARCHAR(32), 
	is_read BOOL NOT NULL DEFAULT '0', 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_notifications PRIMARY KEY (id), 
	CONSTRAINT fk_notifications_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_notifications_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX idx_notification_user ON notifications (user_id, is_read);

-- ---------- operation_logs ----------
CREATE TABLE operation_logs (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	organization_id BIGINT UNSIGNED NOT NULL, 
	user_id BIGINT UNSIGNED, 
	module VARCHAR(64), 
	action VARCHAR(64), 
	request_method VARCHAR(16), 
	request_path VARCHAR(255), 
	ip_address VARCHAR(64), 
	detail JSON, 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_operation_logs PRIMARY KEY (id), 
	CONSTRAINT fk_operation_logs_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_operation_logs_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX idx_operation_time ON operation_logs (organization_id, created_at);

-- ---------- projects ----------
CREATE TABLE projects (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	organization_id BIGINT UNSIGNED NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	description LONGTEXT, 
	owner_id BIGINT UNSIGNED NOT NULL, 
	status VARCHAR(32) NOT NULL DEFAULT 'active', 
	start_date DATE, 
	end_date DATE, 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_projects PRIMARY KEY (id), 
	CONSTRAINT fk_projects_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_projects_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id)
);

-- ---------- tickets ----------
CREATE TABLE tickets (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	organization_id BIGINT UNSIGNED NOT NULL, 
	ticket_no VARCHAR(64) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	description LONGTEXT, 
	creator_id BIGINT UNSIGNED NOT NULL, 
	assignee_id BIGINT UNSIGNED, 
	priority VARCHAR(32) NOT NULL DEFAULT 'medium', 
	status VARCHAR(32) NOT NULL DEFAULT 'pending', 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL COMMENT '更新时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_tickets PRIMARY KEY (id), 
	CONSTRAINT uk_ticket_no UNIQUE (organization_id, ticket_no), 
	CONSTRAINT fk_tickets_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_tickets_creator_id_users FOREIGN KEY(creator_id) REFERENCES users (id), 
	CONSTRAINT fk_tickets_assignee_id_users FOREIGN KEY(assignee_id) REFERENCES users (id)
);
CREATE INDEX idx_ticket_assignee ON tickets (assignee_id, status);

-- ---------- user_roles ----------
CREATE TABLE user_roles (
	user_id BIGINT UNSIGNED NOT NULL, 
	role_id BIGINT UNSIGNED NOT NULL, 
	CONSTRAINT pk_user_roles PRIMARY KEY (user_id, role_id), 
	CONSTRAINT fk_user_roles_user_id_users FOREIGN KEY(user_id) REFERENCES users (id), 
	CONSTRAINT fk_user_roles_role_id_roles FOREIGN KEY(role_id) REFERENCES roles (id)
);

-- ---------- approval_tasks ----------
CREATE TABLE approval_tasks (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	instance_id BIGINT UNSIGNED NOT NULL, 
	approver_id BIGINT UNSIGNED NOT NULL, 
	node_index INTEGER NOT NULL, 
	status VARCHAR(32) NOT NULL DEFAULT 'pending', 
	comment LONGTEXT, 
	handled_at DATETIME, 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_approval_tasks PRIMARY KEY (id), 
	CONSTRAINT fk_approval_tasks_instance_id_approval_instances FOREIGN KEY(instance_id) REFERENCES approval_instances (id), 
	CONSTRAINT fk_approval_tasks_approver_id_users FOREIGN KEY(approver_id) REFERENCES users (id)
);
CREATE INDEX idx_approval_task ON approval_tasks (approver_id, status);

-- ---------- chat_messages ----------
CREATE TABLE chat_messages (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	conversation_id BIGINT UNSIGNED NOT NULL, 
	`role` VARCHAR(32) NOT NULL COMMENT 'system / user / assistant / tool', 
	content LONGTEXT, 
	model_name VARCHAR(128), 
	token_count INTEGER NOT NULL DEFAULT '0', 
	references_json JSON, 
	tool_calls JSON, 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_chat_messages PRIMARY KEY (id), 
	CONSTRAINT fk_chat_messages_conversation_id_conversations FOREIGN KEY(conversation_id) REFERENCES conversations (id)
);
CREATE INDEX idx_chat_conversation ON chat_messages (conversation_id);

-- ---------- documents ----------
CREATE TABLE documents (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	organization_id BIGINT UNSIGNED NOT NULL, 
	kb_id BIGINT UNSIGNED NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	file_path VARCHAR(512) NOT NULL, 
	file_hash VARCHAR(128), 
	file_type VARCHAR(32), 
	file_size BIGINT UNSIGNED, 
	version INTEGER NOT NULL DEFAULT '1', 
	status VARCHAR(32) NOT NULL DEFAULT 'pending', 
	chunk_count INTEGER NOT NULL DEFAULT '0', 
	error_message LONGTEXT, 
	created_by BIGINT UNSIGNED NOT NULL, 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_documents PRIMARY KEY (id), 
	CONSTRAINT fk_documents_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_documents_kb_id_knowledge_bases FOREIGN KEY(kb_id) REFERENCES knowledge_bases (id), 
	CONSTRAINT fk_documents_created_by_users FOREIGN KEY(created_by) REFERENCES users (id)
);
CREATE INDEX idx_document_kb ON documents (kb_id);
CREATE INDEX idx_document_status ON documents (status);

-- ---------- tasks ----------
CREATE TABLE tasks (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	organization_id BIGINT UNSIGNED NOT NULL, 
	project_id BIGINT UNSIGNED NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	description LONGTEXT, 
	assignee_id BIGINT UNSIGNED, 
	creator_id BIGINT UNSIGNED NOT NULL, 
	priority VARCHAR(32) NOT NULL DEFAULT 'medium', 
	status VARCHAR(32) NOT NULL DEFAULT 'todo', 
	due_date DATETIME, 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_tasks PRIMARY KEY (id), 
	CONSTRAINT fk_tasks_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_tasks_project_id_projects FOREIGN KEY(project_id) REFERENCES projects (id), 
	CONSTRAINT fk_tasks_assignee_id_users FOREIGN KEY(assignee_id) REFERENCES users (id), 
	CONSTRAINT fk_tasks_creator_id_users FOREIGN KEY(creator_id) REFERENCES users (id)
);
CREATE INDEX idx_task_assignee ON tasks (assignee_id, status);

-- ---------- ticket_comments ----------
CREATE TABLE ticket_comments (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	ticket_id BIGINT UNSIGNED NOT NULL, 
	user_id BIGINT UNSIGNED NOT NULL, 
	content LONGTEXT NOT NULL, 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_ticket_comments PRIMARY KEY (id), 
	CONSTRAINT fk_ticket_comments_ticket_id_tickets FOREIGN KEY(ticket_id) REFERENCES tickets (id), 
	CONSTRAINT fk_ticket_comments_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)
);

-- ---------- ticket_histories ----------
CREATE TABLE ticket_histories (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	ticket_id BIGINT UNSIGNED NOT NULL, 
	operator_id BIGINT UNSIGNED NOT NULL, 
	old_status VARCHAR(32), 
	new_status VARCHAR(32), 
	remark LONGTEXT, 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_ticket_histories PRIMARY KEY (id), 
	CONSTRAINT fk_ticket_histories_ticket_id_tickets FOREIGN KEY(ticket_id) REFERENCES tickets (id), 
	CONSTRAINT fk_ticket_histories_operator_id_users FOREIGN KEY(operator_id) REFERENCES users (id)
);

-- ---------- document_chunks ----------
CREATE TABLE document_chunks (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	organization_id BIGINT UNSIGNED NOT NULL, 
	document_id BIGINT UNSIGNED NOT NULL, 
	chunk_index INTEGER NOT NULL, 
	content LONGTEXT NOT NULL, 
	vector_id VARCHAR(128) NOT NULL, 
	collection_name VARCHAR(128) NOT NULL, 
	embedding_model VARCHAR(128), 
	metadata JSON, 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_document_chunks PRIMARY KEY (id), 
	CONSTRAINT uk_document_chunk UNIQUE (document_id, chunk_index), 
	CONSTRAINT uk_vector_id UNIQUE (collection_name, vector_id), 
	CONSTRAINT fk_document_chunks_organization_id_organizations FOREIGN KEY(organization_id) REFERENCES organizations (id), 
	CONSTRAINT fk_document_chunks_document_id_documents FOREIGN KEY(document_id) REFERENCES documents (id)
);

-- ---------- task_comments ----------
CREATE TABLE task_comments (
	id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, 
	task_id BIGINT UNSIGNED NOT NULL, 
	user_id BIGINT UNSIGNED NOT NULL, 
	content LONGTEXT NOT NULL, 
	created_at DATETIME NOT NULL COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_task_comments PRIMARY KEY (id), 
	CONSTRAINT fk_task_comments_task_id_tasks FOREIGN KEY(task_id) REFERENCES tasks (id), 
	CONSTRAINT fk_task_comments_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)
);


-- =====================================================================
--  初始数据请使用种子脚本写入（会自动加密密码、绑定内置角色）：
--      alembic upgrade head
--      python -m app.db.seed
-- =====================================================================
