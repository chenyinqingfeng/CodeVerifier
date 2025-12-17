"""
导出查询服务模块
负责数据导出相关的数据库查询操作，支持多级联动筛选
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import traceback


class ExportQueryService:
    """导出查询服务"""

    def __init__(self, db_manager):
        """
        初始化查询服务

        Args:
            db_manager: DatabaseManager实例
        """
        self.db = db_manager

    # ==================== 联动数据查询（用于UI下拉框） ====================

    def get_all_customers(self) -> List[Dict[str, Any]]:
        """
        获取所有客户列表

        Returns:
            客户列表 [{"id": 1, "name": "安吉尔"}, ...]
        """
        try:
            with self.db.get_connection('production') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, customer_name
                    FROM customers
                    ORDER BY customer_name
                """)
                return [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] 获取客户列表失败: {e}")
            traceback.print_exc()
            return []

    def get_containers_by_customer(self, customer_id: Optional[int] = None) -> List[str]:
        """
        根据客户ID获取货柜批号列表（联动）

        Args:
            customer_id: 客户ID，None表示获取全部

        Returns:
            货柜批号列表 ["C001", "C002", ...]
        """
        try:
            with self.db.get_connection('production') as conn:
                cursor = conn.cursor()

                if customer_id is None:
                    # 获取所有货柜
                    cursor.execute("""
                        SELECT DISTINCT container_id
                        FROM batches
                        WHERE container_id IS NOT NULL AND container_id != ''
                        ORDER BY container_id
                    """)
                else:
                    # 获取指定客户的货柜
                    cursor.execute("""
                        SELECT DISTINCT container_id
                        FROM batches
                        WHERE customer_id = ?
                          AND container_id IS NOT NULL
                          AND container_id != ''
                        ORDER BY container_id
                    """, (customer_id,))

                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] 获取货柜列表失败: {e}")
            traceback.print_exc()
            return []

    def get_batches_by_container(
        self,
        customer_id: Optional[int] = None,
        container_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        根据客户和货柜获取批次列表（联动）

        Args:
            customer_id: 客户ID，None表示不筛选
            container_id: 货柜批号，None表示不筛选

        Returns:
            批次列表 [{"id": 1, "name": "K00J00001-K00J00100"}, ...]
        """
        try:
            with self.db.get_connection('production') as conn:
                cursor = conn.cursor()

                # 构建查询条件
                conditions = []
                params = []

                if customer_id is not None:
                    conditions.append("customer_id = ?")
                    params.append(customer_id)

                if container_id is not None:
                    conditions.append("container_id = ?")
                    params.append(container_id)

                where_clause = " AND ".join(conditions) if conditions else "1=1"

                cursor.execute(f"""
                    SELECT id, batch_name
                    FROM batches
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                """, params)

                return [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] 获取批次列表失败: {e}")
            traceback.print_exc()
            return []

    # ==================== 扫码日志查询（5级筛选） ====================

    def query_scan_logs(
        self,
        customer_ids: Optional[List[int]] = None,
        container_ids: Optional[List[str]] = None,
        batch_ids: Optional[List[int]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        scan_result: Optional[str] = None  # 'pass', 'fail', None(全部)
    ) -> List[Dict[str, Any]]:
        """
        查询扫码日志（支持5级联动筛选）
        适配新的scan_logs表结构

        Args:
            customer_ids: 客户ID列表，None表示全部
            container_ids: 货柜批号列表，None表示全部
            batch_ids: 批次ID列表，None表示全部
            start_time: 开始时间 (YYYY-MM-DD HH:MM:SS)
            end_time: 结束时间 (YYYY-MM-DD HH:MM:SS)
            scan_result: 扫码结果筛选 ('pass'/'fail'/None)

        Returns:
            扫码日志列表，包含字段：
            - scan_time: 扫码时间
            - scanner_port: 扫码枪（正面/反面/验证）
            - scan_data: 扫码数据
            - scan_result: 扫码结果
            - result_message: 结果说明
            - operator_name: 操作员
        """
        try:
            with self.db.get_connection('production') as conn:
                cursor = conn.cursor()

                # 构建查询条件
                conditions = []
                params = []

                # 客户筛选（通过batch_id关联）
                if customer_ids:
                    placeholders = ','.join(['?'] * len(customer_ids))
                    conditions.append(f"b.customer_id IN ({placeholders})")
                    params.extend(customer_ids)

                # 货柜筛选
                if container_ids:
                    placeholders = ','.join(['?'] * len(container_ids))
                    conditions.append(f"b.container_id IN ({placeholders})")
                    params.extend(container_ids)

                # 批次筛选
                if batch_ids:
                    placeholders = ','.join(['?'] * len(batch_ids))
                    conditions.append(f"sl.batch_id IN ({placeholders})")
                    params.extend(batch_ids)

                # 时间筛选
                if start_time:
                    conditions.append("sl.scan_time >= ?")
                    params.append(start_time)

                if end_time:
                    conditions.append("sl.scan_time <= ?")
                    params.append(end_time)

                # 结果筛选
                if scan_result:
                    conditions.append("sl.scan_result = ?")
                    params.append(scan_result)

                where_clause = " AND ".join(conditions) if conditions else "1=1"

                # 执行查询 - 使用新的字段结构
                cursor.execute(f"""
                    SELECT
                        sl.scan_time,
                        sl.scanner_port,
                        sl.scan_data,
                        sl.scan_result,
                        sl.result_message,
                        sl.operator_name
                    FROM scan_logs sl
                    LEFT JOIN batches b ON sl.batch_id = b.id
                    LEFT JOIN customers c ON b.customer_id = c.id
                    WHERE {where_clause}
                    ORDER BY sl.scan_time DESC
                """, params)

                # 扫码结果映射
                result_map = {
                    'pass': '验证通过',
                    'fail': '验证失败',
                    'duplicate': '重复扫码',
                    'not_found': '不在批次',
                    'mismatch': '二码不一致',
                    'waiting': '等待中'
                }

                # 扫码枪映射
                port_map = {
                    'front': '正面',
                    'back': '反面',
                    'verify': '验证'
                }

                results = []
                for row in cursor.fetchall():
                    scan_result_raw = row[3] or ''
                    results.append({
                        'scan_time': row[0] or '-',
                        'scanner_port': port_map.get(row[1], row[1] or '-'),
                        'scan_data': row[2] or '-',
                        'scan_result': result_map.get(scan_result_raw, scan_result_raw),
                        'result_message': row[4] or '-',
                        'operator_name': row[5] or '-'
                    })

                return results
        except Exception as e:
            print(f"[ERROR] 查询扫码日志失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_scan_logs_statistics(
        self,
        customer_ids: Optional[List[int]] = None,
        container_ids: Optional[List[str]] = None,
        batch_ids: Optional[List[int]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取扫码日志统计信息（用于汇总Sheet）

        Returns:
            统计信息字典：
            - total_count: 总扫码次数
            - success_count: 成功次数
            - fail_count: 失败次数
            - success_rate: 成功率
            - error_breakdown: 失败原因分类统计
        """
        try:
            with self.db.get_connection('production') as conn:
                cursor = conn.cursor()

                # 构建查询条件（同上）
                conditions = []
                params = []

                if customer_ids:
                    placeholders = ','.join(['?'] * len(customer_ids))
                    conditions.append(f"b.customer_id IN ({placeholders})")
                    params.extend(customer_ids)

                if container_ids:
                    placeholders = ','.join(['?'] * len(container_ids))
                    conditions.append(f"b.container_id IN ({placeholders})")
                    params.extend(container_ids)

                if batch_ids:
                    placeholders = ','.join(['?'] * len(batch_ids))
                    conditions.append(f"sl.batch_id IN ({placeholders})")
                    params.extend(batch_ids)

                if start_time:
                    conditions.append("sl.scan_time >= ?")
                    params.append(start_time)

                if end_time:
                    conditions.append("sl.scan_time <= ?")
                    params.append(end_time)

                where_clause = " AND ".join(conditions) if conditions else "1=1"

                # 统计总数
                cursor.execute(f"""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN sl.scan_result = 'pass' THEN 1 ELSE 0 END) as success,
                        SUM(CASE WHEN sl.scan_result = 'fail' THEN 1 ELSE 0 END) as fail
                    FROM scan_logs sl
                    LEFT JOIN batches b ON sl.batch_id = b.id
                    WHERE {where_clause}
                """, params)

                row = cursor.fetchone()
                total = row[0] or 0
                success = row[1] or 0
                fail = row[2] or 0
                success_rate = (success / total * 100) if total > 0 else 0

                # 统计失败原因分类
                cursor.execute(f"""
                    SELECT
                        sl.error_message,
                        COUNT(*) as count
                    FROM scan_logs sl
                    LEFT JOIN batches b ON sl.batch_id = b.id
                    WHERE {where_clause} AND sl.scan_result = 'fail'
                    GROUP BY sl.error_message
                    ORDER BY count DESC
                """, params)

                error_breakdown = {}
                for row in cursor.fetchall():
                    error_msg = row[0] or '未知错误'
                    count = row[1]
                    error_breakdown[error_msg] = count

                return {
                    'total_count': total,
                    'success_count': success,
                    'fail_count': fail,
                    'success_rate': round(success_rate, 2),
                    'error_breakdown': error_breakdown
                }
        except Exception as e:
            print(f"[ERROR] 获取扫码日志统计失败: {e}")
            traceback.print_exc()
            return {
                'total_count': 0,
                'success_count': 0,
                'fail_count': 0,
                'success_rate': 0,
                'error_breakdown': {}
            }

    # ==================== 生产报告查询（4级筛选） ====================

    def query_production_report(
        self,
        customer_ids: Optional[List[int]] = None,
        container_ids: Optional[List[str]] = None,
        batch_ids: Optional[List[int]] = None,
        match_status: Optional[str] = None  # 'matched', 'unmatched', None(全部)
    ) -> List[Dict[str, Any]]:
        """
        查询生产报告（支持4级联动筛选）

        Args:
            customer_ids: 客户ID列表
            container_ids: 货柜批号列表
            batch_ids: 批次ID列表
            match_status: 匹配状态 ('matched'/'unmatched'/None)

        Returns:
            条码明细列表，包含字段：
            - customer_name: 客户名称
            - container_id: 货柜批号
            - batch_name: 批次名称
            - barcode: 生产条码
            - is_matched: 扫码状态
            - scan_time: 扫码时间
            - is_printed: 打印状态
            - print_time: 打印时间
        """
        try:
            with self.db.get_connection('production') as conn:
                cursor = conn.cursor()

                # 构建查询条件
                conditions = []
                params = []

                # 客户筛选
                if customer_ids:
                    placeholders = ','.join(['?'] * len(customer_ids))
                    conditions.append(f"b.customer_id IN ({placeholders})")
                    params.extend(customer_ids)

                # 货柜筛选
                if container_ids:
                    placeholders = ','.join(['?'] * len(container_ids))
                    conditions.append(f"b.container_id IN ({placeholders})")
                    params.extend(container_ids)

                # 批次筛选
                if batch_ids:
                    placeholders = ','.join(['?'] * len(batch_ids))
                    conditions.append(f"bc.batch_id IN ({placeholders})")
                    params.extend(batch_ids)

                # 匹配状态筛选
                if match_status == 'matched':
                    conditions.append("bc.is_matched = 1")
                elif match_status == 'unmatched':
                    conditions.append("bc.is_matched = 0")

                where_clause = " AND ".join(conditions) if conditions else "1=1"

                # 执行查询
                cursor.execute(f"""
                    SELECT
                        c.customer_name,
                        b.container_id,
                        b.batch_name,
                        bc.barcode,
                        bc.is_matched,
                        bc.scan_time,
                        bc.scan_count,
                        bc.is_printed,
                        bc.last_print_time
                    FROM barcodes bc
                    JOIN batches b ON bc.batch_id = b.id
                    LEFT JOIN customers c ON b.customer_id = c.id
                    WHERE {where_clause}
                    ORDER BY b.batch_name, bc.id
                """, params)

                results = []
                for row in cursor.fetchall():
                    scan_count = row[6] or 0
                    results.append({
                        'customer_name': row[0] or '未指定',
                        'container_id': row[1] or '-',
                        'batch_name': row[2],
                        'barcode': row[3],
                        'is_matched': '已扫' if row[4] else '未扫',
                        'scan_time': row[5] or '-',
                        'scan_count': scan_count if scan_count > 0 else '-',
                        'is_printed': '已打印' if row[7] else '未打印',
                        'print_time': row[8] or '-'
                    })

                return results
        except Exception as e:
            print(f"[ERROR] 查询生产报告失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_production_report_statistics(
        self,
        customer_ids: Optional[List[int]] = None,
        container_ids: Optional[List[str]] = None,
        batch_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        获取生产报告统计信息（用于概览Sheet）

        Returns:
            统计信息字典：
            - customer_count: 客户数量
            - container_count: 货柜数量
            - batch_count: 批次数量
            - total_barcode_count: 总条码数
            - scanned_count: 已扫数量
            - unscanned_count: 未扫数量
            - scan_rate: 扫码率
            - printed_count: 已打印数量
            - unprinted_count: 未打印数量
        """
        try:
            with self.db.get_connection('production') as conn:
                cursor = conn.cursor()

                # 构建查询条件
                conditions = []
                params = []

                if customer_ids:
                    placeholders = ','.join(['?'] * len(customer_ids))
                    conditions.append(f"b.customer_id IN ({placeholders})")
                    params.extend(customer_ids)

                if container_ids:
                    placeholders = ','.join(['?'] * len(container_ids))
                    conditions.append(f"b.container_id IN ({placeholders})")
                    params.extend(container_ids)

                if batch_ids:
                    placeholders = ','.join(['?'] * len(batch_ids))
                    conditions.append(f"bc.batch_id IN ({placeholders})")
                    params.extend(batch_ids)

                where_clause = " AND ".join(conditions) if conditions else "1=1"

                # 统计数据
                cursor.execute(f"""
                    SELECT
                        COUNT(DISTINCT b.customer_id) as customer_count,
                        COUNT(DISTINCT b.container_id) as container_count,
                        COUNT(DISTINCT bc.batch_id) as batch_count,
                        COUNT(bc.id) as total_barcode,
                        SUM(CASE WHEN bc.is_matched = 1 THEN 1 ELSE 0 END) as scanned,
                        SUM(CASE WHEN bc.is_matched = 0 THEN 1 ELSE 0 END) as unscanned,
                        SUM(CASE WHEN bc.is_printed = 1 THEN 1 ELSE 0 END) as printed,
                        SUM(CASE WHEN bc.is_printed = 0 THEN 1 ELSE 0 END) as unprinted
                    FROM barcodes bc
                    JOIN batches b ON bc.batch_id = b.id
                    WHERE {where_clause}
                """, params)

                row = cursor.fetchone()
                total_barcode = row[3] or 0
                scanned = row[4] or 0
                scan_rate = (scanned / total_barcode * 100) if total_barcode > 0 else 0

                return {
                    'customer_count': row[0] or 0,
                    'container_count': row[1] or 0,
                    'batch_count': row[2] or 0,
                    'total_barcode_count': total_barcode,
                    'scanned_count': scanned,
                    'unscanned_count': row[5] or 0,
                    'scan_rate': round(scan_rate, 2),
                    'printed_count': row[6] or 0,
                    'unprinted_count': row[7] or 0
                }
        except Exception as e:
            print(f"[ERROR] 获取生产报告统计失败: {e}")
            traceback.print_exc()
            return {
                'customer_count': 0,
                'container_count': 0,
                'batch_count': 0,
                'total_barcode_count': 0,
                'scanned_count': 0,
                'unscanned_count': 0,
                'scan_rate': 0,
                'printed_count': 0,
                'unprinted_count': 0
            }
