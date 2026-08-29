# Standard 3x4 Dark Hex bounds

Let `v` be Black's win probability under optimal play in standard Classic
Dark Hex. These certificates prove

```text
5642141/26723476 <= v <= 5654469/26723476
0.211130505627336803 <= v <= 0.211591822860169837
```

The previous published bound was `[1/7, 1/4]`, stated by Ryan Hayward, Martin
Müller, and Bedir Tapkan in ["Notes on Dark Hex"](https://www.sfu.ca/~jed/Conferences/CCC2023abstracts.pdf),
page 2. François Bonnet's [2018 analysis](https://doi.org/10.3233/ICG-180057)
gave the earlier bound `[0.112, 0.268]`.

The certificate consists of:

- `black-lower.mix`: a rational mixture of 160 deterministic Black strategies;
- `white-upper.mix`: a rational mixture of 120 deterministic White strategies;
- `verify.py`: the game rules, exact best-response calculation, and replay
  check.

Copy this directory anywhere and run:

```sh
python3 -B verify.py
```

The checker encodes a four-row, three-column board. Black moves first and
connects north--south; White connects west--east. An empty probe places a
stone and ends the turn. Probing an opponent stone reports a collision and
the mover continues. Each strategy depends only on that player's private
probe history.

Against `black-lower.mix`, an unrestricted optimal White response wins
`21081335/26723476` of the mixture's integer mass. Hence Black wins at
least

```text
1 - 21081335/26723476 = 5642141/26723476.
```

Against `white-upper.mix`, an unrestricted optimal Black response wins

```text
11308938/53446952 = 5654469/26723476.
```

The best-response calculation maximizes at every reachable private history.
A probe known to collide in every consistent position is omitted because it
reveals nothing, does not end the turn, and is therefore dominated. Thus these
are bounds on the full minimax game, not on the restricted game used to find
the mixtures.
Randomization cannot improve a response to a fixed mixture beyond its best
deterministic private-history strategy, so checking these best responses also
covers randomized opponents.

## Method and references

The strategies were found with an exact double-oracle search. Starting from a
small restricted game, it solves for mixed strategies, computes each player's
best response in the unrestricted game, adds those responses, and repeats.
Early policy generation also used sequence form, which represents a
perfect-recall strategy by realization weights on action sequences.

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
