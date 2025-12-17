-- ============================================
-- 系统配置数据库初始化脚本 (system.db)
-- 用途：存储系统配置、日志、用户权限等辅助数据
-- 版本: 2.0
-- 创建日期: 2024-12-01
-- ============================================

-- ============================================
-- 1. 用户表 (users)
-- 用途: 登录认证和权限管理
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,        -- 用户名
    password_hash VARCHAR(255) NOT NULL,         -- 密码哈希（bcrypt）
    full_name VARCHAR(100),                      -- 真实姓名
    role VARCHAR(20) NOT NULL CHECK(role IN ('user', 'admin', 'developer')),
    is_active BOOLEAN DEFAULT 1,                 -- 是否启用
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,                         -- 最后登录时间
    created_by INTEGER,                          -- 创建人ID
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- 用户表索引
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- ============================================
-- 2. 系统日志表 (system_logs)
-- 用途: 记录系统运行日志（log_interceptor写入这里）
-- ============================================
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level VARCHAR(10),                           -- INFO/WARN/ERROR/DEBUG
    message TEXT,
    source VARCHAR(100),                         -- 日志来源模块
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 系统日志表索引
CREATE INDEX IF NOT EXISTS idx_system_logs_level_time ON system_logs(level, created_at);
CREATE INDEX IF NOT EXISTS idx_system_logs_time ON system_logs(created_at);

-- ============================================
-- 3. 操作日志表 (operation_logs)
-- 用途: 记录用户操作审计日志
-- ============================================
CREATE TABLE IF NOT EXISTS operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,                             -- 操作用户ID
    username VARCHAR(50),                        -- 操作用户名
    action VARCHAR(50) NOT NULL,                 -- 操作类型（用户登录、创建批次等）
    target_type VARCHAR(50),                     -- 目标类型（batch/user/customer等）
    target_id INTEGER,                           -- 目标ID
    details TEXT,                                -- 操作详情（JSON格式）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 操作日志表索引
CREATE INDEX IF NOT EXISTS idx_operation_logs_user ON operation_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_operation_logs_action ON operation_logs(action);
CREATE INDEX IF NOT EXISTS idx_operation_logs_time ON operation_logs(created_at);

-- ============================================
-- 4. UI配置表 (ui_settings)
-- 用途: 存储UI相关的所有配置（替代config.json）
-- ============================================
CREATE TABLE IF NOT EXISTS ui_settings (
    key TEXT PRIMARY KEY,                    -- 配置键（唯一）
    value TEXT NOT NULL,                     -- 配置值（JSON格式）
    category TEXT NOT NULL,                  -- 配置分类: auth/scanner/batch/print
    data_type TEXT NOT NULL,                 -- 数据类型: string/int/float/bool/json
    description TEXT,                        -- 配置说明
    is_sensitive BOOLEAN DEFAULT 0,          -- 是否敏感数据（加密存储）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- UI配置表索引
CREATE INDEX IF NOT EXISTS idx_ui_settings_category ON ui_settings(category);

-- ============================================
-- 4. 备份配置表 (backup_config)
-- 用途: 自动备份配置（单例表）
-- ============================================
CREATE TABLE IF NOT EXISTS backup_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),       -- 单例表，只有一条记录
    backup_enabled BOOLEAN DEFAULT 1,
    backup_interval VARCHAR(20) DEFAULT 'weekly',
    backup_day INTEGER DEFAULT 0,                -- 周几备份（0=周日）
    backup_time TIME DEFAULT '02:00:00',
    max_backups INTEGER DEFAULT 1,               -- 保留备份数量
    last_backup DATETIME,
    backup_path VARCHAR(255) DEFAULT './数据库备份/'
);

-- 插入默认备份配置
INSERT OR IGNORE INTO backup_config (id) VALUES (1);

-- ============================================
-- 操作日志初始化
-- ============================================
-- 注：操作日志表为空表，由系统运行时自动写入
-- 所有用户操作（登录、创建批次、修改用户等）都会记录到此表

-- ============================================
-- 初始化UI配置默认值
-- ============================================

-- A. 设备认证配置（初始为空，由激活流程写入）
INSERT OR IGNORE INTO ui_settings (key, value, category, data_type, description, is_sensitive) VALUES
('device_id', '', 'auth', 'string', '设备唯一标识（硬件指纹）', 1),
('device_rand', '', 'auth', 'string', '设备随机码', 1),
('uuid_ref', '', 'auth', 'string', 'UUID引用', 1),
('license_key', '', 'auth', 'string', '许可证密钥', 1);

-- B. PLC设备设置
INSERT OR IGNORE INTO ui_settings (key, value, category, data_type, description) VALUES
('device_plc_ip', '192.168.0.5', 'device', 'string', 'PLC设备IP地址'),
('device_plc_port', '502', 'device', 'string', 'PLC设备端口号');

-- C. 扫码器设备设置
INSERT OR IGNORE INTO ui_settings (key, value, category, data_type, description) VALUES
('scanner_front_port', 'COM20', 'scanner', 'string', '前面扫码枪串口号'),
('scanner_back_port', 'COM21', 'scanner', 'string', '后面扫码枪串口号'),
('scanner_single_mode', 'false', 'scanner', 'bool', '是否单枪模式');

-- D. 批次生成参数（上次使用的值，自动保存）
INSERT OR IGNORE INTO ui_settings (key, value, category, data_type, description) VALUES
('batch_prefix', 'STA', 'batch', 'string', '条码前缀（上次使用）'),
('batch_start', '01', 'batch', 'string', '起始编号（上次使用）'),
('batch_end', '15', 'batch', 'string', '结束编号（上次使用）'),
('batch_suffix', '', 'batch', 'string', '条码后缀（上次使用）'),
('batch_container_id', '', 'batch', 'string', '货柜ID（上次使用）'),
('batch_customer_id', '', 'batch', 'string', '客户ID（上次使用）');

-- E. 语音播报配置
INSERT OR IGNORE INTO ui_settings (key, value, category, data_type, description) VALUES
('voice_enabled', 'true', 'voice', 'bool', '是否启用语音播报'),
('voice_rate', '180', 'voice', 'int', '语音播报语速（120慢/180正常/220快）'),
('voice_volume', '1.0', 'voice', 'float', '语音播报音量（0.5低/0.75中/1.0高）'),
('voice_repeat', '1', 'voice', 'int', '语音播报次数（1-3次）');

-- F. 条码打印配置
INSERT OR IGNORE INTO ui_settings (key, value, category, data_type, description) VALUES
('print_enabled', 'false', 'print', 'bool', '是否启用自动打印'),
('print_printer_name', '', 'print', 'string', '打印机名称'),
('print_barcode_type', 'CODE39', 'print', 'string', '条码类型（CODE39/CODE128）'),
('print_label_width', '70.0', 'print', 'float', '标签宽度（mm）'),
('print_label_height', '20.0', 'print', 'float', '标签高度（mm）'),
('print_barcode_width', '0.25', 'print', 'float', '条码窄条宽度（mm）'),
('print_barcode_height', '10.0', 'print', 'float', '条码高度（mm）'),
('print_barcode_top_margin', '2.0', 'print', 'float', '条码上边距（mm）'),
('print_text_gap', '-1.0', 'print', 'float', '文字与条码间距（mm）'),
('print_font_size', '12', 'print', 'int', '文字字体大小'),
('print_current_print', '', 'print', 'string', '当前打印条码'),
('print_last_printed_code', '', 'print', 'string', '最后打印的条码'),
('print_auto_print_locked', 'false', 'print', 'bool', '自动打印锁定状态'),
('print_locked_code', '', 'print', 'string', '当前锁定的条码'),
('print_match_correction_enabled', 'true', 'print', 'bool', '启用打印条码匹配纠错功能');

-- ============================================
-- 5. 打印配方表 (print_recipes)
-- 用途: 存储条码打印参数配方
-- ============================================
CREATE TABLE IF NOT EXISTS print_recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_name VARCHAR(50) NOT NULL UNIQUE,      -- 配方名称（唯一）
    barcode_type VARCHAR(20) DEFAULT 'CODE39',    -- 条码类型
    label_width REAL DEFAULT 70.0,                -- 标签宽度（mm）
    label_height REAL DEFAULT 20.0,               -- 标签高度（mm）
    barcode_width REAL DEFAULT 0.25,              -- 条码线宽（mm）
    barcode_height REAL DEFAULT 10.0,             -- 条码高度（mm）
    barcode_top_margin REAL DEFAULT 2.0,          -- 上边距（mm）
    font_size INTEGER DEFAULT 12,                 -- 字体大小（pt）
    text_gap REAL DEFAULT -1.0,                   -- 文字间距（mm）
    auto_print_repeat_count INTEGER DEFAULT 1,    -- 自动重复打印次数
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 打印配方表索引
CREATE INDEX IF NOT EXISTS idx_print_recipes_name ON print_recipes(recipe_name);

-- 插入默认配方
INSERT OR IGNORE INTO print_recipes (id, recipe_name, barcode_type, label_width, label_height, barcode_width, barcode_height, barcode_top_margin, font_size, text_gap, auto_print_repeat_count)
VALUES (1, '默认配方', 'CODE39', 70.0, 20.0, 0.25, 10.0, 2.0, 12, -1.0, 1);

-- G. 当前使用的打印配方ID
INSERT OR IGNORE INTO ui_settings (key, value, category, data_type, description) VALUES
('print_current_recipe_id', '1', 'print', 'int', '当前使用的打印配方ID');

-- ============================================
-- 系统配置数据库初始化完成
-- ============================================
