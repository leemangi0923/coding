"""Routing packs among the 2×2 compartments in Chungbuk task 3."""

from .search import adjacent, distance, solve


def bridge_plan(initial, target, initial_gantry=0):
    """The practice layout uses the bottom row of each region as the green route."""
    if len(initial) != 16 or sorted(initial) != sorted(target):
        raise ValueError("B needs four matching 2×2 layouts")
    if initial_gantry not in range(8):
        raise ValueError("Gantry location must be one of the eight green columns")
    coordinates = [(r, region * 2 + c) for region in range(4) for r in range(2) for c in range(2)]
    indices = {cell: i for i, cell in enumerate(coordinates)}
    target_cells = {pack: cell for pack, cell in zip(target, coordinates) if pack}

    def clear(board, first, last, picked):
        lo, hi = sorted((first, last))
        return all(not board[slot] or slot == picked
                   for col in range(lo, hi + 1) for slot in (indices[(1, col)],))

    def neighbors(state):
        board, gantry = state
        for slot, pack in enumerate(board):
            if not pack:
                continue
            cell = coordinates[slot]
            for other in adjacent(cell):
                if other not in indices:
                    continue
                destination = indices[other]
                if board[destination]:
                    continue
                first, last = slot // 4, destination // 4
                next_gantry = gantry
                if first != last:
                    if cell[0] != 1 or not clear(board, gantry, cell[1], slot):
                        continue
                    if not clear(board, cell[1], other[1], slot):
                        continue
                    next_gantry = other[1]
                successor = list(board)
                successor[slot], successor[destination] = 0, pack
                yield (pack, cell, other, (gantry, cell[1], other[1]) if first != last else ()), (
                    tuple(successor), next_gantry
                )

    def estimate(state):
        return sum(distance(cell, target_cells[pack])
                   for cell, pack in zip(coordinates, state[0]) if pack)

    return solve((initial, initial_gantry), lambda state: state[0] == target,
                 neighbors, estimate, limit=500_000, weight=8)
