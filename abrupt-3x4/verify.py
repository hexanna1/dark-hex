#!/usr/bin/env python3

"""Verify exact lower and upper bounds for 3x4 Abrupt Dark Hex."""

import lzma
import sys
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

VALUE = Fraction(
    "1658331822631074831337427943811547900335996648106302498021967217529357706919259542347081527633662102542317699782998092767588866739425551081290810814711079814639576765256474596354793049181984903992720545"
    "/3868913339316971476892276370186945925071293647755822939156449134145896763768272159883526263674247737057268842479851914751928049426237596189792828826475233321814469598464329391194550853624424141390761566")

ROWS, COLUMNS = 4, 3
CELLS = ROWS * COLUMNS
ALL = (1 << CELLS) - 1
BLACK, WHITE = 0, 1
PROBE_ORDER = tuple(sorted(range(CELLS), key=lambda cell: (
    abs(2 * (cell // COLUMNS) - ROWS + 1)
    + abs(2 * (cell % COLUMNS) - COLUMNS + 1), cell)))
ADJACENT = []
for cell in range(CELLS):
    row, column = divmod(cell, COLUMNS)
    neighbors = 0
    for dr, dc in ((-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0)):
        r, c = row + dr, column + dc
        if 0 <= r < ROWS and 0 <= c < COLUMNS:
            neighbors |= 1 << (COLUMNS * r + c)
    ADJACENT.append(neighbors)
START = (sum(1 << c for c in range(COLUMNS)),
         sum(1 << (COLUMNS * r) for r in range(ROWS)))
GOAL = (sum(1 << ((ROWS - 1) * COLUMNS + c) for c in range(COLUMNS)),
        sum(1 << (COLUMNS * r + COLUMNS - 1) for r in range(ROWS)))


def connected(stones, player):
    reached = pending = stones & START[player]
    while pending:
        bit = pending & -pending
        pending ^= bit
        fresh = ADJACENT[bit.bit_length() - 1] & stones & ~reached
        reached |= fresh
        pending |= fresh
    return bool(reached & GOAL[player])


WON = tuple(bytearray(connected(stones, player) for stones in range(ALL + 1))
            for player in (BLACK, WHITE))


class Graph:
    def __init__(self, path):
        lines = lzma.decompress(path.read_bytes()).decode("ascii").splitlines()
        self.owner, root, self.total, count = map(int, lines[0].split())
        profiles = []
        for line in lines[1:]:
            fields = list(map(int, line.split()))
            profiles.append(tuple(tuple(fields[i:i + 4])
                                  for i in range(1, len(fields), 4)))
        assert len(profiles) == count
        self.nodes = []

        def expand(state, own, seen, incoming):
            index = len(self.nodes)
            self.nodes.append(None)
            entries = profiles[state]
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

        expand(root, 0, 0, self.total)
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
        # Every probe ends the opponent's turn, including a collision.
        for cell, _, failed, placed in actions:
            if own & (1 << cell):
                result.append(failed)
            elif not WON[self.graph.owner][self.graph.nodes[placed][0]]:
                result.append(placed)
        return tuple(sorted(result))

    def expand(self, own, cell, worlds):
        wins = 0
        collision, success = [], []
        placed = own | (1 << cell)
        for index in worlds:
            enemy, mass, _ = self.graph.nodes[index]
            if enemy & (1 << cell):
                collision.extend(self.advance(own, index))
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
        # An untried occupied cell remains legal in Abrupt.
        legal = ALL & ~seen
        total = self.mass(worlds)
        best, action = -1, None
        for cell in PROBE_ORDER:
            bit = 1 << cell
            if not legal & bit:
                continue
            wins, collision, success = self.expand(own, cell, worlds)
            success_mass = self.mass(success)
            if wins + self.mass(collision) + success_mass <= best:
                continue
            wins += self.value(own, seen | bit, collision)
            if wins + success_mass <= best:
                continue
            wins += self.value(own | bit, seen | bit, success)
            if wins > best:
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
        previous = self.policy.setdefault(history, cell)
        if previous != cell:
            raise ValueError("inconsistent private-history response")
        _, collision, success = self.expand(own, cell, worlds)
        event = (cell + 1) << 1
        self.extract((history << 5) | event, own, seen | (1 << cell), collision)
        self.extract((history << 5) | event | 1, own | (1 << cell),
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
                if not success or not connected(stones, turn):
                    wins += self.replay(next_black, next_white,
                                        placed if success else failed, history, self.me)
            return wins
        cell = self.policy[history]
        success = not (black | white) & (1 << cell)
        if success:
            if self.me == BLACK:
                black |= 1 << cell
            else:
                white |= 1 << cell
        if success and connected(black if self.me == BLACK else white, self.me):
            return mass
        return self.replay(black, white, index,
                           (history << 5) | ((cell + 1) << 1) | int(success),
                           self.graph.owner)

    def solve(self):
        worlds = self.advance(0, 0) if self.graph.owner == BLACK else (0,)
        wins = self.value(0, 0, worlds)
        self.extract(0, 0, 0, worlds)
        if self.replay(0, 0, 0, 0, BLACK) != wins:
            raise ValueError("response replay mismatch")
        print("replay ok", flush=True)
        return wins


def main():
    here = Path(__file__).resolve().parent
    for owner, filename, label in ((BLACK, "black-lower", "lower"),
                                    (WHITE, "white-upper", "upper")):
        graph = Graph(here / (filename + ".strategy.xz"))
        if graph.owner != owner:
            raise ValueError("certificate owner mismatch")
        print("certificate_owner", "Black" if owner == BLACK else "White", flush=True)
        responder = BestResponder(graph)
        wins = responder.solve()
        bound = Fraction(graph.total - wins if owner == BLACK else wins, graph.total)
        if bound != VALUE:
            raise ValueError("bound differs from expected exact value")
        print(label, bound, flush=True)
        del responder.advance
        del responder, graph
    print("exact_value", VALUE, flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
