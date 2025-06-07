
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QLineEdit, QMessageBox,
    QCheckBox, QScrollArea, QGroupBox, QComboBox, QSlider, QProgressBar
)
from PySide6.QtCore import Qt, QTimer, QObject, Signal, QThread
import pandas as pd
import os
import threading
import queue

class ProcessingWorker(QObject):
    progress = Signal(int)                
    completed = Signal(dict)            
    error = Signal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        try:
            from main import run_data_processing
            results = run_data_processing(self.params, self)
            self.completed.emit(results)
        except Exception as e:
            self.error.emit(str(e))

class AuditAppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Taxonomy Audit Helper - Qt Edition")
        self.setMinimumSize(900, 950)

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout(self.main_widget)

        # State
        self.output_dir_path = ''
        self.usage_file_path = ''
        self.usage_df = None
        self.workspace_checkboxes = {}
        self.project_checkboxes = {}
        self.selected_workspaces = []
        self.selected_projects = []
        self.event_files = {}
        self.user_props_files = {}
        self.lookback_window = "30"
        self.threshold = 90

        self.processing_button = None
        self.progress_bar = None

        # UI setup
        self.init_output_dir_section()
        self.init_usage_file_section()
        self.init_workspace_selection()
        self.init_project_selection()
        self.init_project_file_selectors()
        self.init_lookback_selector()
        self.init_threshold_slider()
        self.init_start_processing_section()

    def init_output_dir_section(self):
        layout = QHBoxLayout()
        label = QLabel("1. Select Output Directory:")
        self.output_dir_line = QLineEdit()
        self.output_dir_line.setReadOnly(True)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_output_dir)
        layout.addWidget(label)
        layout.addWidget(self.output_dir_line)
        layout.addWidget(browse_button)
        self.main_layout.addLayout(layout)

    def browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.output_dir_path = dir_path
            self.output_dir_line.setText(dir_path)
            QMessageBox.information(self, "Output Directory Selected", f"Output directory set to:\n{dir_path}")

    def init_usage_file_section(self):
        layout = QHBoxLayout()
        label = QLabel("2. Select Usage Report File:")
        self.usage_file_line = QLineEdit()
        self.usage_file_line.setReadOnly(True)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_usage_file)
        layout.addWidget(label)
        layout.addWidget(self.usage_file_line)
        layout.addWidget(browse_button)
        self.main_layout.addLayout(layout)

    def browse_usage_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Usage Report CSV", "", "CSV Files (*.csv)")
        if file_path:
            self.usage_file_path = file_path
            self.usage_file_line.setText(file_path)
            try:
                self.usage_df = pd.read_csv(file_path, parse_dates=['First Seen', 'Last Seen'])
                self.populate_workspaces()
                QMessageBox.information(self, "Usage Report Loaded", "Usage report loaded successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error Loading CSV", str(e))

    def init_workspace_selection(self):
        self.workspace_group = QGroupBox("3. Select Workspace(s)")
        workspace_layout = QVBoxLayout()
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.workspace_checkbox_container = QWidget()
        self.workspace_checkbox_layout = QVBoxLayout(self.workspace_checkbox_container)
        scroll_area.setWidget(self.workspace_checkbox_container)
        workspace_layout.addWidget(scroll_area)
        self.workspace_group.setLayout(workspace_layout)
        self.main_layout.addWidget(self.workspace_group)

    def init_project_selection(self):
        self.project_group = QGroupBox("4. Select Project(s)")
        project_layout = QVBoxLayout()
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.project_checkbox_container = QWidget()
        self.project_checkbox_layout = QVBoxLayout(self.project_checkbox_container)
        scroll_area.setWidget(self.project_checkbox_container)
        project_layout.addWidget(scroll_area)
        self.project_group.setLayout(project_layout)
        self.main_layout.addWidget(self.project_group)

    def init_project_file_selectors(self):
        self.file_group = QGroupBox("5. Select Event and User Property Files")
        file_layout = QVBoxLayout()
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.file_container = QWidget()
        self.file_layout = QVBoxLayout(self.file_container)
        scroll_area.setWidget(self.file_container)
        file_layout.addWidget(scroll_area)
        self.file_group.setLayout(file_layout)
        self.main_layout.addWidget(self.file_group)

    def init_lookback_selector(self):
        layout = QHBoxLayout()
        label = QLabel("6. Select Lookback Window (Days):")
        self.lookback_combo = QComboBox()
        self.lookback_combo.addItems(["30", "90", "180", "270", "365"])
        self.lookback_combo.setCurrentText("30")
        self.lookback_combo.currentTextChanged.connect(self.update_lookback_window)
        layout.addWidget(label)
        layout.addWidget(self.lookback_combo)
        self.main_layout.addLayout(layout)

    def update_lookback_window(self, value):
        self.lookback_window = value

    def init_threshold_slider(self):
        group = QGroupBox("7. Set Match Threshold")
        layout = QVBoxLayout()
        self.threshold_label = QLabel(f"Threshold: {self.threshold}")
        self.threshold_explanation = QLabel(self.get_threshold_explanation(self.threshold))
        self.threshold_explanation.setWordWrap(True)
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(100)
        self.threshold_slider.setValue(self.threshold)
        self.threshold_slider.valueChanged.connect(self.update_threshold)
        layout.addWidget(self.threshold_label)
        layout.addWidget(self.threshold_slider)
        layout.addWidget(self.threshold_explanation)
        group.setLayout(layout)
        self.main_layout.addWidget(group)

    def update_threshold(self, value):
        self.threshold = value
        self.threshold_label.setText(f"Threshold: {value}")
        self.threshold_explanation.setText(self.get_threshold_explanation(value))

    def get_threshold_explanation(self, value):
        if value >= 85:
            return "Good results for close to exact matches."
        elif value >= 70:
            return "Use for moderate matches and grouping opportunities."
        else:
            return "Use lower values for higher verbosity or consolidation opportunities."

    def init_start_processing_section(self):
        layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setTextVisible(True)
        self.processing_button = QPushButton("Start Processing")
        self.processing_button.clicked.connect(self.start_processing)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.processing_button)
        self.main_layout.addLayout(layout)

    def start_processing(self):
        if not self.output_dir_path or not self.usage_file_path or not self.selected_projects:
            QMessageBox.warning(self, "Missing Inputs", "Please complete all selections.")
            return
        if any(p not in self.event_files for p in self.selected_projects):
            QMessageBox.warning(self, "Missing Files", "Please select event files for all projects.")
            return

        params = {
            "output_dir": self.output_dir_path,
            "usage_file": self.usage_file_path,
            "selected_projects": self.selected_projects,
            "selected_workspaces": self.selected_workspaces,
            "event_files": self.event_files,
            "user_props_files": self.user_props_files,
            "lookback_window": int(self.lookback_window),
            "threshold": self.threshold
        }

        self.progress_bar.setValue(5)
        self.processing_button.setEnabled(False)

        # Setup QThread and ProcessingWorker
        self.thread = QThread()
        self.worker = ProcessingWorker(params)
        self.worker.moveToThread(self.thread)

        self.worker.progress.connect(self.update_progress)
        self.worker.completed.connect(self.update_results)
        self.worker.error.connect(self.show_error)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def update_progress(self, percent):
        self.progress_bar.setValue(int(percent))

    def update_results(self, results):
        self.progress_bar.setValue(100)
        self.processing_button.setEnabled(True)
        QMessageBox.information(self, "Complete", "Processing completed successfully!")

    def show_error(self, message):
        QMessageBox.critical(self, "Processing Error", message)

    def populate_workspaces(self):
        self.workspace_checkboxes.clear()
        self.clear_layout(self.workspace_checkbox_layout)
        workspaces = self.usage_df['Workspace Name'].dropna().unique()
        for ws in sorted(workspaces):
            checkbox = QCheckBox(ws)
            checkbox.stateChanged.connect(self.handle_workspace_selection)
            self.workspace_checkboxes[ws] = checkbox
            self.workspace_checkbox_layout.addWidget(checkbox)

    def handle_workspace_selection(self):
        self.selected_workspaces = [name for name, cb in self.workspace_checkboxes.items() if cb.isChecked()]
        self.project_checkboxes.clear()
        self.clear_layout(self.project_checkbox_layout)
        if not self.selected_workspaces:
            return
        filtered_projects = (
            self.usage_df[self.usage_df['Workspace Name'].isin(self.selected_workspaces)]
            ['Project Name'].dropna().unique()
        )
        for proj in sorted(filtered_projects):
            checkbox = QCheckBox(proj)
            checkbox.stateChanged.connect(self.handle_project_selection)
            self.project_checkboxes[proj] = checkbox
            self.project_checkbox_layout.addWidget(checkbox)

    def handle_project_selection(self):
        self.selected_projects = [name for name, cb in self.project_checkboxes.items() if cb.isChecked()]
        self.event_files.clear()
        self.user_props_files.clear()
        self.clear_layout(self.file_layout)
        for project in self.selected_projects:
            project_box = QGroupBox(f"{project}")
            layout = QVBoxLayout()
            event_layout = QHBoxLayout()
            event_label = QLabel("Event File:")
            event_line = QLineEdit()
            event_line.setReadOnly(True)
            event_browse = QPushButton("Browse")
            event_browse.clicked.connect(lambda _, p=project, l=event_line: self.browse_event_file(p, l))
            event_layout.addWidget(event_label)
            event_layout.addWidget(event_line)
            event_layout.addWidget(event_browse)
            layout.addLayout(event_layout)
            user_layout = QHBoxLayout()
            user_label = QLabel("User Props File:")
            user_line = QLineEdit()
            user_line.setReadOnly(True)
            user_browse = QPushButton("Browse")
            user_browse.clicked.connect(lambda _, p=project, l=user_line: self.browse_user_props_file(p, l))
            user_layout.addWidget(user_label)
            user_layout.addWidget(user_line)
            user_layout.addWidget(user_browse)
            layout.addLayout(user_layout)
            project_box.setLayout(layout)
            self.file_layout.addWidget(project_box)

    def browse_event_file(self, project, line_edit):
        file_path, _ = QFileDialog.getOpenFileName(self, f"Select Event File for {project}", "", "CSV Files (*.csv)")
        if file_path:
            line_edit.setText(file_path)
            self.event_files[project] = file_path

    def browse_user_props_file(self, project, line_edit):
        file_path, _ = QFileDialog.getOpenFileName(self, f"Select User Props File for {project}", "", "CSV Files (*.csv)")
        if file_path:
            line_edit.setText(file_path)
            self.user_props_files[project] = file_path

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

if __name__ == "__main__":
    app = QApplication([])
    window = AuditAppWindow()
    window.show()
    app.exec()
