import random
import copy
import pareto
from collections import deque


def _bfsSet(G, W, s, T):
    # O(m) breadth-first search algorithm. The process ends if all vertices in T have visited, or all reachable vertices have been visited
    prev = dict()
    L = dict()
    visited = set()
    Q = deque()
    Q.append(s)
    visited.add(s)
    L[s] = 0
    while len(Q) > 0:
        u = Q.popleft()
        for v in G[u]:
            if v not in visited:
                visited.add(v)
                prev[v] = u
                L[v] = L[u] + W[(u, v)]
                Q.append(v)
        T.discard(u)
        if len(T) == 0:
            return L, prev
    return L, prev


def _rfsSet(G, W, s, T):
    # O(m) random-first search algorithm. The process ends if all vertices in T have visited, or all reachable vertices have been visited
    prev = dict()
    L = dict()
    visited = set()
    Q = [s]
    visited.add(s)
    L[s] = 0
    while len(Q) > 0:
        i = random.randint(0, len(Q)-1)
        u = Q[i]
        Q[i] = Q[-1]
        Q.pop()
        for v in G[u]:
            if v not in visited:
                visited.add(v)
                prev[v] = u
                L[v] = L[u] + W[(u, v)]
                Q.append(v)
        T.discard(u)
        if len(T) == 0:
            return L, prev
    return L, prev


def _getCumulative(C, W):
    # Construct a list holding the cumulative weight of the circuit defined by C
    cumulative = [0]
    for i in range(1, len(C)):
        cumulative.append(cumulative[-1] + W[(C[i-1], C[i])])
    return cumulative


def _getOverlapSet(C, W, doubleArcSet):
    total = 0
    E = dict()
    for i in range(len(C)-1):
        e = frozenset([C[i], C[i+1]])
        if e not in doubleArcSet:
            e = (C[i], C[i+1])
        if e in E:
            E[e] += 1
            total += W[(C[i], C[i+1])]
        else:
            E[e] = 1
    return E, total


def _getPerm(C):
    # Construct a permutation of the integers {0,1,...,len(C)-1}
    perm = [i for i in range(len(C))]
    random.shuffle(perm)
    return perm


def _doMove(C, uPos, vPos, P):
    # Given the circuit C = [....,uPos,...,vPos,...], replace everything between and including [uPos,...,vPos] with the path P
    CNew = []
    for i in range(uPos):
        CNew.append(C[i])
    for i in range(len(P)):
        CNew.append(P[i])
    for i in range(vPos + 1, len(C)):
        CNew.append(C[i])
    return CNew


def _getPath(s, t, prev, L):
    # Get the s-t path (if one exists) using the prev array
    P = []
    if t in L:
        u = t
        while u != s:
            P.append(u)
            u = prev[u]
        P.append(s)
        P.reverse()
    return P


def _evaluateLen(cumulativeW, uPos, v, vPos, L):
    return cumulativeW[-1] - (cumulativeW[vPos] - cumulativeW[uPos]) + L[v]


def _evaluateOverlap(C, W, doubleArcSet, u, uPos, v, vPos, prev, L, E, currentOverlap, moveType):
    total = currentOverlap
    if moveType == 1:
        # Replacing a u-v-path in C with the u-v-path in prev. First modify E by deleting the edges of the u-v-path in C
        for i in range(uPos, vPos):
            e = frozenset([C[i], C[i+1]])
            if e not in doubleArcSet:
                e = (C[i], C[i+1])
            if E[e] > 1:
                E[e] -= 1
                total -= W[(C[i], C[i+1])]
            else:
                del E[e]
        # The following is necessary to guard against rounding errors bringing the total to slightly beneath zero
        if total < 0.0:
            total = 0.0
        # Now check the edges of the new u-v-path to see if they overlap in E
        x = v
        while x != u:
            e = frozenset([prev[x], x])
            if e not in doubleArcSet:
                e = (prev[x], x)
            if e in E:
                total += W[(prev[x], x)]
            x = prev[x]
        # Now reset E by reinserting the edges of the u-v-path in C
        for i in range(uPos, vPos):
            e = frozenset([C[i], C[i+1]])
            if e not in doubleArcSet:
                e = (C[i], C[i+1])
            if e not in E:
                E[e] = 1
            else:
                E[e] += 1
    else:
        # Doing the second move type: adding a u-cycle to C.
        P = _getPath(u, v, prev, L)
        P[-1] = u
        if len(P) == 3:
            e = frozenset([P[0], P[1]])
            if e in doubleArcSet:
                total += W[(P[0], P[1])]
        else:
            for i in range(len(P)-1):
                e = frozenset([P[i], P[i+1]])
                if e not in doubleArcSet:
                    e = (P[i], P[i+1])
                if e in E:
                    total += W[(P[i], P[i+1])]
    # Return the new overlap value if we were to make these adjustments
    return total


def _updateGraph(G, W, C, u):
    # First remove the edges of C and store them in C_E. Also store the vertices of C in C_V
    C_E = set()
    C_V = set()
    for i in range(len(C) - 1):
        G[C[i]].discard(C[i + 1])
        C_E.add((C[i], C[i + 1]))
        C_V.add(C[i])
    C_V.add(C[-1])
    # Now also add the dummy vertex uPrime and redirect u's incoming edges to uPrime
    uPrime = len(G)
    G[uPrime] = set()
    for v in range(uPrime):
        if u in G[v]:
            G[v].remove(u)
            G[v].add(uPrime)
            W[(v, uPrime)] = W[(v, u)]
            W.pop((v, u))
    C_V.add(uPrime)
    return C_E, C_V


def _resetGraph(G, W, C_E, u):
    # Redirect uPrime's incoming edges back to u and then remove uPrime
    uPrime = len(G) - 1
    for v in range(uPrime):
        if uPrime in G[v]:
            W[(v, u)] = W[(v, uPrime)]
            W.pop((v, uPrime))
            G[v].remove(uPrime)
            G[v].add(u)
    G.pop(uPrime)
    # Now reinstate the edges in the set C_E back into G
    for e in C_E:
        G[e[0]].add(e[1])


def _getUnvisited(archiveVisited):
    # Returns the first observed index seen to hold a False element
    for i in range(len(archiveVisited)):
        if archiveVisited[i] == False:
            return i
    return None


def _updateArchiveWithMove(archive, archiveCosts, archiveVisited, newCost, C, u, uPos, v, vPos, prev, L, moveType):
    # Assumes the archive set comprises mutually non-dominating cost vectors
    removingSolutions = False
    for i in range(len(archiveCosts)):
        if pareto.dominates(newCost, archiveCosts[i]):
            # Mark element i in the archive for deletion
            archive[i] = None
            archiveCosts[i] = None
            archiveVisited[i] = None
            removingSolutions = True
        elif pareto.worseThan(newCost, archiveCosts[i]):
            # newCost is worse than (or equal to) everything in the set, so end
            return archive, archiveCosts, archiveVisited
    # If we are here, we're returning a modified archive set
    if removingSolutions:
        # First remove any solutions that are now dominated
        tempArchive = []
        tempArchiveCosts = []
        tempArchiveVisited = []
        for i in range(len(archive)):
            if archive[i] != None:
                tempArchive.append(archive[i])
                tempArchiveCosts.append(archiveCosts[i])
                tempArchiveVisited.append(archiveVisited[i])
        archive = tempArchive
        archiveCosts = tempArchiveCosts
        archiveVisited = tempArchiveVisited
    # Now create the new solution C' by applying a move to C and add it to the archive
    CPrime = copy.deepcopy(C)
    if moveType == 1:
        P = _getPath(u, v, prev, L)
        CPrime = _doMove(CPrime, uPos, vPos, P)
    else:
        P = _getPath(u, v, prev, L)
        P[-1] = u
        CPrime = _doMove(CPrime, uPos, uPos, P)
    archive.append(CPrime)
    archiveCosts.append(newCost)
    archiveVisited.append(False)
    return archive, archiveCosts, archiveVisited


def multiObjectiveLocalSearch(G, W, doubleArcSet, k, archive, archiveCosts, LSOption):
    # Generate an initial archive set. These are the mutually non-dominating solutions from solSet
    archiveVisited = [False for i in range(len(archive))]
    while True:
        # Select a solution in the archive
        CPos = _getUnvisited(archiveVisited)
        if CPos == None:
            break
        # Initialise some variables to make evaluations cheap and in a random order
        C = copy.deepcopy(archive[CPos])
        archiveVisited[CPos] = True
        cumulativeW = _getCumulative(C, W)
        overlap_E, overlapDist = _getOverlapSet(C, W, doubleArcSet)
        perm = _getPerm(C)
        for permPos in range(len(perm)):
            # Analyse all neighbours of the solution C and use these to update the archive
            uPos = perm[permPos]
            u = C[uPos]
            # Update the graph G w.r.t. C and u, run the path finding algorithm, then reset the graph
            C_E, C_V = _updateGraph(G, W, C, u)
            if LSOption == 1:
                L, prev = _bfsSet(G, W, u, C_V)
            else:
                L, prev = _rfsSet(G, W, u, C_V)
            _resetGraph(G, W, C_E, u)
            # Go through each vertex v that occurs after u (at uPos) in C and examine the effect of replacing C's u-v-path with the new u-v-path
            for vPos in range(uPos + 1, len(C)):
                v = C[vPos]
                if v in L:
                    # There exists and alternative u-v-path that gives us a new solution S'. Add this to the archive if appropriate
                    newLen = _evaluateLen(cumulativeW, uPos, v, vPos, L)
                    if round(newLen) > 0:
                        newOverlap = _evaluateOverlap(
                            C, W, doubleArcSet, u, uPos, v, vPos, prev, L, overlap_E, overlapDist, 1)
                        newCost = [round(abs(k - newLen)),
                                   round((newOverlap/newLen)*100)]
                        archive, archiveCosts, archiveVisited = _updateArchiveWithMove(
                            archive, archiveCosts, archiveVisited, newCost, C, u, uPos, v, vPos, prev, L, 1)
            # Also examine the effect of splicing the u-uPrime path (i.e cycle) into C (if such a path exists)
            if len(G) in L:
                newLen = cumulativeW[-1] + L[len(G)]
                if round(newLen) > 0:
                    newOverlap = _evaluateOverlap(C, W, doubleArcSet, u, uPos, len(
                        G), None, prev, L, overlap_E, overlapDist, 2)
                    newCost = [round(abs(k - newLen)),
                               round((newOverlap/newLen)*100)]
                    archive, archiveCosts, archiveVisited = _updateArchiveWithMove(
                        archive, archiveCosts, archiveVisited, newCost, C, u, uPos, len(G), None, prev, L, 2)
    # When we are here, all solutions in the archive have been visited (and are at local optima), so end
    return archive, archiveCosts
