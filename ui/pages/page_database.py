"""
ui/pages/page_database.py
Страница «База данных» — SQL-консоль.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton,
    QLabel, QTextEdit, QTableWidget, QHeaderView,
)
from PyQt6.QtCore import Qt


def build(mw) -> QWidget:
    """
    mw получает атрибуты: sql_input (если роль != vet), db_table, lbl_sql_status
    """
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(14)

    title = QLabel("SQL КОНСОЛЬ")
    title.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
    mw.page_titles.append(title)
    layout.addWidget(title)

    if mw.user_role == "vet":
        placeholder = QLabel(
            "⛔ ДОСТУП ОГРАНИЧЕН\n\n"
            "У вас нет прав для просмотра и редактирования базы данных.")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("AccessDeniedLabel")
        layout.addWidget(placeholder, stretch=1)
    else:
        mw.sql_input = QTextEdit()
        mw.sql_input.setPlaceholderText(
            "Введите запрос... (например: SELECT * FROM cows;)")
        mw.sql_input.setFixedHeight(100)
        layout.addWidget(mw.sql_input)

        btn = QPushButton("ВЫПОЛНИТЬ ЗАПРОС")
        btn.clicked.connect(mw.execute_sql_query)
        layout.addWidget(btn)

        # --- НОВЫЙ ЛЕЙБЛ ДЛЯ СТАТУСА ---
        mw.lbl_sql_status = QLabel("")
        mw.lbl_sql_status.setStyleSheet("font-size: 14px; font-weight: bold; border: none;")
        mw.lbl_sql_status.setWordWrap(True)
        layout.addWidget(mw.lbl_sql_status)

        mw.db_table = QTableWidget()
        mw.db_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        layout.addWidget(mw.db_table, stretch=1)

    return page