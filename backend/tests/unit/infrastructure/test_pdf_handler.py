# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Unit tests for PDF handler.
"""

from app.infrastructure.data_exchange.pdf_handler import (
    ChartData,
    ChartType,
    PageOrientation,
    PageSize,
    PDFConfig,
    PDFHandler,
    generate_pdf_report,
    is_pdf_available,
)


class TestPDFConfig:
    """Tests for PDFConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PDFConfig()

        assert config.page_size == PageSize.A4
        assert config.orientation == PageOrientation.PORTRAIT
        assert config.margin_top == "20mm"
        assert config.margin_bottom == "25mm"
        assert config.show_page_numbers is True
        assert config.show_date is True
        assert config.primary_color == "#1a56db"

    def test_custom_config(self):
        """Test custom configuration."""
        config = PDFConfig(
            page_size=PageSize.LETTER,
            orientation=PageOrientation.LANDSCAPE,
            company_name="Test Corp",
            watermark_text="CONFIDENTIAL",
            watermark_opacity=0.15,
        )

        assert config.page_size == PageSize.LETTER
        assert config.orientation == PageOrientation.LANDSCAPE
        assert config.company_name == "Test Corp"
        assert config.watermark_text == "CONFIDENTIAL"
        assert config.watermark_opacity == 0.15


class TestChartData:
    """Tests for ChartData dataclass."""

    def test_bar_chart_data(self):
        """Test bar chart data configuration."""
        chart = ChartData(
            chart_type=ChartType.BAR,
            title="Sales by Region",
            labels=["North", "South", "East", "West"],
            data=[100, 150, 80, 120],
            colors=["#1a56db", "#059669", "#dc2626", "#d97706"],
        )

        assert chart.chart_type == ChartType.BAR
        assert len(chart.labels) == 4
        assert len(chart.data) == 4
        assert chart.title == "Sales by Region"

    def test_pie_chart_data(self):
        """Test pie chart data configuration."""
        chart = ChartData(
            chart_type=ChartType.PIE,
            title="Market Share",
            labels=["Product A", "Product B", "Product C"],
            data=[45, 35, 20],
        )

        assert chart.chart_type == ChartType.PIE
        assert sum(chart.data) == 100

    def test_default_dimensions(self):
        """Test default chart dimensions."""
        chart = ChartData(chart_type=ChartType.LINE)

        assert chart.width == 400
        assert chart.height == 300


class TestPDFHandler:
    """Tests for PDFHandler class."""

    def test_initialization_default_config(self):
        """Test handler initialization with default config."""
        handler = PDFHandler()

        assert handler.config is not None
        assert handler.config.page_size == PageSize.A4

    def test_initialization_custom_config(self):
        """Test handler initialization with custom config."""
        config = PDFConfig(company_name="Test Corp")
        handler = PDFHandler(config)

        assert handler.config.company_name == "Test Corp"

    def test_generate_basic_html(self):
        """Test basic HTML generation."""
        handler = PDFHandler()

        content = handler.generate(
            title="Test Report",
            content_html="<p>Hello World</p>",
        )

        assert content is not None
        assert len(content) > 0

    def test_generate_with_table(self):
        """Test generation with table content."""
        handler = PDFHandler()

        table_html = """
        <table>
            <thead>
                <tr><th>Name</th><th>Value</th></tr>
            </thead>
            <tbody>
                <tr><td>Item 1</td><td>100</td></tr>
                <tr><td>Item 2</td><td>200</td></tr>
            </tbody>
        </table>
        """

        content = handler.generate(
            title="Table Report",
            content_html=table_html,
        )

        assert content is not None
        assert len(content) > 0

    def test_generate_with_charts(self):
        """Test generation with charts."""
        handler = PDFHandler()

        charts = [
            ChartData(
                chart_type=ChartType.BAR,
                title="Test Chart",
                labels=["A", "B", "C"],
                data=[10, 20, 30],
            ),
        ]

        content = handler.generate(
            title="Chart Report",
            content_html="<p>Report with charts</p>",
            charts=charts,
        )

        assert content is not None
        # If WeasyPrint is available, should be PDF, otherwise HTML
        if is_pdf_available():
            assert content[:4] == b"%PDF"
        else:
            assert b"<html" in content.lower() or b"<!doctype" in content.lower()

    def test_generate_with_watermark(self):
        """Test generation with watermark."""
        config = PDFConfig(
            watermark_text="CONFIDENTIAL",
            watermark_opacity=0.1,
        )
        handler = PDFHandler(config)

        content = handler.generate(
            title="Confidential Report",
            content_html="<p>Secret data</p>",
        )

        assert content is not None

    def test_html_fallback(self):
        """Test HTML fallback generation."""
        handler = PDFHandler()

        # Get HTML fallback directly
        html = handler._generate_html_fallback(
            title="Test",
            content="<p>Content</p>",
        )

        assert "<!DOCTYPE html>" in html
        assert "<title>Test</title>" in html
        assert "<p>Content</p>" in html


class TestChartSVGGeneration:
    """Tests for SVG chart generation."""

    def test_bar_chart_svg(self):
        """Test bar chart SVG generation."""
        handler = PDFHandler()
        chart = ChartData(
            chart_type=ChartType.BAR,
            labels=["A", "B", "C"],
            data=[10, 20, 15],
        )

        svg = handler._generate_bar_chart_svg(chart)

        assert "<svg" in svg
        assert "</svg>" in svg
        assert "<rect" in svg  # Has bars

    def test_pie_chart_svg(self):
        """Test pie chart SVG generation."""
        handler = PDFHandler()
        chart = ChartData(
            chart_type=ChartType.PIE,
            labels=["X", "Y", "Z"],
            data=[40, 35, 25],
        )

        svg = handler._generate_pie_chart_svg(chart)

        assert "<svg" in svg
        assert "</svg>" in svg
        assert "<path" in svg  # Has pie slices

    def test_line_chart_svg(self):
        """Test line chart SVG generation."""
        handler = PDFHandler()
        chart = ChartData(
            chart_type=ChartType.LINE,
            labels=["Jan", "Feb", "Mar", "Apr"],
            data=[10, 15, 12, 18],
        )

        svg = handler._generate_line_chart_svg(chart)

        assert "<svg" in svg
        assert "</svg>" in svg
        assert "<path" in svg  # Has line path
        assert "<circle" in svg  # Has data points

    def test_empty_chart_data(self):
        """Test handling of empty chart data."""
        handler = PDFHandler()

        chart = ChartData(chart_type=ChartType.BAR, data=[])
        svg = handler._generate_bar_chart_svg(chart)
        assert svg == ""

        chart = ChartData(chart_type=ChartType.PIE, data=[])
        svg = handler._generate_pie_chart_svg(chart)
        assert svg == ""

        chart = ChartData(chart_type=ChartType.LINE, data=[1])  # Less than 2 points
        svg = handler._generate_line_chart_svg(chart)
        assert svg == ""


class TestPDFStyles:
    """Tests for PDF CSS styles generation."""

    def test_get_pdf_styles(self):
        """Test PDF styles generation."""
        handler = PDFHandler()

        styles = handler._get_pdf_styles()

        assert "@page" in styles
        assert "body" in styles
        assert "table" in styles
        assert ".watermark" in styles

    def test_styles_include_custom_colors(self):
        """Test that styles include custom colors."""
        config = PDFConfig(
            primary_color="#ff0000",
            table_header_bg="#0000ff",
        )
        handler = PDFHandler(config)

        styles = handler._get_pdf_styles()

        assert "#ff0000" in styles
        assert "#0000ff" in styles

    def test_landscape_orientation_style(self):
        """Test landscape orientation in styles."""
        config = PDFConfig(orientation=PageOrientation.LANDSCAPE)
        handler = PDFHandler(config)

        styles = handler._get_pdf_styles()

        assert "landscape" in styles


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_is_pdf_available(self):
        """Test PDF availability check."""
        result = is_pdf_available()
        assert isinstance(result, bool)

    def test_generate_pdf_report(self):
        """Test generate_pdf_report function."""
        content, content_type = generate_pdf_report(
            title="Test Report",
            content_html="<p>Test content</p>",
        )

        assert content is not None
        assert len(content) > 0
        assert content_type in ["application/pdf", "text/html"]

    def test_generate_pdf_report_with_config(self):
        """Test generate_pdf_report with custom config."""
        config = PDFConfig(company_name="Test Corp")

        content, content_type = generate_pdf_report(
            title="Custom Report",
            content_html="<p>Custom content</p>",
            config=config,
        )

        assert content is not None

    def test_generate_pdf_report_with_charts(self):
        """Test generate_pdf_report with charts."""
        charts = [
            ChartData(
                chart_type=ChartType.BAR,
                title="Sales",
                data=[100, 200, 150],
                labels=["Q1", "Q2", "Q3"],
            ),
        ]

        content, content_type = generate_pdf_report(
            title="Chart Report",
            content_html="<p>Report with charts</p>",
            charts=charts,
        )

        assert content is not None


class TestPageSizeEnum:
    """Tests for PageSize enum."""

    def test_page_size_values(self):
        """Test page size enum values."""
        assert PageSize.A4.value == "A4"
        assert PageSize.LETTER.value == "letter"
        assert PageSize.LEGAL.value == "legal"
        assert PageSize.A3.value == "A3"
        assert PageSize.A5.value == "A5"


class TestPageOrientationEnum:
    """Tests for PageOrientation enum."""

    def test_orientation_values(self):
        """Test page orientation enum values."""
        assert PageOrientation.PORTRAIT.value == "portrait"
        assert PageOrientation.LANDSCAPE.value == "landscape"


class TestChartTypeEnum:
    """Tests for ChartType enum."""

    def test_chart_type_values(self):
        """Test chart type enum values."""
        assert ChartType.BAR.value == "bar"
        assert ChartType.PIE.value == "pie"
        assert ChartType.LINE.value == "line"
        assert ChartType.DOUGHNUT.value == "doughnut"
