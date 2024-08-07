import numpy as np
import pyvista as pv
import xml.etree.ElementTree as ET
from tqdm import tqdm
import re
import uuid
from geviewer import utils


class Parser:


    def __init__(self, filename):
        self.filename = filename


    def initialize_template(self, name):
        return  {'name': name, 'id': str(uuid.uuid4()), 'shape': [], 'points': [], 'mesh_points': [],\
                 'mesh_inds': [], 'colors': [], 'visible': [], 'scalars': [],\
                 'is_dot': None, 'mesh': None, 'actor': None, 'children': []}
    
    
    def combine_mesh_arrays(self, points, cells, colors, progress_obj=None):
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
        :param pbar: (Optional) A tqdm progress bar instance.
        :type pbar: tqdm.tqdm, optional

        :returns: A tuple containing three elements:
            - points (numpy.ndarray): Combined array of point coordinates.
            - cells (numpy.ndarray): Combined array of cell indices.
            - colors (numpy.ndarray): Combined array of color data.
        :rtype: tuple
        """
        offsets = np.cumsum([0] + [len(p) for p in points[:-1]]).astype(int)
        points = np.concatenate(points)
        for i, cell in enumerate(cells):
            j = 0
            while j < len(cell):
                k = cell[j]
                cell[j + 1:j + k + 1] = (np.array(cell[j + 1:j + k + 1]) + offsets[i]).tolist()
                j += k + 1
        cells = np.concatenate(cells).astype(int)
        colors = np.concatenate(colors)
        if progress_obj:
            progress_obj.value += 1
            if progress_obj.value % 10== 0:
                progress_obj.progress.emit(progress_obj.value)
        return points, cells, colors
    


class VRMLParser(Parser):

    def parse_file(self):
        data = utils.read_file(self.filename)
        viewpoint_block, polyline_blocks, marker_blocks, solid_blocks = self.extract_blocks(data)
        self.viewpoint_block = viewpoint_block
        polyline_mesh, marker_mesh, solid_mesh = self.create_meshes(polyline_blocks, marker_blocks, solid_blocks)
        component_name = self.filename.split('/')[-1].split('.')[0]
        component = self.initialize_template(component_name)
        names = ['Trajectories', 'Step Markers', 'Geometry']
        for i,mesh in enumerate([polyline_mesh, marker_mesh, solid_mesh]):
            comp = self.initialize_template(names[i])
            comp['mesh'] = mesh
            component['children'].append(comp)

        self.components = component
    

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

        :returns: A tuple containing three elements:
            - polyline_mesh (:class:`pyvista.PolyData`): Mesh for polylines.
            - marker_mesh (:class:`pyvista.UnstructuredGrid`): Mesh for markers.
            - solid_mesh (:class:`pyvista.PolyData`): Mesh for solids.
        :rtype: tuple
        """
        total = len(polyline_blocks) + len(marker_blocks) + len(solid_blocks)
        if progress_obj:
            progress_obj.max_range.emit(total)
            progress_obj.progress.emit(0)
        polyline_mesh = self.build_mesh(polyline_blocks, 'polyline', progress_obj)
        marker_mesh = self.build_markers(marker_blocks, progress_obj)
        solid_mesh = self.build_mesh(solid_blocks, 'solid', progress_obj)

        return polyline_mesh, marker_mesh, solid_mesh


    def build_mesh(self, blocks, which, progress_obj=None):
        """Builds a mesh from given blocks of data.

        This function processes blocks of data, creating a mesh based on the specified
        type ('polyline' or 'solid').

        :param blocks: List of blocks containing data for the mesh.
        :type blocks: list
        :param which: Type of mesh to build ('polyline' or 'solid').
        :type which: str
        :param pbar: (Optional) A tqdm progress bar instance.
        :type pbar: tqdm.tqdm, optional

        :returns: The created mesh with combined points, cells, and colors.
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
                progress_obj.value += 1
                if progress_obj.value % 10== 0:
                    progress_obj.progress.emit(progress_obj.value)

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
        """Builds a mesh for markers from given blocks of data.

        This function processes blocks of marker data, creating a mesh of spheres for each marker.

        :param blocks: List of blocks containing marker data.
        :type blocks: list
        :param pbar: (Optional) A tqdm progress bar instance.
        :type pbar: tqdm.tqdm, optional

        :returns: The created mesh with combined centers, radii, and colors.
        :rtype: pyvista.UnstructuredGrid
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
                progress_obj.value += 1
                if progress_obj.value % 10== 0:
                    progress_obj.progress.emit(progress_obj.value)

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
        :return: A tuple containing four elements:
            - The viewpoint block (if found) as a string or `None` if not found.
            - A list of polyline blocks as strings.
            - A list of marker blocks as strings.
            - A list of solid blocks as strings.
        :rtype: tuple
        """
        polyline_blocks = []
        marker_blocks = []
        solid_blocks = []
        viewpoint_block = None

        lines = file_content.split('\n')
        block = []
        inside_block = False
        brace_count = 0

        if progress_obj:
            progress_obj.max_range.emit(len(lines))

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
                progress_obj.value += 1
                if progress_obj.value % 10== 0:
                    progress_obj.progress.emit(progress_obj.value)

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

    def parse_file(self):
        self.root = self.parse_geometry(self.filename)
        component_name = self.filename.split('/')[-1].split('.')[0]
        self.components = [self.initialize_template(component_name)]
        self.populate_meshes(self.root, self.components)
        self.create_meshes(self.components)
        self.reduce_components(self.components)
        self.draw_mesh(self.components)


    def parse_geometry(self, xml_file):
        tree = ET.parse(xml_file)
        root = tree.getroot()
        return root


    def populate_meshes(self, element, components, level=-1):
        for child in element:
            index = 0
            if child.tag.endswith('instance'):
                self.populate_meshes(child, components, level + 1)
            elif child.tag.endswith('attvalue') and child.attrib['name'] == 'DrawAs':
                components[index]['shape'] = child.attrib['value']
            elif child.tag.endswith('attvalue') and child.attrib['name'] == 'LineColor':
                color_str = child.attrib['value']
                color = [float(i)/255. for i in color_str.split(',')]
                components[index]['colors'] = [np.array(color)]
            elif child.tag.endswith('attvalue') and child.attrib['name'] == 'MarkColor':
                color_str = child.attrib['value']
                color = [float(i)/255. for i in color_str.split(',')]
                components[index]['colors'] = [np.array(color)]
                components[index]['is_dot'] = True
            elif child.tag.endswith('attvalue') and child.attrib['name'] == 'Visibility':
                components[index]['visible'] = child.attrib['value'] == 'True'
            elif child.tag.endswith('primitive'):
                points = []
                for grandchild in child:
                    if grandchild.tag.endswith('point'):
                        points.append([float(grandchild.attrib['x']), \
                                       float(grandchild.attrib['y']), \
                                       float(grandchild.attrib['z'])])
                    elif grandchild.tag.endswith('attvalue') and grandchild.attrib['name'].startswith('Radius'):
                        points.append(float(grandchild.attrib['value']))
                components[index]['points'].append(points)
            elif child.tag.endswith('type'):
                name_split = child.attrib['name'].split('_')
                if name_split[-1].isnumeric():
                    name = '_'.join(name_split[:-1])
                else:
                    name = child.attrib['name']
                child_component = self.initialize_template(name)
                self.populate_meshes(child, [child_component], level + 1)
                components[index]['children'].append(child_component)
                    
                index += 1


    def create_meshes(self, components):
        for comp in components:
            if len(comp['children']) > 0:
                self.create_meshes(comp['children'])
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
                for point_set in comp['points']:
                    pt, ind = create_cylinder_mesh(point_set[2], point_set[3], \
                                                   point_set[0], point_set[1])
                    points.append(pt)
                    inds.append(ind)
                    scalars.append(comp['colors']*len(pt))
                comp['mesh_points'] = points
                comp['mesh_inds'] = inds
                comp['scalars'] = scalars

            elif comp['shape'] == 'Polygon':
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
                comp['scalars'] = [comp['colors']*len(comp['mesh_points'][0])]

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
                comp['scalars'] = [comp['colors']*len(comp['mesh_points'][0])]


    def draw_mesh(self, components):
        for comp in components:
            if len(comp['children']) > 0:
                self.draw_mesh(comp['children'])
            if comp['shape'] == 'Prism' and len(comp['mesh_points']) > 0 and comp['visible']:
                for i, points in enumerate(comp['mesh_points']):
                    shape = pv.PolyData(points, faces=comp['mesh_inds'][i])
                    shape.point_data.set_scalars(comp['scalars'][i], name='color')
                    comp['mesh'] = shape

            elif comp['shape'] == 'Cylinder' and comp['visible']:
                for i, points in enumerate(comp['mesh_points']):
                    shape = pv.PolyData(points, faces=comp['mesh_inds'][i])
                    shape.point_data.set_scalars(comp['scalars'][i], name='color')
                    comp['mesh'] = shape

            elif comp['shape'] == 'Polygon' and comp['visible']:
                for i, points in enumerate(comp['mesh_points']):
                    shape = pv.PolyData(points, faces=comp['mesh_inds'][i])
                    shape.point_data.set_scalars(comp['scalars'][i], name='color')
                    comp['mesh'] = shape

            elif comp['shape'] == 'Point' and comp['visible']:
                for i, points in enumerate(comp['mesh_points']):
                    shape = pv.PolyData(points)
                    shape.point_data.set_scalars(comp['scalars'][i], name='color')
                    comp['mesh'] = shape

            elif comp['shape'] == 'Line' and comp['visible']:
                for i, points in enumerate(comp['mesh_points']):
                    shape = pv.PolyData(points, lines=comp['mesh_inds'][i])
                    shape.point_data.set_scalars(comp['scalars'][i], name='color')
                    comp['mesh'] = shape


    def combine_dicts(self, dicts):
        if len(dicts) < 2:
            return dicts[0]
        result = self.initialize_template(dicts[0]['name'])
        result['shape'] = dicts[0]['shape']
        result['visible'] = dicts[0]['visible']
        result['is_dot'] = dicts[0]['is_dot']

        # combine elements in a single dictionary first
        for j in range(len(dicts)):
            if len(dicts[j]['mesh_points']) > 1:
                points, cells, colors = self.combine_mesh_arrays([dicts[j]['mesh_points'][i] for i in range(len(dicts[j]['mesh_points']))],\
                                                                 [dicts[j]['mesh_inds'][i] for i in range(len(dicts[j]['mesh_points']))],\
                                                                 [dicts[j]['scalars'][i] for i in range(len(dicts[j]['mesh_points']))])
                dicts[j]['mesh_points'] = [points]
                dicts[j]['mesh_inds'] = [cells]
                dicts[j]['scalars'] = [colors]

        # then combine the dictionaries
        points, cells, colors = self.combine_mesh_arrays([dicts[i]['mesh_points'][0] for i in range(len(dicts))],\
                                                         [dicts[i]['mesh_inds'][0] for i in range(len(dicts))],\
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


def create_cylinder_mesh(p1, p2, r1, r2, num_segments=20):
    """
    Create a mesh for a cylinder-like object defined by two endpoints and two radii.
    
    Parameters:
    - p1: tuple (x, y, z) for the first endpoint
    - p2: tuple (x, y, z) for the second endpoint
    - r1: radius at the first endpoint
    - r2: radius at the second endpoint
    - num_segments: number of segments to discretize the circle
    
    Returns:
    - points: list of (x, y, z) coordinates
    - indices: list of indices defining the quadrilateral faces
    """
    # Convert endpoints to numpy arrays
    p1 = np.array(p1)
    p2 = np.array(p2)
    
    # Vector along the cylinder axis
    axis = p2 - p1
    length = np.linalg.norm(axis)
    axis = axis / length
    
    # Arbitrary vector not parallel to axis
    if axis[0] != 0 or axis[1] != 0:
        not_axis = np.array([axis[1], -axis[0], 0])
    else:
        not_axis = np.array([0, axis[2], -axis[1]])
    
    # Orthonormal basis vectors perpendicular to axis
    v = np.cross(axis, not_axis)
    u = np.cross(v, axis)
    u = u / np.linalg.norm(u) * r1
    v = v / np.linalg.norm(v) * r1
    
    # Points on the first end cap
    points = []
    for i in range(num_segments):
        angle = 2 * np.pi * i / num_segments
        point = p1 + np.cos(angle) * u + np.sin(angle) * v
        points.append(point)
    
    # Points on the second end cap
    u = u / r1 * r2
    v = v / r1 * r2
    for i in range(num_segments):
        angle = 2 * np.pi * i / num_segments
        point = p2 + np.cos(angle) * u + np.sin(angle) * v
        points.append(point)
    
    # Indices for the side faces using quadrilaterals
    indices = []
    for i in range(num_segments):
        next_i = (i + 1) % num_segments
        indices.extend([4, i, next_i, next_i + num_segments, i + num_segments])
    
    # # Indices for the end caps (triangles)
    # center1 = len(points)
    # center2 = center1 + 1
    # points.append(p1)
    # points.append(p2)
    # for i in range(num_segments):
    #     next_i = (i + 1) % num_segments
    #     indices.extend([3, i, next_i, center1])
    #     indices.extend([3, i + num_segments, next_i + num_segments, center2])
    
    return points, indices