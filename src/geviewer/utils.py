import io
from pathlib import Path
from PyQt6.QtWidgets import QTextEdit, QProgressBar
from PyQt6.QtGui import QTextCharFormat, QColor, QFont, QTextCursor
from PyQt6.QtCore import QDateTime, pyqtSignal, QThread
import re


class ConsoleRedirect(io.StringIO):
    """Redirects stdout and stderr to a QTextEdit widget.
    """
    def __init__(self, text_edit):
        """Initializes the console redirect.

        :param text_edit: The text edit widget to redirect to.
        :type text_edit: QTextEdit
        """
        super().__init__()
        self.text_edit = text_edit
        self.warning_format = QTextCharFormat()
        self.warning_format.setForeground(QColor('orange'))
        self.warning_format.setFontWeight(QFont.Bold)
        self.error_format = QTextCharFormat()
        self.error_format.setForeground(QColor('red'))
        self.error_format.setFontWeight(QFont.Bold)

    def write(self, text):
        """Writes to the console.

        This method writes to the console by inserting the text into the text
        edit widget and moving the cursor to the end.

        :param text: The text to write to the console.
        :type text: str
        """
        self.text_edit.moveCursor(QTextCursor.End)
        text = self.stylize_text(text)
        self.text_edit.insertHtml(text)
        self.text_edit.moveCursor(QTextCursor.End)
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
        return text

    def flush(self):
        pass

    
class ProgressBar(QProgressBar):
    """A custom progress bar class for the GeViewer application.
    """
    progress = pyqtSignal(int)
    maximum = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self):
        """Initializes the progress bar.
        """
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
        """Increments the progress bar by 1%.
        """
        self.current_value += 1
        if 100*(self.current_value - self._internal_value)/self.maximum_value >= 1:
            self._internal_value = self.current_value
            self.progress.emit(self._internal_value)
            
    def reset_progress(self):
        """Resets the progress bar to 0%.
        """
        self.current_value = 0
        self._internal_value = 0
        self.progress.emit(0)

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
        self.finished.emit()
        

class Worker(QThread):
    """A custom worker class for the GeViewer application.
    """
    finished = pyqtSignal()
    def __init__(self, task, progress_bar, **kwargs):
        """Initializes the worker.
        """
        super().__init__()
        self.task = task
        self.kwargs = kwargs
        self.progress_bar = progress_bar

    def run(self):
        """Runs the worker.
        """
        try:
            self.task(progress_callback=self.progress_bar, **self.kwargs)
            self.finished.emit()
        except Exception as e:
            print(e)

    def on_finished(self, func):
        """Connects a function to the finished signal.

        :param func: The function to connect to the finished signal.
        :type func: function
        """
        self.finished.connect(func)


def read_file(filename):
    """Reads the content of multiple files and concatenates it into a single string.

    :param filenames: A list of file paths to read.
    :type filenames: list of str
    :return: A single string containing the concatenated content of all the files.
    :rtype: str
    """
    print('Reading data from ' + str(Path(filename).resolve())+ '...')
    data = []
    with open(filename, 'r') as f:
        for line in f:
            # don't read comments
            if not line.strip().startswith('#'):
                data.append(line)
    data = ''.join(data)
    return data


def check_for_updates():
    """Determines whether the user is using the latest version of GeViewer.
    If not, prints a message to the console to inform the user.
    """
    try:
        import json
        from urllib import request
        import geviewer
        from packaging.version import parse
        url = 'https://pypi.python.org/pypi/geviewer/json'
        releases = json.loads(request.urlopen(url).read())['releases']
        versions = list(releases.keys())
        parsed = [parse(v) for v in versions]
        latest = parsed[parsed.index(max(parsed))]
        current = parse(geviewer.__version__)
        if current < latest and not (latest.is_prerelease or latest.is_postrelease or latest.is_devrelease):
            print('You are using GeViewer version {}. The latest version is {}.'.format(current, latest))
            print('Use "pip install --upgrade geviewer" to update to the latest version.\n')
    except:
        # don't want this to interrupt regular use if there's a problem
        return