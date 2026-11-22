"""Basic-inspection layouts transcribed from the regional task sheets."""

from functools import partial

from .gantry import bridge_plan
from .layers import footprint_plan, stack_plan
from .conveyor import demo
from .search import grid, slide, solve


def layout(cells, rows):
    return tuple(rows[r][c] for r, c in cells)


def places(cells, rows, dominos):
    result = {pack: (1, cell) for cell, pack in zip(cells, layout(cells, rows)) if pack}
    result.update(dominos)
    return result


def stacks(cells, low, high):
    return tuple(tuple(pack for pack in (low[r][c], high[r][c]) if pack) for r, c in cells)


def plan_layout(overrides, region, planner, board, initial, target, **rules):
    """Replace a complete initial/target pair while retaining the region's rules."""
    if overrides and region in overrides:
        supplied = overrides[region]
        if "initial" in supplied:
            initial = read_layout(supplied["initial"], initial)
        if "target" in supplied:
            target = read_layout(supplied["target"], target)
    return planner(board, initial, target, **rules)


def read_layout(data, shape):
    if isinstance(shape, dict):
        if set(data) != {str(pack) for pack in shape}:
            raise ValueError("Footprint IDs must match the example's pack set")
        data = {pack: (data[str(pack)][0], *(tuple(cell) for cell in data[str(pack)][1:]))
                for pack in shape}
    elif shape and isinstance(shape[0], tuple):
        data = tuple(tuple(item) for item in data)
    else:
        data = tuple(data)
    return data


def busan2(layouts=None):
    board = grid(3, 3)
    start = (6, 0, 7, 1, 0, 3, 5, 4, 2)
    goals = {"A": (1, 2, 3, 4, 5, 6, 7, 0, 0), "B": (7, 6, 5, 4, 3, 2, 1, 0, 0),
             "C": (1, 4, 3, 0, 7, 2, 6, 0, 5)}
    shared = tuple(layouts.get("initial", start)) if layouts else start
    c_goal = tuple(layouts.get("C_target", goals["C"])) if layouts else goals["C"]
    goals["C"] = c_goal
    return {name: slide(board, shared, goal, weight=1) for name, goal in goals.items()}


def number_measurements(sizes, ids):
    """Consume measurements in physical scan order. Size is 0, 1, 2, or 3."""
    counts = [0, 0, 0, 0]
    result = []
    for size in sizes:
        if size not in (0, 1, 2, 3):
            raise ValueError("Expected empty, small, medium, or large")
        if not size:
            result.append(0)
            continue
        counts[size] += 1
        count = counts[size]
        if count > 3:
            raise ValueError("More than three objects of one size")
        result.append(ids[size - 1] + count - 1 if count < 3 else -1)
    if any(count < 2 for count in counts[1:]) or result.count(-1) > 1:
        raise ValueError("Expected two regular packs per size and at most one obstacle")
    return tuple(result)


def busan3_plan(square_sizes, round_sizes, initial, target):
    if len(square_sizes) != 9 or len(round_sizes) != 8:
        raise ValueError("Expected A1–A9 and eight IT readings from the exit")
    measured = {
        "IT": number_measurements(round_sizes, (7, 9, 11)),
        "A": number_measurements(square_sizes, (1, 3, 5)),
    }
    if sum(values.count(-1) for values in measured.values()) != 1:
        raise ValueError("Expected one obstacle across A and IT")
    if sorted(initial) != [-1, 0, 0, 0, *range(1, 13)] or sorted(target) != sorted(initial):
        raise ValueError("Expected twelve IDs, one obstacle, and three empty positions")
    if initial.index(-1) != target.index(-1):
        raise ValueError("The C obstacle cannot move")
    obstacle = initial.index(-1)
    board = grid(4, 4, (divmod(obstacle, 4),))
    transfers = {}
    for source, bridge in (("IT", "B-1"), ("A", "B-2")):
        readings = measured[source]
        ids = sorted(pack for pack in readings if pack > 0)
        load = [(pack, readings.index(pack) + 1, i) for i, pack in enumerate(ids, 1)]
        if -1 in readings:
            load.append((-1, readings.index(-1) + 1, 9))
        transfers[bridge] = {
            "load": load,
            "unload": [(pack, slot, initial.index(pack) + 1) for pack, _, slot in load],
        }
    return {
        "measurements": measured,
        "transfer": transfers,
        "C": slide(board, [p for p in initial if p != -1], [p for p in target if p != -1]),
    }


def busan3(layouts=None):
    if layouts:
        return busan3_plan(layouts["square_sizes"], layouts["round_sizes"],
                           layouts["initial"], layouts["target"])
    return busan3_plan(
        (1, 2, 1, 2, 0, 3, 0, 0, 3),
        (2, 1, 0, 2, 1, 1, 3, 3),
        (11, 3, 5, 2, 8, -1, 9, 0, 0, 0, 6, 4, 12, 10, 1, 7),
        (0, 11, 9, 3, 5, -1, 7, 2, 8, 4, 10, 6, 12, 0, 0, 1),
    )


def gwangju2(layouts=None):
    plan = partial(plan_layout, layouts)
    a = grid(3, 4)

    def a_fits(pack, level, cells, occupied):
        if pack in ("H", "V"):
            return level == 2 and all((1, cell) in occupied for cell in cells)
        return level == 1

    a_moves = plan("A", footprint_plan,
        a, places(a, ((3, 5, 0, 8), (0, 6, 2, 0), (4, 1, 0, 7)),
                  {"H": (2, (0, 0), (0, 1)), "V": (2, (1, 1), (2, 1))}),
        places(a, ((1, 2, 3, 4), (5, 6, 7, 8), (0, 0, 0, 0)),
               {"H": (2, (0, 1), (0, 2)), "V": (2, (0, 0), (1, 0))}), fits=a_fits, free_footprints=True,
    )
    b = grid(5, 5, ((0, 0), (0, 4), (4, 0), (4, 4)))
    center = set((r, c) for r in range(1, 4) for c in range(1, 4))

    def b_fits(pack, level, cells, occupied):
        if pack in ("H", "V"):
            return level == 1 and all(cell in center for cell in cells)
        cell = cells[0]
        if cell not in center:
            return level == 1
        return level == 2 and occupied.get((1, cell)) in ("H", "V")

    b_moves = plan("B", footprint_plan,
        b, places(b, ((0, 1, 12, 6, 0), (4, 0, 0, 0, 11), (10, 0, 0, 0, 7),
                      (3, 0, 0, 0, 8), (0, 9, 5, 2, 0)),
                  {"H": (1, (2, 2), (2, 3)), "V": (1, (1, 1), (2, 1))}),
        places(b, ((0, 7, 11, 3, 0), (12, 0, 0, 0, 2), (5, 0, 0, 0, 6),
                   (9, 0, 0, 0, 8), (0, 4, 1, 10, 0)),
               {"H": (1, (1, 2), (1, 3)), "V": (1, (2, 1), (3, 1))}), fits=b_fits,
    )
    c_moves = plan("C", stack_plan,
        grid(2, 3), ((3, 7), (6,), (2,), (4,), (1, 8), (5,)),
        ((3,), (2,), (6, 7), (1, 8), (5,), (4,)), exchange=True, same_layer=True,
    )
    return {"A": a_moves, "B": b_moves, "C": c_moves}


def daegu2(layouts=None):
    plan = partial(plan_layout, layouts)
    small = grid(3, 3)

    def a_fits(pack, level, cells, occupied):
        if pack == 5:
            return level == 2 and all(occupied.get((1, cell)) in (1, 2, 3, 4)
                                      for cell in cells)
        return level == 1

    a_moves = plan("A", footprint_plan,
        small, places(small, ((3, 6, 1), (0, 4, 2), (0, 0, 0)),
                      {5: (2, (1, 2), (0, 2)), -1: (1, (2, 0), (2, 1))}),
        places(small, ((0, 3, 0), (2, 6, 1), (0, 0, 4)),
               {5: (2, (1, 2), (2, 2)), -1: (1, (2, 0), (2, 1))}), fits=a_fits,
        fixed=(-1,), pivot=True,
    )

    def b_fits(pack, level, cells, occupied):
        if pack > 3:
            return level == 1
        if level == 1:
            return True
        first, second = (occupied.get((1, cell)) for cell in cells)
        return first is not None and second is not None and (
            (first > 3 and second > 3) or (first == second and first != pack)
        )

    b_moves = plan("B", footprint_plan,
        small, places(small, ((8, 0, 0), (4, 6, 0), (5, 7, 0)),
                      {1: (1, (2, 2), (1, 2)), 2: (1, (0, 1), (0, 2)),
                       3: (2, (0, 2), (0, 1))}),
        places(small, ((8, 7, 5), (6, 4, 0), (0, 0, 0)),
               {1: (2, (2, 1), (2, 0)), 2: (1, (2, 0), (2, 1)),
                3: (1, (1, 2), (2, 2))}), fits=b_fits, pivot=True,
    )
    large = grid(4, 4)
    c_moves = plan("C", stack_plan,
        large,
        stacks(large, ((0, 0, 3, 8), (17, 0, 11, 5), (0, -1, 12, 7), (13, 16, 14, 6)),
               ((0, 0, 10, 2), (0, 0, 4, 0), (0, -1, 0, 15), (1, 9, 18, 0))),
        stacks(large, ((16, 0, 8, 0), (0, 0, 4, 12), (11, -1, 10, 0), (6, 7, 0, 18)),
               ((5, 0, 13, 0), (0, 0, 3, 1), (2, -1, 14, 0), (9, 15, 0, 17))),
        ceiling=80, heights={p: 40 + 10 * ((p - 1) // 6) for p in range(1, 19)},
    )
    return {"A": a_moves, "B": b_moves, "C": c_moves}


def with_it(moves, shape):
    return [("show_at_IT_exit", shape(move[0]), move) for move in moves]


def chungnam3(layouts=None):
    plan = partial(plan_layout, layouts)
    # Shape groups: 1=red circle, 2=blue square, 3=blue diamond, 4=red triangle.
    a = grid(5, 5, ((0, 2), (2, 0), (2, 2), (2, 4), (4, 2)))
    a_moves = plan("A", slide,
        a, layout(a, ((1, 0, 0, 2, 1), (2, 0, 4, 0, 4), (0, 0, 0, 0, 0),
                      (3, 0, 0, 0, 3), (1, 2, 0, 3, 4))),
        layout(a, ((1, 1, 0, 2, 2), (1, 0, 0, 0, 2), (0, 0, 0, 0, 0),
                   (3, 0, 0, 0, 4), (3, 3, 0, 4, 4))),
        interchangeable=True,
    )
    # Broad blocks cover four half-slots and can straddle a floor slot boundary on top.
    widths = (4, 4, 4, 2, 2, 2, 2)
    names = ("A", "B", "C", 1, 2, 3, 4)
    start = ((1, 0), (1, 4), (2, 4), (2, 2), (1, 8), (1, 10), (2, 8))
    goal = ((1, 4), (1, 0), (2, 2), (1, 8), (1, 10), (2, 8), (1, 12))

    def b_neighbors(state):
        left = {cell: i for i, (level, x) in enumerate(state) if level == 1
                for cell in range(x, x + widths[i])}
        upper = {cell: i for i, (level, x) in enumerate(state) if level == 2
                 for cell in range(x, x + widths[i])}
        for i, (level, x) in enumerate(state):
            if level == 1 and any(cell in upper for cell in range(x, x + widths[i])):
                continue
            for new_level, occupancy in ((1, left), (2, upper)):
                step = 1 if new_level == 2 and widths[i] == 4 else 2
                for new_x in range(0, 15 - widths[i], step):
                    new = new_level, new_x
                    cells = range(new_x, new_x + widths[i])
                    if new == (level, x) or any(occupancy.get(cell, i) != i for cell in cells):
                        continue
                    if new_level == 2 and any(cell not in left or left[cell] == i for cell in cells):
                        continue
                    successor = state[:i] + (new,) + state[i+1:]
                    yield (names[i], (level, x), new), successor

    if layouts and "B" in layouts:
        start = read_layout(layouts["B"].get("initial", start), start)
        goal = read_layout(layouts["B"].get("target", goal), goal)
    b_moves = solve(start, lambda state: state == goal, b_neighbors,
                    lambda state: sum(a != b for a, b in zip(state, goal)), weight=3)
    c = grid(3, 6)
    c_moves = plan("C", stack_plan,
        c, stacks(c, ((1, 0, 8, 11, 6, 0), (0, 2, 0, 0, 13, 0), (15, 0, 0, 3, 4, 0)),
                  ((7, 0, 9, 12, 0, 0), (0, 0, 0, 0, 14, 0), (0, 0, 0, 10, 5, 0))),
        stacks(c, ((1, 2, 3, 4, 5, 6), (7, 8, 0, 0, 0, 0), (9, 0, 0, 0, 0, 0)),
               ((10, 11, 12, 13, 14, 15), (0, 0, 0, 0, 0, 0), (0, 0, 0, 0, 0, 0))),
        holes=((1, 2), (1, 3)), ceiling=100,
        heights=dict.fromkeys(range(1, 16), 60),
    )
    return {
        "A": with_it(a_moves, lambda p: "square" if p in (1, 4) else "round"),
        "B": with_it(b_moves, lambda p: "square" if isinstance(p, str) else "round"),
        "C": with_it(c_moves, lambda p: "square" if p <= 9 else "round"),
    }


def chungbuk3(layouts=None):
    plan = partial(plan_layout, layouts)
    board = grid(1, 4)
    target = ((1, 2), (3, 4), (5, 6), (7, 8))
    initial = ((4, 7, 8), (2, 5), (3,), (1, 6))
    if layouts and "A" in layouts:
        initial = read_layout(layouts["A"].get("initial", initial), initial)
    a_moves = stack_plan(board, initial, target, layers=3, unrestricted=True)
    it = []
    for pack in (2, 4, 6, 8, 1, 3, 5, 7):
        # IT goal is 1 through 8 clockwise starting at 12 o'clock.
        it.append((pack, next(i + 1 for i, column in enumerate(target) if pack in column), pack))
    c = grid(4, 4, ((0, 1), (1, 3), (2, 0), (3, 2)))
    c_moves = plan("C", slide,
        c,
        layout(c, ((5, 0, 7, 1), (4, 10, 8, 0), (0, 0, 6, 3), (0, 2, 0, 9))),
        layout(c, ((1, 0, 2, 3), (4, 5, 6, 0), (0, 7, 8, 9), (10, 0, 0, 0))),
        bridge=True,
        heights={1: 40, 2: 40, 3: 50, 4: 50, 5: 60,
                 6: 40, 7: 40, 8: 50, 9: 50, 10: 60},
    )
    b_initial = (0, 6, 0, 2, 0, 0, 4, 3, 8, 7, 0, 0, 9, 1, 10, 5)
    if layouts and "B" in layouts:
        b_initial = tuple(layouts["B"].get("initial", b_initial))
    b_moves = bridge_plan(b_initial, (1, 2, 9, 10, 3, 4, 0, 0, 5, 6, 0, 0, 7, 8, 0, 0))
    return {"A": a_moves, "IT": it, "B": b_moves, "C": c_moves}


EXAMPLES = {
    "common1": demo, "busan2": busan2, "busan3": busan3, "gwangju2": gwangju2,
    "daegu2": daegu2, "chungnam3": chungnam3, "chungbuk3": chungbuk3,
}
