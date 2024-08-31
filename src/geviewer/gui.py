import sys
import traceback
import webbrowser
import io
import re
from pathlib import Path
import time
import gc
from pyvistaqt import MainWindow

from PyQt6.QtCore import QDateTime, QThread, pyqtSignal, QEventLoop, QTimer

from PyQt6.QtWidgets import (
    QApplication, QVBoxLayout, QHBoxLayout, QPushButton, QWidget,
    QCheckBox, QSplitter, QFileDialog, QLabel, QTextEdit, QLineEdit,
    QColorDialog, QMenu, QToolBar, QSpinBox, QFrame, QScrollArea,
    QMessageBox, QGridLayout, QTabWidget, QGroupBox, QSpacerItem,
    QSizePolicy, QWidgetAction, QGraphicsOpacityEffect, QProgressBar
)
from PyQt6.QtGui import (
    QAction, QFont, QColor, QPalette, QDoubleValidator, QIntValidator,
    QKeySequence, QIcon, QTextCharFormat, QTextCursor, QFontDatabase
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer, QSize, QObject

from geviewer.viewer import GeViewer
import geviewer.utils as utils


class Application(QApplication):
    """A custom application class for the GeViewer application.
    """

    def __init__(self, *args, **kwargs):
        """Initializes the application.
        """
        super().__init__(*args, **kwargs)
        self.window = None

    def notify(self, receiver, event):
        """Handles unhandled exceptions.
        """
        try:
            return super().notify(receiver, event)
        except Exception as e:
            if self.window:
                self.window.global_exception_hook(type(e), e, e.__traceback__)
            return False


class Window(MainWindow):
    """A custom main window class for the GeViewer application.
    """
    #: Signal emitted when the file name changes
    #:
    #: :param str: The new file name
    file_name_changed = pyqtSignal(str)

    #: Signal emitted when the number of events changes
    #:
    #: :param int: The new number of events
    number_of_events = pyqtSignal(int)

    #: Signal emitted when a file is loaded
    file_loaded = pyqtSignal()

    def __init__(self):
        """Initializes the main window.
        """
        super().__init__()

        # initialize some class attributes
        self.default_title = 'GeViewer'
        self.current_file = []
        self.checkbox_mapping = {}
        self.events_list = []
        self.figure_size = [1920, 1440]
        self.worker_running = False
        self.success = True

        # create the main window
        self.setWindowTitle(self.default_title)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        splitter = QSplitter(Qt.Horizontal)

        # add panels and menu bar
        self.create_viewer_panel()
        self.create_control_panel()
        self.create_components_panel()
        self.add_menu_bar()

        # create a splitter and add the panels to it
        splitter.addWidget(self.components_panel)
        splitter.addWidget(self.viewer_panel)
        splitter.addWidget(self.control_panel)
        splitter.setChildrenCollapsible(False)
        splitter.setSizes([300, 800, 300])
        main_layout.addWidget(splitter)

        # other setup
        self.number_of_events.connect(self.update_event_total)
        self.file_name_changed.connect(self.update_title)
        self.print_to_console('Welcome to GeViewer!')
        updates = utils.check_for_updates()
        if updates:
            self.print_to_console(updates)
        self.resize_window()
        QApplication.instance().window = self


    def resize_window(self):
        """Resizes the window to fit the screen.
        """
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()

        if int(screen_geometry.width()) < 1920:
            self.showMaximized()
        else:
            self.resize(QSize(int(screen_geometry.width() * 0.8), \
                              int(screen_geometry.height() * 0.8)))
            self.center_on_screen(screen_geometry)


    def center_on_screen(self, screen_geometry):
        """Centers the window on the screen.

        :param screen_geometry: The geometry of the screen.
        :type screen_geometry: QRect
        """
        frame_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())


    def global_exception_hook(self, exctype, value, traceback_obj):
        """Global method to catch unhandled exceptions.
        """
        self.success = False
        error_message = ''.join(traceback.format_exception(exctype, value, traceback_obj))
        self.print_to_console('Error:\n' + error_message)


    def load_initial_files(self, files):
        """Loads initial files after the window has been shown.

        :param files: List of file paths to load
        :type files: list of str
        """

        for file in files:
            self.load_file(file)
            
            # wait for the file to be loaded completely
            loop = QEventLoop()
            self.file_loaded.connect(loop.quit)
            loop.exec()

    ##############################################################
    # Methods for creating the GUI
    ##############################################################

    def create_components_panel(self):
        """Adds the components panel to the main window.
        """
        # create a layout for the components panel
        self.components_panel = QWidget()
        ojbect_layout = QVBoxLayout(self.components_panel)

        # add a heading
        heading = QLabel('Components')
        tab_height = self.tab_widget.tabBar().height()
        heading.setFixedHeight(tab_height)
        heading.setAlignment(Qt.AlignVCenter)
        heading.setStyleSheet("padding-left: 5px;")
        ojbect_layout.addWidget(heading)

        # create the scroll area for the checkboxes
        components_area = QScrollArea()
        components_area.setWidgetResizable(True)

        # add temporary instructions
        instructions = 'Click "File > Open File..." to add components'
        self.load_instructions = QLabel(instructions)
        load_instructions_font = QFont()
        load_instructions_font.setPointSize(13)
        load_instructions_font.setItalic(True)
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.5)
        self.load_instructions.setGraphicsEffect(opacity_effect)
        self.load_instructions.setFont(load_instructions_font)
        self.load_instructions.setWordWrap(True)

        # create a widget to hold the checkboxes
        checkboxes_widget = QWidget()
        self.checkboxes_layout = QVBoxLayout(checkboxes_widget)
        self.checkboxes_layout.setAlignment(Qt.AlignTop)
        self.checkboxes_layout.addWidget(self.load_instructions)
        components_area.setWidget(checkboxes_widget)
        ojbect_layout.addWidget(components_area)


    def create_viewer_panel(self):
        """Adds the viewer panel to the main window.
        """
        # create a layout for the viewer panel
        self.viewer_panel = QWidget()
        self.viewer_layout = QVBoxLayout(self.viewer_panel)

        # create the viewer
        self.viewer = GeViewer(self.viewer_panel)
        self.plotter = self.viewer.plotter
        self.add_key_events()

        # add the toolbar
        self.add_toolbar()

        # add the plotter to the viewer layout
        self.viewer_layout.addWidget(self.plotter.interactor)


    def create_control_panel(self):
        """Adds the control panel to the main window.
        """
        # create a layout for the control panel
        self.control_panel = QWidget()
        control_layout = QVBoxLayout(self.control_panel)

        # add a heading for the console
        control_panel_heading = QLabel('Control Panel')
        control_panel_heading_font = QFont()
        control_panel_heading_font.setPointSize(14)
        control_panel_heading_font.setBold(True)
        control_panel_heading.setFont(control_panel_heading_font)

        # create a tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumWidth(250)
        self.tab_widget.setMinimumHeight(300)
        self.tab_widget.setMaximumHeight(350)

        # create tabs
        options_tab = QWidget()
        tools_tab = QWidget()
        self.options_layout = QVBoxLayout(options_tab)
        self.tools_layout = QVBoxLayout(tools_tab)
        self.tab_widget.addTab(options_tab, 'Options')
        self.tab_widget.addTab(tools_tab, 'Tools')
        control_layout.addWidget(self.tab_widget)

        # add components to tabs
        self.add_options_tab()
        self.add_tools_tab()

        # create the console
        console_layout = QVBoxLayout()
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        font.setPointSize(13)
        self.console.setFont(font)
        sys.stdout = ConsoleRedirect(self.console)
        sys.stderr = ConsoleRedirect(self.console)
        console_layout.addWidget(self.console)
        control_layout.addLayout(console_layout)

        # Add the progress bar
        self.progress_bar = ProgressBar()
        control_layout.addWidget(self.progress_bar)


    def add_options_tab(self):
        """Adds camera and figure options to the first tab."""
        grid_layout = QGridLayout()

        # camera options section
        heading = QLabel('Camera Options')
        heading_font = QFont()
        heading_font.setPointSize(14)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        grid_layout.addWidget(heading, 0, 0, 1, 2)

        self.camera_position_label = QLabel('Position:')
        self.camera_position_text = QLineEdit()
        self.camera_position_text.setReadOnly(False)
        self.camera_position_text.editingFinished.connect(self.handle_camera_position_change)
        self.camera_position_text.setToolTip('Enter the camera coordinates as three comma-separated numbers')
        grid_layout.addWidget(self.camera_position_label, 1, 0)
        grid_layout.addWidget(self.camera_position_text, 1, 1, 1, 1)

        self.camera_focal_label = QLabel('Focal point:')
        self.camera_focal_text = QLineEdit()
        self.camera_focal_text.setReadOnly(False)
        self.camera_focal_text.editingFinished.connect(self.handle_camera_focal_change)
        self.camera_focal_text.setToolTip('Enter the focal point coordinates as three comma-separated numbers')
        grid_layout.addWidget(self.camera_focal_label, 2, 0)
        grid_layout.addWidget(self.camera_focal_text, 2, 1, 1, 1)

        self.camera_up_label = QLabel('Up vector:')
        self.camera_up_text = QLineEdit()
        self.camera_up_text.setReadOnly(False)
        self.camera_up_text.editingFinished.connect(self.handle_camera_up_change)
        self.camera_up_text.setToolTip('Enter the up vector components as three comma-separated numbers')
        grid_layout.addWidget(self.camera_up_label, 3, 0)
        grid_layout.addWidget(self.camera_up_text, 3, 1, 1, 1)

        # event viewer section
        event_heading = QLabel('Event Viewer')
        event_heading_font = QFont()
        event_heading_font.setPointSize(14)
        event_heading_font.setBold(True)
        event_heading.setFont(event_heading_font)
        grid_layout.addWidget(event_heading, 4, 0, 1, 2)

        self.event_selection_label = QLabel('Show event:')
        self.event_selection_box = QSpinBox()
        self.event_selection_box.setRange(1, 1)
        self.event_selection_box.setValue(1)
        self.event_selection_box.setWrapping(True)
        self.event_selection_box.valueChanged.connect(lambda: self.show_single_event(self.event_selection_box.value()))
        grid_layout.addWidget(self.event_selection_label, 5, 0)
        grid_layout.addWidget(self.event_selection_box, 5, 1, 1, 1)

        # figure options section
        figure_heading = QLabel('Figure Options')
        figure_heading_font = QFont()
        figure_heading_font.setPointSize(14)
        figure_heading_font.setBold(True)
        figure_heading.setFont(figure_heading_font)
        grid_layout.addWidget(figure_heading, 6, 0, 1, 2)

        self.figure_size_label = QLabel('Figure size:')
        self.figure_size_text = QLineEdit()
        self.figure_size_text.setText('{}, {}'.format(*self.figure_size))
        self.figure_size_text.setReadOnly(False)
        self.figure_size_text.editingFinished.connect(self.handle_figure_size_change)
        self.figure_size_text.setToolTip('Enter the figure width and height in pixels as two comma-separated numbers')
        grid_layout.addWidget(self.figure_size_label, 7, 0)
        grid_layout.addWidget(self.figure_size_text, 7, 1, 1, 1)

        self.save_button = QPushButton('Export Figure', self)
        self.save_button.clicked.connect(self.export_figure_dialog)
        grid_layout.addWidget(self.save_button, 8, 0, 1, 2)

        self.options_layout.addLayout(grid_layout)


    def add_tools_tab(self):
        """Adds view and geometry options to the second tab."""
        grid_layout = QGridLayout()

        # overlap inspector section
        overlap_heading = QLabel('Overlap Inspector')
        overlap_heading_font = QFont()
        overlap_heading_font.setPointSize(14)
        overlap_heading_font.setBold(True)
        overlap_heading.setFont(overlap_heading_font)
        grid_layout.addWidget(overlap_heading, 0, 0, 1, 2)

        tolerance_label = QLabel('Tolerance:')
        tolerance_box = QLineEdit()
        double_validator = QDoubleValidator(1e-6, 1, 6)
        double_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        tolerance_box.setValidator(double_validator)
        tolerance_box.setText('0.001')
        tolerance_box.setToolTip('Enter the tolerance for overlap detection')
        grid_layout.addWidget(tolerance_label, 1, 0)
        grid_layout.addWidget(tolerance_box, 1, 1, 1, 1)

        samples_label = QLabel('Number of points:')
        samples_box = QLineEdit(self)
        int_validator = QIntValidator(1000, 10000000)
        samples_box.setValidator(int_validator)
        samples_box.setText('10000')
        samples_box.setToolTip('Enter the number of sample points for overlap detection')
        grid_layout.addWidget(samples_label, 2, 0)
        grid_layout.addWidget(samples_box, 2, 1, 1, 1)

        check_button = QPushButton('Find Overlaps')
        check_button.clicked.connect(lambda: self.check_geometry(tolerance_box.text(), samples_box.text()))
        clear_overlaps_button = QPushButton('Clear')
        clear_overlaps_button.clicked.connect(self.clear_overlaps)
        grid_layout.addWidget(check_button, 3, 0)
        grid_layout.addWidget(clear_overlaps_button, 3, 1, 1, 1)

        # measurement tool section
        measurement_heading = QLabel('Measurement Tool')
        measurement_heading_font = QFont()
        measurement_heading_font.setPointSize(14)
        measurement_heading_font.setBold(True)
        measurement_heading.setFont(measurement_heading_font)
        grid_layout.addWidget(measurement_heading, 4, 0, 1, 2)

        measure_text = QLabel('Measurement 1:')
        self.measurement_box = QLineEdit()
        self.measurement_box.setReadOnly(True)
        grid_layout.addWidget(measure_text, 5, 0)
        grid_layout.addWidget(self.measurement_box, 5, 1, 1, 1)

        measure_text_2 = QLabel('Measurement 2:')
        self.measurement_box_2 = QLineEdit()
        self.measurement_box_2.setReadOnly(True)
        grid_layout.addWidget(measure_text_2, 6, 0)
        grid_layout.addWidget(self.measurement_box_2, 6, 1, 1, 1)

        measure_text_3 = QLabel('Measurement 3:')
        self.measurement_box_3 = QLineEdit()
        self.measurement_box_3.setReadOnly(True)
        grid_layout.addWidget(measure_text_3, 7, 0)
        grid_layout.addWidget(self.measurement_box_3, 7, 1, 1, 1)

        measure_button = QPushButton('Add Measurement')
        measure_button.setMinimumWidth(130)
        measure_button.clicked.connect(self.measure_distance)
        clear_measurement_button = QPushButton('Clear')
        clear_measurement_button.clicked.connect(self.clear_measurement)
        grid_layout.addWidget(measure_button, 8, 0)
        grid_layout.addWidget(clear_measurement_button, 8, 1)

        # timer to update the camera settings when the view is changed
        self.update_timer = QTimer()
        self.update_timer.setInterval(200)
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.update_view_params)
        self.last_camera_position = None
        self.last_figure_size = None
        self.monitor_camera_position()

        self.tools_layout.addLayout(grid_layout)


    def add_toolbar(self):
        """Adds the toolbar to the main window.

        This method creates a QToolBar and populates it with various actions
        for controlling the viewer's display options and camera views. The
        toolbar includes actions for toggling wireframe mode, transparency,
        parallel projection, and setting different standard views (isometric,
        top, bottom, front, back).
        """
        self.toolbar = QToolBar('Main Toolbar')
        self.toolbar.setMovable(True)

        # text and button size
        toolbar_font = QFont()
        toolbar_font.setPointSize(12)
        action_width = 95
        self.toolbar.setFont(toolbar_font)

        # actions that change when clicked
        self.wireframe_action = QAction('Wireframe', self)
        self.wireframe_action.triggered.connect(self.toggle_wireframe)

        self.transparent_action = QAction('Transparent', self)
        self.transparent_action.triggered.connect(self.toggle_transparent)

        self.parallel_action = QAction('Parallel', self)
        self.parallel_action.triggered.connect(self.toggle_parallel)

        self.toolbar.addAction(self.wireframe_action)
        tool_button = self.toolbar.widgetForAction(self.wireframe_action)
        tool_button.setFixedWidth(action_width)
        self.toolbar.addAction(self.transparent_action)
        tool_button = self.toolbar.widgetForAction(self.transparent_action)
        tool_button.setFixedWidth(action_width)
        self.toolbar.addAction(self.parallel_action)
        tool_button = self.toolbar.widgetForAction(self.parallel_action)
        tool_button.setFixedWidth(action_width)

        # view actions that don't change when clicked
        view_actions = [
            ('Isometric', lambda: (self.print_to_console('Switching to isometric view.'), \
                                   self.plotter.view_isometric())),
            ('Top', lambda: (self.print_to_console('Switching to top view.'), \
                             self.plotter.view_xy())),
            ('Bottom', lambda: (self.print_to_console('Switching to bottom view.'), \
                                self.plotter.view_xy(negative=True))),
            ('Front', lambda: (self.print_to_console('Switching to front view.'), \
                               self.plotter.view_yz())),
            ('Back', lambda: (self.print_to_console('Switching to back view.'), \
                              self.plotter.view_yz(negative=True))),
            ('Left', lambda: (self.print_to_console('Switching to left view.'), \
                              self.plotter.view_xz())),
            ('Right', lambda: (self.print_to_console('Switching to right view.'), \
                               self.plotter.view_xz(negative=True)))
        ]

        for text, callback in view_actions:
            action = QAction(text, self)
            action.triggered.connect(callback)
            self.toolbar.addAction(action)
            tool_button = self.toolbar.widgetForAction(action)
            tool_button.setFixedWidth(75)

        self.viewer_layout.addWidget(self.toolbar)


    def add_menu_bar(self):
        """Adds the menu bar to the main window.

        This method creates and configures the main menu bar for the application.
        It adds the following menus:
        - File: Contains actions for opening files, saving, and closing the window.
        - Edit: Contains actions for clearing the console, copying console content, and clearing meshes.
        - View: Contains actions for toggling visibility of various panels and visual elements.
        - Window: Contains actions for closing the window.
        - Help: Contains actions for displaying the license information.

        The menu bar provides easy access to key functionality and settings of the application.
        """ 

        # create the menu bar
        menubar = self.menuBar()

        # create the file menu
        file_menu = menubar.addMenu('File')
        open_action = file_menu.addAction('Open File...')
        open_action.triggered.connect(self.open_file_dialog)
        open_action.setShortcut(QKeySequence.Open)
        save_action = file_menu.addAction('Save As...')
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_file_dialog)
        close_window_action = file_menu.addAction('Close Window')
        close_window_action.triggered.connect(self.close)
        close_window_action.setShortcut(QKeySequence.Close)

        # create the edit menu
        edit_menu = menubar.addMenu('Edit')
        copy_console_action = edit_menu.addAction('Copy Console')
        copy_console_action.triggered.connect(self.console.selectAll)
        copy_console_action.triggered.connect(self.console.copy)
        clear_console_action = edit_menu.addAction('Clear Console')
        clear_console_action.triggered.connect(self.console.clear)
        clear_action = edit_menu.addAction('Clear Viewer')
        clear_action.triggered.connect(self.clear_viewer)
        abort_action = edit_menu.addAction('Abort Process')
        abort_action.triggered.connect(self.abort_process)

        # create the view menu
        view_menu = menubar.addMenu('View')
        show_components_action = QAction('Show Components Panel', self, checkable=True)
        show_components_action.setChecked(True)
        show_components_action.triggered.connect(self.toggle_components_panel)
        view_menu.addAction(show_components_action)

        # create the show controls action
        self.show_controls_action = QAction('Show Control Panel', self, checkable=True)
        self.show_controls_action.setChecked(True)
        self.show_controls_action.triggered.connect(self.toggle_control_panel)
        view_menu.addAction(self.show_controls_action)

        # create the show background action
        show_background_action = QAction('Show Background', self, checkable=True)
        show_background_action.setChecked(True)
        show_background_action.triggered.connect(self.toggle_background)
        view_menu.addAction(show_background_action)

        # create the show gradient action
        gradient_action = QAction('Show Gradient', self, checkable=True)
        gradient_action.setChecked(True)
        gradient_action.triggered.connect(self.toggle_gradient)
        view_menu.addAction(gradient_action)

        # create the depth peeling action
        self.depth_peeling_action = QAction('Use Depth Peeling', self, checkable=True)
        self.depth_peeling_action.setChecked(False)
        self.depth_peeling_action.triggered.connect(self.toggle_depth_peeling)
        view_menu.addAction(self.depth_peeling_action)

        # create the background color menu
        color_menu = QMenu('Background Colors', self)
        color_action_1 = QAction('Set Primary Color...', self)
        color_action_2 = QAction('Set Secondary Color...', self)
        color_action_1.triggered.connect(lambda: self.open_color_picker(0))
        color_action_2.triggered.connect(lambda: self.open_color_picker(1))
        color_menu.addAction(color_action_1)
        color_menu.addAction(color_action_2)
        view_menu.addMenu(color_menu)

        # create the reset background action
        reset_background_action = QAction('Reset Background', self)
        reset_background_action.triggered.connect(lambda: self.open_color_picker(2))
        view_menu.addAction(reset_background_action)

        # create the window menu
        window_menu = menubar.addMenu('Window')
        maximize_action = window_menu.addAction('Maximize')
        maximize_action.triggered.connect(self.showMaximized)
        minimize_action = window_menu.addAction('Minimize')
        minimize_action.triggered.connect(self.showMinimized)
        restore_action = window_menu.addAction('Restore')
        restore_action.triggered.connect(self.showNormal)

        # create the help menu
        help_menu = menubar.addMenu('Help')
        license_action = help_menu.addAction('License')
        license_action.triggered.connect(self.show_license)
        update_action = help_menu.addAction('Check for Updates')
        update_action.triggered.connect(self.check_for_updates)
        documentation_action = help_menu.addAction('Documentation')
        documentation_action.triggered.connect(self.show_documentation)

    ##############################################################
    # Signals and slots
    ##############################################################
    
    @pyqtSlot(str)
    def update_title(self, filename):
        """Updates the title text to reflect the current file being viewed.

        This method updates the text of the window title to indicate the current file
        being viewed. If multiple files are being viewed, it will also show
        the number of additional files being viewed.

        :param filename: The name of the file being viewed.
        :type filename: str
        """
        if filename:
            self.current_file.append(filename)
            title = self.default_title + ' - ' + str(Path(self.current_file[0]).resolve()) \
                    + ['',' + {} more'.format(len(self.current_file) - 1)][len(self.current_file) > 1]
        else:
            title = self.default_title
        self.setWindowTitle(title)


    @pyqtSlot(int)
    def update_event_total(self, total):
        """Updates the event selection box to reflect the total number of events.

        This method updates the range of the event selection box to reflect the
        total number of events in the current file.

        :param total: The total number of events in the current file.
        :type total: int
        """
        self.event_selection_box.setRange(1, max(1, total))

    ##############################################################
    # Methods for the components panel
    ##############################################################

    def generate_checkboxes(self, components, level):
        """Generates checkboxes for the components in the current file.

        This method generates checkboxes for the components in the current file.
        It also sets up the connections for toggling visibility and updating
        the event selection box.

        :param components: The components to generate checkboxes for.
        :type components: list
        :param level: The level of the components to generate checkboxes for.
        :type level: int
        """
        self.checkboxes_layout.removeWidget(self.load_instructions)
        self.load_instructions.setParent(None)
        self.load_instructions.hide()
        for comp in components:
            if comp['id'] not in self.checkbox_mapping:
                checkbox = QCheckBox(comp['name'])
                checkbox.setCheckState(Qt.CheckState.Checked)
                checkbox.stateChanged.connect(lambda state, comp=comp: self.toggle_visibility(state, comp))
                self.checkboxes_layout.addWidget(checkbox)
                checkbox.setStyleSheet('padding-left: {}px'.format(20 * level))
                self.checkbox_mapping[comp['id']] = checkbox
                if comp['is_event'] and 'Event' in comp['name']:
                    self.events_list.append(comp['id'])
                if 'children' in comp and comp['children']:
                    self.generate_checkboxes(comp['children'], level + 1)
        self.number_of_events.emit(len(self.events_list))


    def toggle_visibility(self, state, comp):
        """Toggles the visibility of a component in the viewer.

        This method toggles the visibility of a component in the viewer by
        checking the corresponding checkbox and updating the visibility of the
        associated actors.

        :param state: The state of the checkbox to toggle.
        :type state: int
        :param comp: The component to toggle visibility for.
        :type comp: dict
        """
        visibility = state > 0
        if comp['has_actor']:
            self.viewer.actors[comp['id']].SetVisibility(visibility)
        if 'children' in comp and comp['children']:
            for child in comp['children']:
                self.set_visibility_recursive(child, visibility)
    

    def set_visibility_recursive(self, comp, visibility):
        """Sets the visibility of a component and all its children recursively.

        This method sets the visibility of a component and all its children
        recursively by checking the corresponding checkbox and updating the
        visibility of the associated actors.

        :param comp: The component to set visibility for.
        :type comp: dict
        :param visibility: The visibility to set for the component.
        :type visibility: bool
        """
        state = Qt.CheckState.Checked if visibility else Qt.CheckState.Unchecked
        if comp['has_actor']:
            self.viewer.actors[comp['id']].SetVisibility(visibility)
        self.checkbox_mapping[comp['id']].setCheckState(state)
        if 'children' in comp and comp['children']:
            for child in comp['children']:
                self.set_visibility_recursive(child, visibility)

    ##############################################################
    # Methods for updating the viewer
    ##############################################################

    def show_single_event(self, event_index):
        """Shows a single event in the viewer.

        This method shows a single event in the viewer by checking the
        corresponding checkbox and updating the visibility of the associated
        actors.

        :param event_index: The index of the event to show.
        :type event_index: int
        """
        self.print_to_console('Showing event {}.'.format(event_index))
        for i, event in enumerate(self.events_list):
            if i == event_index - 1:
                self.checkbox_mapping[event].setCheckState(Qt.CheckState.Checked)
            else:
                self.checkbox_mapping[event].setCheckState(Qt.CheckState.Unchecked)


    def toggle_parallel(self):
        """Toggles the parallel projection.

        This method toggles the parallel projection by setting the parallel
        attribute of the viewer to the opposite of its current value and
        updating the parallel button.
        """
        self.print_to_console('Turning parallel projection ' + ['on.','off.'][self.viewer.parallel])
        self.viewer.toggle_parallel_projection()
        self.parallel_action.setText('Perspective' if self.viewer.parallel else 'Parallel')


    def toggle_wireframe(self):
        """Toggles the wireframe.

        This method toggles the wireframe by setting the wireframe attribute
        of the viewer to the opposite of its current value and updating the
        wireframe button.
        """
        self.print_to_console('Switching to ' + ['wireframe', 'solid'][self.viewer.wireframe] + ' mode.')
        self.viewer.toggle_wireframe()
        self.update_wireframe_action()


    def toggle_transparent(self, print=True):
        """Toggles the transparency.

        This method toggles the transparency by setting the transparent attribute
        of the viewer to the opposite of its current value and updating the
        transparency button.
        """
        if print:
            self.print_to_console('Switching to ' + ['transparent', 'opaque'][self.viewer.transparent] + ' mode.')
        self.viewer.toggle_transparent()
        self.transparent_action.setText('Opaque' if self.viewer.transparent else 'Transparent')


    def update_wireframe_action(self):
        """Updates the wireframe button.

        This method updates the wireframe button by setting the text to 'Solid'
        if the wireframe is enabled, otherwise 'Wireframe'.
        """
        self.wireframe_action.setText('Solid' if self.viewer.wireframe else 'Wireframe')


    def add_key_events(self):
        """Adds key events to the plotter.

        This is the simplest way to have the buttons synchronize
        with whatever key inputs the user provides.
        """
        self.plotter.add_key_event('w', lambda: self.synchronize_toolbar(True))
        self.plotter.add_key_event('s', lambda: self.synchronize_toolbar(False))


    def synchronize_toolbar(self, wireframe=True):
        """Synchronizes the toolbar.

        This method synchronizes the toolbar by setting the wireframe attribute
        of the viewer to the opposite of its current value and updating the
        wireframe button.

        :param wireframe: The wireframe state to synchronize.
        :type wireframe: bool
        """
        self.viewer.wireframe = wireframe
        self.update_wireframe_action()

    ##############################################################
    # Methods for the options tab
    ##############################################################

    def set_camera_position(self, position):
        """Sets the camera position in the viewer.

        This method sets the camera position in the viewer by updating the
        camera's position attribute and triggering an update of the plotter.

        :param position: The new camera position.
        :type position: str
        """
        self.print_to_console('Setting camera position to ' + position + '.')
        position = [float(x) for x in position.split(',')]
        self.plotter.camera.position = position
        self.plotter.update()


    def set_camera_focal(self, focal_point):
        """Sets the camera focal point in the viewer.

        This method sets the camera focal point in the viewer by updating the
        camera's focal point attribute and triggering an update of the plotter.

        :param focal_point: The new camera focal point.
        :type focal_point: str
        """
        self.print_to_console('Setting camera focal point to ' + focal_point + '.')
        focal_point = [float(x) for x in focal_point.split(',')]
        self.plotter.camera.focal_point = focal_point
        self.plotter.update()


    def set_camera_up(self, up_vector):
        """Sets the camera up vector in the viewer.

        This method sets the camera up vector in the viewer by updating the
        camera's up vector attribute and triggering an update of the plotter.

        :param up_vector: The new camera up vector.
        :type up_vector: str
        """
        self.print_to_console('Setting camera up vector to ' + up_vector + '.')
        up_vector = [float(x) for x in up_vector.split(',')]
        self.plotter.camera.up = up_vector
        self.plotter.update()


    def set_figure_size(self, figure_size):
        """Sets the figure size in the viewer.

        This method sets the figure size in the viewer by updating the
        figure size attribute and triggering an update of the plotter.

        :param figure_size: The new figure size.
        :type figure_size: str
        """
        self.print_to_console('Setting figure size to ' + figure_size + '.')
        figure_size = [int(x) for x in figure_size.split(',')]
        self.figure_size = figure_size


    def handle_camera_position_change(self):
        """Handles the change in camera position.

        This method handles the change in camera position by validating the
        new position and setting the camera position in the viewer.
        """
        new_position = self.camera_position_text.text()
        if self.validate_camera_position(new_position):
            self.set_camera_position(new_position)
            self.clear_position_error_state()
        else:
            self.set_position_error_state()


    def handle_camera_focal_change(self):
        """Handles the change in camera focal point.

        This method handles the change in camera focal point by validating the
        new focal point and setting the camera focal point in the viewer.
        """
        new_focal = self.camera_focal_text.text()
        if self.validate_camera_focal(new_focal):
            self.set_camera_focal(new_focal)
            self.clear_focal_error_state()
        else:
            self.set_focal_error_state()


    def handle_camera_up_change(self):
        """Handles the change in camera up vector.

        This method handles the change in camera up vector by validating the
        new up vector and setting the camera up vector in the viewer.
        """
        new_up = self.camera_up_text.text()
        if self.validate_camera_up(new_up):
            self.set_camera_up(new_up)
            self.clear_up_error_state()
        else:
            self.set_up_error_state()


    def handle_figure_size_change(self):
        """Handles the change in figure size.

        This method handles the change in figure size by validating the
        new size and setting the figure size in the viewer.
        """
        new_size = self.figure_size_text.text()
        if self.validate_figure_size(new_size):
            self.set_figure_size(new_size)
            self.clear_window_error_state()
        else:
            self.set_window_error_state()


    def validate_camera_position(self, position):
        """Validates the camera position.

        This method validates the camera position by checking if it is a
        comma-separated list of three floats. If not, it will print an error
        message and return False.

        :param position: The camera position to validate.
        :type position: str
        :return: True if the camera position is valid, False otherwise.
        :rtype: bool
        """
        try:
            position = [float(x) for x in position.split(',')]
            if len(position) != 3:
                raise ValueError('Invalid camera position')
            return True
        except ValueError:
            self.print_to_console('Error: invalid camera position. Please enter three comma-separated floats.')
            return False
        

    def validate_camera_focal(self, focal_point):
        """Validates the camera focal point.

        This method validates the camera focal point by checking if it is a
        comma-separated list of three floats. If not, it will print an error
        message and return False.

        :param focal_point: The camera focal point to validate.
        :type focal_point: str
        :return: True if the camera focal point is valid, False otherwise.
        :rtype: bool
        """
        try:
            focal_point = [float(x) for x in focal_point.split(',')]
            if len(focal_point) != 3:
                raise ValueError('Invalid camera focal point')
            return True
        except ValueError:
            self.print_to_console('Error: invalid camera focal point. Please enter three comma-separated floats.')
            return False
        
        
    def validate_camera_up(self, up_vector):
        """Validates the camera up vector.

        This method validates the camera up vector by checking if it is a
        comma-separated list of three floats. If not, it will print an error
        message and return False.

        :param up_vector: The camera up vector to validate.
        :type up_vector: str
        :return: True if the camera up vector is valid, False otherwise.
        :rtype: bool
        """
        try:
            up_vector = [float(x) for x in up_vector.split(',')]
            if len(up_vector) != 3:
                raise ValueError('Invalid camera up vector')
            return True
        except ValueError:
            self.print_to_console('Error: invalid camera up vector. Please enter three comma-separated floats.')
            return False
        
        
    def validate_figure_size(self, figure_size):
        """Validates the figure size.

        This method validates the figure size by checking if it is a
        comma-separated list of two integers. If not, it will print an error
        message and return False.

        :param figure_size: The figure size to validate.
        :type figure_size: str
        :return: True if the figure size is valid, False otherwise.
        :rtype: bool
        """
        try:
            figure_size = [int(x) for x in figure_size.split(',')]
            if len(figure_size) != 2:
                raise ValueError('Invalid figure size')
            return True
        except ValueError:
            self.print_to_console('Error: invalid figure size. Please enter two comma-separated integers.')
            return False


    def clear_position_error_state(self):
        """Clears the position error state.

        This method clears the position error state by setting the palette
        of the camera position text to the default palette.
        """
        self.camera_position_text.setPalette(QApplication.palette())


    def clear_focal_error_state(self):
        """Clears the focal error state.

        This method clears the focal error state by setting the palette
        of the camera focal text to the default palette.
        """
        self.camera_focal_text.setPalette(QApplication.palette())


    def clear_up_error_state(self):
        """Clears the up error state.

        This method clears the up error state by setting the palette
        of the camera up text to the default palette.
        """
        self.camera_up_text.setPalette(QApplication.palette())


    def clear_window_error_state(self):
        """Clears the window error state.

        This method clears the window error state by setting the palette
        of the figure size text to the default palette.
        """
        self.figure_size_text.setPalette(QApplication.palette())


    def set_position_error_state(self):
        """Sets the position error state.

        This method sets the position error state by setting the palette
        of the camera position text to a light red color.
        """
        palette = self.camera_position_text.palette()
        palette.setColor(QPalette.Base, QColor(255, 192, 192))
        self.camera_position_text.setPalette(palette)


    def set_focal_error_state(self):
        """Sets the focal error state.

        This method sets the focal error state by setting the palette
        of the camera focal text to a light red color.
        """
        palette = self.camera_focal_text.palette()
        palette.setColor(QPalette.Base, QColor(255, 192, 192))
        self.camera_focal_text.setPalette(palette)


    def set_up_error_state(self):
        """Sets the up error state.

        This method sets the up error state by setting the palette
        of the camera up text to a light red color.
        """
        palette = self.camera_up_text.palette()
        palette.setColor(QPalette.Base, QColor(255, 192, 192))
        self.camera_up_text.setPalette(palette)


    def set_window_error_state(self):
        """Sets the window error state.

        This method sets the window error state by setting the palette
        of the figure size text to a light red color.
        """
        palette = self.figure_size_text.palette()
        palette.setColor(QPalette.Base, QColor(255, 192, 192))
        self.figure_size_text.setPalette(palette)


    def update_menu_action(self, visible):
        """Updates the menu action.

        This method updates the menu action by setting the check state
        to checked if visible, otherwise unchecked.

        :param visible: The visibility of the menu action.
        :type visible: bool
        """
        state = Qt.CheckState.Checked if visible else Qt.CheckState.Unchecked
        self.show_controls_action.setCheckState(state)


    def monitor_camera_position(self):
        """Monitors the camera position.

        This method monitors the camera position by checking if it has changed
        from the last position and updating the timer if it has.
        """
        camera_position = self.plotter.camera_position
        if camera_position != self.last_camera_position:
            self.last_camera_position = camera_position
            self.update_timer.start()
        QTimer.singleShot(100, self.monitor_camera_position)


    def update_view_params(self):
        """Updates the view parameters.

        This method updates the view parameters by setting the camera position,
        focal point, and up vector in the viewer.
        """
        camera_pos = self.plotter.camera_position
        self.camera_position_text.setText('{:.3f}, {:.3f}, {:.3f}'.format(*camera_pos[0]))
        self.camera_focal_text.setText('{:.3f}, {:.3f}, {:.3f}'.format(*camera_pos[1]))
        self.camera_up_text.setText('{:.3f}, {:.3f}, {:.3f}'.format(*camera_pos[2]))
        self.clear_position_error_state()
        self.clear_focal_error_state()
        self.clear_up_error_state()


    def export_figure_dialog(self):
        """Saves the file dialog.

        This method saves the file dialog by getting the save file name
        and emitting the save figure event.
        """
        options = QFileDialog.Options()
        file_types = 'Supported File Types (*.png *.jpeg *.jpg *.bmp *.tif *.tiff *.svg *.eps *.ps *.pdf *.tex);; '\
                     + 'PNG (*.png);;JPEG (*.jpeg);;JPG (*.jpg);;BMP (*.bmp);;TIF (*.tif);;TIFF (*.tiff);;'\
                     + 'SVG (*.svg);;EPS (*.eps);;PS (*.ps);;PDF (*.pdf);;TEX (*.tex)'
        file_name, _ = QFileDialog.getSaveFileName(self, 'Save Figure', '', file_types, options=options)
        
        if file_name:
            self.export_figure(file_name, *self.figure_size)

                
    def export_figure(self, file_name, width, height):
        """Saves the figure.

        This method saves the figure by creating an off-screen plotter with the
        desired size and copying the mesh and camera settings to the off-screen
        plotter.

        :param file_name: The file name to save the figure to.
        :type file_name: str
        :param width: The width of the figure.
        :type width: int
        :param height: The height of the figure.
        :type height: int
        """
        import pyvista as pv

        # create an off-screen plotter with the given size
        off_screen_plotter = pv.Plotter(off_screen=True, window_size=[width, height])

        if self.viewer.bkg_on:
            if self.viewer.gradient:
                off_screen_plotter.set_background(*self.viewer.bkg_colors)
            else:
                off_screen_plotter.set_background(self.viewer.bkg_colors[0])
        else:
            off_screen_plotter.set_background('white')

        if self.depth_peeling_action.isChecked():
            off_screen_plotter.enable_depth_peeling()
        
        # copy the mesh and camera settings to the off-screen plotter
        for actor in self.plotter.renderer.actors.values():
            off_screen_plotter.add_actor(actor)
        
        off_screen_plotter.camera_position = self.plotter.camera_position
        off_screen_plotter.enable_anti_aliasing('msaa', multi_samples=16)

        screenshot_extensions = ['png', 'jpeg', 'jpg', 'bmp', 'tif', 'tiff']
        if file_name.split('.')[-1] in screenshot_extensions:
            off_screen_plotter.screenshot(file_name)
        else:
            off_screen_plotter.save_graphic(file_name, title='GeViewer Figure')

        del off_screen_plotter
        if self.success:
            self.print_to_console('Success: figure saved to ' + file_name)
        else:
            self.print_to_console('Error: figure not saved.')
        self.success = True

    ##############################################################
    # Methods for the tools tab
    ##############################################################

    def check_geometry(self, tolerance, samples):
        """Checks the geometry.

        This method checks the geometry by finding the overlaps between
        the components and updating the overlaps list.

        :param tolerance: The tolerance for the overlaps.
        :type tolerance: float
        :param samples: The number of samples to use for the overlaps.
        :type samples: int
        """
        if self.worker_running:
            self.print_to_console('Error: wait for the current process to finish.')
            return
        tolerance = float(tolerance) if tolerance else 0.001
        samples = int(samples) if samples else 10000
        if not len(self.viewer.components):
            self.print_to_console('Error: no components loaded.')
            return
        self.print_to_console('Checking selected components for overlaps...')
        self.worker = Worker(self.viewer.find_overlaps, self.progress_bar, tolerance=tolerance, n_samples=samples)
        self.worker.on_finished(self.show_overlaps)
        self.worker.error_signal.connect(self.global_exception_hook)
        self.worker_running = True
        self.worker.start()


    def show_overlaps(self):
        """Shows the overlaps.

        This method shows the overlaps by setting the checkboxes to checked
        for the overlapping meshes and toggling the transparency if it is not
        already enabled.
        """
        overlapping_meshes = self.worker.get_result()
        self.worker.deleteLater()
        self.worker_running = False
        if self.success:
            if len(overlapping_meshes) == 0:
                self.print_to_console('Success: no overlaps found.')
            else:
                for checkbox in self.checkbox_mapping.values():
                    checkbox.setCheckState(Qt.CheckState.Unchecked)
                for mesh_id in list(set(overlapping_meshes)):
                    self.checkbox_mapping[mesh_id].setCheckState(Qt.CheckState.Checked)
                if not self.viewer.transparent:
                    self.toggle_transparent(print=False)
                self.plotter.view_isometric()
                self.print_to_console('Found {} potential overlaps.'.format(len(overlapping_meshes)//2))
        else:
            self.print_to_console('Error: overlap check failed.')
        self.success = True
        self.progress_bar.signal_finished()
        self.progress_bar.interrupt = False


    def clear_overlaps(self):
        """Clears the overlaps.

        This method clears the overlaps by removing all actors from the plotter
        and clearing the overlaps list.
        """
        for actor in self.viewer.overlaps:
            self.plotter.remove_actor(actor)
        self.viewer.overlaps = []
        self.print_to_console('Overlaps cleared.')


    def measure_distance(self):
        """Measures the distance.

        This method measures the distance by adding a measurement widget to the plotter
        and clearing the measurement box.
        """
        self.print_to_console('Measuring distance. Click on two points to measure the distance between them.')
        self.plotter.add_measurement_widget(self.display_measurement)


    def display_measurement(self, point1, point2, distance):
        """Displays the measurement.

        This method displays the measurement by setting the measurement box
        to the distance between the two points.

        :param point1: The first point.
        :type point1: list
        :param point2: The second point.
        :type point2: list
        :param distance: The distance between the two points.
        :type distance: float
        """
        boxes = [self.measurement_box, self.measurement_box_2, self.measurement_box_3]
        for box in boxes:
            if box.text() == '':
                box.setText('{:.3f}'.format(distance))
                return
        boxes[0].setText(boxes[1].text())
        boxes[1].setText(boxes[2].text())
        boxes[2].setText('{:.3f}'.format(distance))


    def clear_measurement(self, print_to_console=True):
        """Clears the measurement.

        This method clears the measurement by clearing the measurement boxes.
        """
        self.plotter.clear_measure_widgets()
        self.measurement_box.setText('')
        self.measurement_box_2.setText('')
        self.measurement_box_3.setText('')
        if print_to_console:
            self.print_to_console('Measurements cleared.')

    ##############################################################
    # Methods for the console
    ##############################################################

    def print_to_console(self, text):
        """Prints to the console.

        This method prints text to the console with the GeViewer prompt.

        :param text: The text to print to the console.
        :type text: str
        """
        print('[geviewer-prompt]: ' + text)

    ##############################################################
    # Methods for the menu bar
    ##############################################################

    def open_file_dialog(self):
        """Opens the file dialog.

        This method opens the file dialog by getting the open file name
        and emitting the file name changed event.
        """
        try:
            options = QFileDialog.Options()
            dialog = QFileDialog(self, 'Open File', '', 
                                 'All Supported Files (*.wrl *.heprep *.gev);;' +
                                 'VRML Files (*.wrl);;HepRep Files (*.heprep);;'
                                 'GEV Files (*.gev)', options=options)
            dialog.setFileMode(QFileDialog.ExistingFile)
            dialog.fileSelected.connect(self.load_file)
            dialog.show()
        except Exception as e:
            self.global_exception_hook(type(e), e, e.__traceback__)


    def load_file(self, file_path):
        """Loads the file.
        
        :param file_path: The path to the file to load.
        :type file_path: str
        """
        if file_path:
            if self.worker_running:
                self.print_to_console('Error: wait for the current process to finish.')
                return
            start_time = time.time()
            self.progress_bar.setValue(0)
            self.file_name_changed.emit(file_path)
            self.print_to_console('Loading file: {}\n'.format(file_path))
            self.worker = Worker(self.load_and_plot, self.progress_bar, filename=file_path)
            self.worker.finished.connect(lambda: self.on_file_loaded(start_time))
            self.worker.error_signal.connect(self.global_exception_hook)
            self.worker.finished.connect(self.worker.deleteLater)
            self.worker_running = True
            self.worker.start()


    def load_and_plot(self, progress_obj, filename):
        """The function to call when a file is loaded.

        :param progress_obj: The progress object to use.
        :type progress_obj: ProgressBar
        :param filename: The path to the file to load.
        :type filename: str
        """
        self.viewer.load_file(filename=filename, progress_obj=progress_obj, off_screen=False)
        self.viewer.create_plotter(progress_obj=progress_obj)


    def on_file_loaded(self, start_time=None):
        """Method to call when a file is loaded.

        :param start_time: The start time of the file loading.
        :type start_time: float, optional
        """
        self.worker_running = False
        self.generate_checkboxes(self.viewer.components, 0)
        time_str = ''
        time_elapsed = 0
        if start_time:
            time_elapsed = time.time() - start_time
            time_str = ' in {:.2f} seconds'.format(time_elapsed)
        if self.success:
            self.print_to_console('Success: file loaded' + time_str + '.')
            if time_elapsed > 10:
                self.print_to_console('Hint: save as .gev to speed up loading next time.')
        else:
            self.print_to_console('Error: file could not be loaded.')
        self.success = True
        self.progress_bar.signal_finished()
        self.progress_bar.interrupt = False
        self.file_loaded.emit()


    def save_file_dialog(self):
        """Saves the file.

        This method saves the file by getting the save file name and emitting
        the save file event.
        """
        try:
            options = QFileDialog.Options()
            file_types = 'GeViewer File (*.gev);; All Files (*)'
            file_name, _ = QFileDialog.getSaveFileName(self, 'Save File', 'viewer.gev', file_types, options=options)
            
            if file_name:
                self.viewer.save_session(file_name)
                if self.success:
                    self.print_to_console('Success: file saved to {}.'.format(file_name))
                else:
                    self.print_to_console('Error: file could not be saved.')
                self.success = True
                
        except Exception as e:
            self.global_exception_hook(type(e), e, e.__traceback__)


    def clear_viewer(self):
        """Clears the meshes.

        This method clears the meshes by removing all actors from the plotter
        and clearing the checkbox mapping.
        """
        self.viewer.clear_meshes()
        self.plotter.reset_camera()
        for checkbox in self.checkbox_mapping.values():
            checkbox.setParent(None)
            checkbox.deleteLater()
        self.checkbox_mapping.clear()
        while self.checkboxes_layout.count() > 0:
            item = self.checkboxes_layout.takeAt(0)
            item.widget().deleteLater()
        self.checkboxes_layout.addWidget(self.load_instructions)
        self.load_instructions.setParent(self.checkboxes_layout.parentWidget())
        self.load_instructions.show()
        self.events_list.clear()
        self.current_file.clear()
        self.file_name_changed.emit(None)
        self.event_selection_box.setRange(1, 1)
        self.event_selection_box.setValue(1)
        self.clear_measurement(print_to_console=False)
        gc.collect()
        self.print_to_console('Viewer cleared.')


    def abort_process(self):
        """Aborts a running process.
        """
        if self.worker_running:
            self.print_to_console('Aborting current process...')
            self.success = False
            self.progress_bar.interrupt_worker()
        else:
            self.print_to_console('No process to abort.')


    def toggle_components_panel(self):
        """Toggles the components panel.

        This method toggles the components panel by showing or hiding it
        depending on its current state.
        """
        if self.components_panel.isVisible():
            self.components_panel.hide()
            self.print_to_console('Hiding components panel.')
        else:
            self.components_panel.show()
            self.print_to_console('Showing components panel.')


    def toggle_control_panel(self):
        """Toggles the control panel.

        This method toggles the control panel by showing or hiding it
        depending on its current state.
        """
        if self.control_panel.isVisible():
            self.control_panel.hide()
            self.print_to_console('Hiding control panel.')
        else:
            self.control_panel.show()
            self.print_to_console('Showing control panel.')


    def toggle_background(self):
        """Toggles the background.

        This method toggles the background by setting the background attribute
        of the viewer to the opposite of its current value and updating the
        background button.
        """
        self.print_to_console('Toggling background ' + ['on.','off.'][self.viewer.bkg_on])
        self.viewer.toggle_background()
        self.viewer.plotter.update()


    def toggle_gradient(self):
        """Toggles the gradient.

        This method toggles the gradient by setting the gradient attribute
        of the viewer to the opposite of its current value and updating the
        background color of the viewer.
        """
        self.print_to_console('Toggling gradient ' + ['on.','off.'][self.viewer.gradient])
        self.viewer.gradient = not self.viewer.gradient
        self.viewer.set_background_color()


    def toggle_depth_peeling(self, on=False):
        """Toggles depth peeling.

        This method turns on or off depth peeling for the plotter.
        """
        self.print_to_console('Turning {} depth peeling.'.format(['off','on'][on]))
        if on:
            self.plotter.enable_depth_peeling()
        else:
            self.plotter.disable_depth_peeling()


    def open_color_picker(self, button):
        """Opens the color picker.

        This method opens the color picker by getting the color from the color
        dialog and setting the background color of the viewer.

        :param button: The button to open the color picker for.
        :type button: int
        """
        if button == 2:
            self.viewer.bkg_colors = ['lightskyblue', 'midnightblue']
            self.print_to_console('Resetting background color.')
        else:
            color = QColorDialog.getColor()
            if color.isValid():
                self.viewer.bkg_colors[button] = color.getRgbF()[:3]
                hex_color = color.name()
                self.print_to_console('Setting background color {} to {}.'.format(button + 1, hex_color))
        self.viewer.set_background_color()


    def show_license(self):
        """Shows the license.

        This method shows the license by reading the license file and
        printing it to the console.
        """
        license_raw = utils.get_license()
        license_text = license_raw.replace('\n\n', '<>').replace('\n', ' ').replace('<>', '\n\n')
        self.print_to_console('\n' + license_text)


    def check_for_updates(self):
        """Checks for updates.

        This method checks for updates by calling the check_for_updates function
        from the utils module and printing the result to the console.
        """
        updates = utils.check_for_updates()
        if updates:
            self.print_to_console(updates)
        else:
            self.print_to_console('You are using the latest version of GeViewer.')


    def show_documentation(self):
        """Shows the documentation.

        This method shows the documentation by opening the documentation in
        the default web browser.
        """
        try:
            webbrowser.open('https://geviewer.readthedocs.io/en/latest/')
        except Exception as e:
            doc_url = 'https://geviewer.readthedocs.io/en/latest/'
            self.print_to_console('Find the GeViewer documentation at ' + \
                '<a href="' + doc_url + '">' + doc_url + '</a>')


class ConsoleRedirect(io.StringIO):
    """Redirects stdout and stderr to a QTextEdit widget.
    """
    def __init__(self, console):
        """Initializes the console redirect.

        :param text_edit: The text edit widget to redirect to.
        :type text_edit: QTextEdit
        """
        super().__init__()
        self.console = console


    def write(self, text):
        """Writes to the console.

        This method writes to the console by inserting the text into the text
        edit widget and moving the cursor to the end.

        :param text: The text to write to the console.
        :type text: str
        """
        self.console.moveCursor(QTextCursor.End)
        text = self.stylize_text(text)
        self.console.insertHtml(text)
        self.console.moveCursor(QTextCursor.End)
        super().write(text)

        
    def stylize_text(self, text):
        """Stylizes the text.

        This method stylizes the text by adding a prompt to the beginning of
        the text, replacing newlines with HTML line breaks, and replacing
        warnings, errors, and successes with HTML formatted text.

        :param text: The text to stylize.
        :type text: str
        :return: The stylized text.
        :rtype: str
        """
        prompt = QDateTime.currentDateTime().toString('[yyyy-MM-dd HH:mm:ss]: ')
        text = text.replace('[geviewer-prompt]: ', '<b style="color: blue;">{}</b>'.format(prompt))
        text = text.replace('\n', '<br>')
        text = re.sub(r'\b(Warning)\b', r'<b style="color: orange;">\1</b>', text)
        text = re.sub(r'\b(Error)\b', r'<b style="color: red;">\1</b>', text)
        text = re.sub(r'\b(Success)\b', r'<b style="color: green;">\1</b>', text)
        text = re.sub(r'\b(Hint)\b', r'<b style="color: purple;">\1</b>', text)
        return text


    def flush(self):
        pass

    
class ProgressBar(QProgressBar):
    """A custom progress bar class for the GeViewer application.

    This class handles all interactions between the worker threads and
    the GUI, including updating the progress bar, sending text updates,
    and interrupting the worker threads if necessary.
    """
    #: Signal emitted to update the progress value
    #:
    #: :param int: The new progress value
    progress = pyqtSignal(int)

    #: Signal emitted to set the maximum value of the progress bar
    #:
    #: :param int: The new maximum value
    maximum = pyqtSignal(int)

    #: Signal emitted when the task is finished
    finished = pyqtSignal()

    #: Signal emitted to send status updates
    #:
    #: :param str: The update text
    update = pyqtSignal(str)

    #: Signal emitted to start or stop the timer
    #:
    #: :param bool: True to start the timer, False to stop
    run_timer = pyqtSignal(bool)

    def __init__(self):
        """Initializes the progress bar.
        """
        super().__init__()
        self.setValue(0)
        self.setRange(0, 100)
        self._internal_value = 0
        self.current_value = 0
        self.maximum_value = 100
        self.update_buffer = []
        self.new_progress = False
        self.interrupt = False
        self.progress.connect(self.setValue, Qt.QueuedConnection)
        self.maximum.connect(self.setMaximum, Qt.QueuedConnection)
        self.finished.connect(lambda: self.setValue(self.maximum_value), Qt.QueuedConnection)
        self.update.connect(print)
        self.run_timer.connect(self.start_or_stop_timer)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.send_updates)


    def increment_progress(self):
        """Increments the progress bar by 1%.
        """
        self.current_value += 1
        if 100*(self.current_value - self._internal_value)/self.maximum_value >= 1:
            self._internal_value = self.current_value
            self.new_progress = True

            
    def reset_progress(self):
        """Resets the progress bar to 0%.
        """
        self.current_value = 0
        self._internal_value = 0
        self.progress.emit(0)
        self.run_timer.emit(True)


    def set_maximum_value(self, value):
        """Sets the maximum value of the progress bar.

        :param value: The maximum value of the progress bar.
        :type value: int
        """
        self.maximum_value = value
        self.maximum.emit(value)


    def signal_finished(self):
        """Signals that the progress bar has finished.
        """
        self.send_updates()
        self.run_timer.emit(False)
        self.finished.emit()


    def start_or_stop_timer(self, start):
        """Starts or stops the timer in the main thread.

        :param start: Whether to start the timer.
        :type start: bool
        """
        if start:
            self.timer.start(500)
        else:
            self.timer.stop()


    def print_update(self, text):
        """Adds an update to the update buffer.
        """
        if self.timer.isActive():
            self.update_buffer.append(text)
        else:
            self.update.emit(text)


    def sync_status(self, update=None, increment=False):
        """Synchronizes the status of the worker with that of the user interface.
        This should be called in the following format:

        .. code-block:: python

            pbar = ProgressBar()
            if pbar.sync_status(update, increment): return
        
        where `update` is a string and `increment` is a boolean.
        This will pass the status updates to the user interface and return True
        if the worker should be interrupted.

        :param update: The update to send to the user interface.
        :type update: str, optional
        :param increment: Whether to increment the progress bar.
        :type increment: bool, optional
        :return: Whether the worker should be interrupted.
        :rtype: bool
        """
        if self.interrupt: return True
        if update:
            self.print_update(update)
        if increment:
            self.increment_progress()


    def interrupt_worker(self):
        """Flags an interrupt to the worker.
        """
        if self.timer.isActive():
            self.interrupt = True


    def send_updates(self):
        """Flushes the update buffer.
        """
        if self.new_progress:
            self.progress.emit(self._internal_value)
            self.new_progress = False
        if self.update_buffer:
            self.update.emit('\n'.join(self.update_buffer))
            self.update_buffer.clear()
        

class Worker(QThread):
    """A custom worker class for the GeViewer application.
    """
    #: Signal emitted when the worker has finished its task
    finished = pyqtSignal()

    #: Signal emitted when an error occurs during the worker's task
    #:
    #: :param type: The type of the exception
    #: :param Exception: The exception instance
    #: :param object: The traceback object
    error_signal = pyqtSignal(type, Exception, object)

    def __init__(self, task, progress_bar, **kwargs):
        """Initializes the worker.

        :param task: The task to be executed by the worker
        :type task: callable
        :param progress_bar: The progress bar to update during the task
        :type progress_bar: ProgressBar
        :param kwargs: Additional keyword arguments for the task
        """
        super().__init__()
        self.task = task
        self.kwargs = kwargs
        self.progress_bar = progress_bar
        self.result = None


    def run(self):
        """Runs the worker.
        """
        try:
            self.result = self.task(progress_obj=self.progress_bar, **self.kwargs)
        except Exception as e:
            self.error_signal.emit(type(e), e, e.__traceback__)
        finally:
            self.finished.emit()


    def on_finished(self, func):
        """Connects a function to the finished signal.

        :param func: The function to connect to the finished signal.
        :type func: function
        """
        self.finished.connect(func)


    def get_result(self):
        """Returns the result of the worker.
        """
        return self.result


    def cleanup(self):
        """Cleans up the resources used by the worker.
        """
        self.task = None
        self.kwargs.clear()
        self.progress_bar = None
        self.result = None


    def deleteLater(self):
        """Overrides the deleteLater method to clean up the resources used by the worker.
        """
        self.cleanup()
        super().deleteLater()


def launch_app(files_to_load=None):
    """Launches the app.
    """
    app = Application([])
    app.setStyle('Fusion')
    
    window = Window()
    sys.excepthook = window.global_exception_hook
    window.show()

    if files_to_load:
        window.load_initial_files(files_to_load)

    return app.exec()
