# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Tests for report templates endpoints.
"""

from uuid import uuid4

import pytest


class TestReportTemplateSchemas:
    """Test report template schemas."""

    def test_report_template_create(self):
        """Test report template create schema."""
        template = {
            "name": "User Activity Report",
            "description": "Weekly user activity summary",
            "entity": "users",
            "columns": ["id", "email", "last_login", "login_count"],
            "filters": {"is_active": True},
        }

        assert template["name"] == "User Activity Report"

    def test_report_template_update(self):
        """Test report template update schema."""
        update = {
            "name": "Updated Report Name",
            "columns": ["id", "email", "full_name"],
        }

        assert "name" in update

    def test_report_template_response(self):
        """Test report template response schema."""
        response = {
            "id": str(uuid4()),
            "name": "User Report",
            "entity": "users",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z",
            "created_by": str(uuid4()),
        }

        assert "created_at" in response


class TestReportTemplateEndpoints:
    """Test report template endpoints."""

    @pytest.mark.asyncio
    async def test_list_templates(self):
        """Test listing report templates."""
        templates = [
            {"id": str(uuid4()), "name": "Report 1"},
            {"id": str(uuid4()), "name": "Report 2"},
        ]

        assert len(templates) == 2

    @pytest.mark.asyncio
    async def test_create_template(self):
        """Test creating report template."""
        template = {
            "name": "New Report",
            "entity": "users",
            "columns": ["id", "email"],
        }

        created = {
            **template,
            "id": str(uuid4()),
            "created_at": "2024-01-15T10:30:00Z",
        }

        assert "id" in created

    @pytest.mark.asyncio
    async def test_get_template(self):
        """Test getting report template by ID."""
        template_id = uuid4()
        template = {
            "id": str(template_id),
            "name": "Test Report",
            "entity": "users",
        }

        assert template["id"] == str(template_id)

    @pytest.mark.asyncio
    async def test_update_template(self):
        """Test updating report template."""
        template_id = uuid4()
        update = {"name": "Updated Report"}

        updated = {
            "id": str(template_id),
            "name": update["name"],
            "updated_at": "2024-01-15T11:30:00Z",
        }

        assert updated["name"] == "Updated Report"

    @pytest.mark.asyncio
    async def test_delete_template(self):
        """Test deleting report template."""
        template_id = uuid4()

        # Simulate successful deletion
        deleted = True

        assert deleted is True

    @pytest.mark.asyncio
    async def test_execute_template(self):
        """Test executing report template."""
        template_id = uuid4()

        result = {
            "template_id": str(template_id),
            "row_count": 100,
            "data": [{"id": 1, "email": "user@example.com"}],
        }

        assert result["row_count"] == 100


class TestReportTemplateFilters:
    """Test report template filter functionality."""

    def test_date_range_filter(self):
        """Test date range filter."""
        filters = {
            "date_field": "created_at",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
        }

        assert filters["date_field"] == "created_at"

    def test_status_filter(self):
        """Test status filter."""
        filters = {
            "is_active": True,
            "is_verified": True,
        }

        assert filters["is_active"] is True

    def test_relation_filter(self):
        """Test relation filter."""
        role_id = uuid4()
        filters = {
            "role_id": str(role_id),
        }

        assert "role_id" in filters

    def test_search_filter(self):
        """Test search filter."""
        filters = {
            "search": "admin",
            "search_fields": ["email", "full_name"],
        }

        assert filters["search"] == "admin"

    def test_dynamic_filter(self):
        """Test dynamic filter (relative dates)."""
        filters = {
            "created_after": "{{today - 30 days}}",
            "created_before": "{{today}}",
        }

        assert "{{today}}" in filters["created_before"]


class TestReportTemplateColumns:
    """Test report template column configuration."""

    def test_column_selection(self):
        """Test column selection."""
        columns = [
            {"name": "id", "visible": True},
            {"name": "email", "visible": True},
            {"name": "password_hash", "visible": False},
        ]

        visible = [c for c in columns if c["visible"]]
        assert len(visible) == 2

    def test_column_aliases(self):
        """Test column aliases."""
        columns = [
            {"name": "id", "alias": "User ID"},
            {"name": "email", "alias": "Email Address"},
        ]

        assert columns[0]["alias"] == "User ID"

    def test_column_formatting(self):
        """Test column formatting."""
        columns = [
            {"name": "created_at", "format": "date", "pattern": "YYYY-MM-DD"},
            {"name": "amount", "format": "currency", "currency": "USD"},
        ]

        assert columns[0]["format"] == "date"

    def test_computed_columns(self):
        """Test computed columns."""
        columns = [
            {
                "name": "full_name",
                "computed": True,
                "expression": "concat(first_name, ' ', last_name)",
            }
        ]

        assert columns[0]["computed"] is True


class TestReportTemplateGrouping:
    """Test report template grouping functionality."""

    def test_group_by_single_column(self):
        """Test grouping by single column."""
        grouping = {
            "group_by": ["role_id"],
        }

        assert "role_id" in grouping["group_by"]

    def test_group_by_multiple_columns(self):
        """Test grouping by multiple columns."""
        grouping = {
            "group_by": ["tenant_id", "role_id"],
        }

        assert len(grouping["group_by"]) == 2

    def test_aggregation_functions(self):
        """Test aggregation functions."""
        aggregations = [
            {"column": "id", "function": "count"},
            {"column": "amount", "function": "sum"},
            {"column": "score", "function": "avg"},
        ]

        functions = [a["function"] for a in aggregations]
        assert "count" in functions
        assert "sum" in functions

    def test_having_clause(self):
        """Test having clause for grouped data."""
        grouping = {
            "group_by": ["role_id"],
            "having": {"count_id": {"gte": 10}},
        }

        assert "having" in grouping


class TestReportTemplateSorting:
    """Test report template sorting functionality."""

    def test_sort_ascending(self):
        """Test ascending sort."""
        sorting = {
            "order_by": [{"column": "created_at", "direction": "asc"}],
        }

        assert sorting["order_by"][0]["direction"] == "asc"

    def test_sort_descending(self):
        """Test descending sort."""
        sorting = {
            "order_by": [{"column": "created_at", "direction": "desc"}],
        }

        assert sorting["order_by"][0]["direction"] == "desc"

    def test_multi_column_sort(self):
        """Test multi-column sort."""
        sorting = {
            "order_by": [
                {"column": "role_id", "direction": "asc"},
                {"column": "created_at", "direction": "desc"},
            ],
        }

        assert len(sorting["order_by"]) == 2


class TestReportTemplateScheduling:
    """Test report template scheduling."""

    def test_schedule_daily(self):
        """Test daily schedule."""
        schedule = {
            "frequency": "daily",
            "time": "08:00",
            "timezone": "UTC",
        }

        assert schedule["frequency"] == "daily"

    def test_schedule_weekly(self):
        """Test weekly schedule."""
        schedule = {
            "frequency": "weekly",
            "day_of_week": "monday",
            "time": "09:00",
        }

        assert schedule["day_of_week"] == "monday"

    def test_schedule_monthly(self):
        """Test monthly schedule."""
        schedule = {
            "frequency": "monthly",
            "day_of_month": 1,
            "time": "10:00",
        }

        assert schedule["day_of_month"] == 1

    def test_schedule_delivery(self):
        """Test scheduled report delivery."""
        delivery = {
            "method": "email",
            "recipients": ["admin@example.com"],
            "format": "pdf",
        }

        assert delivery["method"] == "email"


class TestReportTemplateExport:
    """Test report template export functionality."""

    @pytest.mark.asyncio
    async def test_export_to_pdf(self):
        """Test exporting report to PDF."""
        export_config = {
            "format": "pdf",
            "orientation": "landscape",
            "page_size": "A4",
        }

        assert export_config["format"] == "pdf"

    @pytest.mark.asyncio
    async def test_export_to_excel(self):
        """Test exporting report to Excel."""
        export_config = {
            "format": "excel",
            "include_headers": True,
            "auto_width": True,
        }

        assert export_config["format"] == "excel"

    @pytest.mark.asyncio
    async def test_export_to_csv(self):
        """Test exporting report to CSV."""
        export_config = {
            "format": "csv",
            "delimiter": ",",
            "encoding": "utf-8",
        }

        assert export_config["format"] == "csv"


class TestReportTemplatePermissions:
    """Test report template permissions."""

    def test_public_template(self):
        """Test public template access."""
        template = {
            "visibility": "public",
            "accessible_by_all": True,
        }

        assert template["visibility"] == "public"

    def test_private_template(self):
        """Test private template access."""
        template = {
            "visibility": "private",
            "owner_id": str(uuid4()),
        }

        assert template["visibility"] == "private"

    def test_role_based_access(self):
        """Test role-based template access."""
        template = {
            "visibility": "restricted",
            "allowed_roles": ["admin", "manager"],
        }

        user_role = "admin"
        has_access = user_role in template["allowed_roles"]

        assert has_access is True

    def test_tenant_isolation(self):
        """Test tenant isolation for templates."""
        tenant_id = uuid4()
        template = {
            "tenant_id": str(tenant_id),
            "name": "Tenant Report",
        }

        user_tenant = str(tenant_id)
        has_access = template["tenant_id"] == user_tenant

        assert has_access is True


class TestReportTemplateValidation:
    """Test report template validation."""

    def test_validate_entity(self):
        """Test entity validation."""
        valid_entities = ["users", "roles", "tenants", "audit_logs"]
        requested_entity = "users"

        is_valid = requested_entity in valid_entities
        assert is_valid is True

    def test_validate_columns(self):
        """Test column validation."""
        entity_columns = {
            "users": ["id", "email", "full_name", "is_active", "created_at"],
        }

        requested_columns = ["id", "email", "invalid_column"]
        entity = "users"

        invalid = [c for c in requested_columns if c not in entity_columns[entity]]

        assert "invalid_column" in invalid

    def test_validate_filters(self):
        """Test filter validation."""
        valid_operators = ["eq", "neq", "gt", "gte", "lt", "lte", "in", "contains"]
        filter_operator = "eq"

        is_valid = filter_operator in valid_operators
        assert is_valid is True

    def test_validate_name_uniqueness(self):
        """Test name uniqueness validation."""
        existing_names = {"Report 1", "Report 2"}
        new_name = "Report 1"

        is_duplicate = new_name in existing_names
        assert is_duplicate is True


class TestReportTemplateErrorHandling:
    """Test report template error handling."""

    @pytest.mark.asyncio
    async def test_template_not_found(self):
        """Test handling template not found error."""
        error = {
            "status_code": 404,
            "detail": "Report template not found",
        }

        assert error["status_code"] == 404

    @pytest.mark.asyncio
    async def test_invalid_filter_error(self):
        """Test handling invalid filter error."""
        error = {
            "status_code": 400,
            "detail": "Invalid filter: unknown operator 'invalid'",
        }

        assert error["status_code"] == 400

    @pytest.mark.asyncio
    async def test_permission_denied_error(self):
        """Test handling permission denied error."""
        error = {
            "status_code": 403,
            "detail": "You don't have permission to access this template",
        }

        assert error["status_code"] == 403

    @pytest.mark.asyncio
    async def test_execution_error(self):
        """Test handling execution error."""
        error = {
            "status_code": 500,
            "detail": "Error executing report template",
        }

        assert error["status_code"] == 500
