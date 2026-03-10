from collections import defaultdict
from collections import OrderedDict
import visRoutes
import distance
import Johnson
import copy
import LS
import pareto


def _splitsegment(L):
    assert len(
        L) > 2, "Error in splitsegment() function. Supplied list L must have >= 3 elements, but L =" + str(L)
    mid = len(L) // 2
    L1 = []
    L2 = []
    for i in range(0, mid+1):
        L1.append(L[i])
    for i in range(mid, len(L)):
        L2.append(L[i])
    return L1, L2


def _sameInReverse(L1, L2):
    # Returns true iff the list L2 is the reverse of L1
    if len(L1) != len(L2):
        return False
    for i in range(len(L1)):
        if L1[i] != L2[-(i+1)]:
            return False
    return True


def _removeDoubleChains(segments, source):
    # Removes double chains from the segments structure. First covert each segment value from a tuple to a list
    for el in segments:
        segments[el] = list(segments[el])
    # Identify the predecessors and successors of all vertices included in segments
    pred = defaultdict(set)
    succ = defaultdict(set)
    V = set()
    for edge in segments:
        succ[edge[0]].add(edge[1])
        pred[edge[1]].add(edge[0])
        V.add(edge[0])
        V.add(edge[1])
    # Use these structures to identify the vertices that should be smoothed (because they are internal vertices in a double chain and are not the source)
    toSmooth = set()
    for u in V:
        if u != source and u in pred and u in succ:
            if len(pred[u]) == 2 and len(succ[u]) == 2 and pred[u] == succ[u]:
                neighbours = list(succ[u])
                x = neighbours[0]
                y = neighbours[1]
                if len(segments[(x, u)]) == 2 and len(segments[(u, y)]) == 2 and len(segments[(y, u)]) == 2 and len(segments[(u, x)]) == 2:
                    toSmooth.add(u)
    # Perform smoothing on each vertex u in the toSmooth set. We do this by considering its two neighbours x and y
    for u in toSmooth:
        neighbours = list(succ[u])
        # If the following statement is not true, u has become involved in a "loop" like this (u,x), (x,u). In other words, x == y, so we do not smooth it
        if len(neighbours) == 2:
            x = neighbours[0]
            y = neighbours[1]
            if (x in toSmooth and y not in toSmooth and x in succ[y] and y in succ[x]) or (y in toSmooth and x not in toSmooth and y in succ[x] and x in succ[y]):
                if y in toSmooth and x not in toSmooth:
                    y, x = x, y
                # In this case, we have a cycle involving 3 vertices: u and x, which both need smoothing, and y, which does not. Special actions are needed here
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
                # otherwise, we can smooth in the expected way
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
    # Finally, covert each segment value from a list back to a tuple
    for el in segments:
        segments[el] = tuple(segments[el])


def _getSmoothGraph(R, weight, height, surface, green, travelMode, doVis=False):
    # Takes the set of routes defined by the coordinates in R and constructs a smaller, smoothed digraph
    for i in range(len(R)):
        assert len(
            R[i]) > 2, "Each route in MakeSmoothGraph() must have at least 3 vertices"
        assert R[i][0] == R[i][-1], "The terminals of each route in MakeSmoothPath() should be equal"
    # If desired do a graph visualisation of R
    if doVis == True:
        visRoutes.visualiseRGraph(R)
    # Form the new "smoothed graph". First, generate a set of vertices and arcs in R
    V = set()
    E = set()
    for i in range(len(R)):
        for j in range(len(R[i]) - 1):
            V.add(R[i][j])
            V.add(R[i][j+1])
            E.add((R[i][j], R[i][j+1]))
    # Now, for each vertex, generate a set of successor and predecessor nodes from E
    pred = dict()
    succ = dict()
    for u in V:
        pred[u] = set()
        succ[u] = set()
    for arc in E:
        succ[arc[0]].add(arc[1])
        pred[arc[1]].add(arc[0])
    # Now identify the "junction" vertices (these are vertices where we have a choice of "entering edge" or "leaving edge" (i.e. they have > 1 predecessor OR > 1 successor)
    junctionSet = set()
    for u in V:
        if len(pred[u]) > 1 or len(succ[u]) > 1:
            junctionSet.add(u)
    # Also treat the source vertex as a junction (this ensures it is definitely in the smoothed graph)
    source = R[0][0]
    junctionSet.add(source)
    # A "segment" is a path of non-junction vertices between two junction vertices. Now calculate the set of all segments in the original graph
    segmentSet = set()
    U = copy.deepcopy(junctionSet)
    while len(U) > 0:
        # Choose a junction vertex u with at least one out arc (u,v) and find a path P to another junction vertex
        u = next(iter(U))
        v = next(iter(succ[u]))
        P = [u, v]
        succ[u].remove(v)
        pred[v].remove(u)
        if len(succ[u]) == 0:
            U.remove(u)
        while P[-1] not in junctionSet:
            u = v
            v = next(iter(succ[u]))
            P.append(v)
            succ[u].remove(v)
            pred[v].remove(u)
        segmentSet.add(tuple(P))
    # Now convert the set of segments into a dictionary. The keys are defined using the (directed) pair of
    # terminal vertices; the values are a list of segments with these terminal values, ordered by size
    segments = defaultdict(list)
    for seg in segmentSet:
        segments[(seg[0], seg[-1])].append(seg)
    for el in segments:
        segments[el].sort(key=len)
    # Identify the elements of segments containing more than one segment. These define parallel edges. In these
    # cases we split all except the shortest segments. This is like performing an elementary subdivision
    keys = [key for key in segments.keys() if len(segments[key]) > 1]
    for el in keys:
        for j in range(1, len(segments[el])):
            L1, L2 = _splitsegment(segments[el][j])
            segments[(L1[0], L1[-1])] = [tuple(L1)]
            segments[(L2[0], L2[-1])] = [tuple(L2)]
        segments[el] = [segments[el][0]]
    # Because each element of D is now a list containing just one segment, get rid of the containing list
    for el in segments:
        segments[el] = segments[el][0]
    # We now also need to do a subdivision of any single loops that remain (parallel loops will have been handled above)
    keys = [key for key in segments.keys() if segments[key][0]
         == segments[key][-1]]
    for el in keys:
        L1, L2 = _splitsegment(segments[el])
        segments[(L1[0], L1[-1])] = tuple(L1)
        segments[(L2[0], L2[-1])] = tuple(L2)
        del segments[el]
    # The segment's structure has now been formed. Now modify it further by eliminating "double chains"
    _removeDoubleChains(segments, source)
    # Now map each vertex to an integer 0,1,2,... with the source equal to.
    coordsToNum = dict()
    numToCoords = dict()
    coordsToNum[R[0][0]] = 0
    numToCoords[0] = R[0][0]
    cnt = 1
    for el in segments:
        if el[0] not in coordsToNum:
            coordsToNum[el[0]] = cnt
            numToCoords[cnt] = el[0]
            cnt += 1
        if el[1] not in coordsToNum:
            coordsToNum[el[1]] = cnt
            numToCoords[cnt] = el[1]
            cnt += 1
    # Use these maps to construct the smoothed graph in adjacency list format (i.e. an ordered dictionary of sets)
    smoothGraph = OrderedDict()
    for v in range(len(numToCoords)):
        smoothGraph[v] = set()
    for el in segments:
        u = coordsToNum[el[0]]
        v = coordsToNum[el[1]]
        smoothGraph[u].add(v)
    # Now we want to calculate the weight (W) of each edge in smoothGraph
    W = dict()
    for el in segments:
        W[(coordsToNum[el[0]], coordsToNum[el[1]])] = distance.GPSCrowPathDist(segments[el], weight)
    # For the overlap measure in local search, we also store a set of all double-ended arcs (i.e. if (u,v) and (v,u) exist and their segments are the same in reverse, we store {u,v})
    doubleArcSet = set()
    for el in W:
        if (el[1], el[0]) in W and frozenset([el[0], el[1]]) not in doubleArcSet:
            if _sameInReverse(segments[(numToCoords[el[0]], numToCoords[el[1]])], segments[(numToCoords[el[1]], numToCoords[el[0]])]):
                doubleArcSet.add(frozenset([el[0], el[1]]))
    # Visualise the smoothed, relabelled graph
    if doVis == True:
        visRoutes.visualiseSmoothGraph(smoothGraph, numToCoords, W)
    # Return the relevant data structures
    return smoothGraph, W, segments, doubleArcSet, coordsToNum, numToCoords


def _reconstructRoute(C, segments, numToCoords):
    # Takes a solution C (defined on the smoothed graph) and constructs the corresponding route on the actual map
    assert len(
        C) > 2, "Error in _constructRouteFromCycle. C must have more than one edge"
    L = []
    for i in range(len(C)-2):
        L += list(segments[(numToCoords[C[i]], numToCoords[C[i+1]])])
        L.pop()
    L += list(segments[(numToCoords[C[-2]], numToCoords[C[-1]])])
    return L


def _updateArchiveWithSol(archive, archiveCosts, newCost, C):
    # Assumes the archive set comprises mutually non-dominating cost vectors
    if len(C) == 0:
        # We do not allow the null solution to enter the archive
        return archive, archiveCosts
    removingSolutions = False
    for i in range(len(archiveCosts)):
        if pareto.dominates(newCost, archiveCosts[i]):
            # Mark element i in the archive for deletion
            archive[i] = None
            archiveCosts[i] = None
            removingSolutions = True
        elif pareto.worseThan(newCost, archiveCosts[i]):
            # newCost is worse than (or equal to) everything in the set, so end
            return archive, archiveCosts
    # If we are here, we're returning a modified archive set
    if removingSolutions:
        # First remove any solutions that are now dominated
        tempArchive = []
        tempArchiveCosts = []
        for i in range(len(archive)):
            if archive[i] != None:
                tempArchive.append(archive[i])
                tempArchiveCosts.append(archiveCosts[i])
        archive = tempArchive
        archiveCosts = tempArchiveCosts
    # Add the solution C to the archive
    archive.append(C)
    archiveCosts.append(newCost)
    return archive, archiveCosts


def _getCostVector(C, W, k, doubleArcSet):
    # Return a list of cost values for the solution C
    Wtotal = 0
    for i in range(len(C) - 1):
        Wtotal += W[(C[i], C[i+1])]
    if Wtotal == 0:
        return [0, 0]
    else:
        return [round(abs(k - Wtotal)), round(((distance.getOverlapDistSmoothed(C, W, doubleArcSet))/Wtotal)*100)]


def optimise(solSet, k, weight, height, surface, green, travelMode, LSOption, doVis=False):
    # Get the relevant structures and create the smoothed graph. The source corresponds to vertex 0 in the smoothed graph. First copy the vertex sequences into R,
    # being careful to remove self-loops (u,u)
    R = []
    for i in range(len(solSet)):
        R.append([solSet[i]["routeVertices"][0]])
        for j in range(1, len(solSet[i]["routeVertices"])):
            if R[-1][-1] != solSet[i]["routeVertices"][j]:
                R[-1].append(solSet[i]["routeVertices"][j])
    smoothGraph, W, segments, doubleArcSet, coordsToNum, numToCoords = _getSmoothGraph(
        R, weight, height, surface, green, travelMode, doVis)
    print()
    print("Smoothed graph has n =", len(smoothGraph), "vertices and m =",
          len(W), "arcs (containing", len(doubleArcSet), "double ended edges)")

    # Convert all the solutions in R to corresponding solutions in the smooth graph
    newSolSet = [[0] for i in range(len(R))]
    for i in range(len(R)):
        for j in range(1, len(R[i])):
            u = R[i][j]
            if u in coordsToNum:
                if newSolSet[i][-1] != coordsToNum[u]:
                    newSolSet[i].append(coordsToNum[u])

    # Now parse this solution set to form an archive set of mutually non-dominating solutions
    archive = [newSolSet[0]]
    archiveCosts = [_getCostVector(newSolSet[0], W, k, doubleArcSet)]
    for i in range(1, len(newSolSet)):
        archive, archiveCosts = _updateArchiveWithSol(
            archive, archiveCosts, _getCostVector(newSolSet[i], W, k, doubleArcSet), newSolSet[i])
    print("Starting archive set has costs =")
    print(archiveCosts)

    if LSOption == 1 or LSOption == 2:
        # Do the local search algorithm
        print("\nRunning Local Search algorithm, Option", LSOption, "...")
        archive, archiveCosts = LS.multiObjectiveLocalSearch(
            smoothGraph, W, doubleArcSet, k, archive, archiveCosts, LSOption)
        print("...Done.\n")
    elif LSOption == 3:
        # Do Johnson's algorithm. This iterates through all s-cycles and considers updates to the archive
        print("\nRunning Johnson's algorithm. This may take some time...")
        cnt = 0
        for C in Johnson.Johnson(smoothGraph, 0):
            cnt += 1
            archive, archiveCosts = _updateArchiveWithSol(
                archive, archiveCosts, _getCostVector(C, W, k, doubleArcSet), C)
        print("...Done.", cnt, "cycle(s) produced\n")

    # sort the archive into cost order
    archiveCosts, archive = zip(*sorted(zip(archiveCosts, archive)))
    archiveCosts = list(archiveCosts)
    archive = list(archive)
    print("Final archive set has costs =")
    print(archiveCosts)

    # Finally, convert solutions in the archive back to the original representation. Costs are output at length (to nearest m) and percentage overlap (rounded to nearest whole number)
    A = []
    for i in range(len(archive)):
        A.append(_reconstructRoute(archive[i], segments, numToCoords))
    return A, archiveCosts
