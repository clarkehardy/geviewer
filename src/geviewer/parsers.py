import numpy as np
import pyvista as pv
from lxml import etree
import re
import uuid
import time
import threading

from geviewer import geometry


class Parser:
    """Base class for all parsers.
    """

    def __init__(self, filename):
        """Initializes the parser.

        :param filename: The name of the file to parse.
        :type filename: str
        """
        self.filename = filename


    def initialize_template(self, name):
        """Initializes a template for a component.

        :param name: The name of the component.
        :type name: str
        :return: The initialized template.
        :rtype: dict
        """
        return  {'name': name, 'id': str(uuid.uuid4())[-12:], 'shape': '', 'points': [], 'mesh_points': [],\
                 'mesh_inds': [], 'colors': [], 'visible': True, 'scalars': [], 'is_dot': False, \
                 'is_event': False, 'mesh': None, 'has_actor': False, 'children': []}
    
    
    def combine_mesh_arrays(self, points, cells, colors):
        """Combines multiple mesh arrays into a single mesh.

        This function takes lists of points, indices of faces or line segments
        (called cells), and colors, and combines them into a single set of points,
        cells, and colors, adjusting indices appropriately.

        :param points: A list of arrays containing point coordinates.
        :type points: list of numpy.ndarray
        :param cells: A list of lists containing cell indices.
        :type cells: list of list
        :param colors: A list of arrays containing color data.
        :type colors: list of numpy.ndarray
        :return: The combined points, cells, and colors.
        :rtype: tuple
        """

        offsets = np.cumsum([0] + [len(p) for p in points[:-1]]).astype(int)
        points = np.concatenate(points)
        
        for i, cell in enumerate(cells):
            j = 0
            while j < len(cell):
                k = int(cell[j])
                start_idx = j + 1
                end_idx = j + k + 1
                
                cell[start_idx:end_idx] = (np.array(cell[start_idx:end_idx]) + int(offsets[i])).tolist()
                j += k + 1
        
        cells = np.concatenate(cells).astype(int)
        colors = np.concatenate(colors)

        return points, cells, colors


class VRMLParser(Parser):
    """Parser for VRML files.
    """

    def parse_file(self, progress_obj=None):
        """Parses the VRML file and creates the meshes.

        :param progress_obj: The progress object to use.
        :type progress_obj: geviewer.gui.GeProgressBar, optional
        """
        update = 'Reading VRML file...\n'
        if progress_obj:
            if progress_obj.sync_status(update=update): return
        else:
            print(update)
        data = self.read_file(self.filename)
        viewpoint_block, polyline_blocks, marker_blocks, solid_blocks = self.extract_blocks(data, progress_obj=progress_obj)
        self.viewpoint_block = viewpoint_block
        now = time.time()
        polyline_mesh, marker_mesh, solid_mesh = self.create_meshes(polyline_blocks, marker_blocks, solid_blocks, progress_obj=progress_obj)
        component_name = self.filename.split('/')[-1].split('.')[0]
        component = self.initialize_template(component_name)
        names = ['Trajectories', 'Step Markers', 'Geometry']
        for i, mesh in enumerate([polyline_mesh, marker_mesh, solid_mesh]):
            comp = self.initialize_template(names[i])
            comp['mesh'] = mesh
            if i<2:
                comp['is_event'] = True
            component['children'].append(comp)

        self.components = component


    def read_file(self, filename):
        """Reads the content of a file.

        :param filename: The path to the file to read.
        :type filename: str
        :return: A single string containing the content of the file.
        :rtype: str
        """
        data = []
        with open(filename, 'r') as f:
            for line in f:
                # don't read comments
                if not line.strip().startswith('#'):
                    data.append(line)
        data = ''.join(data)
        return data
    

    def create_meshes(self, polyline_blocks, marker_blocks, solid_blocks, progress_obj=None):
        """Creates and returns meshes for polylines, markers, and solids.

        This function processes blocks of data for polylines, markers, and solids,
        building corresponding meshes for each.

        :param polyline_blocks: List of blocks containing polyline data.
        :type polyline_blocks: list
        :param marker_blocks: List of blocks containing marker data.
        :type marker_blocks: list
        :param solid_blocks: List of blocks containing solid data.
        :type solid_blocks: list
        :param progress_obj: The progress object to use.
        :type progress_obj: geviewer.gui.GeProgressBar, optional
        :return: The created meshes.
        :rtype: tuple
        """
        update = 'Building meshes...\n'
        if progress_obj:
            if progress_obj.sync_status(update=update): return
        else:
            print(update)

        total = len(polyline_blocks) + len(marker_blocks) + len(solid_blocks)
        if progress_obj:
            progress_obj.reset_progress()
            progress_obj.set_maximum_value(total)
        polyline_mesh = self.build_mesh(polyline_blocks, 'polyline', progress_obj)
        marker_mesh = self.build_markers(marker_blocks, progress_obj)
        solid_mesh = self.build_mesh(solid_blocks, 'solid', progress_obj)

        if progress_obj:
            progress_obj.signal_finished()

        return polyline_mesh, marker_mesh, solid_mesh


    def build_mesh(self, blocks, which, progress_obj=None):
        """Builds a mesh for the given blocks.

        This function processes blocks of data for polylines, markers, and solids,
        building corresponding meshes for each.

        :param blocks: List of blocks containing data.
        :type blocks: list
        :param which: The type of mesh to build.
        :type which: str
        :param progress_obj: The progress object to use.
        :type progress_obj: geviewer.gui.GeProgressBar, optional
        :return: The created mesh.
        :rtype: pyvista.PolyData
        """
        points = [None for i in range(len(blocks))]
        cells = [None for i in range(len(blocks))]
        colors = [None for i in range(len(blocks))]

        if which == 'polyline':
            func = self.process_polyline_block
        elif which == 'solid':
            func = self.process_solid_block

        for i, block in enumerate(blocks):
            points[i], cells[i], color = func(block)
            colors[i] = [color]*len(points[i])
            if progress_obj:
                if progress_obj.sync_status(increment=True): return

        if len(points) == 0:
            return None
        
        points, cells, colors = self.combine_mesh_arrays(points, cells, colors)
        if func==self.process_polyline_block:
            mesh = pv.PolyData(points, lines=cells)
        elif func==self.process_solid_block:
            mesh = pv.PolyData(points, faces=cells)
        mesh.point_data.set_scalars(colors, name='color')

        return mesh


    def build_markers(self, blocks, progress_obj=None):
        """Builds a mesh for the given blocks.

        This function processes blocks of data for markers, creating a mesh for each.

        :param blocks: List of blocks containing data.
        :type blocks: list
        :param progress_obj: The progress object to use.
        :type progress_obj: geviewer.gui.GeProgressBar, optional
        :return: The created mesh.
        :rtype: pyvista.PolyData
        """
        centers = [None for i in range(len(blocks))]
        radii = [None for i in range(len(blocks))]
        colors = [None for i in range(len(blocks))]
        
        for i, block in enumerate(blocks):
            centers[i], radii[i], colors[i] = self.process_marker_block(block)
        if len(centers) == 0:
            return None
        
        mesh = pv.MultiBlock()
        for i in range(len(centers)):
            mesh.append(pv.Sphere(radius=radii[i], center=centers[i]))
            colors[i] = [colors[i]]*mesh[-1].n_points
            if progress_obj:
                if progress_obj.sync_status(increment=True): return

        colors = np.concatenate(colors)
        mesh = mesh.combine()
        mesh.point_data.set_scalars(colors, name='color')

        return mesh


    def extract_blocks(self, file_content, progress_obj=None):
        """Extracts polyline, marker, and solid blocks from the given file content.

        This function processes the provided file content, which is expected to
        be in a text format, and extracts blocks of different types based on
        specific keywords. It separates the blocks into categories: polyline,
        marker, and solid blocks, and also identifies the viewpoint block.

        :param file_content: The content of the file as a single string.
        :type file_content: str
        :param progress_obj: The progress object to use.
        :type progress_obj: geviewer.gui.GeProgressBar, optional
        :return: A tuple containing four elements:
            - The viewpoint block (if found) as a string or `None` if not found.
            - A list of polyline blocks as strings.
            - A list of marker blocks as strings.
            - A list of solid blocks as strings.
        :rtype: tuple
        """
        update = 'Parsing VRML file...\n'
        if progress_obj:
            if progress_obj.sync_status(update=update): return
        else:
            print(update)

        polyline_blocks = []
        marker_blocks = []
        solid_blocks = []
        viewpoint_block = None

        lines = file_content.split('\n')
        block = []
        inside_block = False
        brace_count = 0

        if progress_obj:
            progress_obj.reset_progress()
            progress_obj.set_maximum_value(len(lines))

        for i, line in enumerate(lines):
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

            if progress_obj:
                if progress_obj.sync_status(increment=True): return

        if progress_obj:
            progress_obj.signal_finished()

        return viewpoint_block, polyline_blocks, marker_blocks, solid_blocks


    def process_polyline_block(self, block):
        """Processes a polyline block to create a polyline mesh.

        This function takes a block of polyline data and converts it into a
        PyVista`PolyData` object representing the polyline mesh. It also
        extracts the color information associated with the mesh.

        :param block: The polyline block content as a string.
        :type block: str
        :return: A tuple containing:
            - A `pv.PolyData` object representing the polyline mesh.
            - The color associated with the polyline mesh as a list or array.
        :rtype: tuple
        """
        points, indices, color = self.parse_polyline_block(block)
        lines = []
        for i in range(len(indices) - 1):
            if indices[i] != -1 and indices[i + 1] != -1:
                lines.extend([2, indices[i], indices[i + 1]])
        
        return points, lines, color


    def process_marker_block(self, block):
        """Processes a marker block to create a marker mesh.

        This function takes a block of marker data and creates a spherical
        marker mesh using PyVista. It also extracts the color information
        associated with the marker.

        :param block: The marker block content as a string.
        :type block: str
        :return: A tuple containing:
            - A `pv.Sphere` object representing the marker mesh.
            - The color associated with the marker mesh as a list or array.
        :rtype: tuple
        """
        center, radius, color = self.parse_marker_block(block)

        return center, radius, color


    def process_solid_block(self, block):
        """Processes a solid block to create a solid mesh.

        This function takes a block of solid data and creates a mesh for a
        solid object using PyVista. It also extracts the color information
        associated with the solid.

        :param block: The solid block content as a string.
        :type block: str
        :return: A tuple containing:
            - A `pv.PolyData` object representing the solid mesh.
            - The color associated with the solid mesh as a list or array.
        :rtype: tuple
        """
        points, indices, color = self.parse_solid_block(block)
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

        return points, faces, color


    def parse_viewpoint_block(self, block):
        """Parses the viewpoint block to extract the field of view, position,
        and orientation.

        This function extracts the field of view (FOV), position, and orientation
        from a given viewpoint block in a 3D scene description. The FOV is converted
        from radians to degrees.

        :param block: The viewpoint block content as a string.
        :type block: str
        :return: A tuple containing:
            - The field of view in degrees as a float (or None if not found).
            - The position as a list of three floats [x, y, z] (or None if not found).
            - The orientation as a list of four floats [x, y, z, angle] in radians
            (or None if not found).
        :rtype: tuple
        """
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
                            float(orientation_match.group(3)), float(orientation_match.group(4))]
        
        return fov, position, orientation


    def parse_polyline_block(self, block):
        """Parses a polyline block to extract particle track information, including
        coordinates, indices, and color.

        This function processes a block of text representing a polyline in a 3D
        scene description. It extracts the coordinates of the points that define
        the polyline, the indices that describe the lines between these points, 
        and the color associated with the polyline.

        :param block: The polyline block content as a string.
        :type block: str
        :return: A tuple containing:
            - `coords`: An array of shape (N, 3) representing the coordinates of the
            polyline points.
            - `indices`: An array of integers representing the indices that define
            the polyline segments.
            - `color`: An array of four floats representing the RGBA color of the
            polyline, where the alpha is set to 1.
        :rtype: tuple
        """
        coords = []
        coord_inds = []
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
                    coords.append(list(map(float, point)))
            elif reading_indices:
                indices = line.replace(',', '').split()
                coord_inds.extend(list(map(int, indices)))

        color.append(1.)

        return np.array(coords), np.array(coord_inds), np.array(color)


    def parse_marker_block(self, block):
        """Parses a marker block to extract the position, radius, and color of a marker.

        This function processes a block of text representing a marker in a 3D scene
        description. It extracts the position of the marker, the radius of the marker
        (typically a sphere), and the color of the marker. It also accounts for
        transparency and adjusts the alpha value of the color accordingly.

        :param block: The marker block content as a string.
        :type block: str
        :return: A tuple containing:
            - `coords`: An array of shape (3,) representing the position of the marker
            in 3D space.
            - `radius`: A float representing the radius of the marker.
            - `color`: An array of four floats representing the RGBA color of the marker,
            where alpha is adjusted for transparency.
        :rtype: tuple
        """
        coords = []
        color = [1, 1, 1]
        transparency = 0
        radius = 1

        lines = block.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith('translation'):
                point = line.split()[1:]
                if len(point) == 3:
                    coords = list(map(float, point))
            elif 'diffuseColor' in line:
                color = list(map(float, re.findall(r'[-+]?\d*\.?\d+', line)))
            elif 'transparency' in line:
                transparency = float(re.findall(r'[-+]?\d*\.?\d+', line)[0])
            elif 'radius' in line:
                radius = float(re.findall(r'[-+]?\d*\.?\d+', line)[0])

        color.append(1. - transparency)

        return np.array(coords), radius, np.array(color)


    def parse_solid_block(self, block):
        """Parses a solid block to extract geometry information for a 3D
        solid object.

        This function processes a block of text representing a solid object
        in a 3D scene description. It extracts the vertex coordinates, the face
        indices that define the geometry of the solid, and the color of the solid.
        The function also handles transparency by adjusting the alpha value in the
        color array.

        :param block: The solid block content as a string.
        :type block: str
        :return: A tuple containing:
            - `coords`: An array of shape (N, 3) where N is the number of vertices,
            representing the vertex coordinates.
            - `coord_inds`: An array of shape (M,) where M is the number of indices,
            representing the indices defining the faces of the solid.
            - `color`: An array of four floats representing the RGBA color of the solid,
            where the alpha value is adjusted for transparency.
        :rtype: tuple
        """
        coords = []
        coord_inds = []
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
                    coords.append(list(map(float, point)))
            elif reading_indices:
                indices = line.replace(',', '').split()
                coord_inds.extend(list(map(int, indices)))

        color.append(1. - transparency)

        return np.array(coords), np.array(coord_inds), np.array(color)


class HepRepParser(Parser):
    """Parser for HepRep files.
    """

    def parse_file(self, progress_obj=None):
        """Parses the HepRep file and creates the meshes.

        :param progress_obj: The progress object to use for the progress bar.
        :type progress_obj: ProgressBar, optional
        """
        if progress_obj:
            print_func = progress_obj.print_update
        else:
            print_func = print

        print_func('Parsing HepRep file...\n')
        if progress_obj:
            progress_obj.reset_progress()
            progress_obj.set_maximum_value(0)

        # approximate total number of elements from number of lines in file
        with open(self.filename, 'r') as f:
            total_elements = sum(1 for _ in f) // 2

        if total_elements > 1e6:
            print_func('This step should take less than {:.0f} seconds.\n'.format(total_elements/1e6))

        self.root = self.parse_xml(self.filename)
        if progress_obj:
            progress_obj.signal_finished()

        component_name = self.filename.split('/')[-1].split('.')[0]
        seed_component = self.initialize_template(component_name)
        self.event_number = 0
        self.num_components = 0
        print_func('Extracting components...\n')

        if progress_obj:
            progress_obj.reset_progress()
            progress_obj.set_maximum_value(total_elements)

        self.populate_meshes(self.root, seed_component, progress_obj=progress_obj)
        self.components = [seed_component]

        if progress_obj:
            progress_obj.signal_finished()
        
        print_func('Building meshes...\n')

        if progress_obj:
            progress_obj.reset_progress()
            progress_obj.set_maximum_value(self.num_components)
        
        self.create_meshes(self.components, progress_obj=progress_obj)
        self.reduce_components(self.components)
        self.build_mesh_objects(self.components)

        if progress_obj:
            progress_obj.signal_finished()


    def parse_xml(self, xml_file):
        """Parses the HepRep file and returns the root element.
        """
        tree = etree.parse(xml_file)
        root = tree.getroot()
        return root


    def populate_meshes(self, element, component, level=-1, progress_obj=None):
        """Populates the meshes for the given element.

        :param element: The element to populate.
        :type element: xml.etree.ElementTree.Element
        :param component: The component to populate.
        :type component: dict
        :param level: The recursion level.
        :type level: int
        :param progress_obj: The progress object to use for the progress bar.
        :type progress_obj: ProgressBar, optional
        """
        if progress_obj:
            if progress_obj.sync_status(increment=True): return
        
        if element.tag.endswith('instance'):
            # children of instances are attvalues and one primitive
            # loop through the attvalues and set the attributes
            for child in element:
                if progress_obj:
                    if progress_obj.sync_status(increment=True): return

                # get the attributes
                if child.tag.endswith('attvalue'):
                    self.process_attvalue(child, component)

                # now get the point data from the primitive
                elif child.tag.endswith('primitive'):
                    points = []
                    for grandchild in child:
                        if progress_obj:
                            if progress_obj.sync_status(increment=True): return
                            
                        if grandchild.tag.endswith('point'):
                            points.append([float(grandchild.attrib['x']), \
                                           float(grandchild.attrib['y']), \
                                           float(grandchild.attrib['z'])])
                        elif grandchild.tag.endswith('attvalue') and grandchild.attrib['name'].startswith('Radius'):
                            points.append(float(grandchild.attrib['value']))
                    component['points'].append(points)

                # if the child is a type, call the function recursively
                elif child.tag.endswith('type'):
                    self.populate_meshes(child, component, level, progress_obj)

        elif element.tag.endswith('type'):
            # children of types are instances or attvalues
            is_event = False
            name_split = element.attrib['name'].split('_')
            if name_split[-1].isnumeric():
                name = '_'.join(name_split[:-1])
            else:
                name = element.attrib['name']
            if name == 'Event Data':
                self.event_number += 1
            if self.event_number > 0 and (name == 'TransientPolylines' or \
                                          name == 'Hits'):
                # these seem to contain the same information as trajectories
                # so skip them for now
                return
            elif self.event_number > 0 and name == 'Trajectories':
                name = 'Event {} '.format(self.event_number) + name
                is_event = True
                self.event_number += 1
            elif self.event_number > 0 and name == 'Trajectory Step Points':
                is_event = True

            child_component = self.initialize_template(name)
            child_component['is_event'] = is_event

            for child in element:
                if progress_obj:
                    if progress_obj.sync_status(increment=True): return

                if child.tag.endswith('attvalue'):
                    self.process_attvalue(child, child_component)

                elif child.tag.endswith('instance'):
                    self.num_components += 1
                    instance_component = self.initialize_template(name)
                    instance_component['is_event'] = is_event

                    # copy attributes from child_component to instance_component
                    self.copy_parent_attvalues(child_component, instance_component)

                    self.populate_meshes(child, instance_component, level, progress_obj)
                    component['children'].append(instance_component)

            # if no instances were found, add the child_component itself
            if not component['children']:
                component['children'].append(child_component)

        # if not dealing with an instance, try again with each of the children
        else:
            for child in element:
                self.populate_meshes(child, component, level, progress_obj)

        
    def process_attvalue(self, child, component):
        """Processes the attvalue to set the attributes of the component.

        :param child: The attvalue to process.
        :type child: xml.etree.ElementTree.Element
        :param component: The component to set the attributes for.
        :type component: dict
        """
        if child.attrib['name'] == 'DrawAs':
            component['shape'] = child.attrib['value']
        elif child.attrib['name'] == 'LineColor':
            color_str = child.attrib['value']
            color = [float(i)/255. for i in color_str.split(',')]
            component['colors'] = [color]
        elif child.attrib['name'] == 'MarkColor':
            color_str = child.attrib['value']
            color = [float(i)/255. for i in color_str.split(',')]
            component['colors'] = [color]
            component['is_dot'] = True
        elif child.attrib['name'] == 'Visibility':
            component['visible'] = child.attrib['value'] == 'True'


    def copy_parent_attvalues(self, parent, child):
        """Copies the parent attributes to the child.

        :param parent: The parent component.
        :type parent: dict
        :param child: The child component.
        :type child: dict
        """
        child['shape'] = parent['shape']
        child['colors'] = [] if not parent['colors'] else [parent['colors'][0]]
        child['is_dot'] = parent['is_dot']
        child['visible'] = parent['visible']


    def create_meshes(self, components, progress_obj=None):
        """Creates the meshes for the given components.

        :param components: The list of components to create meshes for.
        :type components: list
        """
        for comp in components:
            if progress_obj:
                if progress_obj.sync_status(increment=True): return

            if comp['shape'] == 'Prism':
                comp['mesh_points'] = np.array(comp['points'])
                comp['mesh_inds'] = [[4, 0, 1, 2, 3,\
                                      4, 4, 5, 1, 0,\
                                      4, 7, 4, 0, 3,\
                                      4, 6, 7, 3, 2,\
                                      4, 5, 6, 2, 1,\
                                      4, 7, 6, 5, 4]]
                comp['scalars'] = [comp['colors']*len(comp['points'][0])]
                
            elif comp['shape'] == 'Cylinder':
                points = []
                inds = []
                scalars = []
                if len(comp['points']) == 1:
                    pt, ind = geometry.create_cylinder_mesh(
                        comp['points'][0][2], comp['points'][0][3], \
                        comp['points'][0][0], comp['points'][0][1])
                    points.append(pt)
                    inds.append(ind)
                    scalars.append(comp['colors']*len(pt))
                elif len(comp['points']) == 2:
                    pt, ind = geometry.create_annular_cylinder_mesh(
                        comp['points'][0][2], comp['points'][0][3], \
                        comp['points'][0][0], comp['points'][0][1], \
                        comp['points'][1][0], comp['points'][1][1])
                    points.append(pt)
                    inds.append(ind)
                    scalars.append(comp['colors']*len(pt))
                comp['mesh_points'] = points
                comp['mesh_inds'] = inds
                comp['scalars'] = scalars

            elif comp['shape'] == 'Polygon':
                comp['mesh_points'] = [np.concatenate(comp['points'])]
                unique_points, indices, inverse = np.unique(comp['mesh_points'][0], axis=0,
                                                            return_index=True, return_inverse=True)
                comp['mesh_points'] = [unique_points]

                inds = []
                this_ind = 0
                for point in comp['points']:
                    ind = [len(point)]
                    ind.extend(inverse[this_ind:this_ind + len(point)])
                    this_ind += len(point)
                    inds.append(ind)

                quad_faces = [face for face in inds if len(face) == 5]
                tri_faces = [face for face in inds if len(face) == 4]
                quad_faces = np.unique(np.array(quad_faces), axis=0)
                tri_faces = np.unique(np.array(tri_faces), axis=0)
                comp['mesh_inds'] = [np.concatenate([quad_faces.flatten(), tri_faces.flatten()])]
                comp['scalars'] = [comp['colors'] * len(comp['mesh_points'][0])]

            elif comp['shape'] == 'Point':
                comp['mesh_points'] = np.array(comp['points'])
                comp['mesh_inds'] = [np.array(())]*len(comp['mesh_points'])
                comp['scalars'] = [comp['colors']*len(m) for m in comp['mesh_points']]

            elif comp['shape'] == 'Line':
                comp['mesh_points'] = [np.concatenate(comp['points'])]
                point_inds = np.arange(len(comp['mesh_points'][0]))
                inds = []
                this_ind = 0
                for point in comp['points']:
                    ind = [len(point)]
                    ind.extend(point_inds[this_ind:this_ind + len(point)])
                    this_ind += len(point)
                    inds.append(ind)
                comp['mesh_inds'] = [np.concatenate(inds)]
                comp['scalars'] = [np.concatenate([[color]*len(point) for color, point in \
                                                   zip(comp['colors'], comp['points'])])]

            if len(comp['children']) > 0:
                self.create_meshes(comp['children'], progress_obj)


    def build_mesh_objects(self, components):
        """Draws the meshes for the given components.

        :param components: The list of components to draw meshes for.
        :type components: list
        """
        for comp in components:
            if len(comp['children']) > 0:
                self.build_mesh_objects(comp['children'])
            shape = None
            if comp['shape'] == 'Prism' and len(comp['mesh_points']) > 0 and comp['visible']:
                for i, points in enumerate(comp['mesh_points']):
                    shape = pv.PolyData(points, faces=comp['mesh_inds'][i])

            elif comp['shape'] == 'Cylinder' and comp['visible']:
                for i, points in enumerate(comp['mesh_points']):
                    shape = pv.PolyData(points, faces=comp['mesh_inds'][i])

            elif comp['shape'] == 'Polygon' and comp['visible']:
                for i, points in enumerate(comp['mesh_points']):
                    shape = pv.PolyData(points, faces=comp['mesh_inds'][i])

            elif comp['shape'] == 'Point' and comp['visible']:
                for i, points in enumerate(comp['mesh_points']):
                    shape = pv.PolyData(points)

            elif comp['shape'] == 'Line' and comp['visible']:
                for i, points in enumerate(comp['mesh_points']):
                    shape = pv.PolyData(points, lines=comp['mesh_inds'][i])
            else:
                continue

            if shape is not None:
                shape.point_data.set_scalars(comp['scalars'][i], name='color')

                if shape.n_open_edges > 0:
                    shape, success = self.repair_mesh(shape)

                comp['mesh'] = shape


    def repair_mesh(self, mesh):
        """Attempts to repair the given mesh.
        
        :param mesh: The mesh to repair.
        :type mesh: pv.PolyData
        :return: A tuple containing the repaired mesh and a boolean indicating
            whether the mesh was repaired.
        :rtype: tuple
        """

        cleaned = mesh.clean()
        if cleaned.n_open_edges == 0:
            return cleaned, True
        triangulated = mesh.triangulate()
        if triangulated.n_open_edges == 0:
            return triangulated, True
        else:
            cleaned = triangulated.clean()
            if cleaned.n_open_edges == 0:
                return cleaned, True
        surface = mesh.extract_surface()
        if surface.n_open_edges == 0:
            return surface, True
        else:
            cleaned = surface.clean()
            if cleaned.n_open_edges == 0:
                return cleaned, True
        length = np.linalg.norm(mesh.bounds[1] - mesh.bounds[0])
        filled = mesh.fill_holes(1e-2*length)
        if filled.n_open_edges == 0:
            return filled, True
        else:
            cleaned = filled.clean()
            if cleaned.n_open_edges == 0:
                return cleaned, True

        return mesh, False


    def combine_dicts(self, dicts):
        """Combines the given dictionaries into a single dictionary.

        :param dicts: The list of dictionaries to combine.
        :type dicts: list
        """
        if len(dicts) < 2:
            return dicts[0]
        result = self.initialize_template(dicts[0]['name'])
        result['shape'] = dicts[0]['shape']
        result['visible'] = dicts[0]['visible']
        result['is_dot'] = dicts[0]['is_dot']
        result['is_event'] = dicts[0]['is_event']

        # combine elements in a single dictionary first
        for j in range(len(dicts)):
            if len(dicts[j]['mesh_points']) > 1:
                points, cells, colors = self.combine_mesh_arrays(
                    [dicts[j]['mesh_points'][i] for i in range(len(dicts[j]['mesh_points']))],
                    [dicts[j]['mesh_inds'][i] for i in range(len(dicts[j]['mesh_points']))],
                    [dicts[j]['scalars'][i] for i in range(len(dicts[j]['mesh_points']))])
                dicts[j]['mesh_points'] = [points]
                dicts[j]['mesh_inds'] = [cells]
                dicts[j]['scalars'] = [colors]

        # then combine the dictionaries
        points, cells, colors = self.combine_mesh_arrays(
            [dicts[i]['mesh_points'][0] for i in range(len(dicts))],
            [dicts[i]['mesh_inds'][0] for i in range(len(dicts))],
            [dicts[i]['scalars'][0] for i in range(len(dicts))])
        result['mesh_points'] = [points]
        result['mesh_inds'] = [cells]
        result['scalars'] = [colors]
        children = []
        for d in dicts:
            children.extend(d['children'])
        result['children'] = children
        return result
    
    
    def reduce_components(self, components):
        """Reduces the components by combining duplicate children.

        :param components: The list of components to reduce.
        :type components: list
        """
        for comp in components:
            if len(comp['children']) > 1:
                names = []
                for child in comp['children']:
                    if child['name'] not in names:
                        names.append(child['name'])
                reduced = []
                for name in names:
                    to_combine = [child for child in comp['children'] if child['name'] == name]
                    if len(to_combine) > 1:
                        combined = self.combine_dicts(to_combine)
                        reduced.append(combined)
                    else:
                        reduced.append(to_combine[0])
                comp['children'] = reduced
            self.reduce_components(comp['children'])

        return components
