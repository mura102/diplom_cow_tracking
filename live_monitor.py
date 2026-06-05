import sys
import os
import platform

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

if platform.system() == "Windows":
    venv_path = sys.prefix
    plugins_path = os.path.join(venv_path, "Lib", "site-packages", "PyQt6", "Qt6", "plugins")
    if os.path.exists(plugins_path):
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugins_path

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QLabel, QPushButton, QHBoxLayout, QDialog,
                             QStatusBar, QSizePolicy)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from vision.worker import VideoWorker
from ui.main_window import CameraSelectionDialog
from ui.styles import STYLESHEET_DARK


class LiveMonitorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Рога и Копыта — Тест прямого эфира")
        self.setStyleSheet(STYLESHEET_DARK)
        self.setMinimumSize(800, 550)

        # Старт в 80% от рабочего стола, по центру
        screen = QApplication.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            w = int(available.width()  * 0.80)
            h = int(available.height() * 0.85)
            self.resize(w, h)
            self.move(
                available.x() + (available.width()  - w) // 2,
                available.y() + (available.height() - h) // 2,
            )
        else:
            self.resize(1000, 700)

        self.worker = None
        self._current_cam_idx = None

        self.init_ui()
        self._create_status_bar()

    def _create_status_bar(self):
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Готово. Выберите камеру для начала трансляции.")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        self.title_label = QLabel("МОНИТОРИНГ ПРЯМОГО ЭФИРА")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(
            "color: #7aa2f7; font-size: 18px; font-weight: bold; border: none;"
        )
        layout.addWidget(self.title_label)

        self.lbl_cam_info = QLabel("Камера не выбрана")
        self.lbl_cam_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_cam_info.setStyleSheet("color: #565f89; font-size: 11px; border: none;")
        layout.addWidget(self.lbl_cam_info)

        # Видео-зона: растягивается, но не уходит за экран
        self.video_display = QLabel("ОЖИДАНИЕ ПОДКЛЮЧЕНИЯ...")
        self.video_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_display.setMinimumHeight(200)
        self.video_display.setMaximumHeight(560)
        self.video_display.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.video_display.setStyleSheet("""
            background-color: #000000;
            border: 2px solid #292e42;
            border-radius: 15px;
            color: #565f89;
            font-size: 14px;
            font-weight: bold;
        """)
        layout.addWidget(self.video_display, stretch=1)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_select = QPushButton("🔌 ВЫБРАТЬ КАМЕРУ")
        self.btn_select.setFixedWidth(200)
        self.btn_select.clicked.connect(self.select_and_start)

        self.btn_stop = QPushButton("⏹ ОСТАНОВИТЬ")
        self.btn_stop.setFixedWidth(200)
        self.btn_stop.setObjectName("ExitBtn")
        self.btn_stop.clicked.connect(self.stop_stream)
        self.btn_stop.setEnabled(False)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_select)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def select_and_start(self):
        dialog = CameraSelectionDialog([], self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            cam_idx = dialog.get_camera_index()
            if cam_idx is not None and cam_idx != -1:
                cam_name = dialog.combo.currentText()
                self._current_cam_idx = cam_idx
                self.lbl_cam_info.setText(f"Камера: {cam_name}")
                self.start_stream(cam_idx)

    def start_stream(self, index: int):
        self._stop_worker()
        self.worker = VideoWorker(index)
        self.worker.change_pixmap_signal.connect(self.update_frame)
        if hasattr(self.worker, 'log_signal'):
            self.worker.log_signal.connect(
                lambda msg: self._status_bar.showMessage(msg)
            )
        self.worker.start()
        self.btn_select.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.video_display.setText("")
        self._status_bar.showMessage(f"Трансляция с камеры [{index}] запущена.")

    def update_frame(self, qt_img):
        w = self.video_display.width()
        h = self.video_display.height()
        if w > 0 and h > 0:
            pixmap = QPixmap.fromImage(qt_img).scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.video_display.setPixmap(pixmap)

    def stop_stream(self):
        self._stop_worker()
        self.video_display.clear()
        self.video_display.setText("ПОТОК ОСТАНОВЛЕН")
        self.lbl_cam_info.setText("Камера не выбрана")
        self._current_cam_idx = None
        self.btn_select.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._status_bar.showMessage("Трансляция остановлена.")

    def _stop_worker(self):
        if self.worker is not None:
            if self.worker.isRunning():
                self.worker.stop()
                if not self.worker.wait(3000):
                    self.worker.terminate()
                    self.worker.wait()
            self.worker = None

    def closeEvent(self, event):
        self._stop_worker()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Рога и Копыта — Live Monitor")
    window = LiveMonitorApp()
    window.show()
    sys.exit(app.exec())