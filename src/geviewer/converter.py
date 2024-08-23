import sys
import os
import argparse
from tqdm import tqdm
from pathlib import Path
from geviewer.utils import check_files, print_banner
from geviewer.viewer import GeViewer

class ProgressBar:
    def __init__(self):
        self.pbar = None
        self.total = 0

    def reset_progress(self):
        self.pbar = None
        self.total = 0

    def increment_progress(self):
        if self.pbar is None and self.total > 0:
            self.pbar = tqdm(total=self.total)
        if self.pbar is not None:
            if self.pbar.n + 1 < self.total:
                self.pbar.update(1)

    def set_maximum_value(self, value):
        self.total = value

    def signal_finished(self):
        if self.pbar is not None:
            self.pbar.n = self.total
            self.pbar = None
            print()

    def print_update(self, text):
        print(text)


def main():
    """Converts the file to .gev format and saves it to the 
    specified destination.
    """
    parser = argparse.ArgumentParser(
        description = 'gev-converter is a command-line utility for GeViewer.',
        epilog = 'For more information, visit https://geviewer.readthedocs.io/en/latest/'
    )
    parser.add_argument('file', help='The file to convert.')
    parser.add_argument('destination', help='The destination to save the converted file to.')
    args = parser.parse_args()

    print_banner()
    file = str(Path(args.file).resolve())
    destination = str(Path(args.destination).resolve())

    if check_files([file]):

        print('Converting {} to {}\n'.format(file, destination))

        dest_dir = os.path.dirname(destination)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        if not destination.lower().endswith('.gev'):
            destination += '.gev'
        
        viewer = GeViewer()
        viewer.load_file(file, progress_obj=ProgressBar())
        viewer.save_session(destination)

        print('Success: file saved to {}'.format(destination))
    else:
        print('Error: failed to convert {}'.format(file))


if __name__ == '__main__':
    main()