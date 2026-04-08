# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the Apache License, Version 2.0

"""
PDF Handler for advanced PDF generation.

Provides enhanced PDF features including:
- Custom headers/footers
- Watermarks
- Charts/graphs
- Page numbering
- Table of contents
- Multiple page orientations
"""
# pyright: reportMissingImports=false, reportOptionalMemberAccess=false

import html
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Check for WeasyPrint availability
# ============================================================================

_weasyprint_available = False
WeasyHTML: Any = None
WeasyCSS: Any = None
WeasyFontConfiguration: Any = None

try:
    from weasyprint import CSS as WeasyCSS  # type: ignore[no-redef]
    from weasyprint import HTML as WeasyHTML  # type: ignore[no-redef]
    from weasyprint.text.fonts import (  # type: ignore[no-redef]
        FontConfiguration as WeasyFontConfiguration,
    )

    _weasyprint_available = True
except (ImportError, OSError):
    logger.warning("weasyprint_not_installed")


def is_pdf_available() -> bool:
    """Check if PDF generation is available."""
    return _weasyprint_available


class PageOrientation(str, Enum):
    """Page orientation options."""

    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class PageSize(str, Enum):
    """Standard page sizes."""

    A4 = "A4"
    LETTER = "letter"
    LEGAL = "legal"
    A3 = "A3"
    A5 = "A5"


class ChartType(str, Enum):
    """Chart type options."""

    BAR = "bar"
    PIE = "pie"
    LINE = "line"
    DOUGHNUT = "doughnut"


@dataclass
class PDFConfig:
    """Configuration for PDF generation."""

    # Page settings
    page_size: PageSize = PageSize.A4
    orientation: PageOrientation = PageOrientation.PORTRAIT
    margin_top: str = "20mm"
    margin_bottom: str = "25mm"
    margin_left: str = "15mm"
    margin_right: str = "15mm"

    # Header/Footer
    header_text: str = ""
    footer_text: str = ""
    show_page_numbers: bool = True
    show_date: bool = True

    # Branding
    company_name: str = ""
    company_logo_base64: str | None = None
    primary_color: str = "#1a56db"  # Blue
    secondary_color: str = "#6b7280"  # Gray

    # Watermark
    watermark_text: str | None = None
    watermark_opacity: float = 0.1

    # Fonts
    font_family: str = "Arial, sans-serif"
    header_font_size: str = "10pt"
    body_font_size: str = "9pt"

    # Table styling
    table_header_bg: str = "#1a56db"
    table_header_color: str = "#ffffff"
    table_stripe_bg: str = "#f9fafb"
    table_border_color: str = "#e5e7eb"


@dataclass
class ChartData:
    """Data for generating a chart."""

    chart_type: ChartType
    title: str = ""
    labels: list[str] = field(default_factory=list)
    data: list[float] = field(default_factory=list)
    colors: list[str] = field(default_factory=list)
    width: int = 400
    height: int = 300


class PDFHandler:
    """
    Advanced PDF generation handler.

    Provides features beyond basic HTML-to-PDF conversion including
    charts, watermarks, and advanced styling.
    """

    def __init__(self, config: PDFConfig | None = None):
        """Initialize with optional configuration."""
        self.config = config or PDFConfig()

    def generate(
        self,
        title: str,
        content_html: str,
        charts: list[ChartData] | None = None,
        toc: bool = False,
    ) -> bytes:
        """
        Generate a PDF document.

        Args:
            title: Document title
            content_html: Main content as HTML
            charts: Optional list of charts to include
            toc: Include table of contents

        Returns:
            PDF as bytes
        """
        if not _weasyprint_available:
            # Return HTML wrapped as bytes if WeasyPrint not available
            return self._generate_html_fallback(title, content_html).encode("utf-8")

        # Build complete HTML document
        html = self._build_html_document(title, content_html, charts, toc)

        # Generate PDF using WeasyPrint
        try:
            font_config = WeasyFontConfiguration()
            css = WeasyCSS(string=self._get_pdf_styles(), font_config=font_config)

            pdf_bytes = WeasyHTML(string=html).write_pdf(
                stylesheets=[css],
                font_config=font_config,
            )

            return bytes(pdf_bytes)
        except Exception as e:
            logger.error("pdf_generation_failed", error_type=type(e).__name__)
            # Fallback to HTML
            return self._generate_html_fallback(title, content_html).encode("utf-8")

    def _build_html_document(
        self,
        title: str,
        content_html: str,
        charts: list[ChartData] | None = None,
        toc: bool = False,
    ) -> str:
        """Build complete HTML document for PDF conversion."""
        cfg = self.config
        current_date = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")

        # Build logo HTML if provided (validate base64 to prevent injection)
        logo_html = ""
        if cfg.company_logo_base64:
            import re

            # Only allow valid base64 characters (A-Za-z0-9+/=)
            if re.fullmatch(r"[A-Za-z0-9+/=]+", cfg.company_logo_base64):
                logo_html = f'<img src="data:image/png;base64,{cfg.company_logo_base64}" class="company-logo" alt="Logo">'

        # Build watermark if configured
        watermark_html = ""
        if cfg.watermark_text:
            watermark_html = f"""
            <div class="watermark" style="opacity: {cfg.watermark_opacity};">
                {html.escape(cfg.watermark_text)}
            </div>
            """

        # Build chart HTML
        charts_html = ""
        if charts:
            charts_html = self._generate_charts_html(charts)

        # Build TOC placeholder
        toc_html = ""
        if toc:
            toc_html = """
            <div class="toc">
                <h2>Table of Contents</h2>
                <nav id="toc-content"></nav>
            </div>
            """

        # Build header content
        header_content = cfg.header_text or cfg.company_name
        if cfg.show_date:
            header_content += f" | {current_date}"

        # Build footer content
        footer_content = cfg.footer_text
        if cfg.show_page_numbers:
            footer_content += ' | Page <span class="page-number"></span>'

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
</head>
<body>
    {watermark_html}

    <header class="page-header">
        {logo_html}
        <span class="header-text">{html.escape(header_content)}</span>
    </header>

    <main class="content">
        <h1 class="report-title">{html.escape(title)}</h1>
        {toc_html}
        {charts_html}
        {content_html}  <!-- pre-sanitized HTML content from report generator -->
    </main>

    <footer class="page-footer">
        <span class="footer-text">{html.escape(footer_content)}</span>
    </footer>
</body>
</html>"""

    def _get_pdf_styles(self) -> str:
        """Generate CSS styles for PDF."""
        cfg = self.config

        # Determine page dimensions
        page_size = cfg.page_size.value
        if cfg.orientation == PageOrientation.LANDSCAPE:
            page_size += " landscape"

        return f"""
/* Page Setup */
@page {{
    size: {page_size};
    margin: {cfg.margin_top} {cfg.margin_right} {cfg.margin_bottom} {cfg.margin_left};

    @top-center {{
        content: element(header);
    }}

    @bottom-center {{
        content: element(footer);
    }}

    @bottom-right {{
        content: "Page " counter(page) " of " counter(pages);
        font-size: 9pt;
        color: {cfg.secondary_color};
    }}
}}

@page :first {{
    margin-top: 30mm;
}}

/* Running Header/Footer */
.page-header {{
    position: running(header);
    display: flex;
    align-items: center;
    gap: 10px;
    border-bottom: 1px solid {cfg.table_border_color};
    padding-bottom: 5px;
    font-size: {cfg.header_font_size};
    color: {cfg.secondary_color};
}}

.page-footer {{
    position: running(footer);
    border-top: 1px solid {cfg.table_border_color};
    padding-top: 5px;
    font-size: 8pt;
    color: {cfg.secondary_color};
    text-align: center;
}}

.company-logo {{
    height: 25px;
    width: auto;
}}

/* Body Styles */
body {{
    font-family: {cfg.font_family};
    font-size: {cfg.body_font_size};
    line-height: 1.5;
    color: #111827;
}}

.report-title {{
    color: {cfg.primary_color};
    font-size: 24pt;
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 3px solid {cfg.primary_color};
}}

/* Watermark */
.watermark {{
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%) rotate(-45deg);
    font-size: 80pt;
    color: {cfg.secondary_color};
    z-index: -1;
    white-space: nowrap;
}}

/* Table of Contents */
.toc {{
    margin: 20px 0;
    padding: 15px;
    background: {cfg.table_stripe_bg};
    border-radius: 4px;
    page-break-after: always;
}}

.toc h2 {{
    color: {cfg.primary_color};
    margin-bottom: 15px;
}}

.toc a {{
    color: #111827;
    text-decoration: none;
    display: block;
    padding: 5px 0;
    border-bottom: 1px dotted {cfg.table_border_color};
}}

.toc a::after {{
    content: target-counter(attr(href), page);
    float: right;
}}

/* Tables */
table {{
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
    font-size: {cfg.body_font_size};
}}

thead {{
    background-color: {cfg.table_header_bg};
}}

th {{
    color: {cfg.table_header_color};
    font-weight: 600;
    text-align: left;
    padding: 10px 8px;
    border: 1px solid {cfg.table_border_color};
}}

td {{
    padding: 8px;
    border: 1px solid {cfg.table_border_color};
    vertical-align: top;
}}

tbody tr:nth-child(even) {{
    background-color: {cfg.table_stripe_bg};
}}

/* Charts */
.chart-container {{
    margin: 20px 0;
    text-align: center;
    page-break-inside: avoid;
}}

.chart-title {{
    font-size: 12pt;
    font-weight: 600;
    color: {cfg.primary_color};
    margin-bottom: 10px;
}}

.chart-image {{
    max-width: 100%;
    height: auto;
}}

/* Summary Section */
.summary {{
    background: {cfg.table_stripe_bg};
    padding: 15px;
    border-radius: 4px;
    margin: 15px 0;
}}

.summary h2 {{
    color: {cfg.primary_color};
    font-size: 14pt;
    margin-bottom: 10px;
}}

.summary-item {{
    display: flex;
    justify-content: space-between;
    padding: 5px 0;
    border-bottom: 1px solid {cfg.table_border_color};
}}

.summary-label {{
    font-weight: 500;
}}

.summary-value {{
    font-weight: 600;
    color: {cfg.primary_color};
}}

/* Section Headers */
h2 {{
    color: {cfg.primary_color};
    font-size: 14pt;
    margin-top: 20px;
    margin-bottom: 10px;
    page-break-after: avoid;
}}

h3 {{
    color: #374151;
    font-size: 12pt;
    margin-top: 15px;
    margin-bottom: 8px;
    page-break-after: avoid;
}}

/* Page Break Utilities */
.page-break {{
    page-break-after: always;
}}

.no-break {{
    page-break-inside: avoid;
}}

/* Print Utilities */
@media print {{
    .no-print {{
        display: none;
    }}
}}
"""

    def _generate_charts_html(self, charts: list[ChartData]) -> str:
        """Generate HTML for charts using SVG."""
        html_parts = []

        for chart in charts:
            if chart.chart_type == ChartType.BAR:
                svg = self._generate_bar_chart_svg(chart)
            elif chart.chart_type == ChartType.PIE:
                svg = self._generate_pie_chart_svg(chart)
            elif chart.chart_type == ChartType.LINE:
                svg = self._generate_line_chart_svg(chart)
            else:
                svg = self._generate_bar_chart_svg(chart)

            html_parts.append(f"""
            <div class="chart-container">
                {f'<div class="chart-title">{html.escape(chart.title)}</div>' if chart.title else ""}
                {svg}
            </div>
            """)

        return "\n".join(html_parts)

    def _generate_bar_chart_svg(self, chart: ChartData) -> str:
        """Generate SVG bar chart."""
        if not chart.data:
            return ""

        width = chart.width
        height = chart.height
        padding = 40
        bar_width = (width - 2 * padding) / len(chart.data) * 0.8
        spacing = (width - 2 * padding) / len(chart.data) * 0.2
        max_value = max(chart.data) if chart.data else 1

        # Default colors if not provided
        colors = chart.colors or [
            "#1a56db",
            "#059669",
            "#dc2626",
            "#d97706",
            "#7c3aed",
            "#db2777",
            "#0891b2",
            "#65a30d",
            "#ea580c",
            "#6366f1",
        ]

        bars_svg = []
        labels_svg = []

        for i, value in enumerate(chart.data):
            x = padding + i * (bar_width + spacing)
            bar_height = (value / max_value) * (height - 2 * padding - 20)
            y = height - padding - bar_height
            color = colors[i % len(colors)]

            bars_svg.append(
                f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" '
                f'fill="{color}" rx="2"/>'
            )

            # Value label on top of bar
            bars_svg.append(
                f'<text x="{x + bar_width / 2}" y="{y - 5}" text-anchor="middle" '
                f'font-size="10" fill="#374151">{value:.1f}</text>'
            )

            # X-axis label
            if i < len(chart.labels):
                labels_svg.append(
                    f'<text x="{x + bar_width / 2}" y="{height - 10}" text-anchor="middle" '
                    f'font-size="9" fill="#6b7280">{html.escape(chart.labels[i][:10])}</text>'
                )

        return f'''
        <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"
             xmlns="http://www.w3.org/2000/svg" class="chart-image">
            <!-- Background -->
            <rect width="100%" height="100%" fill="#ffffff"/>

            <!-- Grid lines -->
            <line x1="{padding}" y1="{height - padding}" x2="{width - padding}"
                  y2="{height - padding}" stroke="#e5e7eb" stroke-width="1"/>

            <!-- Bars -->
            {"".join(bars_svg)}

            <!-- Labels -->
            {"".join(labels_svg)}
        </svg>
        '''

    def _generate_pie_chart_svg(self, chart: ChartData) -> str:
        """Generate SVG pie chart."""
        if not chart.data:
            return ""

        import math

        width = chart.width
        height = chart.height
        cx, cy = width / 2, height / 2 - 10
        radius = min(width, height) / 2 - 40

        total = sum(chart.data)
        if total == 0:
            return ""

        colors = chart.colors or [
            "#1a56db",
            "#059669",
            "#dc2626",
            "#d97706",
            "#7c3aed",
            "#db2777",
            "#0891b2",
            "#65a30d",
            "#ea580c",
            "#6366f1",
        ]

        slices_svg = []
        legend_svg = []
        start_angle = 0.0

        for i, value in enumerate(chart.data):
            percentage = value / total
            angle = percentage * 360
            end_angle = start_angle + angle

            # Convert to radians
            start_rad = math.radians(start_angle - 90)
            end_rad = math.radians(end_angle - 90)

            # Calculate arc points
            x1 = cx + radius * math.cos(start_rad)
            y1 = cy + radius * math.sin(start_rad)
            x2 = cx + radius * math.cos(end_rad)
            y2 = cy + radius * math.sin(end_rad)

            large_arc = 1 if angle > 180 else 0
            color = colors[i % len(colors)]

            # Create path
            path = (
                f"M {cx},{cy} L {x1},{y1} "
                f"A {radius},{radius} 0 {large_arc},1 {x2},{y2} Z"
            )

            slices_svg.append(
                f'<path d="{path}" fill="{color}" stroke="#ffffff" stroke-width="2"/>'
            )

            # Legend entry
            label = chart.labels[i] if i < len(chart.labels) else f"Item {i + 1}"
            legend_y = 20 + i * 18
            legend_svg.append(
                f'<rect x="{width - 100}" y="{legend_y}" width="12" height="12" fill="{color}"/>'
            )
            legend_svg.append(
                f'<text x="{width - 84}" y="{legend_y + 10}" font-size="9" fill="#374151">'
                f"{html.escape(label[:12])} ({percentage * 100:.0f}%)</text>"
            )

            start_angle = end_angle

        return f'''
        <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"
             xmlns="http://www.w3.org/2000/svg" class="chart-image">
            <!-- Background -->
            <rect width="100%" height="100%" fill="#ffffff"/>

            <!-- Pie slices -->
            {"".join(slices_svg)}

            <!-- Legend -->
            {"".join(legend_svg)}
        </svg>
        '''

    def _generate_line_chart_svg(self, chart: ChartData) -> str:
        """Generate SVG line chart."""
        if not chart.data or len(chart.data) < 2:
            return ""

        width = chart.width
        height = chart.height
        padding = 40

        max_value = max(chart.data)
        min_value = min(chart.data)
        value_range = max_value - min_value or 1

        points = []
        for i, value in enumerate(chart.data):
            x = padding + (i / (len(chart.data) - 1)) * (width - 2 * padding)
            y = (
                height
                - padding
                - ((value - min_value) / value_range) * (height - 2 * padding - 20)
            )
            points.append((x, y, value))

        color = chart.colors[0] if chart.colors else "#1a56db"

        # Create path
        path_d = f"M {points[0][0]},{points[0][1]}"
        for x, y, _ in points[1:]:
            path_d += f" L {x},{y}"

        # Create dots and labels
        dots_svg = []
        labels_svg = []
        for i, (x, y, value) in enumerate(points):
            dots_svg.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{color}"/>')
            dots_svg.append(
                f'<text x="{x}" y="{y - 8}" text-anchor="middle" '
                f'font-size="8" fill="#374151">{value:.1f}</text>'
            )

            if i < len(chart.labels):
                labels_svg.append(
                    f'<text x="{x}" y="{height - 10}" text-anchor="middle" '
                    f'font-size="9" fill="#6b7280">{html.escape(chart.labels[i][:8])}</text>'
                )

        return f'''
        <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"
             xmlns="http://www.w3.org/2000/svg" class="chart-image">
            <!-- Background -->
            <rect width="100%" height="100%" fill="#ffffff"/>

            <!-- Grid -->
            <line x1="{padding}" y1="{height - padding}" x2="{width - padding}"
                  y2="{height - padding}" stroke="#e5e7eb" stroke-width="1"/>
            <line x1="{padding}" y1="{padding}" x2="{padding}"
                  y2="{height - padding}" stroke="#e5e7eb" stroke-width="1"/>

            <!-- Line -->
            <path d="{path_d}" fill="none" stroke="{color}" stroke-width="2"/>

            <!-- Dots and values -->
            {"".join(dots_svg)}

            <!-- Labels -->
            {"".join(labels_svg)}
        </svg>
        '''

    def _generate_html_fallback(self, title: str, content: str) -> str:
        """Generate HTML fallback when WeasyPrint is not available."""
        cfg = self.config

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>
        body {{
            font-family: {cfg.font_family};
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            color: #111827;
        }}
        h1 {{
            color: {cfg.primary_color};
            border-bottom: 3px solid {cfg.primary_color};
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th {{
            background: {cfg.table_header_bg};
            color: {cfg.table_header_color};
            padding: 10px 8px;
            text-align: left;
        }}
        td {{
            padding: 8px;
            border: 1px solid {cfg.table_border_color};
        }}
        tr:nth-child(even) {{
            background: {cfg.table_stripe_bg};
        }}
        .no-pdf-notice {{
            background: #fef3c7;
            border: 1px solid #f59e0b;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <div class="no-pdf-notice">
        <strong>Note:</strong> PDF generation is not available.
        Install WeasyPrint for full PDF support: <code>pip install weasyprint</code>
    </div>
    <h1>{html.escape(title)}</h1>
    {content}
</body>
</html>"""


# ============================================================================
# Convenience Functions
# ============================================================================


def generate_pdf_report(
    title: str,
    content_html: str,
    config: PDFConfig | None = None,
    charts: list[ChartData] | None = None,
) -> tuple[bytes, str]:
    """
    Generate a PDF report.

    Args:
        title: Report title
        content_html: HTML content
        config: Optional PDF configuration
        charts: Optional charts to include

    Returns:
        Tuple of (content_bytes, content_type)
    """
    handler = PDFHandler(config)
    content = handler.generate(title, content_html, charts)

    if is_pdf_available():
        return content, "application/pdf"
    return content, "text/html"
