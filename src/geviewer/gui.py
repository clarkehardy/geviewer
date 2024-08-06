import sys
import io
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtWidgets import QSplitter
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtWidgets import QProgressBar
from PyQt5.QtWidgets import QColorDialog
from PyQt5.QtWidgets import QAction
from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QToolBar
from PyQt5.QtWidgets import QToolButton
from PyQt5.QtWidgets import QGroupBox
from PyQt5.QtWidgets import QScrollArea
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QPalette
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QThread
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from geviewer.geviewer import GeViewer
from pyvistaqt import MainWindow


class OutputRedirect(io.StringIO):
    """Redirects stdout and stderr to a QTextEdit widget.

    :param io: The QTextEdit widget to redirect output to.
    :type io: QTextEdit
    """
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit

    def write(self, text):
        self.text_edit.append(text)
        super().write(text)

    def flush(self):
        pass


class Progress:
    """A class to handle progress updates for a worker thread.
    """
    def __init__(self,progress, max_range):
        self.range = 100
        self.value = 0
        self.progress = progress
        self.max_range = max_range


class Worker(QThread):
    """A worker thread to run a task in the background.

    :param QThread: The base class for all threads in PyQt5.
    :type QThread: class
    """
    progress = pyqtSignal(int)
    max_range = pyqtSignal(int)
    finished = pyqtSignal()
    
    def __init__(self, task, **kwargs):
        super().__init__()
        self.task = task
        self.kwargs = kwargs
        self.progress_obj = Progress(self.progress, self.max_range)

    def run(self):
        try:
            self.task(**self.kwargs, progress_obj=self.progress_obj)
        except Exception as e:
            print(e)
        self.finished.emit()


class Window(MainWindow):
    """A custom main window class for the GeViewer application.
    """
    file_name_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.current_file = 'No file loaded'
        self.setWindowTitle('GeViewer')
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.checkbox_mapping = {}

        self.splitter = QSplitter(Qt.Horizontal)

        self.plotter_widget = QWidget()
        self.plotter_layout = QVBoxLayout(self.plotter_widget)
        # Add a heading
        self.heading = QLabel('Viewing: ' + self.current_file)
        self.heading_font = QFont()
        self.heading_font.setPointSize(14)
        self.heading_font.setBold(True)
        self.heading.setFont(self.heading_font)
        self.plotter_layout.addWidget(self.heading)
        self.viewer = GeViewer(self.plotter_widget)
        self.plotter = self.viewer.plotter

        self.add_object_panel()
        self.add_control_panel()
        # self.add_dropdown()
        self.add_menu_bar()

        self.splitter.addWidget(self.object_panel)
        self.splitter.addWidget(self.plotter_widget)
        self.splitter.addWidget(self.control_panel)

        # Add the splitter to the layout
        self.main_layout.addWidget(self.splitter)

        # Collapsible Buttons
        # self.collapse_left_button = QToolButton()
        # self.collapse_left_button.setText('<')
        # self.collapse_left_button.clicked.connect(self.toggle_left_panel)
        # self.plotter_layout.addWidget(self.collapse_left_button)

        self.plotter_layout.addWidget(self.plotter.interactor)

        # self.collapse_right_button = QToolButton()
        # self.collapse_right_button.setText('>')
        # self.collapse_right_button.clicked.connect(self.toggle_right_panel)
        # self.plotter_layout.addWidget(self.collapse_right_button)

        self.showMaximized()
        print('Finished initializing')

        self.file_name_changed.connect(self.update_header)

    @pyqtSlot(str)
    def update_header(self, file_name):
        self.heading.setText(f"Viewing: {file_name}")

    def generate_checkboxes(self, components, level):
        for comp in components:
            checkbox = QCheckBox(comp['name'])
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(lambda state, comp=comp: self.toggle_visibility(state, comp))
            self.checkboxes_layout.addWidget(checkbox)
            # Indent based on the level
            checkbox.setStyleSheet(f"padding-left: {20 * level}px")
            self.checkbox_mapping[comp['name']] = checkbox
            # Recursively add children
            if 'children' in comp and comp['children']:
                self.generate_checkboxes(comp['children'], level + 1)
    

    def toggle_visibility(self, state, comp):
        try:
            visibility = state == Qt.Checked
            if comp['actor']:
                comp['actor'].SetVisibility(visibility)
            # Recursively set visibility for children
            if 'children' in comp and comp['children']:
                for child in comp['children']:
                    self.set_visibility_recursive(child, visibility)
        except Exception as e:
            print(e)
    

    def set_visibility_recursive(self, comp, visibility):
        if comp['actor']:
            comp['actor'].SetVisibility(visibility)
        self.checkbox_mapping[comp['name']].setChecked(visibility)
        if 'children' in comp and comp['children']:
            for child in comp['children']:
                self.set_visibility_recursive(child, visibility)


    def add_object_panel(self):
        # Create a control panel with checkboxes
        self.object_panel = QWidget()
        self.object_layout = QVBoxLayout(self.object_panel)

        # Add a heading
        heading = QLabel('Components List')
        heading_font = QFont()
        heading_font.setPointSize(14)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        self.object_layout.addWidget(heading)

        # Create a scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        # Create a widget to contain the checkboxes
        self.checkboxes_widget = QWidget()
        self.checkboxes_layout = QVBoxLayout(self.checkboxes_widget)
        self.checkboxes_layout.setAlignment(Qt.AlignTop)  # Ensure checkboxes stay at the top

        # Add checkboxes to the layout
        # self.trajectories_checkbox = QCheckBox('Show trajectories')
        # self.trajectories_checkbox.setChecked(self.viewer.visible[0])
        # self.trajectories_checkbox.stateChanged.connect(self.toggle_tracks)
        # self.checkboxes_layout.addWidget(self.trajectories_checkbox)

        # self.step_markers_checkbox = QCheckBox('Show step markers')
        # self.step_markers_checkbox.setChecked(self.viewer.visible[1])
        # self.step_markers_checkbox.stateChanged.connect(self.toggle_step_markers)
        # self.checkboxes_layout.addWidget(self.step_markers_checkbox)

        # Set the widget for the scroll area
        self.scroll_area.setWidget(self.checkboxes_widget)

        # Add the scroll area to the object_layout
        self.object_layout.addWidget(self.scroll_area)



    def add_viewer_panel(self):
        pass


    def add_control_panel(self):
        # Create a control panel with checkboxes
        self.control_panel = QWidget()
        self.control_layout = QVBoxLayout(self.control_panel)

        # Add a heading
        heading = QLabel('Viewing Options')
        heading_font = QFont()
        heading_font.setPointSize(14)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        self.control_layout.addWidget(heading)

        # self.background_checkbox = QCheckBox('Show background')
        # self.background_checkbox.setChecked(self.viewer.bkg_on)
        # self.background_checkbox.stateChanged.connect(self.toggle_background)
        # self.control_layout.addWidget(self.background_checkbox)

        # # Nested layout for the color picker button
        # self.color_layout = QHBoxLayout()
        # self.color_button_1 = QPushButton('Color 1')
        # self.color_button_1.setFixedWidth(100)
        # self.color_button_1.setEnabled(self.background_checkbox.isChecked())
        # self.color_button_1.clicked.connect(lambda: self.open_color_picker(0))
        # self.color_layout.addWidget(self.color_button_1, alignment=Qt.AlignLeft)

        # self.gradient_checkbox = QCheckBox('Show gradient')
        # self.gradient_checkbox.setChecked(True)
        # self.gradient_checkbox.stateChanged.connect(self.toggle_gradient)
        # self.color_layout.addWidget(self.gradient_checkbox, alignment=Qt.AlignLeft)

        # self.color_button_2 = QPushButton('Color 2')
        # self.color_button_2.setFixedWidth(100)
        # self.color_button_2.setEnabled(self.background_checkbox.isChecked())
        # self.color_button_2.clicked.connect(lambda: self.open_color_picker(1))
        # self.color_layout.addWidget(self.color_button_2, alignment=Qt.AlignLeft)

        # self.color_button_3 = QPushButton('Reset')
        # self.color_button_3.setFixedWidth(100)
        # self.color_button_3.clicked.connect(lambda: self.open_color_picker(2))
        # self.color_layout.addWidget(self.color_button_3, alignment=Qt.AlignLeft)
        # self.color_layout.setSpacing(0)
        # self.control_layout.addLayout(self.color_layout)

        
        # # Add a label to display the selected color
        # self.color_label = QLabel('Selected Color: None')
        # self.control_layout.addWidget(self.color_label)

        heading = QLabel('Console Output')
        heading_font = QFont()
        heading_font.setPointSize(14)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        self.control_layout.addWidget(heading)

        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)  # Make it read-only
        # self.terminal.setFont(QFont('DejaVu Sans Mono', 12))  # Set monospace font

        # Set terminal-like colors using Qt API
        # self.terminal.setTextInteractionFlags(Qt.TextEditorInteraction)
        # self.terminal.setTextInteractionFlags(Qt.NoTextInteraction)

        self.control_layout.addWidget(self.terminal)
        # Redirect stdout and stderr to the log_output text edit
        sys.stdout = OutputRedirect(self.terminal)
        sys.stderr = OutputRedirect(self.terminal)


        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.control_layout.addWidget(self.progress_bar)


    def add_dropdown(self):
        # Add a dropdown menu for loading files
        dropdown_label = QLabel("Load File:")
        self.control_layout.addWidget(dropdown_label)
        load_button = QPushButton("Open File")
        load_button.clicked.connect(lambda: self.open_file_dialog())
        self.control_layout.addWidget(load_button)


    def toggle_gradient(self):
        self.viewer.gradient = not self.viewer.gradient
        self.viewer.set_background_color()


    def add_menu_bar(self):
        # Create the menu bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu('File')
        db_action = file_menu.addAction("Open File")
        db_action.setStatusTip("Select a file to use as a database")
        db_action.triggered.connect(self.open_file_dialog)

        edit_menu = menubar.addMenu('Edit')
        edit_action = edit_menu.addAction('Preferences')
        edit_action.triggered.connect(self.open_preferences)
        edit_action2 = edit_menu.addAction('Clear Console')
        edit_action2.triggered.connect(self.terminal.clear)
        edit_action3 = edit_menu.addAction('Copy Console')
        edit_action3.triggered.connect(self.terminal.selectAll)
        edit_action3.triggered.connect(self.terminal.copy)

        view_menu = menubar.addMenu('View')
        view_action = view_menu.addAction('Enter Fullscreen')
        view_action.triggered.connect(self.showFullScreen)

        window_menu = menubar.addMenu('Window')
        window_action = window_menu.addAction('Close')
        window_action.triggered.connect(self.close)

        help_menu = menubar.addMenu('Help')
        help_action = help_menu.addAction('License')
        help_action.triggered.connect(self.show_license)


    def toggle_left_panel(self):
        if self.object_panel.isVisible():
            self.object_panel.hide()
            self.collapse_left_button.setText('>')
        else:
            self.object_panel.show()
            self.collapse_left_button.setText('<')


    def toggle_right_panel(self):
        if self.control_panel.isVisible():
            self.control_panel.hide()
            self.collapse_right_button.setText('<')
        else:
            self.control_panel.show()
            self.collapse_right_button.setText('>')


    def show_license(self):
        with open('LICENSE') as f:
            license_text = f.read().replace('\n\n', '<>').replace('\n', ' ').replace('<>', '\n\n')
        print('\nLICENSE:')
        print('--------\n')
        print(license_text)


    def open_preferences(self):
        print('Opening preferences')
        

    def add_toolbar(self):
        # Create a toolbar
        self.toolbar = QToolBar('Main Toolbar')
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.setMovable(False)

        # Add actions to the toolbar
        open_action = QAction('Open', self)
        # self.set_action_font(open_action, 14)
        font = QFont()
        font.setPointSize(14)
        open_action.setFont(font)
        open_action.triggered.connect(self.open_file_dialog)
        self.toolbar.addAction(open_action)

        # Add more actions to the toolbar as needed
        # Example: Add a separator
        # self.toolbar.addSeparator()

        save_action = QAction('Save', self)
        font = QFont()
        font.setPointSize(14)
        save_action.setFont(font)
        save_action.triggered.connect(self.save_file)
        self.toolbar.addAction(save_action)


    # Function to open a file dialog and load the selected file
    def open_file_dialog(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(None, "Open File", "", "All Files (*);;VRML Files (*.wrl);;GEV Files (*.gev)", options=options)
        if file_path:
            self.progress_bar.setValue(0)
            try:
                self.current_file = file_path
                try:
                    self.file_name_changed.emit(self.current_file)
                except Exception as e:
                    print(e)
                self.worker = Worker(self.viewer.load_files, filename=file_path, off_screen=True)
                self.worker.max_range.connect(self.set_progress_range)
                # self.worker.progress.connect(lambda: self.update_progress(self.worker.progress_obj.value))
                self.worker.finished.connect(self.on_task_finished)
                self.worker.start()
            except Exception as e:
                print(e)


    def open_color_picker(self, button):
        if button==2:
            self.viewer.bkg_colors = ['lightskyblue', 'midnightblue']
        else:
            color = QColorDialog.getColor()
            if color.isValid():
                self.viewer.bkg_colors[button] = color.getRgbF()[:3]
        self.viewer.set_background_color()


    def set_progress_range(self, value):
        self.progress_bar.setRange(0, value)


    def update_progress(self, value):
        self.progress_bar.setValue(value)

    
    def on_task_finished(self):
        self.viewer.create_plotter()
        self.generate_checkboxes(self.viewer.components, 0)
        

    def open_file(self):
        print('opening file')


    def save_file(self):
        print('saving file')


    def close(self):
        print('closing application')


    def toggle_tracks(self):
        print('Toggling tracks function called')
        try:
            self.viewer.toggle_tracks()
            self.viewer.plotter.update()
        except Exception as e:
            print(e)

    def toggle_step_markers(self):
        try:
            self.viewer.toggle_step_markers()
            self.viewer.plotter.update()
        except Exception as e:
            print(e)

    def toggle_background(self):
        try:
            self.viewer.toggle_background()
            self.viewer.plotter.update()
        except Exception as e:
            print(e)



def launch_app():
    app = QApplication([])
    window = Window()
    window.show()
    sys.exit(app.exec_())
