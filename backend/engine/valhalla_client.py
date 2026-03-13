"""Valhalla API client — async wrapper for directions and isochrones.

Valhalla costing options used:
  pedestrian: use_hills (0=no hill penalty/neutral, 1=strongly avoid hills/flat), crossing_cost (road crossing penalty)
  bicycle: use_hills (0=no hill penalty/neutral, 1=strongly avoid hills/flat)
"""

import httpx
from collections import defaultdict
from . import distance
import logging

logger = logging.getLogger(__name__)

TRAVEL_MODES = {
    "cycle": "bicycle",
    "walk": "pedestrian",
}


def _decode_polyline(encoded: str, precision: int = 6) -> list:
    """Decode a Valhalla-encoded polyline (precision=6) to list of [lon, lat] pairs."""
    inv = 1.0 / (10 ** precision)
    decoded = []
    prev_lat = 0
    prev_lon = 0
    i = 0
    n = len(encoded)
    while i < n:
        result = 0
        shift = 0
        while True:
            b = ord(encoded[i]) - 63
            i += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = -(result >> 1) if (result & 1) else (result >> 1)
        prev_lat += dlat

        result = 0
        shift = 0
        while True:
            b = ord(encoded[i]) - 63
            i += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlon = -(result >> 1) if (result & 1) else (result >> 1)
        prev_lon += dlon

        decoded.append([prev_lon * inv, prev_lat * inv])

    return decoded


class ValhallaClient:
    def __init__(self, url: str):
        self.url = url.rstrip("/")
        self.num_calls = 0

    def _costing(self, mode: str) -> str:
        return TRAVEL_MODES.get(mode, "pedestrian")

    async def get_isochrone(self, source, dist_meters, mode="walk"):
        costing = self._costing(mode)
        url = f"{self.url}/isochrone"
        body = {
            "locations": [{"lon": source[0], "lat": source[1]}],
            "costing": costing,
            "contours": [{"distance": dist_meters / 1000}],
            "polygons": True,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=body)
            self.num_calls += 1
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Isochrone request failed: {resp.status_code} {resp.text[:200]}"
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

    async def _get_elevation(self, coords_list):
        """POST to /height for a list of [lon, lat] coords. Returns list of heights."""
        url = f"{self.url}/height"
        body = {
            "shape": [{"lat": c[1], "lon": c[0]} for c in coords_list],
            "range": False,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=body)
            self.num_calls += 1
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Height request failed: {resp.status_code} {resp.text[:200]}"
            )
        return resp.json().get("height", [])

    async def get_directions(self, coords, mode="walk", use_hills=0.5, crossing_cost=2.0,
                              weight=None, surface=None, height=None):
        """Get a route through waypoints. Populates weight/surface/height in-place.

        Returns (route, waypoints, wp_indices).
        Surface dict stores True for unpaved edges, False for paved.
        """
        costing = self._costing(mode)
        url = f"{self.url}/route"
        locations = [{"lon": c[0], "lat": c[1], "type": "break"} for c in coords]

        costing_opts: dict = {"use_hills": use_hills}
        if costing == "pedestrian":
            costing_opts["crossing_cost"] = crossing_cost

        body = {
            "locations": locations,
            "costing": costing,
            "costing_options": {costing: costing_opts},
            "shape_format": "geojson",
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=body)
            self.num_calls += 1

        if resp.status_code not in (200, 201):
            # Fallback: try without shape_format (older Valhalla versions use encoded polyline)
            body_fallback = {k: v for k, v in body.items() if k != "shape_format"}
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, json=body_fallback)
                self.num_calls += 1
            if resp.status_code not in (200, 201):
                raise RuntimeError(
                    f"Directions request failed: {resp.status_code} {resp.text[:200]}"
                )

        data = resp.json()
        trip = data.get("trip", {})
        legs = trip.get("legs", [])
        if not legs:
            raise RuntimeError("No legs in Valhalla route response")

        # Merge all legs into a single coordinate list, tracking waypoint indices
        all_coords = []
        wp_shape_indices = [0]

        for leg in legs:
            shape = leg.get("shape")
            if isinstance(shape, str):
                leg_coords = _decode_polyline(shape, precision=6)
            elif isinstance(shape, dict) and shape.get("type") == "LineString":
                leg_coords = shape["coordinates"]
            else:
                raise RuntimeError(f"Unexpected shape format: {type(shape)}")

            if all_coords:
                leg_coords = leg_coords[1:]  # skip duplicate junction point

            # Surface: iterate maneuvers and tag edges with unpaved bool
            if surface is not None:
                maneuvers = leg.get("maneuvers", [])
                base = len(all_coords)
                for m in maneuvers:
                    begin = base + m.get("begin_shape_index", 0)
                    end = base + m.get("end_shape_index", m.get("begin_shape_index", 0) + 1)
                    unpaved = m.get("unpaved", None)
                    if unpaved is not None:
                        for si in range(begin, min(end, base + len(leg_coords) - 1)):
                            # We store relative to all_coords after appending
                            surface[si] = unpaved  # temporary integer key, resolved below

            all_coords.extend(leg_coords)
            wp_shape_indices.append(len(all_coords) - 1)

        route = [tuple(c) for c in all_coords]

        # Resolve temporary surface integer keys to route edge tuples
        if surface is not None:
            int_keys = [k for k in list(surface.keys()) if isinstance(k, int)]
            for k in int_keys:
                v = surface.pop(k)
                if k + 1 < len(route):
                    surface[(route[k], route[k + 1])] = v

        # Get elevation via /height
        if height is not None:
            try:
                heights = await self._get_elevation(all_coords)
                for i, pt in enumerate(route):
                    if i < len(heights):
                        height[pt] = heights[i]
            except Exception as e:
                logger.warning(f"Elevation request failed: {e}")

        # Populate weight (3D distance using elevation if available)
        if weight is not None:
            for i in range(len(route) - 1):
                h1 = height.get(route[i], 0) if height else 0
                h2 = height.get(route[i + 1], 0) if height else 0
                weight[(route[i], route[i + 1])] = distance.gps_crow_dist(
                    route[i], route[i + 1], h1, h2
                )

        # wp_indices: [start, end_of_leg0, end_of_leg1, ...]
        wp_indices = wp_shape_indices
        waypoints = [route[i] for i in wp_indices[:-1]]

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
