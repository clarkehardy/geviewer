import numpy as np
import sys
import os
import ast
import asyncio
from pathlib import Path


def read_files(filenames):
    """Reads the content of multiple files and concatenates it into a single string.

    :param filenames: A list of file paths to read.
    :type filenames: list of str
    :return: A single string containing the concatenated content of all the files.
    :rtype: str
    """
    data = ''
    for filename in filenames:
        print('Reading data from ' + str(Path(filename).resolve())+ '...')
        with open(filename, 'r') as f:
            data += f.read()
    return data


def clear_input_buffer():
    """Clears the input buffer to prevent stray keystrokes from influencing
    subsequent inputs.

    :return: None
    """
    try:
        # if on Unix
        import termios
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except ImportError:
        # if on Windows
        import msvcrt
        while msvcrt.kbhit():
            msvcrt.getch()


async def prompt_for_camera_view():
    """Asynchronously prompts the user for camera view input from the terminal.

    This function prompts the user to enter the camera's position, focal point, and
    up vector. Each input is expected to be a set of three comma-separated numbers.
    The function uses asynchronous input handling to avoid blocking other operations.

    :return: A tuple containing the position, up vector, and focal point. Each
        value is a list of three floating-point numbers or `None` if the user
        skips the input.
    :rtype: tuple
    """
    print('Setting the camera position and orientation.')
    print('Press enter to skip any of the following prompts.')
    clear_input_buffer()
    while(True):
        try:
            position = await asyncio.to_thread(input, 'Enter the position as three comma-separated numbers: ')
            if position == '':
                position = None
                break
            position = list(map(float, ast.literal_eval(position)))
            if len(position) != 3:
                raise ValueError
            break
        except ValueError:
            print('Error: invalid input. Please enter three numbers separated by commas.')
    while(True):
        try:
            focus = await asyncio.to_thread(input, 'Enter the focal point as three comma-separated numbers: ')
            if focus == '':
                focus = None
                break
            focus = list(map(float, ast.literal_eval(focus)))
            if len(focus) != 3:
                raise ValueError
            break
        except ValueError:
            print('Error: invalid input. Please enter three numbers separated by commas.')
    while(True):
        try:
            up = await asyncio.to_thread(input, 'Enter the up vector as three comma-separated numbers: ')
            if up == '':
                up = None
                break
            up = list(map(float, ast.literal_eval(up)))
            if len(up) != 3:
                raise ValueError
            break
        except ValueError:
            print('Error: invalid input. Please enter three numbers separated by commas.')
    return position, up, focus


async def prompt_for_screenshot_path():
    """Asynchronously prompts the user for a file path to save a screenshot.

    This function prompts the user to enter a file path where the screenshot will be saved.
    The accepted file formats are `.png`, `.svg`, `.eps`, `.ps`, `.pdf`, and `.tex`. The 
    function uses asynchronous input handling to avoid blocking other operations.

    :return: The file path as a string if a valid path is provided, or `None` if
        the input is canceled.
    :rtype: str or None
    """
    clear_input_buffer()
    print('Enter the destination file path to save the screenshot,')
    print('or press enter to cancel.')
    print('Accepted formats are .png, .svg, .eps, .ps, .pdf, and .tex.')
    while(True):
        try:
            file_path = await asyncio.to_thread(input,'Save as (e.g. /path/to/file.png): ')
            if file_path == '':
                return None
            if not file_path.endswith(('.png', '.svg', '.eps', '.ps', '.pdf', '.tex')):
                raise ValueError
            if not os.path.isdir('/'.join(str(Path(file_path).resolve()).split('/')[:-1])):
                raise ValueError
            break
        except ValueError:
            print('Error: invalid input. Please enter a valid file path.')
    return file_path


async def prompt_for_window_size():
    """Asynchronously prompts the user for the window size.

    This function prompts the user to enter the window size in pixels as two
    comma-separated integers, representing width and height. The function uses
    asynchronous input handling to avoid blocking other operations.

    :return: A tuple containing the width and height as integers if valid input is provided,
        or `(None, None)` if the input is canceled.
    :rtype: tuple of (int, int) or (None, None)
    """
    clear_input_buffer()
    while(True):
        try:
            print('Enter (width,height) in pixels as two comma-separated integers,')
            dims = await asyncio.to_thread(input, 'or press enter to cancel: ')
            if dims == '':
                return None, None
            dims = list(map(int, ast.literal_eval(dims)))
            width, height = dims
            return width, height
        except ValueError:
            print('Error: invalid input. Please enter an integer.')


def prompt_for_file_path():
    """Prompts the user for a file path to save the session.

    This function asks the user to enter a file path where the session should be saved.
    The file path should end with the `.gev` extension to ensure compatibility with
    GeViewer for later loading of the session.

    :return: The file path as a string if valid input is provided, or `None` if the
        input is canceled.
    :rtype: str or None
    """
    clear_input_buffer()
    print('Enter the destination file path to save the session,')
    print('or press enter to cancel. Use the file extension .gev')
    print('so GeViewer can load the session later.')
    while(True):
        try:
            file_path = input('Save as (e.g. /path/to/file.gev): ')
            if file_path == '':
                return None
            if not file_path.endswith('.gev'):
                raise ValueError
            if not os.path.isdir('/'.join(str(Path(file_path).resolve()).split('/')[:-1])):
                raise ValueError
            print()
            return file_path
        except ValueError:
            print('Error: invalid input. Please enter a valid file path')
            print('ending in .gev')


def prompt_for_save_session(total_meshes):
    """Prompts the user to decide whether to save the session before loading
    a large file.

    This function warns the user if the file they are attempting to view is large,
    based on the number of meshes (`total_meshes`). The user is given the option
    to save the current session to avoid reloading the file in the future.

    :param total_meshes: The number of meshes in the large file being loaded.
    :type total_meshes: int
    :return: A boolean indicating whether the session will be saved.
    :rtype: bool
    """
    clear_input_buffer()
    print('\nWarning: the file you are attempting to view is large')
    print('({} meshes) and may take a while to load. Do you want to save'.format(total_meshes))
    print('the session after loading to avoid having to reload it later?')
    while(True):
        try:
            save_input = input('Enter "y" or "n": ')
            if save_input.lower() not in ['y', 'n']:
                raise ValueError
            save_session = save_input.lower() == 'y'
            print('This session will ' + ['not ', ''][save_session] + 'be saved.')
            print('(To save the session by default, use the --destination flag.')
            print('To avoid this warning, use the --no-warnings flag.)\n')
            return save_session
        except ValueError:
            print('Error: invalid input. Please enter "y" or "n".')


async def prompt_for_html_path():
    """Asynchronously prompts the user to input a file path for saving an HTML file.

    This function prompts the user to enter a destination file path to save the viewer
    as an interactive HTML file.

    :return: The file path provided by the user if valid, or `None` if the user presses
        enter to cancel.
    :rtype: str or None
    """
    clear_input_buffer()
    print('Enter the destination file path to save the HTML file,')
    print('or press enter to cancel. Use the file extension .html')
    print('to save the viewer as an interactive HTML file.')
    while(True):
        try:
            file_path = await asyncio.to_thread(input, 'Save as (e.g. /path/to/file.html): ')
            if file_path == '':
                return None
            if not file_path.endswith('.html'):
                raise ValueError
            if not os.path.isdir('/'.join(str(Path(file_path).resolve()).split('/')[:-1])):
                raise ValueError
            return file_path
        except ValueError:
            print('Error: invalid input. Please enter a valid file path')
            print('ending in .html')


def orientation_transform(orientation):
    """Calculate the up and focus vectors based on the orientation.

    The function takes an orientation specified as a tuple or list `(x, y, z, theta)`,
    where `(x, y, z)` is the axis of rotation and `theta` is the angle of rotation in
    radians. It applies this rotation to the default up vector `(0, 1, 0)` and the
    default focus vector `(0, 0, -1)` to compute the new up and focus vectors.

    :param orientation: A tuple or list containing the axis of rotation and angle of rotation.
        The format is (x, y, z, theta), where (x, y, z) is the axis and theta is the rotation
        angle in radians.
    :type orientation: tuple or list of floats

    :return: A tuple containing the transformed up vector and the transformed focus vector.
    :rtype: tuple of (numpy.ndarray, numpy.ndarray)
    """
    v = orientation[:3]
    v = np.array(v)/np.linalg.norm(v)
    theta = orientation[3]
    up = np.array((v[0]*v[1]*(1-np.cos(theta)) - v[2]*np.sin(theta),\
                   v[1]*v[1]*(1-np.cos(theta)) + np.cos(theta),\
                   v[1]*v[2]*(1-np.cos(theta)) + v[0]*np.sin(theta)))
    focus = -np.array((v[0]*v[2]*(1-np.cos(theta)) + v[1]*np.sin(theta),\
                       v[1]*v[2]*(1-np.cos(theta)) - v[0]*np.sin(theta),\
                       v[2]*v[2]*(1-np.cos(theta)) + np.cos(theta)))
    return up, focus
    