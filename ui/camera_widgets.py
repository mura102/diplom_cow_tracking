"""
ui/camera_widgets.py
Виджеты, связанные с камерами:
  - CameraSelectionDialog  — диалог выбора устройства
  - CameraRemoveDialog     — диалог удаления камеры
  - CameraFeedWidget       — виджет трансляции одной камеры
"""
import math
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtMultimedia import QMediaDevices

from vision.worker import VideoWorker


class CameraSelectionDialog(QDialog):
    def __init__(self, active_indexes=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор устройства видеозахвата")
        self.setFixedSize(400, 160)
        if parent:
            self.setStyleSheet(parent.styleSheet())
        self.active_indexes = active_indexes if active_indexes is not None else []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        lbl = QLabel("Доступные камеры в системе:")
        lbl.setStyleSheet("font-weight: bold; border: none;")
        layout.addWidget(lbl)
        self.combo = QComboBox()
        cameras = QMediaDevices.videoInputs()
        if not cameras:
            self.combo.addItem("Устройства не найдены", -1)
            self.combo.setEnabled(False)
        else:
            for index, cam in enumerate(cameras):
                if index in self.active_indexes:
                    self.combo.addItem(
                        f"[{index}] {cam.description()} (УЖЕ ПОДКЛЮЧЕНА)", -1)
                else:
                    self.combo.addItem(f"[{index}] {cam.description()}", index)
        layout.addWidget(self.combo)
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("ПОДКЛЮЧИТЬ")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("ОТМЕНА")
        self.btn_cancel.setObjectName("ExitBtn")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        layout.addLayout(btn_layout)
        self.combo.currentIndexChanged.connect(self.validate_selection)
        self.validate_selection()

    def validate_selection(self):
        data = self.combo.currentData()
        if data == -1 or data is None:
            self.btn_ok.setEnabled(False)
            self.btn_ok.setStyleSheet(
                "background-color: #555555; color: #888888; border: none;")
        else:
            self.btn_ok.setEnabled(True)
            self.btn_ok.setStyleSheet("")

    def get_camera_index(self):
        return self.combo.currentData()


class CameraRemoveDialog(QDialog):
    def __init__(self, active_cameras, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Отключение устройства")
        self.setFixedSize(400, 160)
        if parent:
            self.setStyleSheet(parent.styleSheet())
        layout = QVBoxLayout(self)
        lbl = QLabel("Выберите камеру для удаления из сетки:")
        lbl.setStyleSheet("font-weight: bold; border: none;")
        layout.addWidget(lbl)
        self.combo = QComboBox()
        if not active_cameras:
            self.combo.addItem("Нет активных трансляций", None)
            self.combo.setEnabled(False)
        else:
            for cam in active_cameras:
                self.combo.addItem(cam.lbl_title.text(), cam)
        layout.addWidget(self.combo)
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("УДАЛИТЬ")
        self.btn_ok.setObjectName("ExitBtn")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("ОТМЕНА")
        self.btn_cancel.setObjectName("ExitBtn")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        layout.addLayout(btn_layout)

    def get_selected_camera(self):
        return self.combo.currentData()


class CameraFeedWidget(QFrame):
    closed_signal = pyqtSignal(object)

    def __init__(self, cam_idx, cam_name, is_dark_theme, parent=None):
        super().__init__(parent)
        self.cam_idx = cam_idx
        self.is_dark_theme = is_dark_theme
        self.setObjectName("CameraFeed")
        self.setMinimumSize(320, 240)
        # Ограничение по максимальному размеру убрано — позволяет виджету
        # занимать весь доступный мультивью, когда камера одна.
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        header = QHBoxLayout()
        self.lbl_title = QLabel(f"📷 {cam_name}")
        self.lbl_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        header.addWidget(self.lbl_title)
        header.addStretch()
        self.btn_close = QPushButton("❌")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setStyleSheet(
            "background: transparent; border: none; font-size: 12px;")
        self.btn_close.clicked.connect(self.close_feed)
        header.addWidget(self.btn_close)
        layout.addLayout(header)
        self.video_label = QLabel("ПОДКЛЮЧЕНИЕ...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: #000; border-radius: 8px;")
        layout.addWidget(self.video_label, stretch=1)
        self.apply_theme()
        self.worker = VideoWorker(cam_idx)
        self.worker.change_pixmap_signal.connect(self.update_frame)
        if hasattr(self.worker, "log_signal"):
            self.worker.log_signal.connect(lambda msg: None)
        self.worker.start()

    def update_frame(self, qt_img):
        w = self.video_label.width()
        h = self.video_label.height()
        if w > 0 and h > 0:
            pixmap = QPixmap.fromImage(qt_img).scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            # Обрезаем по центру, чтобы избежать выхода за границы виджета
            if pixmap.width() > w or pixmap.height() > h:
                x = max(0, (pixmap.width() - w) // 2)
                y = max(0, (pixmap.height() - h) // 2)
                pixmap = pixmap.copy(x, y, w, h)
            self.video_label.setPixmap(pixmap)

    def apply_theme(self):
        bg  = "#16161e" if self.is_dark_theme else "#ffffff"
        bor = "#292e42" if self.is_dark_theme else "#d1d5db"
        txt = "#a9b1d6" if self.is_dark_theme else "#1f2937"
        self.setStyleSheet(
            f"QFrame#CameraFeed {{"
            f"background-color: {bg}; border: 1px solid {bor}; border-radius: 10px;}}"
        )
        self.lbl_title.setStyleSheet(f"color: {txt}; border: none;")

    def set_dark_theme(self, is_dark):
        self.is_dark_theme = is_dark
        self.apply_theme()

    def close_feed(self):
        if self.worker.isRunning():
            self.worker.stop()
            if not self.worker.wait(3000):
                self.worker.terminate()
                self.worker.wait()
        self.closed_signal.emit(self)