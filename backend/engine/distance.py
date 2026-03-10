"""Distance and geometry calculations.

Adapted from distance.py by R. Lewis and P. Corcoran, Cardiff University.

Original publication:
  Lewis, R. and P. Corcoran (2024) "Fast Algorithms for Computing Fixed-Length
  Round Trips in Real-World Street Networks". Springer Nature Computer Science,
  vol. 5, 868. https://link.springer.com/article/10.1007/s42979-024-03223-3

Original source: https://zenodo.org/doi/10.5281/zenodo.8154412
"""

import math


def euclidean_dist(x1, y1, x2, y2):
    a = x1 - x2
    b = y1 - y2
    return math.sqrt(a**2 + b**2)


def get_euclidean_perimeter(coords):
    length = 0
    for i in range(len(coords) - 1):
        length += euclidean_dist(
            coords[i][0], coords[i][1], coords[i + 1][0], coords[i + 1][1]
        )
    length += euclidean_dist(
        coords[-1][0], coords[-1][1], coords[0][0], coords[0][1]
    )
    return length


def gps_crow_dist(u, v, height_u=0, height_v=0):
    """Haversine distance between two (lon, lat) points, accounting for elevation."""
    x1 = math.radians(u[0])
    y1 = math.radians(u[1])
    x2 = math.radians(v[0])
    y2 = math.radians(v[1])
    dist = (
        2
        * math.asin(
            math.sqrt(
                math.sin((x2 - x1) / 2) ** 2
                + math.cos(x1) * math.cos(x2) * math.sin((y2 - y1) / 2) ** 2
            )
        )
        * 6378137.000
    )
    return math.sqrt(dist**2 + abs(height_u - height_v) ** 2)


def get_waypoints_polygon_perimeter(wps):
    total = 0
    for i in range(len(wps) - 1):
        total += gps_crow_dist(wps[i], wps[i + 1])
    total += gps_crow_dist(wps[-1], wps[0])
    return total


def gps_crow_path_dist(path, weight):
    total = 0
    for i in range(len(path) - 1):
        total += weight[(path[i], path[i + 1])]
    return total


def climbed_in_path(path, height):
    total = 0
    for i in range(len(path) - 1):
        if height[path[i]] < height[path[i + 1]]:
            total += height[path[i + 1]] - height[path[i]]
    return total


def get_bearing(x1, y1, x2, y2):
    diff_lon = x2 - x1
    x = math.cos(math.radians(y2)) * math.sin(math.radians(diff_lon))
    y = math.cos(math.radians(y1)) * math.sin(math.radians(y2)) - math.sin(
        math.radians(y1)
    ) * math.cos(math.radians(y2)) * math.cos(math.radians(diff_lon))
    bearing = math.degrees(math.atan2(x, y))
    if bearing < 0:
        bearing += 360
    return bearing


def get_overlap_dist_smoothed(C, W, double_arc_set):
    total = 0
    E = set()
    for i in range(len(C) - 1):
        e = frozenset([C[i], C[i + 1]])
        if e not in double_arc_set:
            e = (C[i], C[i + 1])
        if e in E:
            total += W[(C[i], C[i + 1])]
        else:
            E.add(e)
    return total


def get_overlap_dist_orig_graph(route, weight):
    total = 0
    E = set()
    for i in range(len(route) - 1):
        e = frozenset([route[i], route[i + 1]])
        if e in E:
            total += weight[(route[i], route[i + 1])]
        else:
            E.add(e)
    return total
