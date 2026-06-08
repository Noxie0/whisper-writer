import os
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QBrush, QColor, QFont, QPainterPath, QGuiApplication, QPen
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QMainWindow

_UI_DIR = os.path.dirname(os.path.abspath(__file__))
_ASSETS = os.path.normpath(os.path.join(_UI_DIR, '..', '..', 'assets')).replace('\\', '/')
_ARROW_DOWN_PATH = f'{_ASSETS}/arrow_down.svg'
_ARROW_UP_PATH = f'{_ASSETS}/arrow_up.svg'

GLOBAL_STYLE = """
QWidget {
    font-family: 'Segoe UI', sans-serif;
    font-size: 11px;
    color: #cdd6f4;
    background: transparent;
}
QMainWindow {
    background: transparent;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #cba6f7, stop:1 #a98de8);
    color: #1e1e2e;
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: 600;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d4b1ff, stop:1 #b4befe);
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #a98de8, stop:1 #9173c6);
}
QPushButton:disabled {
    background: #313244;
    color: #6c7086;
}
QLineEdit {
    background-color: #45475a;
    color: #cdd6f4;
    border: 1px solid #7f849c;
    border-radius: 6px;
    padding: 5px 10px;
}
QLineEdit:focus {
    border: 2px solid #cba6f7;
}
QLineEdit:disabled {
    color: #6c7086;
    background-color: #313244;
    border-color: #45475a;
}
QComboBox {
    background-color: #45475a;
    color: #cdd6f4;
    border: 1px solid #7f849c;
    border-radius: 6px;
    padding: 5px 10px;
}
QComboBox:focus {
    border: 2px solid #cba6f7;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: url(ARROW_DOWN_PLACEHOLDER);
    width: 10px;
    height: 6px;
}
QComboBox QAbstractItemView {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    outline: none;
    selection-background-color: #cba6f7;
    selection-color: #1e1e2e;
}
QCheckBox {
    color: #cdd6f4;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #7f849c;
    border-radius: 4px;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-color: #cba6f7;
    border-color: #cba6f7;
}
QCheckBox::indicator:hover {
    border-color: #cba6f7;
}
QTabWidget::pane {
    border: 1px solid #45475a;
    background-color: #1e1e2e;
    top: -1px;
}
QTabBar::tab {
    background-color: #181825;
    color: #9399b2;
    padding: 8px 16px;
    border: 1px solid #45475a;
    border-bottom: none;
    border-radius: 4px 4px 0 0;
    margin-right: 1px;
}
QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border-top: 2px solid #cba6f7;
}
QTabBar::tab:hover:!selected {
    background-color: #313244;
    color: #bac2de;
}
QScrollArea {
    background: transparent;
    border: none;
}
QScrollBar:vertical {
    background-color: #181825;
    width: 6px;
    border-radius: 3px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #cba6f7;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    height: 0;
}
QLabel {
    color: #cdd6f4;
}
QToolButton {
    background: transparent;
    border: none;
    color: #6c7086;
}
QToolButton:hover {
    color: #d4b1ff;
}
QTableWidget {
    background-color: #181825;
    alternate-background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #7f849c;
    border-radius: 6px;
    gridline-color: #45475a;
}
QTableWidget::item {
    padding: 4px 8px;
    border: none;
}
QTableWidget::item:selected {
    background-color: #cba6f7;
    color: #1e1e2e;
    padding: 4px 8px;
}
QHeaderView::section {
    background-color: #313244;
    color: #9399b2;
    border: 1px solid #45475a;
    padding: 6px 8px;
    font-weight: 600;
}
QHeaderView {
    background-color: #313244;
}
QTableWidget QLineEdit {
    background-color: #cba6f7;
    color: #1e1e2e;
    border: 2px solid #a98de8;
    border-radius: 3px;
    padding: 1px 4px;
}
"""
GLOBAL_STYLE = GLOBAL_STYLE.replace('ARROW_DOWN_PLACEHOLDER', _ARROW_DOWN_PATH)


class BaseWindow(QMainWindow):
    def __init__(self, title, width, height, show_title_bar=True):
        super().__init__()
        self.initUI(title, width, height, show_title_bar)
        self.setWindowPosition()
        self.is_dragging = False

    def initUI(self, title, width, height, show_title_bar=True):
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(width, height)

        app = QApplication.instance()
        if app:
            app.setStyleSheet(GLOBAL_STYLE)

        self.main_widget = QWidget(self)
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(14, 12, 14, 14)
        self.main_layout.setSpacing(8)

        if show_title_bar:
            title_bar = QWidget()
            title_bar.setFixedHeight(28)
            title_bar_layout = QHBoxLayout(title_bar)
            title_bar_layout.setContentsMargins(0, 0, 0, 0)
            title_bar_layout.setSpacing(0)

            title_label = QLabel('WHISPERWRITER')
            title_label.setFont(QFont('Segoe UI', 8, QFont.Bold))
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setStyleSheet("color: #6c7086; letter-spacing: 2px;")

            close_button = QPushButton('×')
            close_button.setFixedSize(22, 22)
            close_button.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #6c7086;
                    font-size: 16px;
                    font-weight: 300;
                    border-radius: 11px;
                    padding: 0;
                }
                QPushButton:hover {
                    background: #f38ba8;
                    color: #1e1e2e;
                }
            """)
            close_button.clicked.connect(self.handleCloseButton)

            title_bar_layout.addStretch()
            title_bar_layout.addWidget(title_label)
            title_bar_layout.addStretch()
            title_bar_layout.addWidget(close_button)

            self.main_layout.addWidget(title_bar)

        self.setCentralWidget(self.main_widget)

    def setWindowPosition(self):
        center_point = QGuiApplication.primaryScreen().availableGeometry().center()
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

    def handleCloseButton(self):
        self.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.start_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if Qt.LeftButton and self.is_dragging:
            self.move(event.globalPos() - self.start_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.is_dragging = False

    def paintEvent(self, event):
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 14, 14)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(30, 30, 46, 245)))
        painter.setPen(QPen(QColor(69, 71, 90, 180), 1))
        painter.drawPath(path)
