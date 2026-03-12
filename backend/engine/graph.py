"""Graph construction, smoothing, and Pareto optimization.

Adapted from optimisation.py, Johnson.py, LS.py, and pareto.py
by R. Lewis and P. Corcoran, Cardiff University.

Original publication:
  Lewis, R. and P. Corcoran (2024) "Fast Algorithms for Computing Fixed-Length
  Round Trips in Real-World Street Networks". Springer Nature Computer Science,
  vol. 5, 868. https://link.springer.com/article/10.1007/s42979-024-03223-3

Original source: https://zenodo.org/doi/10.5281/zenodo.8154412
"""

from collections import defaultdict, OrderedDict
from . import distance
import copy


def _split_segment(L):
    mid = len(L) // 2
    return L[: mid + 1], L[mid:]


def _same_in_reverse(L1, L2):
    if len(L1) != len(L2):
        return False
    for i in range(len(L1)):
        if L1[i] != L2[-(i + 1)]:
            return False
    return True


def _remove_double_chains(segments, source):
    for el in segments:
        segments[el] = list(segments[el])
    pred = defaultdict(set)
    succ = defaultdict(set)
    V = set()
    for edge in segments:
        succ[edge[0]].add(edge[1])
        pred[edge[1]].add(edge[0])
        V.add(edge[0])
        V.add(edge[1])
    to_smooth = set()
    for u in V:
        if u != source and u in pred and u in succ:
            if len(pred[u]) == 2 and len(succ[u]) == 2 and pred[u] == succ[u]:
                neighbours = list(succ[u])
                x, y = neighbours[0], neighbours[1]
                if (
                    len(segments[(x, u)]) == 2
                    and len(segments[(u, y)]) == 2
                    and len(segments[(y, u)]) == 2
                    and len(segments[(u, x)]) == 2
                ):
                    to_smooth.add(u)
    for u in to_smooth:
        neighbours = list(succ[u])
        if len(neighbours) == 2:
            x, y = neighbours[0], neighbours[1]
            if (x in to_smooth and y not in to_smooth and x in succ[y] and y in succ[x]) or (
                y in to_smooth and x not in to_smooth and y in succ[x] and x in succ[y]
            ):
                if y in to_smooth and x not in to_smooth:
                    y, x = x, y
                XY = segments[(x, u)]
                XY.pop()
                XY += segments[(u, y)]
                del segments[(x, y)]
                del segments[(x, u)]
                del segments[(u, x)]
                del segments[(u, y)]
                del segments[(y, u)]
                segments[(x, y)] = XY
                del succ[u]
                succ[x].remove(u)
                succ[y].remove(u)
            else:
                XY = segments[(x, u)]
                XY.pop()
                XY += segments[(u, y)]
                YX = segments[(y, u)]
                YX.pop()
                YX += segments[(u, x)]
                del segments[(u, y)]
                del segments[(y, u)]
                del segments[(u, x)]
                del segments[(x, u)]
                segments[(x, y)] = XY
                segments[(y, x)] = YX
                del succ[u]
                succ[x].remove(u)
                succ[x].add(y)
                succ[y].remove(u)
                succ[y].add(x)
    for el in segments:
        segments[el] = tuple(segments[el])


def get_smooth_graph(R, weight):
    """Build a smoothed digraph from route set R. Returns graph structures."""
    V = set()
    E = set()
    for route in R:
        for j in range(len(route) - 1):
            V.add(route[j])
            V.add(route[j + 1])
            E.add((route[j], route[j + 1]))
    pred = {u: set() for u in V}
    succ = {u: set() for u in V}
    for arc in E:
        succ[arc[0]].add(arc[1])
        pred[arc[1]].add(arc[0])
    junction_set = set()
    for u in V:
        if len(pred[u]) > 1 or len(succ[u]) > 1:
            junction_set.add(u)
    source = R[0][0]
    junction_set.add(source)
    segment_set = set()
    U = copy.deepcopy(junction_set)
    while len(U) > 0:
        u = next(iter(U))
        v = next(iter(succ[u]))
        P = [u, v]
        succ[u].remove(v)
        pred[v].remove(u)
        if len(succ[u]) == 0:
            U.remove(u)
        while P[-1] not in junction_set:
            u = v
            v = next(iter(succ[u]))
            P.append(v)
            succ[u].remove(v)
            pred[v].remove(u)
        segment_set.add(tuple(P))
    segments = defaultdict(list)
    for seg in segment_set:
        segments[(seg[0], seg[-1])].append(seg)
    for el in segments:
        segments[el].sort(key=len)
    keys = [key for key in segments.keys() if len(segments[key]) > 1]
    for el in keys:
        for j in range(1, len(segments[el])):
            L1, L2 = _split_segment(list(segments[el][j]))
            segments[(L1[0], L1[-1])] = [tuple(L1)]
            segments[(L2[0], L2[-1])] = [tuple(L2)]
        segments[el] = [segments[el][0]]
    for el in segments:
        segments[el] = segments[el][0]
    keys = [key for key in segments.keys() if segments[key][0] == segments[key][-1]]
    for el in keys:
        L1, L2 = _split_segment(list(segments[el]))
        segments[(L1[0], L1[-1])] = tuple(L1)
        segments[(L2[0], L2[-1])] = tuple(L2)
        del segments[el]
    _remove_double_chains(segments, source)
    coords_to_num = {}
    num_to_coords = {}
    coords_to_num[R[0][0]] = 0
    num_to_coords[0] = R[0][0]
    cnt = 1
    for el in segments:
        for endpoint in [el[0], el[1]]:
            if endpoint not in coords_to_num:
                coords_to_num[endpoint] = cnt
                num_to_coords[cnt] = endpoint
                cnt += 1
    smooth_graph = OrderedDict()
    for v in range(len(num_to_coords)):
        smooth_graph[v] = set()
    for el in segments:
        u = coords_to_num[el[0]]
        v = coords_to_num[el[1]]
        smooth_graph[u].add(v)
    W = {}
    for el in segments:
        W[(coords_to_num[el[0]], coords_to_num[el[1]])] = distance.gps_crow_path_dist(
            segments[el], weight
        )
    double_arc_set = set()
    for el in W:
        if (el[1], el[0]) in W and frozenset([el[0], el[1]]) not in double_arc_set:
            if _same_in_reverse(
                segments[(num_to_coords[el[0]], num_to_coords[el[1]])],
                segments[(num_to_coords[el[1]], num_to_coords[el[0]])],
            ):
                double_arc_set.add(frozenset([el[0], el[1]]))
    return smooth_graph, W, segments, double_arc_set, coords_to_num, num_to_coords


def compute_segment_metrics(segments, coords_to_num, weight, height, surface, green):
    """Compute per-segment metrics for the smooth graph.

    Returns dict mapping (u_num, v_num) -> {length, climb, unpaved_dist,
    paved_dist, green_sum, green_dist} for each segment in the smooth graph.
    """
    from .scoring import PAVED_SURFACES, UNPAVED_SURFACES

    seg_metrics = {}
    for (gps_u, gps_v), seg in segments.items():
        total_length = 0
        total_climb = 0
        paved_dist = 0
        unpaved_dist = 0
        green_sum = 0
        green_count = 0

        for i in range(len(seg) - 1):
            edge = (seg[i], seg[i + 1])
            edge_len = weight.get(edge, 0)
            total_length += edge_len

            h1 = height.get(seg[i], 0)
            h2 = height.get(seg[i + 1], 0)
            if h2 > h1:
                total_climb += h2 - h1

            s = surface.get(edge, 0)
            if s in PAVED_SURFACES:
                paved_dist += edge_len
            elif s in UNPAVED_SURFACES:
                unpaved_dist += edge_len

            g = green.get(edge, None)
            if g is not None:
                green_sum += g * edge_len
                green_count += edge_len

        u_num = coords_to_num[gps_u]
        v_num = coords_to_num[gps_v]
        seg_metrics[(u_num, v_num)] = {
            "length": total_length,
            "climb": total_climb,
            "paved_dist": paved_dist,
            "unpaved_dist": unpaved_dist,
            "green_sum": green_sum,
            "green_dist": green_count,
        }

    return seg_metrics


def reconstruct_route(C, segments, num_to_coords):
    L = []
    for i in range(len(C) - 2):
        L += list(segments[(num_to_coords[C[i]], num_to_coords[C[i + 1]])])
        L.pop()
    L += list(segments[(num_to_coords[C[-2]], num_to_coords[C[-1]])])
    return L


def dominates(a, b):
    """Returns True if cost vector a dominates b (all <= and at least one <)."""
    dominated = False
    for i in range(len(a)):
        if a[i] > b[i]:
            return False
        if a[i] < b[i]:
            dominated = True
    return dominated


def worse_than(a, b):
    """Returns True if a is worse than or equal to b in all objectives."""
    for i in range(len(a)):
        if a[i] < b[i]:
            return False
    return True


def get_cost_vector(C, W, k, double_arc_set):
    w_total = 0
    for i in range(len(C) - 1):
        w_total += W[(C[i], C[i + 1])]
    if w_total == 0:
        return [0, 0]
    return [
        round(abs(k - w_total)),
        round((distance.get_overlap_dist_smoothed(C, W, double_arc_set) / w_total) * 100),
    ]


def update_archive(archive, archive_costs, new_cost, C):
    if len(C) == 0:
        return archive, archive_costs
    removing = False
    for i in range(len(archive_costs)):
        if dominates(new_cost, archive_costs[i]):
            archive[i] = None
            archive_costs[i] = None
            removing = True
        elif worse_than(new_cost, archive_costs[i]):
            return archive, archive_costs
    if removing:
        archive = [a for a in archive if a is not None]
        archive_costs = [c for c in archive_costs if c is not None]
    archive.append(C)
    archive_costs.append(new_cost)
    return archive, archive_costs


def build_pareto_front(sol_set, k, weight):
    """Build the Pareto front from a set of candidate routes.
    Returns list of routes and their costs [length_error, overlap%]."""
    R = []
    for sol in sol_set:
        route = [sol["route"][0]]
        for j in range(1, len(sol["route"])):
            if route[-1] != sol["route"][j]:
                route.append(sol["route"][j])
        R.append(route)

    if len(R) == 0:
        return [], []

    # Check all routes have at least 3 vertices
    R = [r for r in R if len(r) > 2 and r[0] == r[-1]]
    if len(R) == 0:
        # Fall back: return all solutions as-is
        return sol_set, [[0, 0]] * len(sol_set)

    smooth_graph, W, segments, double_arc_set, coords_to_num, num_to_coords = (
        get_smooth_graph(R, weight)
    )

    # Convert solutions to smooth graph representation
    new_sol_set = [[0] for _ in range(len(R))]
    for i in range(len(R)):
        for j in range(1, len(R[i])):
            u = R[i][j]
            if u in coords_to_num:
                if new_sol_set[i][-1] != coords_to_num[u]:
                    new_sol_set[i].append(coords_to_num[u])

    # Build archive
    archive = [new_sol_set[0]]
    archive_costs = [get_cost_vector(new_sol_set[0], W, k, double_arc_set)]
    for i in range(1, len(new_sol_set)):
        archive, archive_costs = update_archive(
            archive,
            archive_costs,
            get_cost_vector(new_sol_set[i], W, k, double_arc_set),
            new_sol_set[i],
        )

    # Sort by cost
    if len(archive_costs) > 0:
        archive_costs, archive = zip(*sorted(zip(archive_costs, archive)))
        archive_costs = list(archive_costs)
        archive = list(archive)

    # Reconstruct routes
    result_routes = []
    for sol in archive:
        result_routes.append(reconstruct_route(sol, segments, num_to_coords))

    return result_routes, archive_costs
