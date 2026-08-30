# Exact Dark Hex values

## Classic 3x4

Let `v` be Black's win probability under optimal play in standard Classic
Dark Hex. These certificates prove

```text
v = 14279/67484
  = 0.211590895619702447987671151680
```

The previous published bound was `[1/7, 1/4]`, stated by Ryan Hayward, Martin
Müller, and Bedir Tapkan in ["Notes on Dark Hex"](https://www.sfu.ca/~jed/Conferences/CCC2023abstracts.pdf),
page 2. François Bonnet's [2018 analysis](https://doi.org/10.3233/ICG-180057)
gave the earlier bound `[0.112, 0.268]`.

The certificate consists of:

- `classic/black-lower.mix`: a rational mixture of 92 deterministic Black
  strategies;
- `classic/white-upper.mix`: a rational mixture of 112 deterministic White
  strategies;
- `classic/verify.py`: the game rules, exact best-response calculation, and
  replay check.

Copy this directory anywhere and run:

```sh
python3 -B classic/verify.py
```

The checker encodes a four-row, three-column board. Black moves first and
connects north--south; White connects west--east. An empty probe places a
stone and ends the turn. Probing an opponent stone reports a collision and
the mover continues. Each strategy depends only on that player's private
probe history.

## First-probe probabilities

For the particular optimal strategies in these certificates, the first-probe
probabilities are:

Black:

| | a | b | c |
| ---: | ---: | ---: | ---: |
| **1** | `1633/67484` (2.419833%) | `1310/16871` (7.764804%) | 0 |
| **2** | `9555/67484` (14.158912%) | `3602/16871` (21.350246%) | `1453/33742` (4.306206%) |
| **3** | `1453/33742` (4.306206%) | `3602/16871` (21.350246%) | `9555/67484` (14.158912%) |
| **4** | 0 | `1310/16871` (7.764804%) | `1633/67484` (2.419833%) |

White:

| | a | b | c |
| ---: | ---: | ---: | ---: |
| **1** | 0 | `30/16871` (0.177820%) | `14023/33742` (41.559481%) |
| **2** | 0 | `109/16871` (0.646079%) | `1285/16871` (7.616620%) |
| **3** | `1285/16871` (7.616620%) | `109/16871` (0.646079%) | 0 |
| **4** | `14023/33742` (41.559481%) | `30/16871` (0.177820%) | 0 |

Black's first probe always places a stone. White's table gives the first
attempted probe, which can collide with Black's hidden stone.

Against `classic/black-lower.mix`, an unrestricted optimal White response wins
`106410/134968` of the mixture's integer mass. Hence Black wins at
least

```text
1 - 106410/134968 = 28558/134968 = 14279/67484
```

Against `classic/white-upper.mix`, an unrestricted optimal Black response wins

```text
1827712/8637952 = 14279/67484
```

The lower and upper certificates coincide, so this is the exact minimax
value.

The best-response calculation maximizes at every reachable private history.
A probe known to collide in every consistent position is omitted because it
reveals nothing, does not end the turn, and is therefore dominated. Thus these
are bounds on the full minimax game, not on the restricted game used to find
the mixtures.
Randomization cannot improve a response to a fixed mixture beyond its best
deterministic private-history strategy, so checking these best responses also
covers randomized opponents.

## Abrupt 3x3

In Abrupt Dark Hex every probe ends the turn, including a collision. An empty
probe places a stone. Probing an opponent stone places nothing and privately
reports a collision to the mover; the opponent observes neither the attempted
cell nor the outcome.

The certificates in `abrupt/` prove that Black's optimal win probability is

```text
207579464761/299876201866
= 0.692217199862218825825789679238
```

Run the standalone exact checker with:

```sh
python3 -B abrupt/verify.py
```

`abrupt/black-lower.mix` is a rational mixture of 234 deterministic Black
strategies. Against it, an unrestricted optimal White response wins integer
mass `553780422630/1799257211196`, proving the matching lower bound for Black.

`abrupt/white-upper.mix` is a rational mixture of 244 deterministic White
strategies. Against it, an unrestricted optimal Black response wins integer
mass `415158929522/599752403732`, proving the matching upper bound.

The checker encodes the rules, parses the complete strategies, computes an
unrestricted exact best response at every reachable private history, and
independently replays the extracted response against every strategy in the
mixture. A randomized response cannot exceed the best deterministic response
to a fixed mixture, so the two matching bounds prove the minimax value.

## Method and references

Both results were found with coupled double-oracle searches. Each pass solved
a restricted matrix game, computed unrestricted best responses, and added new
responses together with their 180-degree rotations. Exact rational
reconstruction on the optimal faces produced the certificate mixtures; the
standalone unrestricted checkers supply the proofs.

Abrupt 3x3 has larger degenerate response faces, so each best-response
calculation retained every maximizing action and cheaply extracted many tied
deterministic responses. Perturbed equilibrium mixtures and separate lower-
and upper-bound closure were used before exact support reduction.

The relevant general methods are:

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
