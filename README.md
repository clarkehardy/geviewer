# GeViewer
A lightweight, Python-based visualization tool for Geant4. GeViewer provides a convenient way to view detector geometries, particle trajectories, and hits, with smooth rendering in an interactive window.

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
This package is intended to be used primarily as a command line tool. Following installation, the program can be run using:
```bash
geviewer /path/to/file.wrl
```
This will load the meshes described in `/path/to/file.wrl` and display them in an interactive window. The viewing perspective can be changed by clicking, dragging, and scrolling in the window, while other options can be toggled on and off using key presses. More specific instructions for use will print in the terminal window when the program is launched.

###  Instructions for Geant4
To produce Geant4 outputs that can be read by GeViewer, you must use `/vis/open VRML2FILE` to tell Geant4 to save the visualization as a VRML file. The following sample macro shows how this could be implemented.
```
# tell Geant4 we want a VRML file rather than to use an interactive viewer
/vis/open VRML2FILE

# the main content of your Geant4 macro goes here

# if you want to see particle tracks and hits
/run/beamOn 1

# by default, the file will be saved as g4_00.wrl
# but it can easily be renamed from within the macro
/control/shell mv g4_00.wrl /new/path/to/file.wrl

# the output can be piped directly to geviewer
/control/shell geviewer /new/path/to/file.wrl

exit
```
Note that if you are running Geant4 on a remote machine over `ssh`, piping the simulation outputs directly to GeViewer may not work as expected. If this is the case, you can download the VRML files and run GeViewer on your local machine instead.


### Safe mode
By default, GeViewer relies on its own VRML parser to extract the meshes to be plotted, however this has only been tested on a small sample set of Geant4 simulation results. If you encounter file parsing errors, try using the `--safe-mode` command line argument (and let me know what caused the error so I can update the parser). This will use a VRML parsing tool from [`vtk`](https://vtk.org) which should be more robust, but which does not allow the program to distinguish trajectories, hits, and detector geometry. In this mode, some features will not be available.

## License
Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

## Contact
Clarke Hardy - [cahardy@stanford.edu](mailto:cahardy@stanford.edu)
