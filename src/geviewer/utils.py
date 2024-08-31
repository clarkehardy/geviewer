import os
from pathlib import Path


def check_files(files):
    """Checks if the file paths are valid.
    """
    for file in files:
        file = str(Path(file).resolve())
        if not os.path.exists(file):
            print('Error: {} does not exist'.format(file))
            return False
        if not (file.endswith('.gev') or file.endswith('.heprep') or file.endswith('.wrl')):
            print('Error: {} is not a valid file'.format(file))
            print('Valid file types are .gev, .heprep, and .wrl')
            return False
    return True


def check_for_updates():
    """Determines whether the user is using the latest version of GeViewer.
    If not, prints a message to the console to inform the user.
    """
    try:
        import json
        from urllib import request
        import geviewer
        from packaging.version import parse
        url = 'https://pypi.python.org/pypi/geviewer/json'
        releases = json.loads(request.urlopen(url).read())['releases']
        versions = list(releases.keys())
        parsed = [parse(v) for v in versions]
        latest = parsed[parsed.index(max(parsed))]
        current = parse(geviewer.__version__)
        if current < latest and not (latest.is_prerelease or latest.is_postrelease or latest.is_devrelease):
            msg = 'You are using GeViewer version {}. The latest version is {}. '.format(current, latest)
            msg += 'Use "pip install --upgrade geviewer" to update to the latest version.'
            return msg
        return
    except:
        # don't want this to interrupt regular use if there's a problem
        return


def get_license():
    """Gets the LICENSE file from the distribution.
    """
    try:
        from importlib import metadata
        dist = metadata.distribution('geviewer')
        license_file = [f for f in dist.files if f.name.upper() == 'LICENSE'][0]
        with license_file.locate().open('r') as f:
            license_raw = f.read()
        return license_raw
    except:
        return 'Error: license file not found. Try a clean install of GeViewer.'


def print_banner():
    """Prints the banner to the terminal.
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