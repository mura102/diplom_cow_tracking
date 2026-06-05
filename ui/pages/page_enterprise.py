"""
ui/pages/page_enterprise.py
Страница «Предприятие» — реестр сотрудников.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QTableWidget, QHeaderView, QStackedWidget,
)


def build(mw) -> QWidget:
    """mw получает атрибуты: ent_stack, ent_table"""
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(14)

    title = QLabel("РЕЕСТР ПРЕДПРИЯТИЯ")
    title.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
    mw.page_titles.append(title)
    layout.addWidget(title)

    mw.ent_stack = QStackedWidget()
    mw.ent_table = QTableWidget()
    mw.ent_table.setColumnCount(4)
    mw.ent_table.setHorizontalHeaderLabels(["ID", "ФИО", "Телефон", "Email"])
    mw.ent_table.horizontalHeader().setSectionResizeMode(
        QHeaderView.ResizeMode.Stretch)
    mw.ent_table.setAlternatingRowColors(True)
    mw.ent_stack.addWidget(mw.ent_table)
    layout.addWidget(mw.ent_stack, stretch=1)
    return page
