# Exact Dark Hex values

This repository gives exact values for Classic 4x4 and 3x4, every public
opening of both boards, and Abrupt 3x4 and 3x3. Each value is Black's
probability of winning under optimal play.

| Variant | Board | Exact Black value | Certificate |
| --- | --- | --- | --- |
| Classic | 4 columns × 4 rows | `5345119702052171/6736824633547900` ≈ 79.3418% | [classic-4x4/](classic-4x4/) |
| Classic, public opening | 4 columns × 4 rows | [Every opening solved](#classic-4x4-public-openings) | [classic-4x4-public/](classic-4x4-public/) |
| Classic | 3 columns × 4 rows | `14279/67484` ≈ 21.1591% | [classic-3x4/](classic-3x4/) |
| Classic, public opening | 3 columns × 4 rows | [Every opening solved](#classic-3x4-public-openings) | [classic-3x4-public/](classic-3x4-public/) |
| Abrupt | 3 columns × 4 rows | [Exact value](#abrupt-3x4) ≈ 42.8630% | [abrupt-3x4/](abrupt-3x4/) |
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

### Other variants

Python's standard library suffices:

```sh
python3 -B classic-4x4-public/verify.py
python3 -B classic-3x4/verify.py
python3 -B classic-3x4-public/verify.py
python3 -B abrupt-3x4/verify.py
python3 -B abrupt-3x3/verify.py
```

Each directory contains its own checker and strategy files and can be copied
elsewhere. The public-opening commands check every cell. To check a single
opening, append its cell name, for example:

```sh
python3 -B classic-3x4-public/verify.py a2
```

Certificates are named `black-lower` for Black and `white-upper` for White.
Public-opening files are grouped by cell; zero-valued cases need only a
White strategy.

## Rules

Black connects top to bottom; White connects left to right. Black moves
first. Players see their own probe histories, including private collisions,
and retain perfect recall. A player may not probe the same cell twice.
There is no swap rule.

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
right; rows are 1–4 from top to bottom.

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

## Classic 4x4: public openings

Each cell below gives Black's value for that announced opening, rounded to
four decimal places as a percentage. Columns are a–d from left to right;
rows are 1–4 from top to bottom.

| | a | b | c | d |
| ---: | ---: | ---: | ---: | ---: |
| **1** | 35.8743% | 39.0359% | 50.0000% | 74.0220% |
| **2** | 46.0755% | 46.4856% | 58.2781% | 39.0248% |
| **3** | 39.0248% | 58.2781% | 46.4856% | 46.0755% |
| **4** | 74.0220% | 50.0000% | 39.0359% | 35.8743% |

The exact values are:

| Openings | Exact Black value |
| --- | --- |
| a1, d4 | `39200463131587349474018821953682501886288090675/109271866634581876366005467237558775842245124437` |
| b1, c4 | `1246266071734072815448447585357/3192617014544364958846653854284` |
| c1, b4 | `1/2` |
| d1, a4 | `205948805123/278226535047` |
| a2, d3 | `13349694926648706453175314826171758852232677435633/28973542266583825852988542841638070814335704203607` |
| b2, c3 | `3171798626214542646/6823179292865617463` |
| c2, b3 | `900674/1545475` |
| d2, a3 | `9265879471/23743551290` |

If Black may choose its opening but must announce it before White moves,
the value is **205948805123/278226535047**, attained by d1 or a4. White can
condition its strategy on the announcement, so randomizing the opening
cannot improve that value.

The files cover eight representative openings. A 180-degree rotation gives
strategies for the other eight.

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
strategies for the other six.

## Abrupt 3x4

The exact value is

```text
1658331822631074831337427943811547900335996648106302498021967217529357706919259542347081527633662102542317699782998092767588866739425551081290810814711079814639576765256474596354793049181984903992720545/3868913339316971476892276370186945925071293647755822939156449134145896763768272159883526263674247737057268842479851914751928049426237596189792828826475233321814469598464329391194550853624424141390761566 = 0.428629870247711792524300308845...
```

The certificates give the probability of each next probe at each private
history, as explained [below](#shared-continuation-certificates).

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
probability gives the upper guarantee.

The mixture checkers use exact integer arithmetic to find a best response.
Each checker separately replays its maximizing policy against every mixture
component to confirm the computed bound.

### Shared-continuation certificates

The 4x4 and Abrupt 3x4 files describe behavioral strategies: at each private
probe history, choose the next probe with the listed exact probabilities.
Histories with the same future strategy share a continuation. With perfect
recall, these strategies are equivalent to mixtures of complete policies.

The checkers compute exact best responses while preserving complete private
histories and applying each variant's collision rule. They separately replay
the maximizing responses on actual boards. Black's strategy supplies a lower
guarantee and White's supplies an upper guarantee.

### Arbitrary opponents

A randomized response is a distribution over deterministic private-history
policies in this finite perfect-recall game. Its expected payoff cannot
exceed the best deterministic response. The bounds therefore cover arbitrary
randomized opponents. Thus the matching guarantees prove the exact values.

## Method and references

The nonzero certificates were found using double-oracle searches: optimizing
over finite sets of candidate strategies and expanding those sets with
unrestricted best responses. Sequence-form optimization also refined choices
at individual private histories. Rational reconstruction supplied exact
probabilities for verification.

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
