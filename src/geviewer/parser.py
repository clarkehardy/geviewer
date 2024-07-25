import numpy as np
import pyvista as pv
import re


def extract_blocks(file_content):
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


def create_meshes(polyline_blocks, marker_blocks, solid_blocks):
    '''
    Create meshes from the polyline, marker, and solid blocks.
    '''
    print('Creating meshes...')
    meshes = []

    # tracks are saved as polyline blocks
    for block in polyline_blocks:
        points, indices, color = parse_polyline_block(block)
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
        center, radius, color = parse_marker_block(block)
        sphere = pv.Sphere(radius=radius, center=center)
        meshes.append((sphere, color, None))

    # geometry is saved as solid blocks
    for block in solid_blocks:
        points, indices, color, transparency = parse_solid_block(block)
        
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


def parse_marker_block(block):
    '''
    Parse a marker block to get step information.
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


def parse_solid_block(block):
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