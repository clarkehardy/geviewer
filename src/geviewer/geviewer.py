import os
import argparse
from pathlib import Path
from geviewer.gui import launch_app
from geviewer.utils import check_files


def main():
    """The main command-line entry point for GeViewer.
    """
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
