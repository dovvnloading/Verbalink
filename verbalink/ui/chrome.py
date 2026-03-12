"""Reusable frameless window chrome components."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDialog,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CustomTitleBar(QWidget):
    def __init__(self, parent=None, title="", enable_maximize=True):
        super().__init__(parent)
        self.parent = parent
        self.enable_maximize = enable_maximize
        self.is_pressed = False
        self.start_pos = None
        self.setup_ui(title)

    def setup_ui(self, title):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)

        # Title label
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold;")

        # Window controls
        btn_size = 16
        self.minimize_btn = QPushButton("─")
        self.minimize_btn.setFixedSize(btn_size, btn_size)
        self.minimize_btn.clicked.connect(self.parent.showMinimized)
        self.minimize_btn.setAutoDefault(False)
        self.minimize_btn.setDefault(False)

        if self.enable_maximize:
            self.maximize_btn = QPushButton("□")
            self.maximize_btn.setFixedSize(btn_size, btn_size)
            self.maximize_btn.clicked.connect(self.toggle_maximize)
            self.maximize_btn.setAutoDefault(False)
            self.maximize_btn.setDefault(False)

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(btn_size, btn_size)
        self.close_btn.clicked.connect(self.parent.close)
        self.close_btn.setAutoDefault(False)
        self.close_btn.setDefault(False)

        # Add widgets to layout
        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(self.minimize_btn)
        if self.enable_maximize:
            layout.addWidget(self.maximize_btn)
        layout.addWidget(self.close_btn)

        self.update_style()

        # Set focus policy to prevent focus
        self.setFocusPolicy(Qt.NoFocus)
        self.minimize_btn.setFocusPolicy(Qt.NoFocus)
        if self.enable_maximize:
            self.maximize_btn.setFocusPolicy(Qt.NoFocus)
        self.close_btn.setFocusPolicy(Qt.NoFocus)

    def update_style(self):
        is_dark = self.parent.is_dark_mode if hasattr(self.parent, 'is_dark_mode') else False
        bg_color = "#1e1e1e" if is_dark else "#f0f0f0"
        text_color = "#ffffff" if is_dark else "#525252"
        button_hover = "#3a3a3a" if is_dark else "#e0e0e0"
        close_hover = "#c42b1c"

        self.setStyleSheet(f"""
            CustomTitleBar {{
                background-color: {bg_color};
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }}
            QLabel {{
                color: {text_color};
                background: transparent;
            }}
            QPushButton {{
                background: transparent;
                border: none;
                color: {text_color};
                border-radius: 2px;
                padding: 2px;
            }}
            QPushButton:hover {{
                background: {button_hover};
            }}
            QPushButton#closeButton:hover {{
                background: {close_hover};
                color: white;
            }}
        """)
        self.close_btn.setObjectName("closeButton")

    def toggle_maximize(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
            self.maximize_btn.setText("□")
        else:
            self.parent.showMaximized()
            self.maximize_btn.setText("❐")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_pressed = True
            self.start_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.is_pressed = False
        self.start_pos = None

    def mouseMoveEvent(self, event):
        if self.is_pressed:
            if self.start_pos is not None:
                move = event.globalPos() - self.start_pos
                self.parent.move(self.parent.pos() + move)
                self.start_pos = event.globalPos()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            event.ignore()
        else:
            super().keyPressEvent(event)


class CustomTitleBarWindow(QDialog):
    def __init__(self, parent=None, title="", enable_maximize=True):
        super().__init__(parent, Qt.Window | Qt.FramelessWindowHint)
        self.parent = parent
        self.setup_window(title, enable_maximize)

    def setup_window(self, title, enable_maximize):
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Custom title bar
        self.title_bar = CustomTitleBar(self, title, enable_maximize)
        self.main_layout.addWidget(self.title_bar)

        # Content widget
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.main_layout.addWidget(self.content_widget)

        # Apply window shadow
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setOffset(0, 0)
        self.shadow.setColor(QColor(0, 0, 0, 100))
        self.setGraphicsEffect(self.shadow)

    def update_style(self):
        is_dark = self.parent.is_dark_mode if hasattr(self.parent, 'is_dark_mode') else False
        bg_color = "#2b2b2b" if is_dark else "#ffffff"
        border_color = "#3a3a3a" if is_dark else "#d0d0d0"

        self.setStyleSheet(f"""
            CustomTitleBarWindow {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 5px;
            }}
        """)
        self.title_bar.update_style()

    def get_content_layout(self):
        return self.content_layout

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            event.ignore()
        else:
            super().keyPressEvent(event)

    def nativeEvent(self, eventType, message):
        retval, result = super().nativeEvent(eventType, message)
        return retval, result

