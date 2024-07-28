import numpy as np
import pyvista as pv
from tqdm import tqdm
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from matplotlib.colors import LinearSegmentedColormap


def create_meshes(polyline_blocks, marker_blocks, solid_blocks):
    '''
    Create meshes from the polyline, marker, and solid blocks.
    '''
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
    '''
    Extract polyline, marker, and solid blocks from the file content.
    '''
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
    '''
    Process a polyline block to create a polyline mesh.
    '''
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
    '''
    Process a marker block to create a marker mesh.
    '''
    center, radius, color = parse_marker_block(block)
    sphere = pv.Sphere(radius=radius, center=center)
    return sphere, color


def process_solid_block(block):
    '''
    Process a solid block to create a solid mesh.
    '''
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


def parse_polyline_block(block):
    '''
    Parse a polyline block to get particle track information.
    '''
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
    '''
    Parse a marker block to get step information.
    '''
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
    '''
    Parse a solid block to get geometry information.
    '''
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