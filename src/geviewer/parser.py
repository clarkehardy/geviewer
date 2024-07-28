import numpy as np
import pyvista as pv
from tqdm import tqdm
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from matplotlib.colors import LinearSegmentedColormap


def create_meshes(polyline_blocks, marker_blocks, solid_blocks):
    """Creates meshes from the polyline, marker, and solid blocks.

    :param polyline_blocks: The polyline blocks to create meshes from.
    :type polyline_blocks: list
    :param marker_blocks: The marker blocks to create meshes from.
    :type marker_blocks: list
    :param solid_blocks: The solid blocks to create meshes from.
    :type solid_blocks: list
    :return: A tuple containing three elements:
        - A list of meshes created from the blocks.
        - An array of scalar values used for coloring the meshes.
        - A list of color maps corresponding to each type of mesh.
    :rtype: tuple
    """
    counts = [len(polyline_blocks), len(marker_blocks), len(solid_blocks)]
    start_inds = np.cumsum([0] + counts)
    total_blocks = start_inds[-1]
    meshes = [None] * total_blocks
    colors = [None] * total_blocks
    
    def process_block(block, index, func):
        meshes[index], colors[index] = func(block)
    
    with ThreadPoolExecutor() as executor:
        futures = []
        
        for i, block in enumerate(polyline_blocks):
            futures.append(executor.submit(process_block, block, i, process_polyline_block))
        
        for i, block in enumerate(marker_blocks):
            futures.append(executor.submit(process_block, block, start_inds[1] + i, process_marker_block))
        
        for i, block in enumerate(solid_blocks):
            futures.append(executor.submit(process_block, block, start_inds[2] + i, process_solid_block))
        
        for future in tqdm(as_completed(futures), desc='Building meshes', total=total_blocks):
            future.result()

    colors = np.array(colors)
    cmaps = []
    scalars = np.array([])
    titles = ['trajectories', 'markers', 'solids']
    for i in range(3):
        if start_inds[i+1] - start_inds[i] == 0:
            cmaps.append(None)
            continue
        # construct a color map for each type of mesh to be plotted
        unique_colors,inverse_indices = np.unique(colors[start_inds[i]:start_inds[i+1]], axis=0, return_inverse=True)
        if unique_colors.shape[0] == 1:
            unique_colors = np.concatenate((unique_colors, unique_colors))
        cmaps.append(LinearSegmentedColormap.from_list(titles[i], unique_colors, N=len(unique_colors)))
        # take the color index for each mesh to be the scalar determining its color
        scalars = np.concatenate((scalars, inverse_indices.flatten()))
        
    return meshes, scalars, cmaps


def extract_blocks(file_content):
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

    for line in tqdm(lines, desc='Parsing data...'):
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


def process_polyline_block(block):
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
    points, indices, color = parse_polyline_block(block)
    lines = []
    for i in range(len(indices) - 1):
        if indices[i] != -1 and indices[i + 1] != -1:
            lines.extend([2, indices[i], indices[i + 1]])
    line_mesh = pv.PolyData(points)
    if len(lines) > 0:
        line_mesh.lines = lines
    return line_mesh, color


def process_marker_block(block):
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
    center, radius, color = parse_marker_block(block)
    sphere = pv.Sphere(radius=radius, center=center)
    return sphere, color


def process_solid_block(block):
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
    points, indices, color = parse_solid_block(block)
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
    return solid_mesh, color


def parse_viewpoint_block(block):
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
        - The orientation as a list of four floats [x, y, z, angle] in degrees
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
                           float(orientation_match.group(3)), float(orientation_match.group(4))*180/np.pi]
    
    return fov, position, orientation


def parse_polyline_block(block):
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

    color.append(1)

    return np.array(coords), np.array(coord_inds), np.array(color)


def parse_marker_block(block):
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

    color.append(1 - transparency)

    return np.array(coords), radius, np.array(color)


def parse_solid_block(block):
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
    color = [1, 1, 1, 0]
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

    color.append(1 - transparency)

    return np.array(coords), np.array(coord_inds), np.array(color)