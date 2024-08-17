import sys
from datetime import datetime
import traceback
import webbrowser

from PyQt6.QtWidgets import (
    QApplication, QVBoxLayout, QHBoxLayout, QPushButton, QWidget,
    QCheckBox, QSplitter, QFileDialog, QLabel, QTextEdit, QLineEdit,
    QColorDialog, QMenu, QToolBar, QSpinBox, QFrame, QScrollArea,
    QMessageBox, QGridLayout, QTabWidget, QGroupBox, QSpacerItem,
    QSizePolicy, QWidgetAction, QGraphicsOpacityEffect
)
from PyQt6.QtGui import (
    QAction, QFont, QColor, QPalette, QDoubleValidator, QIntValidator,
    QKeySequence, QIcon
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer, QSize

from geviewer.geviewer import GeViewer
import geviewer.utils as utils
from pyvistaqt import MainWindow


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
    file_name_changed = pyqtSignal(str)
    number_of_events = pyqtSignal(int)


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

        # create the main window
        self.setWindowTitle(self.default_title)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.splitter = QSplitter(Qt.Horizontal)

        # add panels, toolbar, and menu bar
        self.add_viewer_panel()
        self.add_control_panel()
        self.add_components_panel()

        self.splitter.addWidget(self.components_panel)
        self.splitter.addWidget(self.viewer_panel)
        self.splitter.addWidget(self.control_panel)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setSizes([300, 800, 300])
        
        self.add_menu_bar()

        # Add the splitter to the layout
        self.main_layout.addWidget(self.splitter)
        self.number_of_events.connect(self.update_event_total)
        self.print_to_console('Welcome to GeViewer!')
        utils.check_for_updates()

        # resize and center the window
        self.resize_window()
        # Set the window reference
        QApplication.instance().window = self


    def resize_window(self):
        # Get the primary screen
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()

        # Get the size hint from the main layout
        # size_hint = self.main_layout.sizeHint()

        # Ensure the size is not larger than the screen
        # desired_width = min(size_hint.width(), int(screen_geometry.width() * 0.9))
        # desired_height = min(size_hint.height(), int(screen_geometry.height() * 0.9))

        if int(screen_geometry.width()) < 1920:
            self.showMaximized()
        else:
            self.resize(QSize(int(screen_geometry.width() * 0.8), \
                              int(screen_geometry.height() * 0.8)))
            self.center_on_screen(screen_geometry)


    def center_on_screen(self, screen_geometry):
        frame_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())


    def global_exception_hook(self, exctype, value, traceback_obj):
        """Global method to catch unhandled exceptions."""
        error_message = ''.join(traceback.format_exception(exctype, value, traceback_obj))
        self.print_to_console('Error:\n' + error_message)
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Icon.Critical)
        error_box.setText('An unexpected error occurred.')
        error_box.setInformativeText(str(value))
        error_box.setDetailedText(error_message)
        error_box.setWindowTitle('Error')
        error_box.exec()


    def add_components_panel(self):
        """Adds the components panel to the main window.
        """
        # create a layout for the components panel
        self.components_panel = QWidget()
        # self.components_panel.setMinimumWidth(256)
        self.object_layout = QVBoxLayout(self.components_panel)

        # add a heading
        heading = QLabel('Components')
        # heading_font = QFont()
        # heading_font.setPointSize(13)
        # # heading_font.setWeight(QFont.Light)
        # # heading_font.setBold(True)
        # heading.setFont(heading_font)
        

        tab_height = self.tab_widget.tabBar().height()  # Get the actual height of the tab
        heading.setFixedHeight(tab_height)
        heading.setAlignment(Qt.AlignVCenter)
        heading.setStyleSheet("padding-left: 5px;")
        self.object_layout.addWidget(heading)

        # create the scroll area for the checkboxes
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        instructions = 'Click "File > Open File..." to add components'
        self.load_instructions = QLabel(instructions)
        load_instructions_font = QFont()
        load_instructions_font.setPointSize(12)
        load_instructions_font.setItalic(True)
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.5)
        self.load_instructions.setGraphicsEffect(opacity_effect)
        self.load_instructions.setFont(load_instructions_font)
        self.load_instructions.setWordWrap(True)
        # self.scroll_area.setWidget(self.load_instructions)

        self.checkboxes_widget = QWidget()
        self.checkboxes_layout = QVBoxLayout(self.checkboxes_widget)
        self.checkboxes_layout.setAlignment(Qt.AlignTop)
        self.checkboxes_layout.addWidget(self.load_instructions)
        self.scroll_area.setWidget(self.checkboxes_widget)
        self.object_layout.addWidget(self.scroll_area)


    def add_viewer_panel(self):
        """Adds the viewer panel to the main window.
        """
        # create a layout for the viewer panel
        self.viewer_panel = QWidget()
        # self.viewer_panel.setMinimumWidth(512)
        # self.viewer_panel.setMinimumHeight(720)
        self.viewer_layout = QVBoxLayout(self.viewer_panel)

        # # add a heading that updates as files are loaded
        # self.heading = QLabel('Viewing: ' + self.default_title)
        # heading_font = QFont()
        # heading_font.setPointSize(14)
        # heading_font.setBold(True)
        # self.heading.setFont(heading_font)
        self.file_name_changed.connect(self.update_title)
        # self.viewer_layout.addWidget(self.heading)

        # create the viewer
        self.viewer = GeViewer(self.viewer_panel)
        self.plotter = self.viewer.plotter
        self.add_key_events()

        # add the toolbar
        self.add_toolbar()

        # add the plotter to the viewer layout
        self.viewer_layout.addWidget(self.plotter.interactor)


    def add_control_panel(self):
        """Adds the control panel to the main window.
        """
        # create a layout for the control panel
        self.control_panel = QWidget()
        # self.control_panel.setMinimumWidth(256)
        self.control_layout = QVBoxLayout(self.control_panel)

        # add a heading for the console
        control_panel_heading = QLabel('Control Panel')
        control_panel_heading_font = QFont()
        control_panel_heading_font.setPointSize(14)
        control_panel_heading_font.setBold(True)
        control_panel_heading.setFont(control_panel_heading_font)
        # self.control_layout.addWidget(control_panel_heading)

        # Create a tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumWidth(250)
        self.tab_widget.setMinimumHeight(300)
        self.tab_widget.setMaximumHeight(350)
        # self.tab_widget.setMaximumHeight(350)

        # Create tabs
        self.options_tab = QWidget()
        self.tools_tab = QWidget()

        # Create layouts for each tab
        self.options_layout = QVBoxLayout(self.options_tab)
        self.tools_layout = QVBoxLayout(self.tools_tab)

        # Add tabs to the tab widget
        self.tab_widget.addTab(self.options_tab, 'Options')
        self.tab_widget.addTab(self.tools_tab, 'Tools')

        # Add the tab widget to the control layout
        self.control_layout.addWidget(self.tab_widget)

        # Add components to tabs
        self.add_options_tab()
        self.add_tools_tab()

        # add a separator between the geometry checker and the console
        # line = QFrame()
        # line.setFrameShape(QFrame.HLine)
        # line.setFrameShadow(QFrame.Sunken)
        # self.control_layout.addWidget(line)

        # Create a QGroupBox for the console
        # console_group = QGroupBox("Console")
        console_layout = QVBoxLayout()
        
        # Add the console to the group box
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        sys.stdout = utils.ConsoleRedirect(self.console)
        sys.stderr = utils.ConsoleRedirect(self.console)
        console_layout.addWidget(self.console)
        
        # Set the layout for the group box
        # console_group.setLayout(console_layout)
        
        # Add the group box to the control layout
        # self.control_layout.addWidget(console_group)
        self.control_layout.addLayout(console_layout)

        # Add the progress bar
        self.progress_bar = utils.ProgressBar()
        self.control_layout.addWidget(self.progress_bar)


    def add_options_tab(self):
        """Adds camera and figure options to the first tab."""
        grid_layout = QGridLayout()

        # Camera Options section
        heading = QLabel('Camera Options')
        heading_font = QFont()
        heading_font.setPointSize(14)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        grid_layout.addWidget(heading, 0, 0, 1, 2)  # Spanning 2 columns

        camera_instructions = 'Enter the coordinates as three comma-separated numbers'

        self.camera_position_label = QLabel('Position:')
        self.camera_position_text = QLineEdit()
        self.camera_position_text.setReadOnly(False)
        self.camera_position_text.editingFinished.connect(self.handle_camera_position_change)
        self.camera_position_text.setToolTip(camera_instructions)
        grid_layout.addWidget(self.camera_position_label, 1, 0)
        grid_layout.addWidget(self.camera_position_text, 1, 1, 1, 1)

        self.camera_focal_label = QLabel('Focal point:')
        self.camera_focal_text = QLineEdit()
        self.camera_focal_text.setReadOnly(False)
        self.camera_focal_text.editingFinished.connect(self.handle_camera_focal_change)
        self.camera_focal_text.setToolTip(camera_instructions)
        grid_layout.addWidget(self.camera_focal_label, 2, 0)
        grid_layout.addWidget(self.camera_focal_text, 2, 1, 1, 1)

        self.camera_up_label = QLabel('Up vector:')
        self.camera_up_text = QLineEdit()
        self.camera_up_text.setReadOnly(False)
        self.camera_up_text.editingFinished.connect(self.handle_camera_up_change)
        self.camera_up_text.setToolTip(camera_instructions)
        grid_layout.addWidget(self.camera_up_label, 3, 0)
        grid_layout.addWidget(self.camera_up_text, 3, 1, 1, 1)

        # Event Viewer section (moved above Figure Options)
        event_heading = QLabel('Event Viewer')
        event_heading_font = QFont()
        event_heading_font.setPointSize(14)
        event_heading_font.setBold(True)
        event_heading.setFont(event_heading_font)
        grid_layout.addWidget(event_heading, 4, 0, 1, 2)  # Spanning 2 columns

        self.event_selection_label = QLabel('Show event:')
        self.event_selection_box = QSpinBox()
        self.event_selection_box.setRange(1, 1)
        self.event_selection_box.setValue(1)
        self.event_selection_box.setWrapping(True)
        self.event_selection_box.valueChanged.connect(lambda: self.show_single_event(self.event_selection_box.value()))
        grid_layout.addWidget(self.event_selection_label, 5, 0)
        grid_layout.addWidget(self.event_selection_box, 5, 1, 1, 1)

        # Figure Options section
        figure_heading = QLabel('Figure Options')
        figure_heading_font = QFont()
        figure_heading_font.setPointSize(14)
        figure_heading_font.setBold(True)
        figure_heading.setFont(figure_heading_font)
        grid_layout.addWidget(figure_heading, 6, 0, 1, 2)  # Spanning 2 columns

        figure_instructions = 'Enter the figure width and height in pixels as two comma-separated numbers'

        self.figure_size_label = QLabel('Figure size:')
        self.figure_size_text = QLineEdit()
        self.figure_size_text.setText('{}, {}'.format(*self.figure_size))
        self.figure_size_text.setReadOnly(False)
        self.figure_size_text.editingFinished.connect(self.handle_figure_size_change)
        self.figure_size_text.setToolTip(figure_instructions)
        grid_layout.addWidget(self.figure_size_label, 7, 0)
        grid_layout.addWidget(self.figure_size_text, 7, 1, 1, 1)

        self.save_button = QPushButton('Export Figure', self)
        self.save_button.clicked.connect(self.save_file_dialog)
        grid_layout.addWidget(self.save_button, 8, 0, 1, 2)  # Spanning 2 columns

        self.options_layout.addLayout(grid_layout)
        
        # Align the content to the top
        # self.options_layout.setAlignment(Qt.AlignTop)


    def add_tools_tab(self):
        """Adds view and geometry options to the second tab."""
        grid_layout = QGridLayout()

        # Overlap Inspector section
        overlap_heading = QLabel('Overlap Inspector')
        overlap_heading_font = QFont()
        overlap_heading_font.setPointSize(14)
        overlap_heading_font.setBold(True)
        overlap_heading.setFont(overlap_heading_font)
        grid_layout.addWidget(overlap_heading, 0, 0, 1, 2)  # Spanning 2 columns

        self.tolerance_label = QLabel('Tolerance:')
        self.tolerance_box = QLineEdit()
        double_validator = QDoubleValidator(1e-6, 1, 6)
        double_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.tolerance_box.setValidator(double_validator)
        self.tolerance_box.setText('0.001')
        self.tolerance_box.setToolTip('Enter the tolerance for overlap detection')
        grid_layout.addWidget(self.tolerance_label, 1, 0)
        grid_layout.addWidget(self.tolerance_box, 1, 1, 1, 1)

        self.samples_label = QLabel('Number of points:')
        self.samples_box = QLineEdit(self)
        int_validator = QIntValidator(1000, 10000000)
        self.samples_box.setValidator(int_validator)
        self.samples_box.setText('10000')
        self.samples_box.setToolTip('Enter the number of sample points for overlap detection')
        grid_layout.addWidget(self.samples_label, 2, 0)
        grid_layout.addWidget(self.samples_box, 2, 1, 1, 1)

        self.check_button = QPushButton('Find Overlaps')
        self.check_button.clicked.connect(lambda: self.check_geometry(self.tolerance_box.text(), self.samples_box.text()))
        self.clear_intersections_button = QPushButton('Clear')
        self.clear_intersections_button.clicked.connect(self.clear_intersections)
        grid_layout.addWidget(self.check_button, 3, 0)
        grid_layout.addWidget(self.clear_intersections_button, 3, 1, 1, 1)

        measurement_heading = QLabel('Measurement Tool')
        measurement_heading_font = QFont()
        measurement_heading_font.setPointSize(14)
        measurement_heading_font.setBold(True)
        measurement_heading.setFont(measurement_heading_font)
        grid_layout.addWidget(measurement_heading, 4, 0, 1, 2)  # Spanning 2 columns

        # Measurement 1
        self.measure_text = QLabel('Measurement 1:')
        self.measurement_box = QLineEdit()
        self.measurement_box.setReadOnly(True)
        grid_layout.addWidget(self.measure_text, 5, 0)
        grid_layout.addWidget(self.measurement_box, 5, 1, 1, 1)

        # Measurement 2
        self.measure_text_2 = QLabel('Measurement 2:')
        self.measurement_box_2 = QLineEdit()
        self.measurement_box_2.setReadOnly(True)
        grid_layout.addWidget(self.measure_text_2, 6, 0)
        grid_layout.addWidget(self.measurement_box_2, 6, 1, 1, 1)

        # Measurement 3
        self.measure_text_3 = QLabel('Measurement 3:')
        self.measurement_box_3 = QLineEdit()
        self.measurement_box_3.setReadOnly(True)
        grid_layout.addWidget(self.measure_text_3, 7, 0)
        grid_layout.addWidget(self.measurement_box_3, 7, 1, 1, 1)

        # Add and Clear buttons
        self.measure_button = QPushButton('Add Measurement')
        self.measure_button.setMinimumWidth(130)
        self.measure_button.clicked.connect(self.measure_distance)
        self.clear_measurement_button = QPushButton('Clear')
        self.clear_measurement_button.clicked.connect(self.clear_measurement)
        grid_layout.addWidget(self.measure_button, 8, 0)
        grid_layout.addWidget(self.clear_measurement_button, 8, 1)

        # Create a timer to update the boxes above with the new values
        self.update_timer = QTimer()
        self.update_timer.setInterval(200)
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.update_view_params)
        self.last_camera_position = None
        self.last_figure_size = None
        self.monitor_camera_position()

        self.tools_layout.addLayout(grid_layout)
        
        # Align the content to the top
        # self.tools_layout.setAlignment(Qt.AlignTop)


    def add_toolbar(self):
        """Adds the toolbar to the main window.

        This method creates a QToolBar and populates it with various actions
        for controlling the viewer's display options and camera views. The
        toolbar includes actions for toggling wireframe mode, transparency,
        parallel projection, and setting different standard views (isometric,
        top, bottom, front, back).

        The toolbar is made movable and the actions are given icons for better visibility.
        """
        self.toolbar = QToolBar('Main Toolbar')
        self.toolbar.setMovable(True)

        toolbar_font = QFont()
        toolbar_font.setPointSize(12)  # Adjust this value to change the text size
        action_width = 80
        self.toolbar.setFont(toolbar_font)

        # Create actions
        self.wireframe_action = QAction('Wireframe', self)
        # self.wireframe_action.setCheckable(True)
        self.wireframe_action.triggered.connect(self.toggle_wireframe)

        self.transparent_action = QAction('Transparent', self)
        # self.transparent_action.setCheckable(True)
        self.transparent_action.triggered.connect(self.toggle_transparent)

        self.parallel_action = QAction('Parallel', self)
        # self.parallel_action.setCheckable(True)
        self.parallel_action.triggered.connect(self.toggle_parallel)

        isometric_action = QAction('Isometric', self)
        isometric_action.triggered.connect(self.plotter.view_isometric)

        # Add actions to the toolbar
        self.toolbar.addAction(self.wireframe_action)
        tool_button = self.toolbar.widgetForAction(self.wireframe_action)
        tool_button.setFixedWidth(action_width)
        self.toolbar.addAction(self.transparent_action)
        tool_button = self.toolbar.widgetForAction(self.transparent_action)
        tool_button.setFixedWidth(action_width)
        self.toolbar.addAction(self.parallel_action)
        tool_button = self.toolbar.widgetForAction(self.parallel_action)
        tool_button.setFixedWidth(action_width)
        self.toolbar.addAction(isometric_action)
        tool_button = self.toolbar.widgetForAction(isometric_action)
        tool_button.setFixedWidth(action_width)

        # tool_button.setStyleSheet("QToolButton { min-width: 80px; max-width: 80px; }")

        # Create and add actions for view buttons
        view_actions = [
            ('Top', self.plotter.view_xy),
            ('Bottom', lambda: self.plotter.view_xy(negative=True)),
            ('Front', self.plotter.view_yz),
            ('Back', lambda: self.plotter.view_yz(negative=True)),
            ('Left', self.plotter.view_xz),
            ('Right', lambda: self.plotter.view_xz(negative=True))
        ]

        for text, callback in view_actions:
            action = QAction(text, self)
            action.triggered.connect(callback)
            self.toolbar.addAction(action)
            tool_button = self.toolbar.widgetForAction(action)
            tool_button.setFixedWidth(60)

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
        save_action.triggered.connect(self.save_file)
        close_window_action = file_menu.addAction('Close Window')
        close_window_action.triggered.connect(self.close)
        close_window_action.setShortcut(QKeySequence.Close)

        # create the edit menu
        edit_menu = menubar.addMenu('Edit')
        copy_console_action = edit_menu.addAction('Copy Console')
        copy_console_action.triggered.connect(self.console.selectAll)
        copy_console_action.triggered.connect(self.console.copy)
        copy_console_action.setShortcut(QKeySequence.Copy)
        clear_console_action = edit_menu.addAction('Clear Console')
        clear_console_action.triggered.connect(self.console.clear)
        clear_action = edit_menu.addAction('Clear Viewer')
        clear_action.triggered.connect(self.clear_meshes)

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
        update_action.triggered.connect(utils.check_for_updates)
        documentation_action = help_menu.addAction('Documentation')
        documentation_action.triggered.connect(self.show_documentation)

    
    @pyqtSlot(str)
    def update_title(self, filename):
        """Updates the header text to reflect the current file being viewed.

        This method updates the text of the header to indicate the current file
        being viewed. If multiple files are being viewed, it will also show
        the number of additional files being viewed.

        :param filename: The name of the file being viewed.
        :type filename: str
        """
        if filename:
            self.current_file.append(filename)
            title = self.default_title + ' - ' + self.current_file[0] \
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
        self.load_instructions.hide()
        self.load_instructions.parentWidget().update()
        for comp in components:
            if comp['id'] not in self.checkbox_mapping:
                checkbox = QCheckBox(comp['name'])
                checkbox.setCheckState(Qt.CheckState.Checked)
                checkbox.stateChanged.connect(lambda state, comp=comp: self.toggle_visibility(state, comp))
                self.checkboxes_layout.addWidget(checkbox)
                checkbox.setStyleSheet(f"padding-left: {20 * level}px")
                self.checkbox_mapping[comp['id']] = checkbox
                self.progress_bar.increment_progress()
                if comp['is_event'] and 'Event' in comp['name']:
                    self.events_list.append(comp['id'])
                if 'children' in comp and comp['children']:
                    self.generate_checkboxes(comp['children'], level + 1)
        self.number_of_events.emit(len(self.events_list))


    def show_single_event(self, event_index):
        """Shows a single event in the viewer.

        This method shows a single event in the viewer by checking the
        corresponding checkbox and updating the visibility of the associated
        actors.

        :param event_index: The index of the event to show.
        :type event_index: int
        """
        for i, event in enumerate(self.events_list):
            if i == event_index - 1:
                self.checkbox_mapping[event].setCheckState(Qt.CheckState.Checked)
            else:
                self.checkbox_mapping[event].setCheckState(Qt.CheckState.Unchecked)
    

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


    def set_camera_position(self, position):
        """Sets the camera position in the viewer.

        This method sets the camera position in the viewer by updating the
        camera's position attribute and triggering an update of the plotter.

        :param position: The new camera position.
        :type position: str
        """
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


    def toggle_gradient(self):
        """Toggles the gradient.

        This method toggles the gradient by setting the gradient attribute
        of the viewer to the opposite of its current value and updating the
        background color of the viewer.
        """
        self.viewer.gradient = not self.viewer.gradient
        self.viewer.set_background_color()


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

    
    def clear_meshes(self):
        """Clears the meshes.

        This method clears the meshes by removing all actors from the plotter
        and clearing the checkbox mapping.
        """
        for actor in list(self.plotter.renderer.actors.values()):
            self.plotter.remove_actor(actor)
        self.checkbox_mapping = {}
        while self.checkboxes_layout.count() > 0:
            item = self.checkboxes_layout.takeAt(0)
            item.widget().deleteLater()
        self.checkboxes_layout.addWidget(self.load_instructions)
        self.load_instructions.show()
        self.viewer.clear_meshes()
        self.events_list = []
        self.current_file = []
        self.file_name_changed.emit(None)


    def toggle_components_panel(self):
        """Toggles the components panel.

        This method toggles the components panel by showing or hiding it
        depending on its current state.
        """
        if self.components_panel.isVisible():
            self.components_panel.hide()
        else:
            self.components_panel.show()


    def toggle_control_panel(self):
        """Toggles the control panel.

        This method toggles the control panel by showing or hiding it
        depending on its current state.
        """
        if self.control_panel.isVisible():
            self.control_panel.hide()
        else:
            self.control_panel.show()


    def show_license(self):
        """Shows the license.

        This method shows the license by reading the license file and
        printing it to the console.
        """
        with open('LICENSE') as f:
            license_text = f.read().replace('\n\n', '<>').replace('\n', ' ').replace('<>', '\n\n')
        self.print_to_console('\n' + license_text)


    def toggle_parallel(self):
        """Toggles the parallel projection.

        This method toggles the parallel projection by setting the parallel
        attribute of the viewer to the opposite of its current value and
        updating the parallel button.
        """
        self.viewer.toggle_parallel_projection()
        self.parallel_action.setText('Perspective' if self.viewer.parallel else 'Parallel')


    def toggle_wireframe(self):
        """Toggles the wireframe.

        This method toggles the wireframe by setting the wireframe attribute
        of the viewer to the opposite of its current value and updating the
        wireframe button.
        """
        self.viewer.toggle_wireframe()
        self.update_wireframe_action()


    def toggle_transparent(self):
        """Toggles the transparency.

        This method toggles the transparency by setting the transparent attribute
        of the viewer to the opposite of its current value and updating the
        transparency button.
        """
        self.viewer.toggle_transparent()
        self.transparent_action.setText('Opaque' if self.viewer.transparent else 'Transparent')


    def update_wireframe_action(self):
        """Updates the wireframe button.

        This method updates the wireframe button by setting the text to 'Solid'
        if the wireframe is enabled, otherwise 'Wireframe'.
        """
        self.wireframe_action.setText('Solid' if self.viewer.wireframe else 'Wireframe')


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
            dialog.fileSelected.connect(self.handle_file_selected)
            dialog.show()
        except Exception as e:
            self.global_exception_hook(type(e), e, e.__traceback__)

    def handle_file_selected(self, file_path):
        """Handles the selected file."""
        if file_path:
            self.progress_bar.setValue(0)
            self.file_name_changed.emit(file_path)
            self.print_to_console('Loading file: ' + file_path)
            self.worker = utils.Worker(self.viewer.load_files, self.progress_bar, filename=file_path, off_screen=True)
            self.worker.on_finished(self.add_components)
            self.worker.start()

    def save_file_dialog(self):
        """Saves the file dialog.

        This method saves the file dialog by getting the save file name
        and emitting the save figure event.
        """
        options = QFileDialog.Options()
        file_types = 'Supported File Types (*.png *.svg *.eps *.ps *.pdf *.tex);; '\
                     + 'PNG (*.png);;SVG (*.svg);;EPS (*.eps);;PS (*.ps);;PDF (*.pdf);;TEX (*.tex)'
        file_name, _ = QFileDialog.getSaveFileName(self, 'Save Figure', '', file_types, options=options)
        
        if file_name:
            try:
                self.save_figure(file_name, *self.figure_size)
            except Exception as e:
                print(e)

                
    def save_figure(self, file_name, width, height):
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

        # Create an off-screen plotter with the desired size
        off_screen_plotter = pv.Plotter(off_screen=True, window_size=[width, height])
        off_screen_plotter.set_background(*self.viewer.bkg_colors)
        
        # Copy the mesh and camera settings to the off-screen plotter
        for actor in self.plotter.renderer.actors.values():
            off_screen_plotter.add_actor(actor)
        
        # Copy camera position
        off_screen_plotter.camera_position = self.plotter.camera_position
        off_screen_plotter.enable_anti_aliasing('msaa', multi_samples=16)

        screenshot_extensions = ['png', 'jpeg', 'jpg', 'bmp', 'tif', 'tiff']
        if file_name.split('.')[-1] in screenshot_extensions:
            off_screen_plotter.screenshot(file_name)
        else:
            off_screen_plotter.save_graphic(file_name, title='GeViewer Figure')

        del off_screen_plotter
        print('Success: figure saved to ' + file_name)


    def open_color_picker(self, button):
        """Opens the color picker.

        This method opens the color picker by getting the color from the color
        dialog and setting the background color of the viewer.

        :param button: The button to open the color picker for.
        :type button: int
        """
        if button==2:
            self.viewer.bkg_colors = ['lightskyblue', 'midnightblue']
        else:
            color = QColorDialog.getColor()
            if color.isValid():
                self.viewer.bkg_colors[button] = color.getRgbF()[:3]
        self.viewer.set_background_color()


    def print_to_console(self, text):
        """Prints to the console.

        This method prints text to the console with the GeViewer prompt.

        :param text: The text to print to the console.
        :type text: str
        """
        print('[geviewer-prompt]: ' + text)

    
    def add_components(self):
        """Adds the components.

        This method adds the components by creating the plotter and generating
        the checkboxes for the components.
        """
        num_plotted = len(self.viewer.actors.keys())
        self.viewer.create_plotter(self.progress_bar)
        checkboxes_to_make = len(self.viewer.actors.keys()) - num_plotted
        self.progress_bar.reset_progress()
        self.progress_bar.set_maximum_value(checkboxes_to_make)
        self.generate_checkboxes(self.viewer.components, 0)


    def save_file(self):
        """Saves the file.

        This method saves the file by getting the save file name and emitting
        the save file event.
        """
        try:
            options = QFileDialog.Options()
            file_types = 'GeViewer File (*.gev);; All Files (*)'
            file_name, _ = QFileDialog.getSaveFileName(self, 'Save File', 'viewer.gev', file_types, options=options)
            
            if file_name:
                try:
                    self.viewer.save(file_name)
                except Exception as e:
                    print(e)
        except Exception as e:
            self.global_exception_hook(type(e), e, e.__traceback__)


    def toggle_background(self):
        """Toggles the background.

        This method toggles the background by setting the background attribute
        of the viewer to the opposite of its current value and updating the
        background button.
        """
        self.viewer.toggle_background()
        self.viewer.plotter.update()

    def check_geometry(self, tolerance, samples):
        """Checks the geometry.

        This method checks the geometry by finding the intersections between
        the components and updating the intersections list.

        :param tolerance: The tolerance for the intersections.
        :type tolerance: float
        :param samples: The number of samples to use for the intersections.
        :type samples: int
        """
        tolerance = float(tolerance) if tolerance else 0.001
        samples = int(samples) if samples else 10000
        if not len(self.viewer.components):
            self.print_to_console('Error: no components loaded.')
            return
        self.print_to_console('Checking {} for intersections...'.format(self.viewer.components[0]['name']))
        overlapping_meshes = self.viewer.find_intersections(tolerance, samples)
        if len(overlapping_meshes) == 0:
            self.print_to_console('Success: no intersections found.')
        else:
            self.show_overlaps(overlapping_meshes)
            self.print_to_console('Done.')


    def show_overlaps(self, overlapping_meshes):
        """Shows the overlaps.

        This method shows the overlaps by setting the checkboxes to checked
        for the overlapping meshes and toggling the transparency if it is not
        already enabled.

        :param overlapping_meshes: The overlapping meshes.
        :type overlapping_meshes: list
        """
        for checkbox in self.checkbox_mapping.values():
            checkbox.setCheckState(Qt.CheckState.Unchecked)
        for mesh_id in overlapping_meshes:
            self.checkbox_mapping[mesh_id].setCheckState(Qt.CheckState.Checked)
        if not self.viewer.transparent:
            self.toggle_transparent()
        self.plotter.view_isometric()


    def clear_intersections(self):
        """Clears the intersections.

        This method clears the intersections by removing all actors from the plotter
        and clearing the intersections list.
        """
        for actor in self.viewer.intersections:
            self.plotter.remove_actor(actor)
        self.viewer.intersections = []


    def measure_distance(self):
        """Measures the distance.

        This method measures the distance by adding a measurement widget to the plotter
        and clearing the measurement box.
        """
        self.plotter.add_measurement_widget(self.display_measurement)


    def clear_measurement(self):
        """Clears the measurement.

        This method clears the measurement by clearing the measurement box.
        """
        self.plotter.clear_measure_widgets()
        self.measurement_box.setText('')
        self.measurement_box_2.setText('')
        self.measurement_box_3.setText('')


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


def launch_app():
    """Launches the app."""
    app = Application([])
    app.setStyle('Fusion')
    
    window = Window()
    
    sys.excepthook = window.global_exception_hook
    
    window.show()
    
    # Process events before entering the main event loop
    app.processEvents()
    
    # Use exec() instead of exit() to allow for clean shutdown
    return app.exec()

# Modify the main script to use the return value from launch_app()
if __name__ == "__main__":
    sys.exit(launch_app())


def global_exception_hook(exctype, value, traceback_obj):
    error_message = ''.join(traceback.format_exception(exctype, value, traceback_obj))
    print('Error:')
    print(error_message)