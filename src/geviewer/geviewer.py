import numpy as np
import pyvista as pv
import asyncio
from pathlib import Path
from geviewer import utils, parser


class GeViewer:

    def __init__(self, filenames, safe_mode=False, off_screen=False):
        '''
        Read data from a file and create meshes from it.
        '''
        self.filenames = filenames
        self.off_screen = off_screen
        self.bkg_on = False
        self.safe_mode = safe_mode
        if safe_mode:
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
            data = utils.read_files(filenames)
            viewpoint_block, polyline_blocks, marker_blocks, solid_blocks = parser.extract_blocks(data)
            self.view_params = parser.parse_viewpoint_block(viewpoint_block)
            self.counts = [len(polyline_blocks), len(marker_blocks), len(solid_blocks)]
            self.visible = [True, True, True]
            self.meshes,self.cmap,self.color_inds = parser.create_meshes(polyline_blocks, marker_blocks, solid_blocks)
            self.create_plotter()
            self.plot_meshes()

    
    def create_plotter(self):
        '''
        Create a PyVista plotter.
        '''
        self.plotter = pv.Plotter(title='GeViewer — ' + str(Path(self.filenames[0]).resolve()) + \
                                  ['',' + {} more'.format(len(self.filenames)-1)]\
                                  [(len(self.filenames)>1) and not self.safe_mode],\
                                  off_screen=self.off_screen)
        self.plotter.add_key_event('c', self.save_screenshot)
        self.plotter.add_key_event('t', self.toggle_tracks)
        self.plotter.add_key_event('m', self.toggle_step_markers)
        self.plotter.add_key_event('b', self.toggle_background)
        # solid and wireframe rendering modes have key events by default
        self.plotter.add_key_event('d', self.set_window_size)
        self.plotter.add_key_event('o', self.set_camera_view)
        self.plotter.add_key_event('p', self.print_view_params)
        
        # compute the initial camera position
        if not self.safe_mode:
            fov = self.view_params[0]
            position = self.view_params[1]
            orientation = self.view_params[2]
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
        '''
        Set the camera viewpoint.
        '''
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


    def print_view_params(self):
        '''
        Print the current camera viewpoint parameters.
        '''
        print('Viewpoint parameters:')
        print('  Window size: {}x{}'.format(*self.plotter.window_size))
        print('  Position:    ({}, {}, {})'.format(*self.plotter.camera.position))
        print('  Focal point: ({}, {}, {})'.format(*self.plotter.camera.focal_point))
        print('  Up vector:   ({}, {}, {})\n'.format(*self.plotter.camera.up))


    def plot_meshes(self):
        '''
        Add the meshes to the plot.
        '''

        blocks = pv.MultiBlock()
        cell_inds = []
        for i, mesh in enumerate(self.meshes):
            blocks.append(mesh)
            cell_inds += [int(self.color_inds[i])]*mesh.n_cells

        blocks = blocks.combine()
        cell_inds = np.array(cell_inds)
        scalar_range = [np.amin(cell_inds),np.amax(cell_inds)+1]
        lut = pv.LookupTable(scalar_range=scalar_range)
        lut.apply_cmap(self.cmap,n_values=self.cmap.N)

        self.plotter.add_mesh(blocks,scalars=cell_inds+0.5,cmap=lut,show_scalar_bar=False)

        self.actors = blocks
        print('Done.\n')


    def save_screenshot(self):
        '''
        Save a screenshot (as a png) of the current view.
        '''
        file_path = asyncio.run(utils.prompt_for_file_path())
        if file_path is None:
            print('Operation cancelled.\n')
            return
        elif file_path.endswith('.png'):
            self.plotter.screenshot(file_path)
        else:
            self.plotter.save_graphic(file_path)
        print('Screenshot saved to ' + file_path + '.\n')
    

    def set_window_size(self):
        '''
        Set the window size in pixels.
        '''
        width, height = asyncio.run(utils.prompt_for_window_size())
        if width is None and height is None:
            print('Operation cancelled.\n')
            return
        self.plotter.window_size = width, height
        print('Window size set to ' + str(width) + 'x' + str(height) + '.\n')
        

    def toggle_tracks(self):
        '''
        Toggle the tracks on and off.
        '''
        if not self.safe_mode:
            self.visible[0] = not self.visible[0]
            print('Toggling particle tracks ' + ['off.','on.'][self.visible[0]])
            track_actors = self.actors[:self.counts[0]]
            if self.visible[0]:
                for actor in track_actors:
                    actor.visibility = True
            else:
                for actor in track_actors:
                    actor.visibility = False
            if not self.off_screen:
                self.plotter.update()
        else:
            print('This feature is disabled in safe mode.')
                
                
    def toggle_step_markers(self):
        '''
        Toggle the step markers on and off.
        '''
        if not self.safe_mode:
            self.visible[2] = not self.visible[2]
            print('Toggling step markers ' + ['off.','on.'][self.visible[2]])
            step_actors = self.actors[sum(self.counts[:1]):sum(self.counts[:2])]
            if self.visible[2]:
                for actor in step_actors:
                    actor.visibility = True
            else:
                for actor in step_actors:
                    actor.visibility = False
            if not self.off_screen:
                self.plotter.update()
        else:
            print('This feature is disabled in safe mode.')


    def toggle_background(self):
        '''
        Toggle the gradient background on and off.
        '''
        self.bkg_on = not self.bkg_on
        print('Toggling background ' + ['off.','on.'][self.bkg_on])
        if self.bkg_on:
            self.plotter.set_background('lightskyblue',top='midnightblue')
        else:
            self.plotter.set_background('white')
        if not self.off_screen:
            self.plotter.update()


    def show(self):
        '''
        Show the plotting window.
        '''
        self.plotter.show(cpos=self.initial_camera_pos,\
                          before_close_callback=lambda x: print('\nExiting GeViewer.\n'))
