# PDF & Excel Advanced Features

This document describes the advanced PDF and Excel features for report generation.

## Overview

The Data Exchange system includes powerful PDF and Excel generation capabilities with advanced features like charts, conditional formatting, and watermarks.

| Feature | PDF | Excel |
| --- | --- | --- |
| **Basic Reports** | ✅ | ✅ |
| **Charts** | ✅ (SVG) | ✅ (Native) |
| **Watermarks** | ✅ | ❌ |
| **Headers/Footers** | ✅ | ❌ |
| **Page Numbers** | ✅ | ❌ |
| **Formulas** | ❌ | ✅ |
| **Conditional Formatting** | ❌ | ✅ |
| **Data Validation** | ❌ | ✅ |
| **Multiple Sheets** | ❌ | ✅ |

## Installation

### Required Dependencies

```bash
# In backend directory
pip install openpyxl>=3.1.5 weasyprint>=62.3
```

### System Dependencies for WeasyPrint

WeasyPrint requires system libraries for PDF generation:

**Windows:**
```powershell
# Install GTK3 runtime
# Download from: https://github.com/nicjar/WeasyPrint-GTK3-Install
```

**Ubuntu/Debian:**
```bash
apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0
```

**macOS:**
```bash
brew install pango cairo gdk-pixbuf
```

---

## PDF Features

### PDFConfig Options

```python
from app.infrastructure.data_exchange import PDFConfig, PageSize, PageOrientation

config = PDFConfig(
    # Page Settings
    page_size=PageSize.A4,  # A4, LETTER, LEGAL, A3, A5
    orientation=PageOrientation.PORTRAIT,  # PORTRAIT, LANDSCAPE
    margin_top="20mm",
    margin_bottom="25mm",
    margin_left="15mm",
    margin_right="15mm",
    
    # Header/Footer
    header_text="Company Report",
    footer_text="Confidential",
    show_page_numbers=True,
    show_date=True,
    
    # Branding
    company_name="Acme Corp",
    company_logo_base64="...",  # Base64 encoded logo
    primary_color="#1a56db",
    secondary_color="#6b7280",
    
    # Watermark
    watermark_text="DRAFT",
    watermark_opacity=0.1,
    
    # Fonts
    font_family="Arial, sans-serif",
    header_font_size="10pt",
    body_font_size="9pt",
    
    # Table Styling
    table_header_bg="#1a56db",
    table_header_color="#ffffff",
    table_stripe_bg="#f9fafb",
)
```

### Generating PDF with Charts

```python
from app.infrastructure.data_exchange import (
    PDFHandler,
    PDFConfig,
    ChartData,
    ChartType,
)

# Create handler
handler = PDFHandler(PDFConfig(company_name="Acme Corp"))

# Define charts
charts = [
    ChartData(
        chart_type=ChartType.BAR,
        title="Sales by Region",
        labels=["North", "South", "East", "West"],
        data=[100, 150, 80, 120],
        colors=["#1a56db", "#059669", "#dc2626", "#d97706"],
        width=400,
        height=300,
    ),
    ChartData(
        chart_type=ChartType.PIE,
        title="Market Share",
        labels=["Product A", "Product B", "Product C"],
        data=[45, 35, 20],
    ),
]

# Generate PDF
pdf_bytes = handler.generate(
    title="Sales Report Q1 2026",
    content_html="""
        <h2>Executive Summary</h2>
        <p>Sales increased by 15% compared to previous quarter.</p>
        
        <table>
            <thead>
                <tr><th>Region</th><th>Sales</th><th>Growth</th></tr>
            </thead>
            <tbody>
                <tr><td>North</td><td>$100,000</td><td>+10%</td></tr>
                <tr><td>South</td><td>$150,000</td><td>+20%</td></tr>
            </tbody>
        </table>
    """,
    charts=charts,
)

# Save or return
with open("report.pdf", "wb") as f:
    f.write(pdf_bytes)
```

### Chart Types

| Type | Description | Use Case |
| --- | --- | --- |
| `BAR` | Horizontal bar chart | Comparing categories |
| `PIE` | Pie chart with legend | Showing proportions |
| `LINE` | Line chart with points | Trends over time |
| `DOUGHNUT` | Donut chart | Alternative to pie |

### CSS Styling

The PDF generator supports extensive CSS including:

```css
/* Page breaks */
.page-break { page-break-after: always; }
.no-break { page-break-inside: avoid; }

/* Summary sections */
.summary { background: #f9fafb; padding: 15px; }
.summary-item { display: flex; justify-content: space-between; }

/* Tables (auto-styled) */
table { width: 100%; border-collapse: collapse; }
thead { background: primary_color; color: white; }
tbody tr:nth-child(even) { background: stripe_color; }
```

---

## Excel Features

### ExcelSheetConfig Options

```python
from app.infrastructure.data_exchange import (
    AdvancedExcelHandler,
    ExcelSheetConfig,
    ExcelChartConfig,
    FormulaColumn,
    ConditionalFormatConfig,
    DataValidationConfig,
    ChartType,
    FormatRule,
)

sheet = ExcelSheetConfig(
    name="Sales Data",  # Sheet name (max 31 chars)
    headers=["Product", "Q1", "Q2", "Q3", "Q4", "Total"],
    data=[
        ["Widget A", 100, 120, 110, 130],
        ["Widget B", 80, 90, 95, 100],
    ],
    
    # Formula Columns
    formulas=[
        FormulaColumn(
            column_letter="F",
            header="Total",
            formula_template="=SUM(B{row}:E{row})",
            number_format="#,##0",
        ),
    ],
    
    # Charts
    charts=[
        ExcelChartConfig(
            chart_type=ChartType.COLUMN,
            title="Quarterly Sales",
            data_range="A1:E3",
            position="H2",
        ),
    ],
    
    # Conditional Formatting
    conditional_formats=[
        ConditionalFormatConfig(
            rule_type=FormatRule.COLOR_SCALE,
            cell_range="B2:E10",
            min_color="F8696B",  # Red
            mid_color="FFEB84",  # Yellow
            max_color="63BE7B",  # Green
        ),
    ],
    
    # Data Validation (Dropdowns)
    validations=[
        DataValidationConfig(
            cell_range="G2:G100",
            validation_type="list",
            options=["Active", "Inactive", "Pending"],
        ),
    ],
    
    # Layout
    freeze_panes="A2",
    auto_filter=True,
    column_widths={"A": 25, "F": 15},
    
    # Protection
    protected=False,
    password=None,
)
```

### Creating Multi-Sheet Workbooks

```python
from app.infrastructure.data_exchange import create_multi_sheet_excel

sheets = [
    ExcelSheetConfig(
        name="Data",
        headers=["Name", "Value"],
        data=[["Item 1", 100], ["Item 2", 200]],
    ),
    ExcelSheetConfig(
        name="Summary",
        headers=["Metric", "Result"],
        data=[
            ["Total", 300],
            ["Average", 150],
            ["Count", 2],
        ],
    ),
]

excel_bytes = create_multi_sheet_excel(sheets, "Monthly Report")
```

### Formula Templates

| Formula | Template | Description |
| --- | --- | --- |
| Sum | `=SUM(B{row}:E{row})` | Sum of range |
| Average | `=AVERAGE(B{row}:E{row})` | Average of range |
| Count | `=COUNT(B{row}:E{row})` | Count numbers |
| Percentage | `=B{row}/F{row}` | Calculate percentage |
| Conditional | `=IF(F{row}>100,"High","Low")` | Conditional logic |

### Conditional Formatting Rules

| Rule Type | Description |
| --- | --- |
| `COLOR_SCALE` | Gradient colors based on value |
| `DATA_BAR` | In-cell bar chart |
| `ICON_SET` | Traffic lights, arrows, etc. |
| `FORMULA` | Custom formula-based formatting |

### Data Validation Types

| Type | Description | Example |
| --- | --- | --- |
| `list` | Dropdown list | Status options |
| `whole` | Whole numbers | Age, quantity |
| `decimal` | Decimal numbers | Price, percentage |
| `date` | Date values | Due dates |
| `textLength` | Text length limit | Comments |

---

## Report Templates API

### Create Template

```http
POST /api/v1/report-templates
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Monthly Sales Report",
  "entity": "users",
  "title": "Monthly Sales Report",
  "format": "pdf",
  "columns": ["name", "email", "created_at"],
  "filters": [
    {"field": "is_active", "operator": "eq", "value": true}
  ],
  "include_summary": true,
  "page_orientation": "landscape",
  "watermark": "CONFIDENTIAL",
  "include_charts": true,
  "is_public": false,
  "tags": ["sales", "monthly"]
}
```

### Schedule Report

```http
POST /api/v1/report-templates/{template_id}/schedule
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Weekly Sales Email",
  "frequency": {
    "type": "weekly",
    "day_of_week": 0,
    "time": "09:00",
    "timezone": "UTC"
  },
  "delivery_method": "email",
  "recipients": ["manager@company.com", "cfo@company.com"],
  "enabled": true
}
```

### List Schedules

```http
GET /api/v1/report-templates/schedules
Authorization: Bearer {token}
```

### Run Schedule Now

```http
POST /api/v1/report-templates/schedules/{schedule_id}/run
Authorization: Bearer {token}
```

---

## API Reference

### Report Template Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/report-templates` | Create template |
| `GET` | `/report-templates` | List templates |
| `GET` | `/report-templates/{id}` | Get template |
| `PATCH` | `/report-templates/{id}` | Update template |
| `DELETE` | `/report-templates/{id}` | Delete template |
| `POST` | `/report-templates/{id}/duplicate` | Duplicate template |

### Scheduling Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/report-templates/{id}/schedule` | Create schedule |
| `GET` | `/report-templates/schedules` | List schedules |
| `GET` | `/report-templates/schedules/{id}` | Get schedule |
| `PATCH` | `/report-templates/schedules/{id}` | Update schedule |
| `DELETE` | `/report-templates/schedules/{id}` | Delete schedule |
| `POST` | `/report-templates/schedules/{id}/run` | Run now |
| `POST` | `/report-templates/schedules/{id}/toggle` | Toggle enabled |

### Schedule Frequencies

| Type | Description | Required Fields |
| --- | --- | --- |
| `once` | Run once | `time` |
| `daily` | Every day | `time` |
| `weekly` | Every week | `day_of_week`, `time` |
| `monthly` | Every month | `day_of_month`, `time` |
| `quarterly` | Every quarter | `time` |

---

## Integration Example

### Generating a Complete Report

```python
from app.infrastructure.data_exchange import (
    get_reporter,
    PDFConfig,
    PageOrientation,
)
from app.domain.ports.reports import ReportRequest, ReportFormat

# Configure PDF options
pdf_config = PDFConfig(
    company_name="Acme Corporation",
    orientation=PageOrientation.LANDSCAPE,
    watermark_text="INTERNAL USE ONLY",
    show_page_numbers=True,
)

# Generate report
reporter = get_reporter(session)
result = await reporter.generate(
    ReportRequest(
        entity="users",
        title="User Activity Report",
        format=ReportFormat.PDF,
        columns=["email", "first_name", "last_name", "created_at", "is_active"],
        filters=[
            ReportFilter(field="is_active", operator="eq", value=True)
        ],
        include_summary=True,
        group_by=["role"],
    ),
    pdf_config=pdf_config,
)

# Return as response
return StreamingResponse(
    io.BytesIO(result.content),
    media_type=result.content_type,
    headers={"Content-Disposition": f"attachment; filename={result.filename}"}
)
```

---

## Fallback Behavior

When optional dependencies are not installed:

| Missing Dependency | Behavior |
| --- | --- |
| `weasyprint` | PDF requests return styled HTML |
| `openpyxl` | Excel requests fail with 400 error |

Check availability programmatically:

```python
from app.infrastructure.data_exchange import is_pdf_available, is_advanced_excel_available

if is_pdf_available():
    # Generate PDF
    pass
else:
    # Fall back to HTML
    pass

if is_advanced_excel_available():
    # Generate Excel with advanced features
    pass
else:
    # Use basic CSV export
    pass
```

---

## Best Practices

1. **Use templates** for frequently generated reports
2. **Schedule reports** for regular deliveries
3. **Include charts** for executive summaries
4. **Add conditional formatting** to highlight important data
5. **Use watermarks** for confidential documents
6. **Set landscape orientation** for wide tables
7. **Limit data** to avoid massive files

---

**Last Updated:** February 2026  
**Version:** 1.4.0
