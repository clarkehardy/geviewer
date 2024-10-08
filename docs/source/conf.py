# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
import re
sys.path.insert(0, os.path.abspath('../../geviewer/src/'))
import pypandoc
import geviewer


# Produce some .rst files from README.md
sections = ['about', 'setup', 'usage', 'info']
lines = [[] for i in range(len(sections))]
section = 0
github_path = r'https://github.com/clarkehardy/geviewer/blob/.*?/docs/source/'
with open('../../README.md', 'r') as file:
    for i,line in enumerate(file):
        if i == 0:
            lines[0].append('## About\n')
            continue
        if section < len(sections) - 1 and sections[section + 1] in line.lower() \
        and line.startswith('#'):
            section += 1
        line = re.sub(github_path, '', line)
        line = re.sub(r'\?raw=true', '', line)
        lines[section].append(line)

for i,section in enumerate(sections):
    with open(section + '.md', 'w') as file:
        for line in lines[i]:
            file.write(line)

    # pypandoc.download_pandoc()
    pypandoc.convert_file(section + '.md', 'rst', outputfile=section + '.rst')
    os.remove(section + '.md')

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'GeViewer'
copyright = '2024, Clarke Hardy'
author = 'Clarke Hardy'
release = geviewer.__version__
version = geviewer.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc']

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = []
html_context = {
    'analytics-id': 'G-KMG1S5KJZC', # Google Analytics tracking ID
    'display_github': True, # Integrate GitHub
    'github_user': 'clarkehardy', # Username
    'github_repo': 'geviewer', # Repo name
    'github_version': 'main', # Version
    'display_version': True, # Display version
    'conf_py_path': '/docs/source/', # Path in the checkout to the docs root
}
