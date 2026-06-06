# ui/bcs_result_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class BcsResultDialog(QDialog):

    def __init__(self, records: list, log_text: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Результат расчёта КВС / БКС")
        self.setMinimumSize(650, 480)
        self.setModal(True)
        self._build_ui(records, log_text)

    def _build_ui(self, records, log_text):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Заголовок
        title = QLabel("✅ Анализ БКС завершён")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))  # ← PyQt6: Weight.Bold
        title.setStyleSheet("color: #4CAF50;")
        layout.addWidget(title)

        sub = QLabel(f"Обнаружено коров: {len(records)}")
        sub.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(sub)

        # Таблица результатов
        if records:
            table = QTableWidget(len(records), 3)
            table.setHorizontalHeaderLabels(["ID", "БКС", "Уверенность"])
            table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch   # ← PyQt6: ResizeMode.Stretch
            )
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(
                QTableWidget.EditTrigger.NoEditTriggers  # ← PyQt6: EditTrigger.
            )
            table.setAlternatingRowColors(True)

            for row, rec in enumerate(records):
                cow_label = rec.get("cow_id", rec.get("cow_number", "—"))
                table.setItem(row, 0, QTableWidgetItem(str(cow_label)))
                table.setItem(row, 1, QTableWidgetItem(str(rec["bcs"])))
                table.setItem(row, 2, QTableWidgetItem(f"{rec['confidence']:.2f}"))

            layout.addWidget(table)
        else:
            no_data = QLabel("⚠ Коров на изображении не обнаружено")
            no_data.setStyleSheet("color: #FFA726; font-size: 13px;")
            layout.addWidget(no_data)

        # Лог выполнения
        if log_text:
            log_label = QLabel("Лог выполнения:")
            log_label.setStyleSheet("font-size: 11px; color: #888; margin-top: 6px;")
            layout.addWidget(log_label)

            log_box = QTextEdit()
            log_box.setReadOnly(True)
            log_box.setPlainText(log_text)
            log_box.setMaximumHeight(130)
            log_box.setStyleSheet("""
                QTextEdit {
                    background: #1e1e1e;
                    color: #a9b1d6;
                    font-family: Consolas, monospace;
                    font-size: 11px;
                    border: 1px solid #333;
                    border-radius: 4px;
                }
            """)
            layout.addWidget(log_box)

        # Кнопка закрыть
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.setMinimumWidth(110)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)