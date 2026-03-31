from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any
from datetime import date

from google.cloud import bigquery
from google.oauth2 import service_account

from ....core.config import BqSourceConfig

logger = logging.getLogger(__name__)


class BqQueryService:
    """基于单个 BqSource 的查询服务，每个数据源一个实例。"""

    def __init__(self, source: BqSourceConfig) -> None:
        self.source = source
        self._client: Optional[bigquery.Client] = None

    @property
    def client(self) -> bigquery.Client:
        if self._client is None:
            key_path = self.source.resolve_key_path()
            credentials = service_account.Credentials.from_service_account_file(
                key_path,
                scopes=["https://www.googleapis.com/auth/bigquery"],
            )
            self._client = bigquery.Client(project=self.source.project_id, credentials=credentials)
        return self._client

    @property
    def table(self) -> str:
        return self.source.full_table_id

    # ─────────────────────────────────────────────
    # 通用查询
    # ─────────────────────────────────────────────

    def run_query(self, sql: str, params: Optional[List[bigquery.ScalarQueryParameter]] = None) -> List[Dict[str, Any]]:
        job_config = bigquery.QueryJobConfig(query_parameters=params or [])
        logger.info("BQ [%s] SQL: %s", self.source.key, sql)
        job = self.client.query(sql, job_config=job_config)
        rows = job.result()
        return [dict(row) for row in rows]

    # ─────────────────────────────────────────────
    # 获取表字段（动态发现）
    # ─────────────────────────────────────────────

    def get_table_fields(self) -> List[Dict[str, str]]:
        """返回表的字段列表 [{name, type, description}]"""
        table_ref = f"{self.source.project_id}.{self.source.dataset}.{self.source.table}"
        table = self.client.get_table(table_ref)
        return [
            {"name": f.name, "type": f.field_type, "description": f.description or ""}
            for f in table.schema
        ]

    # ─────────────────────────────────────────────
    # 过滤选项
    # ─────────────────────────────────────────────

    _filter_cache: Dict[str, List[str]]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

    def get_filter_options(self, fields: List[str], min_count: int = 500) -> Dict[str, List[str]]:
        """获取指定字段的可用过滤值（高频值）。"""
        cache_key = f"_filter_cache_{self.source.key}"
        if hasattr(self, cache_key) and getattr(self, cache_key):
            return getattr(self, cache_key)

        result: Dict[str, List[str]] = {}
        for field in fields:
            sql = f"""
            SELECT {field} AS val
            FROM {self.table}
            WHERE {field} IS NOT NULL AND TRIM(CAST({field} AS STRING)) != ''
            GROUP BY {field}
            HAVING COUNT(*) >= {min_count}
            ORDER BY COUNT(*) DESC
            LIMIT 100
            """
            try:
                rows = self.run_query(sql)
                result[field] = [str(r["val"]).strip() for r in rows if r["val"]]
            except Exception as e:
                logger.warning("获取字段 %s 过滤选项失败: %s", field, e)
                result[field] = []

        setattr(self, cache_key, result)
        return result

    def refresh_filter_cache(self, fields: List[str]) -> Dict[str, List[str]]:
        cache_key = f"_filter_cache_{self.source.key}"
        if hasattr(self, cache_key):
            delattr(self, cache_key)
        return self.get_filter_options(fields)

    # ─────────────────────────────────────────────
    # 通用条件查询
    # ─────────────────────────────────────────────

    def search(
        self,
        select_fields: List[str],
        filters: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
        order_by: str = "",
    ) -> List[Dict[str, Any]]:
        conditions = []
        params: List[bigquery.ScalarQueryParameter] = []

        for field, value in filters.items():
            if value is None or value == "":
                continue
            if field.endswith("__gte"):
                real_field = field[:-5]
                conditions.append(f"DATE({real_field}) >= @{field}")
                params.append(bigquery.ScalarQueryParameter(field, "DATE", value))
            elif field.endswith("__lte"):
                real_field = field[:-5]
                conditions.append(f"DATE({real_field}) <= @{field}")
                params.append(bigquery.ScalarQueryParameter(field, "DATE", value))
            else:
                conditions.append(f"{field} = @{field}")
                params.append(bigquery.ScalarQueryParameter(field, "STRING", str(value)))

        if not conditions:
            raise ValueError("请至少提供一个查询条件")

        where_clause = " AND ".join(conditions)
        select_clause = ", ".join(select_fields)
        real_limit = min(limit, self.source.max_query_limit)
        order_clause = f"ORDER BY {order_by}" if order_by else ""

        sql = f"SELECT {select_clause} FROM {self.table} WHERE {where_clause} {order_clause} LIMIT {real_limit} OFFSET {offset}"
        rows = self.run_query(sql, params)
        self._add_image_urls(rows)
        return rows

    def search_by_id(self, id_filters: Dict[str, str], select_fields: List[str], limit: int = 20) -> List[Dict[str, Any]]:
        conditions = []
        params: List[bigquery.ScalarQueryParameter] = []

        for field, value in id_filters.items():
            if value:
                conditions.append(f"{field} = @{field}")
                params.append(bigquery.ScalarQueryParameter(field, "STRING", value))

        if not conditions:
            raise ValueError("请至少提供一个 ID")

        where_clause = " AND ".join(conditions)
        select_clause = ", ".join(select_fields)
        real_limit = min(limit, self.source.max_query_limit)

        sql = f"SELECT {select_clause} FROM {self.table} WHERE {where_clause} ORDER BY create_time DESC LIMIT {real_limit}"
        rows = self.run_query(sql, params)
        self._add_image_urls(rows)
        return rows

    # ─────────────────────────────────────────────
    # Agent 安全查询
    # ─────────────────────────────────────────────

    def execute_agent_query(self, sql: str) -> List[Dict[str, Any]]:
        sql = sql.strip().rstrip(";")
        upper = sql.upper()
        if not upper.startswith("SELECT"):
            raise ValueError("只允许执行 SELECT 查询")
        for keyword in ("INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE", "MERGE"):
            if keyword in upper:
                raise ValueError(f"不允许执行 {keyword} 操作")
        if "LIMIT" not in upper:
            sql = f"{sql}\nLIMIT 50"
        rows = self.run_query(sql)
        self._add_image_urls(rows)
        return rows

    # ─────────────────────────────────────────────
    # 内部工具
    # ─────────────────────────────────────────────

    def _add_image_urls(self, rows: List[Dict[str, Any]]) -> None:
        base = self.source.image_base_url.rstrip("/") if self.source.image_base_url else ""
        for row in rows:
            pk = row.get("picture_key")
            if pk:
                if base:
                    row["image_url"] = f"{base}/{pk}"
                elif isinstance(pk, str) and pk.startswith("gs://"):
                    row["image_url"] = f"https://storage.googleapis.com/{pk[5:]}"
                else:
                    row["image_url"] = pk
            # 确保值为字符串
            for k, v in row.items():
                if v is not None and not isinstance(v, (str, int, float, bool)):
                    row[k] = str(v)


# ─────────────────────────────────────────────
# 全局实例管理
# ─────────────────────────────────────────────

_instances: Dict[str, BqQueryService] = {}


def get_bq_service(source: BqSourceConfig) -> BqQueryService:
    if source.key not in _instances:
        _instances[source.key] = BqQueryService(source)
    return _instances[source.key]
