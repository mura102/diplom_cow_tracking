"""
ui/main_window.py
Главное окно приложения.
Вся логика построения страниц вынесена в ui/pages/*.
Виджеты камер — в ui/camera_widgets.py.
"""
import os
import math
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QFileDialog,
    QStackedWidget, QStatusBar, QDialog, QApplication, QMessageBox,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QPixmap, QFont, QAction
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from ui.styles import STYLESHEET_DARK, STYLESHEET_LIGHT
from vision.worker import VideoWorker, AnalysisWorker
from ui.notifications import WarningAlert, CriticalAlert, InfoAlert
from ui.camera_widgets import (
    CameraSelectionDialog, CameraRemoveDialog, CameraFeedWidget,
)
from ui.pages import (
    page_monitoring, page_cameras,
    page_database, page_notifications, page_enterprise,
)
from ui.bcs_worker import BcsWorker
from ui.bcs_result_dialog import BcsResultDialog
from ui.bcs_window import BcsWindow

try:
    from database.database import SessionLocal
    from database.models import Cow, Employee, Camera, Notification
    from sqlalchemy import select, func, text
    DB_AVAILABLE = True
except (ImportError, Exception):
    DB_AVAILABLE = False


class MainWindow(QMainWindow):
    def __init__(self, role: str = "sa"):
        super().__init__()
        self.user_role = role
        self.setWindowTitle("УМНАЯ ФЕРМА - Система мониторинга AI")
        self.setMinimumSize(900, 600)

        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            w, h = int(avail.width() * 0.90), int(avail.height() * 0.90)
            self.resize(w, h)
            self.move(
                avail.x() + (avail.width()  - w) // 2,
                avail.y() + (avail.height() - h) // 2,
            )
        else:
            self.resize(1350, 900)

        # ── Состояние ────────────────────────────────────────────────
        self.is_dark_theme     = True
        self.ai_worker         = None
        self._analysis_worker  = None
        self._sleep_worker     = None
        self.alert_count       = 0
        self.is_slider_pressed = False
        self.was_playing       = False
        self.nav_buttons:      list = []
        self.page_titles:      list = []
        self.active_camera_widgets: list = []
        self._kvs_running      = False
        self._active_algo      = None   # None | "activity" | "sleep"
        self._is_video_mode    = False

        self._conn_params = {
            "host":     os.environ.get("DB_HOST",     "localhost"),
            "port":     int(os.environ.get("DB_PORT", 5432)),
            "dbname":   os.environ.get("DB_NAME",     "cow_tracking_db"),
            "user":     os.environ.get("DB_USER",     "postgres"),
            "password": os.environ.get("DB_PASSWORD", "SAMsung2024"),
        }

        self.setStyleSheet(STYLESHEET_DARK)
        self._init_ui()
        self._create_menu_bar()
        self._create_status_bar()
        self._setup_media_player()
        self.refresh_db_stats()
        self.load_notifications_data()

        # Заполняем комбобокс камер при старте
        self.refresh_cameras_combo()

    # ═══════════════════════════════════════════════════════════════════
    # ПОСТРОЕНИЕ UI
    # ═══════════════════════════════════════════════════════════════════

    def _init_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())

        self.main_stack = QStackedWidget()
        for build_fn in [
            page_monitoring.build,
            page_cameras.build,
            page_database.build,
            page_notifications.build,
            page_enterprise.build,
        ]:
            self.main_stack.addWidget(build_fn(self))

        root.addWidget(self.main_stack)
        self.switch_page(0)
        self._apply_titles_style()

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(260)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(15, 30, 15, 30)
        layout.setSpacing(10)

        title = QLabel("УМНАЯ ФЕРМА")
        title.setObjectName("Title")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(30)

        nav_items = [
            ("📺 Мониторинг",  0),
            ("📹 Камеры",      1),
            ("💾 База данных", 2),
            ("🔔 Уведомления", 3),
            ("🏢 Предприятие", 4),
        ]
        for text, idx in nav_items:
            btn = QPushButton(text)
            btn.setProperty("navStyle", "nav")
            btn.clicked.connect(lambda _, i=idx: self.switch_page(i))
            self.nav_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        self.btn_theme = QPushButton("☀️ СВЕТЛАЯ ТЕМА")
        self.btn_theme.setObjectName("ThemeBtn")
        self.btn_theme.clicked.connect(self.toggle_theme)
        layout.addWidget(self.btn_theme)

        btn_exit = QPushButton("ВЫХОД ИЗ СИСТЕМЫ")
        btn_exit.setObjectName("ExitBtn")
        btn_exit.clicked.connect(self.safe_exit)
        layout.addWidget(btn_exit)
        return sidebar

    def _create_status_bar(self):
        bar = QStatusBar()
        self.setStatusBar(bar)
        roles = {"sa": "Администратор", "dir": "Директор", "vet": "Ветеринар"}
        self.lbl_status_role = QLabel(f" РОЛЬ: {roles.get(self.user_role, 'Пользователь')} |")
        self.lbl_status_db   = QLabel(
            f" БАЗА: {'ПОДКЛЮЧЕНО' if DB_AVAILABLE else 'DEMO'} ")
        self.lbl_status_db.setStyleSheet(
            f"color: {'#9ece6a' if DB_AVAILABLE else '#f7768e'};"
            f"font-weight: bold; border: none;")
        bar.addPermanentWidget(self.lbl_status_role)
        bar.addPermanentWidget(self.lbl_status_db)
        bar.showMessage("Система загружена и готова к мониторингу")

    def _create_menu_bar(self):
        mb = self.menuBar()

        sys_menu = mb.addMenu("Система")
        sys_menu.addAction(QAction("Выход", self, triggered=self.safe_exit))

        db_menu = mb.addMenu("База данных")
        db_menu.addAction(QAction("Обновить данные", self, triggered=self.refresh_db_stats))
        db_menu.addSeparator()
        #db_menu.addAction(QAction("Параметры соединения", self))
        a_backup = QAction("Резервная копия БД", self)
        a_backup.triggered.connect(self.create_db_backup)
        db_menu.addAction(a_backup)
        rep_menu = mb.addMenu("Отчеты")
        a_excel = QAction("Экспорт уведомлений (Excel)", self)
        a_excel.triggered.connect(self._open_excel_report_dialog)
        rep_menu.addAction(a_excel)
        a_pdf = QAction("Статистика активности (PDF)", self)
        a_pdf.triggered.connect(self._open_pdf_report_dialog)
        rep_menu.addAction(a_pdf)

        tools_menu = mb.addMenu("Инструменты")
        tools_menu.addAction(QAction("Очистка кэша видео", self))
        tools_menu.addAction(QAction("Калибровка YOLO моделей", self))
        if self.user_role == "vet":
            tools_menu.setEnabled(False)

        test_menu = mb.addMenu("Тестирование")
        test_menu.addAction(QAction(
            "Тест: Предупреждение (Желтый)", self,
            triggered=lambda: self.trigger_alert("C-12", "WARNING", "Низкая активность объекта.")))
        test_menu.addAction(QAction(
            "Тест: Критическое (Красный)", self,
            triggered=lambda: self.trigger_alert("A-01", "CRITICAL", "Обнаружено падение животного!")))

        help_menu = mb.addMenu("Справка")
        help_menu.addAction(QAction("О программе", self, triggered=self.show_about_info))

    def _setup_media_player(self):
        self.media_player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.media_player.setAudioOutput(self.audio)
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.positionChanged.connect(self._update_slider_position)
        self.media_player.durationChanged.connect(self._set_slider_range)
        self.media_player.playbackStateChanged.connect(self._on_playback_state_changed)

    # ═══════════════════════════════════════════════════════════════════
    # НАВИГАЦИЯ / ТЕМА
    # ═══════════════════════════════════════════════════════════════════

    def switch_page(self, index: int):
        self.main_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setProperty("navStyle", "active" if i == index else "nav")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if index == 0:
            # Обновляем список камер при каждом открытии страницы мониторинга
            self.refresh_cameras_combo()
        elif index == 3:
            self.load_notifications_data()
        elif index == 4:
            self.load_employees_data()

    def toggle_theme(self):
        self.is_dark_theme = not self.is_dark_theme
        sheet = STYLESHEET_DARK if self.is_dark_theme else STYLESHEET_LIGHT
        QApplication.instance().setStyleSheet(sheet)
        self.setStyleSheet("")

        self.btn_theme.setText("☀️ СВЕТЛАЯ ТЕМА" if self.is_dark_theme else "🌙 ТЕМНАЯ ТЕМА")

        # Кнопка play/pause
        play_color = "#3b82f6" if not self.is_dark_theme else "#7aa2f7"
        self.btn_play_pause.setStyleSheet(
            f"background-color: {play_color}; color: white;")

        # Подсказка зоны видео
        hint_color = "#565f89" if self.is_dark_theme else "#9ca3af"
        self.lbl_video_zone_hint.setStyleSheet(
            f"color:{hint_color}; font-size:11px;")

        # Цвет статус-бара
        db_color = ("#9ece6a" if DB_AVAILABLE else "#f7768e") if self.is_dark_theme \
            else ("#16a34a" if DB_AVAILABLE else "#dc2626")
        self.lbl_status_db.setStyleSheet(
            f"color: {db_color}; font-weight: bold; border: none;")

        self._apply_titles_style()
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

        for w in self.active_camera_widgets:
            w.set_dark_theme(self.is_dark_theme)
        self.update_algorithm_buttons_style()
        self.centralWidget().setStyleSheet(
            "QWidget#centralWidget { background-color: #f0f2f5; }" if not self.is_dark_theme
            else "QWidget#centralWidget { background-color: #1a1b26; }"
        )

    def _apply_titles_style(self):
        color = "#7aa2f7" if self.is_dark_theme else "#2563eb"
        style = f"color: {color}; font-size: 18px; font-weight: bold; border: none;"
        for t in self.page_titles:
            t.setStyleSheet(style)

    def update_algorithm_buttons_style(self):
        if self.is_dark_theme:
            style = """
                QPushButton {
                    background-color: #24283b; border: 1px solid #292e42;
                    color: #7aa2f7; min-height: 38px; font-weight: bold;
                    border-radius: 5px;
                }
                QPushButton:hover   { background-color: #3b4261; }
                QPushButton:checked {
                    background-color: #9ece6a; color: #1a1b26;
                    border: 1px solid #9ece6a;
                }
                QPushButton:disabled { color: #555; border-color: #333; }
            """
        else:
            style = """
                QPushButton {
                    background-color: #eff6ff; border: 1px solid #d1d5db;
                    color: #2563eb; min-height: 38px; font-weight: bold;
                    border-radius: 5px;
                }
                QPushButton:hover   { background-color: #dbeafe; }
                QPushButton:checked {
                    background-color: #22c55e; color: white;
                    border: 1px solid #22c55e;
                }
                QPushButton:disabled { color: #aaa; border-color: #ccc; }
            """
        for btn in [self.btn_detect_activity, self.btn_detect_sleep, self.btn_calc_kvs]:
            btn.setStyleSheet(style)

    # ═══════════════════════════════════════════════════════════════════
    # УТИЛИТЫ ЛОГИРОВАНИЯ
    # ═══════════════════════════════════════════════════════════════════

    def update_log(self, message: str):
        now = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{now}] {message}")

    def update_sleep_log(self, message: str):
        now = datetime.now().strftime("%H:%M:%S")
        self.sleep_log_box.append(f"[{now}] {message}")

    def update_kvs_log(self, message: str):
        now = datetime.now().strftime("%H:%M:%S")
        self.kvs_log_box.append(f"[{now}] {message}")

    # ═══════════════════════════════════════════════════════════════════
    # АЛГОРИТМЫ МОНИТОРИНГА
    # ═══════════════════════════════════════════════════════════════════

    def _block_other_algos(self, except_btn):
        for btn in [self.btn_detect_activity, self.btn_detect_sleep, self.btn_calc_kvs]:
            if btn is not except_btn:
                btn.setEnabled(False)

    def _unblock_all_algos(self):
        for btn in [self.btn_detect_activity, self.btn_detect_sleep, self.btn_calc_kvs]:
            btn.setEnabled(True)
        self.update_algorithm_buttons_style()

    # ── Камеры: загрузка и выбор ──────────────────────────────────────

    def refresh_cameras_combo(self):
        """Загружает активные камеры из БД в combo_camera_activity."""
        self.combo_camera_activity.blockSignals(True)
        self.combo_camera_activity.clear()

        if DB_AVAILABLE:
            try:
                db = SessionLocal()
                cameras = db.query(Camera).filter_by(is_active=True).all()
                db.close()
                for cam in cameras:
                    label = f"Камера {cam.id_camera} — {cam.location}"
                    self.combo_camera_activity.addItem(label, userData=cam)
                if cameras:
                    self.update_log(
                        f"📷 Камер загружено: {len(cameras)}"
                    )
                else:
                    self.combo_camera_activity.addItem("Нет активных камер", userData=None)
                    self.update_log("⚠️ Активные камеры не найдены в БД.")
            except Exception as e:
                self.combo_camera_activity.addItem("Ошибка загрузки камер", userData=None)
                self.update_log(f"⚠️ Ошибка загрузки камер: {e}")
        else:
            # Demo-режим: заглушка
            self.combo_camera_activity.addItem("Камера 1 — кормовая зона", userData=None)
            self.combo_camera_activity.addItem("Камера 2 — питьевая зона", userData=None)

        self.combo_camera_activity.blockSignals(False)

    def _set_activity_source_ui(self, video_mode: bool):
        """Переключает UI: камера из БД (живой поток) или зона для видео-теста."""
        self._is_video_mode = video_mode
        camera_widgets = (
            getattr(self, "combo_camera_activity", None),
            getattr(self, "btn_refresh_cameras", None),
        )
        for w in camera_widgets:
            if w is not None:
                w.setEnabled(not video_mode)
        zone_row = getattr(self, "_video_zone_row_widgets", ())
        for w in zone_row:
            w.setVisible(video_mode)

    def _get_video_test_zone(self) -> str:
        combo = getattr(self, "combo_video_zone", None)
        from external_activity.activity_zone import ZONE_FEED

        if combo is None:
            return ZONE_FEED
        zone = combo.currentData()
        return zone if zone else ZONE_FEED

    def _get_selected_camera_location(self) -> str:
        """
        Живой поток: location камеры из БД.
        Видеофайл: зона из combo_video_zone (тестовый режим).
        """
        if self._is_video_mode:
            return self._get_video_test_zone()

        from external_activity.activity_zone import ZONE_FEED, normalize_zone

        cam = self.combo_camera_activity.currentData()
        if cam is not None:
            loc = getattr(cam, "location", None)
            if loc:
                return normalize_zone(loc)

        text = self.combo_camera_activity.currentText()
        return normalize_zone(text)

    # ── Детекция активности (Рената) ─────────────────────────────────

    def toggle_activity_detection(self, checked: bool):
        if checked:
            self._block_other_algos(self.btn_detect_activity)
            self._active_algo = "activity"
            self.btn_detect_activity.setText("🏃 Детекция активности (СТОП)")
            if self._is_video_mode:
                zone = self._get_video_test_zone()
                self.update_log(
                    f"Мониторинг активности (видео-тест). Зона: {zone}"
                )
            else:
                cam_info = self.combo_camera_activity.currentText()
                self.update_log(f"Мониторинг активности запущен. Камера: {cam_info}")
            self._start_activity_on_video_end()
        else:
            self._active_algo = None
            self._unblock_all_algos()
            self.btn_detect_activity.setText("🏃 Детекция активности (СТАРТ)")
            self.update_log("Мониторинг активности деактивирован.")
            if self._analysis_worker:
                self._analysis_worker.terminate()
                self._analysis_worker = None

    def _pending_snapshots(self):
        if not self.ai_worker or not self.ai_worker._saved_paths:
            return None
        return self.ai_worker._saved_paths, self.ai_worker._saved_timestamps

    def _start_activity_on_video_end(self):
        if not self.ai_worker:
            self.update_log("⚠️ Сначала выберите видеофайл или камеру.")
            return
        try:
            self.ai_worker.snapshots_ready.disconnect()
        except Exception:
            pass
        self.ai_worker.snapshots_ready.connect(self._on_snapshots_ready_activity)
        pending = self._pending_snapshots()
        if pending and not self.ai_worker.isRunning():
            self.update_log(
                f"Видео уже обработано — анализ {len(pending[0])} снимков..."
            )
            self._on_snapshots_ready_activity(*pending)
        else:
            self.update_log("Анализ запустится автоматически после окончания видео.")

    def _on_snapshots_ready_activity(self, image_paths: list, timestamps: list):
        if self._active_algo != "activity":
            return

        cam_location = self._get_selected_camera_location()
        cow_number   = self._get_default_cow_number()
        activity_zone = cam_location if self._is_video_mode else None

        mode_label = "видео-тест" if self._is_video_mode else "камера"
        self.update_log(
            f"Запуск AnalysisWorker ({mode_label}): зона='{cam_location}', "
            f"снимков={len(image_paths)}, корова №{cow_number}"
        )

        self._analysis_worker = AnalysisWorker(
            image_paths=image_paths,
            timestamps=timestamps,
            camera_location=cam_location,
            cow_number=cow_number,
            activity_zone=activity_zone,
        )
        self._analysis_worker.progress.connect(self.update_log)
        self._analysis_worker.finished.connect(self._on_activity_analysis_done)
        self._analysis_worker.error.connect(self._on_activity_analysis_error)
        self._analysis_worker.start()

    def _on_activity_analysis_done(self, result: dict):
        cow_results = result.get("cow_results") or []
        if cow_results:
            summary = "; ".join(
                f"ID {cr['recognized_tag']}: "
                f"{cr.get('feed_min', cr['feed_sec'] // 60)}м "
                f"{cr.get('feed_sec_rem', cr['feed_sec'] % 60)}с"
                for cr in cow_results
            )
            self.update_log(f"✅ Анализ завершён: {summary}")
        else:
            id_label = result.get("recognized_tag") or result.get("cow_number", "—")
            self.update_log(
                f"✅ Анализ завершён: ID={id_label}, "
                f"кормление {result['feed_min']} мин {result['feed_sec']} сек, "
                f"питьё {result['drink_min']} мин {result['drink_sec']} сек"
            )
        self._show_activity_result(result)
        self._unblock_all_algos()
        self.btn_detect_activity.setChecked(False)
        self.btn_detect_activity.setText("🏃 Детекция активности (СТАРТ)")
        self._active_algo = None

    def _on_activity_analysis_error(self, error_text: str):
        self.update_log(f"❌ Ошибка анализа: {error_text[:200]}")
        QMessageBox.critical(self, "Ошибка анализа", f"Не получилось:\n{error_text}")
        self._unblock_all_algos()
        self.btn_detect_activity.setChecked(False)
        self.btn_detect_activity.setText("🏃 Детекция активности (СТАРТ)")
        self._active_algo = None

    def _show_activity_result(self, result: dict):
        from PyQt6.QtWidgets import QTextEdit
        dlg = QDialog(self)
        dlg.setWindowTitle("Результат: Детекция активности")
        dlg.setMinimumSize(480, 320)
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel("✅ Анализ активности завершён"))
        te = QTextEdit()
        te.setReadOnly(True)
        zone = result.get("activity_zone") or result.get("camera", "—")
        lines = [
            f"Зона: {zone}",
            f"Кадров: {result['num_frames']}",
            "",
            "── Итог по каждой корове ──",
        ]
        cow_results = result.get("cow_results") or []
        if cow_results:
            for cr in cow_results:
                fm = cr.get("feed_min", int(cr["feed_sec"]) // 60)
                fs = cr.get("feed_sec_rem", int(cr["feed_sec"]) % 60)
                dm = cr.get("drink_min", int(cr["drink_sec"]) // 60)
                ds = cr.get("drink_sec_rem", int(cr["drink_sec"]) % 60)
                lines.append(f"ID {cr['recognized_tag']} (корова №{cr['cow_number']}):")
                lines.append(f"  Кормление: {fm} мин ({fs} сек)")
                lines.append(f"  Питьё:     {dm} мин ({ds} сек)")
                lines.append("")
        else:
            lines.extend([
                f"ID: {result.get('recognized_tag') or result['cow_number']}",
                f"Корова №{result['cow_number']}",
                "",
                f"Время кормления : {result['feed_min']} мин ({result['feed_sec']} сек)",
                f"Время в питьевой зоне: {result['drink_min']} мин ({result['drink_sec']} сек)",
            ])
        te.setPlainText("\n".join(lines))
        lay.addWidget(te)
        btn = QPushButton("Закрыть")
        btn.clicked.connect(dlg.accept)
        lay.addWidget(btn)
        dlg.exec()

    # ── Детекция сна ──────────────────────────────────────────────────

    def toggle_sleep_detection(self, checked: bool):
        if checked:
            self._block_other_algos(self.btn_detect_sleep)
            self._active_algo = "sleep"
            self.btn_detect_sleep.setText("🌙 Детекция сна (СТОП)")
            self.update_sleep_log("Ночная модель детекции сна запущена.")
            self._start_sleep_on_video_end()
        else:
            self._active_algo = None
            self._unblock_all_algos()
            self.btn_detect_sleep.setText("🌙 Детекция сна (СТАРТ)")
            self.update_sleep_log("Детекция сна деактивирована.")
            if self._sleep_worker:
                self._sleep_worker.terminate()
                self._sleep_worker = None

    def _start_sleep_on_video_end(self):
        if not self.ai_worker:
            self.update_sleep_log("⚠️ Сначала выберите видеофайл.")
            return
        try:
            self.ai_worker.snapshots_ready.disconnect()
        except Exception:
            pass
        self.ai_worker.snapshots_ready.connect(self._on_snapshots_ready_sleep)
        pending = self._pending_snapshots()
        if pending and not self.ai_worker.isRunning():
            self.update_sleep_log(
                f"Видео уже обработано — анализ сна ({len(pending[0])} снимков)..."
            )
            self._on_snapshots_ready_sleep(*pending)
        else:
            self.update_sleep_log("Анализ сна запустится после окончания видео.")

    def _on_snapshots_ready_sleep(self, image_paths: list, timestamps: list):
        if self._active_algo != "sleep":
            return
        try:
            import datetime as dt

            from external_activity.db_config import get_default_cow_number
            from external_activity.sleep_analysis import process_sleep_sequence

            self.update_sleep_log("Запуск ночной модели сна...")
            lying_sec, standing_sec, recognized_tag, cow_results = process_sleep_sequence(
                image_paths=image_paths,
                timestamps=timestamps,
                cow_number=get_default_cow_number(),
                night_start=dt.time(22, 0),
                night_end=dt.time(5, 0),
                force_night=False,
                show_frames=False,
                save_frames=True,
                interval_sec=2.0,
            )
            for cr in cow_results:
                cr["lying_min"] = round(cr["lying_sec"] / 60, 2)
                cr["standing_min"] = round(cr["standing_sec"] / 60, 2)
            result = {
                "lying_sec": lying_sec,
                "standing_sec": standing_sec,
                "lying_min": round(lying_sec / 60, 2),
                "standing_min": round(standing_sec / 60, 2),
                "recognized_tag": recognized_tag,
                "cow_results": cow_results,
            }
            if cow_results:
                summary = "; ".join(
                    f"ID {cr['recognized_tag']}: "
                    f"лёжа {cr['lying_sec']:.0f}с"
                    for cr in cow_results
                )
                self.update_sleep_log(f"✅ Анализ сна завершён. {summary}")
            else:
                self.update_sleep_log(
                    f"✅ Анализ сна завершён. ID={recognized_tag or '—'}"
                )
            self._show_sleep_result(result)
        except Exception as e:
            import traceback
            self.update_sleep_log(f"❌ Ошибка анализа сна: {e}")
            QMessageBox.critical(self, "Ошибка анализа сна",
                                 f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")
        finally:
            self._unblock_all_algos()
            self.btn_detect_sleep.setChecked(False)
            self.btn_detect_sleep.setText("🌙 Детекция сна (СТАРТ)")
            self._active_algo = None

    def _show_sleep_result(self, result):
        from PyQt6.QtWidgets import QTextEdit
        dlg = QDialog(self)
        dlg.setWindowTitle("Результат: Детекция сна")
        dlg.setMinimumSize(480, 280)
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel("🌙 Анализ сна завершён"))
        if isinstance(result, dict):
            lines = [
                "── Итог по каждой корове ──",
            ]
            cow_results = result.get("cow_results") or []
            if cow_results:
                for cr in cow_results:
                    lines.append(f"ID {cr['recognized_tag']} (корова №{cr['cow_number']}):")
                    lines.append(
                        f"  Лёжа: {cr['lying_sec']:.1f} сек "
                        f"({cr.get('lying_min', cr['lying_sec'] / 60):.2f} мин)"
                    )
                    lines.append(
                        f"  Стоя: {cr['standing_sec']:.1f} сек "
                        f"({cr.get('standing_min', cr['standing_sec'] / 60):.2f} мин)"
                    )
                    lines.append("")
            else:
                lines.extend([
                    f"ID: {result.get('recognized_tag') or '—'}",
                    f"Время лёжа: {result['lying_sec']:.1f} сек "
                    f"({result['lying_min']} мин)",
                    f"Время стоя: {result['standing_sec']:.1f} сек "
                    f"({result['standing_min']} мин)",
                ])
            text = "\n".join(lines)
        else:
            text = str(result)
        te = QTextEdit()
        te.setReadOnly(True)
        te.setPlainText(text)
        lay.addWidget(te)
        btn = QPushButton("Закрыть")
        btn.clicked.connect(dlg.accept)
        lay.addWidget(btn)
        dlg.exec()

    # ── Расчёт BCS ───────────────────────────────────────────────────

    def toggle_kvs_calculation(self):
        if self._kvs_running:
            return
        self._kvs_running = True
        self._block_other_algos(self.btn_calc_kvs)
        self.update_kvs_log("Запущен расчёт BCS...")
        self.btn_calc_kvs.setEnabled(False)
        self.btn_calc_kvs.setChecked(False)
        window = BcsWindow(parent=self, dark = self.is_dark_theme)
        
        window.exec()
        self.btn_calc_kvs.setEnabled(True)
        self.btn_calc_kvs.setChecked(False)
        self.update_algorithm_buttons_style()
        self.update_kvs_log("Расчёт BCS завершён.")
        self._unblock_all_algos()
        self._kvs_running = False

    # ── Вспомогательные ──────────────────────────────────────────────

    def _get_default_cow_number(self) -> int:
        if DB_AVAILABLE:
            try:
                db = SessionLocal()
                cow = db.query(Cow).order_by(Cow.cow_number).first()
                db.close()
                if cow and cow.cow_number:
                    return cow.cow_number
            except Exception:
                pass
        return 1

    # ═══════════════════════════════════════════════════════════════════
    # ВИДЕОПЛЕЕР
    # ═══════════════════════════════════════════════════════════════════

    def handle_mode_selection(self, index: int):
        self.stop_processes()
        self._set_activity_source_ui(video_mode=False)
        if index == 1:
            busy = [w.cam_idx for w in self.active_camera_widgets]
            dlg = CameraSelectionDialog(busy, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                cam_idx = dlg.get_camera_index()
                if cam_idx is not None and cam_idx != -1:
                    self.video_stack.setCurrentIndex(1)
                    self.btn_stop.show()
                    self.ai_worker = VideoWorker(cam_idx)
                    self.ai_worker.change_pixmap_signal.connect(self._update_live_frame)
                    self.ai_worker.log_signal.connect(self.update_log)
                    self.ai_worker.start()
                    self._reconnect_algo_signals()
                else:
                    self.combo_mode.setCurrentIndex(0)
            else:
                self.combo_mode.setCurrentIndex(0)
        elif index == 2:
            path, _ = QFileDialog.getOpenFileName(
                self, "Открыть видео", "",
                "Видеофайлы (*.mp4 *.avi *.mkv *.mov)")
            if path:
                self._set_activity_source_ui(video_mode=True)
                self.video_stack.setCurrentIndex(2)
                self.btn_stop.show()
                self.btn_play_pause.show()
                self.slider.show()
                self.media_player.setSource(QUrl.fromLocalFile(path))
                self.media_player.play()
                self.ai_worker = VideoWorker(source=path)
                self.ai_worker.log_signal.connect(self.update_log)
                self.ai_worker.start()
                self.update_log(
                    f"Видео загружено. Для активности выберите зону: "
                    f"{self._get_video_test_zone()}"
                )
                self._reconnect_algo_signals()
            else:
                self.combo_mode.setCurrentIndex(0)

    def _reconnect_algo_signals(self):
        if not self.ai_worker:
            return
        if self._active_algo == "activity":
            self.ai_worker.snapshots_ready.connect(self._on_snapshots_ready_activity)
        elif self._active_algo == "sleep":
            self.ai_worker.snapshots_ready.connect(self._on_snapshots_ready_sleep)

    def toggle_playback(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def _on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play_pause.setText("⏸ ПАУЗА")
            self.btn_play_pause.setStyleSheet("background-color: #e0af68; color: #1a1b26;")
        else:
            self.btn_play_pause.setText("▶ СТАРТ")
            self.btn_play_pause.setStyleSheet("background-color: #3b82f6; color: white;")

    def _set_slider_range(self, duration):
        self.slider.setRange(0, duration)

    def _update_slider_position(self, position):
        if not self.is_slider_pressed:
            self.slider.blockSignals(True)
            self.slider.setValue(position)
            self.slider.blockSignals(False)

    def on_slider_pressed(self):
        self.is_slider_pressed = True
        self.was_playing = (
            self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)
        self.media_player.pause()

    def on_slider_moved(self, position):
        self.media_player.setPosition(position)

    def on_slider_released(self):
        self.is_slider_pressed = False
        if self.was_playing:
            self.media_player.play()

    def _update_live_frame(self, qt_img):
        w = self.label_ai_stream.width()
        h = self.label_ai_stream.height()
        if w > 0 and h > 0:
            pixmap = QPixmap.fromImage(qt_img).scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.label_ai_stream.setPixmap(pixmap)

    def on_stop_clicked(self):
        self.combo_mode.setCurrentIndex(0)

    def stop_processes(self):
        if self.ai_worker:
            self.ai_worker.stop()
            if not self.ai_worker.wait(3000):
                self.ai_worker.terminate()
                self.ai_worker.wait()
            self.ai_worker = None
        self.media_player.stop()
        self.video_stack.setCurrentIndex(0)
        self.btn_stop.hide()
        self.btn_play_pause.hide()
        self.slider.hide()

    # ═══════════════════════════════════════════════════════════════════
    # УПРАВЛЕНИЕ КАМЕРАМИ
    # ═══════════════════════════════════════════════════════════════════

    def add_camera_to_grid(self):
        busy = [w.cam_idx for w in self.active_camera_widgets]
        if self.ai_worker and self.ai_worker.isRunning():
            busy.append(getattr(self.ai_worker, "camera_index", -1))
        dlg = CameraSelectionDialog(busy, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            idx = dlg.get_camera_index()
            if idx is not None and idx != -1:
                w = CameraFeedWidget(idx, dlg.combo.currentText(), self.is_dark_theme, self)
                w.closed_signal.connect(self.remove_camera_from_grid)
                self.active_camera_widgets.append(w)
                self._reorganize_camera_grid()

    def remove_camera_via_dialog(self):
        if not self.active_camera_widgets:
            return
        dlg = CameraRemoveDialog(self.active_camera_widgets, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            w = dlg.get_selected_camera()
            if w:
                w.close_feed()

    def remove_camera_from_grid(self, widget):
        if widget in self.active_camera_widgets:
            self.active_camera_widgets.remove(widget)
            self.camera_layout.removeWidget(widget)
            widget.deleteLater()
            self._reorganize_camera_grid()

    def clear_all_cameras(self):
        for w in list(self.active_camera_widgets):
            w.close_feed()

    def _reorganize_camera_grid(self):
        for i in reversed(range(self.camera_layout.count())):
            item = self.camera_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)
        count = len(self.active_camera_widgets)
        if count == 0:
            return
        cols = max(1, math.ceil(math.sqrt(count)))
        for i, w in enumerate(self.active_camera_widgets):
            self.camera_layout.addWidget(w, i // cols, i % cols)

    # ═══════════════════════════════════════════════════════════════════
    # БАЗА ДАННЫХ
    # ═══════════════════════════════════════════════════════════════════

    def refresh_db_stats(self):
        if not DB_AVAILABLE:
            return
        db = SessionLocal()
        try:
            cow_count = db.scalar(select(func.count()).select_from(Cow))
            lbl = self.card_cows.findChild(QLabel, "ValLabel")
            if lbl:
                lbl.setText(str(cow_count))
            notif_count = db.scalar(select(func.count()).select_from(Notification))
            lbl_ev = self.card_events.findChild(QLabel, "ValLabel")
            if lbl_ev:
                lbl_ev.setText(str(notif_count))
        except Exception as e:
            self.update_log(f"Ошибка обновления статистики: {e}")
        finally:
            db.close()

    def load_notifications_data(self):
        if not DB_AVAILABLE:
            return
        try:
            db = SessionLocal()
            notifs = db.query(Notification).order_by(
                Notification.triggered_at.desc()).all()
            from PyQt6.QtWidgets import QTableWidgetItem
            self.notif_table.setRowCount(len(notifs))
            for i, n in enumerate(notifs):
                try:
                    time_str  = n.triggered_at.strftime("%Y-%m-%d %H:%M:%S") \
                                if n.triggered_at else ""
                    level_str = (
                        "🚨 КРИТИЧЕСКОЕ" if n.severity == "CRITICAL"
                        else "⚠️ ПРЕДУПРЕЖДЕНИЕ"
                    )
                    cow_tag = ""
                    if n.cow:
                        cow_tag = n.cow.tag_number
                    elif n.id_cow:
                        cow_tag = str(n.id_cow)[:8]

                    message = n.message or ""
                    if isinstance(message, bytes):
                        message = message.decode("cp1251", errors="replace")

                    notif_id = str(n.id_notification) if n.id_notification else ""
                    items = [
                        QTableWidgetItem(notif_id),
                        QTableWidgetItem(time_str),
                        QTableWidgetItem(level_str),
                        QTableWidgetItem(cow_tag),
                        QTableWidgetItem(message),
                    ]
                    for item in items:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    for col, item in enumerate(items):
                        self.notif_table.setItem(i, col, item)
                except Exception as row_err:
                    self.update_log(f"[row {i}] Ошибка: {row_err}")
            db.close()
        except Exception as e:
            self.update_log(f"Ошибка загрузки уведомлений: {e}")

    def load_employees_data(self):
        if not DB_AVAILABLE:
            return
        try:
            from PyQt6.QtWidgets import QTableWidgetItem
            db = SessionLocal()
            emps = db.query(Employee).all()
            self.ent_table.setRowCount(len(emps))
            for i, emp in enumerate(emps):
                self.ent_table.setItem(i, 0, QTableWidgetItem(str(emp.id_employee)[:8]))
                self.ent_table.setItem(i, 1, QTableWidgetItem(emp.full_name))
                self.ent_table.setItem(i, 2, QTableWidgetItem(str(emp.phone)))
                self.ent_table.setItem(i, 3, QTableWidgetItem(str(emp.email)))
            db.close()
        except Exception as e:
            self.update_log(f"Ошибка загрузки сотрудников: {e}")

    def execute_sql_query(self):
        if self.user_role == "vet" or not DB_AVAILABLE:
            return
        q = self.sql_input.toPlainText().strip()
        if not q:
            return
        try:
            from PyQt6.QtWidgets import QTableWidgetItem
            db = SessionLocal()
            res = db.execute(text(q))
            if q.lower().startswith("select"):
                rows = res.fetchall()
                cols = list(res.keys())
                self.db_table.setColumnCount(len(cols))
                self.db_table.setRowCount(len(rows))
                self.db_table.setHorizontalHeaderLabels(cols)
                for r_i, r_data in enumerate(rows):
                    for c_i, val in enumerate(r_data):
                        self.db_table.setItem(r_i, c_i, QTableWidgetItem(str(val)))
            else:
                db.commit()
                self.update_log("Запрос выполнен успешно.")
            db.close()
        except Exception as e:
            self.update_log(f"SQL Error: {e}")

    def create_db_backup(self):
        import subprocess
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить резервную копию",
            f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql",
            "SQL Files (*.sql)"
        )
        if not path:
            return
        try:
            env = os.environ.copy()
            env["PGPASSWORD"] = self._conn_params.get("password", "")
            result = subprocess.run(
                [
                    r"C:\Program Files\PostgreSQL\16\bin\pg_dump",
                    "-h", self._conn_params.get("host", "localhost"),
                    "-p", str(self._conn_params.get("port", 5432)),
                    "-U", self._conn_params.get("user", "postgres"),
                    "-d", self._conn_params.get("dbname", "cow_tracking_db"),
                    "-f", path,
                ],
                env=env,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                self.update_log(f"Резервная копия сохранена: {path}")
                InfoAlert(self, "РЕЗЕРВНАЯ КОПИЯ", f"Файл успешно сохранён:\n{path}").exec()
            else:
                self.update_log(f"Ошибка pg_dump: {result.stderr}")
        except FileNotFoundError:
            self.update_log("pg_dump не найден. Убедитесь что PostgreSQL в PATH.")
        except Exception as e:
            self.update_log(f"Ошибка создания бэкапа: {e}")
    # ═══════════════════════════════════════════════════════════════════
    # АЛЕРТЫ
    # ═══════════════════════════════════════════════════════════════════

    def trigger_alert(self, cow_tag: str, level: str, msg: str):
        from PyQt6.QtWidgets import QLabel, QTableWidgetItem
        import random

        now_dt = datetime.now()
        now_str = now_dt.strftime("%H:%M:%S")

        # Данные животного и ветеринара из БД
        vet_info = ""
        cow_display = f"Объект {cow_tag}"

        if DB_AVAILABLE:
            try:
                db = SessionLocal()

                # Берём случайную корову из БД
                cows = db.query(Cow).all()
                if cows:
                    random_cow = random.choice(cows)
                    cow_id = random_cow.cow_number or random_cow.tag_number
                    cow_display = f"Объект id={cow_id} ({random_cow.tag_number})"

                # Берём случайного сотрудника как ветеринара
                employees = db.query(Employee).all()
                if employees:
                    vet = random.choice(employees)
                    vet_info = (
                        f"\n\nСообщение отправлено: {vet.full_name}"
                        f"\nEmail: {vet.email or 'не указан'}"
                        f"\nТел.: {vet.phone or 'не указан'}"
                    )

                db.close()
            except Exception:
                pass

        alert_text = f"{cow_display}: {msg}{vet_info}"

        if level == "CRITICAL":
            CriticalAlert(self, "УГРОЗА ЗДОРОВЬЮ", alert_text).exec()
            self.update_log(f"[{now_str}] КРИТИЧНО [{cow_tag}]: {msg}")
        else:
            WarningAlert(self, "ПРЕДУПРЕЖДЕНИЕ", alert_text).exec()
            self.update_log(f"[{now_str}] ВНИМАНИЕ [{cow_tag}]: {msg}")

        if DB_AVAILABLE:
            try:
                db = SessionLocal()
                cows_all = db.query(Cow).all()
                random_cow = random.choice(cows_all) if cows_all else None
                notif = Notification(
                    id_cow=random_cow.id_cow if random_cow else None,
                    alert_type="MANUAL",
                    severity=level,
                    triggered_at=now_dt,
                    message=msg,
                )
                db.add(notif)
                db.commit()
                db.close()
            except Exception as e:
                self.update_log(f"Ошибка сохранения в БД: {e}")
            self.load_notifications_data()
            self.refresh_db_stats()
        else:
            row = 0
            self.notif_table.insertRow(row)
            items = [
                QTableWidgetItem("—"),
                QTableWidgetItem(now_str),
                QTableWidgetItem("🚨 КРИТИЧЕСКОЕ" if level == "CRITICAL" else "⚠️ ПРЕДУПРЕЖДЕНИЕ"),
                QTableWidgetItem(str(cow_tag)),
                QTableWidgetItem(str(msg)),
            ]
            for item in items:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            for col, item in enumerate(items):
                self.notif_table.setItem(row, col, item)

        self.alert_count += 1
        lbl = self.card_alerts.findChild(QLabel, "ValLabelAlert")
        if lbl:
            lbl.setText(str(self.alert_count))

    # ═══════════════════════════════════════════════════════════════════
    # ОТЧЁТЫ
    # ═══════════════════════════════════════════════════════════════════

    def _get_conn_params(self) -> dict:
        return self._conn_params

    def _open_excel_report_dialog(self):
        try:
            from ui.reports_dialog import BaseReportDialog
        except ImportError:
            QMessageBox.critical(self, "Ошибка", "Модуль ui/reports_dialog.py не найден.")
            return
        BaseReportDialog(
            parent=self, report_type="excel",
            conn_params=self._get_conn_params(),
            company_name="УМНАЯ ФЕРМА",
        ).exec()

    def _open_pdf_report_dialog(self):
        try:
            from ui.reports_dialog import BaseReportDialog
        except ImportError:
            QMessageBox.critical(self, "Ошибка", "Модуль ui/reports_dialog.py не найден.")
            return
        BaseReportDialog(
            parent=self, report_type="pdf",
            conn_params=self._get_conn_params(),
            company_name="УМНАЯ ФЕРМА",
        ).exec()

    # ═══════════════════════════════════════════════════════════════════
    # УТИЛИТЫ
    # ═══════════════════════════════════════════════════════════════════

    def safe_exit(self):
        self.stop_processes()
        self.clear_all_cameras()
        self.close()

    def show_about_info(self):
        InfoAlert(self, "О ПРОГРАММЕ",
                  "ИС 'Умная Ферма'\n\nРазработка студентами группы ИСТ-418Б:\nГафаров Мурат Радикович\nЕременко Станислав Викторович\nЗакирова Рената Винеровна").exec()

    def closeEvent(self, event):
        self.stop_processes()
        self.clear_all_cameras()
        event.accept()
