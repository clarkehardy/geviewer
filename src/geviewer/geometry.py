import numpy as np

def create_cylinder_mesh(p1, p2, r1, r2, num_segments=50):
    """Creates a mesh for a cylinder.

    :param p1: The first endpoint.
    :type p1: tuple
    :param p2: The second endpoint.
    :type p2: tuple
    :param r1: The radius at the first endpoint.
    :type r1: float
    :param r2: The radius at the second endpoint.
    :type r2: float
    :param num_segments: The number of segments to use.
    :type num_segments: int
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
    
    # Indices for the end caps (triangles)
    center1 = len(points)
    center2 = center1 + 1
    points.append(p1)
    points.append(p2)
    for i in range(num_segments):
        next_i = (i + 1) % num_segments
        indices.extend([3, i, next_i, center1])
        indices.extend([3, i + num_segments, next_i + num_segments, center2])
    
    return points, indices


def create_annular_cylinder_mesh(p1, p2, r1_outer, r2_outer, r1_inner, r2_inner, num_segments=50):
    """Creates a mesh for an annular cylinder.

    :param p1: The first endpoint.
    :type p1: tuple
    :param p2: The second endpoint.
    :type p2: tuple
    :param r1_outer: The outer radius at the first endpoint.
    :type r1_outer: float
    :param r2_outer: The outer radius at the second endpoint.
    :type r2_outer: float
    :param r1_inner: The inner radius at the first endpoint.
    :type r1_inner: float
    :param r2_inner: The inner radius at the second endpoint.
    :type r2_inner: float
    :param num_segments: The number of segments to use.
    :type num_segments: int
    """

    if r1_inner == 0 and r2_inner == 0:
        return create_cylinder_mesh(p1, p2, r1_outer, r2_outer, num_segments)

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

    def generate_circle_points(center, radius_u, radius_v, num_segments):
        """ Helper function to generate points on a circle. """
        circle_points = []
        for i in range(num_segments):
            angle = 2 * np.pi * i / num_segments
            point = center + np.cos(angle) * radius_u + np.sin(angle) * radius_v
            circle_points.append(point)
        return circle_points

    # Outer points on the first end cap
    u_outer = u / np.linalg.norm(u) * r1_outer
    v_outer = v / np.linalg.norm(v) * r1_outer
    outer_points_1 = generate_circle_points(p1, u_outer, v_outer, num_segments)

    # Outer points on the second end cap
    u_outer = u / np.linalg.norm(u) * r2_outer
    v_outer = v / np.linalg.norm(v) * r2_outer
    outer_points_2 = generate_circle_points(p2, u_outer, v_outer, num_segments)

    # Inner points on the first end cap
    u_inner = u / np.linalg.norm(u) * r1_inner
    v_inner = v / np.linalg.norm(v) * r1_inner
    inner_points_1 = generate_circle_points(p1, u_inner, v_inner, num_segments)

    # Inner points on the second end cap
    u_inner = u / np.linalg.norm(u) * r2_inner
    v_inner = v / np.linalg.norm(v) * r2_inner
    inner_points_2 = generate_circle_points(p2, u_inner, v_inner, num_segments)

    # Combine all points
    points = outer_points_1 + outer_points_2 + inner_points_1 + inner_points_2

    # Indices for the side faces using quadrilaterals
    indices = []
    for i in range(num_segments):
        next_i = (i + 1) % num_segments
        
        # Outer surface
        indices.extend([4, i, next_i, next_i + num_segments, i + num_segments])
        
        # Inner surface
        indices.extend([4, i + 2*num_segments, next_i + 2*num_segments, 
                        next_i + 3*num_segments, i + 3*num_segments])

    # Indices for the end caps (outer to inner ring, using triangles)
    for i in range(num_segments):
        next_i = (i + 1) % num_segments
        
        # First end cap
        indices.extend([4, i, i + 2*num_segments, next_i + 2*num_segments, next_i])
        
        # Second end cap
        indices.extend([4, i + num_segments, i + 3*num_segments, next_i + 3*num_segments, next_i + num_segments])

    return points, indices
