#!/usr/bin/env python3

"""Verify every public opening of Classic 4x4 Dark Hex using exact integers."""

import lzma
import sys
from fractions import Fraction
from functools import lru_cache
from pathlib import Path


CELLS = 16
ALL = (1 << CELLS) - 1
BLACK = 0
WHITE = 1
PROBE_ORDER = (5, 6, 9, 10, 1, 2, 4, 7, 8, 11, 13, 14, 0, 3, 12, 15)
VALUES = tuple(map(Fraction, (
    "39200463131587349474018821953682501886288090675/109271866634581876366005467237558775842245124437",
    "1246266071734072815448447585357/3192617014544364958846653854284",
    "1/2",
    "205948805123/278226535047",
    "13349694926648706453175314826171758852232677435633/28973542266583825852988542841638070814335704203607",
    "3171798626214542646/6823179292865617463",
    "900674/1545475",
    "9265879471/23743551290",
)))


def cell_name(cell):
    return chr(ord("a") + cell % 4) + str(cell // 4 + 1)


def connection_tables():
    adjacent = []
    for cell in range(CELLS):
        row, column = divmod(cell, 4)
        neighbors = 0
        for dr, dc in ((-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0)):
            r, c = row + dr, column + dc
            if 0 <= r < 4 and 0 <= c < 4:
                neighbors |= 1 << (4 * r + c)
        adjacent.append(neighbors)
    tables = []
    for start, goal in ((0x000f, 0xf000), (0x1111, 0x8888)):
        won = bytearray(ALL + 1)
        for stones in range(ALL + 1):
            reached = pending = stones & start
            while pending:
                bit = pending & -pending
                pending ^= bit
                fresh = adjacent[bit.bit_length() - 1] & stones & ~reached
                reached |= fresh
                pending |= fresh
            won[stones] = bool(reached & goal)
        tables.append(won)
    return tables


WON = connection_tables()


def read_controller(payload):
    """Read varints, packed cell lists, backward references and integer weights."""
    position = 0

    def byte():
        nonlocal position
        value = payload[position]
        position += 1
        return value

    def small():
        value = shift = 0
        while True:
            part = byte()
            value |= (part & 127) << shift
            if part < 128:
                return value
            shift += 7

    def big():
        nonlocal position
        size = small()
        value = int.from_bytes(payload[position:position + size], "little")
        position += size
        return value

    header = [small() for _ in range(6)] + [big(), small()]
    weights = [big() for _ in range(small())]
    profiles = []
    for state in range(header[7]):
        tag = byte()
        if tag == 0:
            profiles.append(("Z", ()))
        elif tag >= 64:
            size = tag - 64
            cells = []
            for _ in range((size + 1) // 2):
                pair = byte()
                cells.extend((pair & 15, pair >> 4))
            cells = cells[:size]
            cells.extend(cell for cell in range(CELLS) if cell not in cells)
            profiles.append(("W", tuple(cells)))
        else:
            edges = []
            for _ in range(tag - 1):
                flags = byte()
                same, prior = bool(flags & 64), bool(flags & 128)
                failed = (0 if flags & 16 else state - 1 if same and prior
                          else state - small())
                placed = (0 if flags & 32 else failed if same
                          else state - 1 if prior else state - small())
                weight = weights[small()] if tag > 2 else 1
                edges.append((flags & 15, failed, placed, weight))
            profiles.append(("B", tuple(edges)))
    return header, profiles


class Graph:
    def __init__(self, path, opening):
        header, profiles = read_controller(lzma.decompress(path.read_bytes()))
        _, _, _, source, self.owner, root, self.total, _ = header
        self.opening = opening
        rotate = source != opening
        self.nodes = []
        initial_own = (1 << opening) if self.owner == BLACK else 0

        @lru_cache(maxsize=None)
        def feasible(own, seen):
            opposed = seen & ~own
            attempts = own.bit_count() + (self.owner == WHITE)
            need = attempts - opposed.bit_count()
            if (need < 0 or WON[self.owner][own] or WON[1 - self.owner][opposed]
                    or seen == ALL):
                return False
            free = ALL & ~seen
            extra = free
            while True:
                if extra.bit_count() == need and not WON[1 - self.owner][opposed | extra]:
                    return True
                if extra == 0:
                    return False
                extra = (extra - 1) & free

        def expand(state, own, seen, incoming):
            index = len(self.nodes)
            self.nodes.append(None)
            kind, data = profiles[state]
            entries = ()
            if state and feasible(own, seen):
                if kind == "W":
                    order = tuple(15 - cell if rotate else cell for cell in data)
                    legal = tuple(cell for cell in order if not seen & (1 << cell))
                    cell = next((cell for cell in legal
                                 if WON[self.owner][own | (1 << cell)]), legal[0])
                    entries = ((cell, state, state, 1),)
                else:
                    entries = tuple((15 - cell if rotate else cell, failed, placed, weight)
                                    for cell, failed, placed, weight in data)
            denominator = sum(edge[3] for edge in entries)
            actions = []
            if entries:
                used = seen
                for cell, failure, success, weight in entries:
                    bit = 1 << cell
                    if used & bit or weight <= 0:
                        raise ValueError("illegal strategy action")
                    used |= bit
                    mass, remainder = divmod(incoming * weight, denominator)
                    if remainder:
                        raise ValueError("nonintegral action mass")
                    failed = expand(failure, own, seen | bit, mass)
                    placed = expand(success, own | bit, seen | bit, mass)
                    actions.append((cell, mass, failed, placed))
            self.nodes[index] = (own, incoming, tuple(actions))
            return index

        expand(root, initial_own, 1 << opening, self.total)
        del expand


class BestResponder:
    def __init__(self, graph):
        self.graph = graph
        self.me = 1 - graph.owner
        self.memo = {}
        self.policy = {}
        self.advance = lru_cache(maxsize=1 << 18)(self._advance)

    def mass(self, worlds):
        return sum(self.graph.nodes[index][1] for index in worlds)

    def _advance(self, own, index):
        actions = self.graph.nodes[index][2]
        if not actions:
            raise ValueError("missing reachable decision")
        result = []
        for cell, _, failed, placed in actions:
            if own & (1 << cell):
                result.extend(self.advance(own, failed))
            elif not WON[self.graph.owner][self.graph.nodes[placed][0]]:
                result.append(placed)
        return tuple(sorted(result))

    def expand(self, own, cell, worlds):
        wins = 0
        collision = []
        success = []
        placed = own | (1 << cell)
        for index in worlds:
            enemy, mass, _ = self.graph.nodes[index]
            if enemy & (1 << cell):
                collision.append(index)
            elif WON[self.me][placed]:
                wins += mass
            else:
                success.extend(self.advance(placed, index))
        return wins, tuple(sorted(collision)), tuple(sorted(success))

    def value(self, own, seen, worlds):
        if not worlds:
            return 0
        key = (own, seen, worlds)
        cached = self.memo.get(key)
        if cached is not None:
            return cached[0]
        # A certainly occupied cell reveals nothing and consumes no turn.
        certain = ALL
        for index in worlds:
            certain &= self.graph.nodes[index][0]
        legal = ALL & ~seen & ~certain
        # A connection-completing probe wins on success; collision leaves
        # every other option available without losing a turn.
        for cell in PROBE_ORDER:
            if legal & (1 << cell) and WON[self.me][own | (1 << cell)]:
                legal = 1 << cell
                break
        total = self.mass(worlds)
        best = 0
        action = None
        for cell in PROBE_ORDER:
            bit = 1 << cell
            if not legal & bit:
                continue
            wins, collision, success = self.expand(own, cell, worlds)
            success_mass = self.mass(success)
            if action is not None and wins + self.mass(collision) + success_mass <= best:
                continue
            wins += self.value(own, seen | bit, collision)
            if action is not None and wins + success_mass <= best:
                continue
            wins += self.value(own | bit, seen | bit, success)
            if action is None or wins > best:
                best, action = wins, cell
            if best == total:
                break
        if action is None or best > total:
            raise ValueError("invalid response value")
        self.memo[key] = (best, action)
        return best

    def extract(self, history, own, seen, worlds):
        if not worlds:
            return
        _, cell = self.memo[(own, seen, worlds)]
        self.policy[history] = cell
        _, collision, success = self.expand(own, cell, worlds)
        event = (cell + 1) << 1
        self.extract((history << 6) | event, own, seen | (1 << cell), collision)
        self.extract((history << 6) | event | 1, own | (1 << cell),
                     seen | (1 << cell), success)

    def replay(self, black, white, index, history, turn):
        _, mass, actions = self.graph.nodes[index]
        if turn == self.graph.owner:
            if not actions:
                raise ValueError("missing replay decision")
            wins = 0
            for cell, _, failed, placed in actions:
                success = not (black | white) & (1 << cell)
                next_black, next_white = black, white
                if success:
                    if turn == BLACK:
                        next_black |= 1 << cell
                    else:
                        next_white |= 1 << cell
                stones = next_black if turn == BLACK else next_white
                if not success or not WON[turn][stones]:
                    wins += self.replay(next_black, next_white, placed if success else failed,
                                        history, self.me if success else turn)
            return wins
        cell = self.policy[history]
        success = not (black | white) & (1 << cell)
        if success:
            if self.me == BLACK:
                black |= 1 << cell
            else:
                white |= 1 << cell
        if success and WON[self.me][black if self.me == BLACK else white]:
            return mass
        return self.replay(black, white, index,
                           (history << 6) | ((cell + 1) << 1) | int(success),
                           self.graph.owner if success else self.me)

    def solve(self):
        opening = 1 << self.graph.opening
        own = opening if self.me == BLACK else 0
        # White moves after the announced Black opening.
        worlds = self.advance(own, 0) if self.graph.owner == WHITE else (0,)
        wins = self.value(own, opening, worlds)
        self.extract(0, own, opening, worlds)
        if self.replay(opening, 0, 0, 0, WHITE) != wins:
            raise ValueError("response replay mismatch")
        print("replay ok", flush=True)
        return wins


def verify(opening):
    representative = min(opening, 15 - opening)
    directory = Path(__file__).resolve().parent / cell_name(representative)
    expected = VALUES[representative]
    print("opening", cell_name(opening), flush=True)
    for owner, filename, label in ((BLACK, "black-lower", "lower"),
                                    (WHITE, "white-upper", "upper")):
        graph = Graph(directory / (filename + ".strategy.xz"), opening)
        if graph.owner != owner:
            raise ValueError("certificate owner mismatch")
        print("certificate_owner", "Black" if owner == BLACK else "White", flush=True)
        responder = BestResponder(graph)
        wins = responder.solve()
        bound = Fraction(graph.total - wins if owner == BLACK else wins, graph.total)
        print(label, bound, flush=True)
        if bound != expected:
            raise ValueError("bound differs from expected exact value")
        del responder.advance
        del responder, graph
    print("exact_value", expected, flush=True)


def main():
    names = {cell_name(cell): cell for cell in range(CELLS)}
    if len(sys.argv) > 2 or len(sys.argv) == 2 and sys.argv[1] not in names:
        raise ValueError("usage: verify.py [OPENING]")
    openings = [names[sys.argv[1]]] if len(sys.argv) == 2 else range(CELLS)
    for opening in openings:
        verify(opening)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
