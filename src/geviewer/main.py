import os
import argparse
from geviewer.gui import launch_app


def check_files(files):
    """Check if the files are valid.
    """
    for file in files:
        if not os.path.exists(file):
            print('Error: {} does not exist'.format(file))
            return False
        if not (file.endswith('.gev') or file.endswith('.heprep') or file.endswith('.wrl')):
            print('Error: {} is not a valid file'.format(file))
            print('Valid file types are .gev, .heprep, and .wrl')
            return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description = 'GeViewer is a lightweight, Python-based visualization tool for Geant4.',
        epilog = 'For more information, visit https://geviewer.readthedocs.io/en/latest/'
    )
    parser.add_argument('files', nargs='*', help='Files to load on startup')
    args = parser.parse_args()

    if check_files(args.files):
        launch_app(args.files)
    

if __name__ == '__main__':
    main()
