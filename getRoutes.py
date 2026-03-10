import requests
import json
import distance
import copy
import time
import config
from collections import defaultdict

# Functions for fetching and processing routes from the API


def _isEulerianDirected(route):
    # Returns True if the route is a valid Eulerian cycle (i.e. does not use an arc more than once)
    arcSet = set()
    for i in range(len(route)-1):
        u = route[i]
        v = route[i+1]
        if (u, v) in arcSet:
            return False
        else:
            arcSet.add((u, v))
    return True


def removeSelfLoops(oldRoute):
    L = [oldRoute[0]]
    for i in range(1, len(oldRoute)):
        if oldRoute[i] != L[-1]:
            L.append(oldRoute[i])
    return L


def _removeBackAndForths(oldRoute, oldWPs):
    # Deletes all out-and-backs from a route. First, fForm a simple graph representation
    # of the routes. This should be stored as an adjacency list. The name of each node is a (lon, lat) tuple
    A = defaultdict(set)
    for i in range(len(oldRoute)-1):
        A[oldRoute[i]].add(oldRoute[i+1])
        A[oldRoute[i+1]].add(oldRoute[i])
    # Remove all degree-one vertices (not including s). S holds the set of currently degree-one
    # vertices, D keeps a record of all the vertices that are to be deleted from route
    s = oldRoute[0]
    S = set()
    D = set()
    for u in A:
        if len(A[u]) == 1:
            S.add(u)
    S.discard(s)
    while len(S) > 0:
        u = S.pop()
        D.add(u)
        v = next(iter(A[u]))
        A[u].remove(v)
        A[v].remove(u)
        if len(A[v]) == 1 and v != s:
            S.add(v)
    # Now construct the new route. This is a copy of the original route, except that vertices
    # in the set D are left out. Also, the new "actual" waypoints are adjusted to the base of any tree
    newRoute = [s]
    newWPs = [s]
    oldWPSet = set(oldWPs)
    for i in range(1, len(oldRoute)):
        v = oldRoute[i]
        if v not in D:
            if v != newRoute[-1]:
                newRoute.append(v)
                if v in oldWPSet:
                    newWPs.append(v)
            else:
                newWPs.append(v)
    newWPs.pop()
    # If newRoute has just one vertex then the original route was a tree, so we return the original route and waypoints
    if len(newRoute) <= 1:
        return oldRoute, oldWPs
    else:
        return newRoute, newWPs


def _getRequest(travelMode):
    # Form the request string based on the given transport mode
    if travelMode == 1:
        s = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
    elif travelMode == 2:
        s = "https://api.openrouteservice.org/v2/directions/cycling-regular/geojson"
    else:
        s = "https://api.openrouteservice.org/v2/directions/foot-walking/geojson"
    return s


def _getBody(coords):
    # Form the request body based on the given waypoints
    body = {"coordinates": coords,
         "continue_straight": "false",
         "elevation": "true",
         "preference": "recommended",
         "radiuses": -1,
         "geometry": "true",
         "extra_info": ["surface", "green"]}
    return body


def _getHeaders():
    # Form the request header based on the specified key
    headers = {
        'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
        'Authorization': config.ORSKEY,
        'Content-Type': 'application/json; charset=utf-8'
    }
    return headers


def _getMultipleRoutes(coords, n, removeBackAndForths, weight, surface, green, height, travelMode):
    # Get several routes by making a single request with many waypoints, and then breaking them up
    s = _getRequest(travelMode)
    body = _getBody(coords)
    headers = _getHeaders()
    start = time.time()
    call = requests.post(s, json=body, headers=headers)
    end = time.time()
    config.totalNumCalls += 1
    config.totalCallTime += end-start
    if int(call.status_code) != 200 and int(call.status_code) != 201:
        config.myQuit("Directions request failed. Code =" +
                      str(call.status_code) + ":" + str(call.reason))
    # If we are here, the request was successful so we can continue
    X = json.loads(call.text)
    L = X["features"][0]["geometry"]["coordinates"]
    # L holds a list of 3-tuples defining each long/lat/height along the a route. Put this into the correct data structures
    fullroute = []
    for el in L:
        fullroute.append((el[0], el[1]))
        height[(el[0], el[1])] = el[2]
    for i in range(len(fullroute)-1):
        weight[(fullroute[i], fullroute[i+1])] = distance.GPSCrowDist(fullroute[i], fullroute[i+1], height[fullroute[i]], height[fullroute[i+1]])
    # Get all of the actual waypoints used in this route (these may well be different to the original polygon coordinates)
    L = X["features"][0]["properties"]["way_points"]
    allWPs = []
    for i in range(len(L)-1):
        allWPs.append(fullroute[L[i]])
    # Also store the details of each edge's surface
    L = X["features"][0]["properties"]["extras"]["surface"]["values"]
    for el in L:
        for i in range(el[0], el[1]):
            surface[(fullroute[i], fullroute[i+1])] = el[2]
    # And the green values (if using foot-walking)
    if travelMode == 3:
        L = X["features"][0]["properties"]["extras"]["green"]["values"]
        for el in L:
            for i in range(el[0], el[1]):
                green[(fullroute[i], fullroute[i+1])] = el[2]
    # Now break the full route up into its constituent sub-routes
    L = X["features"][0]["properties"]["way_points"]
    splitPoints = []
    for i in range(0, len(L), n):
        splitPoints.append(L[i])
    WPs = []
    cnt = 0
    for i in range(len(splitPoints)-1):
        wp = []
        for j in range(n):
            wp.append(allWPs[cnt])
            cnt += 1
        WPs.append(wp)
    subRoutes = []
    for i in range(len(splitPoints)-1):
        route = fullroute[splitPoints[i]:splitPoints[i+1]]
        route.append(route[0])
        # Remove any self loops (edges of the form (u,u)). Also, if requested, remove the back-and-forths from the routes
        route = removeSelfLoops(route)
        if removeBackAndForths == True:
            route, WPs[i] = _removeBackAndForths(route, WPs[i])
        subRoutes.append(route)
    return subRoutes, WPs


def _getSingleRoute(coords, removeBackAndForths, weight, surface, green, height, travelMode):
    # Get a single route by specifying several waypoints
    s = _getRequest(travelMode)
    body = _getBody(coords)
    headers = _getHeaders()
    start = time.time()
    call = requests.post(s, json=body, headers=headers)
    end = time.time()
    config.totalNumCalls += 1
    config.totalCallTime += end-start
    if int(call.status_code) != 200 and int(call.status_code) != 201:
        config.myQuit("Directions request failed. Code =" +
                      str(call.status_code) + ":" + str(call.reason))
    # If we are here, the request was successful so we can continue
    X = json.loads(call.text)
    L = X["features"][0]["geometry"]["coordinates"]
    # L holds a list of 3-tuples defining each long/lat/height along the a route. Put this into the correct data structures
    route = []
    for el in L:
        route.append((el[0], el[1]))
        height[(el[0], el[1])] = el[2]
    for i in range(len(route)-1):
        weight[(route[i], route[i+1])] = distance.GPSCrowDist(route[i], route[i+1], height[route[i]], height[route[i]])
    # Get all of the actual waypoints used in this route (these may well be different to the original polygon coordinates)
    L = X["features"][0]["properties"]["way_points"]
    WPs = []
    for i in range(len(L)-1):
        WPs.append(route[L[i]])
    # Also store the details of each edge's weight (length) and surface
    L = X["features"][0]["properties"]["extras"]["surface"]["values"]
    for el in L:
        for i in range(el[0], el[1]):
            surface[(route[i], route[i+1])] = el[2]
    # And the green values (if using foot-walking)
    if travelMode == 3:
        L = X["features"][0]["properties"]["extras"]["green"]["values"]
        for el in L:
            for i in range(el[0], el[1]):
                green[(route[i], route[i+1])] = el[2]
    # Remove any self loops (edges of the form (u,u)). Also, if requested, remove the out-and-backs from the routes
    route = removeSelfLoops(route)
    if removeBackAndForths == True:
        route, WPs = _removeBackAndForths(route, WPs)
    return route, WPs


def round_trip(s: int, k: int, n: int, travelMode: int, removeBackAndForths: bool, numSols: int, weight: dict, surface: dict, green: dict, height: dict):
    # Use the round_trip function in openrouteservice to produce numSols routes of length k
    try:
        solutions = []
        for seed in range(1, numSols+1):
            body = {
                "coordinates": [s],
                "continue_straight": "false",
                "elevation": "true",
                "extra_info": ["surface", "green"],
                "options": {"round_trip": {"length": k, "points": n, "seed": seed}},
                "preference": "recommended",
                "radiuses": -1,
                "geometry": "true"}
            headers = {
                'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
                'Authorization': config.ORSKEY,
                'Content-Type': 'application/json; charset=utf-8'
            }
            start = time.time()
            if travelMode == 1:
                call = requests.post(
                    'https://api.openrouteservice.org/v2/directions/driving-car/geojson', json=body, headers=headers)
            elif travelMode == 2:
                call = requests.post(
                    'https://api.openrouteservice.org/v2/directions/cycling-regular/geojson', json=body, headers=headers)
            else:
                call = requests.post(
                    'https://api.openrouteservice.org/v2/directions/foot-walking/geojson', json=body, headers=headers)
            end = time.time()
            config.totalNumCalls += 1
            config.totalCallTime += end-start
            if int(call.status_code) != 200 and int(call.status_code) != 201:
                print("Warning: openrouteservice round_trip feature failed with seed =", seed)
                continue
            else:
                print("Openrouteservice round_trip succeeded with seed =", seed)
            # If we are here, the request was successful so we can continue
            X = json.loads(call.text)
            L = X["features"][0]["geometry"]["coordinates"]
            # L holds a list of 3-tuples defining each long/lat/height along the a route. Put this into the correct data structures
            route = []
            for el in L:
                route.append((el[0], el[1]))
                height[(el[0], el[1])] = el[2]
            for i in range(len(route)-1):
                weight[(route[i], route[i+1])] = distance.GPSCrowDist(route[i], route[i+1], height[route[i]], height[route[i]])
            L = X["features"][0]["properties"]["extras"]["surface"]["values"]
            for el in L:
                for i in range(el[0], el[1]):
                    surface[(route[i], route[i+1])] = el[2]
            # And the green values (if using foot-walking)
            if travelMode == 3:
                L = X["features"][0]["properties"]["extras"]["green"]["values"]
                for el in L:
                    for i in range(el[0], el[1]):
                        green[(route[i], route[i+1])] = el[2]
            # Remove any self loops (edges of the form (u,u)). Also, if requested, remove the back-and-forths from the routes
            route = removeSelfLoops(route)
            solutions.append(dict())
            solutions[-1]["routeVertices"] = copy.deepcopy(route)
            solutions[-1]["routeLength"] = distance.GPSCrowPathDist(route, weight)
            solutions[-1]["seedUsed"] = seed
            if solutions[-1]["routeLength"] == 0:
                solutions[-1]["overlapPercent"] = 0
            else:
                solutions[-1]["overlapPercent"] = round((distance.getOverlapDistOrigGraph(
                    solutions[-1]["routeVertices"], weight) / solutions[-1]["routeLength"]) * 100)
            solutions[-1]["isEulerian"] = _isEulerianDirected(
                solutions[-1]["routeVertices"])
        return solutions
    except:
        config.myQuit(
            "Error occurred in getRoutes function. Likely a temporary server-side issue. Ending.")


def getRoutes(polygon: list, removeBackAndForths: bool, weight: dict, surface: dict, green: dict, height: dict, separateCalls: bool, travelMode: int):
    # Produce a list of candidate routes using the polygons listed in P. Vertices in routes are defined/named by their
    # xy gps coordinates. The heights of each vertex, and surface type of each edge are also stored
    solutions = []
    try:
        if separateCalls == True:
            # Get a route for each polygon using a separate call for each one
            solutions.append(dict())
            solutions[-1]["estimatedWPs"] = polygon[0]["estimatedWPs"]
            solutions[-1]["estimatedWPsPerimeter"] = polygon[0]["estimatedWPsPerimeter"]
            solutions[-1]["degreeBearing"] = polygon[0]["degreeBearing"]
            coords = copy.deepcopy(solutions[-1]["estimatedWPs"])
            coords.append(coords[0])
            route, WPs = _getSingleRoute(
                coords, removeBackAndForths, weight, surface, green, height, travelMode)
            solutions[-1]["routeVertices"] = route
            solutions[-1]["isEulerian"] = _isEulerianDirected(
                solutions[-1]["routeVertices"])
            solutions[-1]["routeLength"] = distance.GPSCrowPathDist(
                solutions[-1]["routeVertices"], weight)
            if solutions[-1]["routeLength"] == 0:
                solutions[-1]["overlapPercent"] = 0
            else:
                solutions[-1]["overlapPercent"] = round((distance.getOverlapDistOrigGraph(
                    solutions[-1]["routeVertices"], weight) / solutions[-1]["routeLength"]) * 100)
            solutions[-1]["actualWPs"] = WPs
            solutions[-1]["actualWPsPerimeter"] = distance.getWaypointsPolygonPerimeter(
                WPs)
            return solutions
        else:
            for i in range(len(polygon)-1):
                assert len(polygon[i]["estimatedWPs"]) == len(polygon[i+1]["estimatedWPs"]), "Error: All polygons here should have the same number of waypoints"
            n = len(polygon[0]["estimatedWPs"])
            # Get multiple routes in a single call. First create a sequence of all the polygon coordinates
            coords = []
            for i in range(len(polygon)):
                coords += copy.deepcopy(polygon[i]["estimatedWPs"])
            coords.append(polygon[0]["estimatedWPs"][0])
            routes, WPs = _getMultipleRoutes(
                coords, n, removeBackAndForths, weight, surface, green, height, travelMode)
            for i in range(len(routes)):
                solutions.append(dict())
                solutions[-1]["estimatedWPs"] = polygon[i]["estimatedWPs"]
                solutions[-1]["estimatedWPsPerimeter"] = polygon[i]["estimatedWPsPerimeter"]
                solutions[-1]["degreeBearing"] = polygon[i]["degreeBearing"]
                solutions[-1]["routeVertices"] = routes[i]
                solutions[-1]["isEulerian"] = _isEulerianDirected(
                    solutions[-1]["routeVertices"])
                solutions[-1]["routeLength"] = distance.GPSCrowPathDist(
                    solutions[-1]["routeVertices"], weight)
                if solutions[-1]["routeLength"] == 0:
                    solutions[-1]["overlapPercent"] = 0
                else:
                    solutions[-1]["overlapPercent"] = round((distance.getOverlapDistOrigGraph(
                        solutions[-1]["routeVertices"], weight) / solutions[-1]["routeLength"]) * 100)
                solutions[-1]["actualWPs"] = WPs[i]
                solutions[-1]["actualWPsPerimeter"] = distance.getWaypointsPolygonPerimeter(
                    WPs[i])
            return solutions
    except:
        config.myQuit(
            "Error occurred in getRoutes function. Likely a temporary server-side issue. Ending.")
