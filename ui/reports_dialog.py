# ui/reports_dialog.py
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QFileDialog, QProgressBar,
    QMessageBox, QGroupBox,
)
from PyQt6.QtCore import QThread, pyqtSignal


class ReportWorker(QThread):
    finished = pyqtSignal(str)
    error    = pyqtSignal(str)

    def __init__(self, report_type, save_path, conn_params, days, company_name):
        super().__init__()
        self.report_type  = report_type
        self.save_path    = save_path
        self.conn_params  = conn_params
        self.days         = days
        self.company_name = company_name

    def run(self):
        try:
            from database.reports_db import (
                fetch_notifications, fetch_activity_stats, fetch_cow_summary)
            activity = fetch_activity_stats(self.conn_params, self.days)
            cows = fetch_cow_summary(self.conn_params)
            if self.report_type == "excel":
                from reports.excel_report import generate_excel_report
                generate_excel_report(activity, cows, self.save_path,
                                      self.company_name, self.days)
            else:
                from reports.pdf_report import generate_pdf_report
                generate_pdf_report(activity, cows, self.save_path,
                                    self.company_name, self.days)
            self.finished.emit(self.save_path)
        except Exception as e:
            self.error.emit(str(e))


class BaseReportDialog(QDialog):
    # Стиль диалога полностью изолирован от стилей главного окна.
    # Это гарантирует, что кнопка «Отмена» всегда видна вне зависимости
    # от глобального STYLESHEET темы.
    _DIALOG_STYLE = """
        QDialog {
            background-color: #f0f2f5;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #c8cdd4;
            border-radius: 6px;
            margin-top: 8px;
            padding: 10px 8px 8px 8px;
            background-color: #ffffff;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
            color: #374151;
        }
        QLabel {
            color: #374151;
            border: none;
        }
        QSpinBox {
            border: 1px solid #c8cdd4;
            border-radius: 4px;
            padding: 4px 6px;
            background: #ffffff;
            color: #1f2937;
        }
        QPushButton#CancelBtn {
            background-color: #ffffff;
            border: 1.5px solid #9ca3af;
            border-radius: 5px;
            padding: 8px 18px;
            font-size: 12px;
            color: #374151;
            min-width: 80px;
        }
        QPushButton#CancelBtn:hover {
            background-color: #f3f4f6;
            border-color: #6b7280;
        }
        QPushButton#CancelBtn:pressed {
            background-color: #e5e7eb;
        }
        QPushButton#GenerateBtn {
            background-color: #1e3a5f;
            border: none;
            border-radius: 5px;
            padding: 8px 20px;
            font-size: 12px;
            font-weight: bold;
            color: #ffffff;
            min-width: 120px;
        }
        QPushButton#GenerateBtn:hover {
            background-color: #2563eb;
        }
        QPushButton#GenerateBtn:disabled {
            background-color: #9ca3af;
            color: #e5e7eb;
        }
        QProgressBar {
            border: 1px solid #c8cdd4;
            border-radius: 4px;
            height: 14px;
            background: #e5e7eb;
            text-align: center;
        }
        QProgressBar::chunk {
            background: #2563eb;
            border-radius: 3px;
        }
    """

    def __init__(self, parent=None, report_type="excel",
                 conn_params=None, company_name="Рога и Копыта"):
        super().__init__(parent)
        self.report_type  = report_type
        self.conn_params  = conn_params or {}
        self.company_name = company_name
        self.worker       = None
        self.setStyleSheet(self._DIALOG_STYLE)
        self._setup_ui()

    def _setup_ui(self):
        is_excel = self.report_type == "excel"
        self.setWindowTitle(
            "Экспорт уведомлений (Excel)" if is_excel else "Статистика активности (PDF)")
        self.setMinimumWidth(460)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Заголовок
        title_lbl = QLabel(
            "📊 Экспорт уведомлений" if is_excel else "📈 Статистика активности")
        title_lbl.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #1e3a5f; border: none;")
        layout.addWidget(title_lbl)

        # Период
        period_group = QGroupBox("Период отчёта")
        period_layout = QHBoxLayout(period_group)
        period_layout.addWidget(QLabel("За последние"))
        self.days_spin = QSpinBox()
        self.days_spin.setRange(1, 365)
        self.days_spin.setValue(30 if is_excel else 7)
        self.days_spin.setSuffix(" дн.")
        self.days_spin.setFixedWidth(90)
        period_layout.addWidget(self.days_spin)
        period_layout.addStretch()
        layout.addWidget(period_group)

        # Путь сохранения
        path_group = QGroupBox("Путь сохранения")
        path_layout = QHBoxLayout(path_group)
        ext = "xlsx" if is_excel else "pdf"
        ts  = datetime.now().strftime('%Y%m%d_%H%M')
        default_name = (
            f"report_notifications_{ts}.{ext}" if is_excel
            else f"report_activity_{ts}.{ext}"
        )
        default_path = os.path.join(os.path.expanduser("~"), "Documents", default_name)
        self.path_label = QLabel(default_path)
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet("color: #4b5563; font-size: 11px; border: none;")

        browse_btn = QPushButton("📁 Обзор...")
        browse_btn.setFixedWidth(90)
        browse_btn.setObjectName("GenerateBtn")  # переиспользуем стиль синей кнопки
        browse_btn.clicked.connect(self._browse_path)

        path_layout.addWidget(self.path_label, 1)
        path_layout.addWidget(browse_btn)
        layout.addWidget(path_group)

        # Прогресс-бар
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Кнопки действий
        btn_layout = QHBoxLayout()

        self.gen_btn = QPushButton(
            "📄 Создать Excel" if is_excel else "📄 Создать PDF")
        self.gen_btn.setObjectName("GenerateBtn")
        self.gen_btn.clicked.connect(self._generate)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("CancelBtn")   # ← ключевое: именованный стиль
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.gen_btn)
        layout.addLayout(btn_layout)

    def _browse_path(self):
        ext     = "xlsx" if self.report_type == "excel" else "pdf"
        filter_ = "Excel файлы (*.xlsx)" if ext == "xlsx" else "PDF файлы (*.pdf)"
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчёт", self.path_label.text(), filter_)
        if path:
            self.path_label.setText(path)

    def _generate(self):
        save_path = self.path_label.text().strip()
        if not save_path:
            QMessageBox.warning(self, "Ошибка", "Укажите путь для сохранения файла.")
            return
        save_dir = os.path.dirname(save_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
        self.gen_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.worker = ReportWorker(
            self.report_type, save_path, self.conn_params,
            self.days_spin.value(), self.company_name)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_finished(self, path: str):
        self.progress.setVisible(False)
        self.gen_btn.setEnabled(True)
        msg = QMessageBox(self)
        msg.setWindowTitle("Отчёт готов")
        msg.setText("✅ Отчёт успешно сформирован!")
        msg.setInformativeText(path)
        msg.setStandardButtons(
            QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Ok)
        result = msg.exec()
        if result == QMessageBox.StandardButton.Open:
            if os.name == "nt":
                os.startfile(path)
            else:
                os.system(f'xdg-open "{path}"')
        self.accept()

    def _on_error(self, error_msg: str):
        self.progress.setVisible(False)
        self.gen_btn.setEnabled(True)
        QMessageBox.critical(
            self, "Ошибка формирования отчёта",
            f"Не удалось создать отчёт:\n\n{error_msg}\n\n"
            "Проверьте подключение к БД и наличие таблиц.")