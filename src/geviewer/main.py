from geviewer.geviewer import GeViewer
import argparse


def print_instructions():
    """Prints the banner and instructions for the user.
    """
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
    print('* Press "w" to toggle between wireframe and solid modes')
    print('* Press "v" to switch to an isometric view')
    print('* Press "d" to set the display window size')
    print('* Press "i" to set the camera viewpoint')
    print('* Press "p" to print the current display settings')
    print('* Press "h" to export the viewer to an HTML file')
    print('* Press "q" to quit the viewer')
    print()


def main():
    """Command line interface for GeViewer.

    This function sets up the command-line interface for running the GeViewer application.
    It uses the argparse module to parse command-line arguments, allowing users to specify
    the files to be displayed and various options for running the viewer. 

    Command-line options include:
    - `filenames`: The file or list of files to be displayed. This argument is required.
    - `-d` or `--destination`: Optional argument specifying the path to save the session.
    If provided without a value, the default filename is 'viewer.gev'.
    - `-o` or `--off-screen`: Optional flag to run the viewer in offscreen mode.
    - `-s` or `--safe-mode`: Optional flag to enable a more robust VRML parsing mode at
    the expense of some interactive features.
    - `-w` or `--no-warnings`: Optional flag to suppress warnings and prevent the program
    from pausing to display them.
    """
    print_instructions()

    parser = argparse.ArgumentParser(description='View Geant4 simulation results.')
    parser.add_argument('filenames', nargs='+', help='the file or list of files to be displayed')
    parser.add_argument('-d', '--destination', nargs='?', help='save the session to this location', \
                        default=None, const='viewer.gev')
    parser.add_argument('-o', '--off-screen', help='run in offscreen mode.', action='store_true')
    parser.add_argument('-s', '--safe-mode', help='use more robust VRML parsing ' \
                        + 'at the expense of some interactive features', action='store_true')
    parser.add_argument('-w', '--no-warnings', help='do not pause the program to display warnings', \
                        action='store_true')
    args = parser.parse_args()
    filenames = args.filenames
    destination = args.destination
    off_screen = args.off_screen
    safe_mode = args.safe_mode
    no_warnings = args.no_warnings

    GeViewer(filenames, destination=destination, off_screen=off_screen,\
             safe_mode=safe_mode, no_warnings=no_warnings)


if __name__ == '__main__':
    main()
