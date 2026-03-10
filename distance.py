import math

# Functions for calculating straight-line and geographic distances, etc.


def EuclideanDist(x1, y1, x2, y2):
    # Gets the Euclidean distance between two 2D points
    a = x1 - x2
    b = y1 - y2
    return math.sqrt(a**2 + b**2)


def getEuclideanPerimeter(coords):
    # Gets the Euclidean perimeter of a polygon defined by a series of coordinates (assumes that the first and last point join to complete the polygon)
    length = 0
    for i in range(len(coords) - 1):
        length += EuclideanDist(coords[i][0], coords[i]
                                [1], coords[i + 1][0], coords[i + 1][1])
    length += EuclideanDist(coords[-1][0], coords[-1]
                            [1], coords[0][0], coords[0][1])
    return length


def GPSCrowDist(u, v, heightu, heightv):
    # Given two vertices, (each defined by a (lon,lat) tuple) return the straight-line distance in m (6378137 is the equatorial radius of the earth in m)
    # First convert the coordinates to radians
    x1 = math.radians(u[0])
    y1 = math.radians(u[1])
    x2 = math.radians(v[0])
    y2 = math.radians(v[1])
    # Then use the haversine formula to get the straight line distance on the globe (an alternative here is to use Vincenty's formula,
    # which is slightly more accurate, but also more expensive)
    dist = 2 * math.asin(math.sqrt(math.sin((x2-x1)/2) ** 2 + math.cos(x1)
                         * math.cos(x2) * math.sin((y2-y1)/2) ** 2)) * 6378137.000
    # Finally, use the difference in heights with Pythagoras' theorem to get the final distance
    return math.sqrt(dist**2 + abs(heightu-heightv)**2)


def getWaypointsPolygonPerimeter(WPs):
    # Given a sequence of GPS coordinates, calculate the perimeter of the polygon that it defines
    total = 0
    for i in range(len(WPs)-1):
        total += GPSCrowDist(WPs[i], WPs[i+1], 0, 0)
    total += GPSCrowDist(WPs[-1], WPs[0], 0, 0)
    return total


def GPSCrowPathDist(P, weight):
    # Take a path defined by a sequence of GPS coordinates and return its total length in m
    total = 0
    for i in range(len(P)-1):
        total += weight[(P[i], P[i+1])]
    return total


def climbedInPath(P, height):
    # Take a path defined by a sequence of GPS coordinates and return the amount climbed along it
    total = 0
    for i in range(len(P)-1):
        if height[P[i]] < height[P[i+1]]:
            total += height[P[i+1]] - height[P[i]]
    return total


def getBearing(x1, y1, x2, y2):
    # Returns the bearing from point (x1,y1) to point (x2,y2). The answer is between 0 degrees (north) and 360 degrees
    diffLon = x2 - x1
    x = math.cos(math.radians(y2)) * math.sin(math.radians(diffLon))
    y = math.cos(math.radians(y1)) * math.sin(math.radians(y2)) - math.sin(
        math.radians(y1)) * math.cos(math.radians(y2)) * math.cos(math.radians(diffLon))
    bearing = math.degrees(math.atan2(x, y))
    if bearing < 0:
        bearing += 360
    return bearing


def getOverlapDistSmoothed(C, W, doubleArcSet):
    total = 0
    E = set()
    for i in range(len(C)-1):
        e = frozenset([C[i], C[i+1]])
        if e not in doubleArcSet:
            e = (C[i], C[i+1])
        if e in E:
            total += W[(C[i], C[i+1])]
        else:
            E.add(e)
    return total


def getOverlapDistOrigGraph(route, weight):
    total = 0
    E = set()
    for i in range(len(route)-1):
        e = frozenset([route[i], route[i+1]])
        if e in E:
            total += weight[(route[i], route[i+1])]
        else:
            E.add(e)
    return total
