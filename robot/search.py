"""State search and replay for competition practice. No hardware dependencies."""

from collections import deque
from heapq import heappop, heappush
from itertools import count


class SearchLimit(RuntimeError):
    """The configured search budget expired before reaching the goal."""


def solve(start, goal, neighbors, estimate, limit=500_000, weight=2):
    """Find a feasible path with weighted A*, then replay every step."""
    ticket = count()
    queue = [(weight * estimate(start), next(ticket), 0, start)]
    costs = {start: 0}
    parents = {}
    expanded = 0
    while queue:
        _, _, cost, state = heappop(queue)
        if cost != costs[state]:
            continue
        if goal(state):
            final = state
            path = []
            while state != start:
                state, action = parents[state]
                path.append(action)
            path.reverse()
            if replay(start, path, neighbors) != final:
                raise RuntimeError("Search and replay disagree")
            return path
        if expanded >= limit:
            raise SearchLimit(f"expanded {expanded:,} states")
        expanded += 1
        for action, successor in neighbors(state):
            next_cost = cost + 1
            if next_cost < costs.get(successor, float("inf")):
                costs[successor] = next_cost
                parents[successor] = state, action
                priority = next_cost + weight * estimate(successor)
                heappush(queue, (priority, next(ticket), next_cost, successor))
    raise ValueError("No solution under the selected movement rules")


def replay(state, path, neighbors):
    for index, action in enumerate(path, 1):
        for candidate, successor in neighbors(state):
            if candidate == action:
                state = successor
                break
        else:
            raise ValueError(f"Illegal movement {index}: {action}")
    return state


def adjacent(cell):
    row, col = cell
    return ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1))


def distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def shortest_moves(start, target, neighbors):
    """Shortest distances on the small static movement graph."""
    distances = {target: 0}
    queue = deque([target])
    while queue:
        cell = queue.popleft()
        for other in neighbors[cell]:
            if other not in distances:
                distances[other] = distances[cell] + 1
                queue.append(other)
    return distances.get(start, 999)


def grid(rows, cols, omitted=()):
    missing = set(omitted)
    return tuple((r, c) for r in range(rows) for c in range(cols) if (r, c) not in missing)


def slide(cells, initial, final, *, bridge=False, heights=None, interchangeable=False,
          weight=2, limit=500_000, allowed_edges=None):
    """Flat grids. Positions are zero-based; 0 means empty."""
    if len(cells) != len(initial) or sorted(initial) != sorted(final):
        raise ValueError("The layouts must fill the same grid with the same packs")
    if not interchangeable and len({p for p in initial if p}) != sum(bool(p) for p in initial):
        raise ValueError("Pack IDs must be unique")

    indices = {cell: index for index, cell in enumerate(cells)}
    graph = {
        cell: tuple(other for other in adjacent(cell) if other in indices
                    and (allowed_edges is None or frozenset((cell, other)) in allowed_edges))
        for cell in cells
    }
    targets = {}
    for cell, pack in zip(cells, final):
        if pack:
            targets.setdefault(pack, []).append(cell)
    distances = {
        (source, pack): min(shortest_moves(source, target, graph) for target in destinations)
        for source in cells for pack, destinations in targets.items()
    }

    def neighbors(state):
        for index, (cell, pack) in enumerate(zip(cells, state)):
            if not pack:
                continue
            destinations = [(other, ()) for other in graph[cell] if not state[indices[other]]]
            if bridge:
                for first in graph[cell]:
                    first_pack = state[indices[first]]
                    if not first_pack:
                        continue
                    height = heights[first_pack]
                    seen = {first}
                    queue = deque([(first,)])
                    while queue:
                        path = queue.popleft()
                        for other in graph[path[-1]]:
                            neighbor_pack = state[indices[other]]
                            if not neighbor_pack and len(path) >= 2:
                                destinations.append((other, path))
                            if (other != cell and other not in seen and neighbor_pack
                                    and heights[neighbor_pack] == height):
                                seen.add(other)
                                queue.append(path + (other,))
            for destination, path in destinations:
                successor = list(state)
                successor[index], successor[indices[destination]] = 0, pack
                yield (pack, cell, destination, path), tuple(successor)

    def estimate(state):
        return sum(distances[cell, pack] for cell, pack in zip(cells, state) if pack)

    return solve(tuple(initial), lambda state: state == tuple(final), neighbors, estimate, limit, weight)
