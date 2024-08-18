from pathlib import Path


def read_file(filename):
    """Reads the content of a file.

    :param filename: The path to the file to read.
    :type filename: str
    :return: A single string containing the content of the file.
    :rtype: str
    """
    print('Reading data from ' + str(Path(filename).resolve())+ '...')
    data = []
    with open(filename, 'r') as f:
        for line in f:
            # don't read comments
            if not line.strip().startswith('#'):
                data.append(line)
    data = ''.join(data)
    return data


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