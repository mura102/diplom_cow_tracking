from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import os


C_DARK_BLUE = colors.HexColor("#1F4E79")
C_MID_BLUE = colors.HexColor("#2E75B6")
C_LIGHT_GRAY = colors.HexColor("#F5F5F5")
C_BORDER = colors.HexColor("#B0C4DE")
C_TEXT = colors.HexColor("#2C2C2C")


def _register_fonts() -> str:
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            name = os.path.splitext(os.path.basename(path))[0]
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name
            except Exception:
                continue
    return "Helvetica"


def _build_styles(font_name: str) -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Heading1"],
            fontName=font_name,
            fontSize=18,
            textColor=C_DARK_BLUE,
            alignment=1,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=10,
            textColor=colors.HexColor("#666666"),
            alignment=1,
            spaceAfter=12,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Heading2"],
            fontName=font_name,
            fontSize=12,
            textColor=C_DARK_BLUE,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=9,
            textColor=C_TEXT,
            leading=13,
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=8,
            textColor=colors.HexColor("#999999"),
            alignment=1,
        ),
    }


def _make_table(data: list[list], col_widths: list[float], font_name: str) -> Table:
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_DARK_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), font_name),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("FONTNAME", (0, 1), (-1, -1), font_name),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_LIGHT_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
    ])
    tbl.setStyle(style)
    return tbl


def generate_pdf_report(
    activity_stats: list[dict],
    cow_summary: list[dict],
    save_path: str,
    company_name: str = "Рога и Копыта",
    period_days: int = 7,
) -> str:
    font_name = _register_fonts()
    styles = _build_styles(font_name)

    doc = SimpleDocTemplate(
        save_path,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    story = []
    usable_width = A4[0] - 30 * mm

    story.append(Paragraph(f"🐄 {company_name}", styles["title"]))
    story.append(Paragraph(
        f"Отчёт по статистике активности животных | "
        f"Период: последние {period_days} дней | "
        f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        styles["subtitle"],
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=C_MID_BLUE, spaceAfter=10))

    story.append(Paragraph("1. Сводка по стаду", styles["section"]))

    if cow_summary:
        headers = ["Метка", "Порода", "Вес, кг", "Статус", "Последний осмотр", "Событий"]
        col_w = [
            usable_width * 0.12,
            usable_width * 0.22,
            usable_width * 0.12,
            usable_width * 0.16,
            usable_width * 0.18,
            usable_width * 0.12,
        ]
        data = [headers]
        for cow in cow_summary:
            dt = cow.get("last_inspection")
            dt_str = dt.strftime("%d.%m.%Y %H:%M") if hasattr(dt, "strftime") else (str(dt) if dt else "—")
            weight = cow.get("weight_kg")
            weight_str = f"{weight:.0f}" if isinstance(weight, (int, float)) else "—"
            data.append([
                str(cow.get("tag_number", "—")),
                str(cow.get("breed", "—")),
                weight_str,
                str(cow.get("status", "—")),
                dt_str,
                str(cow.get("total_events", 0)),
            ])
        story.append(_make_table(data, col_w, font_name))
    else:
        story.append(Paragraph("Данные по стаду недоступны.", styles["body"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("2. Детальная статистика активности", styles["section"]))

    if activity_stats:
        headers = ["Метка коровы", "Дата", "Уровень", "Количество событий"]
        col_w = [
            usable_width * 0.20,
            usable_width * 0.20,
            usable_width * 0.30,
            usable_width * 0.30,
        ]
        data = [headers]
        level_map = {
            "CRITICAL": "Критическое",
            "WARNING": "Предупреждение",
            "INFO": "Информация",
        }
        for row in activity_stats:
            d = row.get("date")
            d_str = d.strftime("%d.%m.%Y") if hasattr(d, "strftime") else (str(d) if d else "—")
            level_raw = str(row.get("event_type", "—"))
            level_str = level_map.get(level_raw.upper(), level_raw)
            data.append([
                str(row.get("cow_tag", "—")),
                d_str,
                level_str,
                str(row.get("event_count", 0)),
            ])
        story.append(_make_table(data, col_w, font_name))
    else:
        story.append(Paragraph("Нет данных об активности за выбранный период.", styles["body"]))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Документ сформирован автоматически системой «{company_name}» | "
        f"{datetime.now().strftime('%d.%m.%Y %H:%M')}",
        styles["footer"],
    ))

    doc.build(story)
    return save_path