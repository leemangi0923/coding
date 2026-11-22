"""Stacked packs and two-cell footprints."""

from .search import adjacent, distance, solve


def stack_plan(cells, initial, target, *, layers=2, holes=(), ceiling=None,
               heights=None, exchange=False, same_layer=False, unrestricted=False, limit=300_000):
    """Stacks are given bottom to top. Each action moves one exposed pack."""
    if len(cells) != len(initial) or len(initial) != len(target):
        raise ValueError("Stack layouts must match the grid")
    if sorted(sum(initial, ())) != sorted(sum(target, ())):
        raise ValueError("Initial and target packs differ")
    if any(len(stack) > layers for stack in initial + target):
        raise ValueError("A stack exceeds the allowed layer count")
    if any(initial[i] or target[i] for i, cell in enumerate(cells) if cell in holes):
        raise ValueError("A hole cannot hold a pack")

    index = {cell: i for i, cell in enumerate(cells)}
    goal_slots = {pack: (i, level) for i, stack in enumerate(target)
                  for level, pack in enumerate(stack) if pack > 0}

    def destinations(state, source):
        if unrestricted:
            yield from (i for i in range(len(cells)) if i != source)
            return
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            row, col = cells[source]
            while (row + dr, col + dc) in index:
                row, col = row + dr, col + dc
                cell = row, col
                if cell not in holes:
                    yield index[cell]
                    break

    def height(stack):
        return sum(heights[pack] for pack in stack)

    def neighbors(state):
        for i, stack in enumerate(state):
            if not stack or stack[-1] < 0:
                continue
            if ceiling is not None and height(stack[:-1]) >= ceiling:
                continue
            for j in destinations(state, i):
                destination = state[j]
                if (len(destination) < layers and not any(pack < 0 for pack in destination)
                        and (not same_layer or len(destination) + 1 == len(stack))
                        and (ceiling is None or height(destination) < ceiling)):
                    successor = list(state)
                    successor[i], successor[j] = stack[:-1], destination + stack[-1:]
                    yield (stack[-1], (*cells[i], len(stack)), (*cells[j], len(destination) + 1)), tuple(successor)
        if exchange:
            for i, stack in enumerate(state):
                if len(stack) == 2 and (stack[0] > 6) != (stack[1] > 6):
                    successor = list(state)
                    successor[i] = stack[::-1]
                    yield ("exchange", cells[i], *stack), tuple(successor)

    def estimate(state):
        return sum((goal_slots[pack] != (i, level)) * (1 + (level == 0))
                   for i, stack in enumerate(state) for level, pack in enumerate(stack) if pack > 0)

    return solve(initial, lambda state: state == target, neighbors, estimate, limit, 7)


def footprint_plan(cells, initial, target, *, fits, pivot=False, fixed=(), free_footprints=False, limit=350_000):
    """A placement is (layer, first cell, optional second cell). Order encodes the underline."""
    cells = set(cells)
    pack_ids = tuple(initial)
    if set(pack_ids) != set(target):
        raise ValueError("Initial and target packs differ")

    def occupancy(state):
        occupied = {}
        for pack, (layer, *places) in zip(pack_ids, state):
            for cell in places:
                key = layer, cell
                if cell not in cells or key in occupied:
                    raise ValueError("Overlapping footprint or cell outside the board")
                occupied[key] = pack
        return occupied

    start = tuple(initial.values())
    goal = tuple(target[pack] for pack in pack_ids)
    occupancy(start)
    occupancy(goal)

    def candidates(places):
        first = places[0]
        for next_first in adjacent(first):
            dr, dc = next_first[0] - first[0], next_first[1] - first[1]
            yield tuple((r + dr, c + dc) for r, c in places)
        if free_footprints and len(places) == 2:
            dr, dc = places[1][0] - first[0], places[1][1] - first[1]
            for row, col in sorted(cells):
                if (row, col) != first:
                    yield ((row, col), (row + dr, col + dc))
        if pivot and len(places) == 2:
            for endpoint, center in enumerate(places):
                for other in adjacent(center):
                    if (other[0] == center[0]) != (places[1 - endpoint][0] == center[0]):
                        yield (center, other) if endpoint == 0 else (other, center)

    def neighbors(state):
        occupied = occupancy(state)
        for i, (pack, (layer, *places)) in enumerate(zip(pack_ids, state)):
            if pack in fixed or any((layer + 1, cell) in occupied for cell in places):
                continue
            for next_places in candidates(places):
                if any(cell not in cells for cell in next_places):
                    continue
                for next_layer in (1, 2):
                    if any(occupied.get((next_layer, cell), pack) != pack for cell in next_places):
                        continue
                    if not fits(pack, next_layer, next_places, occupied):
                        continue
                    successor = list(state)
                    successor[i] = (next_layer, *next_places)
                    if successor[i] != state[i]:
                        yield (pack, state[i], successor[i]), tuple(successor)

    def estimate(state):
        return sum(max(placement != target[pack], distance(placement[1], target[pack][1]))
                   for pack, placement in zip(pack_ids, state))

    return solve(start, lambda state: state == goal, neighbors, estimate, limit, 7)
