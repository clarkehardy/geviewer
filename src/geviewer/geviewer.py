import numpy as np
import pyvista as pv
import asyncio
from pathlib import Path
import os
import shutil
import zipfile
import tempfile
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
        if not self.no_warnings:
            utils.check_for_updates()

        # if destination is given, the program will save the session to that file
        if destination is not None:
            self.save_session = True
            if not destination.endswith('.gev'):
                if self.off_screen:
                    print('Renaming the session file to end in .gev so it can be loaded later.')
                    destination = '.'.join(destination.split('.')[:-1]) + '.gev'
                else:
                    print('Error: invalid file extension.')
                    print('Try again, or press enter to continue without saving.\n')
                    destination = utils.prompt_for_file_path()
            if not os.path.isdir('/'.join(str(Path(destination).resolve()).split('/')[:-1])):
                if self.off_screen:
                    print('Destination folder does not exist.')
                    print('Creating the destination folder.')
                    os.makedirs('/'.join(str(Path(destination).resolve()).split('/')[:-1]), exist_ok=True)
                else:
                    print('Error: destination folder does not exist.')
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
            self.filenames = [self.filenames[0]]
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
            self.initial_camera_pos = None
            self.has_transparency = False
            self.create_plotter()
            if len(self.filenames)>1:
                print('Only the first file will be displayed in safe mode.\n')
            self.plotter.import_vrml(self.filenames[0])
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
                if not self.save_session and not no_warnings and sum(self.counts) > 1e6:
                    self.save_session = utils.prompt_for_save_session(sum(self.counts))
                    if self.save_session:
                        destination = utils.prompt_for_file_path()
                self.meshes = parser.create_meshes(polyline_blocks, marker_blocks, solid_blocks)
            self.create_plotter()
            self.plot_meshes()
            self.set_initial_view()
            if self.save_session:
                self.save(destination)
        if not off_screen:
            self.show()

    
    def create_plotter(self):
        """Creates a Plotter object, a subclass of pyvista.Plotter.
        """
        self.plotter = plotter.Plotter(title='GeViewer -- ' + str(Path(self.filenames[0]).resolve()) \
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
        if not self.safe_mode:
            self.check_transparency()
        self.bkg_on = True
        self.wireframe = False


    def check_transparency(self):
        """Enables depth peeling if any of the meshes have transparency. This prevents issues
        with rendering order when displaying transparent objects.
        """
        transparencies = [mesh.point_data['color'][:,-1] for mesh in self.meshes if mesh is not None]
        transparencies = np.concatenate(transparencies)
        if not np.all(transparencies == 1):
            self.plotter.enable_depth_peeling()
            self.has_transparency = True
        else:
            self.has_transparency = False


    def plot_meshes(self):
        """Adds the meshes to the plot.
        """
        print('Plotting meshes...')
        actors = [None for i in range(3)]
        for i in range(3):
            if self.counts[i] > 0:
                actors[i] = self.plotter.add_mesh(self.meshes[i], scalars='color', rgba=True)
        self.actors = actors
        print('Done.\n')


    def set_initial_view(self):
        """Sets the initial camera viewpoint based on the view parameters
        provided in the VRML file.
        """
        fov = self.view_params[0]
        position = self.view_params[1]
        orientation = self.view_params[2]
        if position is not None and orientation is not None:
            up, v = utils.orientation_transform(orientation)
            focus = position + v*np.linalg.norm(position)
        elif position is not None and orientation is None:
            up = np.array([0.,1.,0.])
            focus = position + np.array([0.,0.,-1.])*np.linalg.norm(position)
        elif position is None and orientation is not None:
            self.plotter.view_isometric()
            position = np.linalg.norm(self.plotter.camera.GetPosition())*np.array([0.,0.,1.])
            up, v = utils.orientation_transform(orientation)
            focus = position + v*np.linalg.norm(position)
        else:
            self.plotter.view_isometric()
            position = np.linalg.norm(self.plotter.camera.GetPosition())*np.array([0.,0.,1.])
            up = np.array([0.,1.,0.])
            focus = position + np.array([0.,0.,-1.])*np.linalg.norm(position)
        self.plotter.reset_camera()
        self.set_camera_view((fov,position,up,focus))
        self.initial_camera_pos = self.plotter.camera_position
    

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
            print('Toggling particle tracks ' + ['off.','on.'][self.visible[0]] + '\n')
            if self.visible[0]:
                if self.actors[0] is not None:
                    self.actors[0].visibility = True
            else:
                if self.actors[0] is not None:
                    self.actors[0].visibility = False
            if not self.off_screen:
                self.plotter.update()
        else:
            print('This feature is disabled in safe mode.\n')
                
                
    def toggle_step_markers(self):
        """Toggles the step markers on or off.
        """
        if not self.safe_mode:
            self.visible[1] = not self.visible[1]
            print('Toggling step markers ' + ['off.','on.'][self.visible[1]] + '\n')
            if self.visible[1]:
                if self.actors[1] is not None:
                    self.actors[1].visibility = True
            else:
                if self.actors[1] is not None:
                    self.actors[1].visibility = False
            if not self.off_screen:
                self.plotter.update()
        else:
            print('This feature is disabled in safe mode.\n')


    def toggle_background(self):
        """Toggles the gradient background on and off.
        """
        self.bkg_on = not self.bkg_on
        print('Toggling background ' + ['off.','on.'][self.bkg_on] + '\n')
        if self.bkg_on:
            self.plotter.set_background('lightskyblue',top='midnightblue')
        else:
            self.plotter.set_background('white')
        if not self.off_screen:
            self.plotter.update()


    def toggle_wireframe(self):
        """Toggles between solid and wireframe display modes. Disables depth
        peeling if wireframe mode is enabled to improve responsiveness.
        """
        self.wireframe = not self.wireframe
        print('Switching to ' + ['solid','wireframe'][self.wireframe] + ' mode.\n')
        if not self.safe_mode:
            if self.wireframe:
                self.actors[2].prop.SetRepresentationToWireframe()
                if self.has_transparency:
                    self.plotter.disable_depth_peeling()
            else:
                self.actors[2].prop.SetRepresentationToSurface()
                if self.has_transparency:
                    self.plotter.enable_depth_peeling()
        else:
            if self.wireframe:
                actors = self.plotter.renderer.GetActors()
                actors.InitTraversal()
                actor = actors.GetNextActor()
                while actor:
                    actor.GetProperty().SetRepresentationToWireframe()
                    actor = actors.GetNextActor()
            else:
                actors = self.plotter.renderer.GetActors()
                actors.InitTraversal()
                actor = actors.GetNextActor()
                while actor:
                    actor.GetProperty().SetRepresentationToSurface()
                    actor = actors.GetNextActor()
        if not self.off_screen:
            self.plotter.update()


    def export_to_html(self):
        """Saves the interactive viewer to an HTML file, prompting
        the user for a file path.
        """
        try:
            import nest_asyncio
            import trame
            import trame_vuetify
            import trame_vtk
        except ImportError:
            print('Error: exporting to HTML requires additional dependencies.')
            print('Run "pip install geviewer[extras]" to install them.\n')
            return
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
            counts = []
            mesh_files = [file[-5] for file in os.listdir(tmpfolder) if file.endswith('.vtk')]
            for i in range(3):
                if str(i) not in mesh_files:
                    meshes.append(None)
                    counts.append(0)
                    continue
                meshes.append(pv.read(tmpfolder + 'mesh{}.vtk'.format(i)))
                counts.append(1)
            viewpoint = np.load(tmpfolder + 'viewpoint.npy')
            fov = float(viewpoint[0]) if viewpoint[0] != 'None' else None
            pos = [float(p) for p in viewpoint[1:4]] if viewpoint[1] != 'None' else None
            ori = [float(o) for o in viewpoint[4:]] if viewpoint[4] != 'None' else None
            self.view_params = (fov, pos, ori)
            self.meshes = meshes
            self.counts = counts


    def show(self):
        """Opens the plotting window.
        """
        self.plotter.show(cpos=self.initial_camera_pos,\
                          before_close_callback=lambda x: print('\nExiting GeViewer.\n'))
