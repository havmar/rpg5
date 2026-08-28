# Cultivation World Simulator

A wuxia/xianxia career simulator: a mechanical world kernel whose structured
event logs are the product. The design philosophy is **SIM FIRST, CHEAT
LATER** — no plot armor, no dramaturgy; if raw agent logs already read like
lives, the kernel is right. The full design is in `cultivation_sim_design.txt`
(read it before making non-trivial changes; the code implements Part III, the
"toy version", plus the whole politics layer of Part VI and the whole
playable layer of Part VII — sessions P1-P7, all built).

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
python3 cultivation_sim.py --autopilot --years 200   # VII §12's random-hand bot
```

Play-mode commands: Enter (repeat last season's activity), `1`-`16` or the
activity's name, `menu`, `skip N doing X` (timeskip, cap 12 seasons),
`agenda`, `bag` (crafts, manuals, pills, toxicity, the rack, techniques,
proficiencies, the combat total against the +4 cap), `brew KIND` (what the
furnace is set up for), `take KIND` (swallow a pill), `sell KIND|gear`,
`orders` (the standing-orders card; `orders KEY VALUE` sets one), and on a
throne `hold` / `abdicate` — plus every observer command
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
  (`rels: {aid: Rel(kind, intensity)}`), epithets, private `history`, a
  small `fortune` counter (streaky luck) and VII §9's `techniques` /
  `tech_power` (cards are on the AGENT, because the famous carry them too)
  — plus the politics fields:
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

## The playable layer (Part VII — all seven sessions built)

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
  (`PlayerState`): `stances` (P2), `wound` / `orders` (P3),
  `proficiencies` / `drills` (P5), `professions` / `manuals` / `pills` /
  `brew` / `gear` / `toxicity` / `clarity` (P6) and `flaw` (P7's hidden
  burden). The technique CARDS are not there — they are on the `Agent`,
  because famous NPCs carry them too. There is deliberately no hp field: hp
  exists only inside a fight.
  The camera constraint (VI §8) is REPEALED for a played PC — vice is
  allowed, karma is the price — while bound companions keep it.
- **Season activities** (§3, `World.player_season`) — cultivate, retreat,
  train the body / a weapon / theory, the sect training hall, seek a
  master, the furnace / the forge / the infirmary (P6), fight injustice,
  hunt spirit beasts, trade run, socialize, join the muster, the demon
  front — sixteen in `PLAYER_ACTIVITIES`; each paying `SEASON_RATE`
  (a quarter) of the matching yearly action in gains AND in risk, via
  `_fires` / `_share_int`. At `share=1.0` those two helpers roll no dice at
  all, which is why the NPC year is untouched.
- **Timeskip and the interrupt table** (§3) — `skip N doing X`, cap
  `TIMESKIP_CAP`. HARD interrupts split in two: FORESEEN ones sit on the
  agenda (`_foreseen_hard`) and stop the skip on the EVE, the season before;
  the ones nothing can foresee (a close rel dead or maimed, the home seat
  changing hands, home below desperate, a breakthrough ready, and P7's
  crown taken or lost) are caught at the season boundary by `pc_watch` /
  `pc_alarms`. Waking prints a DIGEST.
- **Deeds, not dice** (§2) — `_record_deed` files every agent's killings,
  cruelties and mercies; `_deed_mutation` turns three of a kind inside
  `DEED_WINDOW` into a trait, and only the PLAYED character mutates off it
  (NPC mutation stays trigger-driven, and the session-7 aggregates with
  it). It is what turns a profiteer Cruel by his own ledger.
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
  VII §5's +4 cap is enforced: it sums `player_power_terms` (P5's Weapon
  proficiency; P6's gear and P7's techniques append there and nowhere else)
  and clips the total at `PLAYER_POWER_CAP`. `fight_power` is
  `power() + player_power()` and is read by every contest a character
  fights with their own hands — `_stance_power`, `_act_front`, `_act_hunt`
  — and deliberately NOT by the group contests (war, incursion,
  expedition), which are army arithmetic.
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
- **Training, masters and the hall** (§8, P5) — ONE RANK MECHANIC with
  several skins: `RANK_SHAPES` is the shape (max rank, seasons rank N
  costs), a dict on `PlayerState` is the store, and `World.track_rank` is
  the only place a rank is computed. `proficiencies` holds Body / Weapon /
  Theory in SEASONS (rank 0-5, rank N costs N seasons); `drills` holds
  seasons per stance (rank 0-3, 2 seasons a rank) while `stances` stays the
  authoritative rank, because a rank can be GIVEN as well as ground out.
  Effects are deliberately small: Body is `PROFICIENCY_BODY_HP` a rank of
  body plus `PROFICIENCY_BODY_RESIST` of a wound coming off one level
  lighter (`_wound_resisted`, read by both wound doors); Weapon is
  `PROFICIENCY_WEAPON_POWER` a rank inside the +4 cap; Theory is a
  percentage point a rank on the tribulation plus an insight trickle. Stance
  ranks are earned three ways — `_drill_stance` (a weapon season, aimed by
  `_drill_target`, which reads the standing orders and rolls no dice),
  `_fight_drill` (a stance carried through a real fight, called from
  `_duel`), and teaching (`_grant_stance` / `_teach_stance`, and
  `_hall_stance`). A master (`master_of`, bound with `_bind` like any other
  rel, so grief, grudges, the `[master]` tag and the timeskip's witness
  alarm all work unchanged) multiplies training seasons by
  `MASTER_TEACHING` and hands over the stances THEY fight in. The trial
  (`_master_trial`) is a reading of the record — karma in the master's own
  direction, insight, epithets, standing, talent — plus one bout at
  Sparring against a peer, never against the master: a realm gap would make
  a trial a flight. `_duel` now RETURNS whoever was left standing, which is
  how the trial knows. The hall (`_act_hall`) gates on `HALL_STANDING` and
  `HALL_COST` and teaches forms; `_hall_manual` (P6) and `_hall_technique`
  (P7) are the other two shelves in the same library season.
- **Professions** (§8, P6) — ONE RANK MECHANIC, THREE SKINS: `PROFESSIONS`
  (alchemy / forging / healing) is one more row in `RANK_SHAPES`
  (`{"max": 3, "step": 3.0}` — eighteen seasons for the whole ladder) and
  one more store on `PlayerState`. §8's WALL is `profession_taught`: past
  `PROFESSION_TEACHER_RANK` the seasons still bank but the rank stops
  rising until a teacher (a master) or a manual (`_hall_manual`, off the
  sect's own shelves) turns up — a wall, not a hole in the floor, so the
  day the book arrives the hands already know it. A craft season also
  cultivates at `PROFESSION_QI_SHARE` and carries `CRAFT_ACCIDENT` (a
  furnace, a billet, a fever taken off a patient; `CRAFT_ACCIDENT_DEATH`
  fatal, `CRAFT_ACCIDENT_SERIOUS` leaving burden) — without it three
  activities on the menu carried no risk at all and the autopilot came out
  ahead of the cohort simply by having safe places to spend a season.
  ALCHEMY brews qi / healing / clarity pills on a STANDING recipe
  (`set_brew` — deliberately not a question a season, or a timeskip would
  stop four times a year to ask); `take_pill` spends a pill where it is
  swallowed, because nothing in the layer carries a pending effect between
  seasons except `play.clarity` (one tribulation) and P7's `play.flaw`.
  TOXICITY is the bill: every pill is a point, and past
  `PILL_TOXICITY_FREE` every further pill is a point of permanent BURDEN
  (`PILL_DECAY` shed per pill-free year) — Part I §3's promise made
  mechanical, and the thing the pill wall measures. FORGING makes gear at
  +1/+2 power (through `player_power_terms`, under the one cap) and
  `sell_item` sells the worst piece off an uncapped rack; a sale melts into
  the buyer's `resources` without deducting their silver, a small
  deliberate faucet. HEALING closes your own wounds through `heal_wound`
  and other people's for karma, gratitude, a fee — and at `LIFEDEBT_RANK`,
  when the patient WOULD have died, a LIFE-DEBT rel, the strongest coin in
  the social ledger. A dire patient lost is a real NPC death, so a played
  healer is a small NPC mortality source in play mode (rulers are excluded
  from the patient pool). The trade run's PROFITEER fork (§3) runs grain
  into a starving land at famine prices for `PROFITEER_MULT` and
  `PROFITEER_KARMA`: vice is still the fast lane.
- **Techniques** (§9, P7) — A TECHNIQUE IS A CARD: a school, a realm gate,
  one effect, known or not (comprehension levels are deferred). The five
  schools and their ladders are `TECHNIQUE_SCHOOLS`: MOVEMENT (3 rungs,
  realm 1+, `ESCAPE_MOVEMENT` a rung on `_escape_chance`), MISSILES (realm
  2+, a free `TECHNIQUE_MISSILE_OPENER` of an exchange at the top of
  `_bout`), PRESSURE (realm 3+, a fight that does not happen —
  `_pressure_backs_down` — plus `TECHNIQUE_PRESSURE_TILT` on the harsh
  road, where the men are mortals), FLIGHT (realm 3+, a floor of
  `TECHNIQUE_FLIGHT_ESCAPE` under any escape, and the bandit road on a
  trade run), ELEMENTAL ARTS (2 rungs, realm 2+, +1 power a rung and an
  epithet). Cards live on `Agent.techniques`, not on `play`, because the
  famous carry them too; `technique_rank` is the only place a ladder is
  counted and `_grant_technique` the ONE door they come through. Four doors
  open onto it: the sect library (`_hall_technique`, gated on
  `HALL_TECHNIQUE_STANDING` and `HALL_TECHNIQUE_COST` — the only one that
  lets the player choose the shelf, through `ask_player`), a master
  (`_master_technique`, at the trial and now and then in a training season,
  teaching from their OWN hand where the disciple's realm can hold it), and
  MANUALS looted out of the treasure slots of the road and the secret
  realms (`_maybe_manual` at `MANUAL_FIND`) — of which `MANUAL_FLAWED`, one
  in five, are FLAWED: the technique works, and the +1 burden it has been
  quietly adding is only discovered at the next tribulation, where it is
  read BESIDE `play.clarity` and never inside it. §9's ONE NPC-FACING
  EXCEPTION is `_famous_techniques`: a famous name (`is_famous` — realm >=
  `FAME_REALM` or standing >= 10) rolls 0-2 cards at realm-up, hung off the
  breakthrough line so a name is news and its homework is not. That is the
  only die the player layer rolls on an NPC path — remove it and a batch
  run is BIT-IDENTICAL to P6's, which is how its cost was measured. What
  reaches an NPC's fight is the elemental point alone (`Agent.tech_power`,
  which the one roll reads); the other four schools are SCENES and are read
  only in a fight the played character is in, because off camera the
  tyranny of realms already says what Pressure says out loud.
- **A played throne** (§10, P7) — throne paths reach the player as choices
  (P1 wired the offers: `_throne_claim`, `_throne_invitation`, the revolt
  championship), and a played REIGN runs at YEAR tempo: `Play.reign_turn`
  prints `World.reign_card` once a year and the court then asks for exactly
  two decisions. THE EMPHASIS (`_player_emphasis`): one facet chosen from
  the top three the ruler's own traits score (`_facet_options`), fired
  ALONGSIDE what the situation forces — a king may lean on what he is, not
  become someone else. THE EDICT (`_player_proclaims` / `_player_repeals`):
  seal the order the court has drawn, or leave it lying; let an old one
  lapse, or keep it — and only in the years the engine's own rules would
  have proclaimed or repealed one anyway, so the player holds no lever the
  engine does not. Everything else is VI §4 unchanged: cultivation locked,
  qi frozen, insight only from governance adversity, `_maybe_corrupt`
  unmodified, and `player_abdicate` on the menu every single year. Being
  crowned or thrown down is a HARD interrupt (`pc_watch` / `pc_alarms`
  carry `ruling`), because the CLOCK changes: a timeskip that ran through a
  coronation would spend the reign's decisions on nobody.
- **The autopilot** (§12, P5, `--autopilot`) — `Autopilot` picks a legal
  activity at random every season and answers every `ask_player` question by
  coin, on its OWN `random.Random` and never on `world.rng`.
  `World.activity_available` / `activity_refusal` are the one list of legal
  choices, read by both the terminal and the bot.
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

## Tuning targets (Part III + VI §13 + VII §12 — check these after changing rates)

Measured over 200-year runs on TWO INDEPENDENT 32-seed blocks (seeds 1-32 and
101-132) with `tune4.py` in the tuning scratch — NOT the older `tune.py`,
which counts incursions as upheavals and misreads the political cadence.
P7's numbers, which all of these currently hold at, are in parentheses as
(block 1-32 / block 101-132).

- **Funnel** (Part III §4): per intake of 64 — ~35-45 reach realm 2, ~15
  reach realm 3, ~4-6 reach realm 4, 0-2 ever touch the top.
  (36.8/15.2/6.5/1.62 and 35.7/15.1/6.2/1.78.) The knobs are `INSIGHT_REQ`
  (the first gate is deliberately wide), `ADVENTURE_DEATH` /
  `ADVENTURE_NEAR_DEATH`, and the breakthrough chance in
  `_try_breakthrough`.
  **THE HORIZON IS PART OF THE TARGET.** Realm 2 and 3 saturate inside 120
  years and never move again; realm 4 and above keep climbing for as long as
  the cohort is alive to climb. One seed block, one build, five horizons:

  | years | >=2 | >=3 | >=4 | >=5 | >=6 |
  |------:|----:|----:|----:|-----:|----:|
  | 100 | 35.7 | 13.6 | 1.5 | 0.00 | 0 |
  | 130 | 35.7 | 14.6 | 4.4 | 0.09 | 0 |
  | 150 | 35.7 | 14.6 | 5.9 | 0.28 | 0 |
  | 200 | 35.7 | 14.6 | 6.6 | 1.59 | 0 |
  | 280 | 35.7 | 14.6 | 6.6 | 1.66 | 0 |

  Session 7's documented 36.0 / 15.1 / 4.2 / 0.25 is a ~130-year reading of
  exactly this curve; every session since P1 has measured at 200 and read
  6.0-7.0 at realm 4, and so does the PRE-P1 build (6.4). Nothing drifted
  and no knob was moved: the band holds at the design's own "century-plus"
  horizon, and ~6.5 is the LIFETIME number (the cohort dead, 280 years).
  Quote the horizon whenever you quote the funnel — everything on this page
  is measured at 200 years. Nobody has ever reached Dao Seeking (realm 6) in
  any measured run.
- **Talent vs luck**: final realm should correlate with talent, with famous
  exceptions. Monotone = luck too weak; uncorrelated = talent is decoration.
  (Pearson r 0.283 / 0.292.)
- **Bad lands**: 2-4 of the nine under visibly bad rule at any moment, and
  at least one prosperous-to-golden. Misery is common, not universal.
  (3.41 bad / 1.00 good, and 3.41 / 1.12.) Knobs: `PROSPERITY_RECOVERY` /
  `PROSPERITY_SETTLING`, `RULE_FACET_EFFECTS`, `COURT_TRAIT_WEIGHTS`,
  `NEGLECT_AGE_SCORE`.
- **Rulership is a real exit, not a common one**: 2-5% of a cohort ends its
  story on a throne. (5.5% / 4.7% ending on one; 9.3% ever ruling.) This
  reads high against session 7's 2.2% for the same reason the funnel does —
  it is a 200-year reading of a number session 7 took at ~130 — and it has
  sat at 4.5-5.7% through every session of the playable layer, which did not
  touch a throne knob. Knobs: the `ABDICATE_*` rates, `INVITE_CHANCE` /
  `INVITE_REFUSE_BASE`, `CLAIM_*`, `REVOLT_REFUSE_BASE`.
- **Cadence**: a revolt or war somewhere every 8-15 years; assassinations
  rarer. (One per 9.6 / 10.1 years; assassinations one per ~122.)
  `REVOLT_CHANCE_PER_UNREST` and `WAR_CHANCE` move as a pair.
- **Karma check**: sort the dead by karma into quintiles. High karma should
  show slightly better realms and kinder deaths, low karma more wealth and
  more violent ends — and NEITHER monotone, or the karma system has become
  dramaturgy. Still U-shaped after P7 put VII §4's missing price on the
  ledger (realm / age at death / silver, block 1-32): q1 (karma -10.2)
  1.49 / 52.3 / 48.3, q2 1.35 / 40.8 / 28.9, q3 1.43 / 50.2 / 38.5,
  q4 1.52 / 59.3 / 46.8, q5 (karma +7.4) 2.21 / 88.4 / 78.2. Both extremes
  outlive and outearn the middle; saints still die young and tyrants still
  die old and rich.
  THE PRICE P7 ADDED (`KARMA_EXECUTE_YIELDED = -2`): `_karma_kill`'s own
  rule is a REALM GAP, so between equals the spare paid +1 and the execution
  cost nothing — mercy was free money and the yield fork was one-sided.
  A yielded foe finished off now costs -2, charged in `_karma_kill` and only
  when the gap has not already charged for it. It moves the stream (karma
  feeds luck, the tribulation, grudges and the assassin's list) but not the
  shape: every band above holds with it in.
- **Chronicle balance**: political lines at most ~30% of the chronicle.
  (24.7% / 24.1%.)
- **Duel aggregates** (P2's retune target, measured over 32 seeds x 200
  years with a scratch instrument on `_duel`/`_maim`/`kill`): ~777 duels a
  run, ~245 dead in them (~47 across a realm gap, ~186 executed or killed
  by mischance between equals), ~100 beaten foes spared, ~33 maimings.
  The stance rewrite holds all of these within a couple of percent; the
  knobs are `STANCE_EDGES`' kill/maim/execute columns,
  `STANCE_EXECUTE_TRAITS`, `STANCE_MURDEROUS_TRAITS` and
  `STANCE_MURDEROUS_PLAIN`.
- **The combat invariant** (VII §5/§12, P3 — `python3 cultivation_sim.py
  --test-combat`, ~40s, exit 1 on FAIL): the round model's win% within 3
  percentage points of `duel_odds` across the matchup grid (21 cells, worst
  ~1.2pp), even fights 3-8 rounds at every edge (median 3 / 6 / 7 / 7),
  sparring kills nobody, duel accidents under 3% (~2%), maim rates ordered
  sparring < duelling < all-out, and the two resolutions killing and
  crippling at the same rates. P7 added two cells carrying elemental arts
  (a POWER term, so the one roll sees it and the invariant must hold with
  it on) and two rows to the body table for the schools the one roll cannot
  see. What things are worth on an even duel, all measured there: a serious
  wound -12.5pp, a light one -5.7pp, Body 5 +3.3pp, MISSILES +2.8pp, the
  whole +4 power cap +4pp, one rung of elemental arts +1.2pp. The stop
  lines (`STANCE_EDGES["stop"]`), the swing band (`ROUND_SWING`), the pause
  thresholds and `TECHNIQUE_MISSILE_OPENER` are all set against this
  harness, not guessed.
- **Techniques** (VII §9, P7): the deck is scarce, symmetric and small.
  Over a 200-year world ~13% of the sect population ends up holding a card
  (0% of Qi Condensation, 11% of Foundation, 47% of Core Formation, 76% of
  Nascent Soul), 1.5 cards each — the arms race is real at the top and
  invisible at the bottom, which is where the funnel lives. A century of
  full-time adventuring is what it takes to collect most of the eight rungs
  (`MANUAL_FIND` is the knob; at a third of treasure slots one hand came
  home with the whole deck, which is no deck at all). The famous-NPC roll
  is the ONLY die the player layer rolls on an NPC path: with
  `_famous_techniques` removed the batch is BIT-IDENTICAL to P6's
  (35.7/14.6/6.6/1.59 and 35.0/14.8/6.3/1.78, exactly), and switched on it
  moves the funnel by less than a stream reshuffle does (zeroing the chance
  but leaving the die in the stream moves realm 4 by 0.6 all by itself).
- **The pill wall** (VII §12, P6 — `wall.py`, three scripted hands over 32
  seeds x 200 years): a pill-stacking bot must reach realm 3 unusually fast
  and STALL at the realm-4 tribulation on burden. It does. GREEDY (fills
  the dantian from the shelf whenever the mind is ready, 33.7 pills a life)
  reaches realm 2 by year 8 and realm 3 by year 35 — against CONTROL's
  (brews the same pills and sells every one) year 31 and year 74 — and then
  reaches realm 4 in 0 of 32 runs, standing at the tribulation with burden
  38 and an 8.4% chance, at the 5% floor in 87% of its attempts. PACED
  (never past `PILL_TOXICITY_FREE`) is the one that gets through: realm 4
  in 3 of 32, burden 6. Toxicity is not decoration.
- **Front cadence** (VII §12, P4 — `front.py` over 16 seeds x 200 years on
  each block): an incursion every 8-15 years (9.3 / 9.2 measured on the
  agenda, 9.8 / 10.2 off the upheaval file), settlements swallowed 3.5 a run
  (defeat is rare), the front the deadliest lane there is (110.9 / 114.9 NPC
  deaths a run against a secret realm's 28.6 / 25.7), and march-lands
  running 1.34 / 1.53 under their own baseline temper against the rest of
  the map's ~0. Knobs: `FRONT_CHANCE` /
  `FRONT_CHANCE_PER_THREAT` / `FRONT_RETURN` for the volume, `FRONT_DEATH` /
  `FRONT_MAUL` for the lethality, `DEMON_THREAT_DRIFT` and
  `DEMON_RELIEF_CAP` for the cadence, `INCURSION_WALL_BASE` /
  `INCURSION_THREAT_SCORE` for how often the line breaks, and
  `MARCH_BASELINE` / `MARCH_DRAG_PER_THREAT` for the marches' standard of
  living. NOTE that `_remember` files incursions too, so a cadence
  instrument must separate them from revolts and wars or it will read one
  upheaval per five years and look broken.
- **The autopilot funnel** (VII §12, P5-P7 — `--autopilot`, measured with
  `auto.py` over two 32-seed blocks x 200 years): a PC played by a random
  legal-choice bot must land inside the Part III funnel and must not be an
  outlier itself. It does: the 64 beside the bot come out 36.4/15.6/6.2/1.69
  and 35.3/14.4/5.8/1.44, and the bot itself ends a shade BEHIND them (mean
  final realm 1.59 / 1.62 against the cohort's 1.93 / 1.89; realm 2 in
  50% / 44% of runs against 57% / 55%) — a hand that is not paying
  attention comes out under an NPC whose traits at least steer it, which is
  the target said the right way round. It runs hotter: 2.39 / 2.38 deaths
  per 100 years lived against the cohort's 1.20 / 1.22, because a uniform
  hand takes the demon front and the harsh road far more often than traits
  do; at realm 1, where most bot lives end, it dies at about the cohort's
  own age. `CRAFT_ACCIDENT` is the lever that moves this (P6 put it in
  because three professions with no risk at all had quietly made the bot
  SAFER than the cohort); it is where P6 set it and P7 measured it there
  and left it. `TRAIN_QI_SHARE` / `PROFESSION_QI_SHARE` are the other lever:
  every activity added to the menu that pays no qi makes the season layer a
  PENALTY for being played. Re-measure both whenever the menu grows.
- **The archetype bar** (VII §13, P7's own): one hand-played life per
  archetype — sword saint, poison merchant, front veteran, tyrant king —
  each describable in one sentence, played non-interactively by piping a
  scripted stdin into `--play`. The four that closed the layer:
  a Righteous swordsman taken as a disciple in his first year, maimed twice
  in duels he refused to escalate, who found a second master at 96, reached
  Nascent Soul at 113 and bought the Weight of the Mountain out of his own
  sect's library at 123; an apothecary who ran grain into starving countries
  at famine prices forty times, was turned Cruel by his own deed ledger
  (karma -78, 298 silver, never past the first realm) and died at 61 testing
  a batch on himself; a disciple who served 31 seasons on the eastern
  marches, stood once in the breaking of the line, took the name Wastewalker
  and was pulled down at 51 defending the villages behind it; and a
  cultivator who stalled at Foundation Establishment, claimed a vacant
  khanate at 101, spent 24 years taxing and terrorising the Sky Steppe under
  three edicts of his own, and died on the seat at 126 with his qi exactly
  where he had left it.
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
- What Part VII deliberately left for later, having built P1-P7:
  **named demon lords as real agents** (out of scope by decision, not
  omission — the Waste is a field and a scene table, VII's up-front block);
  **technique comprehension levels** (§9 defers them: a card is known or it
  is not, and the ladder is the whole depth there is); **a played reign
  deeper than §10's two decisions a year** (the emphasis and the edict fork
  — v1 keeps rulership rulership-shaped rather than opening a strategy
  game); **NPC professions** (§8: an NPC's single `resources` number is
  already the abstraction of every pill, blade and physician, and
  `profession_taught` therefore accepts ANY master rel — a cultivation
  teacher stands in for an alchemy one, which is the seam to fix first if
  crafts ever reach NPCs); the front as a technique door (§9 gives the
  cards four doors and the marches is not one of them); and saves, multiple
  played characters, and anything resembling a UI that is not a terminal.

## Known deviations from the spec (deliberate, from tuning)

- **`TECHNIQUE_MISSILE_OPENER = 0.2`** (VII §9). §9 asks for "a free
  first-round hit at range" and does not price it; a whole free exchange is
  worth +14pp on an even duel — more than the entire +4 power cap buys —
  so the opener is a FIFTH of one, measured in `--test-combat` against the
  cap and against a rung of elemental arts, and worth about two points of
  power.
- **Four of the five schools are read only ON CAMERA** (VII §9): Movement,
  Missiles, Pressure and Flight are scenes, and `_pressure_backs_down`,
  `_bout` and `_escape_chance` are only ever reached in a fight the played
  character is in. Elemental arts, being a power term, is read everywhere.
  §9 does not draw this line; without it a famous NPC's Pressure would
  quietly convert a large share of the world's realm-gap killings into
  back-downs, which is a funnel change dressed as flavour. Off camera the
  kernel's own tyranny of realms already says what Pressure says out loud.
- **`FAMOUS_TECHNIQUE_CHANCE` / `_SECOND` (0.45 / 0.25)** are not in the
  spec; §9 says famous NPCs roll "0-2 techniques at realm-up" and these are
  the two numbers that make that sentence true. They are the only dice the
  player layer rolls on an NPC path, kept in one method so the cost to the
  batch stream can be measured by deleting them.

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
