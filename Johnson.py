from collections import defaultdict
from collections import OrderedDict
import copy


def _strongly_connected_components(G):
    # Returns a list of lists containing the vertices belonging to each SCC in G. The vertices in
    # each SCC are sorted in reverse numerical order before returning
    index_counter = [0]
    stack = []
    lowlink = {}
    index = {}
    result = []

    def strong_connect(u):
        index[u] = index_counter[0]
        lowlink[u] = index_counter[0]
        index_counter[0] += 1
        stack.append(u)
        successors = G[u]
        for v in successors:
            if v not in index:
                strong_connect(v)
                lowlink[u] = min(lowlink[u], lowlink[v])
            elif v in stack:
                lowlink[u] = min(lowlink[u], index[v])

        if lowlink[u] == index[u]:
            connected_component = []
            while True:
                v = stack.pop()
                connected_component.append(v)
                if v == u:
                    break
            result.append(connected_component[:])
    for u in G:
        if u not in index:
            strong_connect(u)
    for i in range(len(result)):
        result[i].sort(reverse=True)
    return result


def _remove_node(G, v):
    # Remove vertex v from the graph G. (
    del G[v]
    for nbrs in G.values():
        nbrs.discard(v)


def _subgraph(G, vertices):
    # Get the subgraph of G induced by the set "vertices".
    H = {v: G[v] & vertices for v in vertices}
    return H


def _unblock(u, blocked, B):
    stack = set([u])
    while stack:
        v = stack.pop()
        if v in blocked:
            blocked.remove(v)
            stack.update(B[v])
            B[v].clear()


def Johnson(myGraph: OrderedDict(), source=-1):
    assert source == 0 or source == -1
    # This is an adapted, dependency-free version of NetworkX's implementation of Johnson's algorithm.
    # If source == -1, the algorithm returns a list S of every cycle in myGraph exactly once.
    # If source == 0, the algorithm returns a list of all s=0-cycles in myGraph exactly once.
    # myGraph must be stored as ordered dictionary where each element is a set of neighbours
    # of the corresponding vertex/key.
    G = copy.deepcopy(myGraph)
    sccs = _strongly_connected_components(G)
    if source == 0:
        # Change sccs so that it only contains one element (that is, he single scc containing vertex 0)
        for scc in sccs:
            if 0 in scc:
                sccs = [scc]
                break
    # Do Johnson's algorithm on every scc in sccs
    while len(sccs) > 0:
        scc = sccs.pop()
        s = scc.pop()
        path = [s]
        if source == 0 and s != source:
            # We have found all the cycles starting at 0, so end
            break
        blocked = set()
        closed = set()
        blocked.add(s)
        B = defaultdict(set)
        stack = [(s, list(G[s]))]
        while len(stack) > 0:
            u, nbrs = stack[-1]
            if len(nbrs) > 0:
                v = nbrs.pop()
                if v == s:
                    # Yield a copy of this path path/cycle
                    P = path.copy()
                    P.append(P[0])
                    yield (P)
                    closed.update(path)
                elif v not in blocked:
                    path.append(v)
                    stack.append((v, list(G[v])))
                    closed.discard(v)
                    blocked.add(v)
                    continue
            if len(nbrs) == 0:
                if u in closed:
                    _unblock(u, blocked, B)
                else:
                    for nbr in G[u]:
                        if u not in B[nbr]:
                            B[nbr].add(u)
                stack.pop()
                path.pop()
        _remove_node(G, s)
        H = _subgraph(G, set(scc))
        sccs.extend(_strongly_connected_components(H))
