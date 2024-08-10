import sys
import io
import time
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
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QProgressBar
from PyQt5.QtWidgets import QColorDialog
from PyQt5.QtWidgets import QAction
from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QToolBar
from PyQt5.QtWidgets import QToolButton
from PyQt5.QtWidgets import QGroupBox
from PyQt5.QtWidgets import QScrollArea
from PyQt5.QtWidgets import QDockWidget
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QPalette
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QThread
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer
from geviewer.geviewer import GeViewer
from pyvistaqt import MainWindow
import pyvista as pv


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
        self.figure_size = [1920, 1440]

        self.splitter = QSplitter(Qt.Horizontal)

        self.viewer_panel = QWidget()
        self.viewer_panel.setMinimumWidth(500)
        self.viewer_panel.setMinimumHeight(500)
        self.viewer_layout = QVBoxLayout(self.viewer_panel)
        # Add a heading
        self.heading = QLabel('Viewing: ' + self.current_file)
        self.heading_font = QFont()
        self.heading_font.setPointSize(14)
        self.heading_font.setBold(True)
        self.heading.setFont(self.heading_font)
        self.viewer_layout.addWidget(self.heading)
        self.viewer = GeViewer(self.viewer_panel)
        self.plotter = self.viewer.plotter
        self.add_key_events()

        # self.viewer_layout.setContentsMargins(0, 0, 0, 0)

        self.add_object_panel()
        self.add_control_panel()
        # self.add_dropdown()
        self.add_menu_bar()

        self.splitter.addWidget(self.object_panel)
        self.splitter.addWidget(self.viewer_panel)
        self.splitter.addWidget(self.control_panel)

        # Add the splitter to the layout
        self.main_layout.addWidget(self.splitter)

        # Collapsible Buttons
        # self.collapse_left_button = QToolButton()
        # self.collapse_left_button.setText('<')
        # self.collapse_left_button.clicked.connect(self.toggle_left_panel)
        # self.viewer_layout.addWidget(self.collapse_left_button)

        self.viewer_layout.addWidget(self.plotter.interactor)

        self.showMaximized()
        print('Finished initializing')

        self.file_name_changed.connect(self.update_header)

    @pyqtSlot(str)
    def update_header(self, file_name):
        self.heading.setText(f"Viewing: {file_name}")

    def generate_checkboxes(self, components, level):
        for comp in components:
            if comp['id'] not in self.checkbox_mapping:
                checkbox = QCheckBox(comp['name'])
                checkbox.setChecked(True)
                checkbox.stateChanged.connect(lambda state, comp=comp: self.toggle_visibility(state, comp))
                self.checkboxes_layout.addWidget(checkbox)
                # Indent based on the level
                checkbox.setStyleSheet(f"padding-left: {20 * level}px")
                self.checkbox_mapping[comp['id']] = checkbox
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
        self.checkbox_mapping[comp['id']].setChecked(visibility)
        if 'children' in comp and comp['children']:
            for child in comp['children']:
                self.set_visibility_recursive(child, visibility)


    def add_object_panel(self):
        # Create a control panel with checkboxes
        # self.object_panel = QDockWidget("Panel", self)
        # self.object_panel.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

        self.object_panel = QWidget()
        self.object_panel.setMinimumWidth(250)
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

        # Set the widget for the scroll area
        self.scroll_area.setWidget(self.checkboxes_widget)

        # Add the scroll area to the object_layout
        self.object_layout.addWidget(self.scroll_area)



    def add_viewer_panel(self):
        pass


    def add_control_panel(self):
        # Create a control panel with checkboxes
        self.control_panel = QWidget()
        self.control_panel.setMinimumWidth(250)
        self.control_layout = QVBoxLayout(self.control_panel)

        # Add a heading
        heading = QLabel('Camera Options')
        heading_font = QFont()
        heading_font.setPointSize(14)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        self.control_layout.addWidget(heading)

        # Create the text box to display the camera position
        self.camera_position_layout = QHBoxLayout()
        self.camera_position_label = QLabel('Position (x, y, z):')
        self.camera_position_text = QLineEdit()
        self.camera_position_text.setReadOnly(False)
        self.camera_position_text.editingFinished.connect(self.handle_camera_position_change)
        self.camera_position_layout.addWidget(self.camera_position_label)
        self.camera_position_layout.addWidget(self.camera_position_text)
        self.control_layout.addLayout(self.camera_position_layout)

        self.camera_focal_layout = QHBoxLayout()
        self.camera_focal_label = QLabel('Focal Point (x, y, z):')
        self.camera_focal_text = QLineEdit()
        self.camera_focal_text.setReadOnly(False)
        self.camera_focal_text.editingFinished.connect(self.handle_camera_focal_change)
        self.camera_focal_layout.addWidget(self.camera_focal_label)
        self.camera_focal_layout.addWidget(self.camera_focal_text)
        self.control_layout.addLayout(self.camera_focal_layout)

        self.camera_up_layout = QHBoxLayout()
        self.camera_up_label = QLabel('Up Vector (x, y, z):')
        self.camera_up_text = QLineEdit()
        self.camera_up_text.setReadOnly(False)
        self.camera_up_text.editingFinished.connect(self.handle_camera_up_change)
        self.camera_up_layout.addWidget(self.camera_up_label)
        self.camera_up_layout.addWidget(self.camera_up_text)
        self.control_layout.addLayout(self.camera_up_layout)

        figure_heading = QLabel('Figure Options')
        figure_heading_font = QFont()
        figure_heading_font.setPointSize(14)
        figure_heading_font.setBold(True)
        figure_heading.setFont(figure_heading_font)
        self.control_layout.addWidget(figure_heading)

        self.figure_size_layout = QHBoxLayout()
        self.figure_size_label = QLabel('Size [px] (width, height):')
        self.figure_size_text = QLineEdit()
        self.figure_size_text.setText('{}, {}'.format(*self.figure_size))
        self.figure_size_text.setReadOnly(False)
        self.figure_size_text.editingFinished.connect(self.handle_figure_size_change)
        self.figure_size_layout.addWidget(self.figure_size_label)
        self.figure_size_layout.addWidget(self.figure_size_text)
        self.control_layout.addLayout(self.figure_size_layout)

        # Create a button
        self.save_button = QPushButton('Export Figure', self)
        self.save_button.clicked.connect(self.save_file_dialog)
        
        # Add the button to the layout
        self.control_layout.addWidget(self.save_button)

        # Timer to delay updates
        self.update_timer = QTimer()
        self.update_timer.setInterval(200)  # Update after 500ms of inactivity
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.update_view_params)

        # Store the last known camera position
        self.last_camera_position = None
        self.last_figure_size = None

        # Start the event loop to monitor the camera position
        self.monitor_camera_position()

        self.add_toolbar()

        # self.camera_position_text.visibilityChanged = self.update_menu_action
        # self.control_panel.showEvent = self.panel_shown

        heading = QLabel('Console')
        heading_font = QFont()
        heading_font.setPointSize(14)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        self.control_layout.addWidget(heading)

        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)  # Make it read-only
        self.terminal.setLineWrapMode(QTextEdit.NoWrap)
        self.terminal.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
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

    def update_view_params(self):
        self.update_camera_position()


    def handle_camera_position_change(self):
        # Validate and set the new camera position
        new_position = self.camera_position_text.text()
        if self.validate_camera_position(new_position):
            self.set_camera_position(new_position)
            self.clear_position_error_state()
        else:
            self.set_position_error_state()

    def handle_camera_focal_change(self):
        # Validate and set the new camera focal point
        new_focal = self.camera_focal_text.text()
        if self.validate_camera_focal(new_focal):
            self.set_camera_focal(new_focal)
            self.clear_focal_error_state()
        else:
            self.set_focal_error_state()

    def handle_camera_up_change(self):
        # Validate and set the new camera up vector
        new_up = self.camera_up_text.text()
        if self.validate_camera_up(new_up):
            self.set_camera_up(new_up)
            self.clear_up_error_state()
        else:
            self.set_up_error_state()

    def handle_figure_size_change(self):
        # Set the window size
        new_size = self.figure_size_text.text()
        if self.validate_figure_size(new_size):
            self.set_figure_size(new_size)
            self.clear_window_error_state()
        else:
            self.set_window_error_state()

    def validate_camera_position(self, position):
        # Validate the camera position
        try:
            position = [float(x) for x in position.split(',')]
            if len(position) != 3:
                raise ValueError('Invalid camera position')
            return True
        except ValueError:
            print('Invalid camera position. Please enter three comma-separated floats.')
            return False
        

    def validate_camera_focal(self, focal_point):
        # Validate the camera focal point
        try:
            focal_point = [float(x) for x in focal_point.split(',')]
            if len(focal_point) != 3:
                raise ValueError('Invalid camera focal point')
            return True
        except ValueError:
            print('Invalid camera focal point. Please enter three comma-separated floats.')
            return False
        
    def validate_camera_up(self, up_vector):
        # Validate the camera up vector
        try:
            up_vector = [float(x) for x in up_vector.split(',')]
            if len(up_vector) != 3:
                raise ValueError('Invalid camera up vector')
            return True
        except ValueError:
            print('Invalid camera up vector. Please enter three comma-separated floats.')
            return False
        
    def validate_figure_size(self, figure_size):
        # Validate the window size
        try:
            figure_size = [int(x) for x in figure_size.split(',')]
            if len(figure_size) != 2:
                raise ValueError('Invalid window size')
            return True
        except ValueError:
            print('Invalid window size. Please enter two comma-separated integers.')
            return False

    def set_camera_position(self, position):
        # Set the camera position
        position = [float(x) for x in position.split(',')]
        self.plotter.camera.position = position
        self.plotter.update()

    def set_camera_focal(self, focal_point):
        # Set the camera focal point
        focal_point = [float(x) for x in focal_point.split(',')]
        self.plotter.camera.focal_point = focal_point
        self.plotter.update()

    def set_camera_up(self, up_vector):
        # Set the camera up vector
        up_vector = [float(x) for x in up_vector.split(',')]
        self.plotter.camera.up = up_vector
        self.plotter.update()

    def set_figure_size(self, figure_size):
        # Set the window size
        figure_size = [int(x) for x in figure_size.split(',')]
        try:
            self.figure_size = figure_size
        except Exception as e:
            print(e)


    def clear_position_error_state(self):
        # Reset the background color of the text box
        self.camera_position_text.setPalette(QApplication.palette())

    def clear_focal_error_state(self):
        # Reset the background color of the text box
        self.camera_focal_text.setPalette(QApplication.palette())

    def clear_up_error_state(self):
        # Reset the background color of the text box
        self.camera_up_text.setPalette(QApplication.palette())


    def clear_window_error_state(self):
        # Reset the background color of the text box
        self.figure_size_text.setPalette(QApplication.palette())

    def set_position_error_state(self):
        # Set the background color of the text box to red
        palette = self.camera_position_text.palette()
        palette.setColor(QPalette.Base, QColor(255, 192, 192))  # Light red color
        self.camera_position_text.setPalette(palette)

    def set_focal_error_state(self):
        # Set the background color of the text box to red
        palette = self.camera_focal_text.palette()
        palette.setColor(QPalette.Base, QColor(255, 192, 192))
        self.camera_focal_text.setPalette(palette)


    def set_up_error_state(self):
        # Set the background color of the text box to red
        palette = self.camera_up_text.palette()
        palette.setColor(QPalette.Base, QColor(255, 192, 192))
        self.camera_up_text.setPalette(palette)

    def set_window_error_state(self):
        # Set the background color of the text box to red
        palette = self.figure_size_text.palette()
        palette.setColor(QPalette.Base, QColor(255, 192, 192))
        self.figure_size_text.setPalette(palette)


    def toggle_panel_visibility(self, checked):
        if checked:
            self.control_panel.show()
        else:
            self.control_panel.hide()

    def update_menu_action(self, visible):
        self.show_controls_action.setChecked(visible)


    def monitor_camera_position(self):
        camera_position = self.plotter.camera_position
        if camera_position != self.last_camera_position:
            self.last_camera_position = camera_position
            self.update_timer.start()
        QTimer.singleShot(100, self.monitor_camera_position)


    def update_camera_position(self):
        camera_pos = self.plotter.camera_position
        self.camera_position_text.setText('{:.3f}, {:.3f}, {:.3f}'.format(*camera_pos[0]))
        self.camera_focal_text.setText('{:.3f}, {:.3f}, {:.3f}'.format(*camera_pos[1]))
        self.camera_up_text.setText('{:.3f}, {:.3f}, {:.3f}'.format(*camera_pos[2]))
        self.clear_position_error_state()
        self.clear_focal_error_state()
        self.clear_up_error_state()


    def toggle_gradient(self):
        self.viewer.gradient = not self.viewer.gradient
        self.viewer.set_background_color()


    def add_menu_bar(self):
        # Create the menu bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu('File')
        open_action = file_menu.addAction('Open File...')
        open_action.triggered.connect(self.open_file_dialog)
        open_action.setShortcut(QKeySequence.Open)
        save_action = file_menu.addAction('Save As...')
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_file)
        close_window_action = file_menu.addAction('Close Window')
        close_window_action.triggered.connect(self.close)
        close_window_action.setShortcut(QKeySequence.Close)

        edit_menu = menubar.addMenu('Edit')
        clear_console_action = edit_menu.addAction('Clear Console')
        clear_console_action.triggered.connect(self.terminal.clear)
        copy_console_action = edit_menu.addAction('Copy Console')
        copy_console_action.triggered.connect(self.terminal.selectAll)
        copy_console_action.triggered.connect(self.terminal.copy)
        clear_action = edit_menu.addAction('Clear Meshes')
        clear_action.triggered.connect(self.clear_meshes)


        view_menu = menubar.addMenu('View')

        # self.collapse_right_button = QToolButton()
        # self.collapse_right_button.setText('>')
        show_components_action = QAction('Show Components Panel', self, checkable=True)
        show_components_action.setChecked(True)
        show_components_action.triggered.connect(self.toggle_left_panel)
        view_menu.addAction(show_components_action)

        self.show_controls_action = QAction('Show Control Panel', self, checkable=True)
        self.show_controls_action.setChecked(True)
        self.show_controls_action.triggered.connect(self.toggle_right_panel)
        view_menu.addAction(self.show_controls_action)

        show_background_action = QAction('Show Background', self, checkable=True)
        show_background_action.setChecked(True)
        show_background_action.triggered.connect(self.toggle_background)
        view_menu.addAction(show_background_action)

        gradient_action = QAction('Show Gradient', self, checkable=True)
        gradient_action.setChecked(True)
        gradient_action.triggered.connect(self.toggle_gradient)
        view_menu.addAction(gradient_action)

        color_menu = QMenu('Background Colors', self)

        # Create actions for the submenu
        color_action_1 = QAction('Set Primary Color...', self)
        color_action_2 = QAction('Set Secondary Color...', self)

        # Connect actions to slots
        color_action_1.triggered.connect(lambda: self.open_color_picker(0))
        color_action_2.triggered.connect(lambda: self.open_color_picker(1))

        # Add actions to the submenu
        color_menu.addAction(color_action_1)
        color_menu.addAction(color_action_2)

        view_menu.addMenu(color_menu)

        reset_background_action = QAction('Reset Background', self)
        reset_background_action.triggered.connect(lambda: self.open_color_picker(2))
        view_menu.addAction(reset_background_action)

        # self.collapse_right_button.clicked.connect(self.toggle_right_panel)
        # self.viewer_layout.addWidget(self.collapse_right_button)

        window_menu = menubar.addMenu('Window')
        window_action = window_menu.addAction('Close')
        window_action.triggered.connect(self.close)

        help_menu = menubar.addMenu('Help')
        help_action = help_menu.addAction('License')
        help_action.triggered.connect(self.show_license)


    def toggle_left_panel(self):
        if self.object_panel.isVisible():
            self.object_panel.hide()
        else:
            self.object_panel.show()

    def add_key_events(self):
        """This is the simplest way to have the buttons synchronize
        with whatever key inputs the user provides.
        """
        self.plotter.add_key_event('w', lambda: self.synchronize_toolbar(True))
        self.plotter.add_key_event('s', lambda: self.synchronize_toolbar(False))


    def synchronize_toolbar(self, wireframe=True):
        self.viewer.wireframe = wireframe
        self.update_wireframe_button()

    
    def clear_meshes(self):
        for actor in list(self.plotter.renderer.actors.values()):
            self.plotter.remove_actor(actor)
        self.checkbox_mapping = {}
        while self.checkboxes_layout.count() > 0:
            item = self.checkboxes_layout.takeAt(0)  # Take the first item
            item.widget().deleteLater()
        # this should be a GeViewer method
        self.viewer.components = []
        self.viewer.plotted = []


    def toggle_right_panel(self):
        if self.control_panel.isVisible():
            self.control_panel.hide()
        else:
            self.control_panel.show()


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
        self.viewer_layout.addWidget(self.toolbar)
        # self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.setMovable(True)

        self.toolbar.setStyleSheet(
            "QToolButton {"
            "    min-width: 70px;"  # Set the minimum width
            "    max-width: 70px;"  # Set the maximum width
            "}"
        )

        font = QFont()
        font.setPointSize(14)
        # Add actions to the toolbar

        self.wireframe_action = QAction('Wireframe', self)
        # self.wireframe_action.setFixedWidth(100)
        self.wireframe_action.setFont(font)
        self.wireframe_action.triggered.connect(self.toggle_wireframe)
        self.toolbar.addAction(self.wireframe_action)
        self.toolbar.addSeparator()

        isometric_action = QAction('Isometric', self)
        isometric_action.setFont(font)
        isometric_action.triggered.connect(self.plotter.view_isometric)
        self.toolbar.addAction(isometric_action)
        self.toolbar.addSeparator()

        top_action = QAction('Top', self)
        top_action.setFont(font)
        top_action.triggered.connect(self.plotter.view_xy)
        self.toolbar.addAction(top_action)
        self.toolbar.addSeparator()

        bottom_action = QAction('Bottom', self)
        bottom_action.setFont(font)
        bottom_action.triggered.connect(lambda: self.plotter.view_xy(negative=True))
        self.toolbar.addAction(bottom_action)
        self.toolbar.addSeparator()

        front_action = QAction('Front', self)
        front_action.setFont(font)
        front_action.triggered.connect(self.plotter.view_yz)
        self.toolbar.addAction(front_action)
        self.toolbar.addSeparator()

        back_action = QAction('Back', self)
        back_action.setFont(font)
        back_action.triggered.connect(lambda: self.plotter.view_yz(negative=True))
        self.toolbar.addAction(back_action)
        self.toolbar.addSeparator()

        left_action = QAction('Left', self)
        left_action.setFont(font)
        left_action.triggered.connect(self.plotter.view_xz)
        self.toolbar.addAction(left_action)
        self.toolbar.addSeparator()

        right_action = QAction('Right', self)
        right_action.setFont(font)
        right_action.triggered.connect(lambda: self.plotter.view_xz(negative=True))
        self.toolbar.addAction(right_action)
        self.toolbar.addSeparator()

        self.parallel_action = QAction('Parallel', self)
        self.parallel_action.setFont(font)
        self.parallel_action.triggered.connect(self.toggle_parallel)
        self.toolbar.addAction(self.parallel_action)
        self.toolbar.addSeparator()


        # Add a separator

        # isometric_action = QAction('Isometric', self)
        # isometric_action.setFont(font)
        # isometric_action.triggered.connect(self.plotter.view_isometric)
        # self.toolbar.addAction(isometric_action)

        # Add more actions to the toolbar as needed
        # Example: Add a separator
        # self.toolbar.addSeparator()

    def toggle_parallel(self):
        try:
            self.viewer.toggle_parallel_projection()
            self.parallel_action.setText('Perspective' if self.viewer.parallel else 'Parallel')
        except Exception as e:
            print(e)

    def toggle_wireframe(self):
        self.viewer.toggle_wireframe()
        self.update_wireframe_button()


    def update_wireframe_button(self):
        self.wireframe_action.setText('Solid' if self.viewer.wireframe else 'Wireframe')


    # Function to open a file dialog and load the selected file
    def open_file_dialog(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(None, 'Open File', '', \
                                                   'All Supported Files (*.wrl *.heprep *.gev);;' +\
                                                   'VRML Files (*.wrl);;HepRep Files (*.heprep);;' +\
                                                   'GEV Files (*.gev)', options=options)
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


    def save_file_dialog(self):
        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog
        file_types = 'Supported File Types(*.png *.svg *.eps *.ps *.pdf *.tex);; '\
                     + 'PNG (*.png);;SVG (*.svg);;EPS (*.eps);;PS (*.ps);;PDF (*.pdf);;TEX (*.tex)'
        file_name, _ = QFileDialog.getSaveFileName(self, 'Save Figure', '', file_types, options=options)
        
        if file_name:
            print(f'Selected file: {file_name}')
            print(self.figure_size)
            try:
                self.save_figure(file_name.split('.')[0]+'a.png', *self.figure_size)
                self.plotter.screenshot(file_name)
            except Exception as e:
                print(e)
                
    def save_figure(self, file_name, width, height):
        try:
            # Create an off-screen plotter with the desired size
            off_screen_plotter = pv.Plotter(off_screen=True, window_size=[width, height])
            off_screen_plotter.set_background(*self.viewer.bkg_colors)
            
            # Copy the mesh and camera settings to the off-screen plotter
            for actor in self.plotter.renderer.actors.values():
                off_screen_plotter.add_actor(actor)
            
            # Copy camera position
            off_screen_plotter.camera_position = self.plotter.camera_position


            off_screen_plotter.enable_anti_aliasing('msaa', multi_samples=16)
            if file_name.endswith('.png'):
                off_screen_plotter.screenshot(file_name)
            else:
                off_screen_plotter.save_graphic(file_name, title='GeViewer Figure')

            del off_screen_plotter
            print(f"Saved screenshot to {file_name}")
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
