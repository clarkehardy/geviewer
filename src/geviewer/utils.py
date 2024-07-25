import numpy as np
import sys
import ast
import asyncio


def read_files(filenames):
    '''
    Read the content of the file.
    '''
    data = ''
    for filename in filenames:
        print('Reading mesh data from ' + filename + '...')
        with open(filename, 'r') as f:
            data += f.read()[:-15]
    return data


def clear_input_buffer():
    '''
    Clear the input buffer to avoid stray keystrokes influencing
    later inputs.
    '''
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
    '''
    Asyncronously get camera view input from the terminal.
    '''
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


async def prompt_for_file_path():
    '''
    Asynchronously get file path input from the terminal.
    '''
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
            break
        except ValueError:
            print('Error: invalid input. Please enter a valid file path.')
    return file_path


async def prompt_for_window_size():
    '''
    Asynchronously get window size input from the terminal.
    '''
    clear_input_buffer()
    while(True):
        try:
            print('Enter (width,height) in pixels as two comma-separated integers,')
            dims = await asyncio.to_thread(input, 'or press enter to cancel: ')
            if dims == '':
                return None, None
            dims = list(map(int, ast.literal_eval(dims)))
            break
        except ValueError:
            print('Error: invalid input. Please enter an integer.')
    width, height = dims
    return width, height


def orientation_transform(orientation):
    '''
    Get the up vector from the orientation. The orientation is of the form
    (x, y, z, theta) where (x, y, z) is the axis of rotation and theta is the
    angle of rotation. The rotation is applied to the default up vector (0, 1, 0).
    '''
    v = orientation[:3]
    v = np.array(v)/np.linalg.norm(v)
    theta = orientation[3]
    up = np.array((v[0]*v[1]*(1-np.cos(theta)) - v[2]*np.sin(theta),\
                   v[1]*v[1]*(1-np.cos(theta)) + np.cos(theta),\
                   v[1]*v[2]*(1-np.cos(theta)) + v[0]*np.sin(theta)))
    focus = -np.array((v[0]*v[2]*(1-np.cos(theta)) + v[1]*np.sin(theta),\
                       v[1]*v[2]*(1-np.cos(theta)) - v[0]*np.sin(theta),\
                       v[2]*v[2]*(1-np.cos(theta)) + np.cos(theta)))
    return up,focus
    