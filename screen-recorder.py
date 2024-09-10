import sys
import os
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QComboBox, QLabel, QFileDialog
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QPainter, QPen
from mss import mss
from PIL import Image
import pygetwindow as gw

class ScreenRecorder(QThread):
    finished = pyqtSignal()
    frame_captured = pyqtSignal(np.ndarray)

    def __init__(self, monitor, output_path):
        super().__init__()
        self.monitor = monitor
        self.output_path = output_path
        self.recording = False

    def run(self):
        with mss() as sct:
            monitor = sct.monitors[self.monitor]
            
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(self.output_path, fourcc, 30.0, (monitor["width"], monitor["height"]))

            while self.recording:
                img = sct.grab(monitor)
                frame = Image.frombytes("RGB", img.size, img.rgb)
                frame = cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR)
                out.write(frame)
                self.frame_captured.emit(frame)

            out.release()
        self.finished.emit()

class RecordingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background:transparent;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
        painter.drawRect(self.rect())

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screen Recorder")
        self.setGeometry(100, 100, 300, 250)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.monitor_combo = QComboBox()
        self.monitor_combo.addItems([f"Monitor {i+1}" for i in range(len(mss().monitors))])
        layout.addWidget(QLabel("Select Monitor:"))
        layout.addWidget(self.monitor_combo)

        self.window_combo = QComboBox()
        self.update_window_list()
        layout.addWidget(QLabel("Select Window:"))
        layout.addWidget(self.window_combo)

        self.output_path = self.get_default_output_path()
        self.path_label = QLabel(f"Output: {self.output_path}")
        layout.addWidget(self.path_label)

        self.select_path_button = QPushButton("Select Output Path")
        self.select_path_button.clicked.connect(self.select_output_path)
        layout.addWidget(self.select_path_button)

        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        layout.addWidget(self.record_button)

        self.recorder = None
        self.overlay = None

    def get_default_output_path(self):
        if sys.platform == "win32":
            videos_dir = os.path.join(os.path.expanduser("~"), "Videos")
            return os.path.join(videos_dir, "screen_recording.mp4")
        return ""

    def select_output_path(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Recording", "", "MP4 Files (*.mp4)")
        if path:
            self.output_path = path
            self.path_label.setText(f"Output: {self.output_path}")

    def update_window_list(self):
        self.window_combo.clear()
        self.window_combo.addItems([win.title for win in gw.getAllWindows() if win.title])

    def toggle_recording(self):
        if self.recorder is None or not self.recorder.isRunning():
            if not self.output_path:
                self.select_output_path()
                if not self.output_path:
                    return

            monitor = self.monitor_combo.currentIndex()
            self.recorder = ScreenRecorder(monitor, self.output_path)
            self.recorder.finished.connect(self.recording_finished)
            self.recorder.frame_captured.connect(self.update_overlay)
            self.recorder.recording = True
            self.recorder.start()
            self.record_button.setText("Stop Recording")
            self.show_overlay()
        else:
            self.recorder.recording = False
            self.record_button.setEnabled(False)
            self.hide_overlay()

    def show_overlay(self):
        if self.window_combo.currentText():
            window = gw.getWindowsWithTitle(self.window_combo.currentText())[0]
            geometry = window.left, window.top, window.width, window.height
        else:
            monitor = mss().monitors[self.monitor_combo.currentIndex()]
            geometry = monitor["left"], monitor["top"], monitor["width"], monitor["height"]

        self.overlay = RecordingOverlay()
        self.overlay.setGeometry(*geometry)
        self.overlay.show()

    def hide_overlay(self):
        if self.overlay:
            self.overlay.hide()
            self.overlay = None

    def update_overlay(self, frame):
        if self.overlay:
            self.overlay.update()

    def recording_finished(self):
        self.record_button.setText("Start Recording")
        self.record_button.setEnabled(True)
        self.hide_overlay()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
