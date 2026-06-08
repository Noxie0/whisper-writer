import os
import sys
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QPushButton, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PyQt5.QtCore import pyqtSignal, Qt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ui.base_window import BaseWindow


class MainWindow(BaseWindow):
    openSettings = pyqtSignal()
    startListening = pyqtSignal()
    closeApp = pyqtSignal()

    def __init__(self):
        super().__init__('WhisperWriter', 340, 215)
        self.initMainUI()

    def initMainUI(self):
        title_label = QLabel('WhisperWriter')
        title_label.setFont(QFont('Segoe UI', 20, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #cdd6f4; letter-spacing: 0.5px;")

        subtitle_label = QLabel('AI Speech Transcription')
        subtitle_label.setFont(QFont('Segoe UI', 9))
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #6c7086; letter-spacing: 1px;")

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #313244; border: none;")

        start_btn = QPushButton('▶   Start Listening')
        start_btn.setFont(QFont('Segoe UI', 10, QFont.Medium))
        start_btn.setFixedHeight(42)
        start_btn.clicked.connect(self.startPressed)

        settings_btn = QPushButton('⚙   Settings')
        settings_btn.setFont(QFont('Segoe UI', 10))
        settings_btn.setFixedHeight(42)
        settings_btn.setStyleSheet("""
            QPushButton {
                background: #313244;
                color: #9399b2;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 8px 20px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #45475a;
                color: #cdd6f4;
                border-color: #cba6f7;
            }
            QPushButton:pressed {
                background: #181825;
            }
        """)
        settings_btn.clicked.connect(self.openSettings.emit)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addWidget(start_btn)
        btn_layout.addWidget(settings_btn)

        self.main_layout.addStretch()
        self.main_layout.addWidget(title_label)
        self.main_layout.addWidget(subtitle_label)
        self.main_layout.addSpacing(6)
        self.main_layout.addWidget(separator)
        self.main_layout.addSpacing(4)
        self.main_layout.addLayout(btn_layout)
        self.main_layout.addStretch()

    def closeEvent(self, event):
        self.closeApp.emit()

    def startPressed(self):
        self.startListening.emit()
        self.hide()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
