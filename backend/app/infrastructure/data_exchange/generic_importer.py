# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Generic Importer implementation.

Provides a flexible importer that works with any registered entity.
"""

import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ports.data_exchange import EntityConfig, EntityRegistry, ImportMode
from app.domain.ports.import_export import (
    DataImportError,
    ImportPort,
    ImportRequest,
    ImportResult,
    DataImportWarning,
)
from app.infrastructure.data_exchange.csv_handler import get_csv_handler
from app.infrastructure.data_exchange.excel_handler import (
    get_excel_handler,
    is_excel_available,
)
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class GenericImporter(ImportPort):
    """
    Generic importer that works with any registered entity.

    Uses the EntityRegistry to get field configurations and
    performs validation, transformation, and database operations.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the importer.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def validate(self, request: ImportRequest) -> ImportResult:
        """
        Validate import file without actually importing.

        Args:
            request: Import request with file data

        Returns:
            ImportResult with validation results
        """
        # Force dry run mode
        request.dry_run = True
        return await self._process_import(request)

    async def execute(self, request: ImportRequest) -> ImportResult:
        """
        Execute the import operation.

        Args:
            request: Import request with file data

        Returns:
            ImportResult with operation results
        """
        request.dry_run = False
        return await self._process_import(request)

    def get_template(self, entity: str, format: str = "csv") -> bytes:
        """
        Generate an empty template file for import.

        Args:
            entity: Entity name
            format: Template format (csv, excel)

        Returns:
            Template file content as bytes

        Raises:
            ValueError: If entity not found or format not supported
        """
        config = EntityRegistry.get(entity)
        if not config:
            raise ValueError("Entity not found in registry")

        if format == "csv":
            handler = get_csv_handler()
            return handler.generate_template(config)
        if format == "excel":
            if not is_excel_available():
                raise ValueError("Excel support not available. Install openpyxl.")
            handler = get_excel_handler()
            return handler.generate_template(config)
        raise ValueError("Unsupported template format")

    async def _process_import(self, request: ImportRequest) -> ImportResult:
        """
        Process the import request.

        Args:
            request: Import request

        Returns:
            ImportResult
        """
        start_time = time.time()

        # Get entity configuration
        config = EntityRegistry.get(request.entity)
        if not config:
            return ImportResult(
                errors=[
                    DataImportError(
                        row=0,
                        field=None,
                        value=None,
                        error="Entity not found in registry",
                    )
                ],
            )

        # Read file content
        file_content = request.file.read()
        if hasattr(request.file, "seek"):
            request.file.seek(0)

        # Parse file based on type
        if request.file_type == "csv":
            rows = list(get_csv_handler().read(file_content, config))
        elif request.file_type == "excel":
            if not is_excel_available():
                return ImportResult(
                    errors=[
                        DataImportError(
                            row=0,
                            field=None,
                            value=None,
                            error="Excel support not available. Install openpyxl.",
                        )
                    ],
                )
            rows = list(get_excel_handler().read(file_content, config))
        else:
            return ImportResult(
                errors=[
                    DataImportError(
                        row=0,
                        field=None,
                        value=None,
                        error=f"Unsupported file type: {request.file_type}",
                    )
                ],
            )

        result = ImportResult(
            total_rows=len(rows),
            dry_run=request.dry_run,
        )

        # Process rows
        batch = []
        for row_num, row_data, parse_errors in rows:
            # Add parse errors to result
            for error_msg in parse_errors:
                result.errors.append(
                    DataImportError(
                        row=row_num,
                        field=None,
                        value=None,
                        error=error_msg,
                    )
                )

            # Skip rows with errors if not skip_errors mode
            if parse_errors:
                result.skipped += 1
                if not request.skip_errors:
                    break
                continue

            # Add tenant_id if provided
            if request.tenant_id:
                row_data["tenant_id"] = request.tenant_id

            # Add to batch
            batch.append((row_num, row_data))

            # Process batch
            if len(batch) >= config.batch_size:
                batch_result = await self._process_batch(
                    batch, config, request.mode, request.dry_run
                )
                result.inserted += batch_result["inserted"]
                result.updated += batch_result["updated"]
                result.skipped += batch_result["skipped"]
                result.errors.extend(batch_result["errors"])
                result.warnings.extend(batch_result["warnings"])
                batch = []

        # Process remaining batch
        if batch:
            batch_result = await self._process_batch(
                batch, config, request.mode, request.dry_run
            )
            result.inserted += batch_result["inserted"]
            result.updated += batch_result["updated"]
            result.skipped += batch_result["skipped"]
            result.errors.extend(batch_result["errors"])
            result.warnings.extend(batch_result["warnings"])

        result.duration_ms = (time.time() - start_time) * 1000

        return result

    async def _process_batch(
        self,
        batch: list[tuple[int, dict[str, Any]]],
        config: EntityConfig,
        mode: ImportMode,
        dry_run: bool,
    ) -> dict[str, Any]:
        """
        Process a batch of rows.

        Args:
            batch: List of (row_num, row_data) tuples
            config: Entity configuration
            mode: Import mode
            dry_run: If True, don't commit changes

        Returns:
            Dictionary with batch results
        """
        result = {
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [],
            "warnings": [],
        }

        for row_num, row_data in batch:
            try:
                if mode == ImportMode.INSERT:
                    if not dry_run:
                        instance = config.model(**row_data)
                        self.session.add(instance)
                    result["inserted"] += 1

                elif mode == ImportMode.UPSERT:
                    # Try to find existing record
                    existing = await self._find_existing(config, row_data)

                    if existing:
                        if not dry_run:
                            for key, value in row_data.items():
                                if hasattr(existing, key):
                                    setattr(existing, key, value)
                        result["updated"] += 1
                    else:
                        if not dry_run:
                            instance = config.model(**row_data)
                            self.session.add(instance)
                        result["inserted"] += 1

                elif mode == ImportMode.UPDATE_ONLY:
                    existing = await self._find_existing(config, row_data)

                    if existing:
                        if not dry_run:
                            for key, value in row_data.items():
                                if hasattr(existing, key):
                                    setattr(existing, key, value)
                        result["updated"] += 1
                    else:
                        result["skipped"] += 1
                        result["warnings"].append(
                            DataImportWarning(
                                row=row_num,
                                field=None,
                                message="Record not found for update",
                            )
                        )

            except Exception as e:
                logger.warning("Import error at row %d: %s", row_num, e)
                result["errors"].append(
                    DataImportError(
                        row=row_num,
                        field=None,
                        value=None,
                        error="Failed to process row",
                    )
                )
                result["skipped"] += 1

        # Commit if not dry run
        if not dry_run:
            try:
                await self.session.flush()
            except Exception as e:
                logger.warning("Import flush failed: %s", e)
                await self.session.rollback()
                result["errors"].append(
                    DataImportError(
                        row=0,
                        field=None,
                        value=None,
                        error="Database error occurred during import",
                    )
                )

        return result

    async def _find_existing(
        self,
        config: EntityConfig,
        row_data: dict[str, Any],
    ) -> Any | None:
        """
        Find an existing record based on unique fields.

        Args:
            config: Entity configuration
            row_data: Row data to match

        Returns:
            Existing record or None
        """
        if not config.unique_fields:
            return None

        # Build query
        query = select(config.model)
        for field_name in config.unique_fields:
            if field_name in row_data:
                query = query.where(
                    getattr(config.model, field_name) == row_data[field_name]
                )

        # Always filter by tenant_id if the model has it and row_data includes it
        if (
            "tenant_id" not in (config.unique_fields or [])
            and "tenant_id" in row_data
            and row_data["tenant_id"] is not None
            and hasattr(config.model, "tenant_id")
        ):
            query = query.where(config.model.tenant_id == row_data["tenant_id"])

        result = await self.session.execute(query)
        return result.scalar_one_or_none()


def get_importer(session: AsyncSession) -> GenericImporter:
    """
    Get a GenericImporter instance.

    Args:
        session: SQLAlchemy async session

    Returns:
        GenericImporter instance
    """
    return GenericImporter(session)
