#!/usr/bin/env python3
"""Cultivation World Simulator — toy version.

First-pass implementation of Part III of cultivation_sim_design.txt:
a uniform agent model, a yearly three-phase loop (action / events /
resolution), traits that weight actions, mutate under pressure and modify
outcomes, epithets, tournaments, expeditions, feuds, successions,
breakthroughs with real failure states, voluntary exits, and generations
via 8-year intakes.

Plus the first four courses of the politics layer (Part VI, sessions 1-4):
the nine lands on a 3x3 grid, a nested tree of places carrying prosperity,
recruitment reach measured in geography, and — above the places — polities
with mortal rulers whose characters become policy. Rule style is scored
from the leader's traits every year and pushes prosperity, unrest and the
ruler's own purse; senseless edicts make a bad reign describable in one
sentence. `map`, `land NAME` and `courts` show the political world.

Session 3 is the contact surface: the common people never become agents,
but their lives reach the sim at four points. A recruit's home village is
already on their sheet (a misruled one hands out burden, banked adversity
and a grudge against the man who did it; a rich one hands out silver); a
family keeps sending silver, or news of a brother taken for the levies;
every adventure now goes to a named land whose prosperity reshapes the risk
table; and a starving settlement can petition a sect for a hero.

Session 4 makes the throne a real exit from the path. Ruling LOCKS
cultivation: a ruler's action phase is one RULE action, qi gain is zero, and
the only insight a seat earns is bought with governance adversity — a raid
the court could not punish, a vassal who kept the tribute, an attempt on the
seat survived. Realm still counts in full, which is what keeps a Core
Formation king on a mortal seat for a century. Cultivators reach thrones
three ways — a claim on a vacant seat, an invitation from a court in
disarray (which they may refuse, and the obituary remembers it), or
usurpation, settled by the tyranny of realms — and leave them three ways:
death, deposition, and abdication, after which a cultivator walks back up
the mountain with their qi exactly where the throne found it. Power
corrupts: every ruling year is a chance to slip one step down the ladder
Greedy -> Power-Hungry -> Cruel. The PC camera keeps rolling through a
reign; enthronement is not an ending.

Session 5 is the moral economy, and it is mechanical to the last digit: no
event anywhere asks "is this the villain". Four vice traits join the pool —
Bully (fights only downward, and shakes the juniors down for what they
carry), Power-Hungry (schemes, covets seats, turns Vengeful when passed
over), Cruel (maims the beaten, so the world fills with walking evidence)
and Bloodthirsty (takes a duel past winning, and rides to any muster that
will have them). Karma is seeded from disposition and then moved by DEEDS
that dominate it over a long life — killing the defenseless, sparing a
beaten foe, rescue, dying in defence of others — and karma is coupled to
everything that was already there: luck drifts toward the sign of it, the
tribulation reads it, the road tilts by it, grudges bite half again as deep
against a black ledger, and vice takes a cut of every win. Virtue is the
luck lane; vice is the fast lane for wealth. The one deliberate cheat in the
whole layer is the camera constraint (§8): the protagonist and the few
people bound to them can darken, but never become monstrous.

Session 6 gives the country its answer. Unrest used to be a gauge with no
valve — the bad courts pinned it at the cap and only a funeral ever spent
it — and now it has three. A country over the threshold RISES, and looks
first for a champion: someone carrying a grudge against that court, or a
Righteous native of it. The rising is settled by the tyranny of realms like
every other contest, which is why a mortal tyrant falls to any Foundation
Establishment champion and a cultivator-king does not fall at all: he walks
into the crowd himself, and the massacre buys him a few quiet years, a
ruined country and a ledger nobody forgets. A winning champion is offered
the seat and may refuse it. A reign whose ledger has gone deeply black
draws KNIVES — grudge-holders within a realm of the seat, one attempt a
year anywhere in the world, and a success is a succession with a corpse on
the floor. And restless courts with armies to spend make WAR along the
edges of the grid: an abstract campaign of one to three years, prosperity
down on both sides, conscripts dead by the thousand as chronicle colour,
and the cultivators who rode to it dying like the agents they are. Wars end
in tribute, in a ceded region, or in a kneeling; a vassal who kept the
tribute one year too many is fought back under the oath, or wins its
independence. Sect headship, meanwhile, turns out to be rulership-lite: the
head's virtues and vices tilt the sect's richness and drift the juniors'
standing, and under a vice-heavy head the Righteous and the Humble DEFECT —
which seeds precisely the cross-sect grudges the feud arithmetic has been
counting all along.

Part VII session P1 makes the PC playable. The year loop is now PLAN (the
YEAR AGENDA: every event of the year rolled at year start and stamped with
a season), PLAY (four season sub-steps; NPCs still take their one action in
spring, read as what they mostly did that year) and CLOSE (the old
resolution phase and the intakes, at winter's end) — in ALL modes, so batch
and observer runs look exactly as they did. `--play` adds agent 65 to the
watched intake with everything rolled honestly and hands them to a human:
one activity per season from a small menu of reskins of the kernel's own
actions, each paying a QUARTER of the matching yearly action, plus
timeskips that stop the season BEFORE anything that is the player's
business and print a digest of what was missed. Traits stop weighting the
played character's choices and start being written BY them: the deed
ledger, not the dice, decides what a played life mutates into.

Logging policy (the product):
  * Every consequential event is appended to the PRIVATE history of every
    agent involved. Nothing is lost.
  * The printed CHRONICLE only carries lines that involve the main
    character (the PC), someone the PC has a relationship with (rivals,
    enemies, friends, allies, masters...), world-scale events, or FAMOUS
    characters (Nascent Soul and above) in dramatic/tragic moments.
  * Any agent's full private history can be inspected with `log <name>`.

Run it:
    python3 cultivation_sim.py                # interactive, step year by year
    python3 cultivation_sim.py --years 200    # batch run
    python3 cultivation_sim.py --seed 7       # reproducible world
    python3 cultivation_sim.py --follow-pc    # follow one PC to the end
    python3 cultivation_sim.py --play         # PLAY agent 65, season by season

Stdlib only. Python 3.9+.
"""

import argparse
import random
import sys
from dataclasses import dataclass, field
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Data tables and tuning knobs
# ---------------------------------------------------------------------------

REALM_NAMES = {
    1: "Qi Condensation",
    2: "Foundation Establishment",
    3: "Core Formation",
    4: "Nascent Soul",
    5: "Spirit Severing",
    6: "Dao Seeking",
}
MAX_REALM = 6
FAME_REALM = 4          # realm at which a character becomes a household name

# Insight required to attempt the breakthrough OUT of each realm. The first
# gate is deliberately WIDE and the rest narrow sharply: insight only ever
# arrives through adversity, so a high first gate did not select for talent,
# it just left two thirds of every intake stalled at Qi Condensation until
# something on the road killed them. Part III's funnel is what these five
# numbers are for.
INSIGHT_REQ = {1: 3, 2: 28, 3: 32, 4: 52, 5: 80}

BASE_LIFESPAN = 80
LIFESPAN_PER_REALM = 45  # each realm past the first adds this many years

INTAKE_SIZE = 64         # total new students per recruitment cycle
INTAKE_PERIOD = 8        # years between intakes
FEUD_THRESHOLD = 14      # summed cross-sect grudge intensity that ignites a feud
FEUD_COOLDOWN = 12
TOURNAMENT_PERIOD = 4
FOLLOW_CAP_YEARS = 500   # safety cap when following one life to its end

TRAIT_POOL = [
    "Proud", "Cautious", "Reckless", "Ruthless", "Loyal", "Vengeful",
    "Scholarly", "Charming", "Stubborn", "Ascetic", "Greedy", "Humble",
    "Righteous", "Cold",
    # The four vices (§7). They are rolled like any other trait; only karma
    # ever reads them as a set.
    "Bully", "Power-Hungry", "Cruel", "Bloodthirsty",
]

# JOB 1 — traits weight the yearly action choice (multipliers on base weights).
TRAIT_ACTION = {
    "Proud":        {"socialize": 1.3},
    "Cautious":     {"adventure": 0.5, "cultivate": 1.3},
    "Reckless":     {"adventure": 2.2, "seclude": 0.6},
    "Ruthless":     {"socialize": 1.2},
    "Loyal":        {"socialize": 1.2},
    "Vengeful":     {"socialize": 1.4},
    "Scholarly":    {"cultivate": 1.4, "teach": 1.8},
    "Charming":     {"socialize": 1.8},
    "Stubborn":     {"cultivate": 1.3},
    "Ascetic":      {"seclude": 2.2, "socialize": 0.5},
    "Greedy":       {"adventure": 1.6},
    "Humble":       {"cultivate": 1.2},
    "Righteous":    {"socialize": 1.1},
    "Cold":         {"seclude": 1.4, "socialize": 0.6},
    "Broken":       {"seclude": 1.7, "adventure": 0.5},
    # A bully needs juniors in front of them, a schemer needs a room, and a
    # bloodthirsty disciple needs someone to fight: all three live in the
    # socialize action, which is where duels come from.
    "Bully":        {"socialize": 1.6, "seclude": 0.6, "teach": 0.4},
    "Power-Hungry": {"socialize": 1.9, "seclude": 0.5, "cultivate": 0.9},
    "Cruel":        {"socialize": 1.3, "teach": 0.5},
    "Bloodthirsty": {"socialize": 1.5, "adventure": 1.5, "seclude": 0.5},
}

# Every trait an agent can actually be carrying: the rolled pool plus the
# ones only mutation hands out. The corruption ladder of §4 walks through
# this set and stops at the last rung that exists in it.
ACQUIRABLE_TRAITS = set(TRAIT_POOL) | set(TRAIT_ACTION)

# Names come from six language pools, each borrowing a real-world language so
# agents stay pronounceable and easy to tell apart. A pool supplies one or
# two of the nine lands (see GEOGRAPHY below); every agent rolls a home
# settlement, and their descent is the name pool of that settlement's land.
# Each intake cohort skews toward one dominant land, and a small fraction of
# agents carry a surname from a different pool than their given name (mixed
# parentage). Rarity is geographic now, not a static per-pool weight: distant
# corner lands simply send fewer recruits.
NAME_LANDS = {
    "Spice Isles": {                                # Indonesian
        "male": [
            "Adi", "Agus", "Anwar", "Arif", "Bagus", "Bambang", "Bayu",
            "Budi", "Cahya", "Dimas", "Eko", "Fajar", "Gede", "Gilang",
            "Hendra", "Ilham", "Joko", "Ketut", "Made", "Panji", "Putu",
            "Raden", "Rizki", "Slamet", "Surya", "Teguh", "Wahyu", "Wayan",
            "Yoga", "Yusuf",
        ],
        "female": [
            "Ayu", "Citra", "Dewi", "Dian", "Endah", "Fitri", "Indah",
            "Intan", "Kartika", "Kirana", "Lestari", "Mega", "Melati",
            "Nia", "Ningsih", "Putri", "Rani", "Ratna", "Rina", "Sari",
            "Sinta", "Siti", "Sri", "Tari", "Wulan", "Yanti", "Yuli",
        ],
        "surnames": [
            "Gunawan", "Halim", "Harahap", "Hartono", "Hutapea", "Kusuma",
            "Lubis", "Manullang", "Nasution", "Panggabean", "Purnama",
            "Santoso", "Saputra", "Sihombing", "Simanjuntak", "Sinaga",
            "Siregar", "Sitorus", "Situmorang", "Tampubolon", "Tanjung",
            "Wibowo", "Widodo", "Wijaya", "Winata",
        ],
    },
    "Sky Steppe": {                                 # Mongolian
        "male": [
            "Altan", "Baatar", "Batbayar", "Batu", "Bold", "Chuluun",
            "Delger", "Dorj", "Enkhbold", "Erdene", "Ganbaatar", "Ganbold",
            "Gantulga", "Jargal", "Khasar", "Munkh", "Naran", "Nergui",
            "Ochir", "Sukhbat", "Temur", "Tsend", "Zorig",
        ],
        "female": [
            "Alimaa", "Altantuya", "Anu", "Bolor", "Bolormaa", "Chimeg",
            "Dulmaa", "Enkhtuya", "Gerel", "Khongorzul", "Khulan",
            "Mandakh", "Narantuya", "Nomin", "Odval", "Oyun", "Sarnai",
            "Solongo", "Suvda", "Tsetseg", "Tuya", "Zaya",
        ],
        "surnames": [
            "Barlas", "Bayad", "Besud", "Borjigin", "Jalair", "Kharchin",
            "Khereid", "Khongirad", "Merkid", "Naiman", "Oirat",
            "Olkhunut", "Onggud", "Sartuul", "Sunud", "Taichuud",
            "Torguud", "Uriankhai", "Zakhchin",
        ],
    },
    "Thousand Lakes": {                             # Finnish
        "male": [
            "Aarne", "Antero", "Antti", "Eero", "Eino", "Esa", "Hannu",
            "Heikki", "Ilmari", "Jaakko", "Jorma", "Juhani", "Jukka",
            "Kalevi", "Kari", "Lauri", "Matti", "Mikko", "Olavi", "Onni",
            "Paavo", "Pekka", "Raimo", "Reino", "Risto", "Sampo", "Seppo",
            "Tapio", "Teemu", "Timo", "Toivo", "Urho", "Veikko", "Vesa",
        ],
        "female": [
            "Aino", "Anneli", "Eeva", "Elina", "Hanna", "Helmi", "Hilkka",
            "Iida", "Inkeri", "Kaarina", "Kaisa", "Katri", "Kerttu",
            "Kielo", "Liisa", "Maija", "Marja", "Marjatta", "Mielikki",
            "Minna", "Pihla", "Ritva", "Saima", "Sanna", "Sirkka", "Suvi",
            "Terhi", "Tuulikki", "Vappu", "Venla", "Vilma",
        ],
        "surnames": [
            "Aalto", "Ahonen", "Halonen", "Heikkinen", "Heinonen",
            "Hiltunen", "Immonen", "Kallio", "Karjalainen", "Kinnunen",
            "Kivinen", "Korhonen", "Koskinen", "Laakso", "Lahtinen",
            "Laine", "Laitinen", "Lehtinen", "Lehtonen", "Manninen",
            "Mattila", "Nieminen", "Niskanen", "Rantanen", "Rautio",
            "Saarinen", "Salminen", "Salo", "Salonen", "Toivonen",
            "Tuominen", "Turunen", "Virtanen",
        ],
    },
    "Glacier Coast": {                              # Icelandic
        # Surnames here are patronymic stems: a father's name that becomes
        # "<stem>sson" for men and "<stem>sdottir" for women.
        "patronymic": True,
        "male": [
            "Ari", "Askur", "Baldur", "Birkir", "Bjarki", "Dagur", "Egill",
            "Einar", "Eldur", "Fannar", "Gisli", "Grimur", "Gunnar",
            "Hakon", "Haukur", "Hilmir", "Kjartan", "Leifur", "Loftur",
            "Magnus", "Orri", "Ragnar", "Sindri", "Skuli", "Snorri",
            "Sturla", "Teitur", "Ulfur", "Vidar",
        ],
        "female": [
            "Alda", "Arna", "Asta", "Birta", "Dagny", "Edda", "Embla",
            "Freyja", "Gudrun", "Halla", "Hekla", "Helga", "Hildur",
            "Idunn", "Katla", "Lilja", "Nanna", "Ragnhild", "Runa",
            "Salvor", "Sigrun", "Svala", "Thora", "Tinna", "Unnur",
            "Vigdis", "Yrsa",
        ],
        "surnames": [
            "Arnar", "Baldur", "Bergur", "Einar", "Eirik", "Finn", "Geir",
            "Gunnar", "Halldor", "Haukur", "Hjalmar", "Hrafn", "Ingolf",
            "Kjartan", "Leif", "Magnus", "Ragnar", "Sigmar", "Stefan",
            "Thorvald", "Ulfar", "Vidar",
        ],
    },
    "River Kingdoms": {                             # Sanskrit
        "male": [
            "Aditya", "Ananta", "Arjun", "Bhaskar", "Chandra", "Devadatta",
            "Dhruva", "Govinda", "Harsha", "Ishan", "Jayanta", "Kartik",
            "Mahendra", "Nakul", "Pranav", "Ravindra", "Rohan", "Vikram",
        ],
        "female": [
            "Aruna", "Devika", "Gauri", "Ila", "Kamala", "Lalita",
            "Madhavi", "Meera", "Nalini", "Padmini", "Radha", "Rukmini",
            "Savitri", "Sudha", "Tara", "Uma", "Vasanti", "Vidya",
        ],
        "surnames": [
            "Agastya", "Atreya", "Bharadwaj", "Gautama", "Kashyap",
            "Kaushika", "Maitreya", "Mitra", "Sandilya", "Sharma",
            "Varma", "Vasishtha",
        ],
    },
    "Sunset Plateau": {                             # Persian
        "male": [
            "Arash", "Ardeshir", "Babak", "Bahram", "Bijan", "Dariush",
            "Farhad", "Faridun", "Hormoz", "Jamshid", "Kaveh", "Khosrow",
            "Kian", "Mehrdad", "Navid", "Omid", "Parviz", "Rostam",
            "Shahin", "Sohrab", "Siyavash",
        ],
        "female": [
            "Anahita", "Azar", "Banu", "Farah", "Golnar", "Laleh",
            "Mahtab", "Mina", "Nasrin", "Parisa", "Roshan", "Roxana",
            "Shirin", "Simin", "Soraya", "Taraneh", "Yasmin", "Ziba",
        ],
        "surnames": [
            "Afshar", "Bakhtiar", "Dashti", "Farahani", "Farrokhzad",
            "Golshani", "Kashani", "Kermani", "Rostami", "Sarabi",
            "Shirazi", "Yazdani", "Zand",
        ],
    },
}
DOMINANT_LAND_BOOST = 3.0   # each intake cohort skews toward one homeland
MIXED_NAME_CHANCE = 0.06    # surname from a different pool than the given name

# --- GEOGRAPHY: the nine lands ---------------------------------------------
# The world is a 3x3 grid of lands. The centre is the Middle Plain: the
# largest population, the seat of all four sects, and culturally a melting
# pot — it has NO name pool of its own, so its natives roll a descent from
# the six pools evenly and carry mixed surnames twice as often. The eight
# outer slots are filled from the six pools; at worldgen the rng picks two
# pools to supply TWO lands each (sibling nations sharing a tongue), using
# the fixed secondary land names below.
MIDDLE_PLAIN = "Middle Plain"
SECONDARY_LAND_NAMES = {
    "Spice Isles":    "Coral Strand",
    "Sky Steppe":     "Wolf Steppe",
    "Thousand Lakes": "Birch Marches",
    "Glacier Coast":  "Ashen Fjords",
    "River Kingdoms": "Lotus Delta",
    "Sunset Plateau": "Salt Wastes",
}
DOUBLED_POOLS = 2               # pools that supply two lands each
SIBLING_ADJACENCY_RETRIES = 1   # reshuffles spent trying to seat siblings together
MIDDLE_PLAIN_MIXED_MULT = 2.0   # the melting pot doubles MIXED_NAME_CHANCE

# Recruitment reach is geographic: the sects sit in the Middle Plain, so the
# centre sends the most students, edge lands fewer, far corners fewest.
RECRUIT_WEIGHT_CENTER = 4.0
RECRUIT_WEIGHT_EDGE = 2.0
RECRUIT_WEIGHT_CORNER = 1.0
# Relative populations when rolling which settlement of a land a recruit
# grew up in.
SETTLEMENT_POP_WEIGHT = {"city": 4.0, "town": 2.0, "village": 1.0}

# Shape of the place tree. The Middle Plain is the biggest land: three
# regions, a capital and the four sect seats; outer lands are smaller.
MIDDLE_PLAIN_REGIONS = 3
MIDDLE_PLAIN_REGION_SIZES = [3, 3, 4]   # settlements per region (rng.choice)
OUTER_REGIONS = [2, 2, 2, 3]
OUTER_REGION_SIZES = [2, 2, 2, 3]
TOWN_CHANCE = 0.35                      # else a village
PLACE_STEM_SURNAME_CHANCE = 0.6         # else the stem is a given name
SETTLEMENT_KINDS = ("city", "town", "village")

# Prosperity: a float 0-10 carried by settlements; regions and lands report
# the mean of the settlements beneath them. Each land rolls a baseline (its
# temper) and every settlement sits near it; left alone prosperity drifts
# back toward baseline. It is ALWAYS shown as a word, never a number.
PROSPERITY_BASELINE = (4.0, 6.0)
PROSPERITY_JITTER = 0.5
# The drift is PROPORTIONAL to the distance from baseline (a fraction of the
# gap per year), not a flat step. With a flat step the field was bang-bang:
# any reign whose yearly pull beat the step ran its country to zero and
# anything gentler pinned it exactly at baseline, so the map came out
# starving-or-golden with nothing in between. Proportional recovery makes
# prosperity a GRADED reading of whoever holds the seat — a country settles
# at baseline + (yearly pull / PROSPERITY_RECOVERY), so one vice makes a
# desperate land, two make a starving one, and a decent reign makes a
# prosperous one.
# It is also ASYMMETRIC: a ruined country climbs back toward its temper
# faster than a rich one can be pushed past it. Ruin is easy to leave and
# wealth is hard to reach, which is why a single vice on a seat makes a
# desperate land, two make a starving one, and only a genuinely decent reign
# — held for a generation — makes a prosperous one.
PROSPERITY_RECOVERY = 0.22      # per year, per point BELOW the baseline
PROSPERITY_SETTLING = 0.05      # ... and per point above it
PROSPERITY_DRIFT_MIN = 0.02     # it never quite stops moving
PROSPERITY_WORDS = [
    (2.0, "starving"), (4.0, "desperate"), (6.0, "modest"),
    (8.0, "comfortable"), (9.5, "prosperous"), (10.1, "golden"),
]

# Settlement names: a stem from the land's name pool plus a plain suffix.
PLACE_SUFFIXES = {
    "region":  ["Vale", "Marches", "Highlands", "Lowlands", "Downs", "Weald",
                "Fen", "Reach", "Uplands", "Hinterland"],
    "city":    ["Gate", "Market", "Hold", "Bastion", "Crossing", "Court",
                "Span", "Keep"],
    "town":    ["Ford", "Wells", "Bridge", "Mill", "Landing", "Bend",
                "Quarry", "Wharf"],
    "village": ["Rest", "Hollow", "Fields", "Croft", "Barrow", "Nook",
                "Watch", "End", "Furrow", "Bough"],
}

# --- POLITICS: polities, mortal rulers, rule styles, edicts ----------------
# Above the places sit the polities. Type follows culture: the Mongolian-pool
# lands raise khanates over tribes, the Icelandic-pool lands jarldoms, the
# centre the empire, everyone else kingdoms over city-states. Keyed by the
# land's NAME_LANDS pool; the Middle Plain (pool None) takes the centre pair.
POLITY_KINDS_BY_POOL = {
    "Sky Steppe":    ("khanate", "tribe"),
    "Glacier Coast": ("jarldom", "jarldom"),
}
POLITY_KINDS_CENTER = ("empire", "city")
POLITY_KINDS_DEFAULT = ("kingdom", "city")
POLITY_WORDS = {"empire": "Empire", "kingdom": "Kingdom", "khanate": "Khanate",
                "jarldom": "Jarldom", "city": "City", "tribe": "Tribe",
                "sect": "Sect"}
POLITY_TITLES = {                       # (male, female) form of address
    "empire":  ("Emperor", "Empress"),
    "kingdom": ("King", "Queen"),
    "khanate": ("Khan", "Khatun"),
    "jarldom": ("Jarl", "Jarl"),
    "city":    ("Lord", "Lady"),
    "tribe":   ("Chief", "Chief"),
    "sect":    ("Sect Head", "Sect Head"),
}
EMPIRE_VASSAL_COUNT = (1, 2)    # the centre rules its regions, holds city-states
OUTER_VASSAL_COUNT = (0, 2)     # each outer sovereign's vassals
TRIBUTE = 2                     # resources a vassal leader sends up each year
RULER_INCOME = 1                # the crown's ordinary revenue, per year
RULER_INCOME_RICH = 1           # again as much out of a comfortable country
RULER_INCOME_RICH_AT = 6.0      # prosperity at which a country pays it

# Worldgen rulers are ordinary Agents: sect-less mortals on the mortal clock.
RULER_AGE = (28, 62)            # age of a ruler installed at worldgen
HEIR_AGE = (32, 58)             # age of a courtier raised to a vacant seat
RULER_REALM2_CHANCE = 0.15      # a sovereign with a cultivator ancestor
RULER_RESOURCES = (6, 14)       # the treasury they sit on
RULER_STANDING = (5, 9)
# Court skew: thrones are not filled at random from the trait pool. The
# ambitious end up near seats, and so do the people willing to use one.
# §4 raises the odds of exactly three: the ambitious, the vain and the
# dutiful. Weighting the other vices up as well (an earlier pass did) put a
# Cruel or Bloodthirsty king on nearly every seat and left the whole map
# starving, which §13 says it must not be.
COURT_TRAIT_WEIGHTS = {"Power-Hungry": 3.0, "Proud": 2.5, "Righteous": 2.5}

# --- VIRTUE, VICE AND KARMA (§7) -------------------------------------------
# The moral sets. Greedy, Ruthless, Vengeful and Cold stay morally GRAY: no
# karma weight, their existing resource and combat edges untouched, and all
# of them legal for the protagonist. Only these four count as vice, and
# karma is the only thing in the sim that reads them as a set — no event
# anywhere asks whether someone is the villain.
VIRTUE_TRAITS = ("Righteous", "Humble", "Loyal")
VICE_TRAITS = ("Cruel", "Bully", "Power-Hungry", "Bloodthirsty")
KARMA_PER_MORAL_TRAIT = 2       # karma is SEEDED 2*(virtue) - 2*(vice)...

# ... and then moved by DEEDS, which dominate disposition over a long life.
KARMA_KILL_DEFENSELESS = -2     # a killing where the realms left no contest
KARMA_SPARE = 1                 # a beaten foe let up off the ground
KARMA_RESCUE = 2                # rescue or liberation
KARMA_DIED_DEFENDING = 3        # posthumous: the obituary and the grief

# The couplings — the whole moral economy, and all of it mechanical.
# Virtue is the luck lane; vice is the fast lane for wealth.
FORTUNE_CAP = 3                 # the streaky-luck counter stays small
FORTUNE_WEIGHT = 0.02           # what a point of it is worth on a die roll
KARMA_FORTUNE_DRIFT = 1         # fortune drifts a step toward sign(karma)/yr
KARMA_TRIBULATION = 0.0025      # karma/4 percentage points on a tribulation
KARMA_TRIBULATION_CAP = 0.05    # ... clamped to five of them
KARMA_ADVENTURE_TILT = 0.01     # the road: fateful encounters, or ambushes
KARMA_ADVENTURE_CAP = 0.05
VICE_SPOILS = 1                 # a vice trait skims every win and every haul
GRUDGE_VS_VICE_MULT = 1.5       # grudges bite deeper against a black ledger
GRUDGE_VS_VICE_AT = 0           # ... karma strictly under this

# THE FOUR VICES, each with a behaviour of its own.
# BULLY — fights only DOWNWARD (the tyranny of realms inverted) and shakes
# the juniors down for what they carry. Every victim keeps a grudge and a
# little of the insight adversity always pays.
BULLY_CHANCE = 0.5              # of a socialize year spent on a junior
BULLY_TAKE = (1, 3)             # resources taken off them
BULLY_GRUDGE = 2
BULLY_INSIGHT = 2
BULLY_SAME_SECT = 2.5           # one's own juniors are nearest to hand
BULLY_LINES = [
    "{bully} cornered {victim} behind the outer hall of {sect} and took "
    "{spoil}; a realm between them left nothing to argue with (+insight, "
    "grudge).",
    "{bully} stopped {victim} at the gate, went through their bundle and "
    "took {spoil} (+insight, grudge).",
    "{bully} beat {victim} in front of the junior hall over a debt no ledger "
    "records, and took {spoil} (+insight, grudge).",
]
# CRUEL — does not stop at winning. The victim carries the evidence.
CRUEL_MAIM_CHANCE = 0.5
CRUEL_MAIM_INSIGHT = 4
CRUEL_MAIM_GRUDGE = 3
# BLOODTHIRSTY — takes a duel past winning, and rides to any muster. Both
# knobs are deliberately small: a duel between equals kills one of the two
# more often than not, so a taste for them is a fast way to empty a sect.
BLOODTHIRSTY_LETHAL = 0.3       # an ordinary duel becomes a killing matter
BLOODTHIRSTY_DUEL_CHANCE = 0.1  # ... and they go looking for one
# The muster (§9): war_volunteer_weight() is the scan a campaign calls to
# find the cultivators who will ride to it, and a peacetime levy under a
# conscripting polity can take a Bloodthirsty cultivator's year on its own.
WAR_VOLUNTEER_TRAITS = {"Bloodthirsty": 3.0, "Greedy": 1.5, "Loyal": 1.5}
WAR_VOLUNTEER_NATIVE = 2.0
WAR_VOLUNTEER_FULL = 5.0        # weight at which someone is certain to go
SERVICE_CHANCE = 0.35           # a Bloodthirsty native answers the muster
SERVICE_PAY = (2, 5)
SERVICE_SKIRMISH = 0.4          # ... and the levies see some fighting
SERVICE_INSIGHT = 2

# THE CAMERA CONSTRAINT (§8) — the one deliberate breach of SIM FIRST in
# this layer. Documented at _mutate, where it is enforced.
CAMERA_BOUND_KINDS = ("friend", "sworn", "lover", "master", "disciple")
CAMERA_REROUTE = ("Vengeful", "Cold", "Broken")

# Rule style: five facets scored from the leader's traits plus situation.
# With the vices in the pool, every row of this table can now fire — a Cruel
# or Bully king is no longer a theoretical shape.
RULE_FACETS = ["BENEVOLENT", "EXTRACTIVE", "CRUEL", "NEGLECTFUL",
               "CONSCRIPTION"]
RULE_FACET_TRAITS = {
    "BENEVOLENT":   {"Righteous": 2, "Humble": 1, "Loyal": 1, "Scholarly": 1},
    "EXTRACTIVE":   {"Greedy": 2, "Power-Hungry": 2},
    "CRUEL":        {"Cruel": 2, "Bully": 1, "Bloodthirsty": 1, "Ruthless": 1},
    "NEGLECTFUL":   {"Broken": 2, "Cold": 1, "Ascetic": 1},
    "CONSCRIPTION": {"Bloodthirsty": 1},
}
RULE_FACET_EFFECTS = {
    # prosperity per settlement, unrest, ruler karma, ruler standing,
    # ruler resources (a range), army (a range)
    # Benevolence is priced a shade above §5's 0.4: a decent reign has to be
    # able to outrun the settling rate far enough to make a land visibly
    # PROSPEROUS, or §13's "at least one is prosperous-to-golden" never fires.
    "BENEVOLENT":   {"prosperity": 0.5,  "unrest": 0, "karma": 1,
                     "standing": 1},
    "EXTRACTIVE":   {"prosperity": -0.5, "unrest": 0, "karma": -1,
                     "resources": (2, 4)},
    "CRUEL":        {"prosperity": -0.4, "unrest": 2, "karma": -2},
    "NEGLECTFUL":   {"prosperity": -0.2, "unrest": 1, "karma": 0},
    "CONSCRIPTION": {"prosperity": -0.3, "unrest": 1, "karma": 0,
                     "army": (2, 5)},
}
STYLE_WORDS = {"BENEVOLENT": "benevolent", "EXTRACTIVE": "extractive",
               "CRUEL": "cruel", "NEGLECTFUL": "neglectful",
               "CONSCRIPTION": "conscripting"}
STYLE_QUIET = "quiet"
MAX_FACETS_PER_YEAR = 2         # a reign has at most two moods at once
NEGLECT_AGE = 70                # a MORTAL ruler past this age governs by
NEGLECT_AGE_SCORE = 1           # absence (§5) — and a cultivator-king only
                                # in the same last eighth of their own, far
                                # longer, life. A Core Formation king of 90
                                # is not a dotard.
NEGLECT_AGE_FRACTION = NEGLECT_AGE / BASE_LIFESPAN
CRACKDOWN_UNREST = 5            # a frightened throne reaches for the headsman,
CRACKDOWN_SCORE = 1             # but only one already willing to use it
POOR_TREASURY = 2               # an empty treasury tempts the tax collector
POOR_TREASURY_SCORE = 1
CONSCRIPTION_BASE = 2           # only at war, or under a Bloodthirsty ruler
UNREST_MAX = 12                 # the cap; revolts (§9) are what spends it
UNREST_DECAY = 1                # a benevolent or quiet year settles the land
SUCCESSION_UNREST_RELIEF = 2    # a new face on the seat buys a little peace
CRUEL_GRUDGE_MAX = 5            # cap on a subject's grudge against their ruler
# What a land still talks about. Risings, massacres and wars are filed here
# as one concrete clause each, and "The State of the Nine Lands" (§12) reads
# them back out at the end of a run.
UPHEAVAL_MEMORY = 60            # years an upheaval stays within living memory
UPHEAVAL_SHOWN = 2              # ... and how many of them a land is asked for
# Unrest, in words, for the same report — the number never leaves the sheet.
UNREST_WORDS = [(2, "quiet"), (5, "restive"), (9, "angry"),
                (UNREST_MAX + 1, "one bad harvest from a rising")]
# A ruler doing the same thing for thirty years is not news every year: a
# facet writes a line when it is newly dominant, and only sometimes after.
RULE_LINE_REPEAT_CHANCE = 0.2
# A century-long reign draws on these every few years, so each pool is wide
# enough that a reader following one country does not read the same four
# sentences over and over.
RULE_LINES = {
    "BENEVOLENT": [
        "{ruler} opened the granaries of {domain} through a hard winter.",
        "{ruler} cut the levies on {domain} and paid for the dikes out of "
        "the treasury.",
        "{ruler} heard petitions in person all year; the assessors of "
        "{domain} were whipped for false measures.",
        "{ruler} rebuilt the roads of {domain} and fed the work gangs at "
        "the crown's expense.",
        "{ruler} bought grain abroad at a loss and sold it cheap in "
        "{domain}; the treasury is thinner for it.",
        "{ruler} had the boundary stones of {domain} reset and gave the "
        "disputed strips to whoever had been ploughing them.",
        "{ruler} pardoned the debtors of {domain} and burned the tally "
        "sticks in the square.",
        "{ruler} paid the bride-price of the poorest houses of {domain} "
        "out of the crown's own purse.",
        "{ruler} sat with the physicians through a fever season in "
        "{domain} and buried the dead by name.",
        "{ruler} dug wells the length of {domain} and charged nothing for "
        "the water.",
    ],
    "EXTRACTIVE": [
        "{ruler} tripled the tax on herds and hearths; the villages of "
        "{domain} go hungry.",
        "{ruler} seized the salt trade of {domain} for the treasury.",
        "{ruler} sold the harvest of {domain} abroad and kept the silver.",
        "{ruler} set a new toll on every bridge and ford in {domain}.",
        "{ruler} called in every debt owed to the crown in {domain} at "
        "once, and took land where there was no coin.",
        "{ruler} farmed out the taxes of {domain} to bidders and asked no "
        "questions about the collecting.",
        "{ruler} took the temple plate of {domain} for the mint.",
        "{ruler} declared the forests of {domain} crown land and fined "
        "the villages for their own firewood.",
        "{ruler} weighed the coin of {domain} short and spent it at full "
        "value.",
    ],
    "CRUEL": [
        "{ruler} answered the complaints of {domain} with the headsman.",
        "{ruler} burned a village of {domain} for a rumour of sedition.",
        "{ruler} hung the tax-defaulters of {domain} along the roads.",
        "{ruler} took hostages from every house of note in {domain}.",
        "{ruler} had the elders of a district of {domain} beaten in the "
        "square for a petition badly worded.",
        "{ruler} put out the eyes of a magistrate of {domain} for a "
        "judgement that displeased the court.",
        "{ruler} quartered the guard on {domain} and let them take what "
        "they liked.",
        "{ruler} kept the sons of {domain}'s notables at court, and made "
        "sure the fathers knew why.",
        "{ruler} drowned a village headman of {domain} for arriving late "
        "with the tally.",
    ],
    "NEGLECTFUL": [
        "{ruler} let the granaries of {domain} stand unrepaired another year.",
        "{ruler} read no petition out of {domain} all year.",
        "{ruler} kept to the inner court while the roads of {domain} washed "
        "out.",
        "{ruler} left the assize of {domain} unheld; the quarrels waited "
        "another year, and some were settled with knives.",
        "{ruler} left the seat of {domain} in the hands of stewards and "
        "asked them nothing.",
        "{ruler} let the river dikes of {domain} go one more season "
        "without a work gang.",
        "{ruler} did not once leave the capital; {domain} saw nothing of "
        "its ruler all year.",
    ],
    "CONSCRIPTION": [
        "{ruler} called up the levies of {domain}; the fields went unsown.",
        "{ruler} took one man in five from the villages of {domain} for the "
        "muster.",
        "{ruler} emptied the gaols of {domain} into the ranks and gave "
        "them spears.",
        "{ruler} set the smiths of {domain} to arrowheads and nothing "
        "else all year.",
        "{ruler} mustered the herdsmen of {domain} with their own horses "
        "and did not say for how long.",
    ],
}

# Edicts — the senseless rules. Each land has a god, so "a foreign god" is
# concrete: the template draws one from a DIFFERENT land.
LAND_GODS = {
    "Middle Plain":   "the Nine-Gated Sovereign",
    "Spice Isles":    "the Clove Mother",
    "Coral Strand":   "the Reef Serpent",
    "Sky Steppe":     "the Eternal Blue",
    "Wolf Steppe":    "the Sky Wolf",
    "Thousand Lakes": "the Lake Smith",
    "Birch Marches":  "the Birch Maiden",
    "Glacier Coast":  "the Ice Widow",
    "Ashen Fjords":   "the Ash Father",
    "River Kingdoms": "the River Mother",
    "Lotus Delta":    "the Lotus Sleeper",
    "Sunset Plateau": "the Sun Behind the Mountain",
    "Salt Wastes":    "the Salt Mother",
}
EDICT_TEMPLATES = [
    ("the dusk silence", "that no voice be raised after dusk"),
    ("the colour law", "that every subject wear the ruler's colour"),
    ("the ban on music", "that no music be played in any house"),
    ("the laughter tax", "that laughter in public be taxed"),
    ("the mirror-breaking", "that every mirror be broken"),
    ("the law of titles",
     "that commoners be addressed only by title, never by name"),
    ("the ban on beards", "that no man wear a beard longer than his thumb"),
    ("the night curfew", "that no door stand open between dusk and dawn"),
    ("the foreign rite",
     "that every household burn incense to {god} of the {land}"),
]
EDICT_CHANCE_PER_POINT = 0.04   # points = Proud + Cold + vice traits
EDICT_MAX_ACTIVE = 3
EDICT_PROSPERITY = -0.2         # per active edict per year
EDICT_UNREST = 1                # per active edict per year
EDICT_REPEAL_CHANCE = 0.30      # a non-Stubborn ruler, after a good year
MANDATE_CHANCE = 0.5            # a liege's edict reaching each vassal

# --- THE THRONE AS AN EXIT (§4, §9) ----------------------------------------
# RULING LOCKS CULTIVATION. A ruler's action phase is replaced by a single
# RULE action: no cultivate, no seclude, no adventure, no teach, and no qi at
# all. Their realm still counts in full — that is exactly what keeps a Core
# Formation king on his seat for a century. The only insight a throne earns is
# bought with governance adversity.
# How a reign began, kept on the agent and spent in the obituary: "Was King
# of the Wolf Steppe for thirty-one years, raised to it by a rising, and was
# thrown down from the seat in Y142."
THRONE_CAME_CLAIM = "having claimed it at a vacancy"
THRONE_CAME_CONTEST = "having claimed it over a rival"
THRONE_CAME_INVITE = "invited to it by its own court"
THRONE_CAME_USURP = "having taken it by force"
THRONE_CAME_RISING = "raised to it by a rising"

RULE_MILESTONE = 10             # a reign is remarked on every ten years
RULE_LINE_CHANCE = 0.10         # ... and otherwise only now and then
RULE_YEAR_LINES = [
    "{ruler} held the assize at {seat} and gave judgement on the quarrels "
    "of {domain}.",
    "{ruler} spent the year on the roads of {domain}, court and baggage "
    "train behind.",
    "{ruler} received the envoys of a neighbouring land at {seat}.",
    "{ruler} named an heir out of the household at {seat}; the court took "
    "note of it.",
    "{ruler} kept the granary accounts of {domain} in person all year.",
    "{ruler} put down a quarrel between two houses of {domain} before it "
    "could become a blood feud.",
    "{ruler} sat through the tax reckoning of {domain} and sent three "
    "assessors away in irons.",
    "{ruler} married a cousin of the house into a neighbouring court; "
    "{domain} calls it a good year's work.",
    "{ruler} rebuilt the walls of {seat} and made the merchants pay half.",
    "{ruler} held a great hunt out of {seat}; the notables of {domain} "
    "came, and so did their grievances.",
    "{ruler} had the laws of {domain} read out in every market, most of "
    "them for the first time in a generation.",
    "{ruler} refused an embassy at {seat} and would not say why.",
]
# The cultivation lock, said out loud once a decade: a cultivator on a throne
# is a cultivator standing still.
RULE_LOCK_LINES = [
    "{ruler} has not sat in meditation for {years}; a throne gives no qi, "
    "and none has come.",
    "{ruler} let another decade of the path go by unwalked — {years} on the "
    "seat, and not a year of it spent cultivating.",
    "The disciples who entered {sect} with {ruler} are elders now; {years} "
    "of governing has left that foundation exactly where it stood.",
    "{ruler} kept the seal of {domain} another ten years, and the sword in "
    "its wrappings; {years} on the seat and counting.",
    "{ruler} has spent {years} settling other people's quarrels; the "
    "cultivation of {sect} waits where it was left.",
    "Another ten years of governing {domain} went by; {ruler} is "
    "{years} older and not one breath further along the path.",
]
RULE_MORTAL_LINES = [
    "{ruler} has held the seat of the {polity} for {years}.",
    "{ruler} completed {years} on the seat; {domain} has known no other "
    "hand for a generation.",
    "{years} on the seat, and the assizes of {domain} still open in "
    "{ruler}'s name.",
    "The court at {seat} marked {years} of {ruler}'s rule; the older "
    "stewards can remember no other.",
]
# Insight bought with governance adversity, by kind. §4 names a revolt
# survived and a war lost as the two largest, and they are priced that way:
# a country that rose against you, and an army that came home beaten, teach a
# throne more than anything else it will ever meet.
GOVERNANCE_INSIGHT = {"petition": 2, "betrayal": 3, "usurpation": 5,
                      "deposition": 6, "assassination": 4, "revolt": 7,
                      "war_lost": 8}

# POWER CORRUPTS: each ruling year, a small chance the seat walks its holder
# one step down the ladder — the only path in the sim that HANDS OUT vice,
# which is why the camera constraint (§8) is enforced inside _mutate rather
# than at the roll.
CORRUPTION_LADDER = [None, "Greedy", "Power-Hungry", "Cruel"]
CORRUPTION_CHANCE = 0.008           # per ruling year
CORRUPTION_PER_EXTRACTION = 0.0015   # ... raised by years of taking
CORRUPTION_EXTRACTION_CAP = 0.02
CORRUPTION_VIRTUE_MULT = 0.25       # Righteous/Humble/Loyal hold the line
CORRUPTION_VIRTUES = ("Righteous", "Humble", "Loyal")

# CLAIMS (§9, secular succession). A vacant seat is a door. The stalled, the
# aging, the greedy and the ambitious walk through it; the Righteous only when
# the land under it is visibly suffering (the idealist takeover). A stranger
# has no claim at all: it takes blood in that land, or a grudge against that
# court.
CLAIM_MIN_REALM = 2
CLAIM_MIN_AGE = 20
CLAIM_TRAIT_WEIGHTS = {"Power-Hungry": 4.0, "Greedy": 2.0}
CLAIM_STALLED = 2.5             # the door out of a path that has stopped
CLAIM_AGING_AT = 0.55           # fraction of lifespan: the path is behind them
CLAIM_AGING = 2.0
CLAIM_NATIVE = 2.0
CLAIM_GRUDGE = 2.0
CLAIM_RIGHTEOUS = 3.5
CLAIM_SUFFERING_AT = 4.0        # prosperity at or under which a land suffers
CLAIM_SUFFERING_UNREST = 6      # ... or unrest at or over which it does
CLAIM_REALM_DAMP = 0.50         # per realm above the second: the higher a
                                # cultivator has climbed, the less a mortal
                                # seat is worth stepping off the path for
CLAIM_CHANCE_PER_POINT = 0.20
CLAIM_CHANCE_MAX = 0.9
CLAIM_CONTEST_CHANCE = 0.35     # two claims pressed at once
CLAIM_CONTEST_STANDING = 2
CLAIM_CONTEST_NOISE = 6.0

# INVITATION AND REFUSAL. A court left in disarray looks outside for a ruler
# and offers the seat to a famous or native cultivator — who is entirely free
# to refuse it, and often does. Refusals are remembered in the obituary.
INVITE_CHANCE = 0.28            # a heirless court looks outside at all
INVITE_UNREST = 4               # an unquiet one looks harder
INVITE_UNREST_BONUS = 0.18
INVITE_MIN_REALM = 2
INVITE_MIN_STANDING = 8
INVITE_NATIVE = 2.5
INVITE_FAMOUS = 2.0
INVITE_STANDING_WEIGHT = 0.4
INVITE_REFUSE_BASE = 0.35
INVITE_REFUSE_TRAITS = {"Ascetic": 0.35, "Scholarly": 0.15, "Cold": 0.15,
                        "Humble": 0.15, "Reckless": 0.10}
INVITE_ACCEPT_TRAITS = {"Power-Hungry": 0.40, "Greedy": 0.25, "Proud": 0.20,
                        "Charming": 0.15, "Righteous": 0.10}
INVITE_REFUSE_PER_REALM = 0.14  # a Nascent Soul does not sit on a mortal chair

# USURPATION: the path onto a throne that does not wait for a funeral. Rare,
# and settled by the tyranny of realms — a mortal king cannot hold his seat
# against a Core Formation cultivator, and a cultivator-king can.
USURP_CHANCE = 0.06             # yearly, across all nine lands
USURP_MIN_REALM = 3
USURP_TRAIT_WEIGHTS = {"Power-Hungry": 4.0, "Ruthless": 2.0, "Vengeful": 2.0,
                       "Greedy": 1.5, "Proud": 1.0}
USURP_GRUDGE_WEIGHT = 1.5       # per point of grudge against that court
USURP_NATIVE = 1.5
USURP_OUTMATCHED = 0.25         # few storm a seat they cannot take
USURP_GAP_CERTAIN = 2           # two realms above the throne: not a fight
USURP_GAP_ODDS = 0.85           # one realm above: the household guard dies
USURP_GUARD = 20.0              # what a seat is worth in its own defence
USURP_GUARD_PER_ARMY = 0.5
USURP_ODDS = (0.10, 0.90)
USURP_KILL_CHANCE = 0.5         # a taken seat does not always keep its holder
USURP_KILL_RUTHLESS = 0.85
USURP_KILL_RIGHTEOUS = 0.15
USURP_SPARE_KARMA = KARMA_SPARE  # §7: sparing a beaten foe
USURP_KARMA = -2                # ... and taking a seat by force
USURP_FAIL_INSIGHT = 5
USURP_FAIL_DEATH = 0.35

# DEFIANCE: a vassal keeps the tribute. This is the betrayal §4 names as one
# of the adversities a throne can actually learn from, and a standing
# defiance is what a war of vassalage grows out of (§9).
DEFIANCE_CHANCE = 0.025
DEFIANCE_TRAITS = ("Proud", "Power-Hungry", "Ruthless", "Stubborn")
DEFIANCE_GRUDGE_WEIGHT = 0.5
DEFIANCE_UNREST = 2
DEFIANCE_MEMORY = 12            # years a kept tribute stays an open quarrel

# ABDICATION: the way off a throne that nobody forces. An Ascetic or Broken
# ruler, or one grown old and weary, lays the seat down — and a cultivator
# walks back up the mountain with their qi exactly where they left it and a
# world that has moved on without them.
ABDICATE_MIN_REIGN = 6
# These four were halved in the tuning pass: abdication was carrying half of
# every exit from a throne, which left §13's "2-5% of a cohort ends its story
# on a throne" short — most cultivator-kings were walking away from the seat
# before it could kill them.
ABDICATE_TRAIT_CHANCE = 0.002    # an Ascetic or Broken ruler
ABDICATE_TRAITS = ("Ascetic", "Broken")
ABDICATE_WEARY_AT = 0.80        # fraction of lifespan: old and weary
ABDICATE_WEARY_CHANCE = 0.007
ABDICATE_LONG_REIGN = 30
ABDICATE_LONG_CHANCE = 0.0015
ABDICATE_CULTIVATOR_CHANCE = 0.001  # the mountain never stops calling
ABDICATE_MORTAL_MULT = 0.4      # a mortal notable has nowhere to go but
                                # exile, and knows it; the mountain is only
                                # waiting for the cultivator
ABDICATE_HOLD_TRAITS = ("Proud", "Stubborn", "Greedy")
ABDICATE_HOLD_MULT = 0.35
RETURN_INSIGHT = 3              # what the years on the seat were worth

# --- CONSEQUENCE EVENTS (§9): REVOLT, ASSASSINATION, WAR -------------------
# Until now unrest was a gauge with no valve: a bad court pinned it at the cap
# and only a funeral ever spent it. These are the three ways a country answers
# back, and all three are settled by the same tyranny of realms as every other
# contest in the sim — which is exactly why a cultivator-king is a different
# problem from a bad king.

# REVOLT. Over the threshold, a country can rise in any year. It looks for a
# CHAMPION first — someone carrying a grudge against that court, or a
# Righteous native of it — because a rising without one is a mob.
REVOLT_THRESHOLD = 9            # unrest over which a country can rise at all
REVOLT_CHANCE_PER_UNREST = 0.0035   # per point of unrest above the threshold
REVOLT_MIN_REALM = 2            # a Qi Condensation disciple leads nothing
REVOLT_MIN_AGE = 18
REVOLT_TRAIT_WEIGHTS = {"Righteous": 4.0, "Vengeful": 2.0, "Power-Hungry": 2.0,
                        "Proud": 1.5, "Reckless": 1.5, "Bloodthirsty": 1.5}
REVOLT_HOME_WEIGHT = 2.5        # blood in that land
REVOLT_GRUDGE_WEIGHT = 2.0      # ... or a grudge against that court
REVOLT_CHAMPION_CHANCE = 0.75   # a willing champion actually rides
# The contest: the household guard, the realm above it, and the levies.
REVOLT_GUARD = 16.0
REVOLT_GUARD_PER_REALM = 12.0
REVOLT_GUARD_PER_ARMY = 0.45
REVOLT_UNREST_HELP = 1.2        # a hungrier country puts more men in the road
REVOLT_ODDS = (0.10, 0.95)
REVOLT_GAP_ODDS = 0.9           # a realm over the throne: the tyrant falls
REVOLT_GAP_CERTAIN = 2          # two realms over it: not a fight at all
REVOLT_UNDER_ODDS = 0.12        # ... and a realm UNDER it, a whole country at
                                # your back is still not nearly enough
REVOLT_MOB_ODDS = 0.10          # a leaderless uprising, against a mortal seat
REVOLT_MOB_PER_UNREST = 0.015
REVOLT_ARMY_LOSS = 0.4          # what putting one down (or losing) costs
REVOLT_KARMA = KARMA_RESCUE     # §7: liberation
REVOLT_RELIEF = 0.8             # what a country eats the year the seat falls
REVOLT_INSIGHT = 2              # what the survivors of a rising learn
REVOLT_REFUSE_BASE = 0.20       # the champion is offered the seat, and may
                                # refuse it; a local notable takes it instead
REVOLT_KILL_CHANCE = 0.55       # a thrown-down ruler does not always live
REVOLT_KILL_RUTHLESS = 0.85
REVOLT_KILL_RIGHTEOUS = 0.2
REVOLT_FAIL_INSIGHT = 5         # adversity, as ever
REVOLT_FAIL_DEATH = 0.45
REVOLT_FAIL_UNREST = 3          # a crushed rising still spends some of it
REVOLT_FAIL_PROSPERITY = -0.4
TYRANT_BREAKER = "Tyrant-Breaker"
# THE MASSACRE. A mortal tyrant falls to any realm-2 champion; a
# cultivator-king turns the same rising into a killing field. Prosperity and
# the ruler's ledger both collapse, and the survivors come out of it with
# insight and grudges — adversity is the insight engine here as everywhere.
MASSACRE_PROSPERITY = -1.6
MASSACRE_KARMA = -8
MASSACRE_UNREST = 4             # terror buys a few quiet years, and no more
MASSACRE_INSIGHT = 4
MASSACRE_GRUDGE = 3
REVOLT_WITNESS_CHANCE = 0.5     # a native whose own people were in it
MASSACRE_DEAD = (400, 9000)     # commoners; chronicle colour, not agents

# ASSASSINATION. §9 sets the bar at karma <= -4, which was written before the
# rule facets were: a facet moves a ledger by 1-2 points A YEAR, so any merely
# bad reign clears -4 inside a decade and a long one ends near -100. The bar
# below is the same intent on the scale the sim actually uses — a deeply evil
# reign, not a disappointing one — and at most one attempt is made anywhere in
# the world in a year, which is what keeps knives rarer than risings (§13).
ASSASSIN_KARMA = -30            # the bar, on the scale rule facets produce
ASSASSIN_CHANCE = 0.018         # one roll a year across all nine lands
ASSASSIN_PER_KARMA = 0.0005     # ... blacker ledgers draw more knives
ASSASSIN_CHANCE_MAX = 0.055
ASSASSIN_REALM_GAP = 1          # grudge-holders within one realm of the seat
ASSASSIN_MIN_GRUDGE = 2
ASSASSIN_TRAIT_WEIGHTS = {"Vengeful": 3.0, "Ruthless": 2.0,
                          "Bloodthirsty": 2.0, "Cold": 1.5, "Righteous": 1.0}
ASSASSIN_GRUDGE_WEIGHT = 1.5
ASSASSIN_BASE = 0.45
ASSASSIN_PER_REALM = 0.25       # the knife's realm against the seat's
ASSASSIN_CAUTIOUS = 0.25        # a frightened ruler sleeps behind guards
ASSASSIN_PER_ARMY = 0.006
ASSASSIN_ODDS = (0.1, 0.85)
ASSASSIN_CAUGHT = 0.6           # a failed assassin rarely walks out
ASSASSIN_FAIL_INSIGHT = 4
ASSASSIN_UNREST = 2

# WAR. Between edge-adjacent sovereigns, rarely across a corner. A restless
# ruler with an army starts one; so does a court left weak by a contested
# succession, and so does a vassal that has kept the tribute one year too
# many. The campaign itself is abstract — 1-3 years, prosperity down on both
# sides, conscripts dead by the thousand as chronicle colour — but the
# cultivators who ride to it are entirely real.
WAR_CHANCE = 0.035              # one roll a year across all nine lands
WAR_MIN_ARMY = 10
WAR_TRAIT_WEIGHTS = {"Bloodthirsty": 3.0, "Power-Hungry": 2.5, "Greedy": 1.0,
                     "Proud": 1.0, "Cruel": 1.0}
WAR_ARMY_WEIGHT = 0.05          # per soldier over the minimum
WAR_CORNER_CHANCE = 0.12        # a war fought across a corner of the grid
WAR_CRISIS_YEARS = 8            # how long a contested seat looks like prey
WAR_CRISIS_WEIGHT = 3.0
WAR_DEFIANCE_WEIGHT = 4.0       # the seam a war of vassalage grows from
WAR_WEAK_PREY = 1.5             # per realm the defender stands below
WAR_LENGTH = (1, 3)
WAR_PROSPERITY_ATT = -0.35      # a campaign costs the invader too
WAR_PROSPERITY_DEF = -0.7
WAR_UNREST = 1
WAR_ARMY_LOSS = (0.10, 0.30)    # fraction of the levies spent per campaign year
WAR_CONSCRIPTS_DEAD = (300, 6000)
WAR_RULER_SCORE = 10.0          # per realm the ruler stands above mortal
WAR_CULTIVATOR_SCORE = 0.35     # a joined cultivator's power, on the scales
WAR_SCORE_NOISE = 0.30          # the friction that decides most campaigns
WAR_BATTLE_DEATH = 0.09         # per campaign year, per cultivator present
WAR_BATTLE_INSIGHT = 3
WAR_BATTLE_SPOILS = (2, 7)
WAR_SPOILS_CHANCE = 0.5         # not every season's army carries off enough
WAR_TRIBUTE = (6, 18)           # what a beaten court hands over
WAR_LOSER_UNREST = 3
WAR_WINNER_PROSPERITY = 0.4     # the spoils reach the villages, a little
WAR_OUTCOME_WEIGHTS = {"tribute": 5.0, "region": 3.0, "vassalage": 2.0}
WAR_DECLARE_LINES = [
    "{att} marched on {def_dom}; the border villages were burning before "
    "the first snow.",
    "{att} crossed into {def_dom} without an envoy sent ahead of the army.",
    "{att} declared the old border of {def_dom} a lie and sent the levies "
    "to correct it.",
    "{att} answered an insult nobody outside the court remembered with an "
    "invasion of {def_dom}.",
]
WAR_VASSAL_DECLARE_LINES = [
    "{att} took the field against {def_ruler}, who had kept the tribute of "
    "{def_dom} and sent no word with it.",
    "{att} called the levies to bring {def_dom} back under the old oath.",
]
WAR_CAMPAIGN_LINES = [
    "The war over {def_dom} ground through another year; some {dead} "
    "conscripts are in the ground and both countries are the poorer.",
    "Another campaigning season over {def_dom}: {dead} dead of the levies, "
    "the fields unsown on both sides of the border.",
    "The armies wintered where they stood after a year in {def_dom}; {dead} "
    "of the conscripts did not winter anywhere.",
]

# SECT HEADS UNDER THE POLITICS LAYER (§11). Headship is rulership-lite: the
# head keeps cultivating, but their character tilts the sect's richness a few
# points either way and drifts the juniors' standing with it. Under a
# vice-heavy head the Righteous and the Humble DEFECT — a voluntary exit that
# does not end a career, and that seeds exactly the cross-sect grudges the
# feud arithmetic is already counting.
SECT_TILT_PER_TRAIT = 0.03      # per virtue (up) or vice (down) the head holds
SECT_TILT_CAP = 0.09
SECT_STANDING_DRIFT = 0.10      # chance per junior per year, either way
SECT_JUNIOR_REALM = 2           # who counts as a junior for the drift
DEFECT_CHANCE = 0.010           # per vice trait the head carries, per year
DEFECT_TRAITS = ("Righteous", "Humble")
DEFECT_GRUDGE_CHANCE = 0.5      # ... or simply a grudge against the head
DEFECT_MIN_AGE = 20
DEFECT_MIN_REALM = 2
DEFECT_STANDING_COST = 2
DEFECT_GRUDGE = 3               # what the defector carries out of the gate
DEFECT_WELCOME_CHANCE = 0.6     # somebody in the new sect vouches for them
DEFECT_LINES = [
    "{who} left {old} for {new}, saying they would not spend another year "
    "under {head}.",
    "{who} walked out of {old} in the night and was taken in at {new}; the "
    "elders of {old} called it theft.",
    "{who} broke with {head} in front of the assembled disciples and took "
    "their name off the register of {old} for {new}.",
]

# --- THE CONTACT SURFACE: where the common people reach the sim (§§9-10) ---
# Commoners never become agents. Their lives touch the simulation at exactly
# four points: the recruitment gate, the family stipend, the road, and the
# petition. Everything below is that contact surface.

# 1. THE GATE. A recruit's childhood is already on their sheet: a hard home
# hands them adversity pre-banked and a grudge; a rich one hands them silver.
MISRULED_HOME_AT = 3.0          # prosperity at or under which a home is misruled
PROSPEROUS_HOME_AT = 7.0        # ... and at or over which it is a good place
MISRULED_RESOURCES = 2          # starting resources a hungry childhood costs
MISRULED_BURDEN = 1
MISRULED_INSIGHT = 2            # adversity, banked before year one
MISRULED_GRUDGE = (1, 2)        # grudge intensity against the home's ruler
PROSPEROUS_RESOURCES = (2, 4)   # a family that can outfit its child

# 2. THE STIPEND. A prosperous home keeps sending silver while it can still
# matter; a home under the levies sends bad news instead.
STIPEND_REALM = 2               # realm at or below which a stipend still counts
STIPEND = 1                     # resources per year
CONSCRIPTION_GRUDGE_CHANCE = 0.25   # a brother taken for the muster

# 3. THE ROAD. Every adventure goes SOMEWHERE. The centre draws hardest, the
# lands touching it next, the far corners least; a cultivator also drifts
# home. The destination's prosperity reshapes the risk table: hungry lands
# yield bandits, refugees and the tyrant's men, rich ones auctions and
# patrons.
ADVENTURE_LAND_WEIGHTS = {"center": 4.0, "edge": 2.0, "corner": 1.0}
ADVENTURE_HOME_BOOST = 1.5      # the roads a cultivator already knows
ROAD_HARD_AT = 3.5              # destination prosperity: below this, misruled
ROAD_RICH_AT = 7.0              # ... and at or above this, golden
ADVENTURE_RISK_SHIFT = {"harsh": -0.06, "settled": 0.0, "rich": 0.05}
# The two bad bands of the road roll. The grave is divided by the traveller's
# realm — the wilds threaten the strong far less — and both are what the
# funnel is most sensitive to: adventure is where the insight is, so a first
# realm that has to go looking for it is also the realm that dies out there.
ADVENTURE_DEATH = 0.015
ADVENTURE_NEAR_DEATH = 0.11
ADVENTURE_RESCUE_KARMA = KARMA_RESCUE   # §7: rescue or liberation
ADVENTURE_RESCUE_CHANCE = 0.5   # ... the rest of the time they only witness it
ADVENTURE_PATRON_CHANCE = 0.4   # a rich land's spoils come with a name attached
ADVENTURE_SCENES = {
    "harsh": {
        # A death cause, spliced into the obituary: "...; <cause>."
        "death": [
            "cut down by bandits on the road to {where} in the {land}",
            "killed by the tyrant's men outside {where} in the {land}",
            "lost in the burned-out country beyond {where} in the {land}",
        ],
        "near_death": [
            "{who} was ambushed by bandits on the road to {where} in the "
            "{land} and barely lived through it (+insight).",
            "{who} fell into the hands of the tyrant's men outside {where} "
            "and crawled away from it (+insight).",
            "{who} was left for dead in a burned village of the {land} "
            "(+insight).",
        ],
        "quiet": [
            "Walked the hungry roads of the {land}: empty granaries, closed "
            "doors, nothing to be had.",
            "Found {where} in the {land} stripped bare — no work, no "
            "masters, no fortune.",
        ],
        "spoils": [
            "Took a bandit camp on the {land} road and kept what they had "
            "stolen (+resources).",
            "Hired out as an escort for the families fleeing {where}; they "
            "paid in the last of their silver (+resources).",
        ],
        # In a misruled land the insight is sometimes bought by a deed (and
        # that is logged), and the rest of the time only witnessed.
        "insight": [
            "Watched the tax collectors empty {where} in the {land} and "
            "could do nothing about it (+insight).",
            "Walked the {land} past the gallows the crown had left standing "
            "along the road (+insight).",
            "Slept in a refugee camp outside {where} and listened all night "
            "(+insight).",
        ],
        "rescue": [
            "{who} brought a column of refugees out of {where} in the {land} "
            "and saw them across the border (+insight).",
            "{who} stood between the tax collectors of the {land} and the "
            "villagers of {where} (+insight).",
        ],
        "treasure": [
            "{who} looted a warlord's cache in the ruins above {where} in "
            "the {land}.",
            "{who} took a dead magistrate's strongbox out of {where} and "
            "nobody in the {land} asked after it.",
        ],
        "meeting": [
            "{who} crossed paths with {other} on the refugee road out of the "
            "{land}; they parted as {kind}s.",
        ],
    },
    "settled": {
        "death": [
            "died on an adventure in the wilds of the {land}",
            "vanished in the back country beyond {where} in the {land}",
        ],
        "near_death": [
            "{who} barely survived a brush with death in the wilds of the "
            "{land} (+insight).",
            "{who} was mauled by something in the hills above {where} and "
            "walked out of the {land} alone (+insight).",
        ],
        "quiet": [
            "Walked the roads of the {land} a long while and came back with "
            "nothing.",
            "Sat out a wet season in {where} in the {land}; nothing found.",
        ],
        "spoils": [
            "Cleared a beast's den near {where} in the {land} for the bounty "
            "(+resources).",
            "Ran a caravan road through the {land} for a merchant's fee "
            "(+resources).",
        ],
        "insight": [
            "An epiphany on the road through the {land} (+insight).",
            "A month alone on the passes above {where} clarified something "
            "(+insight).",
        ],
        "treasure": [
            "{who} found a fortuitous treasure in a ruined cave in the "
            "{land}.",
            "{who} opened a sealed tomb under {where} in the {land} and came "
            "out rich.",
        ],
        "meeting": [
            "{who} crossed paths with {other} on the road through the "
            "{land}; they parted as {kind}s.",
        ],
    },
    "rich": {
        "death": [
            "killed over an auction lot in {where} in the {land}",
            "died when a spirit-beast hunt out of {where} went wrong",
        ],
        "near_death": [
            "{who} was ambushed for their purse leaving the auction at "
            "{where} and barely lived (+insight).",
            "{who} was beaten half to death by a patron's guards in {where} "
            "in the {land} (+insight).",
        ],
        "quiet": [
            "Spent the season at the fairs of {where} in the {land}; much "
            "seen, nothing gained.",
            "Priced out of every lot at the {where} auctions all season.",
        ],
        "spoils": [
            "Sold beast cores at the market in {where} at a fair season's "
            "price (+resources).",
            "A patron of {where} in the {land} paid well for a season's "
            "escort work (+resources).",
        ],
        "insight": [
            "Sat a season with the scholars of {where} in the {land} "
            "(+insight).",
            "Read a borrowed jade slip through the long winter of the {land} "
            "(+insight).",
        ],
        "treasure": [
            "{who} outbid the merchants of {where} for a cracked jade slip "
            "out of a dead man's estate.",
            "{who} won a spirit herb at the {where} auction in the {land} "
            "for a tenth of its worth.",
        ],
        "meeting": [
            "{who} met {other} at the auction house of {where} in the "
            "{land}; they parted as {kind}s.",
        ],
    },
}

# 4. THE PETITION. A settlement below PETITION_AT sends riders to a sect:
# the one interface between the spiritual exemption and the secular world.
# It is a mission hook, not a flood — at most one new plea a year.
PETITION_AT = 3.0               # prosperity under which a village begs
PETITION_CHANCE = 0.35          # yearly chance a new plea is sent at all
PETITION_MAX_OPEN = 3           # pleas on the table at once
PETITION_COOLDOWN = 12          # years before the same village begs again
PETITION_LAPSE = 5              # years an unanswered plea stays on the table
PETITION_MIN_REALM = 2          # a Qi Condensation disciple is not sent
PETITION_ANSWER_CHANCE = 0.5    # per open plea per year, if anyone will go
PETITION_TRAIT_WEIGHTS = {"Righteous": 4.0, "Proud": 2.0, "Charming": 1.5,
                          "Greedy": 1.5, "Reckless": 1.5}
PETITION_HOME_WEIGHT = 2.5      # a native answers their own land first
PETITION_GRUDGE_WEIGHT = 2.0    # so does anyone who already hates that court
PETITION_OPPOSITION = 18.0      # the magistrate's men
PETITION_OPPOSITION_PER_REALM = 10.0    # ... and whoever sits above them
PETITION_OPPOSITION_PER_ARMY = 0.4
PETITION_ODDS = (0.15, 0.9)
PETITION_GAIN = 1.5             # prosperity a rescued village recovers
PETITION_REPRISAL = 0.5         # ... and what a failed rescue costs it
PETITION_KARMA = KARMA_RESCUE   # §7: rescue or liberation
PETITION_STANDING = 3
PETITION_UNREST = 1
PETITION_FAIL_INSIGHT = 4       # adversity, as ever
PETITION_DEATH_CHANCE = 0.2     # a beaten champion does not always walk away
# (what the village begs for, what the answer looks like, what the
# cultivator went there for — the last is used when they fail)
PETITION_MISSIONS = [
    ("to drive the tax collectors out of {where}",
     "drove the tax collectors out of {where} and burned their ledgers",
     "the tax collectors"),
    ("to answer for the magistrate of {where}",
     "dragged the magistrate of {where} out of his hall before the whole "
     "village",
     "the magistrate"),
    ("to kill the beast the crown had left to eat the herds of {where}",
     "killed the beast that had been eating the herds of {where} while the "
     "crown did nothing",
     "the beast"),
    ("to open the sealed granary of {where}",
     "broke open the sealed granary of {where} and fed the village through "
     "the winter",
     "the sealed granary"),
    ("to call the press-gangs of {where} to account",
     "hanged the press-gang captain of {where} from his own gatepost",
     "the press-gangs"),
]

MAIM_EPITHETS = ["One-Armed", "One-Eyed", "Scarred", "Iron-Boned",
                 "Ash-Handed", "Half-Lame"]

SECT_SPECS = [
    ("Azure Peak Sect", 1.15),
    ("Crimson Lotus Pavilion", 1.05),
    ("Iron Gorge Hall", 0.95),
    ("Silent River Monastery", 1.0),
]

FRIENDLY_KINDS = {"friend", "sworn", "ally", "master", "disciple", "lover"}
HOSTILE_KINDS = {"rival", "grudge"}

REL_DISPLAY = {
    "friend": "friend", "sworn": "sworn", "ally": "ally",
    "master": "master", "disciple": "disciple", "lover": "lover",
    "rival": "rival", "grudge": "enemy",
}

# --- THE PLAYABLE LAYER (VII): TWO CLOCKS ----------------------------------
# The world thinks in years; the player lives in seasons. Every year is now
# PLANNED (the agenda below is rolled at year start), PLAYED (four season
# sub-steps) and CLOSED (the old resolution phase). Batch and observer modes
# run all three in one call, which is why there is only one code path.
SEASONS = ("spring", "summer", "autumn", "winter")
NPC_ACTION_SEASON = "spring"    # an NPC's ONE action, read as "what they
                                # mostly did that year"
# Which season each event of the year is stamped with; None = the year rolls
# one for it. Tournaments gather in autumn, armies march in summer.
AGENDA_SEASON = {
    "politics": "spring",       # the standing tick: rule years and tribute
    "campaign": "summer",       # a war already being fought
    "war": "summer",            # ... and one about to be declared
    "muster": "summer",         # notice only: the levies the player may join
    "revolt": "summer",
    "assassination": "autumn",
    "usurpation": "autumn",
    "sect": "winter",
    "petition": "autumn",       # pleas lapse, and new riders are sent
    "answer": None,             # ... and a champion rides for one
    "tournament": "autumn",
    "expedition": None,
    "feud": None,
    "grudge": None,             # somebody's grudge against the PC ripens
}
# Resolution order INSIDE a season — the old event phase's order, kept so
# that stamping events across the calendar changes when they happen and not
# what happens.
AGENDA_ORDER = ("politics", "campaign", "war", "muster", "revolt",
                "assassination", "usurpation", "sect", "answer", "petition",
                "tournament", "expedition", "feud", "grudge")
# What the season prompt says is coming. {season} and the item's own fields.
AGENDA_NOTICES = {
    "campaign": "the armies of {att} are in the field against {dfn} this "
                "{season}",
    "muster": "{domain} is calling up its levies this {season}",
    "revolt": "{domain} is close to rising against {ruler}",
    "tournament": "the sects gather in {season} for the tournament",
    "expedition": "a secret realm is expected to open in {season}",
    "feud": "{s1} and {s2} are one insult from open war",
    "answer": "{sect} has asked you to ride for {where} in {season}",
    "grudge": "{foe} has been asking after you",
}
# Notices everyone can see coming, whether or not they are the player's
# business; the rest are shown only when they are a HARD interrupt for the PC.
AGENDA_PUBLIC = ("tournament", "expedition", "feud")

# --- THE PLAYABLE LAYER: THE SEASON ACTIVITIES (VII §3) --------------------
# NO THROUGHPUT EDGE: a season pays a QUARTER of the matching yearly action,
# in gains and in risk alike. Four choices a year instead of one is the
# player's whole advantage — they can react to the agenda.
SEASON_RATE = 0.25
# Fight injustice: the road, but pointed at the worst-governed land in reach.
INJUSTICE_LANDS = 3             # the worst-off lands the player picks from
# Hunt spirit beasts: a contest against the wilds, priced off the hunter's
# own realm, paying materials (resources) and, when it goes wrong, insight.
HUNT_POWER = (14.0, 26.0)       # what a season's worst beast is worth
HUNT_POWER_PER_REALM = 11.0     # ... and what it grows into higher country
HUNT_SPOILS = (2, 5)            # hides, cores and glands, in silver
HUNT_ODDS = (0.15, 0.95)
HUNT_MAUL_DEATH = 0.05          # of a hunt that goes wrong
HUNT_MAUL_INSIGHT = 4
HUNT_MAUL_EPITHET = 0.25
HUNT_LINES = {
    "kill": [
        "{who} ran down a spirit beast in the wilds of the {land} and came "
        "back with its core (+resources).",
        "{who} took a horned thing out of the ravines above {where} and sold "
        "the hide in the market (+resources).",
        "{who} hunted the uplands of the {land} all season and brought the "
        "beast down in the last of the light (+resources).",
    ],
    "empty": [
        "{who} hunted the wilds of the {land} all season, and found only "
        "tracks.",
        "{who} spent the season in the hills above {where}; the beasts had "
        "moved on.",
    ],
    "maul": [
        "{who} was mauled by the thing they had gone into the wilds of the "
        "{land} to hunt, and crawled out of it (+insight).",
        "{who} cornered a beast above {where} that turned out to be the one "
        "doing the cornering (+insight).",
    ],
    # A death line is a CAUSE, and is read into the obituary: no name, no
    # full stop, exactly like the road's.
    "death": [
        "killed by the thing they had gone into the wilds of the {land} to hunt",
        "torn apart by a spirit beast in the ravines above {where}",
        "lost on a winter hunt in the high country above {where}",
    ],
}
# Trade run: silver made on the difference between two countries. The margin
# is the prosperity GAP — a rich land's grain is worth most where there is
# none — and the road takes its cut in bandits.
# (yearly rates, like every other action here; a season pays SEASON_RATE
# of them)
TRADE_MARGIN = 3.0              # silver per point of prosperity gap
TRADE_FLOOR = 4                 # ... and what an even run still pays
TRADE_RISK = 0.40               # bandits somewhere on a year of that road
TRADE_LOSS = (2, 5)             # what they take, and they take it whole
TRADE_STANDING_CHANCE = 0.40    # a name in two markets is worth something
TRADE_LINES = {
    "run": ["{who} ran {goods} from the {a} into the {b} and sold it well "
            "(+resources).",
            "{who} spent the season on the road between the {a} and the {b} "
            "with {goods} "
            "(+resources).",
            "{who} bought {goods} cheap in the {a} and dear in the {b} "
            "(+resources)."],
    "thin": ["{who} ran {goods} between the {a} and the {b} and barely covered "
             "the road.",
             "{who} traded {goods} out of the {a} all season for very little."],
    "robbed": ["{who} was robbed of {goods} on the road out of the {a} "
               "(-resources).",
               "{who} lost a whole season's {goods} to bandits short of the "
               "{b} (-resources)."],
}
TRADE_GOODS = ("grain", "salt", "iron", "medicine", "spirit-herbs", "cloth",
               "talismans", "horses", "tea")

# --- THE PLAYABLE LAYER: TIMESKIP AND THE INTERRUPT TABLE (VII §3) ---------
TIMESKIP_CAP = 12               # seasons, three years: the hard ceiling
DIGEST_LINES = 20               # chronicle lines a digest will print
# HARD interrupts the agenda can SEE COMING — the skip stops on the eve, the
# season BEFORE the event. (Foreseen: they were rolled at year start.)
# Everything else the chronicle prints is SOFT and goes in the digest.
GRUDGE_RIPE = 3                 # grudge intensity that comes looking for you
GRUDGE_RIPEN_CHANCE = 0.10      # per ripe grudge against the PC, per year
GRUDGE_RIPEN_MAX = 1            # ... and at most this many a year
# HARD interrupts nothing can foresee — checked at each season boundary and
# woken on the season they happen, not on an eve.
WITNESS_REL_INTENSITY = 2       # a rel this close, dead or maimed, wakes you
HOME_DESPERATE = 2.0            # home prosperity that wakes you

# --- THE PLAYABLE LAYER: THE PLAYED CHARACTER (VII §2) ---------------------
PLAYER_AID_NOTE = "agent 65"    # the player joins the watched intake
# Deeds drive the played character's mutation: the world writes on the
# player exactly as it writes on everyone, but it reads the RECORD, not the
# dice. (Recorded for every agent; only the played PC mutates off them in
# P1 — NPCs keep their trigger-driven mutation untouched.)
DEED_WINDOW = 5                 # years a deed stays on the ledger
DEED_THRESHOLD = 3              # deeds of a kind inside the window
DEED_TRAITS = {
    "blood": "Bloodthirsty",    # killings in fights the PC chose
    "cruelty": "Cruel",         # maimings, shakedowns, the defenseless
    "mercy": "Righteous",       # foes spared, villages pulled out of a fire
}
KARMA_WORDS = [(-24, "black"), (-10, "ill-famed"), (-3, "shadowed"),
               (3, "unremarked"), (10, "well-thought-of"), (24, "honoured"),
               (10 ** 9, "shining")]
# The season menu (key, label, one line of what it pays).
PLAYER_ACTIVITIES = [
    ("cultivate", "Cultivate at the sect",
     "qi at the sect's rate, and a trickle of silver"),
    ("retreat", "Meditate in retreat",
     "more qi than the sect gives; the world forgets you"),
    ("injustice", "Fight injustice",
     "a misruled land, its roads and its magistrates; karma and grudges"),
    ("hunt", "Hunt spirit beasts",
     "materials, and the wilds' own risk"),
    ("trade", "Trade run",
     "silver, scaled by what two countries are worth to each other"),
    ("socialize", "Socialize",
     "standing, friends, rivals, and old scores"),
    ("muster", "Join the muster",
     "a captain's pay, and whatever the war does with you"),
]
PLAYER_ACTIVITY_KEYS = [k for k, _, _ in PLAYER_ACTIVITIES]


# ---------------------------------------------------------------------------
# Places — the nested world tree
# ---------------------------------------------------------------------------

def prosperity_word(value: float) -> str:
    """Prosperity is reported in words, never numbers."""
    for ceiling, word in PROSPERITY_WORDS:
        if value < ceiling:
            return word
    return PROSPERITY_WORDS[-1][1]


def karma_word(value: int) -> str:
    """VII §11: a ledger is reported in words too — the player sees how they
    are spoken of, not the counter."""
    for ceiling, word in KARMA_WORDS:
        if value < ceiling:
            return word
    return KARMA_WORDS[-1][1]


@dataclass(eq=False)
class Place:
    """A node of the world tree: land > region > settlement (or sect seat).

    `prosperity` and `baseline` are only carried directly by settlements;
    regions and lands report the mean of the settlements beneath them
    (`wealth()`). Lands additionally carry their grid slot and name pool.
    """
    pid: int
    name: str
    kind: str                                   # land/region/city/town/village/sect
    parent: Optional["Place"] = field(default=None, repr=False)
    land: Optional["Place"] = field(default=None, repr=False)
    children: list = field(default_factory=list, repr=False)
    prosperity: float = 5.0
    baseline: float = 5.0
    grid: Optional[tuple] = None                # (row, col) — lands only
    pool: Optional[str] = None                  # NAME_LANDS key; None = melting pot
    polity: Optional[int] = None                # set on the roots of a territory

    def settlements(self) -> list:
        """Every settlement at or beneath this place (sect seats excluded)."""
        if self.kind in SETTLEMENT_KINDS:
            return [self]
        out = []
        for c in self.children:
            out.extend(c.settlements())
        return out

    def wealth(self) -> float:
        """Prosperity of this place: the mean of the settlements under it."""
        kids = self.settlements()
        if not kids:
            return self.prosperity
        return sum(p.prosperity for p in kids) / len(kids)

    def word(self) -> str:
        return prosperity_word(self.wealth())

    def is_center(self) -> bool:
        return self.grid == (1, 1)

    def reach(self) -> str:
        """Where this land sits on the grid: center / edge / corner."""
        if self.grid is None:
            return ""
        row, col = self.grid
        if row == 1 and col == 1:
            return "center"
        return "edge" if (row == 1 or col == 1) else "corner"


# ---------------------------------------------------------------------------
# Polities — who rules the places
# ---------------------------------------------------------------------------

@dataclass(eq=False)
class Edict:
    """A senseless rule standing over a polity until the ruler changes."""
    label: str                  # "the mirror-breaking" — for repeal lines
    clause: str                 # "that every mirror be broken"
    year: int
    mandate_from: Optional[int] = None   # pid of the liege that imposed it


@dataclass(eq=False)
class Polity:
    """An empire, kingdom, khanate, jarldom, city-state, tribe or sect.

    `territory` holds the places ruled DIRECTLY (a capital plus regions);
    everything beneath them obeys the same ruler. A vassal's region is cut
    out of its liege's territory. Sects are polities too, but stand outside
    the vassalage tree entirely (the spiritual exemption) and take no part
    in the rule-style engine.
    """
    pid: int
    name: str                        # "Khanate of the Wolf Steppe"
    kind: str                        # empire/kingdom/khanate/jarldom/city/tribe/sect
    seat: Optional[Place] = None
    domain: str = ""                 # "the Wolf Steppe" / "Sartuul Ford"
    land: Optional[Place] = None
    territory: list = field(default_factory=list)
    leader: Optional[int] = None     # aid
    liege: Optional[int] = None      # pid
    vassals: list = field(default_factory=list)   # pids
    unrest: int = 0
    army: int = 0
    edicts: list = field(default_factory=list)
    style: str = STYLE_QUIET         # last year's dominant facet, in a word
    last_facets: tuple = ()
    last_line: str = ""              # so a reign does not repeat itself twice
    at_war: bool = False             # set for the length of a campaign (§9)
    crisis_year: Optional[int] = None    # a seat taken over a rival's claim
    defiance_year: Optional[int] = None  # a vassal that kept the tribute

    def is_sovereign(self) -> bool:
        return self.liege is None and self.kind != "sect"

    def settlements(self) -> list:
        out = []
        for p in self.territory:
            out.extend(p.settlements())
        return out

    def title(self, sex: str) -> str:
        pair = POLITY_TITLES.get(self.kind, ("Lord", "Lady"))
        return pair[0] if sex == "m" else pair[1]

    def wealth(self) -> float:
        kids = self.settlements()
        if not kids:
            return 5.0
        return sum(p.prosperity for p in kids) / len(kids)

    def word(self) -> str:
        return prosperity_word(self.wealth())


# ---------------------------------------------------------------------------
# Petitions — the one door between the villages and the sects
# ---------------------------------------------------------------------------

@dataclass(eq=False)
class Petition:
    """A starving settlement's plea to a sect, open until answered or lapsed."""
    place: Place
    sect: str
    year: int
    polity: Optional[int] = None    # pid of the polity that holds the place
    plea: str = ""                  # "to open the sealed granary of {where}"
    done: str = ""                  # what the answer looks like, in past tense
    task: str = ""                  # "the sealed granary" — named on failure


# ---------------------------------------------------------------------------
# Wars — an abstract campaign between two courts (§9)
# ---------------------------------------------------------------------------

@dataclass(eq=False)
class War:
    """A 1-3 year campaign. The armies are numbers and the dead conscripts are
    chronicle colour; the cultivators who ride to it are ordinary agents and
    die like it.

    `kind` is "conquest" (two sovereigns over a border) or "vassalage" (a
    liege bringing a defiant vassal back under the old oath), which is the
    only difference the outcomes read.
    """
    attacker: int                   # pid
    defender: int                   # pid
    year: int
    length: int
    kind: str = "conquest"
    fought: int = 0                 # campaign years resolved so far
    score: dict = field(default_factory=dict)     # pid -> accumulated weight
    enlisted: dict = field(default_factory=dict)  # pid -> [aid] this year
    veterans: set = field(default_factory=set)    # every aid that ever rode


# ---------------------------------------------------------------------------
# The year agenda (VII §1) — the near future, rolled at year start
# ---------------------------------------------------------------------------

@dataclass(eq=False)
class AgendaItem:
    """One thing this year is going to do, and the season it does it in.

    The agenda is the trick that makes "stop BEFORE something interesting"
    possible: the engine knows the near future because it rolled it. Items
    whose OUTCOME was decided at plan time carry it in `payload`; the rest
    carry only the decision that the check happens, and roll their details
    when their season comes.
    """
    kind: str
    season: str
    payload: dict = field(default_factory=dict)
    notice: str = ""                # what the season prompt says about it
    hard: bool = False              # a foreseen HARD interrupt for the PC


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

@dataclass
class PlayerState:
    """What a PLAYED character carries that NPCs abstract into one number.

    P1 fills almost none of this on purpose: hp, wounds and standing orders
    are P3, proficiencies and masters P5, professions and pills P6,
    techniques P7. The fields exist so later sessions have one place to put
    them, and so the shape of a played sheet stops changing underneath the
    save format. Nothing in the kernel reads them yet.
    """
    activity: str = "cultivate"     # the last chosen season activity
    seasons: int = 0                # seasons actually played
    hp: int = 100                   # P3: inside a fight only
    max_hp: int = 100               # P3
    wound: int = 0                  # P3: 0 none, 1 light, 2 serious
    proficiencies: dict = field(default_factory=dict)   # P5: Body/Weapon/Theory
    stances: dict = field(default_factory=dict)         # P2/P5: edge+manner ranks
    professions: dict = field(default_factory=dict)     # P6: alchemy/forge/heal
    techniques: list = field(default_factory=list)      # P7
    pills: dict = field(default_factory=dict)           # P6
    toxicity: int = 0                                   # P6
    orders: dict = field(default_factory=dict)          # P3: standing orders


@dataclass
class Rel:
    kind: str
    intensity: int = 1


@dataclass
class Agent:
    aid: int
    name: str
    sect: str
    age: int
    talent: int                       # 1-10, fixed at birth
    traits: list
    sex: str = "m"                    # "m"/"f"; only picks the given-name pool
    home: Optional[Place] = None      # the settlement they were born in
    homeland: str = ""                # name of the land that home sits in
    descent: str = ""                 # NAME_LANDS pool their names come from
    realm: int = 1
    qi: float = 0.0
    insight: float = 0.0
    burden: int = 0                   # heart demons / unresolved baggage
    resources: int = 3
    standing: int = 1
    ruling: Optional[int] = None      # pid of the polity they rule, or None
    reign_start: Optional[int] = None
    reign_came: str = ""              # how they came to the seat they hold
    past_reigns: list = field(default_factory=list)  # seats held and laid down
    thrones_refused: int = 0          # §4: offers turned down, for the obituary
    revolts_survived: int = 0         # risings put down while on the seat
    wars_won: int = 0                 # campaigns fought from a throne, and
    wars_lost: int = 0                # ... the ones that came home beaten
    extraction_years: int = 0         # years of taking — the corruption clock
    karma: int = 0                    # §7: seeded from traits, moved by deeds
    defended: str = ""                # what they died in defence of, if any
    rels: dict = field(default_factory=dict)     # aid -> Rel
    epithets: list = field(default_factory=list)
    history: list = field(default_factory=list)  # private log: (year, text)
    fortune: int = 0                  # streaky luck, clamped small
    stipend_years: int = 0            # years the family at home has sent silver
    deeds: list = field(default_factory=list)    # VII §2: (year, kind) — the
                                      # record the played character mutates off
    play: Optional[PlayerState] = None   # set only on a PLAYED character
    alive: bool = True
    exited: bool = False              # voluntary exit (not a death)
    death_year: Optional[int] = None
    death_cause: Optional[str] = None
    intake_year: int = 0

    @property
    def lifespan(self) -> int:
        return BASE_LIFESPAN + (self.realm - 1) * LIFESPAN_PER_REALM

    @property
    def realm_name(self) -> str:
        return REALM_NAMES[self.realm]

    def display(self) -> str:
        if self.epithets:
            return f"{self.name} the {self.epithets[-1]}"
        return self.name

    def power(self) -> float:
        p = self.realm * 10 + self.qi / 10 + self.talent
        if "Proud" in self.traits:
            p += 1
        if "Ruthless" in self.traits:
            p += 1
        if "Cautious" in self.traits:
            p -= 1
        return p

    def has_trait(self, t: str) -> bool:
        return t in self.traits

    def is_ruler(self) -> bool:
        return self.ruling is not None

    def stalled(self) -> bool:
        return (self.qi >= 100 and self.realm < MAX_REALM
                and self.insight < INSIGHT_REQ[self.realm])


# ---------------------------------------------------------------------------
# World
# ---------------------------------------------------------------------------

class World:
    def __init__(self, seed=None, intake_size=INTAKE_SIZE):
        self.rng = random.Random(seed)
        self.year = 0
        self.agents: dict[int, Agent] = {}
        self._next_aid = 1
        self.intake_size = intake_size
        # A sect's richness multiplier is its founding endowment TIMES the
        # tilt its current head's character puts on it (§11).
        self.sect_base = {name: richness for name, richness in SECT_SPECS}
        self.sects = dict(self.sect_base)
        self.sect_heads: dict[str, Optional[int]] = {}
        self.chronicle: list[tuple[int, str, str]] = []  # (year, tag, text)
        self._fresh_lines: list[str] = []
        self.obituaries: list[str] = []
        self.next_expedition = 0
        self.feud_cooldown = 0
        self.pc: Optional[Agent] = None
        # VII §1: the two clocks. The world still thinks in years; `agenda`
        # is the year's events, rolled at year start and stamped with the
        # season each will fire in, and `season` is where the calendar is.
        self.season: Optional[str] = None
        self.agenda: list = []
        # VII §2: set only when a human is playing agent 65. It repeals the
        # camera constraint for the PC, takes them out of the NPC action
        # phase, and turns the rolls the kernel makes FOR an agent (leaving
        # the path, an offered seat, an assigned plea) into questions.
        self.playing = False
        self.ask: Optional[Callable] = None   # the UI's question hook
        # Geography (built first, in _setup).
        self.places: dict[int, Place] = {}
        self.lands: dict[str, Place] = {}          # land name -> land Place
        self.grid: list = [[None] * 3 for _ in range(3)]   # grid[row][col]
        self.sect_seats: dict[str, Place] = {}
        self.sibling_lands: list = []              # [(land, land), ...]
        self._next_pid = 1
        self._place_names: set = set()
        # Politics (built in _setup, on top of the geography).
        self.polities: dict[int, Polity] = {}
        self._next_poid = 1
        # The contact surface: open pleas, and when each village last begged.
        self.petitions: list = []
        self._petition_seen: dict[int, int] = {}   # place pid -> year
        # Consequences (§9): the campaigns currently being fought, and what
        # the lands still remember of the ones that are over.
        self.wars: list = []
        self.upheavals: list = []   # (year, land name, one clause)
        self._setup()

    # -- geography ----------------------------------------------------------

    def _new_place(self, name, kind, parent=None, land=None) -> Place:
        p = Place(pid=self._next_pid, name=name, kind=kind, parent=parent,
                  land=land if land is not None else parent)
        if p.kind != "land" and p.land is not None and p.land.kind != "land":
            p.land = p.land.land
        self._next_pid += 1
        if parent is not None:
            parent.children.append(p)
        self.places[p.pid] = p
        self._place_names.add(name)
        return p

    def _place_stem(self, land: Place) -> str:
        """A name stem from the land's pool; the melting pot draws from any."""
        pool = land.pool or self.rng.choice(list(NAME_LANDS))
        spec = NAME_LANDS[pool]
        if self.rng.random() < PLACE_STEM_SURNAME_CHANCE:
            return self.rng.choice(spec["surnames"])
        return self.rng.choice(spec["male"] + spec["female"])

    def _place_name(self, land: Place, kind: str) -> str:
        for _ in range(40):
            name = f"{self._place_stem(land)} {self.rng.choice(PLACE_SUFFIXES[kind])}"
            if name not in self._place_names:
                return name
        return name

    def _build_geography(self):
        """The nine lands: a 3x3 grid, then a nested tree inside each land."""
        r = self.rng
        pools = list(NAME_LANDS)
        doubled = r.sample(pools, DOUBLED_POOLS)
        # (land name, name pool) for the eight outer lands.
        outer = []
        for pool in pools:
            outer.append((pool, pool))
            if pool in doubled:
                outer.append((SECONDARY_LAND_NAMES[pool], pool))
        slots = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2)]

        def siblings_together(order):
            for pool in doubled:
                at = [slots[i] for i, (_, p) in enumerate(order) if p == pool]
                (r1, c1), (r2, c2) = at
                if max(abs(r1 - r2), abs(c1 - c2)) > 1:
                    return False
            return True

        # Sibling nations sit side by side when the shuffle allows; one retry
        # pass, then the world takes whatever falls.
        for _ in range(SIBLING_ADJACENCY_RETRIES + 1):
            r.shuffle(outer)
            if siblings_together(outer):
                break

        center = self._new_place(MIDDLE_PLAIN, "land")
        center.land, center.grid, center.pool = center, (1, 1), None
        self.grid[1][1] = center
        self.lands[center.name] = center
        for slot, (name, pool) in zip(slots, outer):
            land = self._new_place(name, "land")
            land.land, land.grid, land.pool = land, slot, pool
            self.grid[slot[0]][slot[1]] = land
            self.lands[name] = land

        for pool in doubled:
            pair = tuple(l for l in self.lands.values() if l.pool == pool)
            if len(pair) == 2:
                self.sibling_lands.append(pair)

        for land in self.lands.values():
            self._build_land_tree(land)

    def _build_land_tree(self, land: Place):
        r = self.rng
        land.baseline = r.uniform(*PROSPERITY_BASELINE)
        land.prosperity = land.baseline
        if land.is_center():
            n_regions, sizes = MIDDLE_PLAIN_REGIONS, MIDDLE_PLAIN_REGION_SIZES
        else:
            n_regions, sizes = r.choice(OUTER_REGIONS), OUTER_REGION_SIZES
        self._new_settlement(land, "city", land)          # the capital
        for _ in range(n_regions):
            region = self._new_place(self._place_name(land, "region"),
                                     "region", land)
            region.baseline = land.baseline
            region.prosperity = land.baseline
            for _ in range(r.choice(sizes)):
                kind = "town" if r.random() < TOWN_CHANCE else "village"
                self._new_settlement(land, kind, region)

    def _new_settlement(self, land: Place, kind: str, parent: Place) -> Place:
        p = self._new_place(self._place_name(land, kind), kind, parent)
        base = land.baseline + self.rng.uniform(-PROSPERITY_JITTER,
                                                PROSPERITY_JITTER)
        p.baseline = max(0.0, min(10.0, base))
        p.prosperity = p.baseline
        return p

    def settlements(self) -> list:
        return [p for p in self.places.values() if p.kind in SETTLEMENT_KINDS]

    def neighbors(self, land: Place, strong=None) -> list:
        """Lands touching this one. strong=True: shares an edge (war, trade,
        refugees). strong=False: corner contact only (rumours, rare war)."""
        row, col = land.grid
        out = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if not (0 <= nr < 3 and 0 <= nc < 3):
                    continue
                is_strong = (dr == 0 or dc == 0)
                if strong is None or is_strong == strong:
                    out.append(self.grid[nr][nc])
        return out

    def _land_weight(self, land: Place) -> float:
        return {"center": RECRUIT_WEIGHT_CENTER,
                "edge": RECRUIT_WEIGHT_EDGE,
                "corner": RECRUIT_WEIGHT_CORNER}[land.reach()]

    # -- polities -----------------------------------------------------------

    def _new_polity(self, name, kind, seat, domain, territory, land) -> Polity:
        p = Polity(pid=self._next_poid, name=name, kind=kind, seat=seat,
                   domain=domain, land=land, territory=list(territory))
        self._next_poid += 1
        self.polities[p.pid] = p
        for place in p.territory:
            place.polity = p.pid
        p.army = len(p.settlements())
        return p

    def _polity_kinds(self, land: Place) -> tuple:
        """(sovereign kind, vassal kind) for a land, by culture."""
        if land.is_center():
            return POLITY_KINDS_CENTER
        return POLITY_KINDS_BY_POOL.get(land.pool, POLITY_KINDS_DEFAULT)

    def _build_polities(self):
        """One sovereign per land, a few vassals beneath it, and the four
        sects as polities standing outside the vassalage tree."""
        r = self.rng
        for land in self.lands.values():
            sov_kind, vassal_kind = self._polity_kinds(land)
            capital = self._capital(land)
            regions = [c for c in land.children if c.kind == "region"]
            r.shuffle(regions)
            span = EMPIRE_VASSAL_COUNT if land.is_center() else OUTER_VASSAL_COUNT
            n_vassals = min(r.randint(*span), max(0, len(regions) - 1))
            sov = self._new_polity(
                f"{POLITY_WORDS[sov_kind]} of the {land.name}", sov_kind,
                capital, f"the {land.name}",
                [capital] + regions[n_vassals:], land)
            self._install_ruler(sov, age=r.randint(*RULER_AGE), founding=True)
            for region in regions[:n_vassals]:
                seat = self._vassal_seat(region)
                vassal = self._new_polity(
                    f"{POLITY_WORDS[vassal_kind]} of {seat.name}", vassal_kind,
                    seat, f"the {region.name}", [region], land)
                vassal.liege = sov.pid
                sov.vassals.append(vassal.pid)
                self._install_ruler(vassal, age=r.randint(*RULER_AGE),
                                    founding=True)
        for sect, seat in self.sect_seats.items():
            polity = self._new_polity(sect, "sect", seat, sect, [seat],
                                      self.grid[1][1])
            seat.polity = polity.pid

    def _vassal_seat(self, region: Place) -> Place:
        towns = [p for p in region.settlements() if p.kind == "town"]
        return self.rng.choice(towns or region.settlements())

    def polity_at(self, place: Optional[Place]) -> Optional[Polity]:
        """Which polity rules a place: walk up until a territory root."""
        node = place
        while node is not None:
            if node.polity is not None:
                return self.polities.get(node.polity)
            node = node.parent
        return None

    def ruler_at(self, place: Optional[Place]) -> Optional[Agent]:
        polity = self.polity_at(place)
        return self.leader_of(polity) if polity else None

    def leader_of(self, polity: Optional[Polity]) -> Optional[Agent]:
        if polity is None or polity.leader is None:
            return None
        return self.agents.get(polity.leader)

    def ruler_ref(self, a: Agent) -> str:
        """How a ruler is named in the chronicle: 'Khan Batu of the Steppe'."""
        polity = self.polities.get(a.ruling) if a.ruling is not None else None
        if polity is None:
            return a.display()
        return f"{polity.title(a.sex)} {a.display()} of {polity.domain}"

    def ruler_short(self, a: Agent) -> str:
        """A ruler named without their domain — for lines that have already
        said which seat is being talked about."""
        polity = self.polities.get(a.ruling) if a.ruling is not None else None
        if polity is None:
            return a.display()
        return f"{polity.title(a.sex)} {a.display()}"

    def _court_traits(self) -> list:
        """Traits for a ruler: the full pool, skewed toward the court."""
        r = self.rng
        pool = list(TRAIT_POOL)
        weights = [COURT_TRAIT_WEIGHTS.get(t, 1.0) for t in pool]
        traits = []
        for _ in range(r.choice([2, 2, 3])):
            t = r.choices(pool, weights)[0]
            i = pool.index(t)
            pool.pop(i)
            weights.pop(i)
            traits.append(t)
        return traits

    def _seed_karma(self, a: Agent):
        """§7: karma starts as disposition and is SEEDED ONCE, at creation.

        It is not recomputed when traits mutate — a reformed bully does not
        get his ledger wiped, and a corrupted king does not get his past
        debited. Deeds move it from here on, and over a long life they
        dominate the seed by an order of magnitude.
        """
        virtue = sum(1 for t in a.traits if t in VIRTUE_TRAITS)
        vice = sum(1 for t in a.traits if t in VICE_TRAITS)
        a.karma = KARMA_PER_MORAL_TRAIT * (virtue - vice)

    def _vice_spoils(self, a: Agent) -> int:
        """§7: vice takes a cut of every win. Evil is the fast lane."""
        return VICE_SPOILS if any(t in VICE_TRAITS for t in a.traits) else 0

    def _karma_kill(self, killer: Optional[Agent], victim: Agent):
        """§7: killing the DEFENSELESS. A duel between equals is a duel; a
        killing across a realm gap is a killing, and the ledger says so."""
        if killer is None or not killer.alive:
            return
        if victim.realm < killer.realm:
            killer.karma += KARMA_KILL_DEFENSELESS
            self._record_deed(killer, "cruelty")    # VII §2: the ledger

    def _fell_defending(self, a: Agent, whom: str):
        """§7: dying in defence of others. Posthumous — it buys the dead
        nothing at all, only the obituary and the grief of friends."""
        a.defended = whom
        a.karma += KARMA_DIED_DEFENDING

    def _camera_safe(self, a: Agent) -> bool:
        """§8: could this agent hold the camera? (No vice traits.)"""
        return not any(t in VICE_TRAITS for t in a.traits)

    def _install_ruler(self, polity: Polity, age: int,
                       founding=False) -> Agent:
        """Generate a mortal notable and seat them. Session 4 lets ambitious
        cultivators claim seats here instead."""
        r = self.rng
        land = polity.land
        sex = r.choice("mf")
        descent = land.pool or r.choice(list(NAME_LANDS))
        realm = 2 if (polity.is_sovereign()
                      and r.random() < RULER_REALM2_CHANCE) else 1
        a = Agent(
            aid=self._next_aid,
            name=self._new_name(sex, descent, melting_pot=land.pool is None),
            sex=sex,
            home=polity.seat,
            homeland=land.name,
            descent=descent,
            sect="",                        # rulers are sect-less mortals
            age=age,
            talent=self._roll_talent(),
            traits=self._court_traits(),
            realm=realm,
            qi=0.0,
            insight=0.0,
            resources=r.randint(*RULER_RESOURCES),
            standing=r.randint(*RULER_STANDING),
            intake_year=self.year,
            ruling=polity.pid,
            reign_start=self.year,
        )
        self._seed_karma(a)
        self._next_aid += 1
        self.agents[a.aid] = a
        polity.leader = a.aid
        if founding:
            # A successor's coronation is logged by _polity_succession.
            a.history.append((self.year, f"Held the seat of the "
                                         f"{polity.name} when the chronicle "
                                         f"opened."))
        return a

    def _sync_sect_polities(self):
        """Sect polities take the current sect head as their leader."""
        for polity in self.polities.values():
            if polity.kind == "sect":
                polity.leader = self.sect_heads.get(polity.name)

    def sovereigns(self) -> list:
        return [p for p in self.polities.values() if p.is_sovereign()]

    def ruling_polities(self) -> list:
        """Secular polities, lieges before their vassals (mandates flow down
        within the same year)."""
        out = [p for p in self.polities.values() if p.kind != "sect"]
        out.sort(key=lambda p: (p.liege is not None, p.pid))
        return out

    # -- construction -------------------------------------------------------

    def _pick_land(self, dominant=None) -> Place:
        """Where a recruit comes from: reach by grid position, cohort skew."""
        lands = list(self.lands.values())
        weights = [self._land_weight(l)
                   * (DOMINANT_LAND_BOOST if l is dominant else 1.0)
                   for l in lands]
        return self.rng.choices(lands, weights=weights)[0]

    def _pick_home(self, land: Place) -> Place:
        homes = land.settlements()
        weights = [SETTLEMENT_POP_WEIGHT[p.kind] for p in homes]
        return self.rng.choices(homes, weights=weights)[0]

    def _surname_from(self, pool: str, sex: str) -> str:
        spec = NAME_LANDS[pool]
        stem = self.rng.choice(spec["surnames"])
        if spec.get("patronymic"):
            return stem + ("sson" if sex == "m" else "sdottir")
        return stem

    def _new_name(self, sex: str, pool: str, melting_pot=False) -> str:
        r = self.rng
        spec = NAME_LANDS[pool]
        given = r.choice(spec["male"] if sex == "m" else spec["female"])
        surname_pool = pool
        mixed = MIXED_NAME_CHANCE * (MIDDLE_PLAIN_MIXED_MULT
                                     if melting_pot else 1.0)
        if r.random() < mixed:
            surname_pool = r.choice(list(NAME_LANDS))
        name = f"{given} {self._surname_from(surname_pool, sex)}"
        if any(a.name == name for a in self.agents.values()):
            return self._new_name(sex, pool, melting_pot)
        return name

    def _roll_talent(self) -> int:
        # Bell-ish 1-10, rare geniuses.
        return max(1, min(10, round(self.rng.gauss(5, 2))))

    def _make_agent(self, sect, age, realm=1, intake_year=None,
                    dominant_land=None, sex=None, land=None) -> Agent:
        r = self.rng
        # VII §2: the player picks a name, a sex and a homeland. Everything
        # else on this sheet is rolled, here, by the same dice as everyone.
        if sex is None:
            sex = r.choice("mf")
        if land is None:
            land = self._pick_land(dominant_land)
        home = self._pick_home(land)
        # Outer lands have one tongue; the Middle Plain's natives roll a
        # descent from the six pools evenly.
        descent = land.pool or r.choice(list(NAME_LANDS))
        a = Agent(
            aid=self._next_aid,
            name=self._new_name(sex, descent, melting_pot=land.pool is None),
            sex=sex,
            home=home,
            homeland=land.name,
            descent=descent,
            sect=sect,
            age=age,
            talent=self._roll_talent(),
            traits=r.sample(TRAIT_POOL, r.choice([2, 2, 3])),
            realm=realm,
            qi=r.uniform(0, 80),
            insight=r.uniform(0, 5) * realm,
            resources=r.randint(1, 6) * realm,
            standing=realm + r.randint(0, 2),
            intake_year=intake_year if intake_year is not None else self.year,
        )
        self._seed_karma(a)
        self._next_aid += 1
        self.agents[a.aid] = a
        return a

    def _setup(self):
        r = self.rng
        self._build_geography()
        # All four sects keep their seats in the Middle Plain.
        for sect in self.sects:
            self.sect_seats[sect] = self._new_place(
                sect, "sect", self.grid[1][1])
        self._build_polities()

        # Elders and seniors: stand-ins for previous simulated generations.
        for sect in self.sects:
            for _ in range(3):
                self._make_agent(sect, r.randint(140, 220),
                                 realm=r.choice([4, 4, 5]), intake_year=-999)
            for _ in range(5):
                self._make_agent(sect, r.randint(60, 120), realm=3,
                                 intake_year=-999)
            for _ in range(8):
                self._make_agent(sect, r.randint(30, 60), realm=2,
                                 intake_year=-999)
        self._update_sect_heads()

        # The focal intake — the "starting class of 64".
        cohort = self._recruit_intake(announce=False)

        # The random main character — drawn from the recruits who rolled no
        # vice trait (§8: the camera constraint applies at the roll, and the
        # PC is picked after the cohort is rolled).
        self.pc = r.choice([a for a in cohort if self._camera_safe(a)]
                           or cohort)
        self.pc.history.append((0, "Entered the sect as a new disciple."))

    def _recruit_intake(self, announce=True) -> list:
        r = self.rng
        sect_names = list(self.sects)
        # Recruits come from every land, but each cohort skews toward one.
        dominant = self._pick_land()
        cohort = []
        for i in range(self.intake_size):
            sect = sect_names[i % len(sect_names)]
            a = self._make_agent(sect, 14, realm=1, dominant_land=dominant)
            a.qi = r.uniform(0, 15)
            a.insight = 0
            a.resources = r.randint(0, 4)
            a.standing = 1
            self._home_start(a)
            cohort.append(a)
        # Pre-seed a few relationships inside the intake.
        for _ in range(self.intake_size // 4):
            a, b = r.sample(cohort, 2)
            kind = r.choice(["friend", "friend", "rival", "grudge", "sworn"])
            self._bind(a, b, kind, r.randint(1, 3))
        if announce:
            self.log(f"A new intake of {self.intake_size} students enters "
                     f"the sects; most hail from the {dominant.name}, whose "
                     f"villages are {dominant.word()}.",
                     [], world_event=True)
        return cohort

    def _home_start(self, a: Agent):
        """§10: the home a recruit walked out of is already on their sheet.

        A misruled village sends its children out poor, burdened, hardened —
        and sometimes already hating the man whose collectors emptied the
        granary. A prosperous one sends silver and a full trunk. The
        sheltered-genius / battered-underdog divergence starts here, before
        year one.
        """
        r = self.rng
        home = a.home
        if home is None:
            return
        ruler = self.ruler_at(home)
        if home.prosperity <= MISRULED_HOME_AT:
            a.resources = max(0, a.resources - MISRULED_RESOURCES)
            a.burden += MISRULED_BURDEN
            a.insight += MISRULED_INSIGHT
            text = (f"{a.display()} came to {a.sect} out of {home.name} in "
                    f"the {home.land.name}, a {home.word()} {home.kind}")
            if ruler is not None and ruler.alive:
                self._add_grudge(a, ruler, r.randint(*MISRULED_GRUDGE))
                text += (f", carrying a grudge against "
                         f"{self.ruler_ref(ruler)}")
            text += " (+insight, +burden, and nothing in their bundle)."
            self.log(text, [a], place=home)
        elif home.prosperity >= PROSPEROUS_HOME_AT:
            a.resources += r.randint(*PROSPEROUS_RESOURCES)
            a.insight = 0.0
            self.log(f"{a.display()} was sent to {a.sect} out of {home.name} "
                     f"in the {home.land.name}, a {home.word()} {home.kind}, "
                     f"with silver and a full trunk.", [a], place=home)

    def _stipends(self):
        """§10: the family reaches into the sim once a year.

        While a young cultivator's home village can spare it, silver comes up
        the road. While the levies are out, bad news comes instead.
        """
        r = self.rng
        for a in self.cultivators():
            if (a.age < 14 or not a.sect or a.home is None
                    or a.realm > STIPEND_REALM):
                continue
            polity = self.polity_at(a.home)
            if polity is not None and "CONSCRIPTION" in polity.last_facets:
                # The muster empties the same houses the stipend came from.
                ruler = self.leader_of(polity)
                rel = a.rels.get(ruler.aid) if ruler else None
                if (ruler is not None and ruler.alive and ruler.aid != a.aid
                        and (rel is None or rel.intensity < CRUEL_GRUDGE_MAX)
                        and r.random() < CONSCRIPTION_GRUDGE_CHANCE):
                    fresh = rel is None or rel.kind not in HOSTILE_KINDS
                    self._add_grudge(a, ruler, 1)
                    # The first press-gang is news; the tenth is a war.
                    if fresh:
                        self.log(f"{a.display()} learned a brother had been "
                                 f"taken for the levies of {polity.domain}; "
                                 f"they will not forget "
                                 f"{self.ruler_ref(ruler)}.",
                                 [a], place=a.home)
                continue
            if a.home.prosperity >= PROSPEROUS_HOME_AT:
                a.resources += STIPEND
                a.stipend_years += 1
                if a.stipend_years == 1:
                    self.log(f"{a.display()}'s family began sending silver "
                             f"from {a.home.name}, whose fields are "
                             f"{a.home.word()}.", [a])

    # -- relationship helpers -----------------------------------------------

    def _bind(self, a: Agent, b: Agent, kind: str, intensity=1):
        """Symmetric-ish relationship. master/disciple stored directionally."""
        if kind == "master":
            a.rels[b.aid] = Rel("master", intensity)      # b is a's master
            b.rels[a.aid] = Rel("disciple", intensity)
            return
        a.rels.setdefault(b.aid, Rel(kind, 0))
        b.rels.setdefault(a.aid, Rel(kind, 0))
        a.rels[b.aid].kind = kind
        a.rels[b.aid].intensity = max(a.rels[b.aid].intensity, intensity)
        b.rels[a.aid].kind = kind
        b.rels[a.aid].intensity = max(b.rels[a.aid].intensity, intensity)

    def _add_grudge(self, holder: Agent, target: Agent, amount=1):
        # §7: the wronged remember a black ledger longer. Every grudge in the
        # sim comes through here, so this is the whole coupling.
        if target.karma < GRUDGE_VS_VICE_AT:
            amount = int(amount * GRUDGE_VS_VICE_MULT + 0.5)
        rel = holder.rels.get(target.aid)
        if rel and rel.kind in HOSTILE_KINDS:
            rel.intensity += amount
        else:
            holder.rels[target.aid] = Rel("grudge", amount)

    # -- logging ------------------------------------------------------------

    def _pc_homeland(self, place: Optional[Place]) -> bool:
        """Does this place lie in the PC's own land? (The [home] tag.)"""
        pc = self.pc
        if pc is None or pc.home is None or place is None:
            return False
        return place.land is pc.home.land

    def log(self, text, actors, dramatic=False, world_event=False,
            place=None):
        """Record an event. Always private to actors; printed selectively.

        Tag priority: [PC] > relationship > [home] > [world] > [famous].
        """
        for a in actors:
            a.history.append((self.year, text))

        tag = None
        pc = self.pc
        if pc is not None:
            if any(a.aid == pc.aid for a in actors):
                tag = "PC"
            else:
                for a in actors:
                    rel = pc.rels.get(a.aid)
                    if rel is not None:
                        tag = REL_DISPLAY.get(rel.kind, rel.kind)
                        break
        if tag is None and self._pc_homeland(place):
            tag = "home"
        if tag is None and world_event:
            tag = "world"
        if tag is None and dramatic:
            if any(a.realm >= FAME_REALM or a.standing >= 10 for a in actors):
                tag = "famous"
        if tag is not None:
            line = f"Y{self.year:>4} [{tag:^6}] {text}"
            self.chronicle.append((self.year, tag, line))
            self._fresh_lines.append(line)

    # -- the year loop ------------------------------------------------------

    def step(self) -> list[str]:
        """Advance one year; return the chronicle lines it produced.

        VII §1, ONE CODE PATH: a year is PLAN (roll the agenda), PLAY (four
        season sub-steps) and CLOSE (resolution and intakes). Batch and
        observer modes run all three back to back and see exactly what they
        saw before; play mode calls the same three parts one at a time and
        stops between the seasons for the player.
        """
        self.begin_year()
        for season in SEASONS:
            self.run_season(season)
        return self.end_year()

    def begin_year(self) -> None:
        """PLAN: decide the year's events before any of them happen."""
        self._fresh_lines = []
        self.year += 1
        self.season = None
        self._plan_year()

    def run_season(self, season: str) -> None:
        """PLAY: one season sub-step.

        NPCs take their ONE action of the year in spring — read as what they
        mostly did that year — and the agenda's events resolve in the season
        they were stamped with, in the old event phase's order.
        """
        self.season = season
        if season == NPC_ACTION_SEASON:
            self._action_phase()
        for item in self.season_agenda(season):
            self._resolve_agenda(item)

    def end_year(self) -> list[str]:
        """CLOSE: the resolution phase and the intake, at winter's end."""
        self.season = None
        self._resolution_phase()

        if self.year % INTAKE_PERIOD == 0:
            self._recruit_intake()

        # VII §2: the played character mutates off their RECORD, not off the
        # dice — the one place where being played changes the physics, and
        # it changes it toward more honesty, not less.
        if self.playing and self.pc is not None and self.pc.alive:
            self._deed_mutation(self.pc)

        if self.pc is not None and not self.pc.alive:
            self._succeed_pc()

        return self._fresh_lines

    def season_agenda(self, season: str) -> list:
        """This season's agenda items, in the old event phase's order."""
        rank = {k: i for i, k in enumerate(AGENDA_ORDER)}
        items = [i for i in self.agenda if i.season == season]
        items.sort(key=lambda i: rank.get(i.kind, len(rank)))
        return items

    def living(self):
        return [a for a in self.agents.values() if a.alive]

    def cultivators(self):
        """The living who walk the path: rulers are on a different clock."""
        return [a for a in self.agents.values() if a.alive and not a.is_ruler()]

    # -- action phase -------------------------------------------------------

    def _pick_action(self, a: Agent) -> str:
        weights = {"cultivate": 3.0, "seclude": 0.8, "adventure": 1.0,
                   "socialize": 1.2, "teach": 0.0}
        if a.realm >= 3:
            weights["teach"] = 0.6
        for t in a.traits:
            for act, mult in TRAIT_ACTION.get(t, {}).items():
                weights[act] *= mult
        # Situational nudges.
        if a.stalled():  # hunger for insight
            weights["adventure"] *= 2.5
            weights["cultivate"] *= 0.3
        if a.resources <= 1:
            weights["adventure"] *= 1.4
        acts = list(weights)
        return self.rng.choices(acts, [weights[k] for k in acts])[0]

    def _action_phase(self):
        """Every NPC's ONE action of the year, taken in spring (VII §1).

        A PLAYED character is not here: they spend four seasons of their own
        (§3), and if they are on a throne the RULE action is taken for them
        below, because a court runs at year tempo for everyone.
        """
        for a in list(self.living()):
            if a.age < 14 or not a.alive:
                continue
            if a.is_ruler():
                self._act_rule(a)       # §4: ruling replaces the action phase
                continue
            if self.playing and a is self.pc:
                continue                # the player takes their own seasons
            # §9: a war at home can take anyone's year; a muster in peacetime
            # only takes the ones who were looking for one.
            if (self.wars or a.has_trait("Bloodthirsty")) \
                    and self._take_service(a):
                continue
            act = self._pick_action(a)
            getattr(self, f"_act_{act}")(a)

    def war_volunteer_weight(self, a: Agent, polity: Polity) -> float:
        """§9: how badly a cultivator wants a place in somebody's war.

        Bloodthirsty first, then the ones who go for the pay or for the
        country they were born in.
        """
        w = sum(m for t, m in WAR_VOLUNTEER_TRAITS.items() if a.has_trait(t))
        if a.home is not None and self.polity_at(a.home) is polity:
            w += WAR_VOLUNTEER_NATIVE
        return w

    def _take_service(self, a: Agent, forced=False, share=1.0) -> bool:
        """§7/§9: the muster takes a cultivator's whole year.

        A country at war will take anyone with an appetite for it — the
        Bloodthirsty, the ones who go for the pay, and the natives who go
        because it is their country. A peacetime levy only interests the
        first kind. A cultivator who signs on with a war is enlisted in it
        and settles up on the battlefield (`_battle`), not here.
        """
        r = self.rng
        polity = self.polity_at(a.home)
        if polity is None or a.home is None:
            return False
        war = self._war_of(polity)
        if war is None and not (
                "CONSCRIPTION" in polity.last_facets
                and (forced or a.has_trait("Bloodthirsty"))):
            return False
        if not forced:
            eager = min(1.0, self.war_volunteer_weight(a, polity)
                        / WAR_VOLUNTEER_FULL)
            if eager <= 0 or r.random() >= SERVICE_CHANCE * eager:
                return False
        pay = r.randint(*SERVICE_PAY)
        a.resources += self._share_int(pay + self._vice_spoils(a), share)
        a.standing += self._share_int(1, share)
        polity.army += self._share_int(1, share)
        leader = self.leader_of(polity)
        under = (f" under {self.ruler_ref(leader)}"
                 if leader is not None and leader.alive else "")
        if war is not None:
            other = self.polities.get(
                war.defender if war.attacker == polity.pid else war.attacker)
            riders = war.enlisted.setdefault(polity.pid, [])
            if a.aid in riders:
                return True     # already signed on; four seasons, one war
            riders.append(a.aid)
            # No place= on this one, unlike the peacetime muster: a war
            # takes whole cohorts of natives at once, and a land's own
            # chronicle would be nothing else for three years running. The
            # muster is the country's news; who rode to it is each rider's.
            self.log(f"{a.display()} took the field with the armies of "
                     f"{polity.domain}{under} against "
                     f"{other.domain if other else 'the enemy'}.", [a])
            return True
        if r.random() < SERVICE_SKIRMISH * share:
            a.insight += SERVICE_INSIGHT
            self.log(f"{a.display()} rode with the levies of {polity.domain}"
                     f"{under} and spent the season killing along the border "
                     f"(+resources, +insight).", [a], place=a.home)
        else:
            self.log(f"{a.display()} took a captain's pay in the muster of "
                     f"{polity.domain}{under}; the levies drilled and "
                     f"marched nowhere (+resources).", [a], place=a.home)
        return True

    def _act_rule(self, a: Agent):
        """§4: the RULE action, and the cultivation lock.

        A throne has no other action — no cultivate, no seclude, no road, no
        teaching — and NO QI AT ALL: nothing in this method touches it, which
        is the lock. The polity's own year (policy, edicts, tribute) is
        resolved by the rule-style engine in the event phase; this is the
        ruler's private year, and the ladder the seat walks them down.

        A reign is not news every year: the decade marks are written down,
        and the rest of the time only the occasional court year.
        """
        polity = self.polities.get(a.ruling)
        if polity is None:
            return
        self._maybe_corrupt(a, polity)
        reign = self.reign_length(a)
        fields = dict(ruler=self.ruler_ref(a), polity=polity.name,
                      domain=polity.domain, sect=a.sect or "the court",
                      seat=polity.seat.name if polity.seat else polity.domain,
                      years=self.years_phrase(reign))
        if reign and reign % RULE_MILESTONE == 0:
            # A cultivator standing still for a decade is the land's business
            # (place= puts it in front of the reader whose land it is); a
            # mortal notable growing old on a seat is the court's alone.
            lines = RULE_LOCK_LINES if a.sect else RULE_MORTAL_LINES
            self.log(self.rng.choice(lines).format(**fields), [a],
                     place=polity.seat if a.sect else None)
        elif self.rng.random() < RULE_LINE_CHANCE:
            self.log(self.rng.choice(RULE_YEAR_LINES).format(**fields), [a])

    def _maybe_corrupt(self, a: Agent, polity: Polity):
        """POWER CORRUPTS (§4): the seat walks its holder one step down the
        ladder Greedy -> Power-Hungry -> Cruel, suppressed by virtue and
        raised by years of extraction. Routed through the ordinary mutation
        machinery so the chronicle shows the change."""
        chance = CORRUPTION_CHANCE + min(
            CORRUPTION_EXTRACTION_CAP,
            CORRUPTION_PER_EXTRACTION * a.extraction_years)
        if any(a.has_trait(t) for t in CORRUPTION_VIRTUES):
            chance *= CORRUPTION_VIRTUE_MULT
        if self.rng.random() < chance:
            self._mutate(a, "power", sure=True)

    def _corruption_step(self, a: Agent) -> Optional[tuple]:
        """Where a ruler stands on the ladder, and the next rung down — or
        None if they are at the bottom of it, or the next rung is a trait
        this build does not have yet."""
        rung = 0
        for i, t in enumerate(CORRUPTION_LADDER):
            if t is not None and a.has_trait(t):
                rung = i
        if rung + 1 >= len(CORRUPTION_LADDER):
            return None
        nxt = CORRUPTION_LADDER[rung + 1]
        if nxt not in ACQUIRABLE_TRAITS:
            return None     # a rung this build does not carry
        return CORRUPTION_LADDER[rung], nxt

    # -- one year, or one quarter of one (VII §3) ---------------------------
    #
    # NO THROUGHPUT EDGE: a played season pays a QUARTER of the matching
    # yearly action, in gains and in risk alike. `share` is that quarter; at
    # share 1.0 not one extra die is rolled, which is why the NPC year is
    # untouched by any of this.

    def _fires(self, share: float) -> bool:
        """Does a whole-event outcome — a death, a treasure, a meeting —
        happen at this share of a year?"""
        return share >= 1.0 or self.rng.random() < share

    def _share_int(self, amount: int, share: float) -> int:
        """A share of an integer payout, with the remainder rolled for."""
        if share >= 1.0:
            return amount
        whole = int(amount * share)
        if self.rng.random() < amount * share - whole:
            whole += 1
        return whole

    def _act_cultivate(self, a: Agent, share=1.0):
        a.qi = min(100, a.qi
                   + (3 + a.talent * 0.9) * self.sects[a.sect] * share)
        a.resources += self._share_int(1, share)

    def _act_seclude(self, a: Agent, share=1.0):
        a.qi = min(100, a.qi + (6 + a.talent * 1.2) * share)
        # The world moves on: relationships decay. A retreat carries the
        # full social cost whether it lasts a season or a year.
        for rel in a.rels.values():
            if self.rng.random() < 0.3 * share:
                rel.intensity = max(0, rel.intensity - 1)

    def _adventure_destination(self, a: Agent) -> Place:
        """Where the road goes. The centre draws hardest, then the lands that
        touch it, then the far corners; a cultivator also drifts home."""
        lands = list(self.lands.values())
        home_land = a.home.land if a.home is not None else None
        weights = [ADVENTURE_LAND_WEIGHTS[l.reach()]
                   * (ADVENTURE_HOME_BOOST if l is home_land else 1.0)
                   for l in lands]
        land = self.rng.choices(lands, weights=weights)[0]
        return self._pick_home(land)    # a settlement, by its population

    @staticmethod
    def _karma_tilt(a: Agent) -> float:
        """§7: what a life's ledger is worth on the road, clamped small."""
        return max(-KARMA_ADVENTURE_CAP,
                   min(KARMA_ADVENTURE_CAP, a.karma * KARMA_ADVENTURE_TILT))

    @staticmethod
    def road_condition(place: Place) -> str:
        """What a destination's prosperity makes of the risk table."""
        if place.prosperity < ROAD_HARD_AT:
            return "harsh"
        if place.prosperity >= ROAD_RICH_AT:
            return "rich"
        return "settled"

    def _act_adventure(self, a: Agent, share=1.0, dest=None):
        r = self.rng
        if dest is None:
            dest = self._adventure_destination(a)
        land = dest.land
        condition = self.road_condition(dest)
        scenes = ADVENTURE_SCENES[condition]

        def scene(key, **extra) -> str:
            return r.choice(scenes[key]).format(
                who=a.display(), where=dest.name, land=land.name, **extra)

        # The [home] tag belongs to a land's POLITICS, not to every stranger
        # who happened to pass through it: only a misruled destination — where
        # the country itself is what happened to them — carries the place.
        where = dest if condition == "harsh" else None
        # The road's roll: LOW is a grave, HIGH is a fateful encounter.
        # Streaky luck first (a good run carries — the sign of this term was
        # inverted before the karma couplings went in, which made luck run
        # exactly backwards); then the ledger (§7: high karma finds fateful
        # encounters, low karma finds ambushes); then the country itself — a
        # misruled land is a more dangerous place to look for fortune than a
        # golden one.
        roll = (r.random() + a.fortune * FORTUNE_WEIGHT
                + self._karma_tilt(a) + ADVENTURE_RISK_SHIFT[condition])
        if roll < ADVENTURE_DEATH / a.realm and self._fires(share):
            self.kill(a, scene("death"))
        elif roll < ADVENTURE_NEAR_DEATH and self._fires(share):
            a.insight += 4
            a.burden += 1
            a.fortune = max(-FORTUNE_CAP, a.fortune - 1)
            text = scene("near_death")
            if r.random() < 0.4 and len(a.epithets) < 3:
                ep = r.choice([e for e in MAIM_EPITHETS if e not in a.epithets])
                a.epithets.append(ep)
                text += f" [epithet: {ep}]"
            self.log(text, [a], dramatic=True, place=where)
            self._mutate(a, "near_death")
        elif roll < 0.42:
            a.history.append((self.year, scene("quiet")))   # nothing found
        elif roll < 0.67:
            a.resources += self._share_int(r.randint(2, 6)
                                           + self._vice_spoils(a), share)
            if self._fires(share):
                a.fortune = min(FORTUNE_CAP, a.fortune + 1)
                if condition == "rich" \
                        and r.random() < ADVENTURE_PATRON_CHANCE:
                    a.standing += 1     # patrons and fairs make names
            a.history.append((self.year, scene("spoils")))
        elif roll < 0.82:
            a.insight += 3 * share
            if condition == "harsh" and r.random() < ADVENTURE_RESCUE_CHANCE \
                    and self._fires(share):
                # In a misruled land the insight is sometimes bought by a
                # deed, and a deed is worth writing down.
                a.karma += ADVENTURE_RESCUE_KARMA
                self._record_deed(a, "mercy")
                self.log(scene("rescue"), [a], place=where)
            else:
                a.history.append((self.year, scene("insight")))
        elif roll < 0.92:
            a.resources += self._share_int(8 + self._vice_spoils(a), share)
            a.insight += 2 * share
            if self._fires(share):
                a.fortune = min(FORTUNE_CAP, a.fortune + 2)
            self.log(scene("treasure"), [a], dramatic=(a.realm >= 3),
                     place=where)
        elif self._fires(share):
            others = [o for o in self.cultivators()
                      if o.aid != a.aid and abs(o.realm - a.realm) <= 1]
            if others:
                o = r.choice(others)
                kind = "friend" if r.random() < 0.6 else "rival"
                self._bind(a, o, kind, 2)
                self.log(scene("meeting", other=o.display(), kind=kind),
                         [a, o], place=where)
        else:
            a.history.append((self.year, scene("quiet")))

    def _act_socialize(self, a: Agent, share=1.0):
        r = self.rng
        # A vengeful agent with a ripe grudge seeks the enemy. A grudge
        # against a RULER is not settled with a duel — that is a revolt or
        # an assassination (§9), and neither is settled with a duel.
        targets = [self.agents[i] for i, rel in a.rels.items()
                   if rel.kind in HOSTILE_KINDS and rel.intensity >= 3
                   and self.agents[i].alive and not self.agents[i].is_ruler()]
        if (targets and (a.has_trait("Vengeful") or a.has_trait("Ruthless"))
                and self._fires(share)):
            t = max(targets, key=lambda x: a.rels[x.aid].intensity)
            if a.power() >= t.power() - 3:
                self._duel(a, t, lethal=True, context="a long-nursed grudge")
                return
        # §7: a Bully fights only DOWNWARD — the tyranny of realms inverted.
        if a.has_trait("Bully") and r.random() < BULLY_CHANCE * share:
            if self._bully_shakedown(a):
                return
        # ... and Bloodthirsty goes looking for a fight with an equal, which
        # is the only kind that can actually kill them.
        if a.has_trait("Bloodthirsty") \
                and r.random() < BLOODTHIRSTY_DUEL_CHANCE * share:
            peers = [o for o in self.cultivators()
                     if o.aid != a.aid and o.realm == a.realm and o.age >= 14]
            if peers:
                self._duel(a, r.choice(peers), lethal=True,
                           context="a quarrel picked for its own sake")
                return
        if a.has_trait("Proud") and r.random() < 0.25 * share:
            peers = [o for o in self.cultivators() if o.sect == a.sect
                     and o.realm == a.realm and o.aid != a.aid]
            if peers:
                self._duel(a, r.choice(peers), lethal=False,
                           context="a matter of face")
                return
        # Default: mingle.
        a.standing += 1 if r.random() < 0.5 * share else 0
        if r.random() < 0.3 * share:
            peers = [o for o in self.cultivators()
                     if o.aid != a.aid and abs(o.age - a.age) < 20
                     and abs(o.realm - a.realm) <= 1]
            if peers:
                o = r.choice(peers)
                if r.random() < 0.12 and o.aid not in a.rels:
                    self._bind(a, o, "lover", 3)
                    self.log(f"{a.display()} and {o.display()} became lovers.",
                             [a, o])
                else:
                    kind = "friend" if r.random() < 0.75 else "rival"
                    self._bind(a, o, kind, 1)

    def _act_teach(self, a: Agent):
        r = self.rng
        disciples = [self.agents[i] for i, rel in a.rels.items()
                     if rel.kind == "disciple" and self.agents[i].alive]
        if not disciples:
            juniors = [o for o in self.cultivators() if o.sect == a.sect
                       and o.realm <= a.realm - 2 and o.age < a.age - 15]
            if not juniors:
                return
            d = max(r.sample(juniors, min(4, len(juniors))),
                    key=lambda x: x.talent)
            self._bind(d, a, "master", 3)
            self.log(f"{a.display()} took {d.display()} (talent {d.talent}) "
                     f"as a disciple.", [a, d])
            disciples = [d]
        for d in disciples:
            d.qi = min(100, d.qi + a.realm * 2)
        if r.random() < 0.3:
            a.insight += 1

    # -- the season activities the kernel did not already have (VII §3) -----

    def _act_hunt(self, a: Agent, share=1.0):
        """A season in the wilds after spirit beasts.

        The same shape as everything else here: a contest against a number
        that grows with the country the hunter can reach, materials for a
        win, and for a loss the two things adversity always pays — insight
        and a scar.
        """
        r = self.rng
        where = self._adventure_destination(a)   # the roads they know, mostly
        land = where.land
        beast = r.uniform(*HUNT_POWER) + HUNT_POWER_PER_REALM * (a.realm - 1)
        power = a.power()
        odds = max(HUNT_ODDS[0], min(HUNT_ODDS[1], power / (power + beast)))
        fields = dict(who=a.display(), land=land.name, where=where.name)

        def line(key) -> str:
            return r.choice(HUNT_LINES[key]).format(**fields)

        if r.random() < odds:
            a.resources += self._share_int(r.randint(*HUNT_SPOILS)
                                           + self._vice_spoils(a), share)
            a.history.append((self.year, line("kill")))
            return
        if not self._fires(share):
            a.history.append((self.year, line("empty")))
            return
        if r.random() < HUNT_MAUL_DEATH:
            self.kill(a, line("death"))
            return
        a.insight += HUNT_MAUL_INSIGHT
        a.burden += 1
        a.fortune = max(-FORTUNE_CAP, a.fortune - 1)
        text = line("maul")
        if r.random() < HUNT_MAUL_EPITHET and len(a.epithets) < 3:
            ep = r.choice([e for e in MAIM_EPITHETS if e not in a.epithets])
            a.epithets.append(ep)
            text += f" [epithet: {ep}]"
        self.log(text, [a], dramatic=True)
        self._mutate(a, "near_death")

    def _act_trade(self, a: Agent, share=1.0):
        """A season on the roads between two countries.

        The margin is the PROSPERITY GAP — a rich land's grain is worth most
        where there is none — and the road takes its own cut. No insight, no
        qi: this is the lane that only pays silver.
        """
        r = self.rng
        lands = list(self.lands.values())
        home = a.home.land if a.home is not None else r.choice(lands)
        far = [l for l in lands if l is not home]
        other = r.choice(far) if far else home
        gap = abs(home.wealth() - other.wealth())
        fields = dict(who=a.display(), a=home.name, b=other.name,
                      goods=r.choice(TRADE_GOODS))
        if r.random() < TRADE_RISK * share:
            lost = min(a.resources, r.randint(*TRADE_LOSS))
            a.resources -= lost
            a.history.append((self.year,
                              r.choice(TRADE_LINES["robbed"]).format(**fields)))
            return
        take = self._share_int(int(round(TRADE_FLOOR + TRADE_MARGIN * gap))
                               + self._vice_spoils(a), share)
        a.resources += take
        if r.random() < TRADE_STANDING_CHANCE * share:
            a.standing += 1
        key = "run" if take >= 2 else "thin"
        a.history.append((self.year,
                          r.choice(TRADE_LINES[key]).format(**fields)))

    def _act_injustice(self, a: Agent, share=1.0):
        """A season spent on the worst-governed country within reach.

        If the sect is holding an open plea from such a country and this
        cultivator is fit to answer it, this IS the answer — the petition
        machinery is what fighting injustice looks like in this kernel.
        Otherwise it is the harsh road, where the misruled scenes live.
        """
        r = self.rng
        mine = [pt for pt in self.petitions if pt.sect == a.sect]
        if mine and a.realm >= PETITION_MIN_REALM and a.age >= 14:
            worst = min(mine, key=lambda pt: pt.place.prosperity)
            self._answer_petition(worst, a, ask=False)
            return
        lands = sorted(self.lands.values(), key=lambda l: l.wealth())
        lands = lands[:INJUSTICE_LANDS]
        weights = [ADVENTURE_HOME_BOOST
                   if a.home is not None and l is a.home.land else 1.0
                   for l in lands]
        land = r.choices(lands, weights)[0]
        self._act_adventure(a, share=share, dest=self._pick_home(land))

    # -- contests -----------------------------------------------------------

    def _bully_shakedown(self, a: Agent) -> bool:
        """§7: the tyranny of realms, pointed the wrong way.

        A Bully never picks a fight they can lose. They pick a junior, take
        what the junior is carrying, and leave behind exactly two things: a
        grudge, and the little insight that adversity always pays. The sim
        does not punish this — the victims do, eventually.
        """
        r = self.rng
        marks, weights = [], []
        for o in self.cultivators():
            if o.aid == a.aid or o.age < 14 or o.realm >= a.realm:
                continue
            marks.append(o)
            weights.append(BULLY_SAME_SECT if o.sect == a.sect else 1.0)
        if not marks:
            return False
        victim = r.choices(marks, weights)[0]
        taken = min(victim.resources, r.randint(*BULLY_TAKE))
        victim.resources -= taken
        a.resources += taken + self._vice_spoils(a)
        victim.insight += BULLY_INSIGHT
        self._add_grudge(victim, a, BULLY_GRUDGE)
        spoil = (f"{taken} in silver" if taken
                 else "nothing, and beat them for having nothing")
        self._record_deed(a, "cruelty")
        self.log(r.choice(BULLY_LINES).format(
            bully=a.display(), victim=victim.display(), spoil=spoil,
            sect=victim.sect or "the outer court"), [a, victim])
        self._mutate(victim, "humiliated")
        return True

    def _maim(self, winner: Agent, loser: Agent, where: str) -> bool:
        """§7: a Cruel victor does not stop at winning.

        The victim walks out of it with an epithet, a heavier burden and the
        insight that adversity pays — which is how the sim ends up full of
        walking evidence of somebody's character.
        """
        if not loser.alive or len(loser.epithets) >= 3:
            return False
        spare = [e for e in MAIM_EPITHETS if e not in loser.epithets]
        if not spare:
            return False
        ep = self.rng.choice(spare)
        loser.epithets.append(ep)
        loser.insight += CRUEL_MAIM_INSIGHT
        loser.burden += 1
        self._add_grudge(loser, winner, CRUEL_MAIM_GRUDGE)
        self._record_deed(winner, "cruelty")   # VII §2: the ledger
        self.log(f"{winner.display()} went on breaking {loser.name} after "
                 f"{where} was already decided; the mark will not come off "
                 f"[epithet: {ep}] (+insight).", [winner, loser],
                 dramatic=True)
        return True

    def _duel(self, att: Agent, dfn: Agent, lethal=False, context=""):
        """One formula, with the tyranny of realms."""
        r = self.rng
        gap = att.realm - dfn.realm
        ctx = f" over {context}" if context else ""
        # §7: Bloodthirsty escalates. A matter of face becomes a killing
        # matter because one of the two wanted it to be.
        edge = ""
        if not lethal and r.random() < BLOODTHIRSTY_LETHAL and (
                att.has_trait("Bloodthirsty") or dfn.has_trait("Bloodthirsty")):
            lethal = True
            edge = "; one of them had come to kill, not to win"

        if abs(gap) >= 1:
            strong, weak = (att, dfn) if gap > 0 else (dfn, att)
            flee = 0.5 + (0.25 if weak.has_trait("Cautious") else 0)
            if abs(gap) >= 2:
                flee -= 0.25
            if lethal and r.random() > flee:
                strong.resources += self._vice_spoils(strong)
                self._karma_kill(strong, weak)  # §7: killing the defenseless
                self._record_deed(strong, "blood")
                self.log(f"{strong.display()} struck down {weak.display()}"
                         f"{ctx} — a full realm between them left no "
                         f"contest{edge}.", [strong, weak], dramatic=True)
                self.kill(weak, f"killed by {strong.display()}", killer=strong)
            else:
                weak.insight += 3
                self._add_grudge(weak, strong, 2)
                self.log(f"{weak.display()} fled before {strong.display()}"
                         f"{ctx}; the humiliation cuts deep (+insight).",
                         [strong, weak])
                self._mutate(weak, "humiliated")
            return

        pa, pb = att.power(), dfn.power()
        att_wins = r.random() < pa / (pa + pb)
        winner, loser = (att, dfn) if att_wins else (dfn, att)
        winner.standing += 1
        winner.resources += self._vice_spoils(winner)   # §7: spoils to the bone

        kill_chance = 0.0
        if lethal:
            kill_chance = 0.55
            if winner.has_trait("Ruthless"):
                kill_chance = 0.85
            if winner.has_trait("Bloodthirsty"):
                kill_chance = 0.9
            if winner.has_trait("Righteous"):
                kill_chance = 0.25
        if r.random() < kill_chance:
            self._record_deed(winner, "blood")
            self.log(f"{winner.display()} defeated and slew {loser.display()}"
                     f"{ctx}{edge}.", [winner, loser], dramatic=True)
            self.kill(loser, f"slain in a duel by {winner.display()}",
                      killer=winner)
        else:
            loser.insight += 3
            self._add_grudge(loser, winner, 2)
            spared = ""
            if lethal:
                winner.karma += KARMA_SPARE     # §7: sparing a beaten foe
                self._record_deed(winner, "mercy")
                spared = ", spared where the next blow would have finished it"
            self.log(f"{winner.display()} defeated {loser.display()}{ctx}; "
                     f"{loser.display()} survives, shamed{spared} (+insight).",
                     [winner, loser])
            if winner.has_trait("Cruel") and r.random() < CRUEL_MAIM_CHANCE:
                self._maim(winner, loser, "the duel")
            self._mutate(loser, "humiliated")

    # -- event phase --------------------------------------------------------

    def _plan_year(self):
        """Roll the YEAR AGENDA (VII §1) and stamp every item with a season.

        Some items carry their whole decision — who declares war on whom,
        which champion a rising found, who rides for a plea, who is drawn
        into a secret realm; the rest carry only the fact that their check
        happens this year, and roll their details when the season comes.
        Either way the engine knows what the year holds, which is what lets
        a timeskip stop the season BEFORE something interesting.
        """
        r = self.rng
        self.agenda = []
        if self.feud_cooldown > 0:
            self.feud_cooldown -= 1

        def add(kind, payload=None, fields=None):
            season = AGENDA_SEASON.get(kind) or r.choice(SEASONS)
            item = AgendaItem(kind=kind, season=season, payload=payload or {})
            template = AGENDA_NOTICES.get(kind)
            if template is not None and fields is not None:
                item.notice = template.format(season=season, **fields)
            item.hard = self._foreseen_hard(item)
            self.agenda.append(item)
            return item

        add("politics")

        # §9: the campaigns already in the field, and the one this year's
        # restless court may start. A war declared this summer still does
        # not fight until next year's campaign item, exactly as before.
        for war in list(self.wars):
            att = self.polities.get(war.attacker)
            dfn = self.polities.get(war.defender)
            add("campaign", {"war": war},
                {"att": att.domain if att else "the armies",
                 "dfn": dfn.domain if dfn else "the enemy"})
        declaration = self._plan_declare_war()
        if declaration is not None:
            att, dfn, kind = declaration
            add("war", {"attacker": att.pid, "defender": dfn.pid,
                        "kind": kind},
                {"att": att.domain, "dfn": dfn.domain})

        # The muster is a NOTICE, not an event: the levies stand there all
        # season and it is the player who decides whether to ride. NPCs
        # answer it in their own action phase, as they always have.
        home_polity = (self.polity_at(self.pc.home)
                       if self.pc is not None else None)
        if home_polity is not None and (
                self._war_of(home_polity) is not None
                or "CONSCRIPTION" in home_polity.last_facets):
            add("muster", {"polity": home_polity.pid},
                {"domain": home_polity.domain})

        for polity, leader, champion in self._plan_revolts():
            add("revolt", {"polity": polity.pid, "leader": leader.aid,
                           "champion": champion.aid if champion else None},
                {"domain": polity.domain, "ruler": self.ruler_ref(leader)})

        add("assassination")
        add("usurpation")
        add("sect")             # §11: the head's character on the sect

        # The contact surface: a plea that has found its champion is stamped
        # (which is what makes "an assigned petition" a HARD interrupt);
        # lapses and fresh riders keep to their own season.
        for petition in list(self.petitions):
            if self.year - petition.year >= PETITION_LAPSE:
                continue    # this one runs out of time first (below)
            hero = self._plan_petition_answer(petition)
            if hero is not None:
                add("answer", {"petition": petition, "hero": hero.aid},
                    {"sect": petition.sect, "where": petition.place.name})
        add("petition")

        if self.year % TOURNAMENT_PERIOD == 0:
            add("tournament", {}, {})
        if self.year >= self.next_expedition:
            volunteers = self._plan_expedition()
            self.next_expedition = self.year + r.randint(4, 9)
            if volunteers:
                add("expedition", {"volunteers": [a.aid for a in volunteers]},
                    {})
        if self.feud_cooldown <= 0:
            pair = self._feud_pair()
            if pair is not None:
                add("feud", {"pair": pair}, {"s1": pair[0], "s2": pair[1]})
        for foe in self._plan_grudges():
            add("grudge", {"foe": foe.aid}, {"foe": foe.display()})

    def _resolve_agenda(self, item: AgendaItem):
        """Run one agenda item in its stamped season.

        Everything here re-checks the world before it fires: a leader planned
        against in spring may be dead by summer, and the agenda is a
        forecast, not a promise.
        """
        kind, p = item.kind, item.payload
        if kind == "politics":
            self._politics_phase()
        elif kind == "campaign":
            war = p["war"]
            if war in self.wars:
                self._war_year(war)
        elif kind == "war":
            att = self.polities.get(p["attacker"])
            dfn = self.polities.get(p["defender"])
            att_lord = self.leader_of(att)
            def_lord = self.leader_of(dfn)
            if (att is not None and dfn is not None
                    and not att.at_war and not dfn.at_war
                    and att_lord is not None and att_lord.alive
                    and def_lord is not None and def_lord.alive):
                self._declare_war(att, dfn, p["kind"])
        elif kind == "muster":
            return          # a standing offer to the player, not an event
        elif kind == "revolt":
            polity = self.polities.get(p["polity"])
            leader = self.agents.get(p["leader"])
            if (polity is None or leader is None or not leader.alive
                    or polity.leader != leader.aid):
                return      # the seat this rising was aimed at is gone
            champion = self.agents.get(p["champion"]) if p["champion"] else None
            if champion is not None and (not champion.alive
                                         or champion.is_ruler()):
                champion = None
            self._revolt(polity, leader, champion)
        elif kind == "assassination":
            self._maybe_assassinate()
        elif kind == "usurpation":
            self._maybe_usurp()
        elif kind == "sect":
            self._sect_year()
        elif kind == "answer":
            petition, hero = p["petition"], self.agents.get(p["hero"])
            if (petition in self.petitions and hero is not None
                    and hero.alive and not hero.is_ruler()):
                self._answer_petition(petition, hero)
        elif kind == "petition":
            self._lapse_petitions()
            self._maybe_petition()
        elif kind == "tournament":
            self._tournament()
        elif kind == "expedition":
            drawn = [self.agents[aid] for aid in p["volunteers"]
                     if self.agents[aid].alive
                     and not self.agents[aid].is_ruler()]
            if drawn:
                self._run_expedition(drawn)
        elif kind == "feud":
            self._run_feud(*p["pair"])
        elif kind == "grudge":
            self._grudge_comes(self.agents.get(p["foe"]))

    # -- the interrupt table (VII §3) ---------------------------------------

    def _pc_touched(self, polity: Optional[Polity]) -> bool:
        """Is this polity the played character's own country — the seat over
        their home, or a court of their home land?"""
        pc = self.pc
        if polity is None or pc is None or pc.home is None:
            return False
        return (self.polity_at(pc.home) is polity
                or polity.land is pc.home.land)

    def _foreseen_hard(self, item: AgendaItem) -> bool:
        """VII §3: is this a HARD interrupt the agenda can SEE COMING?

        These are what a timeskip stops for, and it stops on the EVE — the
        season before the item fires. The HARD interrupts nothing can
        foresee (a friend killed, a seat overturned, the home village
        falling below desperate) are caught at the season boundary instead,
        by `pc_alarms`.
        """
        pc = self.pc
        if pc is None or not pc.alive:
            return False
        kind, p = item.kind, item.payload
        if kind == "grudge":
            return True
        if kind == "tournament":
            band = sum(1 for a in self.cultivators()
                       if a.realm == pc.realm and a.age >= 14)
            return pc.age >= 14 and pc.realm <= 4 and band >= 4
        if kind == "expedition":
            return pc.aid in p.get("volunteers", ())
        if kind == "feud":
            return pc.sect in p.get("pair", ())
        if kind == "answer":
            return p.get("hero") == pc.aid
        if kind == "muster":
            return self._pc_touched(self.polities.get(p.get("polity")))
        if kind == "war":
            return (self._pc_touched(self.polities.get(p.get("attacker")))
                    or self._pc_touched(self.polities.get(p.get("defender"))))
        if kind == "campaign":
            war = p.get("war")
            if war is None:
                return False
            if any(pc.aid in riders for riders in war.enlisted.values()):
                return True
            return (self._pc_touched(self.polities.get(war.attacker))
                    or self._pc_touched(self.polities.get(war.defender)))
        if kind == "revolt":
            return (p.get("champion") == pc.aid
                    or self._pc_touched(self.polities.get(p.get("polity"))))
        return False

    def pc_watch(self) -> dict:
        """A snapshot of the things a timeskip watches between seasons."""
        pc = self.pc
        if pc is None:
            return {}
        close = {}
        for aid, rel in pc.rels.items():
            if rel.intensity < WITNESS_REL_INTENSITY:
                continue
            other = self.agents.get(aid)
            if other is not None:
                close[aid] = other
        ruler = self.ruler_at(pc.home)
        return {"alive": {aid: a.alive for aid, a in close.items()},
                "marks": {aid: len(a.epithets) for aid, a in close.items()},
                "ruler": ruler.aid if ruler is not None else None,
                "home": pc.home.prosperity if pc.home is not None else 10.0}

    def pc_alarms(self, before: dict) -> list:
        """VII §3, the HARD interrupts nothing could foresee: what has just
        happened to the played character that a timeskip must wake for."""
        pc = self.pc
        out: list = []
        if pc is None or not before:
            return out
        for aid, was_alive in before.get("alive", {}).items():
            other = self.agents.get(aid)
            if was_alive and other is not None and not other.alive:
                out.append(f"{other.display()} is dead")
        for aid, marks in before.get("marks", {}).items():
            other = self.agents.get(aid)
            if other is not None and other.alive and len(other.epithets) > marks:
                out.append(f"{other.display()} was maimed")
        ruler_before = before.get("ruler")
        ruler_now = self.ruler_at(pc.home)
        now_aid = ruler_now.aid if ruler_now is not None else None
        if ruler_before is not None and now_aid != ruler_before:
            old = self.agents.get(ruler_before)
            where = pc.home.land.name if pc.home is not None else "their land"
            out.append(f"{old.display() if old else 'the ruler'} no longer "
                       f"holds the seat over {where}")
        home_now = pc.home.prosperity if pc.home is not None else 10.0
        if home_now < HOME_DESPERATE <= before.get("home", 10.0):
            out.append(f"{pc.home.name} has fallen below desperate")
        if (pc.qi >= 100 and pc.realm < MAX_REALM
                and pc.insight >= INSIGHT_REQ[pc.realm]):
            out.append(f"the way to {REALM_NAMES[pc.realm + 1]} is open — "
                       f"the tribulation waits at the turn of the year")
        return out

    def agenda_notices(self, season: Optional[str] = None) -> list:
        """What the player is told is coming: their own HARD interrupts, and
        the handful of things the whole world can see."""
        out = []
        for item in self.agenda:
            if not item.notice:
                continue
            if season is not None and SEASONS.index(item.season) \
                    < SEASONS.index(season):
                continue        # already happened
            if item.hard or item.kind in AGENDA_PUBLIC:
                out.append(item.notice)
        return out

    # -- the deed ledger (VII §2) -------------------------------------------

    def _record_deed(self, a: Optional[Agent], kind: str):
        """File a deed. Every agent keeps the ledger; in P1 only the PLAYED
        character mutates off it (NPC mutation stays trigger-driven, and the
        session-7 aggregates with it)."""
        if a is None or not a.alive:
            return
        a.deeds.append((self.year, kind))

    def _deed_mutation(self, a: Agent):
        """VII §2: fight murderous three times in five years and the
        Bloodthirsty roll comes for you; pull three villages out of the fire
        and Righteous does. The world writes on the player exactly as it
        writes on everyone — it just reads the record instead of the dice."""
        a.deeds = [(y, k) for y, k in a.deeds
                   if self.year - y <= DEED_WINDOW]
        counts: dict = {}
        for _, kind in a.deeds:
            counts[kind] = counts.get(kind, 0) + 1
        for kind, trait in DEED_TRAITS.items():
            if counts.get(kind, 0) < DEED_THRESHOLD:
                continue
            if a.has_trait(trait) or trait not in ACQUIRABLE_TRAITS:
                continue
            self._mutate(a, "deeds", sure=True, deed_trait=trait)
            a.deeds = [(y, k) for y, k in a.deeds if k != kind]
            return          # one change a year is plenty

    def ask_player(self, kind: str, prompt: str, options: list,
                   default: str) -> str:
        """Put a question to the human, if there is one.

        The kernel calls this wherever it would otherwise roll FOR the played
        character — leaving the path, an offered seat, an assigned plea. With
        no player attached it returns the default and the roll stands, which
        is why observer and batch runs are unchanged. UI input never touches
        `world.rng`.
        """
        if not self.playing or self.ask is None:
            return default
        answer = self.ask(kind, prompt, options, default)
        return answer if answer in options else default

    # -- politics: rule style, edicts, tribute, succession ------------------

    def _politics_phase(self):
        """Every secular polity has a year: its leader's character becomes
        policy, standing edicts grind, and vassals pay their tribute."""
        for polity in self.ruling_polities():
            leader = self.leader_of(polity)
            if leader is None or not leader.alive:
                continue
            self._rule_year(polity, leader)
        self._tribute()

    def _facet_scores(self, polity: Polity, leader: Agent) -> dict:
        scores = {}
        for facet in RULE_FACETS:
            table = RULE_FACET_TRAITS[facet]
            scores[facet] = sum(w for t, w in table.items()
                                if leader.has_trait(t))
        if leader.age >= NEGLECT_AGE_FRACTION * leader.lifespan:
            scores["NEGLECTFUL"] += NEGLECT_AGE_SCORE
        # An angry country hardens a ruler who was already hard; a decent one
        # answers it with bread, not the headsman.
        if polity.unrest >= CRACKDOWN_UNREST and scores["CRUEL"] > 0:
            scores["CRUEL"] += CRACKDOWN_SCORE
        if leader.resources <= POOR_TREASURY:
            scores["EXTRACTIVE"] += POOR_TREASURY_SCORE
        # Levies are raised at war, or by a ruler who likes the sound of it.
        if polity.at_war or leader.has_trait("Bloodthirsty"):
            scores["CONSCRIPTION"] += CONSCRIPTION_BASE
        else:
            scores["CONSCRIPTION"] = 0
        return scores

    def _remember(self, land: Optional[Place], clause: str):
        """File an upheaval under the land it happened in. Nothing reads this
        but the final report — it is the world's memory, not its state."""
        if land is None:
            return
        self.upheavals.append((self.year, land.name, clause))

    def _shift_prosperity(self, polity: Polity, delta: float):
        for p in polity.settlements():
            p.prosperity = max(0.0, min(10.0, p.prosperity + delta))

    def _rule_year(self, polity: Polity, leader: Agent):
        r = self.rng
        # Ordinary revenue: the seat is worth holding, and a rich country is
        # worth more. (This is what tribute is paid out of.)
        leader.resources += RULER_INCOME
        if polity.wealth() >= RULER_INCOME_RICH_AT:
            leader.resources += RULER_INCOME_RICH
        scores = self._facet_scores(polity, leader)
        best = max(scores.values())
        fired = [f for f in RULE_FACETS if scores[f] == best and best > 0]
        fired = fired[:MAX_FACETS_PER_YEAR]

        for facet in fired:
            eff = RULE_FACET_EFFECTS[facet]
            self._shift_prosperity(polity, eff["prosperity"])
            polity.unrest = min(UNREST_MAX, polity.unrest + eff["unrest"])
            leader.karma += eff["karma"]
            leader.standing += eff.get("standing", 0)
            if "resources" in eff:
                leader.resources += r.randint(*eff["resources"])
            if "army" in eff:
                polity.army += r.randint(*eff["army"])
            if facet in ("EXTRACTIVE", "CRUEL"):
                # The corruption clock: a throne that takes, takes more.
                leader.extraction_years += 1
            if facet == "CRUEL":
                self._cruel_grudges(polity, leader)
            # News is a change of course, not a repetition of it.
            if (facet not in polity.last_facets
                    or r.random() < RULE_LINE_REPEAT_CHANCE):
                choices = [t for t in RULE_LINES[facet]
                           if t != polity.last_line] or RULE_LINES[facet]
                template = r.choice(choices)
                polity.last_line = template
                self.log(template.format(ruler=self.ruler_ref(leader),
                                         domain=polity.domain),
                         [leader], place=polity.seat)

        if not fired or "BENEVOLENT" in fired:
            polity.unrest = max(0, polity.unrest - UNREST_DECAY)
        polity.last_facets = tuple(fired)
        # A reign can hold two moods at once: "benevolent/extractive" is the
        # king who builds the dikes and sells the harvest to pay for them.
        polity.style = "/".join(STYLE_WORDS[f] for f in fired) or STYLE_QUIET

        good_year = "BENEVOLENT" in fired or (not fired and polity.unrest == 0)
        self._edict_year(polity, leader, good_year)

    def _cruel_grudges(self, polity: Polity, leader: Agent):
        """Cruelty is remembered by the cultivators born under it."""
        for a in self.cultivators():
            if a.home is None or a.aid == leader.aid:
                continue
            if self.polity_at(a.home) is not polity:
                continue
            rel = a.rels.get(leader.aid)
            if rel is not None and rel.intensity >= CRUEL_GRUDGE_MAX:
                continue
            self._add_grudge(a, leader, 1)

    # -- edicts -------------------------------------------------------------

    def _draw_edict(self, polity: Polity) -> Optional[Edict]:
        r = self.rng
        held = {e.label for e in polity.edicts}
        choices = [t for t in EDICT_TEMPLATES if t[0] not in held]
        if not choices:
            return None
        label, clause = r.choice(choices)
        if "{god}" in clause:
            others = [l for l in self.lands.values()
                      if l is not polity.land and l.name in LAND_GODS]
            foreign = r.choice(others)
            clause = clause.format(god=LAND_GODS[foreign.name],
                                   land=foreign.name)
        return Edict(label=label, clause=clause, year=self.year)

    def _edict_year(self, polity: Polity, leader: Agent, good_year: bool):
        r = self.rng
        # Standing edicts grind on the country every year they stand.
        if polity.edicts:
            self._shift_prosperity(polity, EDICT_PROSPERITY * len(polity.edicts))
            polity.unrest = min(UNREST_MAX,
                                polity.unrest + EDICT_UNREST * len(polity.edicts))

        points = sum(1 for t in ("Proud", "Cold") if leader.has_trait(t))
        points += sum(1 for t in leader.traits if t in VICE_TRAITS)
        if points and len(polity.edicts) < EDICT_MAX_ACTIVE \
                and r.random() < EDICT_CHANCE_PER_POINT * points:
            edict = self._draw_edict(polity)
            if edict is not None:
                polity.edicts.append(edict)
                self.log(f"{self.ruler_ref(leader)} decreed {edict.clause}; "
                         f"heralds carried the order into every village of "
                         f"{polity.domain}.", [leader],
                         place=polity.seat, world_event=polity.is_sovereign())
                self._propagate_mandate(polity, edict)

        # A ruler who is not Stubborn can be talked out of an OLD rule; this
        # year's proclamation is still fresh enough to be worth enforcing.
        old = [e for e in polity.edicts if e.year < self.year]
        if (old and good_year and not leader.has_trait("Stubborn")
                and r.random() < EDICT_REPEAL_CHANCE):
            edict = r.choice(old)
            polity.edicts.remove(edict)
            self.log(f"{self.ruler_ref(leader)} let {edict.label} lapse after "
                     f"{self.years_phrase(self.year - edict.year)}.", [leader],
                     place=polity.seat, world_event=polity.is_sovereign())

    def _propagate_mandate(self, liege: Polity, edict: Edict):
        """A liege's edict reaches each vassal court on a coin-flip."""
        r = self.rng
        for pid in liege.vassals:
            vassal = self.polities.get(pid)
            if vassal is None or len(vassal.edicts) >= EDICT_MAX_ACTIVE:
                continue
            if any(e.label == edict.label for e in vassal.edicts):
                continue
            if r.random() >= MANDATE_CHANCE:
                continue
            vassal.edicts.append(Edict(label=edict.label, clause=edict.clause,
                                       year=self.year, mandate_from=liege.pid))
            vleader = self.leader_of(vassal)
            if vleader is None or not vleader.alive:
                continue
            self.log(f"{self.ruler_ref(vleader)} enforced {edict.label} at "
                     f"the order of the {liege.name}.",
                     [vleader], place=vassal.seat)

    # -- tribute and succession ---------------------------------------------

    def _tribute(self):
        for polity in self.polities.values():
            if polity.liege is None or polity.kind == "sect":
                continue
            liege = self.polities.get(polity.liege)
            vassal_lord = self.leader_of(polity)
            liege_lord = self.leader_of(liege)
            if not (vassal_lord and liege_lord
                    and vassal_lord.alive and liege_lord.alive):
                continue
            if self._maybe_defy(polity, liege, vassal_lord, liege_lord):
                continue
            paid = min(TRIBUTE, vassal_lord.resources)
            vassal_lord.resources -= paid
            liege_lord.resources += paid

    def _maybe_defy(self, vassal: Polity, liege: Polity, lord: Agent,
                    liege_lord: Agent) -> bool:
        """A vassal keeps the tribute and sends no explanation with it.

        This is the betrayal §4 names as one of the few adversities a throne
        can actually learn from, and the quarrel a war of vassalage (§9)
        is declared over.
        """
        r = self.rng
        rel = lord.rels.get(liege_lord.aid)
        grudge = (rel.intensity if rel is not None
                  and rel.kind in HOSTILE_KINDS else 0)
        w = grudge * DEFIANCE_GRUDGE_WEIGHT
        if any(lord.has_trait(t) for t in DEFIANCE_TRAITS):
            w += 1.0
        if lord.realm > liege_lord.realm:
            w += 1.0        # the tyranny of realms, pointed upward
        if w <= 0 or r.random() >= DEFIANCE_CHANCE * w:
            return False
        liege.unrest = min(UNREST_MAX, liege.unrest + DEFIANCE_UNREST)
        self._add_grudge(liege_lord, lord, 2)
        self._governance_insight(liege_lord, "betrayal")
        # An open quarrel, remembered: this is what a war of vassalage is
        # declared over (§9), for as long as the liege keeps caring.
        vassal.defiance_year = self.year
        self.log(f"{self.ruler_ref(lord)} sent no tribute to the "
                 f"{liege.name} this year, and no explanation with it; "
                 f"{self.ruler_ref(liege_lord)} learned what a vassal's word "
                 f"is worth (+insight).", [lord, liege_lord],
                 place=vassal.seat)
        return True

    def reign_length(self, a: Agent) -> int:
        start = a.reign_start if a.reign_start is not None else self.year
        return max(0, (a.death_year if a.death_year is not None
                       else self.year) - start)

    @staticmethod
    def years_phrase(n: int) -> str:
        return "a single year" if n == 1 else f"{n} years"

    def _polity_succession(self, polity: Polity, outgoing: Agent,
                           cause: str = "death"):
        """A seat falls vacant and is filled.

        The default heir is a courtier out of the household — but a vacant
        throne is a door, and §9's ambitious cultivators walk through it: the
        stalled, the aging, the greedy, and the Righteous when (and only when)
        the land under it is visibly suffering. Failing a claim, a court left
        in disarray may look outside and invite a famous or native cultivator,
        who is free to refuse.
        """
        r = self.rng
        reign = self.reign_length(outgoing)
        ref = self.ruler_short(outgoing)    # the seat is named right after
        lapsed = len(polity.edicts)
        polity.edicts = []
        # A new face on the seat buys a honeymoon; the country remembers the
        # rest.
        polity.unrest = max(0, polity.unrest // 2 - SUCCESSION_UNREST_RELIEF)
        polity.last_facets = ()
        polity.leader = None
        if cause == "abdication":
            vacancy = (f"after {ref} laid it down, having ruled "
                       f"{self.years_phrase(reign)}")
        else:
            vacancy = (f"after the death of {ref}, who ruled "
                       f"{self.years_phrase(reign)}")
        tail = ""
        if lapsed:
            tail = (f" The {lapsed} standing edict"
                    f"{'s' if lapsed > 1 else ''} of the old court lapsed "
                    f"unenforced.")

        if self._throne_claim(polity, outgoing, vacancy, tail):
            return
        if self._throne_invitation(polity, vacancy, tail):
            return
        heir = self._install_ruler(polity, age=r.randint(*HEIR_AGE))
        self.log(f"{self.ruler_ref(heir)} took the seat of the "
                 f"{polity.name} {vacancy}.{tail}", [heir],
                 place=polity.seat, world_event=polity.is_sovereign())

    # -- the throne as an exit: claims, invitations, usurpation, abdication --

    def _seat(self, polity: Polity, a: Agent, came=THRONE_CAME_CLAIM):
        """Put a living agent on a throne.

        Everything else in the sim already routes around rulers — the action
        phase hands them the RULE action, and cultivators() keeps them out of
        tournaments, expeditions, petitions and the sect's own life — so this
        plus polity.leader is the whole transition. `came` is the road they
        took onto the seat, kept so the obituary can still name it.
        """
        a.ruling = polity.pid
        a.reign_start = self.year
        a.reign_came = came
        polity.leader = a.aid
        polity.last_facets = ()
        polity.style = STYLE_QUIET
        self._update_sect_heads()   # the sect finds someone else to lead

    def _step_down(self, a: Agent, how: str):
        """Take a living agent off a throne and file the reign away, so the
        obituary can still name it thirty years later."""
        polity = self.polities.get(a.ruling) if a.ruling is not None else None
        if polity is not None:
            a.past_reigns.append((polity.name, polity.domain,
                                  polity.title(a.sex), a.reign_start,
                                  self.year, how, a.reign_came))
        a.ruling = None
        a.reign_start = None
        a.reign_came = ""

    def _after_the_throne(self, a: Agent, how: str, polity: Polity):
        """Off the seat and still breathing.

        A cultivator walks back up the mountain with their qi exactly where
        the throne found it and a world that has moved on without them — the
        deposed king returning to the sect is a life the sim gets for free. A
        mortal notable has nowhere to go but exile.
        """
        years = self.years_phrase(
            self.year - (a.past_reigns[-1][3] if a.past_reigns else self.year))
        if a.sect:
            # A homecoming is a private thing: the coronation and the fall
            # were the world's business, this is the agent's own.
            a.insight += RETURN_INSIGHT
            self.log(f"{a.display()} came back to {a.sect} {how} the "
                     f"{polity.name}; {years} of the world had gone by "
                     f"without them, and their qi stood where they left it "
                     f"(+insight).", [a])
            self._update_sect_heads()
            return
        a.alive = False
        a.exited = True
        a.death_year = self.year
        a.death_cause = f"went into exile {how} the {polity.name}"
        self.log(f"{a.display()} left {polity.domain} for good {how} the "
                 f"{polity.name}, after {years} on the seat.", [a],
                 place=polity.seat, world_event=polity.is_sovereign())

    def _governance_insight(self, a: Optional[Agent], kind: str):
        """§4: the only insight a throne earns. A raid it could not punish, a
        vassal's word broken, an attempt on the seat survived, the seat lost.
        The event that caused it writes its own line; this only banks what the
        ruler learned. The two largest are a revolt survived and a war lost.
        """
        if a is None or not a.alive:
            return
        a.insight += GOVERNANCE_INSIGHT.get(kind, 0)

    def _claim_weight(self, a: Agent, polity: Polity,
                      outgoing: Agent) -> float:
        """How badly a cultivator wants a particular vacant seat. A stranger
        wants it not at all: it takes blood in that land, or a grudge against
        that court."""
        native = a.home is not None and a.home.land is polity.land
        rel = a.rels.get(outgoing.aid)
        grudge = rel is not None and rel.kind in HOSTILE_KINDS
        if not (native or grudge):
            return 0.0
        w = sum(m for t, m in CLAIM_TRAIT_WEIGHTS.items() if a.has_trait(t))
        if a.stalled():
            w += CLAIM_STALLED      # the door out of a path that has stopped
        if a.age >= CLAIM_AGING_AT * a.lifespan:
            w += CLAIM_AGING
        if native:
            w += CLAIM_NATIVE
        if grudge:
            w += CLAIM_GRUDGE
        # The idealist takeover: a Righteous cultivator wants no throne at all
        # until the country under it is visibly suffering.
        if a.has_trait("Righteous") and (
                polity.wealth() <= CLAIM_SUFFERING_AT
                or polity.unrest >= CLAIM_SUFFERING_UNREST):
            w += CLAIM_RIGHTEOUS
        # A Nascent Soul elder does not come down off the mountain to collect
        # a hearth tax. Thrones are claimed by the middle of the path — which
        # is also what keeps the sects' teachers on the mountain.
        return w * CLAIM_REALM_DAMP ** max(0, a.realm - CLAIM_MIN_REALM)

    def _throne_claim(self, polity: Polity, outgoing: Agent,
                      vacancy: str, tail: str) -> bool:
        """§9: an ambitious cultivator claims a vacant seat."""
        r = self.rng
        pool, weights = [], []
        for a in self.cultivators():
            if a.age < CLAIM_MIN_AGE or a.realm < CLAIM_MIN_REALM:
                continue
            w = self._claim_weight(a, polity, outgoing)
            if w <= 0:
                continue
            pool.append(a)
            weights.append(w)
        if not pool:
            return False
        if r.random() >= min(CLAIM_CHANCE_MAX,
                             CLAIM_CHANCE_PER_POINT * max(weights)):
            return False
        claimant = r.choices(pool, weights)[0]
        if self.playing and claimant is self.pc:
            # VII §2: a throne reaches the player as a choice, even when it
            # is their own ambition that walked them to the hall door.
            if self.ask_player(
                    "throne",
                    f"The seat of the {polity.name} is vacant, and your name "
                    f"is being put about for it. A crown freezes your qi for "
                    f"as long as you hold it.",
                    ["press", "stand aside"], "press") != "press":
                self.pc.thrones_refused += 1
                self.log(f"{self.pc.display()} let the seat of the "
                         f"{polity.name} pass without pressing a claim.",
                         [self.pc], place=polity.seat)
                return False

        rivals = [(a, w) for a, w in zip(pool, weights) if a is not claimant]
        if rivals and r.random() < CLAIM_CONTEST_CHANCE:
            other = r.choices([a for a, _ in rivals], [w for _, w in rivals])[0]

            def clout(x):
                return (x.realm * 8 + x.standing * CLAIM_CONTEST_STANDING
                        + r.uniform(0, CLAIM_CONTEST_NOISE)
                        + (4 if x.has_trait("Charming") else 0))

            winner, loser = ((claimant, other) if clout(claimant) >= clout(other)
                             else (other, claimant))
            self._seat(polity, winner, THRONE_CAME_CONTEST)
            # §9: a court that had to settle a claim by acclamation is a court
            # the neighbours look at. The war scan reads this.
            polity.crisis_year = self.year
            self._add_grudge(loser, winner, 3)
            self.log(f"{winner.display()} of {winner.sect}, "
                     f"{winner.realm_name}, took the seat of the "
                     f"{polity.name} {vacancy}; the claim of "
                     f"{loser.display()} was set aside before the assembled "
                     f"notables, who withdrew nursing a grudge.{tail}",
                     [winner, loser], dramatic=True, place=polity.seat,
                     world_event=polity.is_sovereign())
            self._mutate(loser, "passed_over")
            return True

        self._seat(polity, claimant)
        self.log(f"{claimant.display()} of {claimant.sect}, "
                 f"{claimant.realm_name}, claimed the seat of the "
                 f"{polity.name} {vacancy}; a cultivator sits where a "
                 f"mortal sat.{tail}",
                 [claimant], dramatic=True, place=polity.seat,
                 world_event=polity.is_sovereign())
        return True

    def _throne_invitation(self, polity: Polity, vacancy: str,
                           tail: str) -> bool:
        """§4/§9: a court with no heir it trusts sends for a cultivator.

        The offer is genuine and so is the refusal — a Nascent Soul does not
        sit on a mortal chair, and an Ascetic wants nothing to do with a
        treasury. Refusals are counted; the obituary remembers them.
        """
        r = self.rng
        chance = INVITE_CHANCE
        if polity.unrest >= INVITE_UNREST:
            chance += INVITE_UNREST_BONUS
        if r.random() >= chance:
            return False
        pool, weights = [], []
        for a in self.cultivators():
            if a.age < CLAIM_MIN_AGE or a.realm < INVITE_MIN_REALM:
                continue
            native = a.home is not None and a.home.land is polity.land
            if not native and a.standing < INVITE_MIN_STANDING:
                continue
            w = a.standing * INVITE_STANDING_WEIGHT
            if native:
                w += INVITE_NATIVE
            if a.realm >= FAME_REALM:
                w += INVITE_FAMOUS
            if w <= 0:
                continue
            pool.append(a)
            weights.append(w)
        if not pool:
            return False
        guest = r.choices(pool, weights)[0]

        refuse = INVITE_REFUSE_BASE
        refuse += sum(v for t, v in INVITE_REFUSE_TRAITS.items()
                      if guest.has_trait(t))
        refuse -= sum(v for t, v in INVITE_ACCEPT_TRAITS.items()
                      if guest.has_trait(t))
        refuse += INVITE_REFUSE_PER_REALM * (guest.realm - INVITE_MIN_REALM)
        turn_it_down = r.random() < max(0.05, min(0.95, refuse))
        if self.playing and guest is self.pc:
            # VII §2: thrones reach the player as real choices. A crown ends
            # cultivation while it lasts (§4) — that is the whole trade.
            turn_it_down = self.ask_player(
                "throne",
                f"The notables of {polity.domain} offer you the seat of the "
                f"{polity.name}. A crown freezes your qi for as long as you "
                f"hold it.",
                ["take", "refuse"], "refuse") != "take"
        if turn_it_down:
            guest.thrones_refused += 1
            self.log(f"The notables of {polity.domain} offered the seat of "
                     f"the {polity.name} to {guest.display()} of "
                     f"{guest.sect}, who refused it and went back to the "
                     f"mountain.", [guest], dramatic=True, place=polity.seat)
            return False
        self._seat(polity, guest, THRONE_CAME_INVITE)
        self.log(f"The notables of {polity.domain} offered the seat of the "
                 f"{polity.name} to {guest.display()} of {guest.sect}, "
                 f"{guest.realm_name}, {vacancy} — and the offer was "
                 f"taken.{tail}", [guest], dramatic=True, place=polity.seat,
                 world_event=polity.is_sovereign())
        return True

    def _maybe_usurp(self):
        """§4: the path onto a throne that does not wait for a funeral.

        Settled by the tyranny of realms — a mortal king cannot hold his seat
        against a Core Formation cultivator, and a cultivator-king can. Rare:
        one roll a year across all nine lands.
        """
        r = self.rng
        if r.random() >= USURP_CHANCE:
            return
        options, weights = [], []
        for a in self.cultivators():
            if a.realm < USURP_MIN_REALM or a.age < CLAIM_MIN_AGE:
                continue
            ambition = sum(m for t, m in USURP_TRAIT_WEIGHTS.items()
                           if a.has_trait(t))
            for polity in self.ruling_polities():
                leader = self.leader_of(polity)
                if leader is None or not leader.alive:
                    continue
                w = ambition
                rel = a.rels.get(leader.aid)
                if rel is not None and rel.kind in HOSTILE_KINDS:
                    w += USURP_GRUDGE_WEIGHT * rel.intensity
                if a.home is not None and a.home.land is polity.land:
                    w += USURP_NATIVE
                if a.realm <= leader.realm:
                    w *= USURP_OUTMATCHED   # few storm what they cannot take
                if w <= 0:
                    continue
                options.append((a, polity, leader))
                weights.append(w)
        if not options:
            return
        usurper, polity, leader = r.choices(options, weights)[0]
        ref = self.ruler_ref(leader)
        gap = usurper.realm - leader.realm
        if gap >= USURP_GAP_CERTAIN:
            chance = 1.0
        elif gap == 1:
            chance = USURP_GAP_ODDS
        else:
            opposition = (USURP_GUARD
                          + PETITION_OPPOSITION_PER_REALM * (leader.realm - 1)
                          + USURP_GUARD_PER_ARMY * polity.army)
            p = usurper.power()
            chance = max(USURP_ODDS[0],
                         min(USURP_ODDS[1], p / (p + opposition)))

        if r.random() >= chance:
            # The seat holds. Whoever sits on it has learned something about
            # holding it — governance adversity, the throne's only teacher.
            usurper.insight += USURP_FAIL_INSIGHT
            usurper.burden += 1
            self._add_grudge(usurper, leader, 3)
            self._add_grudge(leader, usurper, 3)
            self._governance_insight(leader, "usurpation")
            if r.random() < USURP_FAIL_DEATH:
                self.log(f"{usurper.display()}, {usurper.realm_name}, came "
                         f"for the seat of the {polity.name} and was cut "
                         f"down on its steps by the household of {ref}.",
                         [usurper, leader], dramatic=True, place=polity.seat,
                         world_event=polity.is_sovereign())
                self.kill(usurper, f"killed storming the seat of the "
                                   f"{polity.name}", killer=leader)
                return
            self.log(f"{usurper.display()}, {usurper.realm_name}, came for "
                     f"the seat of the {polity.name} and was driven off it "
                     f"by {ref}; both live, and neither forgets (+insight).",
                     [usurper, leader], dramatic=True, place=polity.seat,
                     world_event=polity.is_sovereign())
            self._mutate(usurper, "humiliated")
            return

        # The seat falls. Seat the usurper FIRST so the old ruler's death is a
        # death and not a second succession.
        usurper.karma += USURP_KARMA
        self._step_down(leader, "was cast down from")
        self._seat(polity, usurper, THRONE_CAME_USURP)
        # §6: edicts stand only until the ruler changes, and a new face on a
        # seat buys the same honeymoon a funeral would.
        polity.edicts = []
        polity.unrest = max(0, polity.unrest // 2 - SUCCESSION_UNREST_RELIEF)
        kill_chance = USURP_KILL_CHANCE
        if usurper.has_trait("Ruthless"):
            kill_chance = USURP_KILL_RUTHLESS
        if usurper.has_trait("Righteous"):
            kill_chance = USURP_KILL_RIGHTEOUS
        if r.random() < kill_chance:
            # §7: a beaten mortal king is as defenseless as anyone else.
            self._karma_kill(usurper, leader)
            self.log(f"{usurper.display()} of {usurper.sect}, "
                     f"{usurper.realm_name}, took the seat of the "
                     f"{polity.name} by force; {ref} did not live out the "
                     f"night.", [usurper, leader], dramatic=True,
                     place=polity.seat, world_event=polity.is_sovereign())
            self.kill(leader, f"cut down by {usurper.display()} in the taking "
                              f"of the {polity.name}", killer=usurper)
            return
        usurper.karma += USURP_SPARE_KARMA      # §7: sparing a beaten foe
        self.log(f"{usurper.display()} of {usurper.sect}, "
                 f"{usurper.realm_name}, took the seat of the {polity.name} "
                 f"by force and let {ref} walk out of the hall alive.",
                 [usurper, leader], dramatic=True, place=polity.seat,
                 world_event=polity.is_sovereign())
        self._governance_insight(leader, "deposition")
        self._after_the_throne(leader, "cast down from", polity)

    def _maybe_abdicate(self, a: Agent):
        """§4: the way off a throne that nobody forces."""
        r = self.rng
        polity = self.polities.get(a.ruling)
        if polity is None:
            return
        if self.playing and a is self.pc:
            return      # VII §2/§10: the player lays it down, or does not
        reign = self.reign_length(a)
        if reign < ABDICATE_MIN_REIGN:
            return
        chance = 0.0
        if any(a.has_trait(t) for t in ABDICATE_TRAITS):
            chance += ABDICATE_TRAIT_CHANCE
        if a.age >= ABDICATE_WEARY_AT * a.lifespan:
            chance += ABDICATE_WEARY_CHANCE
        if reign >= ABDICATE_LONG_REIGN:
            chance += ABDICATE_LONG_CHANCE
        if a.sect:
            chance += ABDICATE_CULTIVATOR_CHANCE    # the mountain still calls
        if not a.sect:
            chance *= ABDICATE_MORTAL_MULT
        if any(a.has_trait(t) for t in ABDICATE_HOLD_TRAITS):
            chance *= ABDICATE_HOLD_MULT
        if r.random() >= chance:
            return
        reason = r.choice([
            "laid the seat down and named no successor",
            "put off the seal and walked out of the hall",
            "abdicated, saying the country had had the best of them",
        ]) if not a.sect else r.choice([
            "laid the seat down for the path they had set aside",
            "put off the seal, saying a throne was a long detour",
            "abdicated with the mountain still unfinished",
        ])
        self.log(f"After {self.years_phrase(reign)} on the seat, "
                 f"{self.ruler_ref(a)} {reason}.", [a], dramatic=True,
                 place=polity.seat, world_event=polity.is_sovereign())
        self._polity_succession(polity, a, cause="abdication")
        self._step_down(a, "laid down")
        self._after_the_throne(a, "having laid down", polity)

    # -- consequences: revolts (§9) -----------------------------------------

    def _plan_revolts(self) -> list:
        """The valve unrest never had.

        Everything else in this layer pushes unrest up — cruelty, edicts,
        levies, a petition answered, a vassal's defiance — and until now only
        a funeral spent it, so bad courts simply pinned at the cap. Over the
        threshold, a country can rise in any year. Vassals rise as readily as
        sovereigns; only a sovereign's rising is world news (§12).

        VII §1: the risings of the year, and the champions who found them,
        are settled at year start; the agenda fires them in summer.
        """
        r = self.rng
        risings = []
        for polity in self.ruling_polities():
            if polity.unrest <= REVOLT_THRESHOLD:
                continue
            leader = self.leader_of(polity)
            if leader is None or not leader.alive:
                continue
            over = polity.unrest - REVOLT_THRESHOLD
            if r.random() < REVOLT_CHANCE_PER_UNREST * over:
                risings.append((polity, leader,
                                self._revolt_champion(polity, leader)))
        return risings

    def _revolt_champion(self, polity: Polity,
                         leader: Agent) -> Optional[Agent]:
        """§9: a living cultivator with a grudge against the ruler, or a
        Righteous one whose home lies in the territory. Nobody else has any
        business at the head of somebody else's rising."""
        r = self.rng
        pool, weights = [], []
        for a in self.cultivators():
            if a.age < REVOLT_MIN_AGE or a.realm < REVOLT_MIN_REALM:
                continue
            native = a.home is not None and self.polity_at(a.home) is polity
            rel = a.rels.get(leader.aid)
            grudge = rel is not None and rel.kind in HOSTILE_KINDS
            if not (grudge or (native and a.has_trait("Righteous"))):
                continue
            w = sum(m for t, m in REVOLT_TRAIT_WEIGHTS.items()
                    if a.has_trait(t))
            if native:
                w += REVOLT_HOME_WEIGHT
            if grudge:
                w += REVOLT_GRUDGE_WEIGHT * rel.intensity
            if w <= 0:
                continue
            pool.append(a)
            weights.append(w)
        if not pool or r.random() >= REVOLT_CHAMPION_CHANCE:
            return None
        return r.choices(pool, weights)[0]

    @staticmethod
    def _of_sect(a: Agent) -> str:
        return f" of {a.sect}" if a.sect else ""

    def _revolt(self, polity: Polity, leader: Agent,
                champion: Optional[Agent]):
        """One rising, settled by the tyranny of realms like everything else.

        A mortal tyrant falls to any Foundation Establishment champion. A
        cultivator-king does not fall at all — he turns the same rising into a
        massacre, and the country pays for having tried.

        The champion was picked when the year was planned (VII §1); None is
        a leaderless mob.
        """
        r = self.rng
        if self.playing and champion is self.pc:
            # VII §2: a revolt championship reaches the player as an offer,
            # not a draft. A refusal leaves the country its leaderless mob.
            if self.ask_player(
                    "revolt",
                    f"The country under {self.ruler_ref(leader)} is ready to "
                    f"rise, and is looking for someone to ride at the head "
                    f"of it.",
                    ["ride", "refuse"], "ride") != "ride":
                champion = None
        world = polity.is_sovereign()
        # These lines all name the domain themselves, so the ruler is named
        # without it: "the villages of the Wolf Steppe rose against Khan X".
        ref = self.ruler_short(leader)

        if champion is not None:
            # The tyranny of realms, in both directions: a realm over the seat
            # and the tyrant falls; a realm under it and a whole country at
            # your back is still not enough; two under and there is no contest
            # at all, only a massacre with a name at the front of it.
            gap = champion.realm - leader.realm
            if gap >= REVOLT_GAP_CERTAIN:
                chance = 1.0
            elif gap == 1:
                chance = REVOLT_GAP_ODDS
            elif gap <= -REVOLT_GAP_CERTAIN:
                chance = 0.0
            elif gap == -1:
                chance = REVOLT_UNDER_ODDS
            else:
                opposition = (REVOLT_GUARD
                              + REVOLT_GUARD_PER_REALM * (leader.realm - 1)
                              + REVOLT_GUARD_PER_ARMY * polity.army)
                strength = (champion.power()
                            + REVOLT_UNREST_HELP * polity.unrest)
                chance = max(REVOLT_ODDS[0],
                             min(REVOLT_ODDS[1],
                                 strength / (strength + opposition)))
            self.log(f"The {polity.word()} villages of {polity.domain} rose "
                     f"against {ref}, and {champion.display()}"
                     f"{self._of_sect(champion)}, {champion.realm_name}, rode "
                     f"at the head of them.", [leader, champion],
                     dramatic=True, place=polity.seat, world_event=world)
        else:
            # A mob is a mob. It can pull down a mortal magistrate and it can
            # do nothing whatever about a cultivator on a seat.
            chance = min(0.6, REVOLT_MOB_ODDS
                         + REVOLT_MOB_PER_UNREST * polity.unrest)
            if leader.realm > 1:
                chance = 0.0
            self.log(f"The {polity.word()} villages of {polity.domain} rose "
                     f"against {ref} with nobody at their head.", [leader],
                     dramatic=True, place=polity.seat, world_event=world)

        polity.army = max(0, int(polity.army * (1 - REVOLT_ARMY_LOSS)))
        if r.random() < chance:
            self._revolt_won(polity, leader, champion)
        else:
            self._revolt_crushed(polity, leader, champion)

    def _revolt_won(self, polity: Polity, leader: Agent,
                    champion: Optional[Agent]):
        """The seat falls. Empty it FIRST, so what happens to its holder next
        is a death and not a second succession."""
        r = self.rng
        world = polity.is_sovereign()
        ref = self.ruler_short(leader)
        self._step_down(leader, "was thrown down from")
        polity.leader = None
        polity.edicts = []
        polity.unrest = 0
        polity.last_facets = ()
        polity.style = STYLE_QUIET
        polity.crisis_year = self.year      # a new court is prey (§9, war)
        # The granaries come open the week the seat falls; a country that has
        # just thrown a tyrant down eats better for a season.
        self._shift_prosperity(polity, REVOLT_RELIEF)

        self._remember(polity.land,
                       f"{polity.domain} rose and threw down {ref}")
        crowned = None
        if champion is not None:
            champion.karma += REVOLT_KARMA          # §7: liberation
            champion.standing += PETITION_STANDING
            if TYRANT_BREAKER not in champion.epithets:
                champion.epithets.append(TYRANT_BREAKER)
            refuse = REVOLT_REFUSE_BASE
            refuse += sum(v for t, v in INVITE_REFUSE_TRAITS.items()
                          if champion.has_trait(t))
            refuse -= sum(v for t, v in INVITE_ACCEPT_TRAITS.items()
                          if champion.has_trait(t))
            refuse += INVITE_REFUSE_PER_REALM * (champion.realm
                                                 - INVITE_MIN_REALM)
            if r.random() >= max(0.05, min(0.95, refuse)):
                crowned = champion
                self._seat(polity, champion, THRONE_CAME_RISING)
                self.log(f"{champion.display()}{self._of_sect(champion)}, "
                         f"{champion.realm_name}, threw down {ref} and was "
                         f"raised to the seat of the {polity.name} by the "
                         f"country that rose with them "
                         f"[epithet: {TYRANT_BREAKER}].",
                         [champion], dramatic=True, place=polity.seat,
                         world_event=world)
            else:
                champion.thrones_refused += 1
                self.log(f"{champion.display()}{self._of_sect(champion)} "
                         f"threw down {ref} and would not take the seat after "
                         f"it [epithet: {TYRANT_BREAKER}].", [champion],
                         dramatic=True, place=polity.seat, world_event=world)
        if crowned is None:
            heir = self._install_ruler(polity, age=r.randint(*HEIR_AGE))
            self.log(f"{self.ruler_ref(heir)}, a notable of {polity.domain}, "
                     f"was raised to the seat of the {polity.name} by the "
                     f"risen villages.", [heir], place=polity.seat,
                     world_event=world)

        kill_chance = REVOLT_KILL_CHANCE
        if champion is not None:
            if champion.has_trait("Ruthless"):
                kill_chance = REVOLT_KILL_RUTHLESS
            if champion.has_trait("Righteous"):
                kill_chance = REVOLT_KILL_RIGHTEOUS
        if r.random() < kill_chance:
            if champion is not None:
                self._karma_kill(champion, leader)   # §7: the realms decide
            self.log(f"{ref} did not live out the rising in "
                     f"{polity.domain}.",
                     [leader], dramatic=True, place=polity.seat,
                     world_event=world)
            self.kill(leader, f"torn down with the seat of the {polity.name} "
                              f"in the rising of {polity.domain}",
                      killer=champion)
            return
        if champion is not None:
            champion.karma += KARMA_SPARE            # §7: a beaten foe spared
        self._governance_insight(leader, "revolt")
        self._after_the_throne(leader, "thrown down from", polity)

    def _revolt_crushed(self, polity: Polity, leader: Agent,
                        champion: Optional[Agent]):
        """The rising fails — and how badly depends entirely on what is
        sitting on the seat. A mortal court hangs the ringleaders. A
        cultivator-king walks into the crowd himself."""
        r = self.rng
        world = polity.is_sovereign()
        ref = self.ruler_short(leader)
        champ_realm = champion.realm if champion is not None else 1
        massacre = leader.realm > champ_realm
        leader.revolts_survived += 1
        self._governance_insight(leader, "revolt")

        # Who it reached: a cultivator born in that country whose own people
        # were among the ones left in the road. Not every native — the sim
        # does not track where anybody is standing, so the coin decides
        # whether the rising took their village or the next one over.
        witnesses = []
        for a in self.cultivators():
            if a.home is None or self.polity_at(a.home) is not polity:
                continue
            if champion is not None and a.aid == champion.aid:
                continue
            if r.random() >= REVOLT_WITNESS_CHANCE:
                continue
            witnesses.append(a)

        if massacre:
            self._shift_prosperity(polity, MASSACRE_PROSPERITY)
            leader.karma += MASSACRE_KARMA
            leader.extraction_years += 2
            polity.unrest = max(0, polity.unrest - MASSACRE_UNREST)
            for a in witnesses:
                a.insight += MASSACRE_INSIGHT
                self._add_grudge(a, leader, MASSACRE_GRUDGE)
            dead = r.randint(*MASSACRE_DEAD)
            self._remember(polity.land,
                           f"{ref} went into the risen villages of "
                           f"{polity.domain} in person, and some {dead:,} "
                           f"were killed")
            self.log(f"{ref}, {leader.realm_name}, went into the risen "
                     f"villages of {polity.domain} in person; some {dead:,} "
                     f"were killed and the country is {polity.word()} after "
                     f"it (survivors +insight, grudges).",
                     [leader] + witnesses, dramatic=True, place=polity.seat,
                     world_event=world)
        else:
            leader.karma += KARMA_KILL_DEFENSELESS
            self._shift_prosperity(polity, REVOLT_FAIL_PROSPERITY)
            polity.unrest = max(0, polity.unrest - REVOLT_FAIL_UNREST)
            for a in witnesses:
                a.insight += REVOLT_INSIGHT
                self._add_grudge(a, leader, 1)
            self._remember(polity.land,
                           f"the rising in {polity.domain} was broken up "
                           f"and its ringleaders hanged")
            self.log(f"The rising in {polity.domain} was broken up by the "
                     f"levies of {ref}; the ringleaders were hanged along the "
                     f"roads (survivors +insight).", [leader] + witnesses,
                     dramatic=True, place=polity.seat, world_event=world)

        if champion is None:
            return
        champion.insight += REVOLT_FAIL_INSIGHT
        champion.burden += 1
        self._add_grudge(champion, leader, 3)
        self._add_grudge(leader, champion, 2)
        death = REVOLT_FAIL_DEATH * (2.0 if massacre else 1.0)
        if r.random() < death:
            # §7: they died standing in front of somebody else's villages.
            self._fell_defending(champion, f"the villages of {polity.domain}")
            self.log(f"{champion.display()} was taken alive at the end of the "
                     f"rising in {polity.domain} and killed in front of the "
                     f"country they had raised.", [champion, leader],
                     dramatic=True, place=polity.seat, world_event=world)
            self.kill(champion, f"executed by {ref} after the rising of "
                                f"{polity.domain} failed", killer=leader)
            return
        self.log(f"{champion.display()} got out of {polity.domain} alive "
                 f"after the rising failed, hunted and no longer welcome in "
                 f"the country they raised (+insight).", [champion, leader],
                 dramatic=True, place=polity.seat)
        self._mutate(champion, "humiliated")

    # -- consequences: assassination (§9) -----------------------------------

    def _maybe_assassinate(self):
        """§9: a deeply evil reign draws knives.

        One roll a year across the whole world, against the blackest ledger on
        any seat, which is what keeps knives rarer than risings (§13). The bar
        is documented at ASSASSIN_KARMA: the rule facets move a ledger by a
        point or two EVERY YEAR, so the spec's literal -4 would fire on every
        disappointing king in the nine lands.
        """
        r = self.rng
        marks = []
        for polity in self.ruling_polities():
            leader = self.leader_of(polity)
            if leader is None or not leader.alive:
                continue
            if leader.karma > ASSASSIN_KARMA:
                continue
            marks.append((polity, leader))
        if not marks:
            return
        polity, leader = r.choices(
            marks, [float(-m[1].karma) for m in marks])[0]
        chance = min(ASSASSIN_CHANCE_MAX,
                     ASSASSIN_CHANCE + ASSASSIN_PER_KARMA
                     * (ASSASSIN_KARMA - leader.karma))
        if r.random() >= chance:
            return

        pool, weights = [], []
        for a in self.cultivators():
            if a.age < CLAIM_MIN_AGE:
                continue
            if abs(a.realm - leader.realm) > ASSASSIN_REALM_GAP:
                continue
            rel = a.rels.get(leader.aid)
            if (rel is None or rel.kind not in HOSTILE_KINDS
                    or rel.intensity < ASSASSIN_MIN_GRUDGE):
                continue
            w = (ASSASSIN_GRUDGE_WEIGHT * rel.intensity
                 + sum(m for t, m in ASSASSIN_TRAIT_WEIGHTS.items()
                       if a.has_trait(t)))
            if w <= 0:
                continue
            pool.append(a)
            weights.append(w)
        if not pool:
            return
        knife = r.choices(pool, weights)[0]

        odds = (ASSASSIN_BASE
                + ASSASSIN_PER_REALM * (knife.realm - leader.realm)
                - ASSASSIN_PER_ARMY * polity.army)
        if leader.has_trait("Cautious"):
            odds -= ASSASSIN_CAUTIOUS
        odds = max(ASSASSIN_ODDS[0], min(ASSASSIN_ODDS[1], odds))
        ref = self.ruler_ref(leader)
        world = polity.is_sovereign()
        where = polity.seat.name if polity.seat else polity.domain

        if r.random() < odds:
            knife.standing += 2
            self._karma_kill(knife, leader)
            self._remember(polity.land,
                           f"{ref} was murdered in the sleeping chamber at "
                           f"{where}")
            self.log(f"{knife.display()}{self._of_sect(knife)} came over the "
                     f"wall at {where} and killed {ref} in the sleeping "
                     f"chamber; a black ledger had been a long time drawing "
                     f"that knife.",
                     [knife, leader], dramatic=True, place=polity.seat,
                     world_event=world)
            # kill() carries the succession: a corpse on the floor of the hall
            # is still a vacancy, and the court fills it before morning.
            self.kill(leader, f"murdered on the seat of the {polity.name} by "
                              f"{knife.display()}", killer=knife)
            return

        knife.insight += ASSASSIN_FAIL_INSIGHT
        self._add_grudge(leader, knife, 3)
        polity.unrest = min(UNREST_MAX, polity.unrest + ASSASSIN_UNREST)
        self._governance_insight(leader, "assassination")
        if r.random() < ASSASSIN_CAUGHT:
            self.log(f"{knife.display()} was taken in the grounds of "
                     f"{where} with a knife meant for {ref}.", [knife, leader],
                     dramatic=True, place=polity.seat, world_event=world)
            self.kill(knife, f"executed for an attempt on {ref}", killer=leader)
            return
        self.log(f"An attempt was made on {ref} and failed; the court did "
                 f"not learn whose hand it was, and "
                 f"{self.ruler_short(leader)} has slept badly since "
                 f"(+insight).", [knife, leader], dramatic=True,
                 place=polity.seat, world_event=world)

    # -- consequences: war (§9) ---------------------------------------------

    def _war_of(self, polity: Polity) -> Optional[War]:
        for war in self.wars:
            if polity.pid in (war.attacker, war.defender):
                return war
        return None

    def _plan_declare_war(self) -> Optional[tuple]:
        """§9: between edge-adjacent sovereigns, and rarely across a corner.

        Started by a restless ruler with an army to spend; a court left weak
        by a contested succession is what one of them looks at, and a vassal
        that has kept the tribute one year too many is the other.

        VII §1: the decision is taken at year start and returned for the
        agenda to fire in summer, so the countries about to be invaded can
        be told the drums are beating.
        """
        r = self.rng
        if r.random() >= WAR_CHANCE:
            return None
        # Who is spoken for: the courts already in a war that will still be
        # running when this declaration fires in summer. A campaign that
        # ends this year frees its two crowns, and the planning knows it —
        # the old code saw the same thing by running after the campaigns.
        busy = set()
        for war in self.wars:
            if war.fought + 1 < war.length:
                busy.add(war.attacker)
                busy.add(war.defender)
        options, weights = [], []
        for polity in self.ruling_polities():
            if polity.pid in busy or polity.army < WAR_MIN_ARMY:
                continue
            leader = self.leader_of(polity)
            if leader is None or not leader.alive:
                continue
            appetite = sum(m for t, m in WAR_TRAIT_WEIGHTS.items()
                           if leader.has_trait(t))
            appetite += WAR_ARMY_WEIGHT * (polity.army - WAR_MIN_ARMY)
            if appetite <= 0:
                continue
            # The seam: a liege brings a defiant vassal back under the oath.
            for pid in polity.vassals:
                vassal = self.polities.get(pid)
                if vassal is None or pid in busy:
                    continue
                if vassal.defiance_year is None:
                    continue
                if self.year - vassal.defiance_year > DEFIANCE_MEMORY:
                    continue
                vlord = self.leader_of(vassal)
                if vlord is None or not vlord.alive:
                    continue
                options.append((polity, vassal, "vassalage"))
                weights.append(appetite + WAR_DEFIANCE_WEIGHT)
            if not polity.is_sovereign():
                continue
            for strong in (True, False):
                lands = self.neighbors(polity.land, strong=strong)
                for other in self.sovereigns():
                    if other.pid in busy or other.pid == polity.pid:
                        continue
                    if other.land not in lands:
                        continue
                    olord = self.leader_of(other)
                    if olord is None or not olord.alive:
                        continue
                    w = appetite
                    if (other.crisis_year is not None
                            and self.year - other.crisis_year
                            <= WAR_CRISIS_YEARS):
                        w += WAR_CRISIS_WEIGHT
                    w += WAR_WEAK_PREY * max(0, leader.realm - olord.realm)
                    if not strong:
                        w *= WAR_CORNER_CHANCE
                    if w <= 0:
                        continue
                    options.append((polity, other, "conquest"))
                    weights.append(w)
        if not options:
            return None
        return r.choices(options, weights)[0]

    def _declare_war(self, attacker: Polity, defender: Polity, kind: str):
        r = self.rng
        war = War(attacker=attacker.pid, defender=defender.pid,
                  year=self.year, length=r.randint(*WAR_LENGTH), kind=kind)
        war.score = {attacker.pid: 0.0, defender.pid: 0.0}
        war.enlisted = {attacker.pid: [], defender.pid: []}
        self.wars.append(war)
        attacker.at_war = True
        defender.at_war = True
        att_lord = self.leader_of(attacker)
        def_lord = self.leader_of(defender)
        lines = (WAR_VASSAL_DECLARE_LINES if kind == "vassalage"
                 else WAR_DECLARE_LINES)
        self._add_grudge(def_lord, att_lord, 3)
        self.log(r.choice(lines).format(att=self.ruler_ref(att_lord),
                                        def_dom=defender.domain,
                                        def_ruler=self.ruler_ref(def_lord)),
                 [att_lord, def_lord], dramatic=True, place=defender.seat,
                 world_event=True)

    def _war_year(self, war: War):
        """One campaigning season, resolved abstractly.

        The armies are numbers, and the conscripts who die by the thousand are
        chronicle colour — they were never agents. The cultivators who rode to
        it are agents, and the battlefield treats them exactly as the wilds do.
        """
        r = self.rng
        att = self.polities.get(war.attacker)
        dfn = self.polities.get(war.defender)
        if att is None or dfn is None:
            self._close_war(war)
            return
        att_lord = self.leader_of(att)
        def_lord = self.leader_of(dfn)
        if not (att_lord and att_lord.alive and def_lord and def_lord.alive):
            # A war does not outlive the court that wanted it.
            self._close_war(war)
            self.log(f"The war over {dfn.domain} came apart unfinished when "
                     f"one of the two seats fell vacant; the armies went "
                     f"home.", [], world_event=True)
            return
        war.fought += 1
        war.score[att.pid] += att.army + WAR_RULER_SCORE * (att_lord.realm - 1)
        war.score[dfn.pid] += dfn.army + WAR_RULER_SCORE * (def_lord.realm - 1)
        for polity, drop in ((att, WAR_PROSPERITY_ATT),
                             (dfn, WAR_PROSPERITY_DEF)):
            self._shift_prosperity(polity, drop)
            polity.unrest = min(UNREST_MAX, polity.unrest + WAR_UNREST)
            polity.army = max(0, int(polity.army
                                     * (1 - r.uniform(*WAR_ARMY_LOSS))))
        self._battle(war, att, dfn.domain)
        self._battle(war, dfn, dfn.domain)
        dead = r.randint(*WAR_CONSCRIPTS_DEAD)
        self.log(r.choice(WAR_CAMPAIGN_LINES).format(def_dom=dfn.domain,
                                                     dead=f"{dead:,}"),
                 [], place=dfn.seat, world_event=True)
        if war.fought >= war.length:
            self._end_war(war, att, dfn, att_lord, def_lord)

    def _battle(self, war: War, polity: Polity, over: str):
        """What the year did to the cultivators who signed on with this side."""
        r = self.rng
        riders = [self.agents[aid] for aid in war.enlisted.get(polity.pid, [])
                  if self.agents[aid].alive]
        war.enlisted[polity.pid] = []
        for a in riders:
            war.veterans.add(a.aid)
            war.score[polity.pid] += WAR_CULTIVATOR_SCORE * a.power()
            if r.random() < WAR_BATTLE_DEATH / a.realm:
                self.log(f"{a.display()} was killed in the fighting over "
                         f"{over}, one name in a casualty roll of thousands.",
                         [a], dramatic=True, place=polity.seat)
                self.kill(a, f"killed in the war over {over}")
                continue
            a.insight += WAR_BATTLE_INSIGHT
            if r.random() < WAR_SPOILS_CHANCE:
                a.resources += (r.randint(*WAR_BATTLE_SPOILS)
                                + self._vice_spoils(a))
                tail = "and took a share of what the army carried off"
                gain = " (+insight, +resources)"
            else:
                tail = "and came out of it with nothing but what they learned"
                gain = " (+insight)"
            self.log(f"{a.display()} came through a campaigning season over "
                     f"{over} {tail}{gain}.", [a])
            self._mutate(a, "near_death")

    def _close_war(self, war: War):
        if war in self.wars:
            self.wars.remove(war)
        for pid in (war.attacker, war.defender):
            polity = self.polities.get(pid)
            if polity is not None:
                polity.at_war = self._war_of(polity) is not None

    def _end_war(self, war: War, att: Polity, dfn: Polity,
                 att_lord: Agent, def_lord: Agent):
        r = self.rng
        sa = war.score[att.pid] * (1 + r.uniform(-WAR_SCORE_NOISE,
                                                 WAR_SCORE_NOISE))
        sd = war.score[dfn.pid] * (1 + r.uniform(-WAR_SCORE_NOISE,
                                                 WAR_SCORE_NOISE))
        self._close_war(war)
        years = self.years_phrase(war.fought)
        if war.kind == "vassalage":
            if sa >= sd:
                dfn.defiance_year = None
                dfn.unrest = min(UNREST_MAX, dfn.unrest + WAR_LOSER_UNREST)
                paid = min(def_lord.resources, r.randint(*WAR_TRIBUTE))
                def_lord.resources -= paid
                att_lord.resources += paid
                self._tally_war(att_lord, def_lord)
                self._remember(dfn.land,
                               f"{dfn.domain} was brought back under the "
                               f"oath of the {att.name}")
                self._remember(att.land,
                               f"the {att.name} brought {dfn.domain} back "
                               f"under the old oath")
                self._governance_insight(def_lord, "war_lost")
                self.log(f"After {years}, {self.ruler_ref(def_lord)} came to "
                         f"the camp of {self.ruler_ref(att_lord)} and swore "
                         f"the old oath again, with the arrears of tribute "
                         f"carried behind (+insight).",
                         [att_lord, def_lord], dramatic=True,
                         place=dfn.seat, world_event=True)
                return
            dfn.liege = None
            dfn.defiance_year = None
            if dfn.pid in att.vassals:
                att.vassals.remove(dfn.pid)
            att.unrest = min(UNREST_MAX, att.unrest + WAR_LOSER_UNREST)
            self._tally_war(def_lord, att_lord)
            self._remember(dfn.land, f"the {dfn.name} broke free of the "
                                     f"{att.name} and pays nobody")
            self._governance_insight(att_lord, "war_lost")
            self.log(f"After {years}, {self.ruler_ref(att_lord)} could not "
                     f"bring {dfn.domain} back under the oath; the "
                     f"{dfn.name} stands sovereign and pays nobody "
                     f"(+insight).", [att_lord, def_lord], dramatic=True,
                     place=dfn.seat, world_event=True)
            return

        winner, loser = (att, dfn) if sa >= sd else (dfn, att)
        win_lord = att_lord if winner is att else def_lord
        lose_lord = def_lord if winner is att else att_lord
        loser.unrest = min(UNREST_MAX, loser.unrest + WAR_LOSER_UNREST)
        loser.crisis_year = self.year
        self._tally_war(win_lord, lose_lord)
        self._remember(loser.land, f"{loser.domain} lost {years} of war "
                                   f"to the {winner.name}")
        if winner.land is not loser.land:
            self._remember(winner.land, f"the {winner.name} beat "
                                        f"{loser.domain} after {years} of "
                                        f"campaigning")
        self._governance_insight(lose_lord, "war_lost")
        self._shift_prosperity(winner, WAR_WINNER_PROSPERITY)
        win_lord.standing += 2

        outcomes = dict(WAR_OUTCOME_WEIGHTS)
        if not (loser.is_sovereign() and winner.is_sovereign()
                and loser.liege is None):
            outcomes.pop("vassalage", None)
        region = self._cedable_region(loser)
        if region is None:
            outcomes.pop("region", None)
        keys = list(outcomes)
        outcome = r.choices(keys, [outcomes[k] for k in keys])[0]

        if outcome == "vassalage":
            loser.liege = winner.pid
            winner.vassals.append(loser.pid)
            self.log(f"After {years}, {self.ruler_ref(lose_lord)} knelt to "
                     f"{self.ruler_ref(win_lord)}; the {loser.name} is a "
                     f"vassal of the {winner.name} and pays tribute to it "
                     f"(+insight).", [win_lord, lose_lord], dramatic=True,
                     place=loser.seat, world_event=True)
        elif outcome == "region":
            loser.territory.remove(region)
            winner.territory.append(region)
            region.polity = winner.pid
            winner.army += len(region.settlements())
            self.log(f"After {years}, the {region.name} was cut out of "
                     f"{loser.domain} and added to the {winner.name}; the "
                     f"villages there pay their hearth-tax to "
                     f"{self.ruler_ref(win_lord)} now (+insight).",
                     [win_lord, lose_lord], dramatic=True, place=region,
                     world_event=True)
        else:
            paid = min(lose_lord.resources, r.randint(*WAR_TRIBUTE))
            lose_lord.resources -= paid
            win_lord.resources += paid
            self.log(f"After {years}, {self.ruler_ref(lose_lord)} bought the "
                     f"armies of {self.ruler_ref(win_lord)} out of "
                     f"{loser.domain} with the treasury and what could be "
                     f"raised on top of it (+insight).",
                     [win_lord, lose_lord], dramatic=True, place=loser.seat,
                     world_event=True)

    @staticmethod
    def _tally_war(winner: Optional[Agent], loser: Optional[Agent]):
        """A campaign settled. Both counts are spent in the obituary: a
        throne is remembered by the wars it won and the ones it lost."""
        if winner is not None:
            winner.wars_won += 1
        if loser is not None:
            loser.wars_lost += 1

    def _cedable_region(self, polity: Polity) -> Optional[Place]:
        """A piece of a country that can change hands: anything in the
        territory that does not hold the seat."""
        if len(polity.territory) < 2:
            return None
        options = [p for p in polity.territory
                   if polity.seat is not p
                   and polity.seat not in p.settlements()
                   and p.settlements()]
        return self.rng.choice(options) if options else None

    # -- sects under the politics layer (§11) --------------------------------

    def _sect_year(self):
        """§11: headship is rulership-lite, and it shows in the accounts.

        The head's character tilts the sect's richness multiplier a few points
        either way — that multiplier is what every disciple's cultivation year
        is measured in — and drifts the juniors' standing with it. Nothing
        here asks whether anyone is the villain: it counts the same two trait
        sets karma counts, and the arithmetic does the rest.
        """
        r = self.rng
        for sect, base in self.sect_base.items():
            head = self.agents.get(self.sect_heads.get(sect))
            tilt = 0.0
            if head is not None and head.alive:
                virtue = sum(1 for t in head.traits if t in VIRTUE_TRAITS)
                vice = sum(1 for t in head.traits if t in VICE_TRAITS)
                tilt = max(-SECT_TILT_CAP,
                           min(SECT_TILT_CAP,
                               SECT_TILT_PER_TRAIT * (virtue - vice)))
            self.sects[sect] = base * (1.0 + tilt)
            if tilt == 0 or head is None or not head.alive:
                continue
            step = 1 if tilt > 0 else -1
            for a in self.cultivators():
                if (a.sect != sect or a.aid == head.aid
                        or a.realm > SECT_JUNIOR_REALM or a.age < 14):
                    continue
                if r.random() < SECT_STANDING_DRIFT:
                    a.standing = max(0, a.standing + step)

    def _maybe_defect(self, a: Agent) -> bool:
        """§11: under a vice-heavy head, the Righteous and the Humble leave.

        A defection is a voluntary exit that does NOT end a career — the
        defector goes on cultivating in somebody else's colours — and it seeds
        exactly the cross-sect grudge the feud arithmetic is already counting,
        which is how a bad headship becomes a sect war two decades later.
        """
        r = self.rng
        if not a.sect or a.age < DEFECT_MIN_AGE or a.realm < DEFECT_MIN_REALM:
            return False
        head = self.agents.get(self.sect_heads.get(a.sect))
        if head is None or not head.alive or head.aid == a.aid:
            return False
        vice = sum(1 for t in head.traits if t in VICE_TRAITS)
        if not vice:
            return False
        rel = a.rels.get(head.aid)
        grudge = rel is not None and rel.kind in HOSTILE_KINDS
        upright = any(a.has_trait(t) for t in DEFECT_TRAITS)
        if not upright and not (grudge and r.random() < DEFECT_GRUDGE_CHANCE):
            return False
        if r.random() >= DEFECT_CHANCE * vice:
            return False
        options, weights = [], []
        for sect in self.sects:
            if sect == a.sect:
                continue
            other = self.agents.get(self.sect_heads.get(sect))
            w = 1.0
            if other is not None and other.alive:
                w += sum(1 for t in other.traits if t in VIRTUE_TRAITS)
                w -= 0.5 * sum(1 for t in other.traits if t in VICE_TRAITS)
            options.append(sect)
            weights.append(max(0.2, w))
        if not options:
            return False
        new = r.choices(options, weights)[0]
        old = a.sect
        a.sect = new
        a.standing = max(0, a.standing - DEFECT_STANDING_COST)
        self._add_grudge(a, head, DEFECT_GRUDGE)
        self._add_grudge(head, a, 1)
        self.log(r.choice(DEFECT_LINES).format(
            who=a.display(), old=old, new=new, head=head.display()),
            [a, head], dramatic=(a.realm >= 3 or head.realm >= FAME_REALM))
        if r.random() < DEFECT_WELCOME_CHANCE:
            peers = [o for o in self.cultivators()
                     if o.sect == new and o.aid != a.aid
                     and abs(o.realm - a.realm) <= 1]
            if peers:
                other = r.choice(peers)
                self._bind(a, other, "ally", 2)
                self.log(f"{other.display()} of {new} stood surety for "
                         f"{a.display()} against the elders of {old}.",
                         [a, other])
        self._update_sect_heads()
        return True

    # -- petitions: the sect/polity interface (§9) ---------------------------

    # Starving villages beg the sects; the sects sometimes answer. This is
    # the only door between the spiritual exemption and the secular world, so
    # it is deliberately narrow: pleas lapse unheard, and at most one new one
    # is sent a year. VII §1 split the old phase in two — the champion a plea
    # finds is picked when the year is planned (so an assigned plea can wake
    # a timeskip on its eve), and lapses and fresh riders keep their own
    # season.

    def _lapse_petitions(self):
        for petition in list(self.petitions):
            if self.year - petition.year < PETITION_LAPSE:
                continue
            self.petitions.remove(petition)
            self.log(f"The plea of {petition.place.name} to "
                     f"{petition.sect} went unanswered for "
                     f"{self.years_phrase(self.year - petition.year)}; the "
                     f"village stopped sending riders.", [],
                     place=petition.place)

    def _petition_sect(self, land: Place) -> str:
        """Which sect a village begs: the one its own children went to."""
        counts = {sect: 1.0 for sect in self.sects}
        for a in self.cultivators():
            if a.sect in counts and a.home is not None and a.home.land is land:
                counts[a.sect] += 1.0
        names = list(counts)
        return self.rng.choices(names, [counts[s] for s in names])[0]

    def _maybe_petition(self):
        r = self.rng
        if r.random() >= PETITION_CHANCE:
            return
        if len(self.petitions) >= PETITION_MAX_OPEN:
            return
        candidates = [p for p in self.settlements()
                      if p.prosperity < PETITION_AT
                      and self.year - self._petition_seen.get(p.pid, -9999)
                      >= PETITION_COOLDOWN]
        if not candidates:
            return
        place = r.choice(candidates)
        polity = self.polity_at(place)
        plea, done, task = r.choice(PETITION_MISSIONS)
        sect = self._petition_sect(place.land)
        self.petitions.append(Petition(
            place=place, sect=sect, year=self.year,
            polity=polity.pid if polity else None, plea=plea, done=done,
            task=task))
        self._petition_seen[place.pid] = self.year
        ruler = self.leader_of(polity) if polity else None
        under = (f" under {self.ruler_ref(ruler)}"
                 if ruler is not None and ruler.alive else "")
        self.log(f"The elders of {place.name} in the {place.land.name}, "
                 f"{place.word()}{under}, sent riders to {sect} begging them "
                 f"{plea.format(where=place.name)}.", [], place=place)

    def _petition_candidates(self, petition: Petition,
                             ruler: Optional[Agent]) -> tuple:
        """Who would go: the Righteous, the standing-hungry, natives of that
        land, and anyone who already hates that court."""
        agents, weights = [], []
        for a in self.cultivators():
            if (a.sect != petition.sect or a.age < 14
                    or a.realm < PETITION_MIN_REALM):
                continue
            w = sum(mult for t, mult in PETITION_TRAIT_WEIGHTS.items()
                    if a.has_trait(t))
            if a.home is not None and a.home.land is petition.place.land:
                w += PETITION_HOME_WEIGHT
            if ruler is not None:
                rel = a.rels.get(ruler.aid)
                if rel is not None and rel.kind in HOSTILE_KINDS:
                    w += PETITION_GRUDGE_WEIGHT
            if w <= 0:
                continue
            agents.append(a)
            weights.append(w)
        return agents, weights

    def _plan_petition_answer(self, petition: Petition) -> Optional[Agent]:
        """Whether this plea finds a champion this year, and who."""
        r = self.rng
        if r.random() >= PETITION_ANSWER_CHANCE:
            return None
        polity = self.polities.get(petition.polity)
        ruler = self.leader_of(polity) if polity else None
        if ruler is not None and not ruler.alive:
            ruler = None
        agents, weights = self._petition_candidates(petition, ruler)
        if not agents:
            return None
        return r.choices(agents, weights)[0]

    def _answer_petition(self, petition: Petition, hero: Agent, ask=True):
        r = self.rng
        polity = self.polities.get(petition.polity)
        ruler = self.leader_of(polity) if polity else None
        if ruler is not None and not ruler.alive:
            ruler = None
        # VII §2: the sect assigns; a played character is asked. A refusal
        # leaves the plea on the table for somebody else, or for the years
        # to run out on it.
        if ask and self.playing and hero is self.pc:
            where_ = petition.place.name
            if self.ask_player(
                    "petition",
                    f"{petition.sect} asks you to ride for {where_}: "
                    f"{petition.plea.format(where=where_)}",
                    ["ride", "refuse"], "ride") != "ride":
                self.log(f"{hero.display()} was asked to ride for "
                         f"{where_} and would not go.", [hero],
                         place=petition.place)
                return
        self.petitions.remove(petition)
        place = petition.place
        where = place.name

        # A contest, under the ordinary rules: the magistrate's men, and
        # whatever realm sits above them.
        opposition = PETITION_OPPOSITION
        if ruler is not None:
            opposition += PETITION_OPPOSITION_PER_REALM * (ruler.realm - 1)
        if polity is not None:
            opposition += PETITION_OPPOSITION_PER_ARMY * polity.army
        power = hero.power()
        chance = max(PETITION_ODDS[0],
                     min(PETITION_ODDS[1], power / (power + opposition)))
        domain = polity.domain if polity is not None else place.land.name

        if r.random() < chance:
            was = place.word()
            place.prosperity = min(10.0, place.prosperity + PETITION_GAIN)
            hero.standing += PETITION_STANDING
            hero.karma += PETITION_KARMA
            self._record_deed(hero, "mercy")     # VII §2: the ledger
            recovery = (f"the village is {place.word()} now where it was "
                        f"{was}" if place.word() != was else
                        f"the village is still {place.word()}, but it eats")
            text = (f"{hero.display()} answered the plea of {where} and "
                    f"{petition.done.format(where=where)}; {recovery}.")
            if ruler is not None:
                self._add_grudge(ruler, hero, 2)
                self._add_grudge(hero, ruler, 1)
                # A raid the court could not punish is the smallest of the
                # governance adversities, and the commonest (§4).
                self._governance_insight(ruler, "petition")
                if polity is not None:
                    polity.unrest = min(UNREST_MAX,
                                        polity.unrest + PETITION_UNREST)
                text += (f" {self.ruler_ref(ruler)} named them an enemy of "
                         f"{domain}.")
            self.log(text, [hero] + ([ruler] if ruler is not None else []),
                     dramatic=True, place=place)
            return

        # Failure is honest: the men of the court are many, and the village
        # pays for having asked.
        hero.insight += PETITION_FAIL_INSIGHT
        hero.burden += 1
        place.prosperity = max(0.0, place.prosperity - PETITION_REPRISAL)
        if polity is not None:
            polity.unrest = min(UNREST_MAX, polity.unrest + PETITION_UNREST)
        if ruler is not None:
            self._add_grudge(hero, ruler, 2)
        lethal = r.random() < PETITION_DEATH_CHANCE
        text = (f"{hero.display()} went to {where} for {petition.task} and "
                f"was broken by the men of {domain}")
        if lethal:
            # §7: dying in defence of others. It buys the dead nothing.
            self._fell_defending(hero, f"the villagers of {where}")
            self.log(text + f"; they did not walk out, and {where} is left "
                            f"worse than it was.",
                     [hero] + ([ruler] if ruler is not None else []),
                     dramatic=True, place=place)
            self.kill(hero, f"killed by the men of {domain} answering the "
                            f"plea of {where}")
            return
        self.log(text + f"; they walked out alive and hunted (+insight), and "
                        f"{where} paid for the asking.",
                 [hero] + ([ruler] if ruler is not None else []),
                 dramatic=True, place=place)
        self._mutate(hero, "humiliated")

    def _tournament(self):
        r = self.rng
        for realm in range(1, 5):
            band = [a for a in self.cultivators()
                    if a.realm == realm and a.age >= 14]
            if len(band) < 4:
                continue
            entrants = r.sample(band, min(8, len(band)))
            while len(entrants) > 1:
                nxt = []
                for i in range(0, len(entrants) - 1, 2):
                    x, y = entrants[i], entrants[i + 1]
                    px, py = x.power(), y.power()
                    w, l = (x, y) if r.random() < px / (px + py) else (y, x)
                    l.insight += 2   # losers who survive learn
                    nxt.append(w)
                if len(entrants) % 2:
                    nxt.append(entrants[-1])
                entrants = nxt
            champ = entrants[0]
            runner = [a for a in band if a is not champ]
            runner = max(r.sample(runner, min(3, len(runner))),
                         key=lambda x: x.power())
            champ.standing += 2
            champ.resources += 4 + self._vice_spoils(champ)
            self._bind(champ, runner, "rival", 2)
            self.log(f"{champ.display()} won the {REALM_NAMES[realm]} "
                     f"tournament, defeating {runner.display()} in the final; "
                     f"a rivalry is born before the assembled sects.",
                     [champ, runner], dramatic=(realm >= 3))
            # §7: a Cruel champion cripples the runner-up in front of the
            # assembled sects, which is how everyone learns what they are.
            if champ.has_trait("Cruel") and r.random() < CRUEL_MAIM_CHANCE:
                self._maim(champ, runner, "the final")
            self._mutate(runner, "humiliated")

    def _plan_expedition(self) -> list:
        """Who a secret realm draws in. Rolled when the year is planned so
        that a drawn cultivator's timeskip stops on the eve of the opening."""
        r = self.rng
        pool = [a for a in self.cultivators() if 14 <= a.age and a.realm <= 4]
        weights = []
        for a in pool:
            w = 1.0
            if a.has_trait("Reckless"):
                w *= 3
            if a.has_trait("Greedy"):
                w *= 2
            if a.has_trait("Cautious"):
                w *= 0.3
            if a.stalled():
                w *= 2.5
            weights.append(w)
        if not pool:
            return []
        k = min(len(pool), r.randint(6, 12))
        volunteers, seen = [], set()
        while len(volunteers) < k:
            a = r.choices(pool, weights)[0]
            if a.aid not in seen:
                seen.add(a.aid)
                volunteers.append(a)
        return volunteers

    def _run_expedition(self, volunteers: list):
        r = self.rng
        self.log(f"A secret realm opened; {len(volunteers)} cultivators "
                 f"entered.", volunteers, world_event=True)
        deaths = []
        for a in volunteers:
            roll = r.random() + a.fortune * FORTUNE_WEIGHT   # low = a grave
            if roll < 0.13:
                deaths.append(a)
            elif roll < 0.25:
                a.insight += 5
                a.burden += 1
                if r.random() < 0.5 and len(a.epithets) < 3:
                    ep = r.choice([e for e in MAIM_EPITHETS
                                   if e not in a.epithets])
                    a.epithets.append(ep)
                    self.log(f"{a.name} was maimed in the secret realm "
                             f"[epithet: {ep}] (+insight).", [a],
                             dramatic=True)
                self._mutate(a, "near_death")
            elif roll < 0.5:
                a.resources += r.randint(4, 10) + self._vice_spoils(a)
                a.fortune = min(FORTUNE_CAP, a.fortune + 1)
            elif roll < 0.7:
                a.insight += 4
        for a in deaths:
            self.kill(a, "perished in the secret realm")
        survivors = [a for a in volunteers if a.alive]
        for a in survivors:
            a.insight += len(deaths)  # witnessing death teaches
        if deaths:
            names = ", ".join(d.display() for d in deaths)
            self.log(f"The secret realm claimed {len(deaths)} lives: {names}.",
                     survivors, world_event=True)

    def _feud_pair(self) -> Optional[tuple]:
        """The two sects whose accumulated grudges are over the line, if any.
        No dice: a feud is a reading of the ledger, which is why the agenda
        can stamp it a season ahead."""
        totals: dict[tuple, int] = {}
        for a in self.cultivators():
            for i, rel in a.rels.items():
                o = self.agents.get(i)
                if (o and o.sect and rel.kind in HOSTILE_KINDS
                        and o.sect != a.sect):
                    key = tuple(sorted((a.sect, o.sect)))
                    totals[key] = totals.get(key, 0) + rel.intensity
        for pair, total in totals.items():
            if total >= FEUD_THRESHOLD:
                return pair         # at most one feud per year
        return None

    def _run_feud(self, s1: str, s2: str):
        """Three duels between the best each side can put in the road, and
        then the grudges are half spent."""
        r = self.rng
        self.feud_cooldown = FEUD_COOLDOWN
        self.log(f"Accumulated grudges ignite a feud between {s1} "
                 f"and {s2}.", [], world_event=True)
        # A crowned disciple does not answer the sect's muster.
        side1 = [a for a in self.cultivators() if a.sect == s1]
        side2 = [a for a in self.cultivators() if a.sect == s2]
        losses = {s1: 0, s2: 0}
        for _ in range(3):
            if not side1 or not side2:
                break
            f1 = max(r.sample(side1, min(3, len(side1))),
                     key=lambda x: x.realm)
            f2 = max(r.sample(side2, min(3, len(side2))),
                     key=lambda x: x.realm)
            self._duel(f1, f2, lethal=True, context="the sect feud")
            side1 = [a for a in side1 if a.alive]
            side2 = [a for a in side2 if a.alive]
            for s in (s1, s2):
                losses[s] = sum(1 for a in self.agents.values()
                                if a.sect == s and not a.alive
                                and a.death_year == self.year)
        loser_sect = max(losses, key=losses.get)
        self.log(f"The feud burns out; {loser_sect} lost the most and "
                 f"loses face.", [], world_event=True)
        # Grudges are partly spent.
        for a in self.living():
            for i, rel in a.rels.items():
                o = self.agents.get(i)
                if (o and rel.kind in HOSTILE_KINDS
                        and {a.sect, o.sect} == {s1, s2}):
                    rel.intensity = max(1, rel.intensity // 2)

    def _plan_grudges(self) -> list:
        """VII §1: whose grudge against the played character ripens this year.

        Only somebody who actually holds a score, is free to act on it, and
        is not sitting on a throne — a crowned enemy answers with soldiers,
        which is what revolts and assassinations are for.
        """
        r = self.rng
        pc = self.pc
        out: list = []
        if pc is None or not pc.alive or pc.is_ruler() or pc.age < 14:
            return out
        for aid in list(pc.rels):
            foe = self.agents.get(aid)
            if foe is None or not foe.alive or foe.is_ruler() or foe.age < 14:
                continue
            held = foe.rels.get(pc.aid)
            if (held is None or held.kind not in HOSTILE_KINDS
                    or held.intensity < GRUDGE_RIPE):
                continue
            if r.random() < GRUDGE_RIPEN_CHANCE:
                out.append(foe)
                if len(out) >= GRUDGE_RIPEN_MAX:
                    break
        return out

    def _grudge_comes(self, foe: Optional[Agent]):
        """VII §1/§3: a grudge against the played character ripens and comes
        looking for them.

        The kernel already does exactly this inside the socialize action —
        a Vengeful agent with a ripe score seeks the enemy out. The agenda
        only decides it a season early, so a timeskip can stop on its eve
        instead of waking the player with a corpse.
        """
        pc = self.pc
        if foe is None or pc is None or not foe.alive or not pc.alive:
            return
        if foe.is_ruler() or pc.is_ruler():
            return      # a grudge against a crown is a revolt, not a duel
        rel = foe.rels.get(pc.aid)
        if rel is None or rel.kind not in HOSTILE_KINDS:
            return
        lethal = any(foe.has_trait(t)
                     for t in ("Vengeful", "Ruthless", "Bloodthirsty"))
        self._duel(foe, pc, lethal=lethal, context="a score come due")

    # -- resolution phase ---------------------------------------------------

    def _resolution_phase(self):
        self._drift_prosperity()
        self._stipends()
        self._karma_luck()
        for a in list(self.living()):
            self._try_breakthrough(a)
        for a in list(self.living()):
            a.age += 1
            if a.age > a.lifespan:
                self.kill(a, f"died of old age at {a.age}, "
                             f"{a.realm_name} to the last")
                continue
            self._maybe_voluntary_exit(a)

    def _karma_luck(self):
        """§7: the luck coupling. Every year, fortune drifts one step toward
        the sign of the ledger — on top of the streaky luck the road hands
        out. Virtue is the luck lane; it is also the SLOW lane, since the
        counter is clamped small and buys only a couple of points on a die.
        """
        for a in self.living():
            if a.karma > 0:
                a.fortune = min(FORTUNE_CAP, a.fortune + KARMA_FORTUNE_DRIFT)
            elif a.karma < 0:
                a.fortune = max(-FORTUNE_CAP, a.fortune - KARMA_FORTUNE_DRIFT)

    def _drift_prosperity(self):
        """Left alone, a settlement returns to its land's temper — fast when
        it is far from it, slowly once it is close. What drags it away from
        baseline is the rule style of whoever holds it, and where the two
        balance is what the map shows."""
        for p in self.settlements():
            gap = p.baseline - p.prosperity
            if abs(gap) < PROSPERITY_DRIFT_MIN:
                p.prosperity = p.baseline
                continue
            step = gap * (PROSPERITY_RECOVERY if gap > 0
                          else PROSPERITY_SETTLING)
            if abs(step) < PROSPERITY_DRIFT_MIN:
                step = PROSPERITY_DRIFT_MIN if gap > 0 else -PROSPERITY_DRIFT_MIN
            p.prosperity = max(0.0, min(10.0, p.prosperity + step))

    def _try_breakthrough(self, a: Agent):
        r = self.rng
        if a.qi < 100 or a.realm >= MAX_REALM:
            return
        req = INSIGHT_REQ[a.realm]
        if a.insight < req:
            return  # stalled; the action phase already biases them to adventure
        chance = 0.35 + a.talent * 0.03 + (a.insight - req) * 0.01 \
            - a.burden * 0.05
        # §7: the tribulation reads the ledger — karma/4 percentage points,
        # clamped to five either way. Enough to be felt over a career, never
        # enough to carry a life on its own.
        chance += max(-KARMA_TRIBULATION_CAP,
                      min(KARMA_TRIBULATION_CAP, a.karma * KARMA_TRIBULATION))
        # Talent soft-caps the realm: reaching far above your talent is hard.
        if a.realm + 1 > a.talent // 2 + 2:
            chance -= 0.15
        chance = max(0.05, min(0.9, chance))
        if r.random() < chance:
            a.realm += 1
            a.qi = 0
            a.insight -= req
            a.standing += 2
            a.burden = max(0, a.burden - 1)
            # A cultivator-king can still break through on the seat: qi is
            # frozen, but governance adversity keeps handing them insight.
            self.log(f"{self.ruler_ref(a)} broke through to {a.realm_name} "
                     f"(age {a.age}).", [a], dramatic=(a.realm >= 3))
            if a.realm >= FAME_REALM and "Ascendant" not in a.epithets:
                a.epithets.append("Ascendant")
            self._update_sect_heads()
        else:
            a.qi = 40
            a.burden += 1
            a.insight += 2  # tribulations teach even in failure
            if a.realm >= 3 and r.random() < 0.20:
                self.log(f"{a.display()}'s tribulation to {REALM_NAMES[a.realm+1]} "
                         f"collapsed into qi deviation.", [a], dramatic=True)
                self.kill(a, "died of qi deviation in a failed tribulation")
                return
            if a.realm >= 3 and r.random() < 0.15:
                a.talent = max(1, a.talent - 2)
                if "Tribulation-Scarred" not in a.epithets:
                    a.epithets.append("Tribulation-Scarred")
                self.log(f"{a.display()} survived a failed tribulation, "
                         f"foundation cracked [epithet: Tribulation-Scarred].",
                         [a], dramatic=True)
                self._mutate(a, "near_death")
            else:
                self.log(f"{a.display()} failed the breakthrough to "
                         f"{REALM_NAMES[a.realm + 1]} (burden {a.burden}).",
                         [a])

    def _maybe_voluntary_exit(self, a: Agent):
        r = self.rng
        if a.is_ruler():
            # A throne has its own exit, and it is not this one.
            self._maybe_abdicate(a)
            return
        # §11: the exit that is not an exit — a defector keeps cultivating.
        if self._maybe_defect(a):
            return
        chance = 0.0
        if a.realm == 1 and a.age > 30 and a.talent <= 4:
            chance = 0.04
        elif a.realm == 2 and a.age > 80 and a.stalled():
            chance = 0.02
        if a is self.pc:
            chance *= 0.25  # protagonists are stubborn, though not immune
        if r.random() < chance:
            reason = r.choice([
                "married out and settled in a mortal town",
                "took an administrative post in the outer sect",
                "lost conviction and returned to their village",
            ])
            # VII §2: voluntary exits are never rolled for the played
            # character — the conditions fire and the door is OFFERED.
            if self.playing and a is self.pc:
                if self.ask_player(
                        "exit",
                        f"The path has stopped paying: you could have "
                        f"{reason}.",
                        ["stay", "leave"], "stay") != "leave":
                    return
            a.alive = False
            a.exited = True
            a.death_year = self.year
            a.death_cause = reason
            self.log(f"{a.display()} left the path: {reason}.", [a])

    # -- death, grief, obituaries -------------------------------------------

    def kill(self, a: Agent, cause: str, killer: Optional[Agent] = None):
        if not a.alive:
            return
        a.alive = False
        a.death_year = self.year
        a.death_cause = cause
        was_head = self.sect_heads.get(a.sect) == a.aid

        # Grief and its consequences.
        for i, rel in list(a.rels.items()):
            o = self.agents.get(i)
            if not (o and o.alive):
                continue
            back = o.rels.get(a.aid)
            if back and back.kind in FRIENDLY_KINDS:
                o.insight += 3 if back.kind != "friend" else 2
                if a.defended:
                    # §7: a death in defence of others is a different grief.
                    o.insight += 1
                    o.history.append((self.year,
                                      f"Grieved the loss of {back.kind} "
                                      f"{a.display()}, who died standing "
                                      f"between {a.defended} and the men who "
                                      f"came for them (+insight)."))
                else:
                    o.history.append((self.year,
                                      f"Grieved the loss of {back.kind} "
                                      f"{a.display()} (+insight)."))
                if killer is not None and killer.alive:
                    self._add_grudge(o, killer, 3)
                    self._mutate(o, "betrayed")

        violent = killer is not None or "old age" not in cause
        obit = self._obituary(a)
        self.obituaries.append(obit)
        # A ruler's death is news in their own land; the coronation line that
        # follows carries it to the wider world.
        self.log(obit, [a], dramatic=violent or a.realm >= FAME_REALM,
                 place=a.home if a.is_ruler() else None)

        if was_head:
            self._succession(a.sect, a)
        else:
            self._update_sect_heads()

        if a.is_ruler():
            polity = self.polities.get(a.ruling)
            if polity is not None and polity.leader == a.aid:
                self._polity_succession(polity, a)

    def _obituary(self, a: Agent) -> str:
        grievers = [self.agents[i].display() for i, rel in a.rels.items()
                    if rel.kind in FRIENDLY_KINDS
                    and self.agents[i].alive][:3]
        celebrants = [o.display() for o in self.living()
                      if o.rels.get(a.aid)
                      and o.rels[a.aid].kind in HOSTILE_KINDS][:3]
        if a.is_ruler():
            reign = self.reign_length(a)
            came = f", {a.reign_came}" if a.reign_came else ""
            parts = [f"OBITUARY: {self.ruler_ref(a)}, dead at {a.age} after "
                     f"{self.years_phrase(reign)} on the seat{came}; "
                     f"{a.death_cause}."]
        else:
            of_sect = f" of {a.sect}" if a.sect else ""
            parts = [f"OBITUARY: {a.display()}{of_sect}, dead at {a.age} "
                     f"({a.realm_name}); {a.death_cause}."]
        if a.defended:
            parts.append(f"Died in defence of {a.defended}.")
        for name, domain, title, start, end, how, came in a.past_reigns:
            got = f"{came}, and " if came else "and "
            parts.append(f"Was {title} of {domain} for "
                         f"{self.years_phrase(end - start)}, {got}"
                         f"{how} the seat in Y{end}.")
        if a.revolts_survived:
            parts.append("Put down a rising." if a.revolts_survived == 1
                         else f"Put down {a.revolts_survived} risings.")
        if a.wars_won or a.wars_lost:
            won = f"won {a.wars_won}" if a.wars_won else ""
            lost = f"lost {a.wars_lost}" if a.wars_lost else ""
            tally = " and ".join(p for p in (won, lost) if p)
            parts.append(f"Of the wars fought from that seat, {tally}.")
        if TYRANT_BREAKER in a.epithets:
            parts.append("Threw down a throne, and the country remembers it.")
        if a.thrones_refused:
            parts.append("Refused a throne." if a.thrones_refused == 1
                         else f"Refused {a.thrones_refused} thrones.")
        if grievers:
            parts.append(f"Grieved by {', '.join(grievers)}.")
        if celebrants:
            parts.append(f"Quietly celebrated by {', '.join(celebrants)}.")
        return " ".join(parts)

    # -- sect politics ------------------------------------------------------

    def _update_sect_heads(self):
        # A disciple who took a throne is not the sect's head: the seat is a
        # different clock, and cultivators() is where the sect's life happens.
        for sect in self.sects:
            members = [a for a in self.cultivators() if a.sect == sect]
            if members:
                head = max(members, key=lambda x: (x.realm, x.standing))
                self.sect_heads[sect] = head.aid
        self._sync_sect_polities()

    def _succession(self, sect: str, dead_head: Agent):
        r = self.rng
        members = [a for a in self.cultivators() if a.sect == sect]
        if len(members) < 2:
            self._update_sect_heads()
            return
        def clout(a):
            return (a.realm * 8 + a.standing * 2 + r.uniform(0, 6)
                    + (4 if a.has_trait("Charming") else 0))
        top = sorted(members, key=clout, reverse=True)[:2]
        winner, loser = top[0], top[1]
        winner.standing += 3
        self._add_grudge(loser, winner, 3)
        self.sect_heads[sect] = winner.aid
        self.log(f"Succession crisis in {sect} after the death of "
                 f"{dead_head.display()}: {winner.display()} prevailed over "
                 f"{loser.display()}, who withdraws nursing a grudge.",
                 [winner, loser], world_event=True)
        # §7: passed over for a seat they wanted, a schemer turns Vengeful.
        self._mutate(loser, "passed_over")

    # -- trait mutation (JOB 3) ---------------------------------------------

    def _camera_cast(self, a: Agent) -> bool:
        """§8: is this agent in the viewpoint cast — the protagonist, or
        someone CURRENTLY bound to them as friend, sworn, lover, master or
        disciple? (Rivals, enemies and allies are not: the cast the reader
        rides with is small.)"""
        pc = self.pc
        if pc is None:
            return False
        if a.aid == pc.aid:
            # VII, decisions taken up front: NO VICE LOCK ON THE PLAYER. A
            # played character may earn, mutate into and act on vice traits;
            # karma and grudges are the honest price. Bound companions KEEP
            # the constraint — the reader's seat around the player is still
            # a seat.
            return not self.playing
        rel = pc.rels.get(a.aid)
        return rel is not None and rel.kind in CAMERA_BOUND_KINDS

    def _camera_filter(self, a: Agent, trait: str) -> str:
        """THE CAMERA CONSTRAINT (§8) — the one deliberate breach of SIM
        FIRST in the whole politics layer, and it is enforced here.

        The protagonist and the handful of people bound to them never mutate
        into a vice trait; a blocked step reroutes to Vengeful, Cold or
        Broken. The viewpoint cast can darken — it cannot become monstrous.

        This protects the READER'S SEAT, not the characters: PC and friends
        still lose, stall, get maimed, get shaken down, and die on schedule,
        and nothing else in the sim knows the camera exists.
        """
        if trait in VICE_TRAITS and self._camera_cast(a):
            return self.rng.choice(CAMERA_REROUTE)
        return trait

    def _mutate(self, a: Agent, trigger: str, sure=False, deed_trait=None):
        """`sure` skips the usual gate: the caller has already rolled for it
        (POWER CORRUPTS carries its own, slower clock; so does the deed
        ledger of VII §2, which has already counted to three)."""
        r = self.rng
        if not a.alive or (not sure and r.random() > 0.35):
            return
        swap = None
        gain = None
        gained_by_the_seat = False
        if trigger == "deeds":
            gain = deed_trait
        elif trigger == "power":
            step = self._corruption_step(a)
            if step is None:
                return              # the bottom of the ladder, or of the build
            frm, to = step
            gained_by_the_seat = True
            if frm is None:
                gain = to
            else:
                swap = (frm, to)
        elif trigger in ("humiliated", "passed_over"):
            # Passed over for a seat, a schemer stops scheming and starts
            # remembering. Crushed in public, a bully's whole method has
            # just failed in front of everyone.
            if trigger == "passed_over" and a.has_trait("Power-Hungry"):
                swap = ("Power-Hungry", "Vengeful")
            elif a.has_trait("Proud"):
                swap = ("Proud", r.choice(["Humble", "Vengeful", "Broken"]))
            elif a.has_trait("Bully"):
                swap = ("Bully", r.choice(["Broken", "Humble"]))
        elif trigger == "betrayed" and a.has_trait("Loyal"):
            swap = ("Loyal", "Vengeful")
        elif trigger == "near_death":
            # Having nearly died of it cures a taste for killing.
            if a.has_trait("Bloodthirsty"):
                swap = ("Bloodthirsty", r.choice(["Cautious", "Ascetic"]))
            elif a.has_trait("Reckless"):
                swap = ("Reckless", r.choice(["Cautious", "Ascetic"]))
            elif r.random() < 0.5 and "Ascetic" not in a.traits:
                gain = "Ascetic"
        by = ""
        if gained_by_the_seat:
            by = " by the seat"
        elif trigger == "deeds":
            by = " by what they have been doing"
        if swap is not None:
            to = self._camera_filter(a, swap[1])
            if to in a.traits:
                return
            a.traits.remove(swap[0])
            a.traits.append(to)
            self.log(f"{self.ruler_ref(a)} is changed{by}: "
                     f"{swap[0]} -> {to}.", [a])
        elif gain is not None:
            to = self._camera_filter(a, gain)
            if to in a.traits:
                return
            a.traits.append(to)
            self.log(f"{self.ruler_ref(a)} is changed{by}: "
                     f"gained trait {to}.", [a])

    # -- the played character (VII §2) --------------------------------------

    def begin_play(self, name: str, sex: Optional[str] = None,
                   land: Optional[Place] = None, ask=None) -> Agent:
        """Add the played character to the watched intake as agent 65.

        Talent, traits, home settlement, the lot: ROLLED. The funnel is real
        and there is no point-buy. The player names them and may pick sex and
        homeland; that is all they get, and it is the whole difference
        between a player and a camera.
        """
        r = self.rng
        sects = list(self.sects)
        a = self._make_agent(sects[self.intake_size % len(sects)], 14,
                             realm=1, intake_year=0, sex=sex, land=land)
        if name:
            a.name = name
        a.qi = r.uniform(0, 15)
        a.insight = 0
        a.resources = r.randint(0, 4)
        a.standing = 1
        a.play = PlayerState()
        self.pc = a
        self.playing = True
        self.ask = ask
        self._home_start(a)         # §10: the home they walked out of
        cohort = [o for o in self.agents.values()
                  if o.intake_year == 0 and o.aid != a.aid and o.alive
                  and o.sect and o.age == a.age]
        for other in r.sample(cohort, min(2, len(cohort))):
            self._bind(a, other, r.choice(["friend", "friend", "rival"]),
                       r.randint(1, 2))
        a.history.append((0, "Entered the sect as a new disciple."))
        return a

    def take_over_pc(self) -> Optional[Agent]:
        """Hand the successor `_succeed_pc` picked to the player."""
        if self.pc is None:
            return None
        if self.pc.play is None:
            self.pc.play = PlayerState()
        return self.pc

    def player_season(self, activity: str) -> None:
        """The played character's ONE activity for this season (VII §3).

        Every activity pays at SEASON_RATE — a quarter of the matching
        yearly action — in gains and in risk alike. Traits no longer weight
        the CHOICE (the player chooses); they keep every other job: power,
        outcomes, and what the year makes of the person.
        """
        a = self.pc
        if a is None or not a.alive or a.age < 14 or a.play is None:
            return
        if a.is_ruler():
            return          # §10: a court eats the calendar, at year tempo
        share = SEASON_RATE
        a.play.activity = activity
        a.play.seasons += 1
        if activity == "retreat":
            self._act_seclude(a, share)
        elif activity == "injustice":
            self._act_injustice(a, share)
        elif activity == "hunt":
            self._act_hunt(a, share)
        elif activity == "trade":
            self._act_trade(a, share)
        elif activity == "socialize":
            self._act_socialize(a, share)
        elif activity == "muster":
            if not self._take_service(a, forced=True, share=share):
                self.log(f"{a.display()} went looking for a muster to join; "
                         f"the levies were stood down and the season went "
                         f"nowhere.", [a])
        else:
            self._act_cultivate(a, share)

    def player_abdicate(self) -> bool:
        """§4/§10: the played ruler lays the seat down. Always on the menu."""
        a = self.pc
        if a is None or not a.is_ruler():
            return False
        polity = self.polities.get(a.ruling)
        if polity is None:
            return False
        reign = self.reign_length(a)
        self.log(f"After {self.years_phrase(reign)} on the seat, "
                 f"{self.ruler_ref(a)} laid it down and walked out of the "
                 f"hall.", [a], dramatic=True, place=polity.seat,
                 world_event=polity.is_sovereign())
        self._polity_succession(polity, a, cause="abdication")
        self._step_down(a, "laid down")
        self._after_the_throne(a, "having laid down", polity)
        return True

    def player_status(self, season: str) -> str:
        """VII §11: the season prompt's header."""
        a = self.pc
        if a is None:
            return "There is no one left to play."
        head = (f"Year {self.year}, {season} — age {a.age}, {a.realm_name}, "
                f"qi {a.qi:.0f}, insight {a.insight:.0f}, "
                f"burden {a.burden}")
        lines = [head,
                 f"  resources {a.resources} | standing {a.standing} | "
                 f"karma {karma_word(a.karma)} ({a.karma:+d})"]
        if a.play is not None and a.play.wound:
            hurt = "light" if a.play.wound == 1 else "serious"
            lines.append(f"  wounded ({hurt})")
        if a.is_ruler():
            polity = self.polities.get(a.ruling)
            if polity is not None:
                lines.append(f"  on the seat of the {polity.name}: "
                             f"{polity.style} rule, unrest {polity.unrest}, "
                             f"{polity.domain} is {polity.word()} "
                             f"— no qi while it lasts")
        rels = self.describe_rels(a)
        if rels:
            lines.append(f"  {rels}")
        if a.home is not None:
            lines.append(f"  home: {a.home.name}, {a.home.word()}")
        for notice in self.agenda_notices(season):
            lines.append(f"  * {notice}")
        return "\n".join(lines)

    def player_bag(self) -> str:
        """VII §11: what the played character is carrying. Almost all of it
        arrives in later sessions; the card exists so it has somewhere to
        land."""
        a = self.pc
        if a is None or a.play is None:
            return "Nothing to show."
        st = a.play
        lines = [f"{a.display()} carries:",
                 f"  silver {a.resources} | standing {a.standing} | "
                 f"burden {a.burden}",
                 f"  epithets: {', '.join(a.epithets) if a.epithets else '-'}",
                 f"  seasons played: {st.seasons}"]
        recent = [k for y, k in a.deeds if self.year - y <= DEED_WINDOW]
        if recent:
            tally = {}
            for k in recent:
                tally[k] = tally.get(k, 0) + 1
            lines.append("  recent deeds: "
                         + ", ".join(f"{k} x{n}" for k, n in tally.items()))
        lines.append("  (wounds, techniques, pills, professions and stance "
                     "ranks arrive with later sessions)")
        return "\n".join(lines)

    # -- PC handling --------------------------------------------------------

    def _succeed_pc(self):
        """The camera moves on when the protagonist DIES — never when they
        take a throne. A PC who is crowned is still the PC (§4: the agent
        stays fully simulated), and the chronicle follows the reign."""
        old = self.pc
        # Dump the fallen protagonist's full life into the chronicle record.
        # §8 again: the successor is drawn from the young who rolled no vice.
        young = [a for a in self.cultivators() if a.age <= 30]
        candidates = [a for a in young if self._camera_safe(a)] or young
        if not candidates:
            candidates = [a for a in self.cultivators() if self._camera_safe(a)]
        if not candidates:
            candidates = self.cultivators()
        if not candidates:
            self.pc = None
            return
        new = self.rng.choice(candidates)
        self.pc = new
        line = (f"Y{self.year:>4} [world ] The chronicle turns from the fallen "
                f"{old.display()} to a new figure: {new.display()} of "
                f"{new.sect} (age {new.age}, talent {new.talent}, "
                f"{'/'.join(new.traits)}).")
        self.chronicle.append((self.year, "world", line))
        self._fresh_lines.append(line)

    # -- reports ------------------------------------------------------------

    def origin_line(self, a: Agent) -> str:
        """Where an agent is from: settlement, land, and (in the melting pot)
        the descent their name came from."""
        if a.home is None:
            return f"the {a.homeland}"
        land = a.home.land
        text = f"{a.home.name} in the {land.name}"
        if land.pool is None and a.descent:
            text += f" ({a.descent} descent)"
        return text

    def pc_intro(self) -> str:
        a = self.pc
        rels = self.describe_rels(a)
        lines = [
            "=" * 72,
            f"MAIN CHARACTER: {a.name} of {a.sect}, "
            f"born in {self.origin_line(a)}",
            f"  age {a.age} | talent {a.talent}/10 | traits: "
            f"{', '.join(a.traits)}",
            f"  relationships: {rels if rels else '(none yet)'}",
            "The chronicle will follow their relationships — rivals, enemies,",
            "friends and allies — plus famous figures and dramatic events.",
            "=" * 72,
        ]
        return "\n".join(lines)

    def describe_rels(self, a: Agent) -> str:
        parts = []
        for i, rel in sorted(a.rels.items(),
                             key=lambda kv: -kv[1].intensity):
            o = self.agents.get(i)
            if o is None or rel.intensity <= 0:
                continue
            status = "" if o.alive else " (dead)"
            parts.append(f"{REL_DISPLAY.get(rel.kind, rel.kind)} "
                         f"{o.display()}{status} ({rel.intensity})")
        return "; ".join(parts)

    def sheet(self, a: Agent) -> str:
        alive = ("alive" if a.alive else
                 ("left the path" if a.exited else
                  f"dead Y{a.death_year}: {a.death_cause}"))
        polity = self.polities.get(a.ruling) if a.is_ruler() else None
        if a.is_ruler():
            affil = f"{polity.title(a.sex)} of the {polity.name}" \
                if polity else "a throne"
            if a.sect:
                affil += f", once of {a.sect}"
        else:
            affil = a.sect or "no sect"
        lines = [
            f"{a.display()} — {affil} [{alive}]",
            f"  home: {self.origin_line(a)}"
            + (f", {a.home.word()}" if a.home is not None else ""),
            f"  age {a.age} | realm {a.realm} ({a.realm_name}) | "
            f"qi {a.qi:.0f}/100",
            f"  talent {a.talent}/10 | insight {a.insight:.0f} | "
            f"burden {a.burden} | resources {a.resources} | "
            f"standing {a.standing} | karma {a.karma:+d}",
            f"  traits: {', '.join(a.traits)}",
            f"  epithets: {', '.join(a.epithets) if a.epithets else '-'}",
            f"  relationships: {self.describe_rels(a) or '-'}",
        ]
        if polity is not None:
            lines.append(
                f"  reign: seated Y{a.reign_start} "
                f"({self.years_phrase(self.reign_length(a))}, "
                f"{a.reign_came}), "
                f"{polity.style} rule, unrest {polity.unrest}, "
                f"{polity.domain} is {polity.word()} — no qi while it lasts")
        for name, domain, title, start, end, how, came in a.past_reigns:
            lines.append(f"  past reign: {title} of {domain} ({name}), "
                         f"Y{start}-Y{end} ({came}; {how} the seat)")
        if a.revolts_survived or a.wars_won or a.wars_lost:
            lines.append(f"  from the seat: risings put down "
                         f"{a.revolts_survived}, wars won {a.wars_won}, "
                         f"wars lost {a.wars_lost}")
        if a.thrones_refused:
            lines.append(f"  thrones refused: {a.thrones_refused}")
        return "\n".join(lines)

    def personal_log(self, a: Agent) -> str:
        lines = [f"PRIVATE HISTORY of {a.display()} ({a.sect or 'no sect'}):"]
        for y, text in a.history:
            lines.append(f"  Y{y:>4}  {text}")
        if len(lines) == 1:
            lines.append("  (an uneventful life so far)")
        return "\n".join(lines)

    def famous_list(self) -> str:
        famous = sorted([a for a in self.living() if a.realm >= FAME_REALM],
                        key=lambda x: (-x.realm, -x.standing))
        if not famous:
            return "No living cultivator has yet reached " \
                   f"{REALM_NAMES[FAME_REALM]}."
        lines = ["FAMOUS FIGURES OF THE AGE:"]
        for a in famous:
            head = " — sect head" if self.sect_heads.get(a.sect) == a.aid \
                else ""
            lines.append(f"  {a.display()}, {a.realm_name}, {a.sect}, "
                         f"age {a.age}{head}")
        return "\n".join(lines)

    def map_view(self) -> str:
        """The 3x3 grid of lands, each with its prosperity in words."""
        w = 24
        rule = "+" + "+".join(["-" * w] * 3) + "+"

        def cell(text):
            return " " + text[:w - 2].ljust(w - 1)

        lines = [f"THE NINE LANDS — year {self.year}", rule]
        for row in range(3):
            band = [[], [], []]
            for col in range(3):
                land = self.grid[row][col]
                title = land.name.upper() if land.is_center() else land.name
                band[0].append(cell(title))
                band[1].append(cell(land.word()))
                band[2].append(cell(self._capital(land).name))
            for parts in band:
                lines.append("|" + "|".join(parts) + "|")
            lines.append(rule)
        lines.append("  Each land: its temper in a word, then its capital.")
        for a, b in self.sibling_lands:
            lines.append(f"  {a.name} and {b.name} are sibling nations, "
                         f"one tongue between them.")
        lines.append("  Lands sharing an edge are close neighbours; corner "
                     "contact is distant.")
        lines.append("  The Middle Plain touches all eight, holds the four "
                     "sect seats, and sends the most recruits.")
        return "\n".join(lines)

    def _capital(self, land: Place) -> Place:
        for c in land.children:
            if c.kind == "city":
                return c
        return land

    def _court_line(self, polity: Polity, indent="  ") -> str:
        leader = self.leader_of(polity)
        if leader is None or not leader.alive:
            who = "(the seat stands empty)"
        else:
            who = (f"{polity.title(leader.sex)} {leader.display()}, "
                   f"age {leader.age}")
            if leader.realm > 1:
                who += f", {leader.realm_name}"
        return (f"{indent}{polity.name:<34} {polity.kind:<8} {who:<44} "
                f"{polity.style:<24} unrest {polity.unrest:<3} "
                f"{polity.word()}")

    def land_sovereigns(self, land: Place) -> list:
        """A land's independent courts, the one holding its capital first.

        Ordinarily there is exactly one. A vassal that won its independence
        in a war (§9) is a second sovereign standing inside somebody else's
        land, and the displays say so rather than pretending it is a crown.
        """
        capital = self._capital(land)
        out = [p for p in self.sovereigns() if p.land is land]
        out.sort(key=lambda p: (capital not in p.territory, p.pid))
        return out

    def courts(self) -> str:
        """Every ruler: their polity, its type, this year's style, unrest."""
        lines = [f"THE COURTS — year {self.year}"]
        lands = sorted(self.lands.values(),
                       key=lambda l: (not l.is_center(), l.name))
        for land in lands:
            for i, sov in enumerate(self.land_sovereigns(land)):
                mark = "" if i == 0 else "  (independent)"
                lines.append(self._court_line(sov) + mark)
                for pid in sov.vassals:
                    vassal = self.polities.get(pid)
                    if vassal is not None:
                        lines.append(self._court_line(vassal, indent="      "))
        seats = []
        for polity in self.polities.values():
            if polity.kind != "sect":
                continue
            head = self.leader_of(polity)
            seats.append(f"{polity.name} ({head.display() if head else '-'})")
        lines.append("  Outside the vassalage tree (the spiritual exemption): "
                     + "; ".join(seats))
        return "\n".join(lines)

    def find_land(self, query: str) -> Optional[Place]:
        q = query.strip().lower()
        for land in self.lands.values():
            if q in land.name.lower():
                return land
        return None

    def land_view(self, land: Place) -> str:
        """One land's tree: its polities, rulers, edicts and prosperity."""
        tongue = f"{land.pool} tongue" if land.pool else "a melting pot"
        lines = [f"THE {land.name.upper()} — {land.reach()} land, {tongue} — "
                 f"{land.word()} (year {self.year})"]
        polities = [p for p in self.polities.values()
                    if p.land is land and p.kind != "sect"]
        polities.sort(key=lambda p: (p.liege is not None, p.pid))
        for polity in polities:
            leader = self.leader_of(polity)
            mark = "" if polity.is_sovereign() else " (vassal)"
            lines.append(f"  {polity.name}{mark} — {polity.word()}, "
                         f"unrest {polity.unrest}, style {polity.style}")
            if leader is not None and leader.alive:
                path = (f", {leader.realm_name} of {leader.sect}"
                        if leader.sect else "")
                lines.append(f"    {polity.title(leader.sex)} "
                             f"{leader.display()}, age {leader.age}{path}, "
                             f"{'/'.join(leader.traits)}, karma "
                             f"{leader.karma:+d}, seated Y{leader.reign_start}")
            else:
                lines.append("    (the seat stands empty)")
            for edict in polity.edicts:
                mandate = " [mandate]" if edict.mandate_from else ""
                lines.append(f"    edict Y{edict.year}: {edict.label} — "
                             f"{edict.clause}{mandate}")
            for place in polity.territory:
                kids = ", ".join(f"{c.name} ({c.word()})"
                                 for c in place.settlements())
                lines.append(f"    {place.name} [{place.kind}]: {kids}")
        seats = [p.name for p in self.places.values()
                 if p.kind == "sect" and p.land is land]
        if seats:
            lines.append(f"  Sect seats here (untaxed, unruled): "
                         f"{', '.join(seats)}")
        return "\n".join(lines)

    # -- the state of the nine lands (§12) -----------------------------------

    @staticmethod
    def unrest_word(unrest: int) -> str:
        for limit, word in UNREST_WORDS:
            if unrest < limit:
                return word
        return UNREST_WORDS[-1][1]

    def _polity_state(self, polity: Polity, indent: str, aside="") -> list:
        """One court, in chronicle house style: who holds it, how they hold
        it, and what standing rules the country lives under."""
        leader = self.leader_of(polity)
        held = polity.word()
        quiet = self.unrest_word(polity.unrest)
        under = aside
        liege = self.polities.get(polity.liege) if polity.liege else None
        if liege is not None:
            under = f", which owes tribute to the {liege.name},"
        if leader is None or not leader.alive:
            return [f"{indent}The {polity.name}{under} has no one on its "
                    f"seat; the villages under it are {held}, the country "
                    f"{quiet}."]
        style = "governing quietly" if polity.style == STYLE_QUIET \
            else f"ruling {polity.style}"
        path = f", {leader.realm_name} of {leader.sect}," if leader.sect \
            else ""
        reign = self.reign_length(leader)
        span = ("in the first year of the reign" if reign < 1
                else f"for {self.years_phrase(reign)}")
        lines = [f"{indent}{polity.title(leader.sex)} {leader.display()}"
                 f"{path} has held the {polity.name}{under} {span}, "
                 f"{style}; the villages under that seat are {held}, the "
                 f"country {quiet}."]
        if polity.edicts:
            clauses = "; ".join(f"{e.label} — {e.clause}"
                                for e in polity.edicts)
            lines.append(f"{indent}  By standing edict there: {clauses}.")
        return lines

    def state_of_the_lands(self) -> str:
        """§12: the nine lands as the world would tell them — prosperity in
        words, who sits on what, the edicts still in force, and what each
        land has not finished talking about."""
        lines = [f"THE STATE OF THE NINE LANDS — YEAR {self.year}"]
        memory = {}
        for year, land_name, clause in self.upheavals:
            if self.year - year <= UPHEAVAL_MEMORY:
                memory.setdefault(land_name, []).append((year, clause))
        for row in range(3):
            for col in range(3):
                land = self.grid[row][col]
                seat = "the seat of the four sects, " if land.is_center() \
                    else ""
                lines.append("")
                lines.append(f"  {land.name.upper()} — {seat}"
                             f"{land.reach()} land, {land.word()}.")
                # Every secular court whose territory lies in this land —
                # sovereigns first (the one holding the capital ahead of any
                # ex-vassal that won its independence), then the vassals,
                # whose lieges may well sit in a different land entirely.
                sovereigns = self.land_sovereigns(land)
                shown = set()
                for i, sov in enumerate(sovereigns):
                    aside = "" if i == 0 else \
                        ", sovereign now and not always so,"
                    lines += self._polity_state(sov, "    ", aside)
                    shown.add(sov.pid)
                # A land whose own crown was vassalised abroad has no
                # sovereign of its own; its courts are not indented under
                # one that is not there.
                indent = "      " if sovereigns else "    "
                for polity in sorted(
                        (p for p in self.polities.values()
                         if p.land is land and p.kind != "sect"
                         and p.pid not in shown), key=lambda p: p.pid):
                    lines += self._polity_state(polity, indent)
                for year, clause in memory.get(land.name,
                                               [])[-UPHEAVAL_SHOWN:]:
                    lines.append(f"    Within living memory: in Y{year}, "
                                 f"{clause}.")
        wars = []
        for war in self.wars:
            att = self.polities.get(war.attacker)
            dfn = self.polities.get(war.defender)
            if att is None or dfn is None:
                continue
            wars.append(f"the {att.name} is {self.years_phrase(war.fought)} "
                        f"into a war on {dfn.domain}")
        lines.append("")
        lines.append("    " + ("As the chronicle closes, "
                               + "; and ".join(wars) + "."
                               if wars else
                               "As the chronicle closes, no army is in the "
                               "field anywhere in the nine lands."))
        return "\n".join(lines)

    def roster(self) -> str:
        lines = [f"ROSTER — year {self.year}, "
                 f"{len(self.living())} living cultivators"]
        for sect in self.sects:
            members = sorted([a for a in self.living() if a.sect == sect],
                             key=lambda x: (-x.realm, -x.standing))
            head_id = self.sect_heads.get(sect)
            lines.append(f"\n{sect} ({len(members)}):")
            for a in members[:12]:
                mark = " *head*" if a.aid == head_id else ""
                pc = " <== PC" if a is self.pc else ""
                lines.append(f"  {a.display():<32} {a.realm_name:<26} "
                             f"age {a.age:<4} T{a.talent}{mark}{pc}")
            if len(members) > 12:
                lines.append(f"  ... and {len(members) - 12} more")
        return "\n".join(lines)

    def life_report(self, a: Agent) -> str:
        """One character's whole life: how it ended, their sheet, their log."""
        if a.alive and a.is_ruler():
            outcome = f"ON THE THRONE — {self.ruler_ref(a)}"
        elif a.realm >= MAX_REALM:
            outcome = f"REACHED THE PEAK — {REALM_NAMES[MAX_REALM]}"
        elif a.exited:
            outcome = "LEFT THE PATH"
        elif not a.alive:
            outcome = "DIED"
        else:
            outcome = "STILL CULTIVATING"
        lines = ["", "=" * 72,
                 f"THE LIFE OF {a.display()} — {outcome} (year {self.year})",
                 "=" * 72, self.sheet(a)]
        if a.realm < MAX_REALM and a.stalled():
            lines.append(f"  stalled at the door: qi {a.qi:.0f}/100, insight "
                         f"{a.insight:.0f}/{INSIGHT_REQ[a.realm]} for "
                         f"{REALM_NAMES[a.realm + 1]}.")
        lines += ["", self.personal_log(a)]
        return "\n".join(lines)

    def final_report(self) -> str:
        lines = ["", "=" * 72, f"FINAL REPORT — YEAR {self.year}", "=" * 72,
                 self.state_of_the_lands(), "", self.famous_list(), "",
                 self.roster(), ""]
        if self.pc is not None:
            lines += ["=" * 72, "THE MAIN CHARACTER'S LIFE", "=" * 72,
                      self.sheet(self.pc), "", self.personal_log(self.pc)]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

HELP = """Commands:
  <enter>        advance one year
  run N          advance N years
  pc             show the main character's sheet
  sheet NAME     show any character's sheet (substring match)
  log NAME       show a character's full private history
  follow         run on until the main character's story ends
  map            the nine lands on their 3x3 grid, with prosperity
  courts         every ruler: polity, type, this year's style, unrest
  land NAME      one land's tree: polities, rulers, edicts, prosperity
  roster         show living cultivators by sect
  famous         list famous figures (Nascent Soul and above)
  obits          show all obituaries so far
  help           this text
  quit           final report and exit
"""


def find_agent(world: World, query: str) -> Optional[Agent]:
    q = query.strip().lower()
    hits = [a for a in world.agents.values() if q in a.name.lower()]
    if not hits:
        return None
    hits.sort(key=lambda a: (not a.alive, -a.realm))
    return hits[0]


def run_years(world: World, n: int, echo=True):
    for _ in range(n):
        for line in world.step():
            if echo:
                print(line)


def pc_story_over(hero: Agent) -> bool:
    """Has this life finished being a story?

    Death and leaving the path end it, and so does the peak — but NOT a
    throne. Enthronement is not an ending (§4: the agent stays fully
    simulated), so the camera keeps rolling through the whole reign, and a
    monarch who reaches the peak on the seat is still mid-story until they
    die, abdicate or are cast down.
    """
    if not hero.alive:
        return True
    return hero.realm >= MAX_REALM and not hero.is_ruler()


def run_until_pc_resolved(world: World, cap_year: int, echo=True):
    """Step until the current protagonist reaches the peak, dies or quits —
    or, if they take a throne, until the reign ends.

    Returns the agent that was followed (the world may pick a successor PC
    on their death; this is the one whose story just ended).
    """
    hero = world.pc
    if hero is None:
        return None
    while not pc_story_over(hero) and world.year < cap_year:
        for line in world.step():
            if echo:
                print(line)
    return hero


def interactive(world: World):
    print(world.pc_intro())
    print("\nType 'help' for commands; press Enter to advance a year.\n")
    while True:
        try:
            cmd = input(f"[year {world.year}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if cmd == "":
            run_years(world, 1)
        elif cmd.isdigit():
            run_years(world, int(cmd))
        elif cmd.startswith("run "):
            try:
                run_years(world, int(cmd.split()[1]))
            except (ValueError, IndexError):
                print("usage: run N")
        elif cmd == "pc":
            if world.pc:
                print(world.sheet(world.pc))
            else:
                print("There is no main character; the world goes on without one.")
        elif cmd.startswith("sheet "):
            a = find_agent(world, cmd[6:])
            print(world.sheet(a) if a else "No such character.")
        elif cmd.startswith("log "):
            a = find_agent(world, cmd[4:])
            print(world.personal_log(a) if a else "No such character.")
        elif cmd == "follow":
            hero = world.pc
            if hero is None:
                print("There is no main character to follow.")
            else:
                run_until_pc_resolved(world, world.year + FOLLOW_CAP_YEARS)
                print(world.life_report(hero))
        elif cmd == "map":
            print(world.map_view())
        elif cmd == "courts":
            print(world.courts())
        elif cmd.startswith("land "):
            land = world.find_land(cmd[5:])
            print(world.land_view(land) if land else "No such land.")
        elif cmd == "roster":
            print(world.roster())
        elif cmd == "famous":
            print(world.famous_list())
        elif cmd == "obits":
            print("\n".join(world.obituaries) or "No deaths yet.")
        elif cmd == "help":
            print(HELP)
        elif cmd in ("quit", "exit", "q"):
            break
        else:
            print("Unknown command; 'help' for the list.")
    print(world.final_report())


PLAY_HELP = """Commands (play mode):
  <enter>            repeat last season's activity
  1-7 or NAME        this season's activity
  menu               show the activity menu again
  skip N doing X     keep doing X for up to %d seasons; the engine wakes you
                     the season BEFORE anything that matters to you
  agenda             what this year is known to hold
  bag                what you are carrying
  orders             standing orders (arrives with round combat)
  pc / sheet NAME    a character sheet
  log NAME           a character's whole private history
  map / courts       the nine lands; every ruler and how they rule
  land NAME          one land's polities, rulers, edicts, prosperity
  roster / famous / obits
  help / quit
""" % TIMESKIP_CAP


class Play:
    """The terminal front end for a played life (VII §11).

    Every print and every input lives in this class: the kernel is never
    asked to print, and nothing the player types ever touches `world.rng`,
    so identical play replays a seeded world and different play diverges it.
    """

    def __init__(self, world: World):
        self.world = world
        self.cursor = len(world.chronicle)
        self.quit = False
        self.skip_left = 0
        self.skip_done = 0
        self.skip_activity = "cultivate"
        self.snapshot: dict = {}
        self.season: Optional[str] = None
        self.hcursor = len(world.pc.history) if world.pc is not None else 0

    # -- plumbing -------------------------------------------------------

    def read(self, prompt: str) -> str:
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            self.quit = True
            return ""

    def flush(self, limit: Optional[int] = None) -> list:
        """Print whatever the world has logged since the last flush."""
        lines = [t for (_, _, t) in self.world.chronicle[self.cursor:]]
        self.cursor = len(self.world.chronicle)
        shown = lines if limit is None or len(lines) <= limit else lines[:limit]
        for line in shown:
            print(line)
        if len(shown) < len(lines):
            print(f"      ... and {len(lines) - len(shown)} more lines that "
                  f"year; 'log' has the rest")
        return lines

    def flush_private(self, printed: list, quiet=False):
        """The season's own record — the lines that went into the played
        character's private history and were never public enough to reach
        the chronicle. Without this the player would choose an activity and
        watch nothing happen."""
        pc = self.world.pc
        if pc is None or pc.play is None:
            return
        fresh = pc.history[self.hcursor:]
        self.hcursor = len(pc.history)
        if quiet:
            return
        for _, text in fresh:
            if any(text in line for line in printed):
                continue        # the chronicle already carried it
            print(f"       . {text}")

    def ask(self, kind: str, prompt: str, options: list, default: str) -> str:
        """The kernel's question hook (World.ask_player)."""
        print()
        print(f"  {prompt}")
        while True:
            answer = self.read(f"  [{' / '.join(options)}] > ").strip().lower()
            if self.quit:
                return default
            if not answer:
                return default
            for opt in options:
                if opt.startswith(answer):
                    return opt
            print(f"  one of: {', '.join(options)}")

    # -- the menu -------------------------------------------------------

    def menu(self) -> str:
        lines = ["What will you do with the season?"]
        for i, (key, label, pays) in enumerate(PLAYER_ACTIVITIES, 1):
            mark = " " if self._available(key) else "-"
            lines.append(f" {mark}{i}. {label:<24} {pays}")
        lines.append("   (a season pays a quarter of a year's work; "
                     "'skip N doing X' runs several)")
        return "\n".join(lines)

    def _available(self, key: str) -> bool:
        if key != "muster":
            return True
        return any(i.kind == "muster" for i in self.world.agenda)

    def match_activity(self, text: str) -> Optional[str]:
        text = text.strip().lower()
        if not text:
            return None
        if text.isdigit():
            i = int(text) - 1
            if 0 <= i < len(PLAYER_ACTIVITIES):
                return PLAYER_ACTIVITIES[i][0]
            return None
        for key, label, _ in PLAYER_ACTIVITIES:
            if key.startswith(text) or label.lower().startswith(text):
                return key
        return None

    # -- the season prompt ----------------------------------------------

    def prompt(self, season: str) -> Optional[str]:
        w = self.world
        self.season = season
        print()
        print(w.player_status(season))
        while True:
            cmd = self.read(f"[{season} of year {w.year}] > ").strip()
            if self.quit:
                return None
            low = cmd.lower()
            if low in ("quit", "exit", "q"):
                self.quit = True
                return None
            if cmd == "":
                return w.pc.play.activity
            if low.startswith("skip"):
                if self.start_skip(low):
                    return self.skip_activity
                continue
            if self.observer_command(cmd):
                continue
            act = self.match_activity(cmd)
            if act is not None:
                if not self._available(act):
                    print("There is no muster to join this year.")
                    continue
                return act
            print("Unknown command; 'help' for the list.")

    def observer_command(self, cmd: str) -> bool:
        """Every command the observer build has, still working in play mode."""
        w = self.world
        low = cmd.lower()
        if low == "help":
            print(PLAY_HELP)
        elif low == "menu":
            print(self.menu())
        elif low == "agenda":
            notices = w.agenda_notices(self.season)
            print("\n".join(f"  * {n}" for n in notices)
                  or "  Nothing this year that concerns you.")
        elif low == "bag":
            print(w.player_bag())
        elif low == "orders":
            print("Standing orders arrive with round combat (session P3).")
        elif low == "pc":
            print(w.sheet(w.pc) if w.pc else "No one to show.")
        elif low.startswith("sheet "):
            a = find_agent(w, cmd[6:])
            print(w.sheet(a) if a else "No such character.")
        elif low.startswith("log "):
            a = find_agent(w, cmd[4:])
            print(w.personal_log(a) if a else "No such character.")
        elif low == "map":
            print(w.map_view())
        elif low == "courts":
            print(w.courts())
        elif low.startswith("land "):
            land = w.find_land(cmd[5:])
            print(w.land_view(land) if land else "No such land.")
        elif low == "roster":
            print(w.roster())
        elif low == "famous":
            print(w.famous_list())
        elif low == "obits":
            print("\n".join(w.obituaries) or "No deaths yet.")
        else:
            return False
        return True

    # -- the timeskip (VII §3) -------------------------------------------

    def start_skip(self, cmd: str) -> bool:
        """`skip N doing X` — keep doing X for up to N seasons."""
        parts = cmd.split()
        count = TIMESKIP_CAP
        activity = self.world.pc.play.activity
        if len(parts) > 1 and parts[1].isdigit():
            count = int(parts[1])
        if "doing" in parts:
            named = " ".join(parts[parts.index("doing") + 1:])
            match = self.match_activity(named)
            if match is None:
                print(f"No such activity: {named}")
                return False
            activity = match
        if not self._available(activity):
            print("There is no muster to join this year.")
            return False
        count = max(1, min(TIMESKIP_CAP, count))
        self.skip_left = count
        self.skip_done = 0
        self.skip_activity = activity
        self.snapshot = self.gains_snapshot()
        label = dict((k, l) for k, l, _ in PLAYER_ACTIVITIES)[activity]
        print(f"  ({label.lower()}, up to {count} seasons — you will be woken "
              f"if anything happens that is yours)")
        return True

    def gains_snapshot(self) -> dict:
        a = self.world.pc
        return dict(qi=a.qi, insight=a.insight, resources=a.resources,
                    standing=a.standing, karma=a.karma, realm=a.realm,
                    age=a.age, burden=a.burden, year=self.world.year)

    def eve_reason(self, season: str) -> Optional[str]:
        """Is something FORESEEN and HARD about to happen this season? Then
        the skip stops now, on its eve."""
        for item in self.world.season_agenda(season):
            if item.hard:
                return item.notice or f"something is coming: {item.kind}"
        return None

    def wake(self, reason: Optional[str]):
        """THE DIGEST (VII §3): seasons elapsed, gains, the chronicle that
        was missed, and then the interrupting event framed on its eve."""
        w = self.world
        a = w.pc
        was = self.snapshot
        self.skip_left = 0
        print()
        seasons = self.skip_done
        span = f"{seasons} season{'s' if seasons != 1 else ''}"
        print(f"--- {span} passed (year {was.get('year', w.year)} to "
              f"{w.year}) ---")
        if a is not None and was:
            deltas = []
            for key, label in (("qi", "qi"), ("insight", "insight"),
                               ("resources", "silver"),
                               ("standing", "standing"), ("karma", "karma"),
                               ("burden", "burden")):
                change = getattr(a, key) - was[key]
                if abs(change) >= 1:
                    deltas.append(f"{label} {change:+.0f}")
            if a.realm != was["realm"]:
                deltas.append(f"now {a.realm_name}")
            print(f"  {a.display()}, age {a.age}: "
                  + (", ".join(deltas) if deltas else "nothing much changed"))
        missed = self.flush(limit=DIGEST_LINES)
        self.flush_private(missed, quiet=True)   # the gains line covers it
        if not missed:
            print("  The chronicle was quiet.")
        if reason:
            print(f"  YOU WAKE: {reason}.")

    # -- a played throne (VII §10 is P7; P1 offers the door out) ----------

    def reign_turn(self) -> bool:
        w = self.world
        print()
        print(w.player_status("the year"))
        print("  A court runs at year tempo: one decision a year, and no qi "
              "while it lasts.")
        while True:
            cmd = self.read(f"[year {w.year}, on the seat] > ").strip()
            if self.quit:
                return False
            low = cmd.lower()
            if low in ("quit", "exit", "q"):
                self.quit = True
                return False
            if low in ("", "hold", "rule", "keep"):
                return True
            if low in ("abdicate", "lay down", "step down"):
                if w.player_abdicate():
                    self.flush()
                    return True
                print("There is no seat to lay down.")
                continue
            if self.observer_command(cmd):
                continue
            print("On the seat you may 'hold' the year or 'abdicate'.")

    # -- the year -------------------------------------------------------

    def season_turn(self, season: str) -> bool:
        w = self.world
        pc = w.pc
        if pc is None or not pc.alive:
            w.run_season(season)        # the world does not stop for a death
            self.flush()
            return True


        activity: Optional[str] = None
        if self.skip_left > 0:
            activity = self.skip_activity
        elif pc.is_ruler():
            if season == NPC_ACTION_SEASON and not self.reign_turn():
                return False
        else:
            activity = self.prompt(season)
            if self.quit:
                return False

        if self.skip_left > 0:
            reason = self.eve_reason(season)
            if reason is not None:
                self.wake(reason)       # stop the season BEFORE it
                if pc.is_ruler():
                    activity = None
                else:
                    activity = self.prompt(season)
                    if self.quit:
                        return False

        skipping = self.skip_left > 0
        watch = w.pc_watch()
        if activity is not None and not pc.is_ruler():
            w.player_season(activity)
        w.run_season(season)

        if not skipping:
            self.flush_private(self.flush())
            return True
        self.skip_left -= 1
        self.skip_done += 1
        if not pc.alive:
            self.wake("you did not walk out of it")
        else:
            alarms = w.pc_alarms(watch)
            if alarms:
                self.wake(alarms[0])
            elif self.skip_left == 0:
                self.wake(None)
        return True

    def on_death(self, hero: Agent) -> bool:
        w = self.world
        print()
        print(w.life_report(hero))
        successor = w.pc
        if successor is None or not successor.alive:
            print("There is no one young enough left to follow.")
            return False
        answer = self.ask(
            "succeed",
            f"{hero.display()} is gone. The chronicle turns to "
            f"{successor.display()} of {successor.sect} (age "
            f"{successor.age}, talent {successor.talent}, "
            f"{'/'.join(successor.traits)}).",
            ["play", "end"], "end")
        if answer != "play":
            return False
        w.take_over_pc()
        self.skip_left = 0
        self.hcursor = len(w.pc.history)
        print()
        print(w.pc_intro())
        print(self.menu())
        return True

    def run(self):
        w = self.world
        print(w.pc_intro())
        print(PLAY_HELP)
        print(self.menu())
        while not self.quit and w.pc is not None and w.pc.alive:
            hero = w.pc
            w.begin_year()
            for season in SEASONS:
                if self.quit:
                    break
                if not self.season_turn(season):
                    break
            if self.quit:
                break
            w.end_year()
            if self.skip_left == 0:
                self.flush_private(self.flush())
            if not hero.alive and not self.on_death(hero):
                break
        print()
        print(w.final_report())


def create_character(world: World, play: Play) -> Agent:
    """VII §2: name, sex and homeland. Everything else is rolled."""
    print("=" * 72)
    print("A new disciple walks up the mountain with the rest of the intake.")
    print("You may give them a name, a sex and a homeland. Talent, temper,")
    print("the village they came out of and everything after it are rolled.")
    print("=" * 72)
    name = play.read("Name (blank for a rolled one) > ").strip()
    sex = play.read("Sex [m/f, blank to roll] > ").strip().lower()
    sex = sex if sex in ("m", "f") else None
    lands = list(world.lands.values())
    print("Homelands:")
    for i, land in enumerate(lands, 1):
        print(f"  {i}. {land.name} ({land.word()})")
    choice = play.read("Homeland [number or name, blank to roll] > ").strip()
    land = None
    if choice.isdigit() and 1 <= int(choice) <= len(lands):
        land = lands[int(choice) - 1]
    elif choice:
        land = world.find_land(choice)
    return world.begin_play(name, sex, land, ask=play.ask)


def play_mode(world: World):
    session = Play(world)
    create_character(world, session)
    session.cursor = len(world.chronicle)
    session.hcursor = len(world.pc.history)
    session.run()


def main():
    p = argparse.ArgumentParser(
        description="Cultivation World Simulator (toy version)")
    p.add_argument("--years", type=int, default=None,
                   help="run N years non-interactively and print the report")
    p.add_argument("--seed", type=int, default=None,
                   help="RNG seed for a reproducible world")
    p.add_argument("--intake", type=int, default=INTAKE_SIZE,
                   help="students per intake cycle (default %(default)s)")
    p.add_argument("--play", action="store_true",
                   help="play agent 65 of the starting intake, one season "
                        "at a time (VII: the playable layer)")
    p.add_argument("--follow-pc", action="store_true",
                   help="run until the main character reaches the peak, dies "
                        "or leaves the path, then print their whole life "
                        "(--years, if given, caps the run)")
    args = p.parse_args()

    world = World(seed=args.seed, intake_size=args.intake)

    if args.play:
        play_mode(world)
    elif args.follow_pc:
        print(world.pc_intro())
        cap = args.years if args.years is not None else FOLLOW_CAP_YEARS
        hero = run_until_pc_resolved(world, cap)
        if hero is None:
            print("This world has no main character.")
        else:
            print(world.life_report(hero))
            print()
            print(world.famous_list())
    elif args.years is not None:
        print(world.pc_intro())
        run_years(world, args.years)
        print(world.final_report())
    else:
        interactive(world)


if __name__ == "__main__":
    main()
