import numpy as np
import pyvista as pv
import asyncio
from pathlib import Path
import os
import shutil
import zipfile
import tempfile
import json
from geviewer import utils, parsers, plotter


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
    def __init__(self, plotter_widget=None):
        self.filename = 'No file loaded'
        self.safe_mode = False
        self.off_screen = False
        self.no_warnings = False
        self.from_gev = False
        self.save_session = False
        self.view_params = (None, None, None)
        self.initial_camera_pos = None
        self.has_transparency = False
        if plotter_widget:
            self.plotter = plotter.Plotter(plotter_widget)
        else:
            self.plotter = pv.Plotter()
        self.counts = [0, 0, 0]
        self.visible = [True, True, True]
        self.bkg_colors = ['lightskyblue', 'midnightblue']
        self.plotter.set_background(*self.bkg_colors)
        self.bkg_on = True
        self.wireframe = False
        self.transparent = False
        self.gradient = True
        self.parallel = False
        self.plotter.enable_depth_peeling()
        self.components = []
        self.intersections = []
        self.actors = {}


    def load_files(self, filename, off_screen=False,\
                   no_warnings=False, progress_callback=None):
        """Constructor method for the GeViewer object.
        """
        self.filename = filename
        self.off_screen = off_screen
        self.no_warnings = no_warnings
        # ensure the input arguments are valid
        self.from_gev = True if filename.endswith('.gev') else False
        # if len(filenames) > 1:
        #     extensions = [Path(f).suffix for f in filenames]
        #     if not all([e == extensions[0] for e in extensions]):
        #         raise Exception('Cannot load .wrl and .gev files together.')
        # if self.from_gev and len(filenames) > 1:
        #     print('Loading multiple .gev files at a time is not supported.')
        #     print('Only the first file will be loaded.\n')
        #     self.filenames = [self.filenames[0]]

        self.visible = [True, True, True]
        if self.from_gev:
            new_components = self.load(filename)
        elif filename.endswith('.wrl'):
            parser = parsers.VRMLParser(filename)
            parser.parse_file(progress_callback)
            self.view_params = parser.viewpoint_block
            # self.counts = [len(polyline_blocks), len(marker_blocks), len(solid_blocks)]
            # if not self.save_session and not no_warnings and sum(self.counts) > 1e6:
            #     self.save_session = utils.prompt_for_save_session(sum(self.counts))
            #     if self.save_session:
            #         destination = utils.prompt_for_file_path()
            new_components = [parser.components]
        elif filename.endswith('heprep'):
            parser = parsers.HepRepParser(filename)
            parser.parse_file()
            new_components = parser.components
        self.num_to_plot = self.count_components(new_components)
        self.components.extend(new_components)


    def count_components(self, components):
        """Counts the number of components in the list of components.

        :param components: A list of components.
        :type components: list
        :return: The number of components in the list.
        :rtype: int
        """
        count = 0
        for comp in components:
            count += 1
            if len(comp['children']) > 0:
                count += self.count_components(comp['children'])
        return count
    
    
    def create_plotter(self, progress_obj=None):
        """Creates a Plotter object, a subclass of pyvista.Plotter.
        """
        print('Plotting meshes...')
        try:
            if progress_obj:
                progress_obj.set_maximum_value(self.num_to_plot)
                progress_obj.reset_progress()
            self.plot_meshes(self.components, progress_obj=progress_obj)
            if progress_obj:
                progress_obj.signal_finished()
        except Exception as e:
            print(e)
        # self.set_initial_view()
        self.plotter.add_key_event('m', self.find_intersections)
        # self.plotter.add_key_event('c', self.save_screenshot)
        # self.plotter.add_key_event('t', self.toggle_tracks)
        # self.plotter.add_key_event('m', self.toggle_step_markers)
        # self.plotter.add_key_event('b', self.toggle_background)
        # self.plotter.add_key_event('w', self.toggle_wireframe)
        # self.plotter.add_key_event('d', self.set_window_size)
        # self.plotter.add_key_event('i', self.set_camera_view)
        # self.plotter.add_key_event('p', self.print_view_params)
        # self.plotter.add_key_event('h', self.export_to_html)
        # self.plotter.add_key_event('v', self.update_camera_position)
        # # if not self.safe_mode:
        #     self.check_transparency()
        # self.enable_depth_peeling = True


    def set_background_color(self):
        if self.gradient:
            self.plotter.set_background(self.bkg_colors[0],top=self.bkg_colors[1])
        else:
            self.plotter.set_background(self.bkg_colors[0])


    # def check_transparency(self):
    #     """Enables depth peeling if any of the meshes have transparency. This prevents issues
    #     with rendering order when displaying transparent objects.
    #     """
    #     transparencies = [mesh.point_data['color'][:,-1] for mesh in self.meshes if mesh is not None]
    #     transparencies = np.concatenate(transparencies)
    #     if not np.all(transparencies == 1):
    #         self.plotter.enable_depth_peeling()
    #         self.has_transparency = True
    #     else:
    #         self.has_transparency = False


    def plot_meshes(self, components, level=0, progress_obj=None):
        """Adds the meshes to the plot.
        """
        # print('Plotting meshes...')
        style = 'wireframe' if self.wireframe else 'surface'
        opacity = 0.3 if self.transparent else 1
        for comp in components:
            print('...'*level + 'Plotting ' + comp['name'] + '...')
            if comp['mesh'] is not None and not comp['has_actor']:
                # try:
                actor = self.plotter.add_mesh(comp['mesh'], scalars='color', rgb=True, \
                                                      render_points_as_spheres=comp['is_dot'], \
                                                      style=style, opacity=opacity)
                self.actors[comp['id']] = actor
                comp['has_actor'] = True
                if progress_obj:
                    progress_obj.increment_progress()
                # except:
                #     comp['actor'] = self.plotter.add_mesh(comp['mesh'])
            if len(comp['children']) > 0:
                self.plot_meshes(comp['children'], level + 1)
        if level == 0:
            print('Done.\n')
            self.num_to_plot = 0


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


    def toggle_parallel_projection(self):
        if not self.parallel:
            self.plotter.enable_parallel_projection()
        else:
            self.plotter.disable_parallel_projection()
        self.parallel = not self.parallel


    def toggle_background(self):
        """Toggles the gradient background on and off.
        """
        self.bkg_on = not self.bkg_on
        print('Toggling background ' + ['off.','on.'][self.bkg_on] + '\n')
        if self.bkg_on:
            self.plotter.set_background(self.bkg_colors[0],top=self.bkg_colors[1])
        else:
            self.plotter.set_background('white')
        if not self.off_screen:
            self.plotter.update()


    def toggle_wireframe(self):
        """Toggles between solid and wireframe display modes. Disables depth
        peeling if wireframe mode is enabled to improve responsiveness.
        """
        print('Switching to ' + ['wireframe', 'solid'][self.wireframe] + ' mode.\n')
        self.wireframe = not self.wireframe
        # actors = self.plotter.renderer.GetActors()
        # actors.InitTraversal()
        # actor = actors.GetNextActor()
        if self.wireframe:
            # while actor:
            #     actor.GetProperty().SetRepresentationToWireframe()
            #     actor = actors.GetNextActor()
            for actor in self.actors.values():
                actor.GetProperty().SetRepresentationToWireframe()
        else:
            # while actor:
            #     actor.GetProperty().SetRepresentationToSurface()
            #     actor = actors.GetNextActor()
            for actor in self.actors.values():
                actor.GetProperty().SetRepresentationToSurface()
        if not self.off_screen:
            self.plotter.update()


    def toggle_transparent(self):
        """Toggles transparency on and off.
        """
        print('Switching to ' + ['transparent', 'opaque'][self.transparent] + ' mode.\n')
        self.transparent = not self.transparent
        # actors = self.plotter.renderer.GetActors()
        # actors.InitTraversal()
        # actor = actors.GetNextActor()
        if self.transparent:
            self.plotter.enable_depth_peeling()
            # while actor:
            #     actor.GetProperty().SetOpacity(0.3)
            #     actor = actors.GetNextActor()
            for actor in self.actors.values():
                actor.GetProperty().SetOpacity(0.3)
        else:
            self.plotter.disable_depth_peeling()
            # while actor:
            #     actor.GetProperty().SetOpacity(1)
            #     actor = actors.GetNextActor()
            for actor in self.actors.values():
                actor.GetProperty().SetOpacity(1)
        if not self.off_screen:
            self.plotter.update()


    # def export_to_html(self):
    #     """Saves the interactive viewer to an HTML file, prompting
    #     the user for a file path.
    #     """
    #     try:
    #         import nest_asyncio
    #         import trame
    #         import trame_vuetify
    #         import trame_vtk
    #     except ImportError:
    #         print('Error: exporting to HTML requires additional dependencies.')
    #         print('Run "pip install geviewer[extras]" to install them.\n')
    #         return
    #     file_path = asyncio.run(utils.prompt_for_html_path())
    #     if file_path is None:
    #         print('Operation cancelled.\n')
    #         return
    #     self.plotter.export_html(file_path)
    #     print('Interactive viewer saved to ' + str(Path(file_path).resolve()) + '.\n')


    def save(self, filename):
        """Saves the meshes to a .gev file.

        :param filename: The name of the file to save the session to.
        :type filename: str
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfolder = tmpdir + '/gevfile/'
            os.makedirs(tmpfolder, exist_ok=False)
            def save_serializable_entries(components, level=0, saveable_dicts=[]):
                for comp in components:
                    temp_dict = {}
                    for key, value in comp.items():
                        if key not in ['mesh_points', 'mesh_inds', 'scalars', 'mesh', 'actor']:
                            temp_dict[key] = value
                    if comp['mesh_points'] is not None:
                        np.save(tmpfolder + 'mesh_points_{}.npy'.format(comp['id']), comp['mesh_points'], allow_pickle=False)
                        temp_dict['mesh_points'] = 'mesh_points_{}.npy'.format(comp['id'])
                    else:
                        temp_dict['mesh_points'] = None
                    if comp['mesh_inds'] is not None:
                        np.save(tmpfolder + 'mesh_inds_{}.npy'.format(comp['id']), comp['mesh_inds'], allow_pickle=False)
                        temp_dict['mesh_inds'] = 'mesh_inds_{}.npy'.format(comp['id'])
                    else:
                        temp_dict['mesh_inds'] = None
                    if comp['scalars'] is not None:
                        np.save(tmpfolder + 'scalars_{}.npy'.format(comp['id']), comp['scalars'], allow_pickle=False)
                        temp_dict['scalars'] = 'scalars_{}.npy'.format(comp['id'])
                    else:
                        temp_dict['scalars'] = None
                    if comp['mesh'] is not None:
                        comp['mesh'].save(tmpfolder + 'mesh_{}.vtk'.format(comp['id']))
                        temp_dict['mesh'] = 'mesh_{}.vtk'.format(comp['id'])
                    else:
                        temp_dict['mesh'] = None
                    temp_dict['has_actor'] = False
                    if len(comp['children']) > 0:
                        temp_dict['children'] = []
                        save_serializable_entries(comp['children'], level + 1, temp_dict['children'])
                    saveable_dicts.append(temp_dict)
                if level == 0:
                    return saveable_dicts
                
            saveable_dicts = save_serializable_entries(self.components)

            for i, saveable_dict in enumerate(saveable_dicts):
                with open(tmpfolder + 'components_dict_{}.json'.format(i), 'w') as f:
                    json.dump(saveable_dict, f)

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
        print('Success: session saved to ' + str(Path(filename).resolve()) + '.\n')

                
    def load(self, filename):
        """Loads the meshes from a .gev file.

        :param filename: The path to the .gev file.
        :type filename: str
        :raises Exception: Invalid file format. Only .gev files are supported.
        """
        # if not filename.endswith('.gev'):
        #     raise Exception('Invalid file format. Only .gev files are supported.')
        # print('Loading session from ' + str(Path(filename).resolve()) + '...')
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfolder = tmpdir + '/gevfile/'
            os.makedirs(tmpfolder, exist_ok=False)
            with zipfile.ZipFile(filename, 'r') as archive:
                archive.extractall(tmpfolder)
            files = [f for f in os.listdir(tmpfolder) if f.endswith('.json')]
            components = []
            for file in files:
                with open(tmpfolder + file, 'r') as f:
                    comp = json.load(f)
                    # if comp['mesh_points'] is not None:
                    #     comp['mesh_points'] = np.load(tmpfolder + comp['mesh_points'], allow_pickle=False)
                    # if comp['mesh_inds'] is not None:
                    #     comp['mesh_inds'] = np.load(tmpfolder + comp['mesh_inds'], allow_pickle=False)
                    # if comp['scalars'] is not None:
                    #     comp['scalars'] = np.load(tmpfolder + comp['scalars'], allow_pickle=False)
                    # if comp['mesh'] is not None:
                    #     comp['mesh'] = pv.read(tmpfolder + comp['mesh'])
                    components.append(comp)

            def load_components(components, level=0):
                for comp in components:
                    if comp['mesh_points'] is not None:
                        comp['mesh_points'] = np.load(tmpfolder + comp['mesh_points'], allow_pickle=False)
                    if comp['mesh_inds'] is not None:
                        comp['mesh_inds'] = np.load(tmpfolder + comp['mesh_inds'], allow_pickle=False)
                    if comp['scalars'] is not None:
                        comp['scalars'] = np.load(tmpfolder + comp['scalars'], allow_pickle=False)
                    if comp['mesh'] is not None:
                        comp['mesh'] = pv.read(tmpfolder + comp['mesh'])
                    if len(comp['children']) > 0:
                        load_components(comp['children'], level + 1)
            
            load_components(components)
            return components
            # meshes = []
            # counts = []
            # mesh_files = [file[-5] for file in os.listdir(tmpfolder) if file.endswith('.vtk')]
            # for i in range(3):
            #     if str(i) not in mesh_files:
            #         meshes.append(None)
            #         counts.append(0)
            #         continue
            #     meshes.append(pv.read(tmpfolder + 'mesh{}.vtk'.format(i)))
            #     counts.append(1)
            # viewpoint = np.load(tmpfolder + 'viewpoint.npy')
            # fov = float(viewpoint[0]) if viewpoint[0] != 'None' else None
            # pos = [float(p) for p in viewpoint[1:4]] if viewpoint[1] != 'None' else None
            # ori = [float(o) for o in viewpoint[4:]] if viewpoint[4] != 'None' else None
            # self.view_params = (fov, pos, ori)
            # self.meshes = meshes
            # self.counts = counts
        
    def find_intersections(self, tolerance=0.001, n_samples=100000):
        for actor in self.intersections:
            self.plotter.remove_actor(actor)
        self.intersections = []
        self.overlapping_meshes = []
        checked = []

        def is_mesh_inside(mesh1, mesh2):
            bounds1 = mesh1.bounds
            bounds2 = mesh2.bounds
            if bounds1[0] >= bounds2[0] and bounds1[1] <= bounds2[1] and \
               bounds1[2] >= bounds2[2] and bounds1[3] <= bounds2[3] and \
               bounds1[4] >= bounds2[4] and bounds1[5] <= bounds2[5]:
                return True
            return False

        def do_bounds_intersect(mesh1, mesh2):
            bounds1 = mesh1.bounds
            bounds2 = mesh2.bounds
            if bounds1[0] >= bounds2[1] or bounds1[1] <= bounds2[0] or \
               bounds1[2] >= bounds2[3] or bounds1[3] <= bounds2[2] or \
               bounds1[4] >= bounds2[5] or bounds1[5] <= bounds2[4]:
                return False
            return True

        def get_intersection(mesh1, mesh2, tolerance=0.001, n_samples=100000):
            points = np.random.uniform(low=mesh1.bounds[::2], \
                                        high=mesh1.bounds[1::2], \
                                        size=(n_samples, 3))
            
            points = pv.PolyData(points)
            select = points.select_enclosed_points(mesh1, tolerance=1e-6)
            points = select.points[select['SelectedPoints']>0.5]
            n_surviving = points.shape[0]
            points = pv.PolyData(points)

            select = points.select_enclosed_points(mesh2, tolerance=1e-6)
            points = select.points[select['SelectedPoints']>0.5]
            points = pv.PolyData(points)
            select = points.compute_implicit_distance(mesh2)
            bounds = mesh2.bounds
            dimensions = np.array([bounds[1]-bounds[0], bounds[3]-bounds[2], bounds[5]-bounds[4]])
            points = select.points[np.abs(select['implicit_distance'])>tolerance*np.linalg.norm(dimensions)]
            points = pv.PolyData(points)

            overlap_fraction = points.n_points/n_surviving

            return points, overlap_fraction

        def find_intersections_recursive(components, level=0):
            for comp in components:
                if comp['mesh'] is not None and not (comp['shape'] == 'Point' or comp['shape'] == 'Line'):
                    check_for_intersections(comp, components)
                if len(comp['children']) > 0:
                    find_intersections_recursive(comp['children'], level + 1)
                checked.append(comp['id'])
                if level == 0:
                    break

        def check_for_intersections(comp1, components):
            for comp2 in components:
                if comp2['mesh'] is not None and not (comp2['shape'] == 'Point' or comp2['shape'] == 'Line') \
                    and (comp1['id'] != comp2['id']) and comp2['id'] not in checked:
                    mesh1 = comp1['mesh']
                    mesh2 = comp2['mesh']
                    if not mesh1.is_all_triangles:
                        mesh1 = mesh1.triangulate()
                    if not mesh2.is_all_triangles:
                        mesh2 = mesh2.triangulate()
                    if is_mesh_inside(mesh1, mesh2):
                        continue
                    if is_mesh_inside(mesh2, mesh1):
                        continue
                    if not do_bounds_intersect(mesh1, mesh2):
                        continue
                    if mesh1.n_open_edges + mesh2.n_open_edges > 0:
                        print('Warning: unable to check for intersection between ' + comp1['name'] + ' and ' + comp2['name'])
                        if mesh1.n_open_edges > 0:
                            print('-> {} has {} open edges.'.format(comp1['name'], mesh1.n_open_edges))
                        else:
                            print('-> {} has {} open edges.'.format(comp2['name'], mesh2.n_open_edges))
                        continue

                    points, overlap_fraction = get_intersection(mesh1, mesh2, tolerance, n_samples)
                    threshold = n_samples * tolerance

                    if points.n_points > threshold:
                        self.overlapping_meshes.append(comp1['id'])
                        self.overlapping_meshes.append(comp2['id'])
                        actor = self.plotter.add_mesh(points, color='red', style='points_gaussian', show_edges=False)
                        self.intersections.append(actor)
                        print('Warning: {} may intersect {} by {:.3f} percent'\
                              .format(comp1['name'], comp2['name'], 100*overlap_fraction))
                if len(comp2['children']) > 0:
                    check_for_intersections(comp1, comp2['children'])

        def show_overlaps():
            self.overlapping_meshes = np.unique(self.overlapping_meshes)
            for actor in self.actors.values():
                actor.SetVisibility(False)
            for mesh in self.overlapping_meshes:
                self.actors[mesh].SetVisibility(True)
            if not self.transparent:
                self.toggle_transparent()
            self.plotter.view_isometric()

        if not len(self.components):
            print('Error: no components loaded.')
            return
        print('Checking {} for intersections...'.format(self.components[0]['name']))
        find_intersections_recursive(self.components)
        if len(self.intersections) == 0:
            print('No intersections found.')
        else:
            show_overlaps()
            print('Done.')

    def show(self):
        """Opens the plotting window.
        """
        self.plotter.show(cpos=self.initial_camera_pos,\
                          before_close_callback=lambda x: print('\nExiting GeViewer.\n'))
