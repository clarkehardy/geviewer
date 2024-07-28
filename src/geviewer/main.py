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
    print('  and drag to pan,  ctrl + click and drag to roll,')
    print('  and scroll to zoom')
    print('* Press "c" to capture a screenshot of the current view')
    print('* Press "t" to toggle the trajectories on or off')
    print('* Press "m" to toggle the step markers on or off')
    print('* Press "b" to toggle the background on or off')
    print('* Press "w" to switch to a wireframe rendering mode')
    print('* Press "s" to switch to a solid rendering mode')
    print('* Press "v" to reset to the default viewpoint')
    print('* Press "d" to set the display window size')
    print('* Press "o" to set the camera viewpoint')
    print('* Press "p" to print the current display settings')
    print('* Press "h" to export the viewer to an HTML file')
    print('* Press "q" or "e" to quit the viewer')
    print()


def main():
    '''
    Command line interface for GeViewer.
    '''
    print_instructions()

    parser = argparse.ArgumentParser(description='View Geant4 simulation results.')
    parser.add_argument('filenames', nargs='+', help='The VRML file to be displayed.')
    parser.add_argument('-d', '--destination', nargs='?', help='The location where the session' \
                        + ' will be saved.', default=None, const='viewer.gev')
    parser.add_argument('-o', '--off-screen', help='Option to run in off-screen mode.', action='store_true')
    parser.add_argument('-s', '--safe-mode', help='Option to use more robust VRML parsing ' \
                        + 'at the expense of some interactive features.', action='store_true')
    parser.add_argument('-w', '--ignore-warnings', help='Option to ignore warnings.', action='store_true')
    args = parser.parse_args()
    filenames = args.filenames
    destination = args.destination
    off_screen = args.off_screen
    safe_mode = args.safe_mode
    ignore_warnings = args.ignore_warnings

    GeViewer(filenames, destination=destination, off_screen=off_screen,\
             safe_mode=safe_mode, ignore_warnings=ignore_warnings)


if __name__ == '__main__':
    main()
