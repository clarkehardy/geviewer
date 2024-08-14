import sys
import io
import time
from datetime import datetime
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
from PyQt5.QtWidgets import QSpinBox
from PyQt5.QtWidgets import QDoubleSpinBox
from PyQt5.QtWidgets import QFrame
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QPalette
from PyQt5.QtGui import QKeySequence
from PyQt5.QtGui import QTextCursor
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtGui import QIntValidator
from PyQt5.QtGui import QTextBlockFormat
from PyQt5.QtGui import QTextCharFormat
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QThread
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import QDateTime
from geviewer.geviewer import GeViewer
import geviewer.utils as utils
from pyvistaqt import MainWindow
import pyvista as pv


class GeConsoleRedirect(io.StringIO):
    """Redirects stdout and stderr to a QTextEdit widget.

    :param io: The QTextEdit widget to redirect output to.
    :type io: QTextEdit
    """
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit
        self.warning_format = QTextCharFormat()
        self.warning_format.setForeground(QColor('orange'))
        self.warning_format.setFontWeight(QFont.Bold)
        self.error_format = QTextCharFormat()
        self.error_format.setForeground(QColor('red'))
        self.error_format.setFontWeight(QFont.Bold)

    def write(self, text):
        self.text_edit.moveCursor(QTextCursor.End)
        text = self.stylize_text(text)
        self.text_edit.insertHtml(text)
        self.text_edit.moveCursor(QTextCursor.End)
        super().write(text)
        
    def stylize_text(self, text):
        prompt = QDateTime.currentDateTime().toString('[yyyy-MM-dd HH:mm:ss]: ')
        text = text.replace('[geviewer-prompt]: ', '<b style="color: blue;">{}</b>'.format(prompt))
        text = text.replace('\n', '<br>')
        text = text.replace('Warning:', '<b style="color: orange;">Warning:</b>')
        text = text.replace('Error:', '<b style="color: red;">Error:</b>')
        text = text.replace('Success:', '<b style="color: green;">Success:</b>')
        return text

    def flush(self):
        pass

    
class GeProgressBar(QProgressBar):

    progress = pyqtSignal(int)
    maximum = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setValue(0)
        self.setRange(0, 100)
        self._internal_value = 0
        self.current_value = 0
        self.maximum_value = 100
        self.progress.connect(self.setValue)
        self.maximum.connect(self.setMaximum)
        self.finished.connect(lambda: self.setValue(self.maximum_value))

    def increment_progress(self):
        self.current_value += 1
        if 100*(self.current_value - self._internal_value)/self.maximum_value >= 1:
            self._internal_value = self.current_value
            self.progress.emit(self._internal_value)
            
    def reset_progress(self):
        self.current_value = 0
        self._internal_value = 0
        self.progress.emit(0)

    def set_maximum_value(self, value):
        self.maximum_value = value
        self.maximum.emit(value)

    def signal_finished(self):
        self.finished.emit()



class GeWorker(QThread):
    finished = pyqtSignal()

    def __init__(self, task, progress_bar, **kwargs):
        super().__init__()
        self.task = task
        self.kwargs = kwargs
        self.progress_bar = progress_bar

    def run(self):
        try:
            self.task(progress_callback=self.progress_bar, **self.kwargs)
            self.finished.emit()
        except Exception as e:
            print(e)

    def on_finished(self, func):
        self.finished.connect(func)


class GeWindow(MainWindow):
    """A custom main window class for the GeViewer application.
    """
    file_name_changed = pyqtSignal(str)
    number_of_events = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        # initialize some class attributes
        self.default_header = 'No file loaded'
        self.current_file = []
        self.checkbox_mapping = {}
        self.events_list = []
        self.figure_size = [1920, 1440]

        # create the main window
        self.setWindowTitle('GeViewer')
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.splitter = QSplitter(Qt.Horizontal)

        # add panels, toolbar, and menu bar
        self.add_components_panel()
        self.add_viewer_panel()
        self.add_control_panel()
        self.add_menu_bar()
        self.splitter.setSizes([200, 800, 200])

        # Add the splitter to the layout
        self.main_layout.addWidget(self.splitter)
        self.showMaximized()
        self.number_of_events.connect(self.update_event_total)
        self.print_to_console('Welcome to GeViewer!')
        utils.check_for_updates()

    def add_components_panel(self):

        # create a layout for the components panel
        self.components_panel = QWidget()
        self.components_panel.setMinimumWidth(250)
        self.object_layout = QVBoxLayout(self.components_panel)

        # add a heading
        heading = QLabel('Components List')
        heading_font = QFont()
        heading_font.setPointSize(14)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        self.object_layout.addWidget(heading)

        # create the scroll area for the checkboxes
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.checkboxes_widget = QWidget()
        self.checkboxes_layout = QVBoxLayout(self.checkboxes_widget)
        self.checkboxes_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.checkboxes_widget)
        self.object_layout.addWidget(self.scroll_area)

        # add the components panel to the main layout
        self.splitter.addWidget(self.components_panel)

    def add_viewer_panel(self):

        # create a layout for the viewer panel
        self.viewer_panel = QWidget()
        self.viewer_panel.setMinimumWidth(500)
        self.viewer_panel.setMinimumHeight(500)
        self.viewer_layout = QVBoxLayout(self.viewer_panel)

        # add a heading that updates as files are loaded
        self.heading = QLabel('Viewing: ' + self.default_header)
        heading_font = QFont()
        heading_font.setPointSize(14)
        heading_font.setBold(True)
        self.heading.setFont(heading_font)
        self.file_name_changed.connect(self.update_header)
        self.viewer_layout.addWidget(self.heading)

        # create the viewer
        self.viewer = GeViewer(self.viewer_panel)
        self.plotter = self.viewer.plotter
        self.add_key_events()

        # add the toolbar
        self.add_toolbar()

        # add the plotter to the viewer layout
        self.viewer_layout.addWidget(self.plotter.interactor)

        # add the viewer panel to the main layout
        self.splitter.addWidget(self.viewer_panel)

    def add_control_panel(self):

        # create a layout for the control panel
        self.control_panel = QWidget()
        self.control_panel.setMinimumWidth(250)
        self.control_layout = QVBoxLayout(self.control_panel)

        # add a heading for the camera options
        heading = QLabel('Camera Options')
        heading_font = QFont()
        heading_font.setPointSize(14)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        self.control_layout.addWidget(heading)

        # add editable text box that show the camera position
        self.camera_position_layout = QHBoxLayout()
        self.camera_position_label = QLabel('Position (x, y, z):')
        self.camera_position_text = QLineEdit()
        self.camera_position_text.setMaximumWidth(250)
        self.camera_position_text.setReadOnly(False)
        self.camera_position_text.editingFinished.connect(self.handle_camera_position_change)
        self.camera_position_layout.addWidget(self.camera_position_label)
        self.camera_position_layout.addWidget(self.camera_position_text)
        self.control_layout.addLayout(self.camera_position_layout)

        # add editable text box that show the camera focal point
        self.camera_focal_layout = QHBoxLayout()
        self.camera_focal_label = QLabel('Focal Point (x, y, z):')
        self.camera_focal_text = QLineEdit()
        self.camera_focal_text.setMaximumWidth(250)
        self.camera_focal_text.setReadOnly(False)
        self.camera_focal_text.editingFinished.connect(self.handle_camera_focal_change)
        self.camera_focal_layout.addWidget(self.camera_focal_label)
        self.camera_focal_layout.addWidget(self.camera_focal_text)
        self.control_layout.addLayout(self.camera_focal_layout)

        # add editable text box that show the camera up vector
        self.camera_up_layout = QHBoxLayout()
        self.camera_up_label = QLabel('Up Vector (x, y, z):')
        self.camera_up_text = QLineEdit()
        self.camera_up_text.setMaximumWidth(250)
        self.camera_up_text.setReadOnly(False)
        self.camera_up_text.editingFinished.connect(self.handle_camera_up_change)
        self.camera_up_layout.addWidget(self.camera_up_label)
        self.camera_up_layout.addWidget(self.camera_up_text)
        self.control_layout.addLayout(self.camera_up_layout)

        # create a timer to update the boxes above with the new values
        self.update_timer = QTimer()
        self.update_timer.setInterval(200)
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.update_view_params)
        self.last_camera_position = None
        self.last_figure_size = None
        self.monitor_camera_position()

        # add a separator between the camera options and the figure options
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)
        self.control_layout.addWidget(line1)

        # add a heading for the figure options
        figure_heading = QLabel('Figure Options')
        figure_heading_font = QFont()
        figure_heading_font.setPointSize(14)
        figure_heading_font.setBold(True)
        figure_heading.setFont(figure_heading_font)
        self.control_layout.addWidget(figure_heading)

        # add an editable textbox to specify the figure size
        self.figure_size_layout = QHBoxLayout()
        self.figure_size_label = QLabel('Size [px] (width, height):')
        self.figure_size_text = QLineEdit()
        self.figure_size_text.setMaximumWidth(250)
        self.figure_size_text.setText('{}, {}'.format(*self.figure_size))
        self.figure_size_text.setReadOnly(False)
        self.figure_size_text.editingFinished.connect(self.handle_figure_size_change)
        self.figure_size_layout.addWidget(self.figure_size_label)
        self.figure_size_layout.addWidget(self.figure_size_text)
        self.control_layout.addLayout(self.figure_size_layout)

        # add a button to export the figure
        self.save_button_layout = QHBoxLayout()
        self.save_button = QPushButton('Export Figure', self)
        self.save_button.clicked.connect(self.save_file_dialog)
        self.save_button_layout.addWidget(self.save_button)
        self.control_layout.addLayout(self.save_button_layout)

        # add a separator between the figure options and the event viewer
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        self.control_layout.addWidget(line2)

        # add a heading for the event viewer
        heading = QLabel('Event Viewer')
        heading_font = QFont()
        heading_font.setPointSize(14)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        self.control_layout.addWidget(heading)

        # add a spin box to select the event number
        self.event_selection_layout = QHBoxLayout()
        self.event_selection_label = QLabel('Show event number:')
        self.event_selection_box = QSpinBox()
        self.event_selection_box.setMaximumWidth(250)
        self.event_selection_box.setRange(1, 1)
        self.event_selection_box.setValue(1)
        self.event_selection_box.setWrapping(True)

        # update the spin box as more events are loaded
        self.event_selection_box.valueChanged.connect(lambda: self.show_single_event(self.event_selection_box.value()))
        self.event_selection_layout.addWidget(self.event_selection_label)
        self.event_selection_layout.addWidget(self.event_selection_box)
        self.control_layout.addLayout(self.event_selection_layout)

        # add a separator between the event viewer and the geometry checker
        line3 = QFrame()
        line3.setFrameShape(QFrame.HLine)
        line3.setFrameShadow(QFrame.Sunken)
        self.control_layout.addWidget(line3)

        # add a heading for the geometry checker
        heading = QLabel('Geometry Checker')
        heading_font = QFont()
        heading_font.setPointSize(14)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        self.control_layout.addWidget(heading)

        # add a text box to specify the tolerance for overlap checking
        self.tolerance_label = QLabel('Tolerance:')
        self.tolerance_box = QLineEdit()
        self.tolerance_box.setMaximumWidth(250)
        double_validator = QDoubleValidator(1e-6, 1, 6)
        double_validator.setNotation(QDoubleValidator.StandardNotation)
        self.tolerance_box.setValidator(double_validator)
        self.tolerance_box.setText('0.001')
        self.intersection_layout_1 = QHBoxLayout()
        self.intersection_layout_1.addWidget(self.tolerance_label)
        self.intersection_layout_1.addWidget(self.tolerance_box)
        self.control_layout.addLayout(self.intersection_layout_1)

        # add a text box to specify the number of samples for overlap checking
        self.samples_label = QLabel('Number of Points:')
        self.samples_box = QLineEdit(self)
        self.samples_box.setMaximumWidth(250)
        int_validator = QIntValidator(1000, 10000000)
        self.samples_box.setValidator(int_validator)
        self.samples_box.setText('10000')
        self.intersection_layout_2 = QHBoxLayout()
        self.intersection_layout_2.addWidget(self.samples_label)
        self.intersection_layout_2.addWidget(self.samples_box)
        self.control_layout.addLayout(self.intersection_layout_2)

        # add a button to check for overlaps
        self.check_button = QPushButton('Find Overlaps')
        self.check_button.setMinimumWidth(120)
        self.check_button.clicked.connect(lambda: self.check_geometry(self.tolerance_box.text(),\
                                                                      self.samples_box.text()))
        self.clear_intersections_button = QPushButton('Clear Overlaps')
        self.clear_intersections_button.setMinimumWidth(120)
        self.clear_intersections_button.clicked.connect(self.clear_intersections)
        self.intersection_layout_3 = QHBoxLayout()
        self.intersection_layout_3.addWidget(self.check_button)
        self.intersection_layout_3.addWidget(self.clear_intersections_button)
        self.control_layout.addLayout(self.intersection_layout_3)

        # add a separator between the geometry checker and the console
        line4 = QFrame()
        line4.setFrameShape(QFrame.HLine)
        line4.setFrameShadow(QFrame.Sunken)
        self.control_layout.addWidget(line4)

        # add a heading for the console
        heading = QLabel('Console')
        heading_font = QFont()
        heading_font.setPointSize(14)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        self.control_layout.addWidget(heading)

        # add the console and redirect stdout and stderr to it
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        sys.stdout = GeConsoleRedirect(self.console)
        sys.stderr = GeConsoleRedirect(self.console)
        self.control_layout.addWidget(self.console)

        # add the progress bar
        self.progress_bar = GeProgressBar()
        self.control_layout.addWidget(self.progress_bar)

        # add the control panel to the main layout
        self.splitter.addWidget(self.control_panel)

    
    @pyqtSlot(str)
    def update_header(self, filename):
        if filename:
            self.current_file.append(filename)
            viewing = 'Viewing: ' + self.current_file[0] \
                    + ['',' + {} more'.format(len(self.current_file) - 1)][len(self.current_file) > 1]
        else:
            viewing = 'Viewing: ' + self.default_header
        self.heading.setText(viewing)


    @pyqtSlot(int)
    def update_event_total(self, total):
        self.event_selection_box.setRange(1, max(1, total))


    def generate_checkboxes(self, components, level):
        for comp in components:
            if comp['id'] not in self.checkbox_mapping:
                checkbox = QCheckBox(comp['name'])
                checkbox.setChecked(True)
                checkbox.stateChanged.connect(lambda state, comp=comp: self.toggle_visibility(state, comp))
                self.checkboxes_layout.addWidget(checkbox)
                checkbox.setStyleSheet(f"padding-left: {20 * level}px")
                self.checkbox_mapping[comp['id']] = checkbox
                self.progress_bar.increment_progress()
                if comp['is_event']:
                    self.events_list.append(comp['id'])
                if 'children' in comp and comp['children']:
                    self.generate_checkboxes(comp['children'], level + 1)
        self.number_of_events.emit(len(self.events_list))


    def show_single_event(self, event_index):
        for i, event in enumerate(self.events_list):
            if i == event_index - 1:
                self.checkbox_mapping[event].setChecked(True)
            else:
                self.checkbox_mapping[event].setChecked(False)
    

    def toggle_visibility(self, state, comp):
        try:
            visibility = state == Qt.Checked
            if comp['has_actor']:
                self.viewer.actors[comp['id']].SetVisibility(visibility)
            if 'children' in comp and comp['children']:
                for child in comp['children']:
                    self.set_visibility_recursive(child, visibility)
        except Exception as e:
            print(e)
    

    def set_visibility_recursive(self, comp, visibility):
        if comp['has_actor']:
            self.viewer.actors[comp['id']].SetVisibility(visibility)
        self.checkbox_mapping[comp['id']].setChecked(visibility)
        if 'children' in comp and comp['children']:
            for child in comp['children']:
                self.set_visibility_recursive(child, visibility)


    def set_camera_position(self, position):
        position = [float(x) for x in position.split(',')]
        self.plotter.camera.position = position
        self.plotter.update()


    def set_camera_focal(self, focal_point):
        focal_point = [float(x) for x in focal_point.split(',')]
        self.plotter.camera.focal_point = focal_point
        self.plotter.update()


    def set_camera_up(self, up_vector):
        up_vector = [float(x) for x in up_vector.split(',')]
        self.plotter.camera.up = up_vector
        self.plotter.update()


    def set_figure_size(self, figure_size):
        figure_size = [int(x) for x in figure_size.split(',')]
        try:
            self.figure_size = figure_size
        except Exception as e:
            print(e)


    def handle_camera_position_change(self):
        new_position = self.camera_position_text.text()
        if self.validate_camera_position(new_position):
            self.set_camera_position(new_position)
            self.clear_position_error_state()
        else:
            self.set_position_error_state()


    def handle_camera_focal_change(self):
        new_focal = self.camera_focal_text.text()
        if self.validate_camera_focal(new_focal):
            self.set_camera_focal(new_focal)
            self.clear_focal_error_state()
        else:
            self.set_focal_error_state()


    def handle_camera_up_change(self):
        new_up = self.camera_up_text.text()
        if self.validate_camera_up(new_up):
            self.set_camera_up(new_up)
            self.clear_up_error_state()
        else:
            self.set_up_error_state()


    def handle_figure_size_change(self):
        new_size = self.figure_size_text.text()
        if self.validate_figure_size(new_size):
            self.set_figure_size(new_size)
            self.clear_window_error_state()
        else:
            self.set_window_error_state()


    def validate_camera_position(self, position):
        try:
            position = [float(x) for x in position.split(',')]
            if len(position) != 3:
                raise ValueError('Invalid camera position')
            return True
        except ValueError:
            self.print_to_console('Error: invalid camera position. Please enter three comma-separated floats.')
            return False
        

    def validate_camera_focal(self, focal_point):
        try:
            focal_point = [float(x) for x in focal_point.split(',')]
            if len(focal_point) != 3:
                raise ValueError('Invalid camera focal point')
            return True
        except ValueError:
            self.print_to_console('Error: invalid camera focal point. Please enter three comma-separated floats.')
            return False
        
        
    def validate_camera_up(self, up_vector):
        try:
            up_vector = [float(x) for x in up_vector.split(',')]
            if len(up_vector) != 3:
                raise ValueError('Invalid camera up vector')
            return True
        except ValueError:
            self.print_to_console('Error: invalid camera up vector. Please enter three comma-separated floats.')
            return False
        
        
    def validate_figure_size(self, figure_size):
        try:
            figure_size = [int(x) for x in figure_size.split(',')]
            if len(figure_size) != 2:
                raise ValueError('Invalid figure size')
            return True
        except ValueError:
            self.print_to_console('Error: invalid figure size. Please enter two comma-separated integers.')
            return False


    def clear_position_error_state(self):
        self.camera_position_text.setPalette(QApplication.palette())


    def clear_focal_error_state(self):
        self.camera_focal_text.setPalette(QApplication.palette())


    def clear_up_error_state(self):
        self.camera_up_text.setPalette(QApplication.palette())


    def clear_window_error_state(self):
        self.figure_size_text.setPalette(QApplication.palette())


    def set_position_error_state(self):
        palette = self.camera_position_text.palette()
        palette.setColor(QPalette.Base, QColor(255, 192, 192))
        self.camera_position_text.setPalette(palette)


    def set_focal_error_state(self):
        palette = self.camera_focal_text.palette()
        palette.setColor(QPalette.Base, QColor(255, 192, 192))
        self.camera_focal_text.setPalette(palette)


    def set_up_error_state(self):
        palette = self.camera_up_text.palette()
        palette.setColor(QPalette.Base, QColor(255, 192, 192))
        self.camera_up_text.setPalette(palette)


    def set_window_error_state(self):
        palette = self.figure_size_text.palette()
        palette.setColor(QPalette.Base, QColor(255, 192, 192))
        self.figure_size_text.setPalette(palette)


    def update_menu_action(self, visible):
        self.show_controls_action.setChecked(visible)


    def monitor_camera_position(self):
        camera_position = self.plotter.camera_position
        if camera_position != self.last_camera_position:
            self.last_camera_position = camera_position
            self.update_timer.start()
        QTimer.singleShot(100, self.monitor_camera_position)


    def update_view_params(self):
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
        clear_console_action.triggered.connect(self.console.clear)
        copy_console_action = edit_menu.addAction('Copy Console')
        copy_console_action.triggered.connect(self.console.selectAll)
        copy_console_action.triggered.connect(self.console.copy)
        clear_action = edit_menu.addAction('Clear Meshes')
        clear_action.triggered.connect(self.clear_meshes)


        view_menu = menubar.addMenu('View')
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
        self.viewer.actors = {}
        self.events_list = []
        self.current_file = []
        self.file_name_changed.emit(None)


    def toggle_left_panel(self):
        if self.components_panel.isVisible():
            self.components_panel.hide()
        else:
            self.components_panel.show()


    def toggle_right_panel(self):
        if self.control_panel.isVisible():
            self.control_panel.hide()
        else:
            self.control_panel.show()


    def show_license(self):
        with open('LICENSE') as f:
            license_text = f.read().replace('\n\n', '<>').replace('\n', ' ').replace('<>', '\n\n')
        self.print_to_console('\nLICENSE:\n----------\n' + license_text)


    def add_toolbar(self):
        # Create a toolbar
        self.toolbar = QToolBar('Main Toolbar')
        self.viewer_layout.addWidget(self.toolbar)
        # self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.setMovable(True)

        self.toolbar.setStyleSheet('QToolButton {min-width: 80px; max-width: 80px;}')

        font = QFont()
        font.setPointSize(14)
        # Add actions to the toolbar

        self.wireframe_action = QAction('Wireframe', self)
        # self.wireframe_action.setFixedWidth(100)
        self.wireframe_action.setFont(font)
        self.wireframe_action.triggered.connect(self.toggle_wireframe)
        self.toolbar.addAction(self.wireframe_action)
        self.toolbar.addSeparator()

        self.transparent_action = QAction('Transparent', self)
        self.transparent_action.setFont(font)
        self.transparent_action.triggered.connect(self.toggle_transparent)
        self.toolbar.addAction(self.transparent_action)
        self.toolbar.addSeparator()

        self.parallel_action = QAction('Parallel', self)
        self.parallel_action.setFont(font)
        self.parallel_action.triggered.connect(self.toggle_parallel)
        self.toolbar.addAction(self.parallel_action)
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


    def toggle_parallel(self):
        self.viewer.toggle_parallel_projection()
        self.parallel_action.setText('Perspective' if self.viewer.parallel else 'Parallel')

    def toggle_wireframe(self):
        self.viewer.toggle_wireframe()
        self.update_wireframe_button()


    def toggle_transparent(self):
        self.viewer.toggle_transparent()
        self.transparent_action.setText('Opaque' if self.viewer.transparent else 'Transparent')


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
                try:
                    self.file_name_changed.emit(file_path)
                except Exception as e:
                    print(e)
                self.print_to_console('Loading file: ' + file_path)
                self.worker = GeWorker(self.viewer.load_files, self.progress_bar, filename=file_path, off_screen=True)
                self.worker.on_finished(self.add_components)
                self.worker.start()
            except Exception as e:
                print(e)


    def save_file_dialog(self):
        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog
        file_types = 'Supported File Types (*.png *.svg *.eps *.ps *.pdf *.tex);; '\
                     + 'PNG (*.png);;SVG (*.svg);;EPS (*.eps);;PS (*.ps);;PDF (*.pdf);;TEX (*.tex)'
        file_name, _ = QFileDialog.getSaveFileName(self, 'Save Figure', '', file_types, options=options)
        
        if file_name:
            try:
                self.save_figure(file_name, *self.figure_size)
                # self.plotter.screenshot(file_name)
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

            screenshot_extensions = ['png', 'jpeg', 'jpg', 'bmp', 'tif', 'tiff']
            if file_name.split('.')[-1] in screenshot_extensions:
                off_screen_plotter.screenshot(file_name)
            else:
                off_screen_plotter.save_graphic(file_name, title='GeViewer Figure')

            del off_screen_plotter
            print('Success: figure saved to ' + file_name)
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

    def print_to_console(self, text):
        print('[geviewer-prompt]: ' + text)

    
    def add_components(self):
        try:
            num_plotted = len(self.viewer.actors.keys())
            self.viewer.create_plotter(self.progress_bar)
            checkboxes_to_make = len(self.viewer.actors.keys()) - num_plotted
            self.progress_bar.reset_progress()
            self.progress_bar.set_maximum_value(checkboxes_to_make)
            self.generate_checkboxes(self.viewer.components, 0)
        except Exception as e:
            print(e)
        

    # def open_file(self):
    #     print('opening file')


    def save_file(self):
        options = QFileDialog.Options()
        file_types = 'GeViewer File (*.gev);; All Files (*)'
        file_name, _ = QFileDialog.getSaveFileName(self, 'Save File', 'viewer.gev', file_types, options=options)
        
        if file_name:
            try:
                self.viewer.save(file_name)
            except Exception as e:
                print(e)

    def close(self):
        print('closing application')


    def toggle_background(self):
        try:
            self.viewer.toggle_background()
            self.viewer.plotter.update()
        except Exception as e:
            print(e)

    def check_geometry(self, tolerance, samples):
        if tolerance:
           tolerance = float(tolerance)
        else:
            tolerance = 0.001
        if samples:
            samples = int(samples)
        else:
            samples = 10000
        try:
            self.viewer.find_intersections(tolerance, samples)
        except Exception as e:
            print(e)

    def clear_intersections(self):
        for actor in self.viewer.intersections:
            self.plotter.remove_actor(actor)



def launch_app():
    app = QApplication([])
    window = GeWindow()
    window.show()
    sys.exit(app.exec_())
