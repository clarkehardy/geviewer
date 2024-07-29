# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
sys.path.insert(0, os.path.abspath('../../geviewer/src/'))
import pypandoc
import git

# Produce a README.rst file from the README.md file
lines = []
with open('../../README.md', 'r') as file:
    for i,line in enumerate(file):
        if i==0:
            line = '# About ' + line[1:]
        if i>1:
            if line.startswith('#'):
                line = line[1:]
        lines.append(line)

with open('temp_readme.md', 'w') as file:
    for line in lines:
        file.write(line)

pypandoc.convert_file('temp_readme.md', 'rst', outputfile='README.rst')
os.remove('temp_readme.md')

# Get the version from the latest git tag
repo = git.Repo('../../../geviewer')
tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
latest_tag = str(tags[-1])

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'GeViewer'
copyright = '2024, Clarke Hardy'
author = 'Clarke Hardy'
release = latest_tag

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc']

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
