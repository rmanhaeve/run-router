import numpy as np
import scipy as sp
import math
import scipy.optimize
import distance

# The following are functions for detecting if a 2D coordinate is within a polygon

BIG_VAL = 40075000  # circumference of the earth


def _onSegment(p: tuple, q: tuple, r: tuple) -> bool:
    # Returns true if the collinear points p, q, r, lies on line segment 'pr'
    if ((q[0] <= max(p[0], r[0])) & (q[0] >= min(p[0], r[0])) & (q[1] <= max(p[1], r[1])) & (q[1] >= min(p[1], r[1]))):
        return True
    return False


def _orientation(p: tuple, q: tuple, r: tuple) -> int:
    # Finds the orientation of ordered triplet (p, q, r). 0 --> p, q and r are collinear;
    # 1 --> Clockwise; 2 --> Anticlockwise
    val = ((q[1] - p[1]) * (r[0] - q[0])) - ((q[0] - p[0]) * (r[1] - q[1]))
    if val == 0:
        return 0
    if val > 0:
        return 1
    else:
        return 2


def _doIntersect(p1, q1, p2, q2):
    # Find the four orientations needed for general and special cases
    o1 = _orientation(p1, q1, p2)
    o2 = _orientation(p1, q1, q2)
    o3 = _orientation(p2, q2, p1)
    o4 = _orientation(p2, q2, q1)
    if (o1 != o2) and (o3 != o4):
        return True
    if (o1 == 0) and (_onSegment(p1, p2, q1)):
        return True
    if (o2 == 0) and (_onSegment(p1, q2, q1)):
        return True
    if (o3 == 0) and (_onSegment(p2, p1, q2)):
        return True
    if (o4 == 0) and (_onSegment(p2, q1, q2)):
        return True
    return False


def _isInsidePolygon(points: list, p: tuple) -> bool:
    # Returns true if the point p lies inside the polygon defined by the list of points
    if len(points) < 3:
        # There must be at least 3 vertices in polygon
        return False
    # Create a point for line segment from p to infinite
    extreme = (BIG_VAL, p[1])
    count = i = 0
    while True:
        next = (i + 1) % len(points)
        if (_doIntersect(points[i], points[next], p, extreme)):
            if _orientation(points[i], p, points[next]) == 0:
                return _onSegment(points[i], p, points[next])
            count += 1
        i = next
        if (i == 0):
            break
    # Return true if count is odd, false otherwise
    return (count % 2 == 1)


def allCoordsInsideIsochrone(coords, I):
    # Returns true iff all the 2D points in the coords list are within the polygon defined by I
    # This allows for the source to be outside of the isochrone
    for i in range(1, len(coords)):
        if not _isInsidePolygon(I, coords[i]):
            return False
    # if we are here then all points are within I
    return True

# The following are functions for generating fixed-perimeter, n-vertex ellipses on the Earth's surface from a given starting coordinate at a given bearing


def _Rotate2D(coord, radians):
    # Rotate a coordinate (about the source (0,0)) by the specified number of radians
    x, y = coord
    newx = x * math.cos(radians) + y * math.sin(radians)
    newy = -x * math.sin(radians) + y * math.cos(radians)
    return ([newx, newy])


def _goNorth(lat, x):
    # Returns the latitude if we travel x km north from lat
    return lat + x * 0.00899280


def _getNorthDist(lat1, lat2):
    # Returns the distance in km between two latitudes, moving north
    return (lat2 - lat1) / 0.00899280


def _goEast(lon, lat, x):
    # Returns the longitude if we travel x km east of lon at latitude lat
    degPerKm = abs(1.0 / (111.2 * math.cos((math.pi / 180.0) * lat)))
    return lon + x * degPerKm


def _getEastDist(lon1, lon2, lat):
    # Returns the distance in km between to longitudes (at latitude lat), moving east
    degPerKm = abs(1.0 / (111.2 * math.cos((math.pi / 180.0) * lat)))
    return (lon2 - lon1) / degPerKm


def _getCoordsInEllipse(n, a, b):
    assert (n > 0)
    # Produces an n-point ellipse according to a major axis a, and minor axis b. The result is a set of n points in
    # 2D Euclidean space. The first of these coordinates occurs at (0 0), and the ellipse "points" upwards
    angles = 2 * math.pi * np.arange(n) / n
    if a != b:
        e2 = (1.0 - a ** 2.0 / b ** 2.0)
        tot_size = sp.special.ellipeinc(2.0 * math.pi, e2)
        arc_size = tot_size / n
        arcs = np.arange(n) * arc_size
        res = sp.optimize.root(lambda x: (
            sp.special.ellipeinc(x, e2) - arcs), angles)
        angles = res.x
    # We now have a list of n angles. Use these to generate the n coordinates
    coords = [[b * math.sin(x), a * math.cos(x)] for x in angles]
    # We now update these coordinates so that the first point appears at the origin
    for i in range(1, len(coords)):
        coords[i][0] -= coords[0][0]
        coords[i][1] -= coords[0][1]
    coords[0][0] = 0
    coords[0][1] = 0
    # Finally, rotate the ellipse so that it "points upwards" (north)
    for i in range(len(coords)):
        coords[i] = _Rotate2D(coords[i], math.radians(180))
    return coords


def getEllipseGPSCoords(sourceGPS: list, k: float, bearing: float, aspectRatio: float, n: int):
    # Get the GPS coordinates of an n-point ellipse with the required aspect ratio, bearing, and perimeter
    coords = _getCoordsInEllipse(n, aspectRatio, 1)
    # Rotate the ellipse to the required bearing
    rotationValue = math.radians(bearing)
    for i in range(len(coords)):
        coords[i] = _Rotate2D(coords[i], rotationValue)
    # Scale the ellipse so that it's perimeter is k
    p = distance.getEuclideanPerimeter(coords)
    for i in range(len(coords)):
        coords[i][0] *= k/p
        coords[i][1] *= k/p
    # Now convert the coordinates to the correct GPS coordinates
    coords[0] = sourceGPS
    for i in range(1, len(coords)):
        newy = _goNorth(coords[0][1], coords[i][1] / 1000)
        newx = _goEast(coords[0][0], newy, coords[i][0] / 1000)
        coords[i] = [newx, newy]
    return coords


def getRescaledPolygon(oldCoords: list, desiredPerimeter: float, desiredNumPoints: int):
    # Take a GPS polygon and resize it to the desired perimeter, keeping the source vertex (the first one) in the same place.
    # First, transform the GPS coordinates to Euclidean ones
    oldDist = distance.getWaypointsPolygonPerimeter(oldCoords)
    scaleFactor = desiredPerimeter / oldDist
    newCoords = [[0, 0]]
    for i in range(1, len(oldCoords)):
        x = _getEastDist(oldCoords[0][0], oldCoords[i][0], oldCoords[i][1])
        y = _getNorthDist(oldCoords[0][1], oldCoords[i][1])
        newCoords.append([x, y])
    # Now rescale these Euclidean coordinates
    for i in range(len(newCoords)):
        newCoords[i][0] *= scaleFactor * 1000
        newCoords[i][1] *= scaleFactor * 1000
    # and transform these new coordinates back to GPS coordinates
    newCoords[0] = oldCoords[0]
    for i in range(1, len(newCoords)):
        newy = _goNorth(newCoords[0][1], newCoords[i][1] / 1000)
        newx = _goEast(newCoords[0][0], newy, newCoords[i][0] / 1000)
        newCoords[i] = [newx, newy]
    # make sure that the polygon has the correct number of points (it's possible it may have too few due to -r option)
    for i in range(len(newCoords), desiredNumPoints):
        newCoords.append(newCoords[-1])
    return newCoords
