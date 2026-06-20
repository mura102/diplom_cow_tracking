# -*- coding: utf-8 -*-
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import traceback
import shutil

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog,
    QFrame, QProgressBar, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont, QColor


# ══════════════════════════════════════════════════════
#  Фоновые потоки
# ══════════════════════════════════════════════════════

class BcsWorker(QThread):
    log_message = pyqtSignal(str)
    finished    = pyqtSignal(str, list)
    error       = pyqtSignal(str)

    def __init__(self, image_path: str, result_path: str,
                 cow_id=None, stream_id=None, parent=None):
        super().__init__(parent)
        self.image_path  = image_path
        self.result_path = result_path
        self.cow_id      = cow_id
        self.stream_id   = stream_id

    def run(self):
        try:
            from external_bcs.bcs_analysis import predict_bcs_all
            _, records = predict_bcs_all(
                image_path=self.image_path,
                cow_id=self.cow_id,
                stream_id=self.stream_id,
                save_result_image=True,
                result_image_path=self.result_path,
                logger=self.log_message.emit,
            )
            self.finished.emit(self.result_path, records)
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")


class BcsVideoWorker(QThread):
    log_message = pyqtSignal(str)
    finished    = pyqtSignal(str, list)
    error       = pyqtSignal(str)

    def __init__(self, video_path: str, result_path: str,
                 cow_id=None, stream_id=None, parent=None):
        super().__init__(parent)
        self.video_path  = video_path
        self.result_path = result_path
        self.cow_id      = cow_id
        self.stream_id   = stream_id

    def run(self):
        try:
            from external_bcs.bcs_analysis import process_video
            output_path, records = process_video(
                video_path=self.video_path,
                output_path=self.result_path,
                cow_id=self.cow_id,
                stream_id=self.stream_id,
                logger=self.log_message.emit,
            )
            self.finished.emit(output_path, records)
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")


# ══════════════════════════════════════════════════════
#  Главное окно
# ══════════════════════════════════════════════════════

class BcsWindow(QDialog):

    # ── Цветовые палитры ──────────────────────────────
    _DARK = {
        "bg_main":    "#1a1b26",
        "bg_card":    "#1e2030",
        "bg_deep":    "#16161e",
        "bg_btn":     "#24283b",
        "bg_hover":   "#3b4261",
        "text":       "#a9b1d6",
        "text_muted": "#565f89",
        "accent":     "#7aa2f7",
        "border":     "#292e42",
        "run_bg":     "#9ece6a",
        "run_text":   "#1a1b26",
        "run_hover":  "#b9f27c",
        "save_bg":    "#e0af68",
        "save_hover": "#fac970",
        "disabled_bg":"#2d3149",
        "disabled_fg":"#555555",
    }

    _LIGHT = {
        "bg_main":    "#f0f2f5",
        "bg_card":    "#ffffff",
        "bg_deep":    "#f9fafb",
        "bg_btn":     "#e5e7eb",
        "bg_hover":   "#d1d5db",
        "text":       "#1f2937",
        "text_muted": "#6b7280",
        "accent":     "#2563eb",
        "border":     "#d1d5db",
        "run_bg":     "#22c55e",
        "run_text":   "#ffffff",
        "run_hover":  "#16a34a",
        "save_bg":    "#f59e0b",
        "save_hover": "#d97706",
        "disabled_bg":"#e5e7eb",
        "disabled_fg":"#9ca3af",
    }

    def __init__(self, parent=None, dark: bool = True):
        super().__init__(parent)
        self.setWindowTitle("Расчёт BCS")
        self.setMinimumSize(1000, 680)
        self.setModal(True)

        self._dark        = dark
        self._worker      = None
        self._image_path  = None
        self._video_path  = None
        self._result_path = None
        self._records     = []
        self._mode        = "image"

        self._build_ui()
        self._apply_theme()

    # ─────────────────────────────────────────────────
    #  Тема
    # ─────────────────────────────────────────────────

    def _t(self) -> dict:
        return self._DARK if self._dark else self._LIGHT

    def _apply_theme(self):
        t = self._t()

        # Глобальный stylesheet диалога
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t['bg_main']};
            }}
            QWidget {{
                color: {t['text']};
                background-color: {t['bg_main']};
            }}
            QLabel {{
                color: {t['text']};
                background-color: transparent;
                border: none;
            }}
            QSplitter::handle {{
                background: {t['border']};
            }}
        """)

        # Заголовок
        self.lbl_title.setStyleSheet(f"color: {t['accent']}; border: none;")

        # Прогресс-бар
        self.progress.setStyleSheet(f"""
            QProgressBar {{ border: none; background: {t['bg_deep']}; }}
            QProgressBar::chunk {{ background: {t['accent']}; border-radius: 2px; }}
        """)

        # Панель управления
        self.frame_controls.setStyleSheet(
            f"QFrame {{ background: {t['bg_card']}; border-radius: 6px; }}"
        )

        btn_load_style = f"""
            QPushButton {{
                background: {t['bg_btn']}; color: {t['text']};
                border: 1px solid {t['border']}; border-radius: 4px;
                font-size: 13px; padding: 7px 16px;
            }}
            QPushButton:hover {{ background: {t['bg_hover']}; }}
        """
        btn_run_style = f"""
            QPushButton {{
                background: {t['run_bg']}; color: {t['run_text']};
                font-weight: bold; border-radius: 4px;
                font-size: 13px; padding: 7px 16px; border: none;
            }}
            QPushButton:disabled {{
                background: {t['disabled_bg']}; color: {t['disabled_fg']};
            }}
            QPushButton:hover:enabled {{ background: {t['run_hover']}; }}
        """
        self.btn_load.setStyleSheet(btn_load_style)
        self.btn_load_video.setStyleSheet(btn_load_style)
        self.btn_run.setStyleSheet(btn_run_style)
        self.lbl_file.setStyleSheet(
            f"color: {t['text_muted']}; font-size: 12px; border: none;"
        )

        # Панель изображения
        self.frame_image.setStyleSheet(
            f"QFrame {{ background: {t['bg_card']}; border-radius: 6px; }}"
        )
        btn_tab_style = f"""
            QPushButton {{
                background: {t['bg_btn']}; color: {t['text']};
                border: 1px solid {t['border']}; border-radius: 4px;
                font-size: 13px; padding: 6px 12px;
            }}
            QPushButton:checked {{
                background: {t['accent']}; color: {'#1a1b26' if self._dark else '#ffffff'};
                font-weight: bold;
            }}
            QPushButton:hover:!checked {{ background: {t['bg_hover']}; }}
            QPushButton:disabled {{ color: {t['disabled_fg']}; border-color: {t['border']}; }}
        """
        self.btn_show_src.setStyleSheet(btn_tab_style)
        self.btn_show_res.setStyleSheet(btn_tab_style)
        self.lbl_image.setStyleSheet(f"""
            QLabel {{
                background: {t['bg_deep']}; color: {t['text_muted']};
                border: 2px dashed {t['border']}; border-radius: 6px; font-size: 14px;
            }}
        """)

        # Панель результатов
        self.frame_results.setStyleSheet(
            f"QFrame {{ background: {t['bg_card']}; border-radius: 6px; }}"
        )
        self.lbl_results_title.setStyleSheet(
            f"color: {t['text']}; font-weight: bold; font-size: 13px; border: none;"
        )
        self.lbl_log_title.setStyleSheet(
            f"color: {t['text']}; font-weight: bold; font-size: 13px; border: none;"
        )
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background: {t['bg_deep']}; color: {t['text']};
                border: 1px solid {t['border']}; gridline-color: {t['border']};
            }}
            QHeaderView::section {{
                background: {t['bg_btn']}; color: {t['accent']};
                border: 1px solid {t['border']}; padding: 4px; font-weight: bold;
            }}
            QTableWidget::item:alternate {{ background: {t['bg_card']}; }}
            QHeaderView::section:vertical {{ width: 0; border: none; }}
        """)
        self.log_box.setStyleSheet(f"""
            QTextEdit {{
                background: {t['bg_deep']}; color: {t['text']};
                font-family: Consolas, monospace; font-size: 12px;
                border: 1px solid {t['border']}; border-radius: 4px;
            }}
        """)

        # Нижняя панель
        self.frame_bottom.setStyleSheet("QFrame { background: transparent; }")
        self.lbl_status.setStyleSheet(
            f"color: {t['text_muted']}; font-size: 12px; border: none;"
        )
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background: {t['save_bg']}; color: {'#1a1b26' if self._dark else '#ffffff'};
                font-weight: bold; border-radius: 4px;
                font-size: 13px; padding: 7px 18px; border: none;
            }}
            QPushButton:disabled {{
                background: {t['disabled_bg']}; color: {t['disabled_fg']};
            }}
            QPushButton:hover:enabled {{ background: {t['save_hover']}; }}
        """)
        self.btn_close.setStyleSheet(f"""
            QPushButton {{
                background: {t['bg_btn']}; color: {t['text']};
                border: 1px solid {t['border']}; border-radius: 4px;
                font-size: 13px; padding: 7px 18px;
            }}
            QPushButton:hover {{ background: {t['bg_hover']}; }}
        """)

    # ─────────────────────────────────────────────────
    #  Построение UI
    # ─────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        self.lbl_title = QLabel("Анализ упитанности (BCS)")
        self.lbl_title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        root.addWidget(self.lbl_title)

        root.addWidget(self._build_controls())

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(4)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_image_panel())
        splitter.addWidget(self._build_results_panel())
        splitter.setSizes([520, 460])
        root.addWidget(splitter, stretch=1)

        root.addWidget(self._build_bottom_bar())

    def _build_controls(self) -> QFrame:
        self.frame_controls = QFrame()
        lay = QHBoxLayout(self.frame_controls)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(10)

        self.btn_load = QPushButton("Загрузить фото")
        self.btn_load.clicked.connect(self._load_image)

        self.btn_load_video = QPushButton("Загрузить видео")
        self.btn_load_video.clicked.connect(self._load_video)

        self.btn_run = QPushButton("Запустить расчёт")
        self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self._run_analysis)

        self.lbl_file = QLabel("Файл не выбран")
        self.lbl_file.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        lay.addWidget(self.btn_load)
        lay.addWidget(self.btn_load_video)
        lay.addWidget(self.btn_run)
        lay.addWidget(self.lbl_file)
        return self.frame_controls

    def _build_image_panel(self) -> QFrame:
        self.frame_image = QFrame()
        lay = QVBoxLayout(self.frame_image)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        tab_row = QHBoxLayout()
        tab_row.setSpacing(6)

        self.btn_show_src = QPushButton("Исходное фото")
        self.btn_show_res = QPushButton("Результат")

        for b in (self.btn_show_src, self.btn_show_res):
            b.setCheckable(True)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.btn_show_src.setChecked(True)
        self.btn_show_res.setEnabled(False)
        self.btn_show_src.clicked.connect(lambda: self._switch_image_view("src"))
        self.btn_show_res.clicked.connect(lambda: self._switch_image_view("res"))

        tab_row.addWidget(self.btn_show_src)
        tab_row.addWidget(self.btn_show_res)
        lay.addLayout(tab_row)

        self.lbl_image = QLabel("Загрузите изображение")
        self.lbl_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_image.setMinimumHeight(420)
        self.lbl_image.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        lay.addWidget(self.lbl_image, stretch=1)
        return self.frame_image

    def _build_results_panel(self) -> QFrame:
        self.frame_results = QFrame()
        lay = QVBoxLayout(self.frame_results)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        self.lbl_results_title = QLabel("Результаты по коровам")
        lay.addWidget(self.lbl_results_title)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "БКС", "Уверенность"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setFixedHeight(200)
        lay.addWidget(self.table)

        self.lbl_log_title = QLabel("Лог выполнения")
        lay.addWidget(self.lbl_log_title)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("Здесь будет отображаться ход выполнения...")
        lay.addWidget(self.log_box, stretch=1)
        return self.frame_results

    def _build_bottom_bar(self) -> QFrame:
        self.frame_bottom = QFrame()
        lay = QHBoxLayout(self.frame_bottom)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(8)

        self.lbl_status = QLabel("Ожидание загрузки изображения...")

        self.btn_save = QPushButton("Сохранить")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._save_result)

        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.reject)

        lay.addWidget(self.lbl_status)
        lay.addStretch()
        lay.addWidget(self.btn_save)
        lay.addWidget(self.btn_close)
        return self.frame_bottom

    # ─────────────────────────────────────────────────
    #  Логика
    # ─────────────────────────────────────────────────

    def _load_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите изображение", "",
            "Изображения (*.jpg *.jpeg *.png *.bmp *.tiff)"
        )
        if not path:
            return
        self._mode        = "image"
        self._image_path  = path
        self._video_path  = None
        self._result_path = None
        self._records     = []

        self.lbl_file.setText(os.path.basename(path))
        self.btn_run.setEnabled(True)
        self.btn_save.setEnabled(False)
        self.btn_show_res.setEnabled(False)
        self.btn_show_src.setChecked(True)
        self.btn_show_res.setChecked(False)
        self.table.setRowCount(0)
        self.log_box.clear()
        self._show_pixmap(path)
        self._set_status(f"Загружено фото: {os.path.basename(path)}")

    def _load_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите видео", "",
            "Видео (*.mp4 *.avi *.mov *.mkv)"
        )
        if not path:
            return
        self._mode        = "video"
        self._video_path  = path
        self._image_path  = None
        self._result_path = None
        self._records     = []

        self.lbl_file.setText(os.path.basename(path))
        self.btn_run.setEnabled(True)
        self.btn_save.setEnabled(False)
        self.btn_show_res.setEnabled(False)
        self.btn_show_src.setChecked(True)
        self.btn_show_res.setChecked(False)
        self.table.setRowCount(0)
        self.log_box.clear()
        self.lbl_image.setPixmap(QPixmap())
        self.lbl_image.setText(f"Видео: {os.path.basename(path)}\nНажмите «Запустить расчёт»")
        self._set_status(f"Загружено видео: {os.path.basename(path)}")

    def _run_analysis(self):
        if self._mode == "image" and not self._image_path:
            return
        if self._mode == "video" and not self._video_path:
            return

        self.btn_run.setEnabled(False)
        self.btn_load.setEnabled(False)
        self.btn_load_video.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.btn_show_res.setEnabled(False)
        self.log_box.clear()
        self.table.setRowCount(0)
        self.progress.setVisible(True)
        self._set_status("Выполняется анализ БКС...")
        self._append_log("Запуск анализа БКС с распознаванием ID...")

        if self._mode == "video":
            base, _ = os.path.splitext(self._video_path)
            result_path = base + "_bcs_result.mp4"
            self._worker = BcsVideoWorker(
                video_path=self._video_path,
                result_path=result_path,
            )
        else:
            base, ext = os.path.splitext(self._image_path)
            result_path = base + "_bcs_result" + ext
            self._worker = BcsWorker(
                image_path=self._image_path,
                result_path=result_path,
            )

        self._worker.log_message.connect(self._append_log)
        self._worker.finished.connect(self._on_success)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_success(self, result_path: str, records: list):
        self.progress.setVisible(False)
        self.btn_run.setEnabled(True)
        self.btn_load.setEnabled(True)
        self.btn_load_video.setEnabled(True)
        self._result_path = result_path
        self._records     = records

        display_records = records
        if self._mode == "video" and records:
            seen = {}
            for rec in records:
                tag = rec.get("cow_id", str(rec.get("cow_number", "")))
                if tag not in seen or rec["bcs"] > seen[tag]["bcs"]:
                    seen[tag] = rec
            display_records = list(seen.values())

        self.table.setRowCount(len(display_records))
        for row, rec in enumerate(display_records):
            bcs_val   = rec["bcs"]
            cow_label = rec.get("cow_id", rec.get("cow_number", "—"))

            item_num = QTableWidgetItem(str(cow_label))
            item_num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item_bcs = QTableWidgetItem(str(bcs_val))
            item_bcs.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if bcs_val <= 2.0:
                item_bcs.setForeground(QColor("#f7768e"))
            elif bcs_val >= 4.5:
                item_bcs.setForeground(QColor("#e0af68"))
            else:
                item_bcs.setForeground(QColor("#9ece6a"))

            item_conf = QTableWidgetItem(f"{rec['confidence']:.2f}")
            item_conf.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(row, 0, item_num)
            self.table.setItem(row, 1, item_bcs)
            self.table.setItem(row, 2, item_conf)

        if self._mode == "image" and os.path.exists(result_path):
            self.btn_show_res.setEnabled(True)
            self._switch_image_view("res")
        elif self._mode == "video" and os.path.exists(result_path):
            self.lbl_image.setPixmap(QPixmap())
            self.lbl_image.setText(
                f"Видео обработано.\nФайл: {os.path.basename(result_path)}\n"
                f"Записей в БД: {len(records)}"
            )

        has_result = bool(records) and os.path.exists(result_path)
        self.btn_save.setEnabled(has_result and self._mode == "image")

        if records:
            unique = len({r.get("cow_id", r.get("cow_number")) for r in records})
            self._set_status(f"Анализ завершён — уникальных коров: {unique}")
            self._append_log(
                f"\nАнализ завершён. Уникальных коров: {unique}, "
                f"всего измерений: {len(records)}"
            )
        else:
            self._set_status("Анализ завершён — коров не обнаружено")
            self._append_log("\nКоров не обнаружено на изображении.")

    def _on_error(self, error_text: str):
        self.progress.setVisible(False)
        self.btn_run.setEnabled(True)
        self.btn_load.setEnabled(True)
        self.btn_load_video.setEnabled(True)
        self._set_status("Ошибка анализа")
        self._append_log(f"\nОШИБКА:\n{error_text}")
        QMessageBox.critical(
            self, "Не получилось",
            "Не удалось выполнить расчёт БКС.\n\n" + error_text[:400]
        )

    def _save_result(self):
        if not self._result_path or not os.path.exists(self._result_path):
            return
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить размеченное изображение",
            "bcs_result.jpg",
            "JPEG (*.jpg);;PNG (*.png);;Все файлы (*)"
        )
        if not save_path:
            return
        try:
            shutil.copy2(self._result_path, save_path)
            self._set_status(f"Сохранено: {os.path.basename(save_path)}")
            self._append_log(f"Файл сохранён: {save_path}")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка сохранения", str(e))

    # ─────────────────────────────────────────────────
    #  Вспомогательные
    # ─────────────────────────────────────────────────

    def _switch_image_view(self, mode: str):
        self.btn_show_src.setChecked(mode == "src")
        self.btn_show_res.setChecked(mode == "res")
        if mode == "src" and self._image_path:
            self._show_pixmap(self._image_path)
        elif mode == "res" and self._result_path and os.path.exists(self._result_path):
            self._show_pixmap(self._result_path)

    def _show_pixmap(self, path: str):
        pix = QPixmap(path)
        if pix.isNull():
            self.lbl_image.setText("Не удалось загрузить изображение")
            return
        scaled = pix.scaled(
            self.lbl_image.width() - 10,
            self.lbl_image.height() - 10,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.lbl_image.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.btn_show_res.isChecked() and self._result_path:
            self._show_pixmap(self._result_path)
        elif self._image_path:
            self._show_pixmap(self._image_path)

    def _append_log(self, msg: str):
        self.log_box.append(msg)

    def _set_status(self, text: str):
        self.lbl_status.setText(text)