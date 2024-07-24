import numpy as np
import pyvista as pv
import re
import asyncio
from tqdm import tqdm
from pathlib import Path
from geviewer import utils


class GeViewer:

    def __init__(self, filename, safe_mode=False, off_screen=False):
        '''
        Read data from a file and create meshes from it.
        '''
        self.filename = filename
        self.off_screen = off_screen
        self.bkg_on = False
        self.wireframe = False
        self.safe_mode = safe_mode
        if safe_mode:
            print('Running in safe mode with some features disabled.')
            print()
            self.view_params = (None, None, None)
            self.create_plotter()
            self.plotter.import_vrml(self.filename)
            self.counts = []
            self.visible = []
            self.meshes = []
        else:
            data = self.read_file()
            viewpoint_block, polyline_blocks, marker_blocks, solid_blocks = self.extract_blocks(data)
            self.view_params = self.parse_viewpoint_block(viewpoint_block)
            self.counts = [len(polyline_blocks), len(marker_blocks), len(solid_blocks)]
            self.visible = [True, True, True]
            self.meshes = self.create_meshes(polyline_blocks, marker_blocks, solid_blocks)
            self.create_plotter()
            self.plot_meshes()

        
    def read_file(self):
        '''
        Read the content of the file.
        '''
        print('Reading mesh data from ' + self.filename + '...')
        with open(self.filename, 'r') as f:
            data = f.read()
        return data
    
    
    def extract_blocks(self, file_content):
        '''
        Extract polyline, marker, and solid blocks from the file content.
        '''
        print('Parsing mesh data...')
        polyline_blocks = []
        marker_blocks = []
        solid_blocks = []
        viewpoint_block = None

        lines = file_content.split('\n')
        block = []
        inside_block = False
        brace_count = 0

        for line in lines:
            stripped_line = line.strip()

            if stripped_line.startswith('Shape') or stripped_line.startswith('Anchor')\
                or stripped_line.startswith('Viewpoint'):
                inside_block = True
                brace_count = 0
            
            if inside_block:
                block.append(line)
                brace_count += line.count('{') - line.count('}')
                
                if brace_count == 0:
                    block_content = '\n'.join(block)
                    
                    if 'IndexedLineSet' in block_content:
                        polyline_blocks.append(block_content)
                    elif 'Sphere' in block_content:
                        marker_blocks.append(block_content)
                    elif 'IndexedFaceSet' in block_content:
                        solid_blocks.append(block_content)
                    elif 'Viewpoint' in block_content:
                        viewpoint_block = block_content

                    block = []
                    inside_block = False

        return viewpoint_block, polyline_blocks, marker_blocks, solid_blocks
    
    
    def create_meshes(self, polyline_blocks, marker_blocks, solid_blocks):
        '''
        Create meshes from the polyline, marker, and solid blocks.
        '''
        print('Creating meshes...')
        meshes = []

        # tracks are saved as polyline blocks
        for block in polyline_blocks:
            points, indices, color = self.parse_polyline_block(block)
            lines = []
            for i in range(len(indices) - 1):
                if indices[i] != -1 and indices[i + 1] != -1:
                    lines.extend([2, indices[i], indices[i + 1]])
            line_mesh = pv.PolyData(points)
            if len(lines) > 0:
                line_mesh.lines = lines
            meshes.append((line_mesh, color, None))

        # energy depositions are saved as marker blocks
        for block in marker_blocks:
            center, radius, color = self.parse_marker_block(block)
            sphere = pv.Sphere(radius=radius, center=center)
            meshes.append((sphere, color, None))

        # geometry is saved as solid blocks
        for block in solid_blocks:
            points, indices, color, transparency = self.parse_solid_block(block)
            
            faces = []
            current_face = []
            for index in indices:
                if index == -1:
                    if len(current_face) == 3:
                        faces.extend([3] + current_face)
                    elif len(current_face) == 4:
                        faces.extend([4] + current_face)
                    current_face = []
                else:
                    current_face.append(index)
            
            faces = np.array(faces)
            solid_mesh = pv.PolyData(points, faces)
            meshes.append((solid_mesh, color, transparency))

        return meshes
    

    def parse_viewpoint_block(self, block):
        '''
        Parse the viewpoint block to get the field of view, position, and orientation.
        '''
        fov = None
        position = None
        orientation = None

        if block is not None:
            fov_match = re.search(r'fieldOfView\s+([\d.]+)', block)
            if fov_match:
                fov = float(fov_match.group(1))*180/np.pi
            
            position_match = re.search(r'position\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)', block)
            if position_match:
                position = [float(position_match.group(1)), float(position_match.group(2)), \
                            float(position_match.group(3))]

            orientation_match = re.search(r'orientation\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)', block)
            if orientation_match:
                orientation = [float(orientation_match.group(1)), float(orientation_match.group(2)), \
                               float(orientation_match.group(3)), float(orientation_match.group(4))*180/np.pi]
        
        return fov, position, orientation
    

    def parse_polyline_block(self, block):
        '''
        Parse a polyline block to get particle track information.
        '''
        coord = []
        coordIndex = []
        color = [1, 1, 1]

        lines = block.split('\n')
        reading_points = False
        reading_indices = False

        for line in lines:
            line = line.strip()
            if line.startswith('point ['):
                reading_points = True
                continue
            elif line.startswith(']'):
                reading_points = False
                reading_indices = False
                continue
            elif line.startswith('coordIndex ['):
                reading_indices = True
                continue
            elif 'diffuseColor' in line:
                color = list(map(float, re.findall(r'[-+]?\d*\.?\d+', line)))

            if reading_points:
                point = line.replace(',', '').split()
                if len(point) == 3:
                    coord.append(list(map(float, point)))
            elif reading_indices:
                indices = line.replace(',', '').split()
                coordIndex.extend(list(map(int, indices)))

        return np.array(coord), coordIndex, color
    

    def parse_marker_block(self, block):
        '''
        Parse a marker block to get hit information.
        '''
        coord = []
        color = [1, 1, 1]
        radius = 1

        lines = block.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith('translation'):
                point = line.split()[1:]
                if len(point) == 3:
                    coord = list(map(float, point))
            elif 'diffuseColor' in line:
                color = list(map(float, re.findall(r'[-+]?\d*\.?\d+', line)))
            elif 'radius' in line:
                radius = float(re.findall(r'[-+]?\d*\.?\d+', line)[0])

        return np.array(coord), radius, color
    

    def parse_solid_block(self, block):
        '''
        Parse a solid block to get geometry information.
        '''
        coord = []
        coordIndex = []
        color = [1, 1, 1]
        transparency = 0

        lines = block.split('\n')
        reading_points = False
        reading_indices = False

        for line in lines:
            line = line.strip()
            if line.startswith('point ['):
                reading_points = True
                continue
            elif line.startswith(']'):
                reading_points = False
                reading_indices = False
                continue
            elif line.startswith('coordIndex ['):
                reading_indices = True
                continue
            elif 'diffuseColor' in line:
                color = list(map(float, re.findall(r'[-+]?\d*\.?\d+', line)))
            elif 'transparency' in line:
                transparency = float(re.findall(r'[-+]?\d*\.?\d+', line)[0])

            if reading_points:
                point = line.replace(',', '').split()
                if len(point) == 3:
                    coord.append(list(map(float, point)))
            elif reading_indices:
                indices = line.replace(',', '').split()

                coordIndex.extend(list(map(int, indices)))

        return np.array(coord), coordIndex, color, transparency

    
    def create_plotter(self):
        '''
        Create a PyVista plotter.
        '''
        self.plotter = pv.Plotter(title='GeViewer — ' + str(Path(self.filename).resolve()),\
                                  off_screen=self.off_screen)
        self.plotter.add_key_event('c', self.save_screenshot)
        self.plotter.add_key_event('g', self.save_graphic)
        self.plotter.add_key_event('t', self.toggle_tracks)
        self.plotter.add_key_event('h', self.toggle_hits)
        self.plotter.add_key_event('b', self.toggle_background)
        # solid and wireframe rendering modes have key events by default
        self.plotter.add_key_event('d', self.set_window_size)
        self.plotter.add_key_event('p', self.set_camera_view)


    def set_camera_view(self,args=None):
        '''
        Set the camera viewpoint.
        '''
        if args is None:
            fov, position, up, zoom, elev, azim = asyncio.run(self.prompt_for_camera_view())
        else:
            fov, position, up, zoom, elev, azim = args
            print(fov,position,)
        if fov is not None:
            self.plotter.camera.view_angle = fov
        if position is not None:
            self.plotter.camera.position = position
        if up is not None:
            self.plotter.camera.up = up
        if zoom is not None:
            self.plotter.camera.zoom = zoom
        if elev is not None:
            self.plotter.camera.elevation = elev
        if azim is not None:
            self.plotter.camera.azimuth = azim
        if args is None:
            print('Camera view set.\n')

    
    async def prompt_for_camera_view(self):
        '''
        Asyncronously get camera view input from the terminal.
        '''
        print('Setting the camera position and orientation.')
        print('Press enter to skip any of the following prompts.')
        print('If the camera view is overdefined, later inputs will override earlier ones.')
        utils.clear_input_buffer()
        while(True):
            try:
                fov = await asyncio.to_thread(input, 'Enter the field of view in degrees: ')
                if fov == '':
                    fov = None
                    break
                fov = float(fov)
                break
            except ValueError:
                print('Error: invalid input. Please enter a number.')
        while(True):
            try:
                position = await asyncio.to_thread(input, 'Enter the position as three space-separated numbers: ')
                if position == '':
                    position = None
                    break
                position = list(map(float, position.split()))
                if len(position) != 3:
                    raise ValueError
                break
            except ValueError:
                print('Error: invalid input. Please enter three numbers separated by spaces.')
        while(True):
            try:
                up = await asyncio.to_thread(input, 'Enter the up vector as three space-separated numbers: ')
                if up == '':
                    up = None
                    break
                up = list(map(float, up.split()))
                if len(up) != 3:
                    raise ValueError
                break
            except ValueError:
                print('Error: invalid input. Please enter three numbers separated by spaces.')
        while(True):
            try:
                zoom = await asyncio.to_thread(input, 'Enter the zoom factor: ')
                if zoom == '':
                    zoom = None
                    break
                zoom = float(zoom)
                break
            except ValueError:
                print('Error: invalid input. Please enter a number.')
        while(True):
            try:
                elev = await asyncio.to_thread(input, 'Enter the elevation in degrees: ')
                if elev == '':
                    elev = None
                    break
                elev = float(elev)
                break
            except ValueError:
                print('Error: invalid input. Please enter a number.')
        while(True):
            try:
                azim = await asyncio.to_thread(input, 'Enter the azimuth in degrees: ')
                if azim == '':
                    azim = None
                    break
                azim = float(azim)
                break
            except ValueError:
                print('Error: invalid input. Please enter a number.')
        return fov, position, up, zoom, elev, azim


    def save_graphic(self):
        '''
        Save a high-quality graphic (ie a vector graphic) of the current view.
        '''
        file_path = asyncio.run(self.prompt_for_file_path('graphic', 'svg'))
        self.plotter.save_graphic(file_path)
        print('Graphic saved to ' + file_path + '\n')


    def save_screenshot(self):
        '''
        Save a screenshot (as a png) of the current view.
        '''
        file_path = asyncio.run(self.prompt_for_file_path('screenshot', 'png'))
        self.plotter.screenshot(file_path)
        print('Screenshot saved to ' + file_path + '\n')


    async def prompt_for_file_path(self,*args):
        '''
        Asynchronously get file path input from the terminal.
        '''
        print('Enter the file path to save the ' + args[0])
        utils.clear_input_buffer()
        file_path = await asyncio.to_thread(input,'  (e.g., /path/to/your_file.' + args[1] + '): ')
        
        return file_path
    

    def set_window_size(self):
        '''
        Set the window size in pixels.
        '''
        width, height = asyncio.run(self.prompt_for_window_size())
        self.plotter.window_size = width, height
        print('Window size set to ' + str(width) + 'x' + str(height) + '.\n')


    async def prompt_for_window_size(self):
        '''
        Asynchronously get window size input from the terminal.
        '''
        utils.clear_input_buffer()
        while(True):
            try:
                width = await asyncio.to_thread(input, 'Enter the window width in pixels: ')
                width = int(width)
                break
            except ValueError:
                print('Error: invalid input. Please enter an integer.')
        while(True):
            try:
                height = await asyncio.to_thread(input, 'Enter the window height in pixels: ')
                height = int(height)
                break
            except ValueError:
                print('Error: invalid input. Please enter an integer.')
        return width, height

    
    def plot_meshes(self):
        '''
        Add the meshes to the plot.
        '''
        print('Rendering meshes...')
        actors = []
        for mesh, color, transparency in tqdm(self.meshes):
            if transparency:
                opacity = 1. - transparency
            else:
                opacity = 1.
            actors.append(self.plotter.add_mesh(mesh, color=color, opacity=opacity))
        self.actors = actors
        print('Done.\n')
        

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
                
                
    def toggle_hits(self):
        '''
        Toggle the hits on and off.
        '''
        if not self.safe_mode:
            self.visible[2] = not self.visible[2]
            print('Toggling hits ' + ['on.','off.'][self.visible[2]])
            hit_actors = self.actors[sum(self.counts[:1]):sum(self.counts[:2])]
            if self.visible[2]:
                for actor in hit_actors:
                    actor.visibility = True
            else:
                for actor in hit_actors:
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
        self.plotter.show(before_close_callback=lambda x: print('\nExiting GeViewer.\n'))
