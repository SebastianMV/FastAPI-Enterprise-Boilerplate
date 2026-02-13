# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for Report Templates - focusing on internal functions and models.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.api.v1.endpoints.report_templates import (
    ReportFilterSchema,
    ReportTemplateCreate,
    ReportTemplateResponse,
    ScheduleFrequency,
    _calculate_next_run,
    _report_templates,
    _scheduled_reports,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def clear_storage():
    """Clear in-memory storage before each test."""
    _report_templates.clear()
    _scheduled_reports.clear()
    yield
    _report_templates.clear()
    _scheduled_reports.clear()


# ============================================================================
# Helper Functions Tests
# ============================================================================


class TestCalculateNextRun:
    """Tests for _calculate_next_run helper function."""

    def test_once_frequency(self):
        """Test 'once' frequency calculation."""
        freq = ScheduleFrequency(type="once", time="14:00")

        result = _calculate_next_run(freq)

        assert result is not None
        assert result.hour == 14
        assert result.minute == 0

    def test_daily_frequency(self):
        """Test 'daily' frequency calculation."""
        freq = ScheduleFrequency(type="daily", time="09:00")

        result = _calculate_next_run(freq)

        assert result is not None
        assert result.hour == 9
        assert result.minute == 0

    def test_weekly_frequency(self):
        """Test 'weekly' frequency calculation."""
        freq = ScheduleFrequency(type="weekly", day_of_week=0, time="09:00")

        result = _calculate_next_run(freq)

        assert result is not None
        assert result.weekday() == 0  # Monday

    def test_monthly_frequency(self):
        """Test 'monthly' frequency calculation."""
        freq = ScheduleFrequency(type="monthly", day_of_month=15, time="09:00")

        result = _calculate_next_run(freq)

        assert result is not None
        assert result.day <= 28  # Safe day handling

    def test_quarterly_frequency(self):
        """Test 'quarterly' frequency calculation."""
        freq = ScheduleFrequency(type="quarterly", time="09:00")

        result = _calculate_next_run(freq)

        assert result is not None
        assert result.month in [1, 4, 7, 10]

    def test_with_start_date(self):
        """Test calculation with start date."""
        future_date = datetime.now(UTC) + timedelta(days=7)
        freq = ScheduleFrequency(type="daily", time="10:00")

        result = _calculate_next_run(freq, future_date)

        assert result is not None


# ============================================================================
# ScheduleFrequency Model Tests
# ============================================================================


class TestScheduleFrequency:
    """Tests for ScheduleFrequency model."""

    def test_create_daily_frequency(self):
        """Test creating a daily frequency schedule."""
        freq = ScheduleFrequency(type="daily", time="08:00")
        assert freq.type == "daily"
        assert freq.time == "08:00"

    def test_create_weekly_frequency(self):
        """Test creating a weekly frequency schedule."""
        freq = ScheduleFrequency(type="weekly", day_of_week=1, time="10:30")
        assert freq.type == "weekly"
        assert freq.day_of_week == 1
        assert freq.time == "10:30"

    def test_create_monthly_frequency(self):
        """Test creating a monthly frequency schedule."""
        freq = ScheduleFrequency(type="monthly", day_of_month=15, time="12:00")
        assert freq.type == "monthly"
        assert freq.day_of_month == 15

    def test_create_quarterly_frequency(self):
        """Test creating a quarterly frequency schedule."""
        freq = ScheduleFrequency(type="quarterly", time="09:00")
        assert freq.type == "quarterly"

    def test_create_once_frequency(self):
        """Test creating a one-time schedule."""
        freq = ScheduleFrequency(type="once", time="14:30")
        assert freq.type == "once"

    def test_default_timezone(self):
        """Test default timezone is set."""
        freq = ScheduleFrequency(type="daily", time="08:00")
        assert freq.timezone == "UTC"


# ============================================================================
# ReportFilterSchema Model Tests
# ============================================================================


class TestReportFilterSchema:
    """Tests for ReportFilterSchema model."""

    def test_create_equality_filter(self):
        """Test creating an equality filter."""
        filter_obj = ReportFilterSchema(field="is_active", operator="eq", value=True)
        assert filter_obj.field == "is_active"
        assert filter_obj.operator == "eq"
        assert filter_obj.value is True

    def test_create_in_filter(self):
        """Test creating an 'in' filter."""
        filter_obj = ReportFilterSchema(
            field="role", operator="in", value=["admin", "manager"]
        )
        assert filter_obj.field == "role"
        assert filter_obj.operator == "in"
        assert filter_obj.value == ["admin", "manager"]

    def test_create_contains_filter(self):
        """Test creating a contains filter."""
        filter_obj = ReportFilterSchema(field="name", operator="contains", value="test")
        assert filter_obj.field == "name"
        assert filter_obj.operator == "contains"

    def test_default_operator(self):
        """Test default operator is eq."""
        filter_obj = ReportFilterSchema(field="status", value="active")
        assert filter_obj.operator == "eq"


# ============================================================================
# ReportTemplateCreate Model Tests
# ============================================================================


class TestReportTemplateCreate:
    """Tests for ReportTemplateCreate model."""

    def test_minimal_template_request(self):
        """Test creating a minimal template request."""
        request = ReportTemplateCreate(
            name="Simple Report",
            entity="users",
            title="User Report",
            format="pdf",
        )
        assert request.name == "Simple Report"
        assert request.entity == "users"
        assert request.format == "pdf"

    def test_template_with_filters(self):
        """Test creating a template with filters."""
        request = ReportTemplateCreate(
            name="Filtered Report",
            entity="users",
            title="Filtered Users",
            format="excel",
            filters=[
                ReportFilterSchema(field="is_active", operator="eq", value=True),
            ],
        )
        assert len(request.filters) == 1
        assert request.filters[0].field == "is_active"

    def test_template_with_columns(self):
        """Test creating a template with columns."""
        request = ReportTemplateCreate(
            name="Custom Columns",
            entity="users",
            title="User Columns",
            format="csv",
            columns=["name", "email"],
        )
        assert len(request.columns) == 2

    def test_template_with_pdf_options(self):
        """Test creating a template with PDF-specific options."""
        request = ReportTemplateCreate(
            name="PDF Report",
            entity="users",
            title="PDF Users",
            format="pdf",
            page_orientation="landscape",
            page_size="A4",
            watermark="CONFIDENTIAL",
        )
        assert request.page_orientation == "landscape"
        assert request.page_size == "A4"
        assert request.watermark == "CONFIDENTIAL"

    def test_template_with_tags(self):
        """Test creating a template with tags."""
        request = ReportTemplateCreate(
            name="Tagged Report",
            entity="users",
            title="Tagged",
            format="pdf",
            tags=["sales", "monthly", "important"],
        )
        assert len(request.tags) == 3

    def test_template_with_date_range(self):
        """Test template with date range configuration."""
        request = ReportTemplateCreate(
            name="Date Range Report",
            entity="users",
            title="Date Report",
            format="pdf",
            date_range_field="created_at",
            date_range_type="this_month",
        )
        assert request.date_range_field == "created_at"
        assert request.date_range_type == "this_month"


# ============================================================================
# In-Memory Storage Tests
# ============================================================================


class TestInMemoryStorage:
    """Tests for in-memory report template storage."""

    def test_templates_storage_initialized(self):
        """Test that templates storage is properly initialized."""
        assert isinstance(_report_templates, dict)

    def test_schedules_storage_initialized(self):
        """Test that schedules storage is properly initialized."""
        assert isinstance(_scheduled_reports, dict)

    def test_add_template_to_storage(self):
        """Test adding a template to storage."""
        template_id = str(uuid4())
        _report_templates[template_id] = {
            "id": template_id,
            "name": "Test Template",
            "entity": "users",
        }

        assert template_id in _report_templates
        assert _report_templates[template_id]["name"] == "Test Template"

    def test_remove_template_from_storage(self):
        """Test removing a template from storage."""
        template_id = str(uuid4())
        _report_templates[template_id] = {"id": template_id, "name": "To Delete"}

        del _report_templates[template_id]

        assert template_id not in _report_templates

    def test_add_schedule_to_storage(self):
        """Test adding a schedule to storage."""
        schedule_id = str(uuid4())
        template_id = str(uuid4())

        _scheduled_reports[schedule_id] = {
            "id": schedule_id,
            "template_id": template_id,
            "name": "Weekly Schedule",
            "enabled": True,
        }

        assert schedule_id in _scheduled_reports
        assert _scheduled_reports[schedule_id]["template_id"] == template_id


# ============================================================================
# Format Validation Tests
# ============================================================================


class TestFormatValidation:
    """Tests for format validation."""

    def test_valid_pdf_format(self):
        """Test that pdf is a valid format."""
        request = ReportTemplateCreate(
            name="PDF Report",
            entity="users",
            title="PDF",
            format="pdf",
        )
        assert request.format == "pdf"

    def test_valid_excel_format(self):
        """Test that excel is a valid format."""
        request = ReportTemplateCreate(
            name="Excel Report",
            entity="users",
            title="Excel",
            format="excel",
        )
        assert request.format == "excel"

    def test_valid_csv_format(self):
        """Test that csv is a valid format."""
        request = ReportTemplateCreate(
            name="CSV Report",
            entity="users",
            title="CSV",
            format="csv",
        )
        assert request.format == "csv"

    def test_valid_html_format(self):
        """Test that html is a valid format."""
        request = ReportTemplateCreate(
            name="HTML Report",
            entity="users",
            title="HTML",
            format="html",
        )
        assert request.format == "html"


# ============================================================================
# Orientation Validation Tests
# ============================================================================


class TestOrientationValidation:
    """Tests for page orientation validation."""

    def test_portrait_orientation(self):
        """Test portrait orientation."""
        request = ReportTemplateCreate(
            name="Portrait",
            entity="users",
            title="Portrait Report",
            format="pdf",
            page_orientation="portrait",
        )
        assert request.page_orientation == "portrait"

    def test_landscape_orientation(self):
        """Test landscape orientation."""
        request = ReportTemplateCreate(
            name="Landscape",
            entity="users",
            title="Landscape Report",
            format="pdf",
            page_orientation="landscape",
        )
        assert request.page_orientation == "landscape"


# ============================================================================
# Frequency Type Validation Tests
# ============================================================================


class TestFrequencyTypeValidation:
    """Tests for schedule frequency type validation."""

    def test_all_valid_frequency_types(self):
        """Test all valid frequency types."""
        valid_types = ["once", "daily", "weekly", "monthly", "quarterly"]

        for freq_type in valid_types:
            freq = ScheduleFrequency(type=freq_type, time="09:00")
            assert freq.type == freq_type

    def test_weekly_with_day_of_week(self):
        """Test that weekly schedules can have day_of_week."""
        freq = ScheduleFrequency(type="weekly", day_of_week=0, time="09:00")
        assert freq.day_of_week == 0

    def test_monthly_with_day_of_month(self):
        """Test that monthly schedules can have day_of_month."""
        freq = ScheduleFrequency(type="monthly", day_of_month=1, time="09:00")
        assert freq.day_of_month == 1


# ============================================================================
# Template Response Tests
# ============================================================================


class TestReportTemplateResponse:
    """Tests for ReportTemplateResponse model."""

    def test_response_has_required_fields(self):
        """Test that response model has required fields."""
        response = ReportTemplateResponse(
            id=str(uuid4()),
            name="Test Template",
            description=None,
            entity="users",
            title="Test",
            format="pdf",
            columns=None,
            filters=[],
            group_by=None,
            sort_by=None,
            include_summary=True,
            date_range_field=None,
            date_range_type=None,
            page_orientation=None,
            page_size=None,
            include_charts=False,
            watermark=None,
            is_public=False,
            tags=[],
            created_by=str(uuid4()),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tenant_id=None,
        )

        assert response.id is not None
        assert response.name == "Test Template"
        assert response.created_at is not None


# ============================================================================
# Edge Cases Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_filters_list(self):
        """Test template with empty filters list."""
        request = ReportTemplateCreate(
            name="No Filters",
            entity="users",
            title="No Filters",
            format="pdf",
            filters=[],
        )
        assert len(request.filters) == 0

    def test_empty_columns_list(self):
        """Test template with empty columns list."""
        request = ReportTemplateCreate(
            name="No Columns",
            entity="users",
            title="No Columns",
            format="pdf",
            columns=[],
        )
        assert len(request.columns) == 0

    def test_long_template_name(self):
        """Test template with maximum allowed name length."""
        long_name = "A" * 100  # max_length is 100
        request = ReportTemplateCreate(
            name=long_name,
            entity="users",
            title="Long Name",
            format="pdf",
        )
        assert len(request.name) == 100

    def test_special_characters_in_name(self):
        """Test template name with special characters."""
        special_name = "Report - Q1 (2024) [Final]"
        request = ReportTemplateCreate(
            name=special_name,
            entity="users",
            title="Special",
            format="pdf",
        )
        assert request.name == special_name


# ============================================================================
# Filter Operators Tests
# ============================================================================


class TestFilterOperators:
    """Tests for filter operators."""

    def test_eq_operator(self):
        """Test equality operator."""
        f = ReportFilterSchema(field="status", operator="eq", value="active")
        assert f.operator == "eq"

    def test_ne_operator(self):
        """Test not equal operator."""
        f = ReportFilterSchema(field="status", operator="ne", value="deleted")
        assert f.operator == "ne"

    def test_gt_operator(self):
        """Test greater than operator."""
        f = ReportFilterSchema(field="age", operator="gt", value=18)
        assert f.operator == "gt"

    def test_gte_operator(self):
        """Test greater than or equal operator."""
        f = ReportFilterSchema(field="score", operator="gte", value=80)
        assert f.operator == "gte"

    def test_lt_operator(self):
        """Test less than operator."""
        f = ReportFilterSchema(field="age", operator="lt", value=65)
        assert f.operator == "lt"

    def test_lte_operator(self):
        """Test less than or equal operator."""
        f = ReportFilterSchema(field="count", operator="lte", value=100)
        assert f.operator == "lte"

    def test_in_operator(self):
        """Test in operator."""
        f = ReportFilterSchema(field="role", operator="in", value=["admin", "user"])
        assert f.operator == "in"

    def test_contains_operator(self):
        """Test contains operator."""
        f = ReportFilterSchema(field="name", operator="contains", value="test")
        assert f.operator == "contains"


# ============================================================================
# Page Size Tests
# ============================================================================


class TestPageSizeValidation:
    """Tests for page size validation."""

    def test_a4_page_size(self):
        """Test A4 page size."""
        request = ReportTemplateCreate(
            name="A4 Report",
            entity="users",
            title="A4",
            format="pdf",
            page_size="A4",
        )
        assert request.page_size == "A4"

    def test_letter_page_size(self):
        """Test letter page size."""
        request = ReportTemplateCreate(
            name="Letter Report",
            entity="users",
            title="Letter",
            format="pdf",
            page_size="letter",
        )
        assert request.page_size == "letter"

    def test_legal_page_size(self):
        """Test legal page size."""
        request = ReportTemplateCreate(
            name="Legal Report",
            entity="users",
            title="Legal",
            format="pdf",
            page_size="legal",
        )
        assert request.page_size == "legal"


# ============================================================================
# Date Range Type Tests
# ============================================================================


class TestDateRangeTypes:
    """Tests for date range types."""

    def test_today_range(self):
        """Test today date range."""
        request = ReportTemplateCreate(
            name="Today Report",
            entity="users",
            title="Today",
            format="pdf",
            date_range_type="today",
        )
        assert request.date_range_type == "today"

    def test_yesterday_range(self):
        """Test yesterday date range."""
        request = ReportTemplateCreate(
            name="Yesterday Report",
            entity="users",
            title="Yesterday",
            format="pdf",
            date_range_type="yesterday",
        )
        assert request.date_range_type == "yesterday"

    def test_this_week_range(self):
        """Test this week date range."""
        request = ReportTemplateCreate(
            name="This Week Report",
            entity="users",
            title="This Week",
            format="pdf",
            date_range_type="this_week",
        )
        assert request.date_range_type == "this_week"

    def test_this_month_range(self):
        """Test this month date range."""
        request = ReportTemplateCreate(
            name="This Month Report",
            entity="users",
            title="This Month",
            format="pdf",
            date_range_type="this_month",
        )
        assert request.date_range_type == "this_month"

    def test_this_quarter_range(self):
        """Test this quarter date range."""
        request = ReportTemplateCreate(
            name="This Quarter Report",
            entity="users",
            title="This Quarter",
            format="pdf",
            date_range_type="this_quarter",
        )
        assert request.date_range_type == "this_quarter"

    def test_this_year_range(self):
        """Test this year date range."""
        request = ReportTemplateCreate(
            name="This Year Report",
            entity="users",
            title="This Year",
            format="pdf",
            date_range_type="this_year",
        )
        assert request.date_range_type == "this_year"


# ============================================================================
# Group By and Sort By Tests
# ============================================================================


class TestGroupByAndSortBy:
    """Tests for group by and sort by options."""

    def test_group_by_single_field(self):
        """Test grouping by single field."""
        request = ReportTemplateCreate(
            name="Grouped Report",
            entity="users",
            title="Grouped",
            format="pdf",
            group_by=["department"],
        )
        assert len(request.group_by) == 1
        assert request.group_by[0] == "department"

    def test_group_by_multiple_fields(self):
        """Test grouping by multiple fields."""
        request = ReportTemplateCreate(
            name="Multi-Grouped Report",
            entity="users",
            title="Multi-Grouped",
            format="pdf",
            group_by=["department", "role"],
        )
        assert len(request.group_by) == 2

    def test_sort_by_field(self):
        """Test sorting by field."""
        request = ReportTemplateCreate(
            name="Sorted Report",
            entity="users",
            title="Sorted",
            format="pdf",
            sort_by="name",
        )
        assert request.sort_by == "name"
