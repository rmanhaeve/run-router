"""OpenRouteService API client — async wrapper for directions, isochrones, and round trips.

Adapted from getRoutes.py and isochrone.py by R. Lewis and P. Corcoran, Cardiff University.

Original publication:
  Lewis, R. and P. Corcoran (2024) "Fast Algorithms for Computing Fixed-Length
  Round Trips in Real-World Street Networks". Springer Nature Computer Science,
  vol. 5, 868. https://link.springer.com/article/10.1007/s42979-024-03223-3

Original source: https://zenodo.org/doi/10.5281/zenodo.8154412
"""

import httpx
from collections import defaultdict
from . import distance
import copy
import logging

logger = logging.getLogger(__name__)

TRAVEL_MODES = {
    "cycle": "cycling-regular",
    "walk": "foot-walking",
}

ORS_BASE = "https://api.openrouteservice.org/v2"


class ORSClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.num_calls = 0

    def _headers(self):
        return {
            "Accept": "application/json, application/geo+json",
            "Authorization": self.api_key,
            "Content-Type": "application/json; charset=utf-8",
        }

    def _profile(self, mode: str) -> str:
        return TRAVEL_MODES.get(mode, "foot-walking")

    async def get_isochrone(self, source, dist_meters, mode="walk"):
        profile = self._profile(mode)
        url = f"{ORS_BASE}/isochrones/{profile}"
        body = {
            "locations": [source],
            "range": [dist_meters],
            "location_type": "start",
            "range_type": "distance",
            "smoothing": 1,
            "area_units": "m",
            "units": "m",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=body, headers=self._headers())
            self.num_calls += 1
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Isochrone request failed: {resp.status_code} {resp.reason_phrase}"
            )
        data = resp.json()
        isochrone = data["features"][0]["geometry"]["coordinates"][0]
        max_dist, bearing = self._get_max_dist(source, isochrone)
        shrink_factor = min(max_dist / dist_meters, 1.0) if dist_meters > 0 else 1.0
        return isochrone, shrink_factor, bearing

    def _get_max_dist(self, source, isochrone):
        max_dist = distance.gps_crow_dist(source, isochrone[0])
        furthest = isochrone[0]
        for pt in isochrone[1:]:
            d = distance.gps_crow_dist(source, pt)
            if d > max_dist:
                max_dist = d
                furthest = pt
        bearing = distance.get_bearing(source[0], source[1], furthest[0], furthest[1])
        return max_dist, bearing

    async def get_directions(self, coords, mode="walk"):
        """Get a route through waypoints. Returns raw ORS GeoJSON response."""
        profile = self._profile(mode)
        url = f"{ORS_BASE}/directions/{profile}/geojson"
        body = {
            "coordinates": coords,
            "continue_straight": "false",
            "elevation": "true",
            "preference": "recommended",
            "radiuses": -1,
            "geometry": "true",
            "extra_info": ["surface", "green"],
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=body, headers=self._headers())
            self.num_calls += 1
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Directions request failed: {resp.status_code} {resp.reason_phrase}"
            )
        return resp.json()

    async def get_round_trip(self, source, length, points, mode="walk", seed=1):
        """Use ORS built-in round_trip feature."""
        profile = self._profile(mode)
        url = f"{ORS_BASE}/directions/{profile}/geojson"
        body = {
            "coordinates": [source],
            "continue_straight": "false",
            "elevation": "true",
            "extra_info": ["surface", "green"],
            "options": {
                "round_trip": {"length": length, "points": points, "seed": seed}
            },
            "preference": "recommended",
            "radiuses": -1,
            "geometry": "true",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=body, headers=self._headers())
            self.num_calls += 1
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Round trip request failed: {resp.status_code} {resp.reason_phrase}"
            )
        return resp.json()


def parse_route_response(data, weight, surface, green, height, mode="walk"):
    """Extract route, waypoints, and edge data from an ORS directions response."""
    coords_3d = data["features"][0]["geometry"]["coordinates"]
    route = []
    for el in coords_3d:
        pt = (el[0], el[1])
        route.append(pt)
        height[pt] = el[2]
    for i in range(len(route) - 1):
        weight[(route[i], route[i + 1])] = distance.gps_crow_dist(
            route[i], route[i + 1], height[route[i]], height[route[i + 1]]
        )
    # Waypoints
    wp_indices = data["features"][0]["properties"]["way_points"]
    waypoints = [route[idx] for idx in wp_indices[:-1]]
    # Surface info
    for el in data["features"][0]["properties"]["extras"]["surface"]["values"]:
        for i in range(el[0], el[1]):
            surface[(route[i], route[i + 1])] = el[2]
    # Green info
    if mode == "walk":
        try:
            for el in data["features"][0]["properties"]["extras"]["green"]["values"]:
                for i in range(el[0], el[1]):
                    green[(route[i], route[i + 1])] = el[2]
        except KeyError:
            pass
    return route, waypoints, wp_indices


def remove_self_loops(route):
    result = [route[0]]
    for i in range(1, len(route)):
        if route[i] != result[-1]:
            result.append(route[i])
    return result


def remove_back_and_forths(old_route, old_wps):
    A = defaultdict(set)
    for i in range(len(old_route) - 1):
        A[old_route[i]].add(old_route[i + 1])
        A[old_route[i + 1]].add(old_route[i])
    s = old_route[0]
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
    new_route = [s]
    new_wps = [s]
    old_wp_set = set(old_wps)
    for i in range(1, len(old_route)):
        v = old_route[i]
        if v not in D:
            if v != new_route[-1]:
                new_route.append(v)
                if v in old_wp_set:
                    new_wps.append(v)
            else:
                new_wps.append(v)
    new_wps.pop()
    if len(new_route) <= 1:
        return old_route, old_wps
    return new_route, new_wps
