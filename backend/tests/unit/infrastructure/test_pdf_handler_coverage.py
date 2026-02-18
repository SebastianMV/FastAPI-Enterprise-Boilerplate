# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Coverage tests for PDFHandler – exercising chart SVG generation,
HTML fallback, and all branches without requiring WeasyPrint.
"""

from unittest.mock import MagicMock, patch

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

# ---------------------------------------------------------------------------
# is_pdf_available
# ---------------------------------------------------------------------------


class TestIsPdfAvailable:
    def test_returns_bool(self):
        assert isinstance(is_pdf_available(), bool)


# ---------------------------------------------------------------------------
# PDFConfig defaults
# ---------------------------------------------------------------------------


class TestPDFConfig:
    def test_defaults(self):
        cfg = PDFConfig()
        assert cfg.page_size == PageSize.A4
        assert cfg.orientation == PageOrientation.PORTRAIT
        assert cfg.show_page_numbers is True
        assert cfg.show_date is True
        assert cfg.watermark_text is None
        assert cfg.primary_color == "#1a56db"

    def test_custom_values(self):
        cfg = PDFConfig(
            page_size=PageSize.LETTER,
            orientation=PageOrientation.LANDSCAPE,
            company_name="Acme Corp",
            watermark_text="DRAFT",
        )
        assert cfg.page_size == PageSize.LETTER
        assert cfg.orientation == PageOrientation.LANDSCAPE
        assert cfg.watermark_text == "DRAFT"


# ---------------------------------------------------------------------------
# PDFHandler – HTML fallback (works without WeasyPrint)
# ---------------------------------------------------------------------------


class TestHTMLFallback:
    def test_fallback_contains_content(self):
        handler = PDFHandler()
        html = handler._generate_html_fallback("Test Report", "<p>Data</p>")
        assert "Test Report" in html
        assert "<p>Data</p>" in html
        assert "no-pdf-notice" in html  # Warning about no PDF support

    def test_fallback_uses_config_styles(self):
        cfg = PDFConfig(primary_color="#ff0000", table_header_bg="#00ff00")
        handler = PDFHandler(cfg)
        html = handler._generate_html_fallback("Report", "<p>x</p>")
        assert "#ff0000" in html
        assert "#00ff00" in html


# ---------------------------------------------------------------------------
# _build_html_document
# ---------------------------------------------------------------------------


class TestBuildHtmlDocument:
    def test_basic_document(self):
        handler = PDFHandler()
        html = handler._build_html_document("My Report", "<table>rows</table>")
        assert "My Report" in html
        assert "<table>rows</table>" in html

    def test_with_watermark(self):
        cfg = PDFConfig(watermark_text="CONFIDENTIAL", watermark_opacity=0.2)
        handler = PDFHandler(cfg)
        html = handler._build_html_document("Report", "content")
        assert "CONFIDENTIAL" in html
        assert "0.2" in html

    def test_with_logo(self):
        cfg = PDFConfig(
            company_logo_base64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
        )
        handler = PDFHandler(cfg)
        html = handler._build_html_document("Report", "content")
        assert "data:image/png;base64" in html

    def test_with_toc(self):
        handler = PDFHandler()
        html = handler._build_html_document("Report", "content", toc=True)
        assert "Table of Contents" in html

    def test_with_charts(self):
        charts = [
            ChartData(
                chart_type=ChartType.BAR,
                title="Sales",
                labels=["Q1", "Q2"],
                data=[100, 200],
            ),
        ]
        handler = PDFHandler()
        html = handler._build_html_document("Report", "content", charts=charts)
        assert "Sales" in html

    def test_header_with_company_name_and_date(self):
        cfg = PDFConfig(company_name="Acme", show_date=True, header_text="")
        handler = PDFHandler(cfg)
        html = handler._build_html_document("Report", "content")
        assert "Acme" in html

    def test_footer_with_page_numbers(self):
        cfg = PDFConfig(footer_text="© 2026", show_page_numbers=True)
        handler = PDFHandler(cfg)
        html = handler._build_html_document("Report", "content")
        assert "© 2026" in html
        assert "page-number" in html


# ---------------------------------------------------------------------------
# _get_pdf_styles
# ---------------------------------------------------------------------------


class TestGetPdfStyles:
    def test_portrait_a4(self):
        handler = PDFHandler(
            PDFConfig(page_size=PageSize.A4, orientation=PageOrientation.PORTRAIT)
        )
        css = handler._get_pdf_styles()
        assert "A4" in css
        assert "landscape" not in css

    def test_landscape_letter(self):
        handler = PDFHandler(
            PDFConfig(page_size=PageSize.LETTER, orientation=PageOrientation.LANDSCAPE)
        )
        css = handler._get_pdf_styles()
        assert "letter" in css
        assert "landscape" in css

    def test_custom_colors(self):
        cfg = PDFConfig(primary_color="#aabbcc", secondary_color="#ddeeff")
        handler = PDFHandler(cfg)
        css = handler._get_pdf_styles()
        assert "#aabbcc" in css
        assert "#ddeeff" in css


# ---------------------------------------------------------------------------
# _generate_bar_chart_svg
# ---------------------------------------------------------------------------


class TestBarChart:
    def test_basic_bar_chart(self):
        handler = PDFHandler()
        chart = ChartData(
            chart_type=ChartType.BAR,
            title="Revenue",
            labels=["Jan", "Feb", "Mar"],
            data=[100, 200, 150],
            width=400,
            height=300,
        )
        svg = handler._generate_bar_chart_svg(chart)
        assert "<svg" in svg
        assert "100.0" in svg
        assert "200.0" in svg

    def test_bar_chart_with_custom_colors(self):
        handler = PDFHandler()
        chart = ChartData(
            chart_type=ChartType.BAR,
            labels=["A"],
            data=[50],
            colors=["#ff0000"],
        )
        svg = handler._generate_bar_chart_svg(chart)
        assert "#ff0000" in svg

    def test_bar_chart_empty_data(self):
        handler = PDFHandler()
        chart = ChartData(chart_type=ChartType.BAR, labels=[], data=[])
        svg = handler._generate_bar_chart_svg(chart)
        assert svg == ""

    def test_bar_chart_more_data_than_labels(self):
        handler = PDFHandler()
        chart = ChartData(
            chart_type=ChartType.BAR,
            labels=["Only"],
            data=[10, 20, 30],
        )
        svg = handler._generate_bar_chart_svg(chart)
        assert "<svg" in svg


# ---------------------------------------------------------------------------
# _generate_pie_chart_svg
# ---------------------------------------------------------------------------


class TestPieChart:
    def test_basic_pie(self):
        handler = PDFHandler()
        chart = ChartData(
            chart_type=ChartType.PIE,
            labels=["Cats", "Dogs"],
            data=[60, 40],
            width=400,
            height=300,
        )
        svg = handler._generate_pie_chart_svg(chart)
        assert "<svg" in svg
        assert "Cats" in svg
        assert "Dogs" in svg

    def test_pie_empty_data(self):
        handler = PDFHandler()
        chart = ChartData(chart_type=ChartType.PIE, data=[])
        assert handler._generate_pie_chart_svg(chart) == ""

    def test_pie_zero_total(self):
        handler = PDFHandler()
        chart = ChartData(chart_type=ChartType.PIE, data=[0, 0, 0])
        assert handler._generate_pie_chart_svg(chart) == ""

    def test_pie_large_arc(self):
        """One slice > 180 degrees should set large_arc=1."""
        handler = PDFHandler()
        chart = ChartData(
            chart_type=ChartType.PIE,
            labels=["Dominant", "Minor"],
            data=[90, 10],
        )
        svg = handler._generate_pie_chart_svg(chart)
        assert "<svg" in svg

    def test_pie_custom_colors(self):
        handler = PDFHandler()
        chart = ChartData(
            chart_type=ChartType.PIE,
            labels=["A", "B"],
            data=[50, 50],
            colors=["#aaa", "#bbb"],
        )
        svg = handler._generate_pie_chart_svg(chart)
        assert "#aaa" in svg
        assert "#bbb" in svg


# ---------------------------------------------------------------------------
# _generate_line_chart_svg
# ---------------------------------------------------------------------------


class TestLineChart:
    def test_basic_line(self):
        handler = PDFHandler()
        chart = ChartData(
            chart_type=ChartType.LINE,
            labels=["Mon", "Tue", "Wed"],
            data=[10, 20, 15],
        )
        svg = handler._generate_line_chart_svg(chart)
        assert "<svg" in svg
        assert "Mon" in svg

    def test_line_too_few_points(self):
        handler = PDFHandler()
        chart = ChartData(chart_type=ChartType.LINE, data=[10])
        assert handler._generate_line_chart_svg(chart) == ""

    def test_line_empty(self):
        handler = PDFHandler()
        chart = ChartData(chart_type=ChartType.LINE, data=[])
        assert handler._generate_line_chart_svg(chart) == ""

    def test_line_custom_color(self):
        handler = PDFHandler()
        chart = ChartData(
            chart_type=ChartType.LINE,
            data=[5, 10, 15],
            colors=["#00ff00"],
        )
        svg = handler._generate_line_chart_svg(chart)
        assert "#00ff00" in svg

    def test_line_flat_values(self):
        """All same values – value_range fallback to 1."""
        handler = PDFHandler()
        chart = ChartData(
            chart_type=ChartType.LINE,
            data=[5, 5, 5],
        )
        svg = handler._generate_line_chart_svg(chart)
        assert "<svg" in svg


# ---------------------------------------------------------------------------
# _generate_charts_html (dispatch)
# ---------------------------------------------------------------------------


class TestGenerateChartsHtml:
    def test_dispatches_bar(self):
        handler = PDFHandler()
        charts = [ChartData(chart_type=ChartType.BAR, data=[1, 2], labels=["A", "B"])]
        html = handler._generate_charts_html(charts)
        assert "chart-container" in html

    def test_dispatches_pie(self):
        handler = PDFHandler()
        charts = [ChartData(chart_type=ChartType.PIE, data=[60, 40], labels=["X", "Y"])]
        html = handler._generate_charts_html(charts)
        assert "chart-container" in html

    def test_dispatches_line(self):
        handler = PDFHandler()
        charts = [ChartData(chart_type=ChartType.LINE, data=[1, 2, 3])]
        html = handler._generate_charts_html(charts)
        assert "chart-container" in html

    def test_dispatches_doughnut_fallback_to_bar(self):
        handler = PDFHandler()
        charts = [
            ChartData(chart_type=ChartType.DOUGHNUT, data=[1, 2], labels=["A", "B"])
        ]
        html = handler._generate_charts_html(charts)
        assert "chart-container" in html

    def test_chart_with_title(self):
        handler = PDFHandler()
        charts = [
            ChartData(
                chart_type=ChartType.BAR, title="My Chart", data=[5], labels=["A"]
            )
        ]
        html = handler._generate_charts_html(charts)
        assert "My Chart" in html
        assert "chart-title" in html

    def test_chart_without_title(self):
        handler = PDFHandler()
        charts = [ChartData(chart_type=ChartType.BAR, title="", data=[5], labels=["A"])]
        html = handler._generate_charts_html(charts)
        assert "chart-title" not in html


# ---------------------------------------------------------------------------
# generate (main method)
# ---------------------------------------------------------------------------


class TestGenerate:
    @patch("app.infrastructure.data_exchange.pdf_handler._weasyprint_available", False)
    def test_fallback_when_weasyprint_unavailable(self):
        handler = PDFHandler()
        result = handler.generate("Test", "<p>Data</p>")
        assert isinstance(result, bytes)
        html = result.decode("utf-8")
        assert "no-pdf-notice" in html

    @patch("app.infrastructure.data_exchange.pdf_handler._weasyprint_available", True)
    @patch("app.infrastructure.data_exchange.pdf_handler.HTML")
    @patch("app.infrastructure.data_exchange.pdf_handler.CSS")
    @patch("app.infrastructure.data_exchange.pdf_handler.FontConfiguration")
    def test_generates_pdf_when_available(self, mock_font, mock_css, mock_html):
        mock_html_obj = MagicMock()
        mock_html_obj.write_pdf.return_value = b"%PDF-1.4 ..."
        mock_html.return_value = mock_html_obj

        handler = PDFHandler()
        result = handler.generate("Test", "<p>Data</p>")
        assert result == b"%PDF-1.4 ..."

    @patch("app.infrastructure.data_exchange.pdf_handler._weasyprint_available", True)
    @patch("app.infrastructure.data_exchange.pdf_handler.HTML")
    @patch("app.infrastructure.data_exchange.pdf_handler.CSS")
    @patch("app.infrastructure.data_exchange.pdf_handler.FontConfiguration")
    def test_fallback_on_exception(self, mock_font, mock_css, mock_html):
        mock_html.side_effect = Exception("WeasyPrint crashed")

        handler = PDFHandler()
        result = handler.generate("Test", "<p>Data</p>")
        html = result.decode("utf-8")
        assert "no-pdf-notice" in html

    @patch("app.infrastructure.data_exchange.pdf_handler._weasyprint_available", True)
    @patch("app.infrastructure.data_exchange.pdf_handler.HTML")
    @patch("app.infrastructure.data_exchange.pdf_handler.CSS")
    @patch("app.infrastructure.data_exchange.pdf_handler.FontConfiguration")
    def test_generates_with_charts(self, mock_font, mock_css, mock_html):
        mock_html_obj = MagicMock()
        mock_html_obj.write_pdf.return_value = b"%PDF-1.4"
        mock_html.return_value = mock_html_obj

        charts = [ChartData(chart_type=ChartType.BAR, data=[10], labels=["A"])]
        handler = PDFHandler()
        result = handler.generate("Charts", "<p>Data</p>", charts=charts)
        assert result == b"%PDF-1.4"


# ---------------------------------------------------------------------------
# generate_pdf_report (convenience)
# ---------------------------------------------------------------------------


class TestGeneratePdfReport:
    @patch("app.infrastructure.data_exchange.pdf_handler._weasyprint_available", False)
    def test_returns_html_fallback(self):
        content, ctype = generate_pdf_report("Title", "<p>body</p>")
        assert ctype == "text/html"
        assert b"Title" in content

    @patch("app.infrastructure.data_exchange.pdf_handler._weasyprint_available", True)
    @patch("app.infrastructure.data_exchange.pdf_handler.HTML")
    @patch("app.infrastructure.data_exchange.pdf_handler.CSS")
    @patch("app.infrastructure.data_exchange.pdf_handler.FontConfiguration")
    def test_returns_pdf_type(self, mock_font, mock_css, mock_html):
        mock_html_obj = MagicMock()
        mock_html_obj.write_pdf.return_value = b"%PDF"
        mock_html.return_value = mock_html_obj

        content, ctype = generate_pdf_report("Title", "<p>body</p>")
        assert ctype == "application/pdf"
        assert content == b"%PDF"

    @patch("app.infrastructure.data_exchange.pdf_handler._weasyprint_available", False)
    def test_with_custom_config(self):
        cfg = PDFConfig(company_name="Test Co")
        content, ctype = generate_pdf_report("Report", "<p>x</p>", config=cfg)
        assert ctype == "text/html"
