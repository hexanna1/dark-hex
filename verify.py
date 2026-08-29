#!/usr/bin/env python3

"""Verify exact lower and upper bounds for standard 3x4 Classic Dark Hex."""

import sys
import time
from bisect import bisect_left
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from functools import lru_cache
from pathlib import Path


ROWS = 4
COLUMNS = 3
CELLS = ROWS * COLUMNS
ALL = (1 << CELLS) - 1
U64_MAX = (1 << 64) - 1
BLACK = 0
WHITE = 1
TYPE_BITS = 8
TYPE_MASK = (1 << TYPE_BITS) - 1
BLACK_SHIFT = TYPE_BITS
WHITE_SHIFT = BLACK_SHIFT + CELLS
HISTORY_SHIFT = WHITE_SHIFT + CELLS
MAX_POLICY_COUNT = 1 << TYPE_BITS
CERTIFICATES = (
    ("black-lower.mix", BLACK, Fraction(5642141, 26723476)),
    ("white-upper.mix", WHITE, Fraction(5654469, 26723476)),
)


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


def rotate_history(history):
    result = 0
    shift = 0
    while history:
        event = history & 31
        cell = (event >> 1) - 1
        if not 0 <= cell < CELLS:
            raise ValueError("invalid private history")
        result |= (((CELLS - cell) << 1) | (event & 1)) << shift
        shift += 5
        history >>= 5
    return result


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

    def rotated(self):
        return Policy(
            tuple(CELLS - 1 - cell for cell in self.priority),
            tuple(sorted((rotate_history(history), CELLS - 1 - action)
                         for history, action in self.decisions)))


def parse_u64(token, field):
    if not token or not token.isascii() or not token.isdecimal():
        raise ValueError(f"invalid {field}")
    value = int(token)
    if value > U64_MAX:
        raise ValueError(f"invalid {field}")
    return value


def read_mixture(path, expected_owner):
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

    take("DARKHEX_MIXTURE")
    if parse_u64(take(), "format version") != 1:
        raise ValueError("unsupported mixture version")
    take("ROWS")
    rows = parse_u64(take(), "board rows")
    take("COLUMNS")
    columns = parse_u64(take(), "board columns")
    if (rows, columns) != (ROWS, COLUMNS):
        raise ValueError("mixture board mismatch")
    take("MODE")
    take("STANDARD")
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
                         for _ in range(CELLS))
        take("DECISIONS")
        decision_count = parse_u64(take(), "decision count")
        if decision_count > 1000000:
            raise ValueError("invalid decision count")
        decisions = tuple(
            (parse_u64(take(), "history"),
             parse_u64(take(), "action"))
            for _ in range(decision_count))
        take("END")
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
    by_policy = {policy: weight for weight, policy in weighted}
    for weight, policy in weighted:
        if by_policy.get(policy.rotated()) != weight:
            raise ValueError("mixture is not rotation invariant")
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

    def value(self, history, worlds):
        if not worlds:
            return 0
        own, unavailable = knowledge(history)
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
            score += self.value(append_event(history, action, False), collision)
            score += self.value(append_event(history, action, True), success)
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
            score += self.value(append_event(history, action, False), collision)
            score += self.value(append_event(history, action, True), success)
            if score > best:
                best = score
                best_action = action
            if best == total:
                break
        if best_action is None:
            raise ValueError("best response has no legal probe")
        self.memo[key] = best, best_action
        return best

    def extract(self, history, worlds, decisions):
        if not worlds:
            return
        own, unavailable = knowledge(history)
        _, action = self.memo[own, unavailable, worlds]
        previous = decisions.setdefault(history, action)
        if previous != action:
            raise AssertionError("one information set has two actions")
        _, collision, success = self.expand(action, worlds)
        self.extract(append_event(history, action, False), collision, decisions)
        self.extract(append_event(history, action, True), success, decisions)

    def solve(self):
        initial = tuple(pack_world(policy_type, 0, 0, 0)
                        for policy_type in range(len(self.policies)))
        if self.me == BLACK:
            worlds = initial
        else:
            advanced = []
            for world in initial:
                terminal, next_world = self.advance_opponent(world)
                if not terminal:
                    advanced.append(next_world)
            worlds = tuple(advanced)
        wins = self.value(0, worlds)
        decisions = {}
        self.extract(0, worlds, decisions)
        response = Policy(self.priority, tuple(sorted(decisions.items())))
        return wins, sum(self.weights), response


def simulate(black, white):
    stones = [0, 0]
    histories = [0, 0]
    policies = (black, white)
    player = BLACK
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
    here = Path(__file__).resolve().parent
    for name, owner, expected_bound in CERTIFICATES:
        verify(here / name, owner, expected_bound)
    lower = CERTIFICATES[0][2]
    upper = CERTIFICATES[1][2]
    with localcontext() as context:
        context.prec = 30
        lower_decimal = Decimal(lower.numerator) / Decimal(lower.denominator)
        upper_decimal = Decimal(upper.numerator) / Decimal(upper.denominator)
    print(f"true_value_interval {lower} {upper}")
    print(f"true_value_interval_decimal {lower_decimal} {upper_decimal}")
    print("standard_3x4_certificate ok")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
