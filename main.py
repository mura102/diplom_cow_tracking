import os
import platform
import sys

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
    app.setApplicationName("Рога и копыта AI")

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