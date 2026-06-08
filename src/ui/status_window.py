import sys
import os
import random
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup, QTimer
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush
from PyQt5.QtWidgets import QApplication, QLabel, QHBoxLayout, QWidget, QGraphicsOpacityEffect

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ui.base_window import BaseWindow


class PulseDot(QWidget):
    def __init__(self, color='#f38ba8', parent=None):
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self._color = QColor(color)

    def setColor(self, color):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(self._color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 10, 10)


class WaveformBars(QWidget):
    BAR_COUNT = 12
    MAX_HEIGHT = 22
    BAR_WIDTH = 4
    BAR_GAP = 2

    def __init__(self, color='#f38ba8', parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._heights = [0.0] * self.BAR_COUNT
        self._targets = [0.0] * self.BAR_COUNT
        total_w = self.BAR_COUNT * (self.BAR_WIDTH + self.BAR_GAP) - self.BAR_GAP
        self.setFixedSize(total_w, self.MAX_HEIGHT)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.setInterval(30)

    def setColor(self, color):
        self._color = QColor(color)
        self.update()

    def setLevel(self, level):
        level = max(0.0, min(1.0, level))
        for i in range(self.BAR_COUNT):
            variation = random.uniform(0.35, 1.0)
            self._targets[i] = max(self._targets[i] * 0.6, level * variation)

    def start(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()
        self._targets = [0.0] * self.BAR_COUNT
        self._heights = [0.0] * self.BAR_COUNT
        self.update()

    def _tick(self):
        for i in range(self.BAR_COUNT):
            # Decay targets slowly
            self._targets[i] *= 0.88
            # Smoothly move heights toward targets
            self._heights[i] += (self._targets[i] - self._heights[i]) * 0.35
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.BAR_WIDTH
        g = self.BAR_GAP
        max_h = self.MAX_HEIGHT
        mid_y = self.height() // 2

        for i in range(self.BAR_COUNT):
            h = max(2, int(self._heights[i] * max_h))
            x = i * (w + g)
            y = mid_y - h // 2

            alpha = 80 + int(175 * self._heights[i])
            color = QColor(self._color)
            color.setAlpha(alpha)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x, y, w, h, 2, 2)


class StatusWindow(BaseWindow):
    statusSignal = pyqtSignal(str)
    closeSignal = pyqtSignal()

    def __init__(self):
        super().__init__('WhisperWriter Status', 320, 62, show_title_bar=False)
        self.initStatusUI()
        self.statusSignal.connect(self.updateStatus)

    def initStatusUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)

        self.pulse_dot = PulseDot('#f38ba8')

        self.waveform = WaveformBars('#f38ba8')

        self.status_label = QLabel('Recording...')
        self.status_label.setFont(QFont('Segoe UI', 11, QFont.Medium))
        self.status_label.setStyleSheet("color: #f38ba8;")

        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(10)
        status_layout.addStretch()
        status_layout.addWidget(self.pulse_dot, alignment=Qt.AlignVCenter)
        status_layout.addWidget(self.waveform, alignment=Qt.AlignVCenter)
        status_layout.addWidget(self.status_label, alignment=Qt.AlignVCenter)
        status_layout.addStretch()

        self.main_layout.setContentsMargins(16, 0, 16, 0)
        self.main_layout.addLayout(status_layout)

        # Pulse animation for dot
        self.opacity_effect = QGraphicsOpacityEffect(self.pulse_dot)
        self.pulse_dot.setGraphicsEffect(self.opacity_effect)

        anim_out = QPropertyAnimation(self.opacity_effect, b'opacity')
        anim_out.setDuration(600)
        anim_out.setStartValue(1.0)
        anim_out.setEndValue(0.15)
        anim_out.setEasingCurve(QEasingCurve.InOutSine)

        anim_in = QPropertyAnimation(self.opacity_effect, b'opacity')
        anim_in.setDuration(600)
        anim_in.setStartValue(0.15)
        anim_in.setEndValue(1.0)
        anim_in.setEasingCurve(QEasingCurve.InOutSine)

        self.pulse_anim = QSequentialAnimationGroup()
        self.pulse_anim.addAnimation(anim_out)
        self.pulse_anim.addAnimation(anim_in)
        self.pulse_anim.setLoopCount(-1)

    def show(self):
        screen = QApplication.primaryScreen()
        geo = screen.geometry()
        x = (geo.width() - self.width()) // 2
        y = geo.height() - self.height() - 100
        self.move(x, y)
        super().show()

    def closeEvent(self, event):
        self.pulse_anim.stop()
        self.waveform.stop()
        self.closeSignal.emit()
        super().closeEvent(event)

    @pyqtSlot(float)
    def updateLevel(self, level):
        self.waveform.setLevel(level)

    @pyqtSlot(str)
    def updateStatus(self, status):
        if status == 'recording':
            self.pulse_dot.setColor('#f38ba8')
            self.waveform.setColor('#f38ba8')
            self.status_label.setText('Recording...')
            self.status_label.setStyleSheet("color: #f38ba8; font-family: 'Segoe UI';")
            self.waveform.setVisible(True)
            self.waveform.start()
            if self.pulse_anim.state() != QSequentialAnimationGroup.Running:
                self.pulse_anim.start()
            self.show()
        elif status == 'transcribing':
            self.pulse_dot.setColor('#89b4fa')
            self.waveform.setColor('#89b4fa')
            self.status_label.setText('Transcribing...')
            self.status_label.setStyleSheet("color: #89b4fa; font-family: 'Segoe UI';")
            self.waveform.setVisible(False)
            self.waveform.stop()
            if self.pulse_anim.state() != QSequentialAnimationGroup.Running:
                self.pulse_anim.start()
        if status in ('idle', 'error', 'cancel'):
            self.pulse_anim.stop()
            self.waveform.stop()
            self.close()


if __name__ == '__main__':
    from PyQt5.QtCore import QTimer
    app = QApplication(sys.argv)
    w = StatusWindow()
    w.statusSignal.emit('recording')
    # Simulate some audio levels
    import random
    def fake_level():
        w.updateLevel(random.uniform(0.1, 0.9))
    t = QTimer()
    t.timeout.connect(fake_level)
    t.start(80)
    QTimer.singleShot(4000, lambda: w.statusSignal.emit('transcribing'))
    QTimer.singleShot(7000, lambda: w.statusSignal.emit('idle'))
    sys.exit(app.exec_())
