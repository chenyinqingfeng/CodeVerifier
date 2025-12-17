-- ============================================
-- 生产数据库初始化脚本 (production.db)
-- 用途：存储核心业务数据（批次、条码、扫描记录）
-- 版本: 2.0
-- 创建日期: 2024-12-01
-- ============================================

-- ============================================
-- 1. 客户预设表 (customers)
-- 用途: 快速登记客户名称，便于区分订单归属
-- ============================================
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name VARCHAR(100) NOT NULL,         -- 客户名称（中文）
    is_active BOOLEAN DEFAULT 1,                 -- 是否启用
    notes TEXT,                                  -- 备注
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER                           -- 创建人ID（关联system.db的users表）
);

-- 客户表索引
CREATE INDEX IF NOT EXISTS idx_customers_active ON customers(is_active);

-- ============================================
-- 2. 批次表 (batches)
-- 用途: 存储批次元信息和统计数据
-- ============================================
CREATE TABLE IF NOT EXISTS batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_name VARCHAR(100) UNIQUE NOT NULL,     -- 批次名称
    customer_id INTEGER,                         -- 客户ID（外键）
    container_id VARCHAR(100),                   -- 货柜批号
    prefix VARCHAR(50),                          -- 条码前缀
    suffix VARCHAR(50),                          -- 条码后缀
    start_number INTEGER,                        -- 起始序号
    end_number INTEGER,                          -- 结束序号
    total_count INTEGER DEFAULT 0,               -- 总条码数
    matched_count INTEGER DEFAULT 0,             -- 已扫数量
    unmatched_count INTEGER DEFAULT 0,           -- 未扫数量
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status INTEGER DEFAULT 0,                    -- 0=待激活, 1=活动中, 2=已归档
    archived_at DATETIME,                        -- 归档时间
    created_by INTEGER,                          -- 创建人（关联system.db的users表）
    archived_by INTEGER,                         -- 归档人
    notes TEXT,                                  -- 备注
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- 批次表索引
CREATE INDEX IF NOT EXISTS idx_batches_customer ON batches(customer_id);
CREATE INDEX IF NOT EXISTS idx_batches_container ON batches(container_id);
CREATE INDEX IF NOT EXISTS idx_batches_created ON batches(created_at);
CREATE INDEX IF NOT EXISTS idx_batches_status ON batches(status);

-- ============================================
-- 3. 条码明细表 (barcodes)
-- 用途: 存储每个条码及扫描状态
-- ============================================
CREATE TABLE IF NOT EXISTS barcodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL,                   -- 所属批次
    barcode VARCHAR(100) NOT NULL,               -- 条码内容
    is_matched BOOLEAN DEFAULT 0,                -- 是否已扫
    scan_time DATETIME,                          -- 扫码时间
    scan_count INTEGER DEFAULT 0,                -- 重复扫码次数
    scan_result VARCHAR(20) DEFAULT 'pending',   -- pending/pass/fail
    front_code VARCHAR(100),                     -- 正面扫码
    back_code VARCHAR(100),                      -- 反面扫码
    is_printed BOOLEAN DEFAULT 0,                -- 是否已打印
    last_print_time DATETIME,                    -- 上次打印时间
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE
);

-- 条码表索引（核心查询优化）
CREATE UNIQUE INDEX IF NOT EXISTS idx_barcodes_barcode ON barcodes(barcode);
CREATE INDEX IF NOT EXISTS idx_barcodes_batch ON barcodes(batch_id);
CREATE INDEX IF NOT EXISTS idx_barcodes_scan_time ON barcodes(scan_time);
CREATE INDEX IF NOT EXISTS idx_barcodes_matched ON barcodes(is_matched);

-- ============================================
-- 4. 扫描日志表 (scan_logs)
-- 用途: 记录所有扫描操作（审计和追溯）
-- 核心理念：每次扫码立即记录，侧重于谁扫的、扫了什么、结果是什么
-- ============================================
CREATE TABLE IF NOT EXISTS scan_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scanner_port VARCHAR(10),                    -- 扫码枪: front(正面)/back(反面)
    scan_data VARCHAR(100) NOT NULL,             -- 扫进来的原始数据
    scan_result VARCHAR(20),                     -- waiting/pass/fail/duplicate/not_found/mismatch
    result_message TEXT,                         -- 结果说明（如：等待反面、验证通过、重复扫码等）
    scan_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    operator_id INTEGER,                         -- 操作员ID
    operator_name VARCHAR(50),                   -- 操作员姓名
    -- 以下字段保留兼容性
    batch_id INTEGER,
    barcode VARCHAR(100),
    front_code VARCHAR(100),
    back_code VARCHAR(100),
    error_message TEXT,
    plc_signal VARCHAR(10),
    FOREIGN KEY (batch_id) REFERENCES batches(id)
);

-- 扫描日志表索引
CREATE INDEX IF NOT EXISTS idx_scan_logs_time ON scan_logs(scan_time);
CREATE INDEX IF NOT EXISTS idx_scan_logs_batch ON scan_logs(batch_id);
CREATE INDEX IF NOT EXISTS idx_scan_logs_barcode ON scan_logs(barcode);
CREATE INDEX IF NOT EXISTS idx_scan_logs_operator ON scan_logs(operator_id);

-- ============================================
-- 5. 打印记录表 (print_records)
-- 用途: 记录条码打印历史
-- ============================================
CREATE TABLE IF NOT EXISTS print_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode VARCHAR(100) NOT NULL,
    printer_name VARCHAR(100),
    barcode_type VARCHAR(20),                    -- CODE39/CODE128
    print_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    print_status VARCHAR(20),                    -- success/failed
    error_message TEXT
);

-- 打印记录表索引
CREATE INDEX IF NOT EXISTS idx_print_barcode ON print_records(barcode);
CREATE INDEX IF NOT EXISTS idx_print_time ON print_records(print_time);

-- ============================================
-- 注：操作日志表 (operation_logs) 已移至 system.db
-- 所有操作日志统一记录在系统数据库中
-- ============================================

-- ============================================
-- 初始化数据
-- ============================================

-- 插入默认客户（示例数据）
INSERT OR IGNORE INTO customers (id, customer_name) VALUES
(1, '安吉尔'),
(2, 'PW');

-- ============================================
-- 生产数据库初始化完成
-- ============================================
