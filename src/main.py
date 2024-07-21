from geviewer import GeViewer
import argparse

def main():
    '''
    Command line interface for GeViewer.
    '''
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
