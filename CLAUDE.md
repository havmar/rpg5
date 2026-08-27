# Cultivation World Simulator

A wuxia/xianxia career simulator: a mechanical world kernel whose structured
event logs are the product. The design philosophy is **SIM FIRST, CHEAT
LATER** — no plot armor, no dramaturgy; if raw agent logs already read like
lives, the kernel is right. The full design is in `cultivation_sim_design.txt`
(read it before making non-trivial changes; the code implements Part III, the
"toy version").

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
`log NAME`, `follow` (run on until the PC's story ends), `roster`,
`famous`, `obits`, `help`, `quit`. Name lookup is
case-insensitive substring match.

## Architecture (all in cultivation_sim.py)

- **Data tables / tuning knobs** at the top: realms, `INSIGHT_REQ`, lifespans,
  intake size/period, feud threshold, trait pool, `TRAIT_ACTION` weights, and
  `NAME_LANDS` — six fictional homelands with male/female given-name and
  surname pools borrowed from real-world languages (Indonesian, Mongolian,
  Finnish, Icelandic; Sanskrit and Persian are rare). Each agent rolls a sex
  and homeland; every intake cohort skews toward one dominant land
  (`DOMINANT_LAND_BOOST`), and `MIXED_NAME_CHANCE` gives a surname from a
  different land. Glacier Coast surnames are patronymic
  (`-sson`/`-sdottir`).
- **`Agent`** — the uniform agent sheet from the design doc: age, realm, qi,
  talent, insight, burden, resources, standing, traits, relationships
  (`rels: {aid: Rel(kind, intensity)}`), epithets, private `history`, and a
  small `fortune` counter (streaky luck).
- **`World`** — owns agents, sects, sect heads, the chronicle, and the year
  loop. `World.step()` advances exactly one year and returns the chronicle
  lines it produced (this is the API to build on: a UI, an AI-DM renderer,
  or a player layer would call `step()` and read the logs).
- **Year loop** (`step`): action phase (each agent softmax-picks
  cultivate/seclude/adventure/socialize/teach via trait weights + situational
  nudges) → event phase (tournament every 4 years, secret-realm expedition on
  a random timer, sect feud when cross-sect grudges pass a threshold,
  successions on sect-head death) → resolution phase (breakthroughs, aging,
  old-age death, voluntary exits) → intake recruitment every 8 years.
- **Contests** — one formula (`Agent.power`) with the "tyranny of realms":
  1 realm apart = flee or lose; 2+ = not a fight. Insight is granted by
  ADVERSITY (surviving losses, near-death, grief), never by victory.
- **Trait mutation** (`_mutate`) — Proud crushed in public may become
  Humble/Vengeful/Broken, Loyal betrayed becomes Vengeful, near-death breeds
  Cautious/Ascetic. This is the main tool for making characters legible.

## The logging model (the important part)

Every consequential event goes through `World.log(text, actors, dramatic=,
world_event=)`. It ALWAYS appends to each actor's private `history` —
nothing is lost, and `log NAME` shows any character's full life. A line is
printed to the shared chronicle only when one of these holds, in priority
order:

1. **`[PC]`** — the main character is an actor.
2. **`[friend]`/`[rival]`/`[enemy]`/`[ally]`/`[master]`/...** — an actor has
   a relationship with the PC (the tag names it).
3. **`[world]`** — world-scale events (feuds, successions, expeditions,
   intakes), passed with `world_event=True`.
4. **`[famous]`** — the event is `dramatic=True` AND involves a famous
   character (realm >= `FAME_REALM`, currently Nascent Soul, or standing >= 10):
   breakthroughs of the mighty, violent deaths, maimings, high-realm
   tournament finals.

Everything else stays private to the characters involved. The PC is chosen
at random from the starting intake of 64; if they die, their obituary prints
and the chronicle picks a new young protagonist (`_succeed_pc`).

## Tuning targets (from the design doc — check these after changing rates)

- **Funnel**: per intake of 64 over ~a century: ~35–45 reach realm 2, ~15
  reach realm 3, ~4–6 reach realm 4, 0–2 touch the top.
- **Talent vs luck**: final realm should correlate with talent, with famous
  exceptions. Monotone = luck too weak; uncorrelated = talent is decoration.
- **Distinguishability**: pick five agents, read `log NAME` for each; every
  life should be describable in one sentence. If lives blur, add trait
  mutation and relationship events, not stats.

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
- The player layer (Part IV): real inventory, techniques, explicit dao,
  scene-level tribulations. The PC here is only a *camera*, not a player.
