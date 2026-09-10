#!/usr/bin/env python3

"""Verify all public-opening 3x4 Classic Dark Hex values."""

import sys
import time
from bisect import bisect_left
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from functools import lru_cache
from pathlib import Path


VALUES = {
    "a1": Fraction(0), "b1": Fraction(0), "c1": Fraction(0),
    "a2": Fraction(5456, 57029), "b2": Fraction(1, 7), "c2": Fraction(0),
    "a3": Fraction(0), "b3": Fraction(1, 7), "c3": Fraction(5456, 57029),
    "a4": Fraction(0), "b4": Fraction(0), "c4": Fraction(0),
}
# Store one representative per 180-degree pair; verify its mate directly.
SOURCES = {
    "a1": "a1", "b1": "b1", "c1": "c1",
    "a2": "a2", "b2": "b2", "c2": "c2",
    "a3": "c2", "b3": "b2", "c3": "a2",
    "a4": "c1", "b4": "b1", "c4": "a1",
}
TARGET = "a2"
OPENING = 3

ROWS = 4
COLUMNS = 3
CELLS = ROWS * COLUMNS
ALL = (1 << CELLS) - 1
OPENING_HISTORY = ((OPENING + 1) << 1) | 1
U64_MAX = (1 << 64) - 1
BLACK = 0
WHITE = 1
TYPE_BITS = 16
TYPE_MASK = (1 << TYPE_BITS) - 1
BLACK_SHIFT = TYPE_BITS
WHITE_SHIFT = BLACK_SHIFT + CELLS
HISTORY_SHIFT = WHITE_SHIFT + CELLS
MAX_POLICY_COUNT = 1 << TYPE_BITS


def bit(cell):
    return 1 << cell


NEIGHBORS = []
for cell in range(CELLS):
    row, column = divmod(cell, COLUMNS)
    adjacent = 0
    for dr, dc in ((-1, 0), (-1, 1), (0, -1), (0, 1),
                   (1, -1), (1, 0)):
        next_row, next_column = row + dr, column + dc
        if 0 <= next_row < ROWS and 0 <= next_column < COLUMNS:
            adjacent |= bit(next_row * COLUMNS + next_column)
    NEIGHBORS.append(adjacent)


def connected(stones, player):
    if player == BLACK:
        first = sum(bit(column) for column in range(COLUMNS))
        last = sum(bit((ROWS - 1) * COLUMNS + column)
                   for column in range(COLUMNS))
    else:
        first = sum(bit(row * COLUMNS) for row in range(ROWS))
        last = sum(bit(row * COLUMNS + COLUMNS - 1)
                   for row in range(ROWS))
    frontier = stones & first
    seen = frontier
    while frontier:
        if frontier & last:
            return True
        expanded = 0
        work = frontier
        while work:
            cell = (work & -work).bit_length() - 1
            work &= work - 1
            expanded |= NEIGHBORS[cell]
        frontier = expanded & stones & ~seen
        seen |= frontier
    return False


WON = tuple(tuple(connected(stones, player)
                  for stones in range(ALL + 1))
            for player in (BLACK, WHITE))


def append_event(history, cell, success):
    if history >> 55:
        raise ValueError("private history exceeds twelve probes")
    return (history << 5) | ((cell + 1) << 1) | int(success)


@lru_cache(maxsize=None)
def knowledge(history):
    own = 0
    unavailable = 0
    while history:
        event = history & 31
        cell = (event >> 1) - 1
        if not 0 <= cell < CELLS or unavailable & bit(cell):
            raise ValueError("invalid private history")
        unavailable |= bit(cell)
        if event & 1:
            own |= bit(cell)
        history >>= 5
    return own, unavailable


@dataclass(frozen=True)
class Policy:
    priority: tuple
    decisions: tuple

    def __post_init__(self):
        if (len(self.priority) != CELLS
                or set(self.priority) != set(range(CELLS))):
            raise ValueError("priority is not a board permutation")
        if self.decisions != tuple(sorted(self.decisions)):
            raise ValueError("decisions are not sorted")
        if len({history for history, _ in self.decisions}) != len(self.decisions):
            raise ValueError("duplicate decision history")
        for history, action in self.decisions:
            _, unavailable = knowledge(history)
            if not 0 <= action < CELLS or unavailable & bit(action):
                raise ValueError("decision selects an unavailable cell")

    def action(self, history):
        _, unavailable = knowledge(history)
        unavailable |= bit(OPENING)
        index = bisect_left(self.decisions, (history, -1))
        if index < len(self.decisions) and self.decisions[index][0] == history:
            selected = self.decisions[index][1]
            if unavailable & bit(selected):
                raise ValueError("policy selects an unavailable cell")
            return selected
        for cell in self.priority:
            if not unavailable & bit(cell):
                return cell
        raise ValueError("policy has no legal probe")


def parse_u64(token, field):
    if not token or not token.isascii() or not token.isdecimal():
        raise ValueError(f"invalid {field}")
    value = int(token)
    if value > U64_MAX:
        raise ValueError(f"invalid {field}")
    return value


def rotate_history(history):
    result = 0
    shift = 0
    while history:
        event = history & 31
        cell = (event >> 1) - 1
        result |= (((CELLS - cell) << 1) | (event & 1)) << shift
        history >>= 5
        shift += 5
    return result


def read_mixture(path, expected_owner):
    source = SOURCES[TARGET]
    source_opening = (int(source[1]) - 1) * COLUMNS + ord(source[0]) - ord("a")
    source_history = ((source_opening + 1) << 1) | 1
    try:
        tokens = iter(path.read_bytes().decode("ascii").split())
    except UnicodeDecodeError as error:
        raise ValueError("mixture is not ASCII") from error

    def take(expected=None):
        try:
            token = next(tokens)
        except StopIteration as error:
            raise ValueError("truncated mixture") from error
        if expected is not None and token != expected:
            raise ValueError(f"expected {expected}, got {token}")
        return token

    take("DARKHEX_PUBLIC_MIXTURE")
    take("BOARD")
    rows = parse_u64(take(), "board rows")
    columns = parse_u64(take(), "board columns")
    if (rows, columns) != (ROWS, COLUMNS):
        raise ValueError("mixture board mismatch")
    take("MODE")
    take("PUBLIC")
    take("OPENING")
    take(source)
    take("OWNER")
    take("BLACK" if expected_owner == BLACK else "WHITE")
    take("POLICIES")
    count = parse_u64(take(), "policy count")
    if not 0 < count <= MAX_POLICY_COUNT:
        raise ValueError("invalid policy count")
    weighted = []
    for _ in range(count):
        take("POLICY")
        weight = parse_u64(take(), "policy weight")
        if not weight:
            raise ValueError("zero policy weight")
        take("PRIORITY")
        priority = tuple(parse_u64(take(), "priority cell")
                         for _ in range(CELLS - 1))
        if source_opening in priority or len(set(priority)) != CELLS - 1:
            raise ValueError("priority is not a non-opening permutation")
        priority += (source_opening,)
        take("DECISIONS")
        decision_count = parse_u64(take(), "decision count")
        if decision_count > 1000000:
            raise ValueError("invalid decision count")
        decisions = tuple(
            (parse_u64(take(), "history"),
             parse_u64(take(), "action"))
            for _ in range(decision_count))
        take("END")
        for history, action in decisions:
            if action == source_opening:
                raise ValueError("policy selects the public opening")
            if expected_owner == BLACK:
                oldest = history
                while oldest >> 5:
                    oldest >>= 5
                if oldest != source_history:
                    raise ValueError("Black history lacks the public opening")
            elif knowledge(history)[1] & bit(source_opening):
                raise ValueError("White history contains the public opening")
        weighted.append((weight, Policy(priority, decisions)))
    take("DONE")
    try:
        trailing = next(tokens)
    except StopIteration:
        trailing = None
    if trailing is not None:
        raise ValueError("trailing mixture data")
    if len({policy for _, policy in weighted}) != len(weighted):
        raise ValueError("duplicate mixture policy")
    if source != TARGET:
        weighted = [(weight, Policy(
            tuple(CELLS - 1 - cell for cell in policy.priority),
            tuple(sorted((rotate_history(history), CELLS - 1 - action)
                         for history, action in policy.decisions))))
                    for weight, policy in weighted]
    return weighted


def pack_world(policy_type, black, white, opponent_history):
    # A world is one opponent policy together with its hidden board state and
    # private history. Packing keeps the belief-state memo compact.
    if not 0 <= policy_type <= TYPE_MASK:
        raise ValueError("policy index does not fit packed belief world")
    return (policy_type | (black << BLACK_SHIFT) | (white << WHITE_SHIFT)
            | (opponent_history << HISTORY_SHIFT))


def unpack_world(world):
    return (world & TYPE_MASK, (world >> BLACK_SHIFT) & ALL,
            (world >> WHITE_SHIFT) & ALL, world >> HISTORY_SHIFT)


class BestResponder:
    def __init__(self, responder, weighted):
        self.me = responder
        self.opponent = WHITE if responder == BLACK else BLACK
        self.weights = tuple(weight for weight, _ in weighted)
        self.policies = tuple(policy for _, policy in weighted)
        self.memo = {}
        self.transition_cache = {}
        self.nodes = 0
        self.priority = tuple(sorted(range(CELLS), key=lambda cell: (
            abs(2 * (cell // COLUMNS) - ROWS + 1)
            + abs(2 * (cell % COLUMNS) - COLUMNS + 1), cell)))
        self.priority = tuple(cell for cell in self.priority
                              if cell != OPENING)

    def advance_opponent(self, world):
        cached = self.transition_cache.get(world)
        if cached is not None:
            return cached
        policy_type, black, white, history = unpack_world(world)
        policy = self.policies[policy_type]
        for _ in range(CELLS):
            cell = policy.action(history)
            cell_bit = bit(cell)
            own = black if self.opponent == BLACK else white
            if (black | white) & cell_bit:
                if own & cell_bit:
                    raise ValueError("opponent policy probes its own stone")
                history = append_event(history, cell, False)
                continue
            if self.opponent == BLACK:
                black |= cell_bit
                own = black
            else:
                white |= cell_bit
                own = white
            history = append_event(history, cell, True)
            if WON[self.opponent][own]:
                result = (True, 0)
            else:
                result = (False, pack_world(policy_type, black, white, history))
            self.transition_cache[world] = result
            return result
        raise ValueError("opponent turn did not terminate")

    def expand(self, action, worlds):
        action_bit = bit(action)
        immediate = 0
        collision = []
        success = []
        for world in worlds:
            policy_type, black, white, opponent_history = unpack_world(world)
            opponent_stones = white if self.me == BLACK else black
            if opponent_stones & action_bit:
                collision.append(world)
                continue
            own = black if self.me == BLACK else white
            if own & action_bit:
                raise ValueError("belief contradicts private history")
            own |= action_bit
            if self.me == BLACK:
                black = own
            else:
                white = own
            if WON[self.me][own]:
                immediate += self.weights[policy_type]
                continue
            terminal, next_world = self.advance_opponent(
                pack_world(policy_type, black, white, opponent_history))
            if not terminal:
                success.append(next_world)
        return immediate, tuple(collision), tuple(success)

    def value(self, own, unavailable, worlds):
        if not worlds:
            return 0
        # The responder's current knowledge and the consistent hidden worlds
        # determine every future payoff. The order of earlier probes has no
        # additional effect once these are fixed.
        key = own, unavailable, worlds
        cached = self.memo.get(key)
        if cached is not None:
            return cached[0]
        self.nodes += 1

        # Probing a cell occupied by the opponent in every consistent world
        # gives a certain collision and no information. Any continuation after
        # that collision can be played immediately, so such a probe is
        # dominated and may be omitted.
        certain_opponent = ALL
        for world in worlds:
            _, black, white, _ = unpack_world(world)
            certain_opponent &= white if self.me == BLACK else black
        legal = ALL & ~unavailable & ~certain_opponent
        total = sum(self.weights[world & TYPE_MASK] for world in worlds)
        finishing = 0
        candidates = ALL & ~own
        while candidates:
            candidate_bit = candidates & -candidates
            candidates &= candidates - 1
            if WON[self.me][own | candidate_bit]:
                finishing |= candidate_bit
        finishing &= legal

        # Failed probes do not end the turn. If every consistent world leaves
        # some connection-completing cell empty, trying finishing cells until
        # one succeeds wins in every world.
        if finishing and all(
                finishing & ~(unpack_world(world)[1] | unpack_world(world)[2])
                for world in worlds):
            action = next(cell for cell in self.priority if finishing & bit(cell))
            immediate, collision, success = self.expand(action, worlds)
            score = immediate
            action_bit = bit(action)
            score += self.value(own, unavailable | action_bit, collision)
            score += self.value(own | action_bit,
                                unavailable | action_bit, success)
            if score != total:
                raise AssertionError("connection shortcut is not a win")
            self.memo[key] = score, action
            return score
        best = -1
        best_action = None
        for action in self.priority:
            if not legal & bit(action):
                continue
            immediate, collision, success = self.expand(action, worlds)
            score = immediate
            action_bit = bit(action)
            score += self.value(own, unavailable | action_bit, collision)
            score += self.value(own | action_bit,
                                unavailable | action_bit, success)
            if score > best:
                best = score
                best_action = action
            if best == total:
                break
        if best_action is None:
            raise ValueError("best response has no legal probe")
        self.memo[key] = best, best_action
        return best

    def extract(self, history, own, unavailable, worlds, decisions):
        if not worlds:
            return
        _, action = self.memo[own, unavailable, worlds]
        previous = decisions.setdefault(history, action)
        if previous != action:
            raise AssertionError("one information set has two actions")
        _, collision, success = self.expand(action, worlds)
        action_bit = bit(action)
        self.extract(append_event(history, action, False), own,
                     unavailable | action_bit, collision, decisions)
        self.extract(append_event(history, action, True), own | action_bit,
                     unavailable | action_bit, success, decisions)

    def solve(self):
        opponent_history = OPENING_HISTORY if self.opponent == BLACK else 0
        initial = tuple(pack_world(
                        policy_type, bit(OPENING), 0, opponent_history)
                        for policy_type in range(len(self.policies)))
        if self.me == WHITE:
            worlds = initial
        else:
            advanced = []
            for world in initial:
                terminal, next_world = self.advance_opponent(world)
                if not terminal:
                    advanced.append(next_world)
            worlds = tuple(advanced)
        root_history = OPENING_HISTORY if self.me == BLACK else 0
        own, unavailable = knowledge(root_history)
        unavailable |= bit(OPENING)
        wins = self.value(own, unavailable, worlds)
        decisions = {}
        self.extract(root_history, own, unavailable, worlds, decisions)
        response = Policy(
            self.priority + (OPENING,), tuple(sorted(decisions.items())))
        return wins, sum(self.weights), response


def simulate(black, white):
    stones = [bit(OPENING), 0]
    histories = [OPENING_HISTORY, 0]
    policies = (black, white)
    player = WHITE
    for _ in range(2 * CELLS + 1):
        cell = policies[player].action(histories[player])
        cell_bit = bit(cell)
        if (stones[BLACK] | stones[WHITE]) & cell_bit:
            if stones[player] & cell_bit:
                raise ValueError("policy probes its own stone")
            histories[player] = append_event(histories[player], cell, False)
            continue
        stones[player] |= cell_bit
        histories[player] = append_event(histories[player], cell, True)
        if WON[player][stones[player]]:
            return player
        player = WHITE if player == BLACK else BLACK
    raise ValueError("game did not terminate")


def verify(path, owner, expected_bound):
    weighted = read_mixture(path, owner)
    responder = WHITE if owner == BLACK else BLACK
    started = time.monotonic()
    engine = BestResponder(responder, weighted)
    wins, total, response = engine.solve()
    replayed = 0
    for weight, policy in weighted:
        black, white = ((policy, response) if owner == BLACK
                        else (response, policy))
        if simulate(black, white) == responder:
            replayed += weight
    if replayed != wins:
        raise AssertionError("best-response replay mismatch")
    bound = 1 - Fraction(wins, total) if owner == BLACK else Fraction(wins, total)
    if bound != expected_bound:
        raise AssertionError(f"unexpected bound: {bound}")
    label = "lower" if owner == BLACK else "upper"
    print(f"{label}_support {len(weighted)}")
    print(f"{label}_integer_total {total}")
    print(f"{label}_best_response_wins {wins}")
    print(f"{label}_best_response_nodes {engine.nodes}")
    print(f"{label} {bound}")
    print(f"{label}_verification_seconds {time.monotonic() - started:.3f}")


def main():
    global TARGET, OPENING, OPENING_HISTORY
    if len(sys.argv) > 2 or (len(sys.argv) == 2
                            and sys.argv[1] not in (*VALUES, "all")):
        raise SystemExit(f"usage: {Path(sys.argv[0]).name} [all|OPENING]")
    targets = list(VALUES) if len(sys.argv) == 1 or sys.argv[1] == "all" else sys.argv[1:]
    here = Path(__file__).resolve().parent
    for TARGET in targets:
        OPENING = (int(TARGET[1]) - 1) * COLUMNS + ord(TARGET[0]) - ord("a")
        OPENING_HISTORY = ((OPENING + 1) << 1) | 1
        expected = VALUES[TARGET]
        source = here / SOURCES[TARGET]
        print(f"opening {TARGET}", flush=True)
        if expected:
            verify(source / "black-lower.mix", BLACK, expected)
        else:
            # Every winning probability is nonnegative; only the upper
            # certificate is needed to prove value zero.
            print("lower 0 (nonnegative winning probability)")
        verify(source / "white-upper.mix", WHITE, expected)
        with localcontext() as context:
            context.prec = 40
            decimal = Decimal(expected.numerator) / Decimal(expected.denominator)
        print(f"true_value_interval {expected} {expected}")
        print(f"true_value_interval_decimal {decimal} {decimal}")
        print(f"public_{TARGET}_3x4_certificate ok", flush=True)
    if len(targets) == CELLS:
        print("all_public_openings_3x4_certificate ok")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
