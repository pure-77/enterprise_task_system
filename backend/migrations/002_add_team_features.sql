-- ==========================================
-- 任务系统 v2 数据库迁移
-- 新增：is_team_wide 字段、task_completions 表、task_assignees 表
-- 执行前请备份数据库
-- ==========================================

-- 1. tasks 表新增 is_team_wide 字段
-- 团队公开任务标记，全员可见可编辑
ALTER TABLE tasks
    ADD COLUMN is_team_wide BOOLEAN DEFAULT FALSE
    COMMENT '团队公开任务，全员可见可编辑';

-- 2. 新建 task_completions 表
-- 团队任务完成追踪，每个成员一条记录
CREATE TABLE IF NOT EXISTS task_completions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    task_id     INT          NOT NULL COMMENT '任务ID',
    user_id     INT          NOT NULL COMMENT '完成人ID',
    completed_at DATETIME    DEFAULT CURRENT_TIMESTAMP COMMENT '完成时间',
    created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active   BOOLEAN      DEFAULT TRUE,

    CONSTRAINT fk_completion_task
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    CONSTRAINT fk_completion_user
        FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT uk_task_user
        UNIQUE KEY (task_id, user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='团队任务完成记录';

-- 3. 新建 task_assignees 中间表
-- 任务多人分配（M2M）
CREATE TABLE IF NOT EXISTS task_assignees (
    task_id     INT NOT NULL COMMENT '任务ID',
    user_id     INT NOT NULL COMMENT '被分配人ID',

    PRIMARY KEY (task_id, user_id),
    CONSTRAINT fk_assignee_task
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    CONSTRAINT fk_assignee_user
        FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务多人分配';
