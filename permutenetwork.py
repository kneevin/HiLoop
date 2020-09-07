from collections import deque
import networkx as nx
import random

def permutenetwork(graph):
    '''Randomly moves regulations, preserving degree sequence.'''
    repression_count = len([edge for edge in graph.edges if graph.edges[edge]['repress']])
    in_degrees = [graph.in_degree(n) for n in graph.nodes]
    out_degrees = [graph.out_degree(n) for n in graph.nodes]
    while True:
        multigraph = nx.generators.degree_seq.directed_configuration_model(in_degrees, out_degrees)
        flattened = nx.DiGraph(multigraph)
        if len(flattened.edges) != len(graph.edges):
            continue
        for edge in flattened.edges:
            flattened.edges[edge]['repress'] = False
        for edge in random.sample(list(flattened.edges), repression_count):
            flattened.edges[edge]['repress'] = True
        for index, node in enumerate(graph.nodes):
            flattened.nodes[index]['name'] = graph.nodes[node]['name']
        return flattened

def permuteedgeswaps(graph):
    '''Attempts a random number of double edge swaps and directed triangle reversals in place.'''
    for _ in range(int(len(graph.edges) * (1 + 2 * random.random()))):
        edges = list(graph.edges)
        ab, cd = random.sample(edges, 2)
        a, b = ab
        c, d = cd
        if graph.has_edge(a, d) or graph.has_edge(c, b):
            a_pred = list(graph.predecessors(a))
            if len(a_pred) == 0:
                continue
            e = random.choice(a_pred)
            if e != b and graph.has_edge(b, e):
                reversedirectedtriangle(graph, a, b, e)
            continue
        ab_data = graph.edges[ab]
        cd_data = graph.edges[cd]
        graph.remove_edge(a, b)
        graph.remove_edge(c, d)
        graph.add_edge(a, d, **ab_data)
        graph.add_edge(c, b, **cd_data)
    return graph

def reversedirectedtriangle(graph, a, b, c):
    for src, dest in [(a, b), (b, c), (c, a)]:
        if graph.has_edge(dest, src):
            continue
        data = graph.edges[src, dest]
        graph.remove_edge(src, dest)
        graph.add_edge(dest, src, **data)
        
def permuteregulations(graph):
    '''Randomly changes which regulations are repressions, maintaining activation and repression counts and directions.'''
    edges = list(graph.edges)
    copy = graph.copy()
    repressions = 0
    for edge in edges:
        edge_data = copy.edges[edge]
        if edge_data['repress']:
            repressions += 1
            edge_data['repress'] = False
    for new_repression in random.sample(edges, repressions):
        copy.edges[new_repression]['repress'] = True
    return copy

def randomsubgraph(graph, max_nodes):
    queue = deque(maxlen=len(graph.nodes))
    selected = set()
    queue.append(random.sample(graph.nodes, 1)[0])
    while len(selected) < max_nodes and len(queue) > 0:
        head = queue.popleft()
        if head in selected:
            continue
        selected.add(head)
        neighbors = list(graph.successors(head))
        random.shuffle(neighbors)
        for n in neighbors:
            queue.append(n)
    return graph.subgraph(selected)

def neighborhoodsubgraph(graph, start_node, depth):
    current_ring = set([start_node])
    next_ring = set()
    selected = set(current_ring)
    level = 0
    while level < depth:
        for n in current_ring:
            for neighbor in graph.successors(n):
                if neighbor not in selected:
                    selected.add(neighbor)
                    next_ring.add(neighbor)
        current_ring = next_ring
        next_ring = set()
        level += 1
    return graph.subgraph(selected)

def generatepermutations(graph, require_connected, use_full_permutation=True, max_nodes_for_sample=None):
    last_permutation = graph
    checked_permutations = 0
    while True:
        if checked_permutations % 20 == 0 and use_full_permutation:
            last_permutation = permutenetwork(graph)
        else:
            last_permutation = permuteedgeswaps(permuteregulations(last_permutation))
        if require_connected and not nx.algorithms.is_strongly_connected(last_permutation):
            continue
        feasible_subgraph = last_permutation if max_nodes_for_sample is None else randomsubgraph(last_permutation, max_nodes_for_sample)
        checked_permutations += 1
        yield checked_permutations, feasible_subgraph
