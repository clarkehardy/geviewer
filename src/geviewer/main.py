from geviewer.geviewer import GeViewer
import argparse


def print_instructions():
    '''
    Print the instructions for the user.
    '''
    print()
    print('###################################################')
    print('#    _____   __      ___                          #')
    print('#   / ____|  \\ \\    / (_)                         #')
    print('#  | |  __  __\\ \\  / / _  _____      _____ _ __   #')
    print('#  | | |_ |/ _ \\ \\/ / | |/ _ \\ \\ /\\ / / _ \\  __|  #')
    print('#  | |__| |  __/\\  /  | |  __/\\ V  V /  __/ |     #')
    print('#   \\_____|\\___| \\/   |_|\\___| \\_/\\_/ \\___|_|     #')
    print('#                                                 #')
    print('###################################################')
    print()
    print('Instructions:')
    print('-------------')
    print('* Click and drag to rotate the view, shift + click')
    print('  and drag to pan, and scroll to zoom')
    print('* Press "c" to capture a screenshot of the current view')
    print('* Press "g" to save a vector graphic of the current view')
    print('* Press "t" to toggle the tracks on or off')
    print('* Press "h" to toggle the hits on or off')
    print('* Press "b" to toggle the background on or off')
    print('* Press "w" to switch to a wireframe rendering mode')
    print('* Press "s" to switch to a solid rendering mode')
    print('* Press "v" to switch to the default viewpoint')
    print('* Press "q" or "e" to quit the viewer')
    print()


def main():
    '''
    Command line interface for GeViewer.
    '''
    print_instructions()

    parser = argparse.ArgumentParser(description='View Geant4 simulation results.')
    parser.add_argument('filename', help='The VRML file to be displayed.')
    parser.add_argument('--safe-mode', help='Option to get more robust VRML parsing ' \
                          + 'at the expense of some interactive features.',action='store_true')
    args = parser.parse_args()
    filename = args.filename
    safe_mode = args.safe_mode

    gev = GeViewer(filename, safe_mode)
    gev.show()


if __name__ == '__main__':
    main()
