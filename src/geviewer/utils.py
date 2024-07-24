import sys


def read_file(filename):
    '''
    Read the content of the file.
    '''
    print('Reading mesh data from ' + filename + '...')
    with open(filename, 'r') as f:
        data = f.read()
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