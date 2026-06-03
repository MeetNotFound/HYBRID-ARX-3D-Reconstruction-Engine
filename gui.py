import sys
import subprocess
import os

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QTextEdit,
    QLabel, QProgressBar,
    QFileDialog, QInputDialog,
    QFrame
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt


STAGES = [
    "FRAME_EXTRACTION",
    "FEATURE_EXTRACTION",
    "MATCHING",
    "SPARSE",
    "UNDISTORT",
    "DENSE",
    "FUSION",
    "MESH",
    "GLB"
]


# ==============================
# PIPELINE THREAD
# ==============================
class PipelineThread(QThread):
    log_signal = pyqtSignal(str)
    stage_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, mode, model_name, video_path):
        super().__init__()
        self.mode = mode
        self.model_name = model_name
        self.video_path = video_path

    def run(self):

        script_path = os.path.abspath("run_pipeline.ps1")

        cmd = [
            "powershell.exe",
            "-ExecutionPolicy", "Bypass",
            "-File", script_path,
            "-Mode", self.mode,
            "-ModelName", self.model_name,
            "-VideoPath", self.video_path
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in process.stdout:
            line = line.strip()
            self.log_signal.emit(line)

            if "[STAGE]" in line:
                stage = line.replace("[STAGE]", "").strip()
                self.stage_signal.emit(stage)

        process.wait()
        self.finished_signal.emit()


# ==============================
# MAIN GUI
# ==============================
class HybridEngineGUI(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("HYBRID-ARX Reconstruction Engine")
        self.setMinimumSize(1000, 700)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setSpacing(25)

        # ==============================
        # HEADER
        # ==============================
        header = QLabel("HYBRID-ARX")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #00d9ff;
            letter-spacing: 2px;
        """)
        main_layout.addWidget(header)

        subtitle = QLabel("Adaptive Multi-Mode 3D Reconstruction Engine")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 14px; color: #aaaaaa;")
        main_layout.addWidget(subtitle)

        # ==============================
        # SEPARATOR LINE
        # ==============================
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #333333;")
        main_layout.addWidget(line)

        # ==============================
        # CONTROL PANEL
        # ==============================
        control_layout = QHBoxLayout()
        control_layout.setSpacing(20)
        control_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        mode_label = QLabel("Reconstruction Mode:")
        mode_label.setStyleSheet("font-size: 15px;")

        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["FAST", "BALANCED", "HQ"])
        self.mode_selector.setFixedWidth(200)

        self.run_button = QPushButton("Create New Model")
        self.run_button.setFixedWidth(220)
        self.run_button.clicked.connect(self.start_pipeline)

        control_layout.addWidget(mode_label)
        control_layout.addWidget(self.mode_selector)
        control_layout.addWidget(self.run_button)

        main_layout.addLayout(control_layout)

        # ==============================
        # PROGRESS BAR
        # ==============================
        self.progress = QProgressBar()
        self.progress.setRange(0, len(STAGES))
        self.progress.setFixedHeight(28)
        main_layout.addWidget(self.progress)

        self.status_label = QLabel("Status: Idle")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 16px;")
        main_layout.addWidget(self.status_label)

        # ==============================
        # LOG OUTPUT
        # ==============================
        log_title = QLabel("Execution Log")
        log_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        log_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        main_layout.addWidget(log_title)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("font-size: 13px;")
        main_layout.addWidget(self.log_output)

        self.setLayout(main_layout)
        self.apply_dark_theme()

    # ==============================
    # THEME
    # ==============================
    def apply_dark_theme(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #0f0f0f;
                color: #e0e0e0;
                font-family: Segoe UI;
            }

            QPushButton {
                background-color: #1f1f1f;
                padding: 10px;
                border-radius: 6px;
                font-size: 14px;
            }

            QPushButton:hover {
                background-color: #2c2c2c;
            }

            QComboBox {
                background-color: #1f1f1f;
                padding: 6px;
                border-radius: 5px;
            }

            QProgressBar {
                border: 1px solid #333;
                border-radius: 5px;
                text-align: center;
                background-color: #1a1a1a;
            }

            QProgressBar::chunk {
                background-color: #00d9ff;
            }

            QTextEdit {
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 6px;
            }
        """)

    # ==============================
    # START PIPELINE
    # ==============================
    def start_pipeline(self):

        video_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Model Video",
            "",
            "Video Files (*.mp4 *.mov *.avi)"
        )

        if not video_path:
            return

        model_name, ok = QInputDialog.getText(
            self,
            "Model Name",
            "Enter Model Name:"
        )

        if not ok or not model_name:
            return

        self.log_output.clear()
        self.progress.setValue(0)

        mode = self.mode_selector.currentText()

        self.thread = PipelineThread(mode, model_name, video_path)
        self.thread.log_signal.connect(self.update_log)
        self.thread.stage_signal.connect(self.update_stage)
        self.thread.finished_signal.connect(self.finished)
        self.thread.start()

        self.status_label.setText("Status: Running")

    def update_log(self, text):
        self.log_output.append(text)

    def update_stage(self, stage):
        if stage in STAGES:
            index = STAGES.index(stage) + 1
            self.progress.setValue(index)
            self.status_label.setText(f"Status: {stage}")

    def finished(self):
        self.status_label.setText("Status: Completed")


# ==============================
# RUN APPLICATION
# ==============================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HybridEngineGUI()
    window.show()
    sys.exit(app.exec())