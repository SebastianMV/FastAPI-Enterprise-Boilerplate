# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
Unit tests for Advanced Excel handler.
"""

from datetime import date, datetime
from uuid import uuid4

import pytest

from app.infrastructure.data_exchange.advanced_excel_handler import (
    AdvancedExcelHandler,
    ChartType,
    ConditionalFormatConfig,
    DataValidationConfig,
    ExcelChartConfig,
    ExcelSheetConfig,
    FormatRule,
    FormulaColumn,
    create_excel_report,
    create_multi_sheet_excel,
    is_advanced_excel_available,
)

# Skip all tests if openpyxl is not available
pytestmark = pytest.mark.skipif(
    not is_advanced_excel_available(),
    reason="openpyxl not installed",
)


class TestExcelSheetConfig:
    """Tests for ExcelSheetConfig dataclass."""

    def test_basic_config(self):
        """Test basic sheet configuration."""
        config = ExcelSheetConfig(
            name="Test Sheet",
            headers=["Name", "Value"],
            data=[["Item 1", 100], ["Item 2", 200]],
        )

        assert config.name == "Test Sheet"
        assert len(config.headers) == 2
        assert len(config.data) == 2

    def test_default_values(self):
        """Test default configuration values."""
        config = ExcelSheetConfig(name="Test")

        assert config.freeze_panes == "A2"
        assert config.auto_filter is True
        assert config.protected is False
        assert config.formulas == []
        assert config.charts == []

    def test_with_formulas(self):
        """Test configuration with formulas."""
        config = ExcelSheetConfig(
            name="With Formulas",
            headers=["A", "B", "C", "Total"],
            data=[
                [10, 20, 30],
                [15, 25, 35],
            ],
            formulas=[
                FormulaColumn(
                    column_letter="D",
                    header="Total",
                    formula_template="=SUM(A{row}:C{row})",
                ),
            ],
        )

        assert len(config.formulas) == 1
        assert config.formulas[0].column_letter == "D"


class TestExcelChartConfig:
    """Tests for ExcelChartConfig dataclass."""

    def test_bar_chart_config(self):
        """Test bar chart configuration."""
        config = ExcelChartConfig(
            chart_type=ChartType.BAR,
            title="Sales Chart",
            data_range="A1:B10",
            category_range="A1:A10",
            position="E2",
        )

        assert config.chart_type == ChartType.BAR
        assert config.data_range == "A1:B10"
        assert config.position == "E2"

    def test_default_dimensions(self):
        """Test default chart dimensions."""
        config = ExcelChartConfig(
            chart_type=ChartType.PIE,
            data_range="A1:B5",
        )

        assert config.width == 15
        assert config.height == 10
        assert config.style == 10


class TestConditionalFormatConfig:
    """Tests for ConditionalFormatConfig dataclass."""

    def test_color_scale_config(self):
        """Test color scale configuration."""
        config = ConditionalFormatConfig(
            rule_type=FormatRule.COLOR_SCALE,
            cell_range="B2:B100",
            min_color="FF0000",
            mid_color="FFFF00",
            max_color="00FF00",
        )

        assert config.rule_type == FormatRule.COLOR_SCALE
        assert config.cell_range == "B2:B100"

    def test_formula_rule_config(self):
        """Test formula rule configuration."""
        config = ConditionalFormatConfig(
            rule_type=FormatRule.FORMULA,
            cell_range="A1:A100",
            formula="$A1>100",
            fill_color="FFEB84",
        )

        assert config.rule_type == FormatRule.FORMULA
        assert config.formula == "$A1>100"


class TestDataValidationConfig:
    """Tests for DataValidationConfig dataclass."""

    def test_list_validation(self):
        """Test list validation configuration."""
        config = DataValidationConfig(
            cell_range="C2:C100",
            validation_type="list",
            options=["Active", "Inactive", "Pending"],
        )

        assert config.validation_type == "list"
        assert len(config.options) == 3

    def test_numeric_validation(self):
        """Test numeric validation configuration."""
        config = DataValidationConfig(
            cell_range="D2:D100",
            validation_type="whole",
            min_value=0,
            max_value=100,
        )

        assert config.validation_type == "whole"
        assert config.min_value == 0
        assert config.max_value == 100


class TestFormulaColumn:
    """Tests for FormulaColumn dataclass."""

    def test_sum_formula(self):
        """Test SUM formula column."""
        formula = FormulaColumn(
            column_letter="F",
            header="Total",
            formula_template="=SUM(B{row}:E{row})",
            number_format="#,##0.00",
        )

        assert formula.column_letter == "F"
        assert "{row}" in formula.formula_template
        assert formula.number_format == "#,##0.00"

    def test_percentage_formula(self):
        """Test percentage formula column."""
        formula = FormulaColumn(
            column_letter="G",
            header="Percentage",
            formula_template="=B{row}/F{row}",
            number_format="0.00%",
        )

        assert formula.number_format == "0.00%"


class TestAdvancedExcelHandler:
    """Tests for AdvancedExcelHandler class."""

    def test_initialization(self):
        """Test handler initialization."""
        handler = AdvancedExcelHandler()
        assert handler is not None

    def test_create_simple_workbook(self):
        """Test creating a simple workbook."""
        handler = AdvancedExcelHandler()

        sheets = [
            ExcelSheetConfig(
                name="Data",
                headers=["Name", "Value"],
                data=[
                    ["Item 1", 100],
                    ["Item 2", 200],
                    ["Item 3", 150],
                ],
            ),
        ]

        result = handler.create_workbook(sheets, "Test Workbook")

        assert result is not None
        assert len(result) > 0
        # Check for Excel file signature (PK for zip)
        assert result[:2] == b"PK"

    def test_create_multi_sheet_workbook(self):
        """Test creating a workbook with multiple sheets."""
        handler = AdvancedExcelHandler()

        sheets = [
            ExcelSheetConfig(
                name="Sheet 1",
                headers=["A", "B"],
                data=[["1", "2"], ["3", "4"]],
            ),
            ExcelSheetConfig(
                name="Sheet 2",
                headers=["X", "Y", "Z"],
                data=[["a", "b", "c"]],
            ),
        ]

        result = handler.create_workbook(sheets, "Multi Sheet")

        assert result is not None
        assert len(result) > 0

    def test_create_workbook_with_formulas(self):
        """Test creating a workbook with formula columns."""
        handler = AdvancedExcelHandler()

        sheets = [
            ExcelSheetConfig(
                name="Sales",
                headers=["Product", "Q1", "Q2", "Q3", "Q4"],
                data=[
                    ["Widget A", 100, 120, 110, 130],
                    ["Widget B", 80, 90, 95, 100],
                    ["Widget C", 200, 180, 190, 220],
                ],
                formulas=[
                    FormulaColumn(
                        column_letter="F",
                        header="Total",
                        formula_template="=SUM(B{row}:E{row})",
                        number_format="#,##0",
                    ),
                    FormulaColumn(
                        column_letter="G",
                        header="Average",
                        formula_template="=AVERAGE(B{row}:E{row})",
                        number_format="#,##0.00",
                    ),
                ],
            ),
        ]

        result = handler.create_workbook(sheets, "Sales Report")

        assert result is not None
        assert len(result) > 0

    def test_create_workbook_with_charts(self):
        """Test creating a workbook with charts."""
        handler = AdvancedExcelHandler()

        sheets = [
            ExcelSheetConfig(
                name="Data with Chart",
                headers=["Category", "Value"],
                data=[
                    ["A", 30],
                    ["B", 50],
                    ["C", 25],
                    ["D", 45],
                ],
                charts=[
                    ExcelChartConfig(
                        chart_type=ChartType.BAR,
                        title="Category Values",
                        data_range="A1:B5",
                        category_range="A2:A5",
                        position="D2",
                    ),
                ],
            ),
        ]

        result = handler.create_workbook(sheets, "Chart Report")

        assert result is not None

    def test_create_workbook_with_conditional_formatting(self):
        """Test creating a workbook with conditional formatting."""
        handler = AdvancedExcelHandler()

        sheets = [
            ExcelSheetConfig(
                name="Formatted Data",
                headers=["Name", "Score"],
                data=[
                    ["Alice", 85],
                    ["Bob", 92],
                    ["Charlie", 78],
                    ["Diana", 95],
                ],
                conditional_formats=[
                    ConditionalFormatConfig(
                        rule_type=FormatRule.COLOR_SCALE,
                        cell_range="B2:B5",
                    ),
                ],
            ),
        ]

        result = handler.create_workbook(sheets, "Formatted Report")

        assert result is not None

    def test_create_workbook_with_validation(self):
        """Test creating a workbook with data validation."""
        handler = AdvancedExcelHandler()

        sheets = [
            ExcelSheetConfig(
                name="Validated Data",
                headers=["Name", "Status", "Priority"],
                data=[
                    ["Task 1", "Active", "High"],
                    ["Task 2", "Pending", "Medium"],
                ],
                validations=[
                    DataValidationConfig(
                        cell_range="B2:B100",
                        validation_type="list",
                        options=["Active", "Pending", "Completed"],
                    ),
                    DataValidationConfig(
                        cell_range="C2:C100",
                        validation_type="list",
                        options=["High", "Medium", "Low"],
                    ),
                ],
            ),
        ]

        result = handler.create_workbook(sheets, "Validated Report")

        assert result is not None

    def test_create_report_with_summary(self):
        """Test creating a report with summary sheet."""
        handler = AdvancedExcelHandler()

        result = handler.create_report_with_summary(
            title="Sales Report",
            headers=["Product", "Sales", "Revenue"],
            data=[
                ["Widget A", 100, 5000],
                ["Widget B", 150, 7500],
                ["Widget C", 80, 4000],
            ],
            summary_data={
                "Total Products": 3,
                "Total Sales": 330,
                "Total Revenue": 16500,
                "Average Sale": 110,
            },
            include_charts=True,
        )

        assert result is not None
        assert len(result) > 0

    def test_format_value_uuid(self):
        """Test UUID value formatting."""
        handler = AdvancedExcelHandler()

        uuid = uuid4()
        formatted = handler._format_value(uuid)

        assert isinstance(formatted, str)
        assert str(uuid) == formatted

    def test_format_value_date(self):
        """Test date value formatting."""
        handler = AdvancedExcelHandler()

        d = date(2026, 1, 15)
        formatted = handler._format_value(d)

        assert formatted == d

    def test_format_value_datetime(self):
        """Test datetime value formatting."""
        handler = AdvancedExcelHandler()

        dt = datetime(2026, 1, 15, 10, 30, 0)
        formatted = handler._format_value(dt)

        assert formatted == dt

    def test_format_value_string(self):
        """Test string value formatting."""
        handler = AdvancedExcelHandler()

        formatted = handler._format_value("Hello World")

        assert formatted == "Hello World"

    def test_format_value_number(self):
        """Test numeric value formatting."""
        handler = AdvancedExcelHandler()

        assert handler._format_value(42) == 42
        assert handler._format_value(3.14) == 3.14


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_is_advanced_excel_available(self):
        """Test Excel availability check."""
        result = is_advanced_excel_available()
        assert result is True  # We're in skipif block, so should be True

    def test_create_excel_report(self):
        """Test create_excel_report function."""
        result = create_excel_report(
            title="Test Report",
            headers=["A", "B", "C"],
            data=[
                [1, 2, 3],
                [4, 5, 6],
            ],
        )

        assert result is not None
        assert len(result) > 0

    def test_create_excel_report_with_summary(self):
        """Test create_excel_report with summary."""
        result = create_excel_report(
            title="Summary Report",
            headers=["Name", "Value"],
            data=[
                ["Item 1", 100],
                ["Item 2", 200],
            ],
            summary={
                "Total": 300,
                "Average": 150,
                "Count": 2,
            },
        )

        assert result is not None

    def test_create_multi_sheet_excel(self):
        """Test create_multi_sheet_excel function."""
        sheets = [
            ExcelSheetConfig(
                name="Data",
                headers=["X", "Y"],
                data=[[1, 2], [3, 4]],
            ),
            ExcelSheetConfig(
                name="Summary",
                headers=["Metric", "Value"],
                data=[["Total", 10]],
            ),
        ]

        result = create_multi_sheet_excel(sheets, "Multi Sheet Report")

        assert result is not None
        assert len(result) > 0


class TestChartTypeEnum:
    """Tests for ChartType enum."""

    def test_chart_type_values(self):
        """Test chart type enum values."""
        assert ChartType.BAR.value == "bar"
        assert ChartType.COLUMN.value == "column"
        assert ChartType.LINE.value == "line"
        assert ChartType.PIE.value == "pie"


class TestFormatRuleEnum:
    """Tests for FormatRule enum."""

    def test_format_rule_values(self):
        """Test format rule enum values."""
        assert FormatRule.COLOR_SCALE.value == "color_scale"
        assert FormatRule.DATA_BAR.value == "data_bar"
        assert FormatRule.ICON_SET.value == "icon_set"
        assert FormatRule.FORMULA.value == "formula"


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_data(self):
        """Test handling empty data."""
        handler = AdvancedExcelHandler()

        sheets = [
            ExcelSheetConfig(
                name="Empty",
                headers=["A", "B"],
                data=[],
            ),
        ]

        result = handler.create_workbook(sheets, "Empty Report")

        assert result is not None

    def test_long_sheet_name(self):
        """Test handling long sheet names (Excel limits to 31 chars)."""
        handler = AdvancedExcelHandler()

        long_name = "A" * 50  # Longer than 31 characters

        sheets = [
            ExcelSheetConfig(
                name=long_name,
                headers=["X"],
                data=[[1]],
            ),
        ]

        result = handler.create_workbook(sheets, "Long Name Test")

        assert result is not None

    def test_special_characters_in_data(self):
        """Test handling special characters in data."""
        handler = AdvancedExcelHandler()

        sheets = [
            ExcelSheetConfig(
                name="Special Chars",
                headers=["Name", "Description"],
                data=[
                    ["<Test>", "Contains & ampersand"],
                    ['"Quoted"', "Has 'quotes'"],
                    ["Unicode: 日本語", "Emoji: 🎉"],
                ],
            ),
        ]

        result = handler.create_workbook(sheets, "Special Characters")

        assert result is not None

    def test_large_dataset(self):
        """Test handling larger datasets."""
        handler = AdvancedExcelHandler()

        # Generate 1000 rows
        data = [[f"Row {i}", i, i * 2, i * 3] for i in range(1000)]

        sheets = [
            ExcelSheetConfig(
                name="Large Data",
                headers=["Name", "A", "B", "C"],
                data=data,
            ),
        ]

        result = handler.create_workbook(sheets, "Large Dataset")

        assert result is not None
        assert len(result) > 10000  # Should be reasonably large
