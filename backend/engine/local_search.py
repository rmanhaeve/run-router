"""Multi-objective local search for route optimization.

Adapted from LS.py by R. Lewis and P. Corcoran, Cardiff University.

Uses BFS-based neighborhood exploration with two move types:
1. Path replacement: swap a sub-path with an alternative
2. Cycle insertion: add a new cycle at a position

Cost vector: [length_error, -preference_score]
Uses Pareto archive to maintain non-dominated solutions.

Original publication:
  Lewis, R. and P. Corcoran (2024) "Fast Algorithms for Computing Fixed-Length
  Round Trips in Real-World Street Networks". Springer Nature Computer Science,
  vol. 5, 868. https://link.springer.com/article/10.1007/s42979-024-03223-3
"""

import logging
import random
from collections import deque, defaultdict
from . import distance, scoring

logger = logging.getLogger(__name__)


def _get_path_segment_totals(path, seg_metrics, W):
    """Sum segment metrics along a path on the smooth graph."""
    length = 0
    climb = 0
    unpaved = 0
    paved = 0
    for i in range(len(path) - 1):
        edge = (path[i], path[i + 1])
        sm = seg_metrics.get(edge)
        if sm:
            length += sm["length"]
            climb += sm["climb"]
            unpaved += sm["unpaved_dist"]
            paved += sm["paved_dist"]
        else:
            length += W.get(edge, 0)
    return length, climb, unpaved, paved


def _totals_to_metrics(length, climb, unpaved, paved, overlap_pct):
    """Convert raw totals into a metrics dict compatible with scoring."""
    climb_per_km = (climb / (length / 1000)) if length > 0 else 0
    offroad_pct = (unpaved / length * 100) if length > 0 else 0
    paved_pct_val = (paved / length * 100) if length > 0 else 0
    return {
        "length": round(length),
        "climb": round(climb),
        "climb_per_km": round(climb_per_km, 1),
        "overlap_pct": round(overlap_pct, 1),
        "offroad_pct": round(offroad_pct, 1),
        "paved_pct": round(paved_pct_val, 1),
    }


def _cost_vector(C, seg_metrics, W, double_arc_set, target_distance, preferences):
    """Compute cost vector [length_error_pct, -preference_score].

    Both dimensions are on a 0-100 scale so the Pareto archive and pruning
    treat distance accuracy and preference satisfaction equally.
    """
    length, climb, unpaved, paved = _get_path_segment_totals(C, seg_metrics, W)
    overlap_dist = distance.get_overlap_dist_smoothed(C, W, double_arc_set)
    overlap_pct = (overlap_dist / length * 100) if length > 0 else 0
    metrics = _totals_to_metrics(length, climb, unpaved, paved, overlap_pct)
    pref_score = scoring.score_route_preferences(metrics, preferences)
    length_error_pct = abs(metrics["length"] - target_distance) / target_distance * 100 if target_distance > 0 else 0
    return [length_error_pct, -pref_score]


def _bfs(adj, start, excluded_edges):
    """BFS from start, avoiding excluded_edges. Returns parent map."""
    parent = {start: None}
    queue = deque([start])
    while queue:
        u = queue.popleft()
        for v in adj.get(u, set()):
            if v not in parent and (u, v) not in excluded_edges:
                parent[v] = u
                queue.append(v)
    return parent


def _reconstruct_path(parent, start, end):
    """Reconstruct path from BFS parent map."""
    path = [end]
    while path[-1] != start:
        path.append(parent[path[-1]])
    path.reverse()
    return path


def _dominates(a, b):
    """Returns True if cost vector a dominates b (all <= and at least one <)."""
    any_better = False
    for i in range(len(a)):
        if a[i] > b[i]:
            return False
        if a[i] < b[i]:
            any_better = True
    return any_better


def _worse_than(a, b):
    """Returns True if a is worse than or equal to b in all objectives."""
    for i in range(len(a)):
        if a[i] < b[i]:
            return False
    return True


def _update_archive(archive, archive_costs, new_cost, C, visited):
    """Add solution to Pareto archive if non-dominated. Returns updated archive."""
    if len(C) < 3:
        return archive, archive_costs

    removing = []
    for i in range(len(archive_costs)):
        if _dominates(new_cost, archive_costs[i]):
            removing.append(i)
        elif _worse_than(new_cost, archive_costs[i]):
            return archive, archive_costs  # dominated, discard

    if removing:
        removing_set = set(removing)
        new_archive = []
        new_costs = []
        new_visited = set()
        j = 0
        for i in range(len(archive)):
            if i not in removing_set:
                new_archive.append(archive[i])
                new_costs.append(archive_costs[i])
                if i in visited:
                    new_visited.add(j)
                j += 1
        archive = new_archive
        archive_costs = new_costs
        visited.clear()
        visited.update(new_visited)

    archive.append(C)
    archive_costs.append(new_cost)
    return archive, archive_costs


def _prune_archive(archive, archive_costs, visited, max_size):
    """Prune archive to max_size keeping best solutions."""
    if len(archive) <= max_size:
        return archive, archive_costs, visited

    # Sort by sum of costs (rough quality measure), keep best
    indices = sorted(range(len(archive)), key=lambda i: sum(archive_costs[i]))
    keep = indices[:max_size]

    new_archive = []
    new_costs = []
    new_visited = set()
    old_to_new = {}
    for j, i in enumerate(keep):
        new_archive.append(archive[i])
        new_costs.append(archive_costs[i])
        old_to_new[i] = j
        if i in visited:
            new_visited.add(j)

    return new_archive, new_costs, new_visited


def multi_objective_local_search(
    smooth_graph, W, segments, double_arc_set,
    coords_to_num, num_to_coords,
    seg_metrics,
    target_distance, preferences,
    initial_solutions,
    max_archive_size=50,
):
    """Multi-objective local search on the smoothed graph.

    Explores the neighborhood of each solution in the Pareto archive by:
    1. BFS from each vertex to find alternative paths (avoiding current route edges)
    2. Trying path replacements and cycle insertions
    3. Keeping non-dominated solutions

    Returns list of optimized solutions (vertex sequences on smooth graph).
    """
    if not initial_solutions:
        return []

    # Build adjacency
    adj = defaultdict(set)
    for u in smooth_graph:
        for v in smooth_graph[u]:
            adj[u].add(v)

    # Also build reverse adjacency for cycle insertion
    rev_adj = defaultdict(set)
    for u in adj:
        for v in adj[u]:
            rev_adj[v].add(u)

    # Initialize archive
    archive = []
    archive_costs = []
    visited = set()

    for sol in initial_solutions:
        if len(sol) < 3:
            continue
        cost = _cost_vector(sol, seg_metrics, W, double_arc_set, target_distance, preferences)
        archive, archive_costs = _update_archive(archive, archive_costs, cost, sol, visited)

    logger.info(f"Local search: initial archive size = {len(archive)}")

    iteration = 0
    max_iterations = max(len(archive) * 20, 100)
    passes_without_growth = 0
    archive_size_at_pass_start = len(archive)

    while iteration < max_iterations:
        # Find an unvisited solution
        unvisited_idx = None
        for i in range(len(archive)):
            if i not in visited:
                unvisited_idx = i
                break

        if unvisited_idx is None:
            # Completed a full pass over all archive members.
            # BFS positions are randomised, so fresh passes may find different paths.
            # Stop only after 2 consecutive passes with no archive growth.
            if len(archive) > archive_size_at_pass_start:
                passes_without_growth = 0
            else:
                passes_without_growth += 1
            if passes_without_growth >= 2:
                break
            archive_size_at_pass_start = len(archive)
            visited.clear()
            continue

        visited.add(unvisited_idx)
        C = archive[unvisited_idx]
        iteration += 1

        if len(C) < 3:
            continue

        # Edges of current solution
        C_edges = set()
        for i in range(len(C) - 1):
            C_edges.add((C[i], C[i + 1]))

        # Precompute cumulative segment totals along C
        cum = {"length": [0], "climb": [0], "unpaved": [0], "paved": [0]}
        for i in range(len(C) - 1):
            edge = (C[i], C[i + 1])
            sm = seg_metrics.get(edge, {})
            cum["length"].append(cum["length"][-1] + sm.get("length", W.get(edge, 0)))
            cum["climb"].append(cum["climb"][-1] + sm.get("climb", 0))
            cum["unpaved"].append(cum["unpaved"][-1] + sm.get("unpaved_dist", 0))
            cum["paved"].append(cum["paved"][-1] + sm.get("paved_dist", 0))

        totals = {k: v[-1] for k, v in cum.items()}

        # Explore moves at each position
        positions = list(range(len(C) - 1))
        random.shuffle(positions)

        for uPos in positions:
            u = C[uPos]
            parent = _bfs(adj, u, C_edges)

            # Move Type 1: Path Replacement
            for vPos in range(uPos + 1, len(C)):
                v = C[vPos]
                if v not in parent or v == u:
                    continue

                new_path = _reconstruct_path(parent, u, v)
                p_len, p_climb, p_unpaved, p_paved = \
                    _get_path_segment_totals(new_path, seg_metrics, W)

                # Subtract old segment, add new path
                new_length = totals["length"] - (cum["length"][vPos] - cum["length"][uPos]) + p_len
                if new_length < 100:
                    continue

                new_climb = totals["climb"] - (cum["climb"][vPos] - cum["climb"][uPos]) + p_climb
                new_unpaved = totals["unpaved"] - (cum["unpaved"][vPos] - cum["unpaved"][uPos]) + p_unpaved
                new_paved = totals["paved"] - (cum["paved"][vPos] - cum["paved"][uPos]) + p_paved

                new_C = list(C[:uPos]) + new_path + list(C[vPos + 1:])

                overlap_dist = distance.get_overlap_dist_smoothed(new_C, W, double_arc_set)
                overlap_pct = (overlap_dist / new_length * 100) if new_length > 0 else 0

                metrics = _totals_to_metrics(
                    new_length, new_climb, new_unpaved, new_paved, overlap_pct
                )
                pref_score = scoring.score_route_preferences(metrics, preferences)
                length_error_pct = abs(metrics["length"] - target_distance) / target_distance * 100 if target_distance > 0 else 0
                new_cost = [length_error_pct, -pref_score]

                archive, archive_costs = _update_archive(
                    archive, archive_costs, new_cost, new_C, visited
                )

            # Move Type 2: Cycle Insertion
            # Find a vertex x reachable from u that has an edge back to u
            for x in rev_adj.get(u, set()):
                if (x, u) not in C_edges and x in parent and x != u:
                    # Cycle: u -> ... -> x -> u
                    cycle_path = _reconstruct_path(parent, u, x) + [u]
                    c_len, c_climb, c_unpaved, c_paved = \
                        _get_path_segment_totals(cycle_path, seg_metrics, W)

                    new_length = totals["length"] + c_len
                    if new_length < 100:
                        continue

                    new_C = list(C[:uPos]) + cycle_path + list(C[uPos + 1:])

                    overlap_dist = distance.get_overlap_dist_smoothed(new_C, W, double_arc_set)
                    overlap_pct = (overlap_dist / new_length * 100) if new_length > 0 else 0

                    metrics = _totals_to_metrics(
                        new_length,
                        totals["climb"] + c_climb,
                        totals["unpaved"] + c_unpaved,
                        totals["paved"] + c_paved,
                        overlap_pct,
                    )
                    pref_score = scoring.score_route_preferences(metrics, preferences)
                    length_error_pct = abs(metrics["length"] - target_distance) / target_distance * 100 if target_distance > 0 else 0
                    new_cost = [length_error_pct, -pref_score]

                    archive, archive_costs = _update_archive(
                        archive, archive_costs, new_cost, new_C, visited
                    )
                    break  # One cycle insertion per position

            if len(archive) > max_archive_size:
                archive, archive_costs, visited = _prune_archive(
                    archive, archive_costs, visited, max_archive_size
                )

    logger.info(f"Local search: final archive size = {len(archive)}, iterations = {iteration}")
    return archive
