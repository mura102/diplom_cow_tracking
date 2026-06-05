"""
ui/pages/page_cameras.py
Страница «Камеры» — мультивью трансляций.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QScrollArea, QGridLayout,
)
from PyQt6.QtCore import Qt


def build(mw) -> QWidget:
    """
    mw получает атрибуты: camera_layout, grid_container
    """
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(14)

    header = QHBoxLayout()
    title = QLabel("МУЛЬТИВЬЮ: ТРАНСЛЯЦИИ")
    title.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
    mw.page_titles.append(title)
    header.addWidget(title)
    header.addStretch()

    btn_add = QPushButton("➕ ДОБАВИТЬ")
    btn_add.clicked.connect(mw.add_camera_to_grid)
    header.addWidget(btn_add)

    btn_rem = QPushButton("➖ УДАЛИТЬ")
    btn_rem.clicked.connect(mw.remove_camera_via_dialog)
    header.addWidget(btn_rem)

    btn_clr = QPushButton("🗑 ОЧИСТИТЬ")
    btn_clr.setObjectName("ExitBtn")
    btn_clr.clicked.connect(mw.clear_all_cameras)
    header.addWidget(btn_clr)
    layout.addLayout(header)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setStyleSheet("background: transparent; border: none;")

    mw.grid_container = QWidget()
    mw.camera_layout = QGridLayout(mw.grid_container)
    mw.camera_layout.setSpacing(16)
    mw.camera_layout.setContentsMargins(0, 0, 0, 0)
    mw.camera_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    scroll.setWidget(mw.grid_container)
    layout.addWidget(scroll, stretch=1)
    return page
