# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Generic Exporter implementation.

Provides a flexible exporter that works with any registered entity.
"""

import json
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ports.data_exchange import (
    EntityConfig,
    EntityRegistry,
    ExportFormat,
)
from app.domain.ports.import_export import (
    ExportPort,
    ExportRequest,
    ExportResult,
)
from app.infrastructure.data_exchange.csv_handler import get_csv_handler
from app.infrastructure.data_exchange.excel_handler import (
    get_excel_handler,
    is_excel_available,
)
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class GenericExporter(ExportPort):
    """
    Generic exporter that works with any registered entity.

    Uses the EntityRegistry to get field configurations and
    generates CSV, Excel, or JSON exports.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the exporter.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    def _apply_tenant_filter(
        self, query: Any, config: EntityConfig, tenant_id: UUID | None
    ) -> Any:
        """Apply tenant filter to query, raising error when tenant_id is missing for tenant-aware models."""
        if tenant_id and hasattr(config.model, "tenant_id"):
            return query.where(config.model.tenant_id == tenant_id)
        if not tenant_id and hasattr(config.model, "tenant_id"):
            raise ValueError("tenant_id is required for tenant-aware model exports")
        return query

    async def export(self, request: ExportRequest) -> ExportResult:
        """
        Export data according to the request.

        Args:
            request: Export request configuration

        Returns:
            ExportResult with file content and metadata
        """
        start_time = time.time()

        # Get entity configuration
        config = EntityRegistry.get(request.entity)
        if not config:
            raise ValueError("Entity not found in registry")

        # Query data
        data = await self._query_data(config, request)

        # Convert to dictionaries
        rows = [self._model_to_dict(item, config) for item in data]

        # Generate output based on format
        if request.format == ExportFormat.CSV:
            content = get_csv_handler().write(rows, config, request.columns)
            content_type = "text/csv; charset=utf-8"
            extension = "csv"

        elif request.format == ExportFormat.EXCEL:
            if not is_excel_available():
                raise ValueError("Excel support not available. Install openpyxl.")
            content = get_excel_handler().write(rows, config, request.columns)
            content_type = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            extension = "xlsx"

        elif request.format == ExportFormat.JSON:
            # Serialize with custom encoder
            content = json.dumps(
                rows,
                ensure_ascii=False,
                indent=2,
                default=self._json_serializer,
            ).encode("utf-8")
            content_type = "application/json; charset=utf-8"
            extension = "json"

        else:
            raise ValueError(f"Unsupported format: {request.format}")

        # Generate filename
        if request.filename:
            filename = request.filename
        else:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            filename = f"{config.name}_{timestamp}.{extension}"

        duration_ms = (time.time() - start_time) * 1000

        return ExportResult(
            content=content,
            filename=filename,
            content_type=content_type,
            row_count=len(rows),
            duration_ms=duration_ms,
        )

    async def get_preview(
        self,
        entity: str,
        filters: dict[str, Any] | None = None,
        tenant_id: UUID | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get a preview of data to be exported.

        Args:
            entity: Entity name
            filters: Filters to apply
            tenant_id: Tenant context
            limit: Maximum rows to return

        Returns:
            List of dictionaries representing rows
        """
        config = EntityRegistry.get(entity)
        if not config:
            raise ValueError("Entity not found in registry")

        # Build query
        query = select(config.model)

        # Exclude soft-deleted records
        if hasattr(config.model, "is_deleted"):
            query = query.where(config.model.is_deleted.is_(False))

        # Apply tenant filter
        query = self._apply_tenant_filter(query, config, tenant_id)

        # Apply filters
        if filters:
            query = self._apply_filters(query, config, filters)

        # Apply limit
        query = query.limit(limit)

        # Execute
        result = await self.session.execute(query)
        items = result.scalars().all()

        return [self._model_to_dict(item, config) for item in items]

    async def get_count(
        self,
        entity: str,
        filters: dict[str, Any] | None = None,
        tenant_id: UUID | None = None,
    ) -> int:
        """
        Get count of records that would be exported.

        Args:
            entity: Entity name
            filters: Filters to apply
            tenant_id: Tenant context

        Returns:
            Count of records
        """
        config = EntityRegistry.get(entity)
        if not config:
            raise ValueError("Entity not found in registry")

        # Build count query
        query = select(func.count()).select_from(config.model)

        # Apply tenant filter
        query = self._apply_tenant_filter(query, config, tenant_id)

        # Apply filters
        if filters:
            query = self._apply_filters(query, config, filters)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def _query_data(
        self,
        config: EntityConfig,
        request: ExportRequest,
    ) -> list[Any]:
        """
        Query data from the database.

        Args:
            config: Entity configuration
            request: Export request

        Returns:
            List of model instances
        """
        # Build query
        query = select(config.model)

        # Exclude soft-deleted records
        if hasattr(config.model, "is_deleted"):
            query = query.where(config.model.is_deleted.is_(False))

        # Apply tenant filter
        query = self._apply_tenant_filter(query, config, request.tenant_id)

        # Apply filters
        if request.filters:
            query = self._apply_filters(query, config, request.filters)

        # Apply sorting
        allowed_fields = {f.name for f in config.fields}
        if config.default_sort:
            sort_field = config.default_sort
            descending = sort_field.startswith("-")
            if descending:
                sort_field = sort_field[1:]

            if sort_field in allowed_fields and hasattr(config.model, sort_field):
                column = getattr(config.model, sort_field)
                query = query.order_by(column.desc() if descending else column)

        # Apply limit
        query = query.limit(config.max_export_rows)

        # Execute
        result = await self.session.execute(query)
        return list(result.scalars().all())

    def _apply_filters(
        self,
        query: Any,
        config: EntityConfig,
        filters: dict[str, Any],
    ) -> Any:
        """
        Apply filters to a query.

        Args:
            query: SQLAlchemy query
            config: Entity configuration
            filters: Filter dictionary

        Returns:
            Modified query
        """
        allowed_fields = {f.name for f in config.fields}
        for field_name, value in filters.items():
            if field_name not in allowed_fields or not hasattr(
                config.model, field_name
            ):
                continue

            column = getattr(config.model, field_name)

            if isinstance(value, dict):
                # Complex filter with operator
                operator = value.get("operator", "eq")
                filter_value = value.get("value")

                if operator == "eq":
                    query = query.where(column == filter_value)
                elif operator == "ne":
                    query = query.where(column != filter_value)
                elif operator == "gt":
                    query = query.where(column > filter_value)
                elif operator == "gte":
                    query = query.where(column >= filter_value)
                elif operator == "lt":
                    query = query.where(column < filter_value)
                elif operator == "lte":
                    query = query.where(column <= filter_value)
                elif operator == "in":
                    query = query.where(column.in_(filter_value))
                elif operator == "contains":
                    escaped = (
                        str(filter_value)
                        .replace("\\", "\\\\")
                        .replace("%", "\\%")
                        .replace("_", "\\_")
                    )
                    query = query.where(column.ilike(f"%{escaped}%", escape="\\"))
            else:
                # Simple equality filter
                query = query.where(column == value)

        return query

    def _model_to_dict(
        self,
        instance: Any,
        config: EntityConfig,
    ) -> dict[str, Any]:
        """
        Convert a model instance to a dictionary.

        Args:
            instance: SQLAlchemy model instance
            config: Entity configuration

        Returns:
            Dictionary with field values
        """
        result = {}

        for field in config.get_exportable_fields():
            if hasattr(instance, field.name):
                value = getattr(instance, field.name)
                result[field.name] = value

        return result

    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for non-standard types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def get_exporter(session: AsyncSession) -> GenericExporter:
    """
    Get a GenericExporter instance.

    Args:
        session: SQLAlchemy async session

    Returns:
        GenericExporter instance
    """
    return GenericExporter(session)
