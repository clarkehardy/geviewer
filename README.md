# GeViewer
![PyPI - Version](https://img.shields.io/pypi/v/geviewer)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/clarkehardy/geviewer/.github%2Fworkflows%2Fpython-package.yml)
![Last Commit](https://img.shields.io/github/last-commit/clarkehardy/geviewer)
![GitHub License](https://img.shields.io/github/license/clarkehardy/geviewer)

A lightweight, Python-based visualization tool for Geant4. GeViewer provides a convenient way to view detector geometries and particle trajectories, with smooth rendering in an interactive window.

### Features

* **Physics-focused visuals:** See color-coded particle trajectories in a 3D-rendered detector

* **Intuitive controls:** Use your mouse to rotate, zoom, pan, and interact with the geomery

* **Customizable viewing:** Toggle through different viewing options with simple key commands

* **High-quality graphics:** Produce publication-quality visuals of detectors and events

* **Fast performance:** Enjoy smooth, responsive rendering even with large and complex detector geometries

## Setup
### Dependencies
The following packages are required:

* `numpy`

* `tqdm`

* `pyvista`

* `nest_asyncio`

* `trame`

* `trame_vuetify`

* `trame_vtk`

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
### Quick start
GeViewer is intended to be used primarily as a command line tool. To run the program, you should have already produced one or more [VRML files](https://en.wikipedia.org/wiki/VRML) from Geant4 simulations. See the section below for instructions on what to put in your Geant4 macro. If you already have a VRML file, you can view it using:
```bash
geviewer /path/to/file.wrl
```
This will load the meshes described in `/path/to/file.wrl` and display them in an interactive window. The viewing perspective can be changed by clicking, dragging, and scrolling in the window, while other functions can be activated using key commands. More specific instructions for use will print in the terminal window when the program is launched.

### Instructions for Geant4
To produce Geant4 outputs that can be read by GeViewer, you must tell Geant4 to save the visualization as a VRML file. You can do this by putting the following in your Macro file:
```
# this line should come BEFORE the /run/beamOn command
/vis/open VRML2FILE
```
Following this, you can add the geometry, trajectories, and step markers. Any of these can be omitted if they are not needed.
```
# now ensure that the geometry is displayed
/vis/drawVolume

# add the trajectories
/vis/scene/add/trajectories

# add the step markers
/vis/modeling/trajectories/create/drawByParticleID
/vis/modeling/trajectories/drawByParticleID-0/default/setDrawStepPts true

# ensure that they are not cleared at the end of the event
/vis/scene/endOfEventAction accumulate
```
There are many other visualization commands that can be added here as well. Consult the [Geant4 documentation](https://geant4.web.cern.ch/docs/) for more information. This section is also where you can put any other application-specific commands. Next, start the simulation with `/run/beamOn` followed by the number of primaries to generate. For visualization purposes, you should not be generating more than a handful of events.
```
# specify the number of events and start the simulation
/run/beamOn 1
```
Finally, refresh the viewer to ensure that the events generated have been added.
```
/vis/viewer/flush
```
By default, the VRML file will be saved as `g4_00.wrl` in the working directory, but it can easily be renamed from within the macro by issuing a shell command.
```
/control/shell mv g4_00.wrl /new/path/to/file.wrl
```
If you are using your local computer, you can even pipe the VRML file directly to GeViewer to have the interactive window open automatically following the simulation.
```
/control/shell geviewer /new/path/to/file.wrl
```
Note that this will not work if you are running Geant4 on a remote machine over `ssh`, as GeViewer cannot be run using X11 forwarding. If that is your use case, you can download the resulting VRML file to open on your local computer, or you can add the `-o` and `-d` flags to the command above to save a GeViewer session to disk. This will be discussed more later on.

### Interacting with the viewer
The following instructions for interacting with the viewer will display when the program is launched:

* Click and drag to rotate the view, `shift` + click
  and drag to pan,  `ctrl` + click and drag to roll,
  and scroll to zoom

* Press `c` to capture a screenshot of the current view

* Press `t` to toggle the trajectories on or off

* Press `m` to toggle the step markers on or off

* Press `b` to toggle the background on or off

* Press `w` to toggle between wireframe and solid modes

* Press `v` to switch to an isometric view

* Press `d` to set the display window size

* Press `i` to set the camera viewpoint

* Press `p` to print the current display settings

* Press `h` to export the viewer to an HTML file

* Press `q` to quit the viewer

While the primary interface is with the viewer window, some commands require text entry in the terminal window. Any saving commands will require the user to enter a file path in the terminal. Some of these functions have been specifically designed to provide more precise control of the viewer than can be achieved using the mouse alone.

#### Saving figures
The following is an example of how you might use GeViewer to produce figures. Suppose you want to save two figures showing different events or geometries from the same perspective. To do this, you could:

1. Open Geviewer to view one of the files

2. Set the window to the desired resolution by pressing `d` and entering the dimensions in pixels at the prompt

3. Use the mouse to find a good view of the event

4. Export the graphic by pressing `c` and entering a filename (e.g. `event1.eps`)

5. Print the view settings by pressing `p`

6. Close GeViewer and reopen to view the second file

7. Press `d` to set the window to the same resolution as for the first file

8. Press `i` to set the viewpoint and paste in the output from step 5

9. Export the graphic by pressing `c` and entering a filename (e.g. `event2.eps`)

This process will give you two graphics of the desired resolution from an identical viewpoint.

### Additional options
The full list of command-line options can be displayed using the `--help` flag:
```console
$ geviewer --help

usage: geviewer [-h] [-d [DESTINATION]] [-o] [-s] [-w] filenames [filenames ...]

View Geant4 simulation results.

positional arguments:
  filenames             the file or list of files to be displayed

options:
  -h, --help            show this help message and exit
  -d [DESTINATION], --destination [DESTINATION]
                        save the session to this location
  -o, --off-screen      run in offscreen mode.
  -s, --safe-mode       use more robust VRML parsing at the expense of some interactive features
  -w, --no-warnings     do not pause the program to display warnings
```
Detailed descriptions of selected options are provided below.

#### Saving and loading
For particularly large VRML files (>100,000 meshes), the process of building the interactive viewer can be time consuming, sometimes taking ten minutes or more. Thankfully, this step only needs to be done once, and the resulting session can be saved and rapidly reloaded at a later time. This is done using the ```--destination``` (or `-d`) flag, optionally followed by the output filename (ending in `.gev`). If no filename is provided, the session will be saved in the working directory as `viewer.gev`. To reload this session, run the program again, passing the `.gev` file as the `filenames` argument.
```bash
geviewer viewer.gev
```

#### Running offscreen
As the process of loading a very large VRML file can take time, it is often convenient to run it offscreen and save the resulting session for later. This can be done using the `--off-screen` (or `-o`) flag. This flag must be paired with the `--destination` flag in order for the session to be saved. As mentioned above, you can add the following line to your macro file to automatically run this process at the end of a simulation.
```
/control/shell geviewer /name/of/file.wrl -d /output/session/name.gev -o
```

#### Safe mode
By default, GeViewer uses its own VRML parser to extract the meshes for plotting. However, this parser has only been tested on a small sample set of Geant4 simulation results. If you encounter file parsing errors, try using the `--safe-mode` command line argument (and create an issue to report the problem). This will use a VRML parsing tool from [`vtk`](https://vtk.org) which should provide more robustness at the expense of some features. In safe mode, the program will be unable to distinguish trajectories, step markers, and detector components, and for large files the performance may be sluggish due to less efficient handling of the mesh data.

#### Viewing multiple files
If you want to view multiple files in the same viewer (e.g. to directly compare two geometries), pass in a list of filenames rather than a single argument.
```bash
geviewer /path/to/file1.wrl /path/to/file2.wrl /path/to/file3.wrl
```
This function only works for VRML files; previous GeViewer sessions cannot be opened simultaneously. However, you can always load multiple VRML files, save the session, and revisit it later as you would when viewing a single file.

## Additional Info
### License
Distributed under the MIT License. See [LICENSE](https://github.com/clarkehardy/geviewer/blob/main/LICENSE) for more information.

### Contact
Clarke Hardy – [cahardy@stanford.edu](mailto:cahardy@stanford.edu)
