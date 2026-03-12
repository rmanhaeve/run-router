"""Score routes based on user preferences.

Part of the Circular Route Generator web application.
Route generation algorithms by R. Lewis and P. Corcoran, Cardiff University.

Original publication:
  Lewis, R. and P. Corcoran (2024) "Fast Algorithms for Computing Fixed-Length
  Round Trips in Real-World Street Networks". Springer Nature Computer Science,
  vol. 5, 868. https://link.springer.com/article/10.1007/s42979-024-03223-3
"""

from . import distance


def compute_route_metrics(route, weight, height, surface):
    """Compute all metrics for a single route. Returns a dict of metric values."""
    total_length = 0
    total_climb = 0
    paved_dist = 0
    unpaved_dist = 0

    for i in range(len(route) - 1):
        edge = (route[i], route[i + 1])
        edge_len = weight.get(edge, 0)
        total_length += edge_len

        # Elevation
        h1 = height.get(route[i], 0)
        h2 = height.get(route[i + 1], 0)
        if h2 > h1:
            total_climb += h2 - h1

        # Surface: Valhalla stores True=unpaved, False=paved
        s = surface.get(edge)
        if s is False:
            paved_dist += edge_len
        elif s is True:
            unpaved_dist += edge_len

    # Overlap
    overlap_dist = distance.get_overlap_dist_orig_graph(route, weight)
    overlap_pct = (overlap_dist / total_length * 100) if total_length > 0 else 0

    # Derived metrics
    offroad_pct = (unpaved_dist / total_length * 100) if total_length > 0 else 0
    paved_pct = (paved_dist / total_length * 100) if total_length > 0 else 0

    # Elevation per km
    climb_per_km = (total_climb / (total_length / 1000)) if total_length > 0 else 0

    return {
        "length": round(total_length),
        "climb": round(total_climb),
        "climb_per_km": round(climb_per_km, 1),
        "overlap_pct": round(overlap_pct, 1),
        "offroad_pct": round(offroad_pct, 1),
        "paved_pct": round(paved_pct, 1),
    }


def score_route_preferences(metrics, preferences):
    """Score a route based on preferences only (no distance matching).

    Weights scale with how far each slider is from center (50):
    - At 50: weight=0, preference has no effect
    - At 0 or 100: weight=3, preference strongly affects score

    This means moving a slider away from center makes that dimension
    matter more in the scoring, which is directly interpretable.
    """
    score = 0
    total_weight = 0

    # Hilliness: 0=flat, 100=hilly
    hilly_pref = preferences.get("hilly", 50)
    intensity = abs(hilly_pref - 50) / 50  # 0..1
    w = intensity * 3
    if w > 0.01:
        climb_normalized = min(metrics["climb_per_km"] / 30, 1.0) * 100
        if hilly_pref > 50:
            hill_score = climb_normalized
        else:
            hill_score = 100 - climb_normalized
        score += w * hill_score
        total_weight += w

    # Surface: 0=paved, 100=trails
    offroad_pref = preferences.get("offroad", 50)
    intensity = abs(offroad_pref - 50) / 50
    w = intensity * 3
    if w > 0.01:
        if offroad_pref > 50:
            surface_score = metrics["offroad_pct"]
        else:
            surface_score = metrics["paved_pct"]
        score += w * surface_score
        total_weight += w

    # Repetition: 0=avoid repeats, 100=don't care
    rep_pref = preferences.get("repetition", 50)
    caring = 1 - rep_pref / 100  # 1=strongly avoid, 0=don't care
    w = caring * 2
    if w > 0.01:
        rep_score = max(0, 100 - metrics["overlap_pct"] * 2)
        score += w * rep_score
        total_weight += w

    if total_weight < 0.01:
        return 50  # all preferences neutral
    return round(score / total_weight, 1)


def score_route(metrics, target_distance, preferences):
    """Score a route 0-100 based on distance match and preferences.

    The tradeoff preference (0-100) controls the balance:
    - 0:  distance accuracy only, preferences ignored
    - 50: balanced (default)
    - 100: route quality only, distance accuracy ignored
    """
    tradeoff = preferences.get("tradeoff", 50)
    dist_w_scale = (100 - tradeoff) / 100   # 1.0 → 0.0
    pref_w_scale = tradeoff / 100            # 0.0 → 1.0

    score = 0
    total_weight = 0

    # Distance match
    w = dist_w_scale * 3
    if w > 0.01:
        length_error_pct = abs(metrics["length"] - target_distance) / target_distance * 100
        dist_score = max(0, 100 - length_error_pct * 2)
        score += w * dist_score
        total_weight += w

    # Preference scores
    pref_score_val = score_route_preferences(metrics, preferences)

    hilly_intensity = abs(preferences.get("hilly", 50) - 50) / 50
    offroad_intensity = abs(preferences.get("offroad", 50) - 50) / 50
    rep_caring = 1 - preferences.get("repetition", 50) / 100

    pref_weight = pref_w_scale * (hilly_intensity * 3 + offroad_intensity * 3 + rep_caring * 2)
    if pref_weight > 0.01:
        score += pref_weight * pref_score_val
        total_weight += pref_weight

    return round(score / total_weight, 1) if total_weight > 0 else 50


def build_elevation_profile(route, weight, height):
    """Build elevation profile data for charting."""
    profile = []
    cum_dist = 0
    for i, pt in enumerate(route):
        h = height.get(pt, 0)
        profile.append({"distance": round(cum_dist), "elevation": round(h, 1)})
        if i < len(route) - 1:
            cum_dist += weight.get((route[i], route[i + 1]), 0)
    return profile


def build_surface_profile(route, weight, surface):
    """Build surface type data for charting."""
    profile = []
    cum_dist = 0
    for i in range(len(route) - 1):
        edge = (route[i], route[i + 1])
        edge_len = weight.get(edge, 0)
        s = surface.get(edge)
        if s is False:
            stype = "paved"
        elif s is True:
            stype = "unpaved"
        else:
            stype = "unknown"
        profile.append({
            "start": round(cum_dist),
            "end": round(cum_dist + edge_len),
            "type": stype,
        })
        cum_dist += edge_len
    return profile
