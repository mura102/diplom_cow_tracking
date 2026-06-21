"""
ui/pages/page_monitoring.py
Страница «Мониторинг».

Нижняя зона — три независимых блока (кнопка + свой лог):
  [🏃 Детекция активности] [🌙 Детекция сна] [📊 Расчет КВС]
   log_box                  sleep_log_box     kvs_log_box

Дашборды (статистика сверху) убраны для расширения зоны плеера.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QFrame,
    QComboBox, QSlider, QStackedWidget, QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtMultimediaWidgets import QVideoWidget


def build(mw) -> QWidget:
    """
    Добавляет атрибуты:
      video_stack, label_placeholder, label_ai_stream, video_widget,
      combo_mode, btn_play_pause, btn_stop, slider,
      combo_camera_activity,          ← выбор камеры для анализа активности
      btn_refresh_cameras,            ← обновить список камер из БД
      btn_detect_activity, btn_detect_sleep, btn_calc_kvs,
      log_box, sleep_log_box, kvs_log_box
    """
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(14)

    # ── Видео-зона ────────────────────────────────────────────────────
    mw.video_stack = QStackedWidget()
    mw.video_stack.setMinimumHeight(220)
    # Убрали setMaximumHeight, чтобы видеоплеер занимал всё доступное место
    mw.video_stack.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Expanding,
    )

    mw.label_placeholder = QLabel("ОЖИДАНИЕ ВЫБОРА РЕЖИМА...")
    mw.label_placeholder.setObjectName("VideoPlaceholder")
    mw.label_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
    mw.video_stack.addWidget(mw.label_placeholder)

    mw.label_ai_stream = QLabel()
    mw.label_ai_stream.setObjectName("VideoStream")
    mw.label_ai_stream.setAlignment(Qt.AlignmentFlag.AlignCenter)
    mw.video_stack.addWidget(mw.label_ai_stream)

    mw.video_widget = QVideoWidget()
    mw.video_widget.setObjectName("VideoPlayer")
    mw.video_stack.addWidget(mw.video_widget)

    # Увеличили stretch для плеера, чтобы он забирал максимум места
    layout.addWidget(mw.video_stack, stretch=5)

    # ── Панель управления (режим + плеер) ─────────────────────────────
    controls = QHBoxLayout()
    controls.setSpacing(10)

    mw.combo_mode = QComboBox()
    mw.combo_mode.setMinimumWidth(280)
    mw.combo_mode.addItems(["Ожидание...", "📡 Live-сессия (AI)", "📁 Видеофайл"])
    mw.combo_mode.currentIndexChanged.connect(mw.handle_mode_selection)
    controls.addWidget(mw.combo_mode)

    mw.btn_play_pause = QPushButton("⏸ ПАУЗА")
    mw.btn_play_pause.setStyleSheet("background-color: #3b82f6; color: white;")
    mw.btn_play_pause.clicked.connect(mw.toggle_playback)
    mw.btn_play_pause.hide()
    controls.addWidget(mw.btn_play_pause)

    mw.btn_stop = QPushButton("⏹ СТОП")
    mw.btn_stop.setObjectName("ExitBtn")
    mw.btn_stop.clicked.connect(mw.on_stop_clicked)
    mw.btn_stop.hide()
    controls.addWidget(mw.btn_stop)

    mw.slider = QSlider(Qt.Orientation.Horizontal)
    mw.slider.setObjectName("VideoSlider")
    mw.slider.sliderPressed.connect(mw.on_slider_pressed)
    mw.slider.sliderReleased.connect(mw.on_slider_released)
    mw.slider.sliderMoved.connect(mw.on_slider_moved)
    mw.slider.hide()
    controls.addWidget(mw.slider, stretch=1)
    layout.addLayout(controls)

    # ── Три блока алгоритмов ──────────────────────────────────────────
    algos = QHBoxLayout()
    algos.setSpacing(12)

    # — Блок 1: Детекция активности (Рената) —
    col_activity = QVBoxLayout()
    col_activity.setSpacing(6)

    # Строка: выбор камеры + кнопка обновления
    camera_row = QHBoxLayout()
    camera_row.setSpacing(6)

    lbl_camera = QLabel("📷 Камера:")
    lbl_camera.setObjectName("CameraLabel")
    lbl_camera.setFixedWidth(70)
    camera_row.addWidget(lbl_camera)

    mw.combo_camera_activity = QComboBox()
    mw.combo_camera_activity.setMinimumWidth(160)
    mw.combo_camera_activity.setToolTip(
        "Выберите камеру для анализа активности.\n"
        "Зона (кормовая/питьевая) определяется автоматически по настройкам камеры в БД."
    )
    camera_row.addWidget(mw.combo_camera_activity, stretch=1)

    mw.btn_refresh_cameras = QPushButton("🔄")
    mw.btn_refresh_cameras.setFixedWidth(36)
    mw.btn_refresh_cameras.setToolTip("Обновить список камер из базы данных")
    mw.btn_refresh_cameras.clicked.connect(mw.refresh_cameras_combo)
    camera_row.addWidget(mw.btn_refresh_cameras)

    col_activity.addLayout(camera_row)

    video_zone_row = QHBoxLayout()
    video_zone_row.setSpacing(6)

    lbl_video_zone = QLabel("🎬 Зона (видео):")
    lbl_video_zone.setObjectName("CameraLabel")
    lbl_video_zone.setFixedWidth(100)
    video_zone_row.addWidget(lbl_video_zone)

    mw.combo_video_zone = QComboBox()
    mw.combo_video_zone.addItem("кормовая зона — питание", userData="кормовая зона")
    mw.combo_video_zone.addItem("питьевая зона — питьё", userData="питьевая зона")
    mw.combo_video_zone.setToolTip(
        "Для теста по видеофайлу: выберите зону, где якобы установлена камера.\n"
        "От этого зависит, считается ли активность кормлением или питьём."
    )
    video_zone_row.addWidget(mw.combo_video_zone, stretch=1)

    mw.lbl_video_zone_hint = QLabel("активна при режиме «Видеофайл»")
    mw.lbl_video_zone_hint.setStyleSheet("color:#565f89; font-size:11px;")
    video_zone_row.addWidget(mw.lbl_video_zone_hint)

    col_activity.addLayout(video_zone_row)
    mw._video_zone_row_widgets = (
        lbl_video_zone, mw.combo_video_zone, mw.lbl_video_zone_hint
    )
    for w in mw._video_zone_row_widgets:
        w.setVisible(False)

    mw.btn_detect_activity = QPushButton("🏃 Детекция активности (СТАРТ)")
    mw.btn_detect_activity.setCheckable(True)
    mw.btn_detect_activity.toggled.connect(mw.toggle_activity_detection)
    col_activity.addWidget(mw.btn_detect_activity)

    mw.log_box = QTextEdit()
    mw.log_box.setObjectName("LogBox")
    mw.log_box.setReadOnly(True)
    col_activity.addWidget(mw.log_box, stretch=1)

    # — Блок 2: Детекция сна (ночная модель) —
    col_sleep = QVBoxLayout()
    col_sleep.setSpacing(6)
    mw.btn_detect_sleep = QPushButton("🌙 Детекция сна (СТАРТ)")
    mw.btn_detect_sleep.setCheckable(True)
    mw.btn_detect_sleep.toggled.connect(mw.toggle_sleep_detection)
    mw.sleep_log_box = QTextEdit()
    mw.sleep_log_box.setObjectName("LogBox")
    mw.sleep_log_box.setReadOnly(True)
    col_sleep.addWidget(mw.btn_detect_sleep)
    col_sleep.addWidget(mw.sleep_log_box, stretch=1)

    # — Блок 3: Расчёт КВС (Стас) —
    col_kvs = QVBoxLayout()
    col_kvs.setSpacing(6)
    mw.btn_calc_kvs = QPushButton("📊 Расчет BCS (СТАРТ)")
    mw.btn_calc_kvs.setCheckable(True)
    mw.btn_calc_kvs.toggled.connect(mw.toggle_kvs_calculation)
    mw.kvs_log_box = QTextEdit()
    mw.kvs_log_box.setObjectName("LogBox")
    mw.kvs_log_box.setReadOnly(True)
    col_kvs.addWidget(mw.btn_calc_kvs)
    col_kvs.addWidget(mw.kvs_log_box, stretch=1)

    algos.addLayout(col_activity, stretch=1)
    algos.addLayout(col_sleep,    stretch=1)
    algos.addLayout(col_kvs,      stretch=1)

    # Немного уменьшили растяжение нижней панели, чтобы отдать место плееру
    layout.addLayout(algos, stretch=2)

    # alert_box — заглушка (main_window.py обращается к нему в trigger_alert)
    mw.alert_box = QTextEdit()
    mw.alert_box.hide()

    mw.update_algorithm_buttons_style()
    return page