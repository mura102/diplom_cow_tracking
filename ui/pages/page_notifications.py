"""
ui/pages/page_notifications.py
Страница «Уведомления» — архив событий.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QTableWidget, QHeaderView,
)


def build(mw) -> QWidget:
    """mw получает атрибут: notif_table"""
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(14)

    title = QLabel("АРХИВ СОБЫТИЙ")
    title.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
    mw.page_titles.append(title)
    layout.addWidget(title)

    mw.notif_table = QTableWidget()
    mw.notif_table.setColumnCount(4)
    mw.notif_table.setHorizontalHeaderLabels(["Время", "Тип", "Объект", "Сообщение"])
    mw.notif_table.horizontalHeader().setSectionResizeMode(
        3, QHeaderView.ResizeMode.Stretch)
    mw.notif_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    mw.notif_table.setAlternatingRowColors(True)
    layout.addWidget(mw.notif_table, stretch=1)
    return page
