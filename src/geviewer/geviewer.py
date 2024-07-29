import numpy as np
import pyvista as pv
import asyncio
from pathlib import Path
import json
import os
import shutil
import zipfile
import tempfile
from matplotlib.colors import LinearSegmentedColormap
from geviewer import utils, parser, plotter


class GeViewer:
    """The main interface for the GeViewer application, responsible for loading,
    processing, and visualizing data files. This class manages the creation
    and display of 3D visualizations based on the provided data files and
    offers various functionalities such as toggling display options and saving
    sessions.

    :param filenames: A list of file paths to be loaded. Supported file formats
        include .gev and .wrl. Only the first file is used if multiple .gev files
        are provided.
    :type filenames: list of str
    :param destination: The file path where the session will be saved. If not provided,
        the session is not saved. The file extension must be .gev if specified.
    :type destination: str, optional
    :param off_screen: If True, the plotter is created without displaying it. Defaults to False.
    :type off_screen: bool, optional
    :param safe_mode: If True, the viewer operates in safe mode with some features disabled.
    :type safe_mode: bool, optional
    :param no_warnings: If True, suppresses warning messages. Defaults to False.
    :type no_warnings: bool, optional

    :raises Exception: If .gev and .wrl files are mixed, or if multiple .gev files are provided.
    :raises Exception: If attempting to save a session using an invalid file extension.
    """

    def __init__(self, filenames, destination=None, off_screen=False,\
                 safe_mode=False, no_warnings=False):
        """Constructor method for the GeViewer object.
        """
        self.filenames = filenames
        self.safe_mode = safe_mode
        self.off_screen = off_screen
        self.no_warnings = no_warnings

        # if destination is given, the program will save the session to that file
        if destination is not None:
            self.save_session = True
            if not destination.endswith('.gev'):
                if self.off_screen:
                    print('Renaming the session file to end in .gev so it can be loaded later.')
                    destination = destination.split('.')[:-1] + '.gev'
                else:
                    print('Error: invalid file extension.')
                    print('Try again, or press enter to continue without saving.\n')
                    destination = utils.prompt_for_file_path()
            if destination is None:
                self.save_session = False
        else:
            self.save_session = False

        # ensure the input arguments are valid
        self.from_gev = True if filenames[0].endswith('.gev') else False
        if len(filenames) > 1:
            extensions = [Path(f).suffix for f in filenames]
            if not all([e == extensions[0] for e in extensions]):
                raise Exception('Cannot load .wrl and .gev files together.')
        if self.from_gev and len(filenames) > 1:
            print('Loading multiple .gev files at a time is not supported.')
            print('Only the first file will be loaded.\n')
            filenames = [filenames[0]]
        if self.from_gev and self.safe_mode:
            print('Safe mode can only be used for VRML files.')
            print('Ignoring the --safe-mode flag.\n')
            self.safe_mode = False
        if self.from_gev and self.save_session:
            print('This session has already been saved.')
            print('Ignoring the --destination flag.\n')
            self.save_session = False
        if destination is not None and self.safe_mode:
            print('Cannot save a session in safe mode.')
            print('Ignoring the --destination flag.\n')
            self.save_session = False

        if self.safe_mode:
            print('Running in safe mode with some features disabled.\n')
            self.view_params = (None, None, None)
            self.create_plotter()
            if len(filenames)>1:
                print('Only the first file will be displayed in safe mode.\n')
            self.plotter.import_vrml(filenames[0])
            self.counts = []
            self.visible = []
            self.meshes = []
        else:
            self.visible = [True, True, True]
            if self.from_gev:
                self.load(filenames[0])
            else:
                data = utils.read_files(filenames)
                viewpoint_block, polyline_blocks, marker_blocks, solid_blocks = parser.extract_blocks(data)
                self.view_params = parser.parse_viewpoint_block(viewpoint_block)
                self.counts = [len(polyline_blocks), len(marker_blocks), len(solid_blocks)]
                if not self.save_session and not no_warnings and sum(self.counts)>1e4:
                    self.save_session = utils.prompt_for_save_session(sum(self.counts))
                    if self.save_session:
                        destination = utils.prompt_for_file_path()
                self.meshes, self.scalars, self.cmaps = parser.create_meshes(polyline_blocks, \
                                                                            marker_blocks, \
                                                                            solid_blocks)
                self.reduce_meshes()
            self.make_colormaps()
            self.create_plotter()
            self.plot_meshes()
            if self.save_session:
                self.save(destination)
        if not off_screen:
            self.show()

    
    def create_plotter(self):
        """Creates a Plotter object, a subclass of pyvista.Plotter.
        """
        self.plotter = plotter.Plotter(title='GeViewer — ' + str(Path(self.filenames[0]).resolve()) \
                                       + ['',' + {} more'.format(len(self.filenames)-1)]\
                                         [(len(self.filenames)>1) and not self.safe_mode],\
                                       off_screen=self.off_screen)
        self.plotter.add_key_event('c', self.save_screenshot)
        self.plotter.add_key_event('t', self.toggle_tracks)
        self.plotter.add_key_event('m', self.toggle_step_markers)
        self.plotter.add_key_event('b', self.toggle_background)
        self.plotter.add_key_event('w', self.toggle_wireframe)
        self.plotter.add_key_event('d', self.set_window_size)
        self.plotter.add_key_event('i', self.set_camera_view)
        self.plotter.add_key_event('p', self.print_view_params)
        self.plotter.add_key_event('h', self.export_to_html)
        self.plotter.add_key_event('v', self.update_camera_position)
        self.plotter.set_background('lightskyblue',top='midnightblue')
        self.bkg_on = True
        self.wireframe = False
        
        # compute the initial camera position
        fov = self.view_params[0]
        position = self.view_params[1]
        orientation = self.view_params[2]
        if fov is not None or position is not None or orientation is not None:
            up = None
            focus = None
            if position is not None:
                up = np.array([0.,1.,0.])
                focus = np.array([0.,0.,-1.])*np.linalg.norm(position) - np.array(position)
            if orientation is not None:
                up,focus = utils.orientation_transform(orientation)
                if position is not None:
                    focus = np.array(focus)*np.linalg.norm(position) - np.array(position)
            self.plotter.reset_camera()
            self.set_camera_view((fov,position,up,focus))
            self.initial_camera_pos = self.plotter.camera_position
        else:
            self.initial_camera_pos = None


    def set_camera_view(self,args=None):
        """Sets the camera viewpoint.

        :param args: A list of the view parameters, defaults to None
        :type args: list, optional
        """
        if args is None:
            fov = None
            position, up, focus = asyncio.run(utils.prompt_for_camera_view())
        else:
            fov, position, up, focus = args
        if fov is not None:
            self.plotter.camera.view_angle = fov
        if position is not None:
            self.plotter.camera.position = position
        if up is not None:
            self.plotter.camera.up = up
        if focus is not None:
            self.plotter.camera.focal_point = focus
        if args is None:
            if not self.off_screen:
                self.plotter.update()
            print('Camera view set.\n')


    def update_camera_position(self):
        """Updates the camera position. This method's only job is to ensure
        that the PyVista plotter knows that the camera position has changed
        on a key event handled by vtk under the hood. This is necessary to
        avoid a bug where the camera jumps back to the isometric view the next
        time the user prints the camera position.
        """
        self.plotter.camera.GetPosition()


    def print_view_params(self):
        """Prints the current camera viewpoint parameters.
        """
        print('Viewpoint parameters:')
        print('  Window size: {}x{}'.format(*self.plotter.window_size))
        print('  Position:    ({}, {}, {})'.format(*self.plotter.camera.position))
        print('  Focal point: ({}, {}, {})'.format(*self.plotter.camera.focal_point))
        print('  Up vector:   ({}, {}, {})\n'.format(*self.plotter.camera.up))


    def make_colormaps(self):
        """Makes the colormaps used to color the meshes.
        """
        luts = []
        for t in range(3):
            if self.counts[t] > 0:
                scalar_range = [min(self.scalars[t]), max(self.scalars[t]) + 1]
                lut = pv.LookupTable(scalar_range=scalar_range)
                lut.apply_cmap(self.cmaps[t], n_values=self.cmaps[t].N)
                luts.append(lut)
            else:
                luts.append(None)
        self.luts = luts


    def reduce_meshes(self):
        """Reduces the number of meshes by combining them.
        """
        blocks = [pv.MultiBlock() for i in range(3)]
        scalars = [[] for i in range(3)]
        for i, mesh in enumerate(self.meshes):
            if i < self.counts[0]:
                type_ind = 0
            elif i < sum(self.counts[:2]):
                type_ind = 1
            else:
                type_ind = 2
            blocks[type_ind].append(mesh)
            scalars[type_ind] += [self.scalars[i].astype(int)]*mesh.n_cells
        for t in range(3):
            if self.counts[t] > 0:
                blocks[t] = blocks[t].combine()
            else:
                blocks[t] = None
        self.meshes = blocks
        self.scalars = scalars


    def plot_meshes(self):
        """Adds the meshes to the plot.
        """
        print('Plotting meshes...')
        actors = [None for i in range(3)]
        for t in range(3):
            if self.counts[t] > 0:
                actors[t] = self.plotter.add_mesh(self.meshes[t], scalars=np.array(self.scalars[t]) + 0.5,\
                                                  cmap=self.luts[t], show_scalar_bar=False, point_size=0)
        self.actors = actors
        print('Done.\n')


    def save_screenshot(self):
        """Saves a screenshot of of the current view, prompting the user
        for a file path.
        """
        file_path = asyncio.run(utils.prompt_for_screenshot_path())
        if file_path is None:
            print('Operation cancelled.\n')
            return
        elif file_path.endswith('.png'):
            self.plotter.screenshot(file_path)
        else:
            self.plotter.save_graphic(file_path)
        print('Screenshot saved to ' + str(Path(file_path).resolve()) + '.\n')
    

    def set_window_size(self):
        """Sets the size of the viewer window in pixels, prompting the user
        for the width and height.
        """
        width, height = asyncio.run(utils.prompt_for_window_size())
        if width is None and height is None:
            print('Operation cancelled.\n')
            return
        self.plotter.window_size = width, height
        print('Window size set to ' + str(width) + 'x' + str(height) + '.\n')
        

    def toggle_tracks(self):
        """Toggles the particle trajectories on or off.
        """
        if not self.safe_mode:
            self.visible[0] = not self.visible[0]
            print('Toggling particle tracks ' + ['off.','on.'][self.visible[0]])
            if self.visible[0]:
                if self.actors[0] is not None:
                    self.actors[0].visibility = True
            else:
                if self.actors[0] is not None:
                    self.actors[0].visibility = False
            if not self.off_screen:
                self.plotter.update()
        else:
            print('This feature is disabled in safe mode.')
                
                
    def toggle_step_markers(self):
        """Toggles the step markers on or off.
        """
        if not self.safe_mode:
            self.visible[1] = not self.visible[1]
            print('Toggling step markers ' + ['off.','on.'][self.visible[1]])
            if self.visible[1]:
                if self.actors[1] is not None:
                    self.actors[1].visibility = True
            else:
                if self.actors[1] is not None:
                    self.actors[1].visibility = False
            if not self.off_screen:
                self.plotter.update()
        else:
            print('This feature is disabled in safe mode.')


    def toggle_background(self):
        """Toggles the gradient background on and off.
        """
        self.bkg_on = not self.bkg_on
        print('Toggling background ' + ['off.','on.'][self.bkg_on])
        if self.bkg_on:
            self.plotter.set_background('lightskyblue',top='midnightblue')
        else:
            self.plotter.set_background('white')
        if not self.off_screen:
            self.plotter.update()


    def toggle_wireframe(self):
        """Toggles between solid and wireframe display modes.
        """
        self.wireframe = not self.wireframe
        print('Switching to ' + ['solid','wireframe'][self.wireframe] + ' mode.')
        if self.wireframe:
            self.actors[2].prop.SetRepresentationToWireframe()
        else:
            self.actors[2].prop.SetRepresentationToSurface()
        if not self.off_screen:
            self.plotter.update()


    def export_to_html(self):
        """Saves the interactive viewer to an HTML file, prompting
        the user for a file path.
        """
        file_path = asyncio.run(utils.prompt_for_html_path())
        if file_path is None:
            print('Operation cancelled.\n')
            return
        self.plotter.export_html(file_path)
        print('Interactive viewer saved to ' + str(Path(file_path).resolve()) + '.\n')


    def save(self, filename):
        """Saves the meshes to a .gev file.

        :param filename: The name of the file to save the session to.
        :type filename: str
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfolder = tmpdir + '/gevfile/'
            os.makedirs(tmpfolder, exist_ok=False)
            for i,mesh in enumerate(self.meshes):
                if mesh is not None:
                    mesh.save(tmpfolder + 'mesh{}.vtk'.format(i))
                    np.save(tmpfolder + 'scalars{}.npy'.format(i),self.scalars[i],allow_pickle=False)
                    with open(tmpfolder + 'cmap{}.json'.format(i), 'w') as f:
                        cmap_dict = self.cmaps[i]._segmentdata
                        cmap_dict['N'] = self.cmaps[i].N
                        for c in ['red', 'green', 'blue', 'alpha']:
                            cmap_dict[c] = [val.item() for val in cmap_dict[c][:,-1]]
                        json.dump(cmap_dict, f)
            fov, pos, ori = self.view_params
            if fov is None:
                fov = 'None'
            if pos is None:
                pos = ['None' for i in range(3)]
            if ori is None:
                ori = ['None' for i in range(4)]
            viewpoint = np.array([str(fov)] + [str(p) for p in pos] + [str(o) for o in ori])
            np.save(tmpfolder + 'viewpoint.npy',np.array(viewpoint),allow_pickle=False)
            with zipfile.ZipFile(tmpdir + '/gevfile.gev', 'w') as archive:
                for file_name in os.listdir(tmpfolder):
                    file_path = os.path.join(tmpfolder, file_name)
                    archive.write(file_path, arcname=file_name)

            # if using the default filename and it exists, increment
            # the number until a unique filename is found
            if filename=='viewer.gev' and os.path.exists(filename):
                filename = 'viewer2.gev'
                i = 2
                while(os.path.exists('viewer{}.gev'.format(i))):
                    i += 1
                filename = 'viewer{}.gev'.format(i)
            shutil.copy(tmpdir + '/gevfile.gev', filename)
        print('Session saved to ' + str(Path(filename).resolve()) + '.\n')

                
    def load(self, filename):
        """Loads the meshes from a .gev file.

        :param filename: The path to the .gev file.
        :type filename: str
        :raises Exception: Invalid file format. Only .gev files are supported.
        """
        if not filename.endswith('.gev'):
            raise Exception('Invalid file format. Only .gev files are supported.')
        print('Loading session from ' + str(Path(filename).resolve()) + '...')
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfolder = tmpdir + '/gevfile/'
            os.makedirs(tmpfolder, exist_ok=False)
            with zipfile.ZipFile(filename, 'r') as archive:
                archive.extractall(tmpfolder)
            meshes = []
            scalars = []
            cmaps = []
            counts = []
            mesh_files = [file[-5] for file in os.listdir(tmpfolder) if file.endswith('.vtk')]
            for i in range(3):
                if str(i) not in mesh_files:
                    meshes.append(None)
                    scalars.append(None)
                    cmaps.append(None)
                    counts.append(0)
                    continue
                meshes.append(pv.read(tmpfolder + 'mesh{}.vtk'.format(i)))
                scalars.append(np.load(tmpfolder + 'scalars{}.npy'.format(i)))
                with open(tmpfolder + 'cmap{}.json'.format(i), 'r') as f:
                    cmap_dict = json.load(f)
                cmap_list = [np.array((cmap_dict['red'][i],\
                                       cmap_dict['green'][i],\
                                       cmap_dict['blue'][i],\
                                       cmap_dict['alpha'][i]))\
                             for i in range(len(cmap_dict['red']))]
                cmaps.append(LinearSegmentedColormap.from_list("my_colormap", cmap_list, N=cmap_dict['N']))
                counts.append(1)
            viewpoint = np.load(tmpfolder + 'viewpoint.npy')
            fov = float(viewpoint[0]) if viewpoint[0] != 'None' else None
            pos = [float(p) for p in viewpoint[1:4]] if viewpoint[1] != 'None' else None
            ori = [float(o) for o in viewpoint[4:]] if viewpoint[4] != 'None' else None
            self.view_params = (fov, pos, ori)
            self.meshes = meshes
            self.scalars = scalars
            self.cmaps = cmaps
            self.counts = counts


    def show(self):
        """Opens the plotting window.
        """
        self.plotter.show(cpos=self.initial_camera_pos,\
                          before_close_callback=lambda x: print('\nExiting GeViewer.\n'))
