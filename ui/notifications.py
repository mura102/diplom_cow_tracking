# ui/notifications.py
import base64
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QCheckBox, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QKeyEvent


# ─── Учётные данные вынесены в константу ──────────────────────────────────────
# Формат: "логин": (роль, пароль)
# В production заменить на проверку через БД с хэшированием паролей (bcrypt/argon2)
_VALID_USERS: dict[str, tuple[str, str]] = {
    "sa":  ("sa",  "sa"),
    "dir": ("dir", "dir"),
    "vet": ("vet", "vet"),
}
_MAX_LOGIN_ATTEMPTS = 5


def _encode(text: str) -> str:
    """Минимальное обфусцирование пароля перед сохранением в QSettings."""
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _decode(text: str) -> str:
    """Декодирование пароля из QSettings."""
    try:
        return base64.b64decode(text.encode("ascii")).decode("utf-8")
    except Exception:
        return ""


# ─── Диалог авторизации ────────────────────────────────────────────────────────
class LoginDialog(QDialog):
    """
    Диалоговое окно авторизации при входе в систему.
    Поддерживает сохранение логина/пароля через QSettings (пароль обфусцирован base64).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Авторизация системы")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        self.setFixedSize(400, 340)

        self.role             = None
        self._login_attempts  = 0
        self.settings         = QSettings("RogaIKopyta", "ERP_Auth")

        # Наследуем стили родителя или применяем тёмную тему по умолчанию
        if parent:
            self.setStyleSheet(parent.styleSheet())
        else:
            try:
                from ui.styles import STYLESHEET_DARK
                self.setStyleSheet(STYLESHEET_DARK)
            except ImportError:
                pass

        self._init_ui()
        self._center_on_screen()
        self._load_saved_credentials()

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            g = screen.geometry()
            self.move(
                (g.width()  - self.width())  // 2,
                (g.height() - self.height()) // 2,
            )

    def _init_ui(self):
        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("InfoPopup")
        self.main_frame.setGeometry(0, 0, 400, 340)

        layout = QVBoxLayout(self.main_frame)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(12)

        # Заголовок
        title = QLabel("ВХОД В СИСТЕМУ")
        title.setObjectName("InfoTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "font-size: 20px; font-weight: bold; border: none; margin-bottom: 5px;"
        )
        layout.addWidget(title)

        # Поле логина — стиль берётся из темы через objectName,
        # не хардкодим цвета inline чтобы смена темы работала корректно
        self.txt_username = QLineEdit()
        self.txt_username.setObjectName("LoginInput")
        self.txt_username.setPlaceholderText("Логин (sa, dir, vet)")
        self.txt_username.returnPressed.connect(self.attempt_login)
        layout.addWidget(self.txt_username)

        # Поле пароля + кнопка показа
        pwd_layout = QHBoxLayout()
        pwd_layout.setSpacing(5)

        self.txt_password = QLineEdit()
        self.txt_password.setObjectName("LoginInput")
        self.txt_password.setPlaceholderText("Пароль")
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.returnPressed.connect(self.attempt_login)

        self.btn_show_pass = QPushButton("👁️")
        self.btn_show_pass.setCheckable(True)
        self.btn_show_pass.setFixedSize(36, 36)
        self.btn_show_pass.setStyleSheet("""
            QPushButton {
                background-color: #16161e;
                color: #a9b1d6;
                border: 1px solid #292e42;
                border-radius: 6px;
                font-size: 14px;
                padding: 0;
            }
            QPushButton:hover { background-color: #24283b; }
            QPushButton:checked { background-color: #292e42; color: #7aa2f7; }
        """)
        self.btn_show_pass.toggled.connect(self._toggle_password_visibility)

        pwd_layout.addWidget(self.txt_password, stretch=1)
        pwd_layout.addWidget(self.btn_show_pass)
        layout.addLayout(pwd_layout)

        # Чекбокс «Запомнить пароль»
        self.chk_remember = QCheckBox("Запомнить пароль")
        self.chk_remember.setStyleSheet(
            "QCheckBox { color: #a9b1d6; font-size: 12px; border: none; }"
        )
        layout.addWidget(self.chk_remember)

        # Метка ошибок
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet(
            "color: #f7768e; font-size: 12px; border: none;"
        )
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_error.setWordWrap(True)
        layout.addWidget(self.lbl_error)

        # Кнопки
        btn_layout = QHBoxLayout()

        self.btn_cancel = QPushButton("ОТМЕНА")
        self.btn_cancel.setObjectName("ExitBtn")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_login = QPushButton("ВОЙТИ")
        self.btn_login.setDefault(True)
        self.btn_login.clicked.connect(self.attempt_login)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_login)
        layout.addLayout(btn_layout)

    def _toggle_password_visibility(self, checked: bool):
        if checked:
            self.txt_password.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_show_pass.setText("🔒")
        else:
            self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_show_pass.setText("👁️")

    def attempt_login(self):
        # Блокировка после превышения лимита попыток
        if self._login_attempts >= _MAX_LOGIN_ATTEMPTS:
            self.lbl_error.setText(
                f"Превышен лимит попыток ({_MAX_LOGIN_ATTEMPTS}). "
                "Перезапустите приложение."
            )
            self.btn_login.setEnabled(False)
            return

        username = self.txt_username.text().strip()
        password = self.txt_password.text().strip()

        # Защита от пустых полей
        if not username or not password:
            self.lbl_error.setText("Заполните логин и пароль.")
            return

        if username in _VALID_USERS and _VALID_USERS[username][1] == password:
            self.role = _VALID_USERS[username][0]
            self._save_credentials(username, password)
            self.lbl_error.setText("")
            self.accept()
        else:
            self._login_attempts += 1
            remaining = _MAX_LOGIN_ATTEMPTS - self._login_attempts
            self.lbl_error.setText(
                f"Неверный логин или пароль! "
                f"Осталось попыток: {remaining}"
            )
            self.txt_password.clear()
            self.txt_password.setFocus()

    def _save_credentials(self, username: str, password: str):
        if self.chk_remember.isChecked():
            self.settings.setValue("remember",  True)
            self.settings.setValue("username",  username)
            # Пароль сохраняется обфусцированным, не открытым текстом
            self.settings.setValue("password",  _encode(password))
        else:
            self.settings.setValue("remember",  False)
            self.settings.setValue("username",  "")
            self.settings.setValue("password",  "")

    def _load_saved_credentials(self):
        remember = self.settings.value("remember", False, type=bool)
        if remember:
            self.chk_remember.setChecked(True)
            self.txt_username.setText(self.settings.value("username", ""))
            self.txt_password.setText(
                _decode(self.settings.value("password", ""))
            )

    def keyPressEvent(self, event: QKeyEvent):
        # Escape — отмена, Enter — попытка входа
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.attempt_login()
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        self.main_frame.resize(self.size())
        super().resizeEvent(event)


# ─── Базовое уведомление ───────────────────────────────────────────────────────
class BaseNotification(QDialog):
    """
    Базовый класс модальных уведомлений.
    Размер окна адаптируется под длину сообщения (не фиксированный).
    """

    def __init__(
        self,
        parent=None,
        title:    str = "УВЕДОМЛЕНИЕ",
        message:  str = "",
        frame_id: str = "InfoPopup",
        title_id: str = "InfoTitle",
        btn_id:   str = "BtnAcknowledgeInfo",
    ):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        # Минимальный размер — растягивается под контент
        self.setMinimumSize(500, 220)
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Minimum,
        )

        if parent:
            self.setStyleSheet(parent.styleSheet())

        self.main_frame = QFrame(self)
        self.main_frame.setObjectName(frame_id)

        layout = QVBoxLayout(self.main_frame)
        layout.setContentsMargins(30, 40, 30, 40)
        layout.setSpacing(20)

        # Заголовок
        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName(title_id)
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setWordWrap(True)
        layout.addWidget(self.lbl_title)

        # Сообщение
        self.lbl_msg = QLabel(message)
        self.lbl_msg.setObjectName("NotifText")
        self.lbl_msg.setWordWrap(True)
        self.lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_msg)

        # Кнопка подтверждения
        self.btn_close = QPushButton("ПОНЯТНО")
        self.btn_close.setObjectName(btn_id)
        self.btn_close.setDefault(True)
        self.btn_close.setFixedWidth(160)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.accept)
        layout.addWidget(self.btn_close, alignment=Qt.AlignmentFlag.AlignCenter)

        # Подгоняем размер окна под содержимое и центрируем
        self.adjustSize()
        self._center_on_screen()

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            g = screen.geometry()
            self.move(
                (g.width()  - self.width())  // 2,
                (g.height() - self.height()) // 2,
            )

    def keyPressEvent(self, event: QKeyEvent):
        # Enter и Escape оба закрывают уведомление
        if event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
            Qt.Key.Key_Escape,
        ):
            self.accept()
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        self.main_frame.resize(self.size())
        super().resizeEvent(event)


# ─── Конкретные типы уведомлений ──────────────────────────────────────────────
class CriticalAlert(BaseNotification):
    """Критическое уведомление (красная рамка)."""
    def __init__(self, parent=None, title="КРИТИЧЕСКОЕ", message=""):
        super().__init__(
            parent, title, message,
            frame_id="CriticalPopup",
            title_id="CriticalTitle",
            btn_id="BtnAcknowledgeCrit",
        )


class WarningAlert(BaseNotification):
    """Предупреждение (жёлтая рамка)."""
    def __init__(self, parent=None, title="ПРЕДУПРЕЖДЕНИЕ", message=""):
        super().__init__(
            parent, title, message,
            frame_id="WarningPopup",
            title_id="WarningTitle",
            btn_id="BtnAcknowledgeWarn",
        )


class InfoAlert(BaseNotification):
    """Информационное уведомление (синяя рамка)."""
    def __init__(self, parent=None, title="ИНФОРМАЦИЯ", message=""):
        super().__init__(
            parent, title, message,
            frame_id="InfoPopup",
            title_id="InfoTitle",
            btn_id="BtnAcknowledgeInfo",
        )