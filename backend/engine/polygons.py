"""Ellipse/polygon generation for route waypoints.

Adapted from polygons.py by R. Lewis and P. Corcoran, Cardiff University.

Original publication:
  Lewis, R. and P. Corcoran (2024) "Fast Algorithms for Computing Fixed-Length
  Round Trips in Real-World Street Networks". Springer Nature Computer Science,
  vol. 5, 868. https://link.springer.com/article/10.1007/s42979-024-03223-3

Original source: https://zenodo.org/doi/10.5281/zenodo.8154412
"""

import numpy as np
import scipy as sp
import math
import scipy.optimize
from . import distance

BIG_VAL = 40075000  # circumference of the earth


def _on_segment(p, q, r):
    if (
        (q[0] <= max(p[0], r[0]))
        & (q[0] >= min(p[0], r[0]))
        & (q[1] <= max(p[1], r[1]))
        & (q[1] >= min(p[1], r[1]))
    ):
        return True
    return False


def _orientation(p, q, r):
    val = ((q[1] - p[1]) * (r[0] - q[0])) - ((q[0] - p[0]) * (r[1] - q[1]))
    if val == 0:
        return 0
    return 1 if val > 0 else 2


def _do_intersect(p1, q1, p2, q2):
    o1 = _orientation(p1, q1, p2)
    o2 = _orientation(p1, q1, q2)
    o3 = _orientation(p2, q2, p1)
    o4 = _orientation(p2, q2, q1)
    if (o1 != o2) and (o3 != o4):
        return True
    if (o1 == 0) and (_on_segment(p1, p2, q1)):
        return True
    if (o2 == 0) and (_on_segment(p1, q2, q1)):
        return True
    if (o3 == 0) and (_on_segment(p2, p1, q2)):
        return True
    if (o4 == 0) and (_on_segment(p2, q1, q2)):
        return True
    return False


def _is_inside_polygon(points, p):
    if len(points) < 3:
        return False
    extreme = (BIG_VAL, p[1])
    count = i = 0
    while True:
        next_i = (i + 1) % len(points)
        if _do_intersect(points[i], points[next_i], p, extreme):
            if _orientation(points[i], p, points[next_i]) == 0:
                return _on_segment(points[i], p, points[next_i])
            count += 1
        i = next_i
        if i == 0:
            break
    return count % 2 == 1


def all_coords_inside_isochrone(coords, isochrone):
    for i in range(1, len(coords)):
        if not _is_inside_polygon(isochrone, coords[i]):
            return False
    return True


def _rotate_2d(coord, radians):
    x, y = coord
    newx = x * math.cos(radians) + y * math.sin(radians)
    newy = -x * math.sin(radians) + y * math.cos(radians)
    return [newx, newy]


def _go_north(lat, x):
    return lat + x * 0.00899280


def _get_north_dist(lat1, lat2):
    return (lat2 - lat1) / 0.00899280


def _go_east(lon, lat, x):
    deg_per_km = abs(1.0 / (111.2 * math.cos((math.pi / 180.0) * lat)))
    return lon + x * deg_per_km


def _get_east_dist(lon1, lon2, lat):
    deg_per_km = abs(1.0 / (111.2 * math.cos((math.pi / 180.0) * lat)))
    return (lon2 - lon1) / deg_per_km


def _get_coords_in_ellipse(n, a, b):
    assert n > 0
    angles = 2 * math.pi * np.arange(n) / n
    if a != b:
        e2 = 1.0 - a**2.0 / b**2.0
        tot_size = sp.special.ellipeinc(2.0 * math.pi, e2)
        arc_size = tot_size / n
        arcs = np.arange(n) * arc_size
        res = sp.optimize.root(lambda x: (sp.special.ellipeinc(x, e2) - arcs), angles)
        angles = res.x
    coords = [[b * math.sin(x), a * math.cos(x)] for x in angles]
    for i in range(1, len(coords)):
        coords[i][0] -= coords[0][0]
        coords[i][1] -= coords[0][1]
    coords[0][0] = 0
    coords[0][1] = 0
    for i in range(len(coords)):
        coords[i] = _rotate_2d(coords[i], math.radians(180))
    return coords


def get_ellipse_gps_coords(source_gps, k, bearing, aspect_ratio, n):
    coords = _get_coords_in_ellipse(n, aspect_ratio, 1)
    rotation_value = math.radians(bearing)
    for i in range(len(coords)):
        coords[i] = _rotate_2d(coords[i], rotation_value)
    p = distance.get_euclidean_perimeter(coords)
    for i in range(len(coords)):
        coords[i][0] *= k / p
        coords[i][1] *= k / p
    coords[0] = source_gps
    for i in range(1, len(coords)):
        newy = _go_north(coords[0][1], coords[i][1] / 1000)
        newx = _go_east(coords[0][0], newy, coords[i][0] / 1000)
        coords[i] = [newx, newy]
    return coords


def get_rescaled_polygon(old_coords, desired_perimeter, desired_num_points):
    old_dist = distance.get_waypoints_polygon_perimeter(old_coords)
    scale_factor = desired_perimeter / old_dist
    new_coords = [[0, 0]]
    for i in range(1, len(old_coords)):
        x = _get_east_dist(old_coords[0][0], old_coords[i][0], old_coords[i][1])
        y = _get_north_dist(old_coords[0][1], old_coords[i][1])
        new_coords.append([x, y])
    for i in range(len(new_coords)):
        new_coords[i][0] *= scale_factor * 1000
        new_coords[i][1] *= scale_factor * 1000
    new_coords[0] = old_coords[0]
    for i in range(1, len(new_coords)):
        newy = _go_north(new_coords[0][1], new_coords[i][1] / 1000)
        newx = _go_east(new_coords[0][0], newy, new_coords[i][0] / 1000)
        new_coords[i] = [newx, newy]
    for i in range(len(new_coords), desired_num_points):
        new_coords.append(new_coords[-1])
    return new_coords
