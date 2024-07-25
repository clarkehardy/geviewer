# GeViewer
![PyPI - Version](https://img.shields.io/pypi/v/geviewer)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/clarkehardy/geviewer/.github%2Fworkflows%2Fpython-package.yml)
![Last Commit](https://img.shields.io/github/last-commit/clarkehardy/geviewer)
![GitHub License](https://img.shields.io/github/license/clarkehardy/geviewer)

A lightweight, Python-based visualization tool for Geant4. GeViewer provides a convenient way to view detector geometries and particle trajectories, with smooth rendering in an interactive window.

## Features
* 🔬 **Physics visualization:** See color-coded particle trajectories in a 3D rendering of the detector

* 🕹️ **Intuitive controls:** Use your mouse to rotate, zoom, and pan to explore the geometry

* 🎨 **Customizable rendering:** Toggle through different viewing options with simple keystroke commands

* ✨ **High-quality graphics:** Produce publication-quality visuals of detectors and events

* 🚀 **Smooth & fast:** Efficient handling of large and complex detector geometries

## Getting started
### Dependencies
The following packages are required:
* `numpy`
* `tqdm`
* `pyvista`

### Installation
GeViewer can be installed using `pip` as follows:
```bash
pip install geviewer
```
To uninstall:
```bash
pip uninstall geviewer
```

## Usage
This package is intended to be used primarily as a command line tool. To run the program, you must have already produced one or more [VRML files](https://en.wikipedia.org/wiki/VRML) from Geant4 simulations. See the section below for instructions on what to put in your Geant4 macro. Following installation, the program can be run using:
```bash
geviewer /path/to/file1.wrl
```
This will load the meshes described in `/path/to/file.wrl` and display them in an interactive window. To view multiple files at once, simply provide multiple paths when launching the program. The viewing perspective can be changed by clicking, dragging, and scrolling in the window, while other functions can be activated using keystrokes. More specific instructions for use will print in the terminal window when the program is launched.

###  Instructions for Geant4
To produce Geant4 outputs that can be read by GeViewer, you must use `/vis/open VRML2FILE` to tell Geant4 to save the visualization as a VRML file. The following macro snippet shows how this could be implemented, along with some other options.
```
# tell Geant4 we want a VRML file rather than to use an interactive viewer
# this line should come BEFORE the /run/beamOn command
/vis/open VRML2FILE

# now ensure that the geometry is displayed
/vis/drawVolume

# add the trajectories
/vis/scene/add/trajectories

# add the step markers
/vis/modeling/trajectories/create/drawByParticleID
/vis/modeling/trajectories/drawByParticleID-0/default/setDrawStepPts true

# ensure that they are not cleared at the end of the event
/vis/scene/endOfEventAction accumulate

# you can also apply other commands here to control other
# aspects of how the geometry and events will be displayed

# the main content of your Geant4 macro goes here

# specify the number of events and start the simulation
/run/beamOn 1

# by default, the file will be saved as g4_00.wrl
# but it can easily be renamed from within the macro
/control/shell mv g4_00.wrl /new/path/to/file.wrl

# if you are running on your local computer, the
# VRML file can be piped directly to GeViewer
/control/shell geviewer /new/path/to/file.wrl

exit
```
For more information on how to construct a macro, refer to the [Geant4 documentation](https://geant4.web.cern.ch/docs/). Note that if you are running Geant4 on a remote machine over `ssh`, you will have to download the VRML files to view on your local computer, as GeViewer does not work over X11 forwarding.

### Safe mode
By default, GeViewer relies on its own VRML parser to extract the meshes to be plotted, however this has only been tested on a small sample set of Geant4 simulation results. If you encounter file parsing errors, try using the `--safe-mode` command line argument (and create an issue to report the problem). This will use a VRML parsing tool from [`vtk`](https://vtk.org) which should be more robust, but which does not allow the program to distinguish trajectories, step markers, and detector components. In this mode, some features will not be available.

## License
Distributed under the MIT License. See [LICENSE](https://github.com/clarkehardy/geviewer/blob/main/LICENSE) for more information.

## Contact
Clarke Hardy - [cahardy@stanford.edu](mailto:cahardy@stanford.edu)
