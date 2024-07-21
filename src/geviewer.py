import numpy as np
import pyvista as pv
import re
import asyncio
from tqdm import tqdm


class GeViewer:

    def __init__(self, filename, quick_plot=False):
        '''
        Read data from a file and create meshes from it.
        '''
        self.print_instructions()
        self.filename = filename
        self.bkg_on = False
        self.wireframe = False
        self.quick_plot = quick_plot
        if quick_plot:
            print('Running in quick plot mode with some features disabled.')
            print()
            self.create_plotter()
            self.plotter.import_vrml(self.filename)
            self.counts = []
            self.visible = []
            self.meshes = []
        else:
            data = self.read_file()
            polyline_blocks, marker_blocks, solid_blocks = self.extract_blocks(data)
            self.counts = [len(polyline_blocks), len(marker_blocks), len(solid_blocks)]
            self.visible = [True, True, True]
            self.meshes = self.create_meshes(polyline_blocks, marker_blocks, solid_blocks)
            self.create_plotter()
            self.plot_meshes()


    def print_instructions(self):
        '''
        Print the instructions for the user.
        '''
        print()
        print('#################################################')
        print('#                                               #')
        print('#                     GeViewer                  #')
        print('#                                               #')
        print('#################################################')
        print()
        print('Instructions:')
        print('-------------')
        print('* Click and drag to rotate the view, shift + click')
        print('  and drag to pan, and scroll to zoom')
        print('* Press "c" to capture a screenshot of the current view')
        print('* Press "g" to save a higher quality graphic')
        print('* Press "t" to toggle the tracks on or off')
        print('* Press "d" to toggle energy deposition on or off')
        print('* Press "b" to toggle the background on or off')
        print('* Press "w" to switch to a wireframe rendering mode')
        print('* Press "s" to switch to a solid rendering mode')
        print('* Press "q" or "e" to quit the viewer')
        print()

        
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

        lines = file_content.split('\n')
        block = []
        inside_block = False
        brace_count = 0

        for line in lines:
            stripped_line = line.strip()

            if stripped_line.startswith('Shape') or stripped_line.startswith('Anchor'):
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

                    block = []
                    inside_block = False

        return polyline_blocks, marker_blocks, solid_blocks
    
    
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
    

    def parse_polyline_block(self, block):
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
        self.plotter = pv.Plotter(title='GeViewer — ' + self.filename)
        self.plotter.add_key_event('c', self.save_screenshot)
        self.plotter.add_key_event('g', self.save_graphic)
        self.plotter.add_key_event('t', self.toggle_tracks)
        self.plotter.add_key_event('d', self.toggle_energy_deps)
        self.plotter.add_key_event('b', self.toggle_background)
        # solid and wireframe rendering modes have key events by default


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
        Asynchronously get input from the terminal.
        '''
        print('Enter the file path to save the ' + args[0])
        file_path = await asyncio.to_thread(input,'  (e.g., /path/to/your_file.' + args[1] + '): ')
        
        return file_path
    
    
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
        if not self.quick_plot:
            self.visible[0] = not self.visible[0]
            print('Toggling particle tracks ' + ['on.','off.'][self.visible[0]])
            track_actors = self.actors[:self.counts[0]]
            if self.visible[0]:
                for actor in track_actors:
                    actor.visibility = True
            else:
                for actor in track_actors:
                    actor.visibility = False
            self.plotter.update()
        else:
            print('This feature is disabled in quick plot mode.')
                
                
    def toggle_energy_deps(self):
        '''
        Toggle the energy depositions on and off.
        '''
        if not self.quick_plot:
            self.visible[2] = not self.visible[2]
            print('Toggling energy depositions ' + ['on.','off.'][self.visible[2]])
            edep_actors = self.actors[sum(self.counts[:1]):sum(self.counts[:2])]
            if self.visible[2]:
                for actor in edep_actors:
                    actor.visibility = True
            else:
                for actor in edep_actors:
                    actor.visibility = False
            self.plotter.update()
        else:
            print('This feature is disabled in quick plot mode.')


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
        self.plotter.update()

    
    def toggle_wireframe(self):
        '''
        Toggle between wireframe and solid rendering.
        '''
        self.wireframe = not self.wireframe
        print('Toggling rendering mode to ' + ['solid.','wireframe.'][self.wireframe])
        for actor in self.actors:
            if self.wireframe:
                actor.prop.SetRepresentationToWireframe()
            else:
                actor.prop.SetRepresentationToSurface()
        self.plotter.update()


    def show(self):
        '''
        Show the plotting window.
        '''
        self.plotter.show()
