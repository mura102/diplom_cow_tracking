# ui/styles.py

# --- ТЕМНАЯ ТЕМА (TOKYO NIGHT) ---
STYLESHEET_DARK = """

QMainWindow {
    background-color: #1a1b26;
}

/* ─── Глобальные виджеты ─────────────────────────────────────────────── */
QWidget {
    color: #a9b1d6;
    background-color: transparent;
}

QLabel {
    color: #a9b1d6;
    background-color: transparent;
}

QLabel#AccessDeniedLabel {
    font-size: 16px; font-weight: bold;
    color: #f7768e;
    border: none; margin-top: 100px;
}

QDialog {
    background-color: #1a1b26;
}

QDialog QLabel {
    color: #a9b1d6;
    background-color: transparent;
}

/* ─── Сайдбар ────────────────────────────────────────────────────────── */
QFrame#Sidebar {
    background-color: #16161e;
    border-right: 1px solid #292e42;
}
QLabel#Title {
    color: #7aa2f7;
    margin-top: 10px;
    margin-bottom: 20px;
}

/* ─── Общие кнопки ───────────────────────────────────────────────────── */
QPushButton {
    background-color: #3b4261;
    color: #c0caf5;
    border-radius: 6px;
    padding: 10px 15px;
    font-size: 14px;
    font-weight: bold;
    border: none;
}
QPushButton:hover {
    background-color: #7aa2f7;
    color: #1a1b26;
}
QPushButton:pressed {
    background-color: #5d7bd5;
    color: #1a1b26;
}
QPushButton:disabled {
    background-color: #2a2e44;
    color: #565f89;
}

/* ─── Кнопки навигации ───────────────────────────────────────────────── */
QPushButton[navStyle="nav"] {
    background-color: transparent;
    color: #a9b1d6;
    text-align: left;
    padding: 15px 20px;
    border-radius: 6px;
    font-size: 15px;
    font-weight: 500;
    border: none;
}
QPushButton[navStyle="nav"]:hover {
    background-color: #24283b;
    color: #7aa2f7;
}
QPushButton[navStyle="active"] {
    background-color: #292e42;
    color: #7aa2f7;
    text-align: left;
    padding: 15px 20px;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    border-top-left-radius: 0px;
    border-bottom-left-radius: 0px;
    font-size: 15px;
    font-weight: bold;
    border: none;
    border-left: 4px solid #7aa2f7;
}

/* ─── Служебные кнопки ───────────────────────────────────────────────── */
QPushButton#ExitBtn {
    background-color: transparent;
    color: #f7768e;
    border: 1px solid #f7768e;
}
QPushButton#ExitBtn:hover {
    background-color: #f7768e;
    color: #1a1b26;
}
QPushButton#ExitBtn:pressed {
    background-color: #d45b70;
    color: #1a1b26;
}

QPushButton#ThemeBtn {
    background-color: transparent;
    color: #e0af68;
    border: 1px solid #e0af68;
    margin-bottom: 10px;
}
QPushButton#ThemeBtn:hover {
    background-color: #e0af68;
    color: #1a1b26;
}

/* ─── Карточки статистики ─────────────────────────────────────────────── */
QFrame#StatCard {
    background-color: #16161e;
    border: 1px solid #292e42;
    border-radius: 10px;
}
QLabel#StatTitle {
    color: #565f89;
    font-size: 13px;
    font-weight: bold;
    border: none;
}
QLabel#ValLabel {
    color: #7aa2f7;
    font-size: 32px;
    font-weight: bold;
    border: none;
}
QLabel#ValLabelAlert {
    color: #f7768e;
    font-size: 32px;
    font-weight: bold;
    border: none;
}

/* ─── Журналы / TextEdit ─────────────────────────────────────────────── */
QTextEdit {
    background-color: #16161e;
    color: #a9b1d6;
    border: 1px solid #292e42;
    border-radius: 8px;
    padding: 15px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13px;
}

/* ─── LineEdit ───────────────────────────────────────────────────────── */
QLineEdit {
    background-color: #16161e;
    color: #a9b1d6;
    border: 1px solid #292e42;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: #3b4261;
    selection-color: #c0caf5;
}
QLineEdit:focus {
    border: 1px solid #7aa2f7;
    color: #c0caf5;
}
QLineEdit:disabled {
    color: #565f89;
    background-color: #1a1b26;
}

/* ─── ComboBox ───────────────────────────────────────────────────────── */
QComboBox {
    background-color: #16161e;
    color: #a9b1d6;
    border: 1px solid #292e42;
    border-radius: 6px;
    padding: 8px 15px;
    font-size: 14px;
    selection-background-color: #292e42;
    selection-color: #c0caf5;
}
QComboBox:focus {
    border: 1px solid #7aa2f7;
    color: #c0caf5;
}
QComboBox:on {
    background-color: #1a1b26;
    color: #c0caf5;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    width: 10px;
    height: 10px;
}
QComboBox QAbstractItemView {
    background-color: #16161e;
    color: #a9b1d6;
    selection-background-color: #292e42;
    selection-color: #7aa2f7;
    border: 1px solid #292e42;
    outline: none;
    padding: 4px;
}

/* ─── SpinBox ────────────────────────────────────────────────────────── */
QSpinBox {
    background-color: #16161e;
    color: #a9b1d6;
    border: 1px solid #292e42;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #292e42;
    border: none;
    width: 18px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #3b4261;
}

/* ─── Ползунок видео ─────────────────────────────────────────────────── */
QSlider#VideoSlider { min-height: 20px; }
QSlider::groove:horizontal {
    border: 1px solid #292e42;
    height: 8px;
    background: #16161e;
    border-radius: 4px;
}
QSlider::sub-page:horizontal {
    background: #7aa2f7;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #e0af68;
    border: 1px solid #e0af68;
    width: 14px;
    margin-top: -3px;
    margin-bottom: -3px;
    border-radius: 7px;
}

/* ─── Прогресс-бар ───────────────────────────────────────────────────── */
QProgressBar {
    background-color: #16161e;
    border: 1px solid #292e42;
    border-radius: 4px;
    height: 14px;
    text-align: center;
    color: #a9b1d6;
    font-size: 11px;
}
QProgressBar::chunk {
    background-color: #7aa2f7;
    border-radius: 3px;
}

/* ─── Статус-бар и меню ──────────────────────────────────────────────── */
QStatusBar {
    background-color: #16161e;
    color: #565f89;
    border-top: 1px solid #292e42;
    font-size: 12px;
}
QStatusBar::item { border: none; }

QMenuBar {
    background-color: #16161e;
    color: #a9b1d6;
    font-size: 13px;
    border-bottom: 1px solid #292e42;
    padding: 2px;
}
QMenuBar::item:selected {
    background-color: #292e42;
    color: #7aa2f7;
    border-radius: 4px;
}
QMenu {
    background-color: #16161e;
    color: #a9b1d6;
    border: 1px solid #292e42;
}
QMenu::item:selected {
    background-color: #7aa2f7;
    color: #1a1b26;
}

/* ─── Таблицы ────────────────────────────────────────────────────────── */
QTableWidget, QTableView {
    background-color: #16161e;
    color: #a9b1d6;
    border: 1px solid #292e42;
    border-radius: 8px;
    gridline-color: #24283b;
    font-size: 13px;
    alternate-background-color: #1a1e2e;
}
QTableWidget::item, QTableView::item {
    padding: 6px;
    border: none;
    color: #a9b1d6;
    background-color: transparent;
}
QTableWidget::item:selected, QTableView::item:selected {
    background-color: #292e42;
    color: #7aa2f7;
}

/* ─── Заголовки таблиц ───────────────────────────────────────────────── */
QHeaderView {
    background-color: #16161e;
    border: none;
}
QHeaderView::section {
    background-color: #1a1b26;
    color: #7aa2f7;
    padding: 10px;
    border: none;
    border-bottom: 2px solid #292e42;
    font-weight: bold;
}
QHeaderView::section:vertical {
    background-color: #16161e;
    color: transparent;
    border: none;
    width: 0px;
    min-width: 0px;
    max-width: 0px;
    padding: 0px;
}
QTableCornerButton::section {
    background-color: #16161e;
    border: none;
}

/* ─── Скроллбары ─────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #16161e;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #3b4261;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #7aa2f7; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

QScrollBar:horizontal {
    background: #16161e;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #3b4261;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #7aa2f7; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }

/* ─── Диалоговые окна ────────────────────────────────────────────────── */
QGroupBox {
    color: #a9b1d6;
    border: 1px solid #292e42;
    border-radius: 6px;
    margin-top: 8px;
    padding: 10px 8px 8px 8px;
    font-weight: bold;
    background-color: #1a1b26;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #7aa2f7;
}

/* ─── Окна уведомлений ───────────────────────────────────────────────── */
QFrame#CriticalPopup {
    background-color: #1a1b26;
    border: 3px solid #f7768e;
    border-radius: 12px;
}
QLabel#CriticalTitle {
    color: #f7768e;
    font-size: 22px;
    font-weight: bold;
    border: none;
}
QPushButton#BtnAcknowledgeCrit {
    background-color: #f7768e;
    color: #1a1b26;
    border: none;
    border-radius: 6px;
    font-weight: bold;
    padding: 12px 30px;
}
QPushButton#BtnAcknowledgeCrit:hover { background-color: #d45b70; }

QFrame#WarningPopup {
    background-color: #1a1b26;
    border: 3px solid #e0af68;
    border-radius: 12px;
}
QLabel#WarningTitle {
    color: #e0af68;
    font-size: 22px;
    font-weight: bold;
    border: none;
}
QPushButton#BtnAcknowledgeWarn {
    background-color: #e0af68;
    color: #1a1b26;
    border: none;
    border-radius: 6px;
    font-weight: bold;
    padding: 12px 30px;
}
QPushButton#BtnAcknowledgeWarn:hover { background-color: #c49040; }

QFrame#InfoPopup {
    background-color: #1a1b26;
    border: 3px solid #7aa2f7;
    border-radius: 12px;
}
QLabel#InfoTitle {
    color: #7aa2f7;
    font-size: 22px;
    font-weight: bold;
    border: none;
}
QPushButton#BtnAcknowledgeInfo {
    background-color: #7aa2f7;
    color: #1a1b26;
    border: none;
    border-radius: 6px;
    font-weight: bold;
    padding: 12px 30px;
}
QPushButton#BtnAcknowledgeInfo:hover { background-color: #5d7bd5; }

QLabel#NotifText {
    color: #a9b1d6;
    font-size: 15px;
    border: none;
    background: transparent;
}
QLabel#VideoPlaceholder {
    background-color: #000000;
    border-radius: 10px;
    color: #565f89;
    font-weight: bold;
}
QLabel#VideoStream {
    background-color: #000000;
    border-radius: 10px;
}
QVideoWidget#VideoPlayer {
    background-color: #000000;
    border-radius: 10px;
}
QTextEdit#LogBox {
    background-color: #1a1b26;
    color: #a9b1d6;
    border: 1px solid #292e42;
    border-radius: 6px;
}
"""


# --- СВЕТЛАЯ ТЕМА (CLEAN LIGHT) ---
STYLESHEET_LIGHT = """

QMainWindow { background-color: #f0f2f5; }

/* ─── Глобальные виджеты ─────────────────────────────────────────────── */
QWidget {
    color: #1f2937;
    background-color: transparent;
}

QLabel {
    color: #1f2937;
    background-color: transparent;
}

QLabel#AccessDeniedLabel {
    font-size: 16px; font-weight: bold;
    color: #dc2626;
    border: none; margin-top: 100px;
}

QDialog {
    background-color: #f0f2f5;
}

QDialog QLabel {
    color: #1f2937;
    background-color: transparent;
}

/* ─── Сайдбар ────────────────────────────────────────────────────────── */
QFrame#Sidebar { background-color: #ffffff; border-right: 1px solid #e5e7eb; }
QLabel#Title { color: #2563eb; margin-top: 10px; margin-bottom: 20px; }

/* ─── Общие кнопки ───────────────────────────────────────────────────── */
QPushButton {
    background-color: #3b82f6;
    color: white;
    border-radius: 6px;
    padding: 10px 15px;
    font-size: 14px;
    font-weight: bold;
    border: none;
}
QPushButton:hover { background-color: #2563eb; }
QPushButton:pressed { background-color: #1d4ed8; }
QPushButton:disabled { background-color: #cbd5e1; color: #94a3b8; }

/* ─── Кнопки навигации ───────────────────────────────────────────────── */
QPushButton[navStyle="nav"] {
    background-color: transparent;
    color: #4b5563;
    text-align: left;
    padding: 15px 20px;
    border-radius: 6px;
    font-size: 15px;
    font-weight: 500;
    border: none;
}
QPushButton[navStyle="nav"]:hover { background-color: #f3f4f6; color: #2563eb; }
QPushButton[navStyle="active"] {
    background-color: #eff6ff;
    color: #2563eb;
    text-align: left;
    padding: 15px 20px;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    border-top-left-radius: 0px;
    border-bottom-left-radius: 0px;
    font-size: 15px;
    font-weight: bold;
    border: none;
    border-left: 4px solid #3b82f6;
}

/* ─── Служебные кнопки ───────────────────────────────────────────────── */
QPushButton#ThemeBtn {
    background-color: transparent;
    color: #f59e0b;
    border: 1px solid #f59e0b;
    margin-bottom: 10px;
}
QPushButton#ThemeBtn:hover { background-color: #f59e0b; color: white; }

QPushButton#ExitBtn {
    background-color: transparent;
    color: #ef4444;
    border: 1px solid #ef4444;
}
QPushButton#ExitBtn:hover { background-color: #ef4444; color: white; }
QPushButton#ExitBtn:pressed { background-color: #dc2626; color: white; }

/* ─── Карточки статистики ─────────────────────────────────────────────── */
QFrame#StatCard { background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px; }
QLabel#StatTitle { color: #6b7280; font-size: 13px; font-weight: bold; border: none; }
QLabel#ValLabel { color: #2563eb; font-size: 32px; font-weight: bold; border: none; }
QLabel#ValLabelAlert { color: #ef4444; font-size: 32px; font-weight: bold; border: none; }

/* ─── TextEdit ───────────────────────────────────────────────────────── */
QTextEdit {
    background-color: #ffffff;
    color: #1f2937;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 15px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13px;
}

/* ─── LineEdit ───────────────────────────────────────────────────────── */
QLineEdit {
    background-color: #ffffff;
    color: #1f2937;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: #bfdbfe;
    selection-color: #1e3a8a;
}
QLineEdit:focus {
    border: 1px solid #3b82f6;
    color: #111827;
}
QLineEdit:disabled {
    color: #9ca3af;
    background-color: #f9fafb;
}

/* ─── ComboBox ───────────────────────────────────────────────────────── */
QComboBox {
    background-color: #ffffff;
    color: #1f2937;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 8px 15px;
    font-size: 14px;
    selection-background-color: #eff6ff;
    selection-color: #2563eb;
}
QComboBox:focus {
    border: 1px solid #3b82f6;
    color: #111827;
}
QComboBox:on {
    background-color: #f9fafb;
    color: #111827;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    width: 10px;
    height: 10px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #1f2937;
    selection-background-color: #eff6ff;
    selection-color: #2563eb;
    border: 1px solid #e5e7eb;
    outline: none;
    padding: 4px;
}

/* ─── SpinBox ────────────────────────────────────────────────────────── */
QSpinBox {
    background-color: #ffffff;
    color: #1f2937;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #f3f4f6;
    border: none;
    width: 18px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #e5e7eb;
}

/* ─── Ползунок видео ─────────────────────────────────────────────────── */
QSlider#VideoSlider { min-height: 20px; }
QSlider::groove:horizontal { border: 1px solid #d1d5db; height: 8px; background: #f3f4f6; border-radius: 4px; }
QSlider::sub-page:horizontal { background: #3b82f6; border-radius: 4px; }
QSlider::handle:horizontal { background: #f59e0b; border: 1px solid #f59e0b; width: 14px; margin-top: -3px; margin-bottom: -3px; border-radius: 7px; }

/* ─── Прогресс-бар ───────────────────────────────────────────────────── */
QProgressBar {
    background-color: #f3f4f6;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    height: 14px;
    text-align: center;
    color: #4b5563;
    font-size: 11px;
}
QProgressBar::chunk { background-color: #3b82f6; border-radius: 3px; }

/* ─── Статус-бар и меню ──────────────────────────────────────────────── */
QStatusBar { background-color: #ffffff; color: #6b7280; border-top: 1px solid #e5e7eb; font-size: 12px; }
QStatusBar::item { border: none; }

QMenuBar { background-color: #ffffff; color: #1f2937; border-bottom: 1px solid #e5e7eb; padding: 2px; font-size: 13px; }
QMenuBar::item:selected { background-color: #eff6ff; color: #2563eb; border-radius: 4px; }
QMenu { background-color: #ffffff; color: #1f2937; border: 1px solid #e5e7eb; }
QMenu::item:selected { background-color: #eff6ff; color: #2563eb; }

/* ─── Таблицы ────────────────────────────────────────────────────────── */
QTableWidget, QTableView {
    background-color: #ffffff;
    color: #1f2937;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    gridline-color: #f3f4f6;
    font-size: 13px;
    alternate-background-color: #f9fafb;
}
QTableWidget::item, QTableView::item {
    padding: 6px;
    border: none;
    color: #1f2937;
    background-color: transparent;
}
QTableWidget::item:selected, QTableView::item:selected {
    background-color: #eff6ff;
    color: #2563eb;
}

/* ─── Заголовки таблиц ───────────────────────────────────────────────── */
QHeaderView {
    background-color: #ffffff;
    border: none;
}
QHeaderView::section {
    background-color: #f9fafb;
    color: #4b5563;
    padding: 10px;
    border: none;
    border-bottom: 2px solid #e5e7eb;
    font-weight: bold;
}
QHeaderView::section:vertical {
    background-color: #ffffff;
    color: transparent;
    border: none;
    width: 0px;
    min-width: 0px;
    max-width: 0px;
    padding: 0px;
}
QTableCornerButton::section {
    background-color: #f9fafb;
    border: none;
}

/* ─── Скроллбары ─────────────────────────────────────────────────────── */
QScrollBar:vertical { background: #f3f4f6; width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #d1d5db; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #3b82f6; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

QScrollBar:horizontal { background: #f3f4f6; height: 8px; border-radius: 4px; }
QScrollBar::handle:horizontal { background: #d1d5db; border-radius: 4px; min-width: 30px; }
QScrollBar::handle:horizontal:hover { background: #3b82f6; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }

/* ─── Диалоговые окна ────────────────────────────────────────────────── */
QGroupBox {
    color: #374151;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    margin-top: 8px;
    padding: 10px 8px 8px 8px;
    font-weight: bold;
    background-color: #ffffff;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #2563eb; }

/* ─── Окна уведомлений ───────────────────────────────────────────────── */
QFrame#CriticalPopup { background-color: #ffffff; border: 3px solid #ef4444; border-radius: 12px; }
QLabel#CriticalTitle { color: #ef4444; font-size: 22px; font-weight: bold; border: none; }
QPushButton#BtnAcknowledgeCrit { background-color: #ef4444; color: white; border: none; border-radius: 6px; font-weight: bold; padding: 12px 30px; }
QPushButton#BtnAcknowledgeCrit:hover { background-color: #dc2626; }

QFrame#WarningPopup { background-color: #ffffff; border: 3px solid #f59e0b; border-radius: 12px; }
QLabel#WarningTitle { color: #d97706; font-size: 22px; font-weight: bold; border: none; }
QPushButton#BtnAcknowledgeWarn { background-color: #f59e0b; color: white; border: none; border-radius: 6px; font-weight: bold; padding: 12px 30px; }
QPushButton#BtnAcknowledgeWarn:hover { background-color: #d97706; }

QFrame#InfoPopup { background-color: #ffffff; border: 3px solid #3b82f6; border-radius: 12px; }
QLabel#InfoTitle { color: #2563eb; font-size: 22px; font-weight: bold; border: none; }
QPushButton#BtnAcknowledgeInfo { background-color: #3b82f6; color: white; border: none; border-radius: 6px; font-weight: bold; padding: 12px 30px; }
QPushButton#BtnAcknowledgeInfo:hover { background-color: #2563eb; }

QLabel#NotifText { color: #374151; font-size: 15px; border: none; background: transparent; }

QLabel#VideoPlaceholder {
    background-color: #e2e8f0;
    border-radius: 10px;
    color: #64748b;
    font-weight: bold;
}
QLabel#VideoStream {
    background-color: #e2e8f0;
    border-radius: 10px;
}
QVideoWidget#VideoPlayer {
    background-color: #000000;
    border-radius: 10px;
}
QTextEdit#LogBox {
    background-color: #f8fafc;
    color: #1f2937;
    border: 1px solid #d1d5db;
    border-radius: 6px;
}
"""