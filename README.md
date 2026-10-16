# Exact Dark Hex values

This repository gives exact values for Classic 4x4 and 3x4, every public
opening of Classic 3x4, and Abrupt 3x3. Each value is Black's probability of
winning under optimal play.

| Variant | Board | Exact Black value | Certificate |
| --- | --- | --- | --- |
| Classic | 4 columns × 4 rows | `5345119702052171/6736824633547900` ≈ 79.3418% | [classic-4x4/](classic-4x4/) |
| Classic | 3 columns × 4 rows | `14279/67484` ≈ 21.1591% | [classic-3x4/](classic-3x4/) |
| Classic, public opening | 3 columns × 4 rows | [Every opening solved](#classic-3x4-public-openings) | [classic-3x4-public/](classic-3x4-public/) |
| Abrupt | 3 columns × 3 rows | `207579464761/299876201866` ≈ 69.2217% | [abrupt-3x3/](abrupt-3x3/) |

The certificates specify strategies with exact rational probabilities. Their
checkers compute exact best responses over all legal opponent strategies;
matching lower and upper bounds establish each value.

## Verify

Run the following commands from the repository root.

### Classic 4x4 checker

Expand the certificates using Python's standard library:

```sh
python3 - <<'PY'
import lzma
from pathlib import Path
for path in Path('classic-4x4').glob('*.strategy.xz'):
    path.with_suffix('').write_bytes(lzma.decompress(path.read_bytes()))
PY
```

Build and run the C++ checker using GCC or Clang. The checker requires
128-bit integer support:

```sh
c++ -O3 -std=c++20 classic-4x4/verify.cpp -o classic-4x4/verify4x4
classic-4x4/verify4x4 classic-4x4/black-lower.strategy \
    classic-4x4/white-upper.strategy
```

The checker prints `exact_value` when the bounds match exactly.

### Classic 3x4 and Abrupt 3x3

Python's standard library suffices:

```sh
python3 -B classic-3x4/verify.py
python3 -B classic-3x4-public/verify.py
python3 -B abrupt-3x3/verify.py
```

Each directory contains its own checker and strategy files and can be copied
elsewhere. The public-opening command checks all twelve cells. To check a
single opening, use, for example:

```sh
python3 -B classic-3x4-public/verify.py a2
```

`black-lower.mix` supplies Black's strategy and `white-upper.mix` supplies
White's. Public-opening files are grouped by cell; zero-valued cases need
only a White strategy.

## Rules

Black connects top to bottom; White connects left to right. Black moves
first. Players see their own probe histories, including private collisions,
and retain perfect recall. There is no swap rule.

An empty probe places a stone. In **Classic** Dark Hex, a collision leaves the
same player to probe again; only a successful placement ends the turn.
In **Abrupt** Dark Hex, every probe ends the turn, including a collision.
Probe locations and collision reports are private. In Classic, the turn
passing tells the opponent that a stone was placed; in Abrupt it does not.

In the **public-opening** variant, Black must place the specified opening,
its location is announced, and White moves next.

## Classic 4x4

The exact value is

```text
5345119702052171/6736824633547900 = 0.793418263470100503868159979448...
```

Black's opening is private. The certificates give the probability of each
next probe at each private history, as explained
[below](#shared-continuation-certificates).

### First-probe probabilities

These are the supplied strategies' first-probe probabilities, rounded to four
decimal places as percentages. A zero is exact. Columns are a–d from left to
right; rows are 1–4 from top to bottom. Exact probabilities are the root
profile’s action weights divided by their sum, after applying the root
reference’s cell orientation.

**Black**

| | a | b | c | d |
| ---: | ---: | ---: | ---: | ---: |
| **1** | 0 | 0 | 2.6221% | 39.8581% |
| **2** | 0.1509% | 0 | 0 | 7.3689% |
| **3** | 7.3689% | 0 | 0 | 0.1509% |
| **4** | 39.8581% | 2.6221% | 0 | 0 |

**White**

| | a | b | c | d |
| ---: | ---: | ---: | ---: | ---: |
| **1** | 1.1072% | 4.8888% | 5.5797% | 15.2623% |
| **2** | 0 | 7.9268% | 15.0590% | 0.1762% |
| **3** | 0.1762% | 15.0590% | 7.9268% | 0 |
| **4** | 15.2623% | 5.5797% | 4.8888% | 1.1072% |

Black's first probe always places a stone. White's table gives the first
attempted probe, which can collide with Black's hidden stone.

## Classic 3x4

The exact value is

```text
14279/67484 = 0.211590895619702447987671151680...
```

The certificate uses 80 Black policies and 74 White policies.
The previous published bound was `[1/7, 1/4]`, stated by Ryan Hayward, Martin
Müller, and Bedir Tapkan in ["Notes on Dark Hex"](https://www.sfu.ca/~jed/Conferences/CCC2023abstracts.pdf),
page 2. François Bonnet's [2018 analysis](https://doi.org/10.3233/ICG-180057)
gave the earlier bound `[0.112, 0.268]`.

### First-probe probabilities

These are the exact first-probe probabilities of the supplied optimal
strategies.

**Black**

| | a | b | c |
| ---: | ---: | ---: | ---: |
| **1** | `1633/67484` | `1310/16871` | 0 |
| **2** | `9555/67484` | `3602/16871` | `1453/33742` |
| **3** | `1453/33742` | `3602/16871` | `9555/67484` |
| **4** | 0 | `1310/16871` | `1633/67484` |

**White**

| | a | b | c |
| ---: | ---: | ---: | ---: |
| **1** | 0 | `30/16871` | `14023/33742` |
| **2** | 0 | `109/16871` | `1285/16871` |
| **3** | `1285/16871` | `109/16871` | 0 |
| **4** | `14023/33742` | `30/16871` | 0 |

Black's first probe always places a stone. White's table gives the first
attempted probe, which can collide with Black's hidden stone.

## Classic 3x4: public openings

Each cell below gives Black's exact value for that announced opening.
Columns are a–c from left to right; rows are 1–4 from top to bottom.

| | a | b | c |
| ---: | ---: | ---: | ---: |
| **1** | 0 | 0 | 0 |
| **2** | `5456/57029` | `1/7` | 0 |
| **3** | 0 | `1/7` | `5456/57029` |
| **4** | 0 | 0 | 0 |

Here `5456/57029` ≈ 9.5671% and `1/7` ≈ 14.2857%.
If Black may choose its opening but must announce it before White moves,
the value is **1/7**, attained by b2 or b3. White can condition its strategy
on the announcement, so randomizing the opening cannot improve that value.

The stored a2 certificates use 78 Black policies and 68 White policies;
b2 uses 12 and 7. For each zero-valued representative (a1, b1, c1 and c2), a
single deterministic White policy suffices. Black's unrestricted best
response never wins, and nonnegativity supplies the matching lower bound.

The files cover six representative openings. A 180-degree rotation gives
strategies for the other six. The checker transforms each complete policy
and directly verifies its bound at the rotated opening, searching all legal
responses there as well.

## Abrupt 3x3

The exact value is

```text
207579464761/299876201866 = 0.692217199862218825825789679238...
```

The certificate uses 206 Black policies and 214 White policies.

## Why the certificates prove the values

### Policy mixtures

A `.mix` file specifies a rational distribution over complete deterministic
private-history policies. Select one policy once, with probability equal to
its integer weight divided by the total, and retain it throughout the game.

For a Black mixture, the checker maximizes the total weight of policies
White can defeat with one responding strategy. Dividing by the mixture's
total weight gives White's maximum winning probability; its complement is
Black's lower guarantee. For a White mixture, Black's maximum winning
probability gives the upper guarantee:

| Case | Black lower guarantee | Black upper guarantee |
| --- | --- | --- |
| Classic 3x4 | `1 − 53205/67484 = 14279/67484` | `14279/67484` |
| Classic, public a2 | `1 − 51573/57029 = 5456/57029` | `5456/57029` |
| Classic, public b2 | `1 − 6/7 = 1/7` | `1/7` |
| Classic, other public representatives | `0` by nonnegativity | `0/1 = 0` |
| Abrupt | `1 − 92296737105/299876201866` | `207579464761/299876201866` |

Both Abrupt fractions equal `207579464761/299876201866`.

The mixture checkers use exact integer arithmetic to find a best response.
In Classic, a probe certain to collide is omitted: its outcome is already
known, it reveals nothing and it consumes no turn. Each checker extracts a
maximizing policy and separately replays it against every mixture component.

### Shared-continuation certificates

The 4x4 files describe behavioral strategies: at each private probe history,
choose the next probe with the listed exact probabilities. With perfect
recall, this has the same expressive power as a mixture of complete policies.

Identical future strategies share a continuation profile, including those
that differ only by a 180-degree rotation. Each profile lists probes, positive
integer weights and continuation references for collision and success. Its
action probabilities are the weights divided by their sum.

The checker expands these references at each actual private history using
exact 128-bit masses. Each observation history inherits its action's full
mass. Sharing continuations changes only storage; the best-response search
still distinguishes complete private histories and enforces probe legality.

A response state records the responder's stones and probed cells, together
with the compatible opponent histories and their masses. For each possible
probe, the checker separates success from collision and follows the
opponent's hidden choices until the next response turn. It adds immediate
winning mass to the optimal values of the two observation branches; an
opponent connection contributes zero. Taking the maximum over probes gives
the response value. Every probe extends a private history, so induction on
the remaining probes establishes the result.

The checker may omit a certainly occupied probe. It may also try a probe that
completes a connection first: a collision costs no turn and leaves the other
options available.

The Black certificate limits White to `1391704931495729/6736824633547900`.
The White certificate limits Black to `5345119702052171/6736824633547900`.
Taking the complement of the first bound gives the second, proving the value.
The checker separately replays the maximizing response on actual boards,
checking that it attains the computed bound.

### Arbitrary opponents

A randomized response is a distribution over deterministic private-history
policies in this finite perfect-recall game. Its expected payoff cannot
exceed the best deterministic response. The bounds therefore cover arbitrary
randomized opponents. Thus the matching guarantees prove the exact values.

## Method and references

The nonzero certificates were found using double-oracle searches: optimizing
over finite sets of candidate strategies and expanding those sets with
unrestricted best responses. For public a2 and Classic 4x4, sequence-form
optimization also allowed choices from different policies to be combined at
individual private histories. Rational reconstruction supplied the exact
integer weights for verification.

Background on these methods:

- Bernhard von Stengel, ["Efficient Computation of Behavior
  Strategies"](https://doi.org/10.1006/game.1996.0050), 1996;
- Daphne Koller, Nimrod Megiddo, and Bernhard von Stengel,
  ["Efficient Computation of Equilibria for Extensive Two-Person
  Games"](https://ai.stanford.edu/~koller/Papers/Koller%2Bal%3AGEB96.pdf),
  1996;
- H. Brendan McMahan, Geoffrey J. Gordon, and Avrim Blum,
  ["Planning in the Presence of Cost Functions Controlled by an
  Adversary"](https://www.cs.cmu.edu/~ggordon/mcmahan-ggordon-blum.icml2003.pdf),
  2003.

Related Dark Hex work includes Bedir Tapkan's
[*Dark Hex: A Large Scale Imperfect Information
Game*](https://webdocs.cs.ualberta.ca/~hayward/theses/bedir.pdf), 2022, and the
Hayward--Müller--Tapkan abstract cited above.
