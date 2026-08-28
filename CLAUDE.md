# Cultivation World Simulator

A wuxia/xianxia career simulator: a mechanical world kernel whose structured
event logs are the product. The design philosophy is **SIM FIRST, CHEAT
LATER** — no plot armor, no dramaturgy; if raw agent logs already read like
lives, the kernel is right. The full design is in `cultivation_sim_design.txt`
(read it before making non-trivial changes; the code implements Part III, the
"toy version", plus the whole politics layer of Part VI).

## Files

- `cultivation_sim_design.txt` — the design document (source of truth for intent).
- `cultivation_sim.py` — the whole simulation, single file, stdlib only, Python 3.9+.
- No tests or dependencies yet.

## Running it

```bash
python3 cultivation_sim.py                 # interactive: Enter = advance 1 year
python3 cultivation_sim.py --years 200     # batch run + final report
python3 cultivation_sim.py --seed 7        # reproducible world
python3 cultivation_sim.py --intake 32     # smaller recruitment cycles
python3 cultivation_sim.py --follow-pc     # run until the PC peaks, dies or quits
```

Interactive commands: Enter (step a year), `run N`, `pc`, `sheet NAME`,
`log NAME`, `follow` (run on until the PC's story ends), `map` (the nine
lands on their 3x3 grid, with prosperity in words), `courts` (every ruler:
polity, type, this year's style, unrest), `land NAME` (one land's tree:
polities, rulers, edicts, prosperity), `roster`, `famous`, `obits`, `help`,
`quit`. Name and land lookup are case-insensitive substring matches.

## Architecture (all in cultivation_sim.py)

- **Data tables / tuning knobs** at the top: realms, `INSIGHT_REQ`, lifespans,
  intake size/period, feud threshold, trait pool, `TRAIT_ACTION` weights, and
  `NAME_LANDS` — six fictional homelands with male/female given-name and
  surname pools borrowed from real-world languages (Indonesian, Mongolian,
  Finnish, Icelandic; Sanskrit and Persian are rare). Each agent rolls a sex
  and homeland; every intake cohort skews toward one dominant land
  (`DOMINANT_LAND_BOOST`), and `MIXED_NAME_CHANCE` gives a surname from a
  different land. Glacier Coast surnames are patronymic
  (`-sson`/`-sdottir`). Every politics knob lives up here too, in labelled
  blocks: geography and prosperity, polities and rulers, karma and vice,
  rule facets and edicts, thrones, revolts, assassinations, wars, the
  contact surface, and the adventure scene tables.
- **`Agent`** — the uniform agent sheet from the design doc: age, realm, qi,
  talent, insight, burden, resources, standing, traits, relationships
  (`rels: {aid: Rel(kind, intensity)}`), epithets, private `history`, and a
  small `fortune` counter (streaky luck) — plus the politics fields:
  `home` (a real settlement), `karma`, `ruling`/`reign_start`/`reign_came`,
  `past_reigns`, `thrones_refused`, `revolts_survived`, `wars_won/lost`.
- **`World`** — owns agents, sects, sect heads, the chronicle, and the year
  loop. `World.step()` advances exactly one year and returns the chronicle
  lines it produced (this is the API to build on: a UI, an AI-DM renderer,
  or a player layer would call `step()` and read the logs).
- **Year loop** (`step`): action phase (each agent softmax-picks
  cultivate/seclude/adventure/socialize/teach via trait weights + situational
  nudges; a ruler instead gets the single RULE action, and a war can take
  anyone's year) → event phase (every polity's rule year and tribute, then
  campaigns, revolts, assassinations, usurpations, the sect year, petitions,
  a tournament every 4 years, secret-realm expeditions, sect feuds,
  successions) → resolution phase (prosperity drift, stipends, karma luck,
  breakthroughs, aging, old-age death, abdications and voluntary exits) →
  intake recruitment every 8 years.
- **Contests** — one formula (`Agent.power`) with the "tyranny of realms":
  1 realm apart = flee or lose; 2+ = not a fight. Insight is granted by
  ADVERSITY (surviving losses, near-death, grief), never by victory.
- **Trait mutation** (`_mutate`) — Proud crushed in public may become
  Humble/Vengeful/Broken, Loyal betrayed becomes Vengeful, near-death breeds
  Cautious/Ascetic. This is the main tool for making characters legible.

## The politics layer (Part VI, all seven sessions built)

- **Geography** — nine lands on a 3x3 grid; the Middle Plain is the centre
  (no name pool of its own, a melting pot, the four sect seats, the most
  recruits). Two pools supply two lands each, using `SECONDARY_LAND_NAMES`.
  Inside a land is a tree of `Place`s (region → city/town/village), each
  carrying a **prosperity** float shown only as a word
  (`PROSPERITY_WORDS`). Prosperity drifts back toward the land's baseline
  at a rate PROPORTIONAL to the gap and asymmetric — `PROSPERITY_RECOVERY`
  up, `PROSPERITY_SETTLING` down — so a country settles at
  `baseline + (yearly pull / rate)` and its word is a graded reading of
  whoever holds the seat.
- **Polities** (`Polity`) — empires, kingdoms, khanates, jarldoms, cities,
  tribes, and the four sects (which stand outside the vassalage tree). One
  sovereign per land plus vassals who pay tribute and inherit their liege's
  edicts by `MANDATE_CHANCE`. Rulers are ordinary `Agent`s: mortal notables
  generated with a court trait skew, or cultivators who took the seat.
- **Rule style** (`_rule_year`) — no policy AI. Each year a polity scores
  five facets (`RULE_FACET_TRAITS`) off its leader's traits plus situation;
  the top ones fire, moving prosperity, unrest, ruler karma and the
  treasury (`RULE_FACET_EFFECTS`), and write a chronicle line from
  `RULE_LINES`. **Edicts** (`EDICT_TEMPLATES`) are the senseless rules —
  each one grinds prosperity and unrest until the ruler changes.
- **Rulership as an exit** (§4) — `ruling` locks cultivation: the RULE
  action replaces the action phase, qi gain is zero, and the only insight a
  throne earns is `GOVERNANCE_INSIGHT` (a revolt survived, a war lost).
  Paths on: succession claim, invitation, usurpation, revolt championship
  (`reign_came` remembers which, for the obituary). Paths off: death,
  deposition, abdication — a deposed king walks back to the sect with his
  qi exactly where he left it. `_maybe_corrupt` walks a long reign down
  Greedy → Power-Hungry → Cruel.
- **Karma and vice** (§7) — `VICE_TRAITS` / `VIRTUE_TRAITS`; karma is
  seeded from disposition and then moved by DEEDS. Couplings: luck drift
  (`_karma_luck`), the tribulation modifier, the adventure tilt, the vice
  resource bonus, and a grudge multiplier against black ledgers. Virtue is
  the luck lane, vice is the fast lane for wealth.
- **Consequences** (§9) — revolts with champions (a cultivator-king turns a
  rising into a massacre), assassinations, wars along grid edges that move
  territory and vassalage, petitions from starving villages, adventure
  destinations whose risk table follows the destination's prosperity, and
  sect defections under a vice-heavy head. Every resolved rising, massacre,
  war and murdered ruler is filed by `_remember` into `world.upheavals`,
  which only the final report reads.
- **The camera constraint** (§8, the layer's one deliberate cheat) — the PC
  and anyone bound to them as friend/sworn/lover/master/disciple never roll
  or mutate into a vice trait; blocked mutations reroute through
  `CAMERA_REROUTE`. It protects the reader's seat, not the characters.

## The logging model (the important part)

Every consequential event goes through `World.log(text, actors, dramatic=,
world_event=)`. It ALWAYS appends to each actor's private `history` —
nothing is lost, and `log NAME` shows any character's full life. A line is
printed to the shared chronicle only when one of these holds, in priority
order:

1. **`[PC]`** — the main character is an actor.
2. **`[friend]`/`[rival]`/`[enemy]`/`[ally]`/`[master]`/...** — an actor has
   a relationship with the PC (the tag names it).
3. **`[home]`** — the event carries a `place=` that lies in the PC's home
   region or land. This is what keeps one land's politics on screen without
   flooding the chronicle: the reader watches a country because it is
   THEIRS.
4. **`[world]`** — world-scale events (feuds, successions, expeditions,
   intakes, coronations, depositions, wars, risings), passed with
   `world_event=True`.
5. **`[famous]`** — the event is `dramatic=True` AND involves a famous
   character (realm >= `FAME_REALM`, currently Nascent Soul, or standing >= 10):
   breakthroughs of the mighty, violent deaths, maimings, high-realm
   tournament finals.

Everything else stays private to the characters involved. The PC is chosen
at random from the starting intake of 64; if they die, their obituary prints
and the chronicle picks a new young protagonist (`_succeed_pc`). Obituaries
name reigns (and how the seat was come by), risings put down, wars won and
lost, thrones thrown down and thrones refused. The final report opens with
**"The State of the Nine Lands"** (`state_of_the_lands`): every land's
prosperity in words, who holds what and how they rule it, the edicts still
in force, and what each land has not finished talking about.

## Tuning targets (Part III + Part VI §13 — check these after changing rates)

Measured over 200-year runs across 16–32 seeds. Session 7's numbers, which
all of these currently hold at, are in parentheses.

- **Funnel**: per intake of 64 over ~a century: ~35–45 reach realm 2, ~15
  reach realm 3, ~4–6 reach realm 4, 0–2 touch the top. (36.0 / 15.1 / 4.2
  / 0.25.) The knobs are `INSIGHT_REQ` (the first gate is deliberately
  wide), `ADVENTURE_DEATH` / `ADVENTURE_NEAR_DEATH`, and the breakthrough
  chance in `_try_breakthrough`.
- **Talent vs luck**: final realm should correlate with talent, with famous
  exceptions. Monotone = luck too weak; uncorrelated = talent is decoration.
  (Pearson r ≈ 0.32.)
- **Bad lands**: 2–4 of the nine under visibly bad rule at any moment, and
  at least one prosperous-to-golden. Misery is common, not universal.
  (3.4 bad, 1.4 good.) Knobs: `PROSPERITY_RECOVERY` / `PROSPERITY_SETTLING`,
  `RULE_FACET_EFFECTS`, `COURT_TRAIT_WEIGHTS`, `NEGLECT_AGE_SCORE`.
- **Rulership is a real exit, not a common one**: 2–5% of a cohort ends its
  story on a throne. (2.2%; ~4.7% ever rule.) Knobs: the `ABDICATE_*` rates,
  `INVITE_CHANCE` / `INVITE_REFUSE_BASE`, `CLAIM_*`, `REVOLT_REFUSE_BASE`.
- **Cadence**: a revolt or war somewhere every 8–15 years; assassinations
  rarer. (One per 10.5 years; assassinations one per ~100.)
  `REVOLT_CHANCE_PER_UNREST` and `WAR_CHANCE` move as a pair.
- **Karma check**: sort the dead by karma. High karma should show slightly
  better realms and kinder deaths, low karma more wealth and more violent
  ends — and NEITHER monotone, or the karma system has become dramaturgy.
  (Currently U-shaped: both extremes outlive and outearn the middle; saints
  still die young and tyrants still die old and rich.)
- **Chronicle balance**: political lines at most ~30% of the chronicle.
  (20.6%.)
- **Distinguishability**: pick five agents — including one ruler and one
  revolt champion — read `log NAME` for each; every life should be
  describable in one sentence, `log <ruler>` should read like a reign, and
  a recruit from a misruled land should show that land in the life. If
  lives blur, add trait mutation and relationship events, not stats.

The test for any change: does `log <agent>` still read like a life?

## Conventions

- Single file, stdlib only, no third-party deps — keep it that way until the
  toy phase is done.
- All randomness through `world.rng` (a seeded `random.Random`) so `--seed`
  stays reproducible. Never use the module-level `random` functions.
- New events must be routed through `World.log` with honest `dramatic` /
  `world_event` flags — never `print` from simulation code.
- Log text is written for a future AI-DM renderer: past tense, concrete,
  self-contained ("X defeated Y; Y gains grudge"), names via `a.display()`
  so epithets show up.

## Not yet implemented (build order from Part V of the design doc)

- Destiny hooks (per-agent event-bias tags rolled at creation); the rumor /
  witness layer (witness insight exists only crudely in expeditions);
  elder-tempo opportunity injection (dying elders seeking heirs, purges).
- AI DM as renderer over the logs (chronicles, "state of the world" digests).
- World-generation mode (run 200 years, freeze, survivors become the setting).
- The player layer: fully specced as **Part VII** of the design doc
  (sessions P1–P7) — season-resolution play over the year kernel, timeskips
  with an interrupt table, edge×manner stances, round-based autocombat with
  pause points, the demon front, masters/professions/techniques, played
  thrones. Until P1 lands, the PC here is only a *camera*, not a player.

## Known deviations from the spec (deliberate, from tuning)

- **Prosperity drift** is proportional and asymmetric, not §2's flat
  0.2/year. A flat step made the field bang-bang (every country pinned at
  baseline or run to zero) and the map came out starving-or-golden with
  nothing between.
- **`RULE_FACET_EFFECTS["BENEVOLENT"]`** is 0.5, a shade above §5's 0.4, so
  a decent reign can outrun the settling rate far enough to make a land
  visibly prosperous.
- **`COURT_TRAIT_WEIGHTS`** raises exactly the three traits §4 names
  (Power-Hungry, Proud, Righteous). Weighting the other vices up as well
  put a Cruel king on nearly every seat.
- **`ASSASSIN_KARMA = -30`**, not §9's -4: rule facets move karma by ±1–2 a
  year over reigns of decades, so -4 is reached by any ordinary reign.
  Re-derive this if the karma scale changes.
- **Wars never touch a foreign sovereign's vassals** — deliberate, per §9;
  a war is fought between the two crowns that declared it.
