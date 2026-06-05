"""
ui/pages/page_monitoring.py
Страница «Мониторинг».

Нижняя зона — три независимых блока (кнопка + свой лог):
  [🏃 Детекция активности] [🌙 Детекция сна] [📊 Расчет КВС]
   log_box                  sleep_log_box     kvs_log_box

alert_box убран — тревоги на этой странице больше не отображаются.
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
      card_cows, card_events, card_alerts,
      video_stack, label_placeholder, label_ai_stream, video_widget,
      combo_mode, btn_play_pause, btn_stop, slider,
      combo_camera_activity,          ← НОВЫЙ: выбор камеры для анализа активности
      btn_refresh_cameras,            ← НОВЫЙ: обновить список камер из БД
      btn_detect_activity, btn_detect_sleep, btn_calc_kvs,
      log_box, sleep_log_box, kvs_log_box
    """
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(14)

    # ── Карточки статистики ───────────────────────────────────────────
    stats_layout = QHBoxLayout()
    stats_layout.setSpacing(16)
    mw.card_cows   = _stat_card("🐄 КОРОВ В БАЗЕ", "?")
    mw.card_events = _stat_card("📊 СОБЫТИЙ",      "0")
    mw.card_alerts = _stat_card("⚠️ ТРЕВОГИ",      "0", is_alert=True)
    for card in [mw.card_cows, mw.card_events, mw.card_alerts]:
        stats_layout.addWidget(card)
    layout.addLayout(stats_layout)

    # ── Видео-зона ────────────────────────────────────────────────────
    mw.video_stack = QStackedWidget()
    mw.video_stack.setMinimumHeight(220)
    mw.video_stack.setMaximumHeight(520)
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

    layout.addWidget(mw.video_stack, stretch=4)

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
        "Зона (кормушка/поилка) определяется автоматически по настройкам камеры в БД."
    )
    camera_row.addWidget(mw.combo_camera_activity, stretch=1)

    mw.btn_refresh_cameras = QPushButton("🔄")
    mw.btn_refresh_cameras.setFixedWidth(36)
    mw.btn_refresh_cameras.setToolTip("Обновить список камер из базы данных")
    mw.btn_refresh_cameras.clicked.connect(mw.refresh_cameras_combo)
    camera_row.addWidget(mw.btn_refresh_cameras)

    col_activity.addLayout(camera_row)

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
    mw.btn_calc_kvs = QPushButton("📊 Расчет КВС (СТАРТ)")
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
    layout.addLayout(algos, stretch=3)

    # alert_box — заглушка (main_window.py обращается к нему в trigger_alert)
    mw.alert_box = QTextEdit()
    mw.alert_box.hide()

    mw.update_algorithm_buttons_style()
    return page


def _stat_card(title: str, value: str, is_alert: bool = False) -> QFrame:
    card = QFrame()
    card.setObjectName("StatCard")
    card.setMinimumHeight(100)
    card.setMaximumHeight(150)
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(20, 16, 20, 16)
    card_layout.setSpacing(8)
    lbl_title = QLabel(title)
    lbl_title.setObjectName("StatTitle")
    lbl_val = QLabel(value)
    lbl_val.setObjectName("ValLabelAlert" if is_alert else "ValLabel")
    lbl_val.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    card_layout.addWidget(lbl_title)
    card_layout.addWidget(lbl_val)
    card_layout.addStretch()
    return card
