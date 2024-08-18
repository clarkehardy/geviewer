import numpy as np
import pyvista as pv
from pathlib import Path
import os
import shutil
import zipfile
import tempfile
import json
from pyvistaqt import QtInteractor
from geviewer import parsers


class GeViewer:
    """The main interface for the GeViewer application, responsible for loading,
    processing, and visualizing data files. This class manages the creation
    and display of 3D visualizations based on the provided data files and
    offers various functionalities such as toggling display options and saving
    sessions.
    """
    def __init__(self, plotter_widget=None):
        """Initializes the GeViewer object.

        :param plotter_widget: The widget to use for the plotter.
        :type plotter_widget: QWidget, optional
        """
        self.off_screen = False
        if plotter_widget:
            self.plotter = QtInteractor(plotter_widget)
        else:
            self.plotter = pv.Plotter()
        self.bkg_colors = ['lightskyblue', 'midnightblue']
        self.plotter.set_background(*self.bkg_colors)
        self.bkg_on = True
        self.wireframe = False
        self.transparent = False
        self.gradient = True
        self.parallel = False
        self.components = []
        self.overlaps = []
        self.event_ids = []
        self.actors = {}


    def load_file(self, filename, off_screen=False,\
                   progress_callback=None):
        """Loads the files.

        :param filename: The name of the file to load.
        :type filename: str
        :param off_screen: If True, the plotter is created without displaying it. Defaults to False.
        :type off_screen: bool, optional
        :param progress_callback: The callback to use for the progress bar.
        :type progress_callback: callable, optional
        """
        self.off_screen = off_screen
        if filename.endswith('.gev'):
            new_components = self.load(filename)
        elif filename.endswith('.wrl'):
            parser = parsers.VRMLParser(filename)
            parser.parse_file(progress_callback)
            new_components = [parser.components]
        elif filename.endswith('heprep'):
            parser = parsers.HepRepParser(filename)
            parser.parse_file(progress_callback)
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
        """Creates the plotter.

        :param progress_obj: The progress object to use for the plotter.
        :type progress_obj: ProgressBar, optional
        """
        print('Plotting meshes...')
        if progress_obj:
            progress_obj.set_maximum_value(self.num_to_plot)
            progress_obj.reset_progress()
        self.plot_meshes(self.components, progress_obj=progress_obj)
        if progress_obj:
            progress_obj.signal_finished()


    def plot_meshes(self, components, level=0, progress_obj=None):
        """Plots the meshes.

        :param components: The components to plot.
        :type components: list
        :param level: Keeps track of the recursion level.
        :type level: int, optional
        :param progress_obj: The progress object to use for the plotter.
        :type progress_obj: ProgressBar, optional
        """
        style = 'wireframe' if self.wireframe else 'surface'
        opacity = 0.3 if self.transparent else 1.
        for comp in components:
            if comp['mesh'] is not None and not comp['has_actor']:
                print('...'*level + 'Plotting ' + comp['name'] + '...')
                if comp['is_event']:
                    self.event_ids.append(comp['id'])
                    this_opacity = 1
                else:
                    this_opacity = opacity
                actor = self.plotter.add_mesh(comp['mesh'], scalars='color', rgb=True, \
                                              render_points_as_spheres=comp['is_dot'], \
                                              point_size=5*comp['is_dot'], style=style, \
                                              opacity=this_opacity, name=comp['id'])
                self.actors[comp['id']] = actor
                comp['has_actor'] = True
                if progress_obj:
                    progress_obj.increment_progress()
            if len(comp['children']) > 0:
                self.plot_meshes(comp['children'], level + 1)
        if level == 0:
            self.plotter.view_isometric()
            print('Done plotting.')
            self.num_to_plot = 0
        

    def set_background_color(self):
        """Sets the background color.
        """
        if not self.bkg_on:
            return
        if self.gradient:
            self.plotter.set_background(self.bkg_colors[0],top=self.bkg_colors[1])
        else:
            self.plotter.set_background(self.bkg_colors[0])


    def toggle_parallel_projection(self):
        """Toggles the parallel projection on and off.
        """
        if not self.parallel:
            self.plotter.enable_parallel_projection()
        else:
            self.plotter.disable_parallel_projection()
        self.parallel = not self.parallel


    def toggle_background(self):
        """Toggles the gradient background on and off.
        """
        self.bkg_on = not self.bkg_on
        if self.bkg_on:
            top = self.bkg_colors[1] if self.gradient else None
            self.plotter.set_background(self.bkg_colors[0],top=top)
        else:
            self.plotter.set_background('white')
        if not self.off_screen:
            self.plotter.update()


    def toggle_wireframe(self):
        """Toggles between solid and wireframe display modes. Disables depth
        peeling if wireframe mode is enabled to improve responsiveness.
        """
        self.wireframe = not self.wireframe
        if self.wireframe:
            for actor in self.actors.values():
                actor.GetProperty().SetRepresentationToWireframe()
        else:
            for actor in self.actors.values():
                actor.GetProperty().SetRepresentationToSurface()
        if not self.off_screen:
            self.plotter.update()


    def toggle_transparent(self):
        """Toggles transparency on and off.
        """
        self.transparent = not self.transparent
        if self.transparent:
            self.plotter.enable_depth_peeling()
            for id, actor in self.actors.items():
                if id in self.event_ids:
                    continue
                actor.GetProperty().SetOpacity(0.3)
        else:
            self.plotter.disable_depth_peeling()
            for actor in self.actors.values():
                actor.GetProperty().SetOpacity(1)
        if not self.off_screen:
            self.plotter.update()


    def save(self, filename):
        """Saves the session to a .gev file.

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

                
    def load(self, filename):
        """Loads the session from a .gev file.

        :param filename: The name of the file to load the session from.
        :type filename: str
        """
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
        
        
    def is_mesh_inside(self, mesh1, mesh2):
        """Checks if one mesh is inside another.

        :param mesh1: The first mesh.
        :type mesh1: pyvista.PolyData
        :param mesh2: The second mesh.
        :type mesh2: pyvista.PolyData
        :return: True if mesh1 is inside mesh2, False otherwise.
        :rtype: bool
        """
        bounds1 = mesh1.bounds
        bounds2 = mesh2.bounds
        if bounds1[0] >= bounds2[0] and bounds1[1] <= bounds2[1] and \
            bounds1[2] >= bounds2[2] and bounds1[3] <= bounds2[3] and \
            bounds1[4] >= bounds2[4] and bounds1[5] <= bounds2[5]:
            return True
        return False
    

    def do_bounds_overlap(self, mesh1, mesh2):
        """Checks if the bounds of two meshes overlap.

        :param mesh1: The first mesh.
        :type mesh1: pyvista.PolyData
        :param mesh2: The second mesh.
        :type mesh2: pyvista.PolyData
        :return: True if the bounds overlap, False otherwise.
        :rtype: bool
        """
        bounds1 = mesh1.bounds
        bounds2 = mesh2.bounds
        if bounds1[0] >= bounds2[1] or bounds1[1] <= bounds2[0] or \
            bounds1[2] >= bounds2[3] or bounds1[3] <= bounds2[2] or \
            bounds1[4] >= bounds2[5] or bounds1[5] <= bounds2[4]:
            return False
        return True
    
    
    def get_overlap(self, mesh1, mesh2, tolerance=0.001, n_samples=100000):
        """Gets the overlap between two meshes.

        :param mesh1: The first mesh.
        :type mesh1: pyvista.PolyData
        :param mesh2: The second mesh.
        :type mesh2: pyvista.PolyData
        :param tolerance: The tolerance for the overlap.
        :type tolerance: float, optional
        :param n_samples: The number of samples to use.
        :type n_samples: int, optional
        :return: The points of overlap and the fraction of points that survived.
        :rtype: tuple
        """
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
        
        
    def find_overlaps(self, tolerance=0.001, n_samples=100000):
        """Finds the overlaps between the meshes.

        :param tolerance: The tolerance for the overlap.
        :type tolerance: float, optional
        :param n_samples: The number of samples to use.
        :type n_samples: int, optional
        :return: The ids of the meshes that overlap.
        :rtype: list
        """
        for actor in self.overlaps:
            self.plotter.remove_actor(actor)
        self.overlaps = []
        overlapping_meshes = []
        checked = []


        def find_overlaps_recursive(components, level=0):
            """Finds the overlaps between the meshes.

            :param components: The components to check for overlaps.
            :type components: list
            :param level: Keeps track of the recursion level.
            :type level: int, optional
            """
            for comp in components:
                if comp['mesh'] is not None and not (comp['shape'] == 'Point' or comp['shape'] == 'Line'):
                    check_for_overlaps(comp, components)
                if len(comp['children']) > 0:
                    find_overlaps_recursive(comp['children'], level + 1)
                checked.append(comp['id'])
                if level == 0:
                    break

        def check_for_overlaps(comp1, components):
            """Checks for overlaps between one component and all other components.

            :param comp1: The first component.
            :type comp1: dict
            :param components: The components to check for overlaps.
            :type components: list
            """
            for comp2 in components:
                if comp2['mesh'] is not None and not (comp2['shape'] == 'Point' or comp2['shape'] == 'Line') \
                    and (comp1['id'] != comp2['id']) and comp2['id'] not in checked:
                    mesh1 = comp1['mesh']
                    mesh2 = comp2['mesh']
                    if not mesh1.is_all_triangles:
                        mesh1 = mesh1.triangulate()
                    if not mesh2.is_all_triangles:
                        mesh2 = mesh2.triangulate()
                    if self.is_mesh_inside(mesh1, mesh2):
                        continue
                    if self.is_mesh_inside(mesh2, mesh1):
                        continue
                    if not self.do_bounds_overlap(mesh1, mesh2):
                        continue
                    if mesh1.n_open_edges + mesh2.n_open_edges > 0:
                        print('Warning: unable to check for overlap between ' + comp1['name'] + ' and ' + comp2['name'])
                        if mesh1.n_open_edges > 0:
                            print('-> {} has {} open edges.'.format(comp1['name'], mesh1.n_open_edges))
                        else:
                            print('-> {} has {} open edges.'.format(comp2['name'], mesh2.n_open_edges))
                        continue

                    points, overlap_fraction = self.get_overlap(mesh1, mesh2, tolerance, n_samples)
                    threshold = n_samples * tolerance

                    if points.n_points > threshold:
                        overlapping_meshes.append(comp1['id'])
                        overlapping_meshes.append(comp2['id'])
                        actor = self.plotter.add_mesh(points, color='red', style='points', show_edges=False)
                        self.overlaps.append(actor)
                        print('Warning: {} may overlap {} by {:.3f} percent'\
                              .format(comp1['name'], comp2['name'], 100*overlap_fraction))
                if len(comp2['children']) > 0:
                    check_for_overlaps(comp1, comp2['children'])

        find_overlaps_recursive(self.components)
        return np.unique(overlapping_meshes)


    def clear_meshes(self):
        """Clears the meshes.
        """
        for actor in self.actors.values():
            self.plotter.remove_actor(actor)
        self.actors = {}
        self.components = []
        self.overlaps = []
        self.event_ids = []
        self.num_to_plot = 0
