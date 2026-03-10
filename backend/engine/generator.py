"""Main route generation orchestrator.

Adapted from makeroundtrip.py by R. Lewis and P. Corcoran, Cardiff University.

Original publication:
  Lewis, R. and P. Corcoran (2024) "Fast Algorithms for Computing Fixed-Length
  Round Trips in Real-World Street Networks". Springer Nature Computer Science,
  vol. 5, 868. https://link.springer.com/article/10.1007/s42979-024-03223-3

Original source: https://zenodo.org/doi/10.5281/zenodo.8154412
"""

import copy
import logging
from . import distance, polygons, graph, scoring
from .ors_client import ORSClient, parse_route_response, remove_self_loops, remove_back_and_forths

logger = logging.getLogger(__name__)

MAX_WP = 50


def _get_initial_polygons(source, k, initial_bearing, n, isochrone, max_len):
    polygon_list = []
    for reduction in [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]:
        for aspect_ratio in [1, 1/2, 2, 1/3, 3, 1/4, 4, 1/5, 5, 1/6, 6, 1/7, 7, 1/8, 8, 1/9, 9, 1/10, 10]:
            for angle in [0, 90, 180, 270, 30, 120, 210, 300, 60, 150, 240, 330]:
                bearing = (initial_bearing + angle) % 360
                coords = polygons.get_ellipse_gps_coords(
                    source, reduction * k, bearing, aspect_ratio, n
                )
                if polygons.all_coords_inside_isochrone(coords, isochrone):
                    polygon_list.append({
                        "estimated_wps": coords,
                        "estimated_wps_perimeter": reduction * k,
                        "degree_bearing": bearing,
                    })
                    if len(polygon_list) >= max_len:
                        return polygon_list
    return polygon_list


def _route_similarity(route_a, route_b):
    """Compute edge overlap ratio between two routes (0=disjoint, 1=identical)."""
    edges_a = set()
    for i in range(len(route_a) - 1):
        edges_a.add(frozenset([route_a[i], route_a[i + 1]]))
    edges_b = set()
    for i in range(len(route_b) - 1):
        edges_b.add(frozenset([route_b[i], route_b[i + 1]]))
    if len(edges_a) == 0 or len(edges_b) == 0:
        return 0
    overlap = len(edges_a & edges_b)
    return overlap / min(len(edges_a), len(edges_b))


def _deduplicate_routes(sol_list, threshold=0.85):
    """Remove routes that are >threshold similar to a better-scored route."""
    if len(sol_list) <= 1:
        return sol_list
    kept = [sol_list[0]]
    for sol in sol_list[1:]:
        is_dup = False
        for existing in kept:
            if _route_similarity(sol["route"], existing["route"]) > threshold:
                is_dup = True
                break
        if not is_dup:
            kept.append(sol)
    return kept


async def _fetch_polygon_routes(ors_client, polygon_list, polygon_points, mode,
                                 remove_backtracks, weight, surface, green, height):
    """Fetch routes using the isochrone-polygon method. Returns list of solution dicts."""
    sol_list = []
    n = polygon_points
    polygons_per_call = (MAX_WP - 1) // n

    # Process in batches
    for j in range(0, len(polygon_list), polygons_per_call):
        sub_list = polygon_list[j:j + polygons_per_call]
        coords = []
        for poly in sub_list:
            coords += copy.deepcopy(poly["estimated_wps"])
        coords.append(sub_list[0]["estimated_wps"][0])

        try:
            data = await ors_client.get_directions(coords, mode)
            full_coords_3d = data["features"][0]["geometry"]["coordinates"]
            full_route = []
            for el in full_coords_3d:
                pt = (el[0], el[1])
                full_route.append(pt)
                height[pt] = el[2]
            for k_idx in range(len(full_route) - 1):
                weight[(full_route[k_idx], full_route[k_idx + 1])] = distance.gps_crow_dist(
                    full_route[k_idx], full_route[k_idx + 1],
                    height[full_route[k_idx]], height[full_route[k_idx + 1]]
                )
            # Surface
            for el in data["features"][0]["properties"]["extras"]["surface"]["values"]:
                for si in range(el[0], el[1]):
                    if si + 1 < len(full_route):
                        surface[(full_route[si], full_route[si + 1])] = el[2]
            # Green
            if mode == "walk":
                try:
                    for el in data["features"][0]["properties"]["extras"]["green"]["values"]:
                        for si in range(el[0], el[1]):
                            if si + 1 < len(full_route):
                                green[(full_route[si], full_route[si + 1])] = el[2]
                except KeyError:
                    pass

            # Split into sub-routes at every n-th waypoint
            wp_indices = data["features"][0]["properties"]["way_points"]
            split_points = [wp_indices[i_wp] for i_wp in range(0, len(wp_indices), n)]

            all_wps = [full_route[wp_indices[i_wp]] for i_wp in range(len(wp_indices) - 1)]
            wps_list = []
            cnt = 0
            for si in range(len(split_points) - 1):
                wp = []
                for _ in range(n):
                    if cnt < len(all_wps):
                        wp.append(all_wps[cnt])
                        cnt += 1
                wps_list.append(wp)

            for si in range(len(split_points) - 1):
                sub_route = list(full_route[split_points[si]:split_points[si + 1]])
                if len(sub_route) > 1:
                    sub_route.append(sub_route[0])
                    sub_route = remove_self_loops(sub_route)
                    if remove_backtracks and si < len(wps_list):
                        sub_route, _ = remove_back_and_forths(sub_route, wps_list[si])
                    if len(sub_route) > 2:
                        route_len = distance.gps_crow_path_dist(sub_route, weight)
                        overlap = distance.get_overlap_dist_orig_graph(sub_route, weight)
                        sol_list.append({
                            "route": sub_route,
                            "length": route_len,
                            "overlap_pct": (overlap / route_len * 100) if route_len > 0 else 0,
                        })
        except Exception as e:
            logger.warning(f"Polygon route batch failed: {e}")

    return sol_list


async def _fetch_round_trip_routes(ors_client, source, target_distance, mode,
                                    num_seeds, weight, surface, green, height):
    """Fetch routes using ORS round_trip with multiple seeds. Returns list of solution dicts."""
    sol_list = []
    for seed in range(1, num_seeds + 1):
        try:
            data = await ors_client.get_round_trip(source, target_distance, 3, mode, seed)
            route, wps, wp_indices = parse_route_response(data, weight, surface, green, height, mode)
            route = remove_self_loops(route)
            if len(route) > 2:
                route_len = distance.gps_crow_path_dist(route, weight)
                overlap = distance.get_overlap_dist_orig_graph(route, weight)
                sol_list.append({
                    "route": route,
                    "length": route_len,
                    "overlap_pct": (overlap / route_len * 100) if route_len > 0 else 0,
                })
        except Exception as e:
            logger.warning(f"Round trip seed {seed} failed: {e}")
    return sol_list


async def generate_routes(
    source: list,
    target_distance: int,
    mode: str = "walk",
    preferences: dict | None = None,
    ors_client: ORSClient | None = None,
    num_polygons: int = 3,
    polygon_points: int = 3,
    algorithm: int = 1,
    iterations: int = 2,
    remove_backtracks: bool = True,
    on_progress=None,
):
    """Generate circular routes and return scored results.

    Uses a hybrid approach: both the isochrone-polygon method AND ORS round_trip
    with multiple seeds, then deduplicates and scores all candidates.
    """
    if preferences is None:
        preferences = {}

    weight = {}
    surface = {}
    green = {}
    height = {}

    async def progress(step, pct):
        if on_progress:
            await on_progress(step, pct)

    await progress("Computing reachable area", 10)

    # Step 1: Get isochrone
    iso, shrink_factor, init_bearing = await ors_client.get_isochrone(
        source, target_distance / 2, mode
    )
    logger.info(f"Isochrone obtained, shrink={shrink_factor:.2f}, bearing={init_bearing:.0f}")

    await progress("Generating candidate polygons", 20)

    # Step 2: Generate polygons
    polygons_per_call = (MAX_WP - 1) // polygon_points
    max_polygons = iterations * polygons_per_call
    polygon_list = _get_initial_polygons(
        source,
        target_distance * shrink_factor,
        init_bearing,
        polygon_points,
        iso,
        max_polygons,
    )
    logger.info(f"Generated {len(polygon_list)} candidate polygons")

    await progress("Fetching routes from OpenRouteService", 30)

    # Step 3: Fetch routes using BOTH methods for diversity
    sol_list = []

    # 3a: Polygon method (if we got polygons)
    if len(polygon_list) > 0:
        polygon_sols = await _fetch_polygon_routes(
            ors_client, polygon_list, polygon_points, mode,
            remove_backtracks, weight, surface, green, height
        )
        sol_list.extend(polygon_sols)
        logger.info(f"Polygon method produced {len(polygon_sols)} routes")

    await progress("Fetching diverse alternatives", 55)

    # 3b: ORS round_trip with multiple seeds (always — this is the diversity source)
    num_seeds = max(3, iterations + 2)
    round_trip_sols = await _fetch_round_trip_routes(
        ors_client, source, target_distance, mode,
        num_seeds, weight, surface, green, height
    )
    sol_list.extend(round_trip_sols)
    logger.info(f"Round trip method produced {len(round_trip_sols)} routes")

    if len(sol_list) == 0:
        raise ValueError("No routes could be generated. Try a different location or distance.")

    await progress("Scoring and ranking", 75)

    # Step 4: Score all routes
    scored = []
    for sol in sol_list:
        route = sol["route"]
        if len(route) < 3:
            continue
        try:
            metrics = scoring.compute_route_metrics(route, weight, height, surface, green)
            score = scoring.score_route(metrics, target_distance, preferences)
            scored.append({**sol, "metrics": metrics, "score": score})
        except Exception as e:
            logger.warning(f"Scoring failed for a route: {e}")

    if len(scored) == 0:
        raise ValueError("No valid routes could be scored.")

    # Sort by score descending
    scored.sort(key=lambda r: r["score"], reverse=True)

    # Step 5: Deduplicate similar routes (keep best-scored variant)
    scored = _deduplicate_routes(scored, threshold=0.80)
    logger.info(f"After dedup: {len(scored)} unique routes")

    await progress("Building profiles", 90)

    # Step 6: Build final results
    results = []
    for i, sol in enumerate(scored):
        route = sol["route"]
        metrics = sol["metrics"]
        elevation_profile = scoring.build_elevation_profile(route, weight, height)
        surface_profile = scoring.build_surface_profile(route, weight, surface)
        geojson_coords = [[pt[0], pt[1]] for pt in route]

        results.append({
            "id": i,
            "coordinates": geojson_coords,
            "metrics": metrics,
            "score": sol["score"],
            "costs": [round(abs(target_distance - metrics["length"])), round(sol["overlap_pct"])],
            "elevation_profile": elevation_profile,
            "surface_profile": surface_profile,
        })

    await progress("Done", 100)

    return {
        "routes": results,
        "isochrone": [[pt[0], pt[1]] for pt in iso],
        "source": source,
        "target_distance": target_distance,
        "mode": mode,
    }
