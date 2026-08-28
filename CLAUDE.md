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
python3 cultivation_sim.py --play          # PLAY agent 65, one season at a time
python3 cultivation_sim.py --test-combat   # VII §5's combat harness (exit 1 = FAIL)
```

Play-mode commands: Enter (repeat last season's activity), `1`-`8` or the
activity's name, `menu`, `skip N doing X` (timeskip, cap 12 seasons),
`agenda`, `bag`, `orders` (the standing-orders card; `orders KEY VALUE`
sets one), plus every observer command
(`pc`, `sheet`, `log`, `map`, `courts`, `land`, `roster`, `famous`,
`obits`, `help`, `quit`).

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
- **Year loop** (`step` = `begin_year` + four `run_season`s + `end_year`,
  Part VII §1): PLAN rolls the YEAR AGENDA (`_plan_year`: every event of the
  year, stamped with the season it fires in) → PLAY runs four season
  sub-steps (`run_season`: the NPC action phase in spring — each agent
  softmax-picks cultivate/seclude/adventure/socialize/teach via trait
  weights + situational nudges, a ruler instead gets the single RULE action,
  and a war can take anyone's year — then the agenda items stamped for that
  season, in `AGENDA_ORDER`: rule years and tribute, campaigns and
  declarations, revolts, assassinations, usurpations, the sect year,
  petitions, a tournament every 4 years, expeditions, feuds) → CLOSE
  (`end_year`: prosperity drift, stipends, karma luck, breakthroughs, aging,
  old-age death, abdications and voluntary exits, then intake recruitment
  every 8 years). Batch and observer modes run all three parts in one call
  and print exactly what they printed before.
- **Contests** — one formula (`World.duel_odds`, off `Agent.power`) with the
  "tyranny of realms": 1 realm apart = flee or lose; 2+ = not a fight.
  Between equals the fight is fought IN STANCE (Part VII §4, below).
  Insight is granted by ADVERSITY (surviving losses, near-death, grief),
  never by victory.
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

## The playable layer (Part VII — sessions P1-P3 built)

- **Two clocks** (§1) — the world thinks in years, the player lives in
  seasons. The agenda (`World.agenda`, a list of `AgendaItem`) is what makes
  "stop before something interesting" possible: the engine knows the near
  future because it rolled it. Items that carry their whole decision were
  split out of their old phases — `_plan_declare_war`, `_plan_revolts`,
  `_plan_petition_answer`, `_plan_expedition`, `_feud_pair`,
  `_plan_grudges`; the rest (assassination, usurpation, the sect year, new
  pleas) are stamped to a season and roll their own details there.
- **`--play`** (§2) — `World.begin_play` adds agent 65 to the watched
  intake with everything rolled (no point-buy); the player supplies a name
  and may pick sex and homeland. PC-only state lives on `Agent.play`
  (`PlayerState`); `stances` is filled by P2 and `wound` / `orders` by P3;
  proficiencies, professions, techniques and pills are still placeholders
  for P5-P7. There is deliberately no hp field: hp exists only inside a
  fight.
  The camera constraint (VI §8) is REPEALED for a played PC — vice is
  allowed, karma is the price — while bound companions keep it.
- **Season activities** (§3, `World.player_season`) — cultivate, retreat,
  fight injustice, hunt spirit beasts, trade run, socialize, join the
  muster; all reskins of existing machinery, each paying `SEASON_RATE`
  (a quarter) of the matching yearly action in gains AND in risk, via
  `_fires` / `_share_int`. At `share=1.0` those two helpers roll no dice at
  all, which is why the NPC year is untouched.
- **Timeskip and the interrupt table** (§3) — `skip N doing X`, cap
  `TIMESKIP_CAP`. HARD interrupts split in two: FORESEEN ones sit on the
  agenda (`_foreseen_hard`) and stop the skip on the EVE, the season before;
  the ones nothing can foresee (a close rel dead or maimed, the home seat
  changing hands, home below desperate, a breakthrough ready) are caught at
  the season boundary by `pc_watch` / `pc_alarms`. Waking prints a DIGEST.
- **Deeds, not dice** (§2) — `_record_deed` files every agent's killings,
  cruelties and mercies; `_deed_mutation` turns three of a kind inside
  `DEED_WINDOW` into a trait, and in P1 only the PLAYED character mutates
  off it (NPC mutation stays trigger-driven, and the session-7 aggregates
  with it).
- **Stances: edge x manner** (§4, P2) — a stance is one EDGE
  (`STANCE_EDGES`: sparring / duelling / all-out / murderous — the stop
  line, the accidental kill, the maim chance, the exchange weight and the
  victor's appetite for a yield) plus at most one MANNER (`STANCE_MANNERS`:
  rage, patience, harmonious, showy, humiliating, studying, merciful). The
  two-slot grammar is the combination rule: contradictions cannot be
  written down. `_duel` speaks it — `_pick_stance` reads both fighters off
  their traits and the CONTEXT EDGE the call site passes (a tournament bout
  is not a murder; a feud and a score come due are not sparring), the
  harsher edge is the fight, and every death, maiming, yield, spare and
  execution comes out of the tables instead of a ladder of trait checks.
  Merciful forces kill and maim to zero, Humiliating costs the beaten one
  standing and lands the grudge heavier, Studying pays insight win or lose,
  Showy pays standing on a win, a murderous edge costs standing when it is
  seen. The chronicle prints the vocabulary ("fought in a rage", "waited
  out the storm"). **PROFICIENCY** is rank 0-3 (`stance_rank`): untrained
  halves a bonus and doubles a malus; an NPC is trained up to the edge
  their own character takes them to and in the one manner their nature
  fights in, a played character's ranks live in `PlayerState.stances`
  (`_seed_stances`), and EARNING ranks is P5's. `World.duel_odds` is the
  one-roll win probability, and the invariant the round model below holds
  within 3 percentage points of.
- **Round combat** (§5, P3) — ONE DISTRIBUTION, TWO RESOLUTIONS. Fights
  stay one roll off camera; a fight the PLAYED character is in unfolds into
  exchanges (`_rounds_wanted` -> `_bout`), and `_duel`'s outcome chain is
  the same chain either way, so death and maim rates are identical.
  THE INVARIANT is held by construction, not by tuning: each fighter's blow
  (`_swing_of`) is rolled once, so the bout is a RACE to a known pair of
  whole numbers, and `_exchange_chance` INVERTS that binomial tail to find
  the per-exchange chance whose race lands exactly on `duel_odds`. The
  calibration is computed for two UNWOUNDED fighters stopping at the edge's
  own line and the fight is then run on the real geometry — which is how a
  wound, or a yield line the player moved, costs something without the
  kernel ever hearing about it. The tyranny of realms is untouched: a gap
  returns before a bout is ever built. `player_power` is the ONE place
  VII §5's +4 cap will be enforced (zero for everybody until P5).
- **Pauses, wounds, standing orders** (§5-6, P3) — a bout stops when a
  fighter crosses `PAUSE_OWN[0]` (60%) or THE BRINK (one exchange above the
  line they actually stop at), and again when the one who is AHEAD watches
  the other cross the same marks: yield / fight on / fight to the last /
  switch edge or manner / in a killing fight, escape (`_escape_chance`;
  the Movement term is P7's). ONE prompt per crossing. NPCs cross the same
  lines and answer with their nature (`NPC_PAUSE_LOSING` /
  `NPC_PAUSE_WINNING`, `NPC_YIELD_TRAITS`). hp is gone when the fight is:
  what walks out is a WOUND (`_bout_wounds`) — light under 50%, serious
  under 25%, costing max hp and (serious) half of every season's payout,
  healed one level by a restful season (`heal_wound`, the seam P6's healer
  and healing pill write through). STANDING ORDERS (`ORDERS_DEFAULT`,
  `orders_of` / `set_order`) are to a played character what traits are to an
  NPC: default edge and manner (read by `_pick_stance`), the yield line, the
  execution policy (`_finishes`), the escape policy, and whether crossings
  ask at all. A bout that never has to ask prints as ONE line, like anybody
  else's fight. `World.tell` is the fight camera the UI hangs on the kernel
  — narration only, never the chronicle, and the kernel still never prints.
- **The demon front** (§7, P4) — at worldgen a seeded roll puts the DEMON
  WASTE beyond one outer EDGE of the grid; the 2-3 lands along it are
  MARCH-LANDS (`world.march_lands`, `is_march`), and the front is a fact of
  their geography. `world.demon_threat` is a float 0-10 that BOILS
  (`DEMON_THREAT_DRIFT` a season) and is only ever cooled by people standing
  on the line (`DEMON_THREAT_PER_SEASON`, capped per year by
  `DEMON_RELIEF_CAP`). DEMONS ARE A FIELD, NOT AGENTS: the threat number and
  the scene tables are the whole roster, so the front never reaches `_bout`
  (which wants two agents and a stance each) — a front season (`_act_front`)
  is the expedition's kind of roll against the pot, about twice as lethal as
  the harsh road, paying materials, insight, standing and the front epithets
  (Wastewalker at `FRONT_VETERAN_SEASONS`, Demon-Scarred and the rest off a
  mauling). NPCs volunteer through the war-volunteer machinery
  (`front_volunteer_weight` / `_take_front`, Righteous and Bloodthirsty skew,
  march natives doubled, and `FRONT_RETURN` because a soldier goes back), so
  the front burns NPC lives on the player's own table. At threat >=
  `INCURSION_AT` an INCURSION is rolled onto the agenda (`_plan_incursion`),
  which is what lets a timeskip stop on its eve for march-landers and front
  veterans; `_run_incursion` costs the marches prosperity and conscripts,
  draws defenders like an expedition, and resolves one contest against the
  threat. Won, the pot resets to 2-4 and the dead are named; lost — rarely —
  a settlement is SWALLOWED (`_swallow`: floored, `Place.swallowed`, off the
  map for good) and leaves a scar line in `state_of_the_lands`. March-lands
  under `PETITION_AT` beg through the EXISTING petition machinery
  (`Petition.front`, `FRONT_PETITION_MISSIONS`): the Waste holds no court,
  so answering one makes no enemy and signs nothing.
- **The question hook** — `World.ask_player` is called wherever the kernel
  would otherwise roll FOR the played character: leaving the path, a throne
  claimed or offered, a rising asking for a champion, a plea assigned. With
  no player attached it returns the default and the old roll stands. The UI
  (`Play`, `play_mode`) owns every print and every `input`; nothing the
  player types touches `world.rng`.

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
- **Duel aggregates** (P2's retune target, measured over 32 seeds x 200
  years with a scratch instrument on `_duel`/`_maim`/`kill`): ~777 duels a
  run, ~245 dead in them (~47 across a realm gap, ~186 executed or killed
  by mischance between equals), ~100 beaten foes spared, ~33 maimings.
  The stance rewrite holds all of these within a couple of percent; the
  knobs are `STANCE_EDGES`' kill/maim/execute columns,
  `STANCE_EXECUTE_TRAITS`, `STANCE_MURDEROUS_TRAITS` and
  `STANCE_MURDEROUS_PLAIN`.
- **The combat invariant** (VII §5/§12, P3 — `python3 cultivation_sim.py
  --test-combat`, ~20s, exit 1 on FAIL): the round model's win% within 3
  percentage points of `duel_odds` across the matchup grid (worst cell
  ~1.2pp), even fights 3-8 rounds at every edge (median 3 / 6 / 6 / 7),
  sparring kills nobody, duel accidents under 3% (~2%), maim rates ordered
  sparring < duelling < all-out, and the two resolutions killing and
  crippling at the same rates. The stop lines (`STANCE_EDGES["stop"]`), the
  swing band (`ROUND_SWING`), the pause thresholds (`PAUSE_OWN` /
  `PAUSE_FOE` / `PAUSE_BRINK_GAP`) and `ROUND_PATIENCE_ROUNDS` are all
  tuned against this harness, not guessed. NPC fights stay one roll, so a
  change here must leave every number above untouched — after P3 a batch
  run is still BIT-IDENTICAL to P2's.
- **Front cadence** (VII §12, P4 — measured with a scratch instrument over
  16-32 seeds x 200 years): an incursion every 8-15 years (9.8 / 10.2 on two
  independent seed blocks), settlements swallowed ~3 per 200 years (defeat
  is rare), the front the deadliest lane per season (~2x the harsh road, and
  ~110 NPC deaths a run against a secret realm's ~28), and march-lands
  running 1-2 under their own baseline temper (mean ~1.1, and the spread is
  wide because one land's rule style moves it further than the Waste does).
  Knobs: `FRONT_CHANCE` / `FRONT_CHANCE_PER_THREAT` / `FRONT_RETURN` for the
  volume, `FRONT_DEATH` / `FRONT_MAUL` for the lethality,
  `DEMON_THREAT_DRIFT` and `DEMON_RELIEF_CAP` for the cadence,
  `INCURSION_WALL_BASE` / `INCURSION_THREAT_SCORE` for how often the line
  breaks, and `MARCH_BASELINE` / `MARCH_DRAG_PER_THREAT` for the marches'
  standard of living. NOTE that `_remember` files incursions too, so a
  cadence instrument must separate them from revolts and wars or it will
  read one upheaval per five years and look broken.
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
- The rest of the player layer (**Part VII**, sessions P5-P7): masters and
  proficiencies, which is where stance ranks are earned and where
  `player_power`'s +4 cap starts carrying anything; professions with
  toxicity (`heal_wound` is the healer's and the healing pill's seam);
  techniques (`_movement_rank` is the escape table's); and the played
  throne (P1 offers only hold-or-abdicate). Sessions P1 — two clocks,
  `--play`, the season menu, the timeskip — P2 — stances in the kernel —
  P3 — round combat, wounds, standing orders, `--test-combat` — and P4 —
  the demon front — are built. Named demon lords as real agents stay out of
  scope by decision, not omission (VII's up-front block).

## Known deviations from the spec (deliberate, from tuning)

- **The stop lines and the pause thresholds** (VII §4/§5). §4's 75%/50% stop
  lines are 70%/45%, and §5's 50%/25% pauses are 60% and THE BRINK (one
  exchange above whatever line the fighter stops at). With a 12-20 point
  swing the spec's numbers make a duel end on its own first pause and put
  the second pause inside one exchange of the yield, so neither would ever
  be a choice; §5 asks for 3-8 round fights and pauses that fire, and these
  are what `--test-combat` says delivers both.
- **The demon front's pot** (VII §7 vs §12). §7 says the threat drifts
  +0.15 a year and a cultivator-season on the line buys -0.1; §12 asks for
  an incursion every 8-15 years off a 2-4 reset and a 35% roll at 7. Those
  cannot both be true: at +0.15 a YEAR the climb alone is twenty-six years.
  The drift is therefore read at the layer's own resolution — +0.15 a
  SEASON, the same unit the sink beside it is written in — and
  `DEMON_RELIEF_CAP` bounds a year's total relief, so the cadence is a
  property of the front and not of how many Righteous the last intake
  happened to roll. `MARCH_BASELINE` is not in the spec at all: the marches
  are worth more on paper than any other land and the drag takes it back
  out, because without it they are simply the poorest lands on the map and
  VI §13's count of badly-RULED countries stops meaning anything.
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
