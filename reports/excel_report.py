# reports/excel_report.py
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime


COLOR_HEADER    = "1F4E79"
COLOR_ROW_ODD   = "EBF3FB"
COLOR_ROW_EVEN  = "FFFFFF"
SEVERITY_COLORS = {
    "critical": "FFCCCC",
    "warning":  "FFF3CC",
    "info":     "CCFFCC",
}
THIN_BORDER = Border(
    left=Side(style="thin", color="B0C4DE"),
    right=Side(style="thin", color="B0C4DE"),
    top=Side(style="thin", color="B0C4DE"),
    bottom=Side(style="thin", color="B0C4DE"),
)


def _header(cell, text: str):
    cell.value = text
    cell.font = Font(bold=True, color="FFFFFF", name="Calibri", size=11)
    cell.fill = PatternFill("solid", fgColor=COLOR_HEADER)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = THIN_BORDER


def _data(cell, value, row_idx: int, severity: str = ""):
    cell.value = value
    sev = severity.lower()
    if sev in SEVERITY_COLORS:
        cell.fill = PatternFill("solid", fgColor=SEVERITY_COLORS[sev])
    elif row_idx % 2 == 0:
        cell.fill = PatternFill("solid", fgColor=COLOR_ROW_ODD)
    cell.alignment = Alignment(vertical="center", wrap_text=True)
    cell.font = Font(name="Calibri", size=10)
    cell.border = THIN_BORDER


def generate_excel_report(
    notifications: list[dict],
    save_path: str,
    company_name: str = "Рога и Копыта",
) -> str:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Уведомления"
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:E1")
    t = ws["A1"]
    t.value = f"📋 Отчёт по уведомлениям — {company_name}"
    t.font = Font(bold=True, size=14, color="1F4E79", name="Calibri")
    t.alignment = Alignment(horizontal="center", vertical="center")
    t.fill = PatternFill("solid", fgColor="D6E4F0")
    ws.row_dimensions[1].height = 28

    ws.merge_cells("A2:E2")
    d = ws["A2"]
    d.value = f"Сформирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    d.font = Font(italic=True, size=9, color="666666", name="Calibri")
    d.alignment = Alignment(horizontal="right")
    ws.row_dimensions[2].height = 18

    ws.row_dimensions[3].height = 5

    headers = ["№", "Метка коровы", "Сообщение", "Уровень", "Дата и время"]
    widths = [5, 16, 50, 14, 20]
    for col, (h, w) in enumerate(zip(headers, widths), start=1):
        c = ws.cell(row=4, column=col)
        _header(c, h)
        ws.column_dimensions[get_column_letter(col)].width = w

    ws.row_dimensions[4].height = 20

    if not notifications:
        ws.merge_cells("A5:E5")
        c = ws["A5"]
        c.value = "Нет уведомлений за выбранный период"
        c.alignment = Alignment(horizontal="center")
        c.font = Font(italic=True, color="999999")
    else:
        severity_map = {
            "critical": "Критическое",
            "warning":  "Предупреждение",
            "info":     "Информация",
        }
        for idx, n in enumerate(notifications, start=1):
            row = idx + 4
            sev = str(n.get("severity", "")).lower()
            ts = n.get("created_at")
            if hasattr(ts, "strftime"):
                ts_str = ts.strftime("%d.%m.%Y %H:%M")
            else:
                ts_str = str(ts) if ts else "—"
            values = [
                idx,
                n.get("cow_tag", "—"),
                n.get("message", ""),
                severity_map.get(sev, sev.upper() or "—"),
                ts_str,
            ]
            for col, val in enumerate(values, start=1):
                cell = ws.cell(row=row, column=col)
                _data(cell, val, idx, sev if col == 4 else "")
            ws.row_dimensions[row].height = 18

    wb.save(save_path)
    return save_path