import os
import platform
import sys


def _load_dotenv():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

current_os = platform.system()

if current_os == "Linux":
    os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
    os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"

elif current_os == "Windows":
    venv_path = sys.prefix
    plugins_path = os.path.join(venv_path, "Lib", "site-packages", "PyQt6", "Qt6", "plugins")
    if os.path.exists(plugins_path):
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugins_path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QDialog
from ui.main_window import MainWindow
from ui.notifications import LoginDialog


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("УМНАЯ ФЕРМА")

    from database.db_startup import ensure_db_or_prompt

    if not ensure_db_or_prompt():
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.critical(
            None,
            "PostgreSQL",
            "Не удалось подключиться к базе данных.\n"
            "Убедитесь, что служба PostgreSQL запущена, и перезапустите приложение.",
        )
        sys.exit(1)

    login_dialog = LoginDialog()
    result = login_dialog.exec()

    if result == QDialog.DialogCode.Accepted:
        role = login_dialog.role
        window = MainWindow(role=role)
        window.show()
        sys.exit(app.exec())
    else:
        # Явно завершаем QApplication перед выходом
        app.quit()
        sys.exit(0)


if __name__ == "__main__":
    main()