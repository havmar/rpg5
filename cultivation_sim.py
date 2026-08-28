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
import math
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
# (How OFTEN is now the fighting stance's business: VII §4's edges carry
# their own maim chance and STANCE_MAIM_CRUEL is what a Cruel victor
# multiplies it by.)
CRUEL_MAIM_INSIGHT = 4
CRUEL_MAIM_GRUDGE = 3
# BLOODTHIRSTY — takes a duel past winning, and rides to any muster. The
# knob is deliberately small: a duel between equals kills one of the two
# more often than not, so a taste for them is a fast way to empty a sect.
# (Taking a duel past winning is VII §4's murderous EDGE now — see
# STANCE_MURDEROUS_TRAITS.)
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

# VII §8: a LIFE-DEBT is friendly the way a sworn brother is — the holder
# grieves, the obituary names them — and it is the one bond `_add_grudge`
# will not write over. Only a played healer ever mints one.
FRIENDLY_KINDS = {"friend", "sworn", "ally", "master", "disciple", "lover",
                  "life-debt"}
HOSTILE_KINDS = {"rival", "grudge"}

REL_DISPLAY = {
    "friend": "friend", "sworn": "sworn", "ally": "ally",
    "master": "master", "disciple": "disciple", "lover": "lover",
    "rival": "rival", "grudge": "enemy", "life-debt": "life-debt",
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
    "incursion": "summer",      # §7: the year the Waste comes over
}
# Resolution order INSIDE a season — the old event phase's order, kept so
# that stamping events across the calendar changes when they happen and not
# what happens.
AGENDA_ORDER = ("politics", "campaign", "war", "muster", "incursion",
                "revolt", "assassination", "usurpation", "sect", "answer",
                "petition", "tournament", "expedition", "feud", "grudge")
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
    "incursion": "the {edge} marches will not hold through {season}; the "
                 "Waste is coming over into {land}",
}
# Notices everyone can see coming, whether or not they are the player's
# business; the rest are shown only when they are a HARD interrupt for the PC.
AGENDA_PUBLIC = ("tournament", "expedition", "feud", "incursion")

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

# --- THE PLAYABLE LAYER: STANCES — EDGE x MANNER (VII §4) ------------------
# A stance is one EDGE (required) plus at most one MANNER. That two-slot
# grammar IS the combination rule: every sensible pair exists and the
# contradictions (murderous non-violence) cannot be written down at all.
#
# The kernel speaks stance too. `_duel` picks both fighters' stances off
# their traits and the fight's context, and every duel death, maiming,
# yield, spare and execution in the world now comes out of these numbers —
# which is why they are tuned to the aggregates the trait-to-lethality code
# they replaced produced, not to taste.
#
# NOTHING HERE BRIDGES A REALM (VII §5). The tyranny of realms is settled
# first: across a gap of one realm the fight is flee-or-die and the only
# column read is `lethal` (did somebody come to kill, or only to win). The
# weights tilt a fight between EQUALS and nothing else.
#
# The maim and execute columns are RETUNED, not §4's literal numbers. The
# spec's 2/5/15% maim is read by EVERY victor, where the code these tables
# replace let only a Cruel one cripple anybody, and it came out half again
# too many maimings; the execute rates had to come up to hold the old flat
# 0.55 a lethal duel killed at. §13 asks for the session-7 aggregates over
# the spec's decimals, and these hold them inside a couple of percent over
# 32 seeds x 200 years: ~245 dead in duels, ~100 spared, ~32 maimed.
#
#   stop     hp fraction left at which the fight is CALLED. §4 writes 75%
#            and 50%; both come down one swing (P3) so that a bout runs the
#            3-8 rounds VII §5 asks for and the pauses have somewhere to
#            fire. Zero means the edge itself never calls it: a killing
#            fight is ended by a yield (ORDERS_DEFAULT["yield"]) or by a
#            body.
#   kill     the ACCIDENT — a death nobody in the ring intended
#   maim     a crippling the loser carries out of it for good
#   weight   the one-roll exchange weight
#   dmg      P3: what a blow struck at this edge is worth. The harsher
#            edges hit harder, which shortens the bout and does NOT tilt it
#            — the race calibration absorbs damage exactly (VII §5).
#   execute  the victor's own appetite for finishing a beaten foe who
#            yields — the choice VII §4 puts in their hands, not the dice
#   lethal   whether a yield is even offered, and whether the realm-gap
#            branch above is a killing or a fleeing
STANCE_EDGES = {
    "sparring":  {"stop": 0.70, "kill": 0.00, "maim": 0.013, "weight": 0.0,
                  "dmg": 1.0, "execute": 0.0, "lethal": False},
    "duelling":  {"stop": 0.45, "kill": 0.02, "maim": 0.037, "weight": 0.0,
                  "dmg": 1.0, "execute": 0.0, "lethal": False},
    "allout":    {"stop": 0.0,  "kill": 0.10, "maim": 0.112, "weight": 0.15,
                  "dmg": 1.15, "execute": 0.35, "lethal": True},
    # Murderous kills by intent, not by accident, and does not stop to
    # cripple: it stops when the other one is dead or has been let go.
    "murderous": {"stop": 0.0,  "kill": 0.0,  "maim": 0.0,  "weight": -0.10,
                  "dmg": 1.15, "execute": 0.84, "lethal": True},
}
EDGE_ORDER = ("sparring", "duelling", "allout", "murderous")   # by harshness
# MANNERS — how you fight and what the fight is FOR.
#   weight    the one-roll exchange weight
#   taken     Rage: damage taken as well as dealt (P3 reads it; the one-roll
#             form hands the opponent the same weight)
#   early/late  Patience: P3's two-phase schedule. `weight` is what the
#             schedule is worth over a whole fight.
#   vs_rage / vs_vice   Harmonious: what it is worth against a burning
#             opponent, or one carrying a vice trait
STANCE_MANNERS = {
    "rage":        {"weight": 0.20, "taken": 0.20},
    "patience":    {"weight": 0.05, "early": -0.15, "late": 0.15},
    "harmonious":  {"weight": 0.0, "vs_rage": 0.10, "vs_vice": 0.10},
    "showy":       {"weight": -0.10, "standing": 1},
    "humiliating": {"weight": -0.10, "shame": 1, "grudge": 1},
    "studying":    {"weight": -0.15, "insight": 1},
    "merciful":    {"weight": -0.10, "spares": True},
}
# PROFICIENCY, rank 0-3: untrained HALVES what a stance gives you and
# DOUBLES what it costs. Ranks are earned through use, masters and the
# training hall — all of which is P5; P2 only stores them and reads them
# here (`stance_rank`). A played character's ranks live in
# `PlayerState.stances`; an NPC is trained UP TO the edge their own
# character takes them to and in the one manner their nature fights in, so
# an edge the situation forces on them is the expensive one.
STANCE_RANK_MAX = 3
STANCE_PROFICIENCY = {          # rank: (bonus multiplier, malus multiplier)
    0: (0.5, 2.0),
    1: (1.0, 1.0),
    2: (1.15, 0.85),
    3: (1.3, 0.7),
}
STANCE_NPC_RANK = 1             # the stances a character's own nature has
# Which manner a trait fights in, in priority order — the first trait an
# agent carries decides. (VII §4 names Cruel, Proud, Cautious, Scholarly
# and Righteous; the other three are the same reading of traits the sim
# already fights with.)
STANCE_TRAIT_MANNER = [
    ("Righteous", "merciful"),
    ("Cruel", "humiliating"),
    ("Scholarly", "studying"),
    ("Proud", "showy"),
    ("Reckless", "rage"),
    ("Cautious", "patience"),
    ("Humble", "harmonious"),
    ("Cold", "patience"),
]
# Who carries a fight past the edge its context asked for. A killing matter
# is a killing matter whoever came to it; these are the people who make one
# out of something else. (This replaces the flat trait-to-lethality roll the
# kernel used to make inside _duel: the same behaviour, said in stance.)
STANCE_MURDEROUS_TRAITS = {"Bloodthirsty": 0.80, "Ruthless": 0.30,
                           "Vengeful": 0.25}
STANCE_MURDEROUS_PLAIN = 0.05   # ... multiplied down when nobody came to a
                                # fight that was ever going to be a killing
STANCE_EXECUTE_ATTACKED = 0.30  # ... and what it adds to have been fought
                                # by somebody who DID come to kill, when you
                                # did not
STANCE_MERCIFUL_HOLDS = 0.6     # a Righteous fighter who keeps the pledge
                                # even after the other one drew for the neck
# The victor's appetite for a yield, on top of the edge's own `execute`.
STANCE_EXECUTE_TRAITS = {"Bloodthirsty": 0.30, "Ruthless": 0.25,
                         "Vengeful": 0.10, "Cruel": 0.10,
                         "Righteous": -0.30, "Humble": -0.15,
                         "Loyal": -0.10}
STANCE_MAIM_CRUEL = 5.0         # a Cruel or humiliating victor does not stop
                                # at winning: the edge's maim chance, times
STANCE_SEEN = 0.5               # a killing edge is remembered by somebody
STANCE_SEEN_STANDING = 1        # ... and costs the standing of the one who
                                # brought it: people remember who came to kill
# What the chronicle says. A manner is what a fight LOOKED like, so it is
# printed when there is one; an edge is what it was FOR, and speaks when
# the fighter brought no manner to it.
MANNER_PHRASE = {
    "rage": "fought in a rage",
    "patience": "waited out the storm",
    "harmonious": "gave the quarrel nothing to burn",
    "showy": "fought for the gallery",
    "humiliating": "made a lesson of it",
    "studying": "fought to learn",
    "merciful": "fought to end it and no further",
}
EDGE_PHRASE = {
    "sparring": "kept the edges blunted",
    "duelling": "fought it as a duel",
    "allout": "held nothing back",
    "murderous": "had come to kill",
}
# A maiming is either meant or it is not, and the line says which.
MAIM_LINES = {
    "meant": "{winner} went on breaking {loser} after {where} was already "
             "decided; the mark will not come off [epithet: {ep}] (+insight).",
    "accident": "{winner} put {loser} down harder than {where} called for, "
                "and the damage did not heal [epithet: {ep}] (+insight).",
}

# --- THE PLAYABLE LAYER: ROUND COMBAT (VII §5) -----------------------------
# ONE DISTRIBUTION, TWO RESOLUTIONS. The kernel's one roll (`duel_odds`,
# pa/(pa+pb)) stays the truth and every fight off camera is still settled
# with it; a fight the PLAYED character is in unfolds into rounds instead.
# THE INVARIANT: the round model's win probability must sit within three
# percentage points of that one roll across the matchup grid, so the funnel
# cannot tell which resolution ran. `--test-combat` measures it.
#
# How the invariant is HELD rather than tuned: a bout is a RACE. Each
# fighter's blow (`swing`) is rolled once when the bout opens, so the number
# of exchanges each of them needs to win is a known pair of whole numbers,
# and the chance of taking your own before the other takes theirs is a
# binomial tail. `_exchange_chance` INVERTS that tail — it solves for the
# per-exchange chance whose race comes out at exactly the one roll's number.
# Everything the rounds add (heavier blows at the harsher edges, rage
# trading damage both ways, patience's two-phase schedule) only moves the
# geometry, and the inversion absorbs it.
#
# What it deliberately does NOT absorb: the calibration is computed for two
# UNWOUNDED fighters stopping at the edge's own line. Fight it wounded, or
# with a yield line you moved yourself, and the geometry is worse than the
# reference — which is exactly how a wound is allowed to cost something
# without the kernel ever hearing about it.
# THE HARD CAP (VII §5). Everything the player layer will ever add to a
# fighter — Body and Weapon proficiency (P5), forged gear (P6), techniques
# (P7) — is summed and clipped HERE, at less than half a realm's ten points,
# so that nothing this layer builds can bridge a realm. `player_power` is
# the one place it is enforced; P5 fills it in.
PLAYER_POWER_CAP = 4.0
ROUND_HP = 100.0                # a whole body, in points. hp exists ONLY
                                # inside a fight (VII §5); what walks out is
                                # a wound.
ROUND_SWING = (12.0, 20.0)      # what the loser of an exchange takes ...
ROUND_SWING_TILT = 0.5          # ... raised by the power ratio, this power
ROUND_SWING_CLAMP = (0.75, 1.35)
ROUND_CAP = 40                  # a bout neither can finish is called on hp
# Patience's two-phase schedule (VII §4): the early rounds are given away
# and taken back afterwards. Two rounds is what makes the schedule worth
# STANCE_MANNERS["patience"]["weight"] over a whole fight — the number the
# one roll reads — measured against --test-combat, not assumed.
ROUND_PATIENCE_ROUNDS = 2
# THE PAUSE THRESHOLDS (VII §5), as a fraction of the fighter's own maximum.
# §5 asks for 50% and 25%, and neither survives contact with a 12-20 point
# swing: 50% lands ON the duelling stop line, and 25% IS the yield, so the
# fight would be over before either could be a choice. So the first is moved
# up one swing — 60% is "this is going badly" — and the second is not a
# fixed number at all but THE BRINK: one exchange above whatever line this
# fighter actually stops at, so it always arrives with exactly one decision
# left. PAUSE_*[1] is its floor, and a brink closer than PAUSE_BRINK_GAP to
# the first threshold is dropped rather than asked twice in two rounds —
# which is why a duel pauses once and a killing fight twice.
PAUSE_OWN = (0.60, 0.30)        # own hp: yield / stance / fight on / escape
PAUSE_FOE = (0.60, 0.30)        # theirs, while ahead: ease off, or change
PAUSE_BRINK_GAP = 0.10
# What a round looks like from outside, by how the one who took it is doing.
# Picked by round number, never by a die: narration must not move the world.
ROUND_BLOW_LINES = {
    "even": ["{w} turned {l}'s guard and made them pay for it",
             "{w} took the exchange; {l} gave a step and kept their feet",
             "{w} came inside {l}'s reach and was gone again before it told",
             "{w} read the opening and took it"],
    "hurt": ["{w} broke through and put {l} back on their heels",
             "{w} landed one that {l} felt in the bone",
             "{l} blocked it late, and the block cost as much as the blow",
             "{w} drove {l} across the ground they had been holding"],
    "failing": ["{w} landed one that folded {l} up",
                "{l} is fighting off the back foot now, and losing it",
                "{w} put {l} down and let them get up",
                "{l} can barely lift the guard, and {w} knows it"],
}
ROUND_OPEN = "{a} ({aw}) and {b} ({bw}) squared off{ctx}."
ROUND_LINE = "   {n}. {blow}.  [{a} {ahp:.0f} | {b} {bhp:.0f}]"

# --- THE PLAYABLE LAYER: WOUNDS (VII §5) -----------------------------------
# WOUNDS, NOT HIT POINTS. Walk out of a fight low and you carry it: a
# smaller body to fight the next one with, and a season that pays less.
# Maiming is untouched — permanent, an epithet, the kernel's `_maim`.
WOUND_LIGHT_AT = 0.50           # walked out under this: a light wound
WOUND_SERIOUS_AT = 0.25         # ... and under this, a serious one
WOUND_MAX_HP = {0: 0.0, 1: 10.0, 2: 25.0}    # points off the body
WOUND_PAYOUT = {0: 1.0, 1: 1.0, 2: 0.5}      # a serious wound halves a season
WOUND_WORD = {0: "unhurt", 1: "light", 2: "serious"}
# Seasons that heal one level. The road, the hunt, the front and the muster
# do not; sitting still does. (A healer or a healing pill closes one
# instantly — that is P6, and `heal_wound` is the seam it writes through.)
# P5 adds the two training seasons that are sitting still: the reading room
# and the sect library. Drilling the body or the sword is not rest, and the
# front is still not rest at all.
WOUND_REST = ("cultivate", "retreat", "socialize", "theory", "hall")
WOUND_LINES = {
    1: "{who} walked out of it carrying a wound that will keep for a season.",
    2: "{who} walked out of it badly hurt; everything will come harder until "
       "it closes.",
}
# ... and the one line it writes, in whichever hand closed it (P6 §8: a
# healer and a healing pill go through the same door, and say so).
WOUND_HEALED = {
    "rest": "{who} rested, and the {what} wound closed.",
    "pill": "{who} swallowed a healing pill, and the {what} wound closed "
            "over inside the hour.",
    "craft": "{who} closed their own {what} wound in the infirmary, which "
             "is a good deal of what the craft is for.",
}

# --- THE PLAYABLE LAYER: BREAKING OFF (VII §5) -----------------------------
# The door out of a killing matter. Base one in two; the realm gap term is
# the hook for the fights this layer never sees (a gap is settled before
# rounds are reached at all), and the Movement term is P7's technique
# school reaching back for it.
ESCAPE_BASE = 0.50
ESCAPE_CAUTIOUS = 0.15
ESCAPE_PER_REALM = 0.25
ESCAPE_MOVEMENT = 0.15          # per rank of P7's Movement school
ESCAPE_CLAMP = (0.05, 0.95)
ESCAPE_INSIGHT = 2              # running is a kind of adversity too
ESCAPE_STANDING = 1             # ... and it is seen

# --- THE PLAYABLE LAYER: STANDING ORDERS (VII §6) --------------------------
# Orders are to a played character exactly what traits are to an NPC, which
# is why the machinery underneath is the same one. A bout that resolves
# entirely inside them never asks a question, and prints as one line like
# anybody else's fight.
ORDERS_DEFAULT = {
    "edge": "context",      # what the fight was called at, or an edge of
                            # your own (you may only carry it FURTHER)
    "manner": "nature",     # what your own character fights in, or a manner
    "yield": 0.25,          # own hp at which you stop fighting
    "execute": "ask",       # spare / ask / kill — a beaten foe who yields
    "escape": "ask",        # never / ask / always, in a killing fight
    "pauses": "ask",        # ask / orders — does a crossing stop the fight
}
ORDERS_CHOICES = {
    "edge": ("context",) + EDGE_ORDER,
    "manner": ("nature", "none") + tuple(STANCE_MANNERS),
    "execute": ("spare", "ask", "kill"),
    "escape": ("never", "ask", "always"),
    "pauses": ("ask", "orders"),
}
ORDERS_HELP = {
    "edge": "how far you take a fight you did not call",
    "manner": "how you fight when nobody has asked you otherwise",
    "yield": "the hp you stop at (0 to fight to the last)",
    "execute": "what you do with a beaten foe who yields",
    "escape": "whether you try the door in a killing fight",
    "pauses": "'orders' fights the whole bout without asking",
}
ORDERS_YIELD_CLAMP = (0.0, 0.60)
# NPCs hit the same thresholds and answer them by their nature. A yield line
# is where a character stops fighting, and the traits that cannot stop are
# the ones that get people killed.
NPC_YIELD_BASE = 0.25
NPC_YIELD_TRAITS = {"Proud": -0.10, "Reckless": -0.15, "Bloodthirsty": -0.20,
                    "Loyal": -0.05, "Cautious": 0.10, "Humble": 0.05}
NPC_YIELD_CLAMP = (0.0, 0.40)
# The manner a losing NPC changes into at a threshold, and the one a winning
# NPC eases off into. First trait held decides; no trait, no change.
NPC_PAUSE_LOSING = [("Reckless", "rage"), ("Bloodthirsty", "rage"),
                    ("Vengeful", "rage"), ("Cautious", "patience"),
                    ("Cold", "patience"), ("Scholarly", "studying"),
                    ("Humble", "harmonious")]
NPC_PAUSE_WINNING = [("Cruel", "humiliating"), ("Proud", "showy"),
                     ("Scholarly", "studying"), ("Humble", "merciful")]
NPC_ESCAPE_TRAITS = ("Cautious", "Broken")     # who tries the door ...
NPC_ESCAPE_CHANCE = 0.5                        # ... and how often

# --- THE DEMON FRONT (VII §7) ----------------------------------------------
# DEMONS ARE A FIELD, NOT AGENTS. Like the common people (VI §10), the host
# on the far side of the marches is a NUMBER and a set of scene tables: one
# threat level, no roster, no court, no tribute, nothing that can be
# negotiated with. Named demon lords as real agents are a later session,
# deliberately out of scope.
#
# At worldgen one outer EDGE of the 3x3 grid borders the DEMON WASTE; the
# two or three lands along it are MARCH-LANDS, and the front is a fact of
# their geography, like weather.
DEMON_WASTE_EDGES = ("north", "south", "west", "east")
MARCH_SHELTERED_CHANCE = 0.45   # one corner of that edge the Waste never
                                # reaches — which is what makes the marches
                                # two lands as often as three
WASTE_EDGE_WORDS = {"north": "northern", "south": "southern",
                    "west": "western", "east": "eastern"}
# THE POT. Threat is a float 0-10 and starts at 3. §7's drift is +0.15 and
# its sink is -0.1 per cultivator-SEASON served; the drift is read at that
# same resolution (per season — 0.6 a year), because it is the only reading
# on which §12's cadence comes out: an incursion every 8-15 years, off a 2-4
# reset and a 35% roll once the pot is over 7. At §7's literal +0.15 a YEAR
# the climb alone is twenty-six years and the front never boils.
DEMON_THREAT_START = 3.0
DEMON_THREAT_DRIFT = 0.15       # per season; the pot boils on its own
DEMON_THREAT_MAX = 10.0
DEMON_THREAT_PER_SEASON = 0.1   # what one cultivator-season on the line buys
DEMON_RELIEF_CAP = 0.20         # ... and all the relief one year can hold.
                                # The line is long: past a handful of swords
                                # the Waste does not notice. Without the cap
                                # the cadence would be a reading of how many
                                # Righteous the last intake happened to roll.
DEMON_THREAT_WORDS = [(2.0, "quiet"), (4.0, "stirring"), (6.0, "restless"),
                      (8.0, "boiling"), (99.0, "at the gates")]
# THE DRAG: the marches live under raids that never stop, and settle one to
# two points under the temper the rest of their land would have had. What
# they are worth ON PAPER is higher than any other land's — a country that
# keeps an army fed keeps a market, and the cores off the Waste are worth
# silver — and the drag is what the front takes back out of it. Both halves
# are needed: without the bonus the marches are simply the worst-off lands
# on the map, and VI §13's count of badly-RULED countries stops meaning
# anything.
MARCH_BASELINE = 1.3            # what the front economy is worth on paper
MARCH_DRAG_PER_THREAT = 0.024   # prosperity a year, per point of threat
MARCH_DRAG_CAP = 0.30

# THE FRONT ACTIVITY (VII §3, §7): a season of deadly fighting, on a risk
# table roughly twice as lethal as the harsh road, paying insight, standing,
# materials and the front's own epithets. There is nothing here to duel —
# the Waste is a number, not an agent — so it is resolved with the
# expedition's kind of roll and never through `_bout`.
FRONT_MIN_REALM = 2             # the marches do not take Qi Condensation
FRONT_MIN_AGE = 18              # ... nor children
FRONT_POWER = (18.0, 30.0)      # what a season on the line throws at you
FRONT_POWER_PER_REALM = 11.0    # the deeper in they send the strong ...
FRONT_POWER_PER_THREAT = 2.6    # ... and the hotter the pot is
FRONT_ODDS = (0.10, 0.88)
FRONT_SPOILS = (2, 6)           # cores, black iron, hides off the Waste
FRONT_INSIGHT = 2               # a season of it teaches whatever happens
FRONT_STANDING_CHANCE = 0.35
FRONT_KARMA = 1                 # per year of standing between people and it
FRONT_DEATH = 0.22              # of a season that goes wrong
FRONT_MAUL = 0.45               # ... and of the rest, the ones carried back
FRONT_MAUL_INSIGHT = 4
FRONT_MAUL_EPITHET = 0.30
FRONT_DRIVEN_INSIGHT = 2
FRONT_EPITHETS = ("Demon-Scarred", "Ash-Marked", "Gate-Held")
FRONT_VETERAN_EPITHET = "Wastewalker"
FRONT_VETERAN_SEASONS = 8       # seasons on the line that earn it
FRONT_VETERAN_YEARS = 3         # §3: a front served on within three years is
                                # still yours, and wakes a timeskip
FRONT_VOLUNTEER_TRAITS = {"Righteous": 3.0, "Bloodthirsty": 3.0,
                          "Reckless": 1.5, "Loyal": 1.0}
FRONT_VOLUNTEER_NATIVE = 1.0    # blood in that land ...
FRONT_VOLUNTEER_NATIVE_MULT = 2.0   # ... and march-land natives, doubled
FRONT_VOLUNTEER_FULL = 6.0      # weight at which someone is certain to go
FRONT_CHANCE = 0.03             # an eager cultivator's year, given to it
FRONT_CHANCE_PER_THREAT = 0.006     # a boiling front calls louder
FRONT_RETURN = 3.0              # ... and a soldier goes back. This is what
                                # makes a veteran's log read like a war
                                # record instead of a hobby: service comes
                                # in stretches, and the stretches are what
                                # the front kills people in the middle of.
FRONT_LINES = {
    "held": [
        "{who} stood a season on the {edge} line beyond {where} and came "
        "back off it with the sect's share of the cores.",
        "{who} held a stretch of the {edge} marches above {where}; the "
        "things that came over it in the dark did not get past (+silver).",
        "{who} spent the season burning what crossed into {land}, and was "
        "paid in black iron for it.",
    ],
    "quiet": [
        "{who} watched an empty stretch of the {edge} marches; nothing came "
        "over it that season.",
        "{who} stood the line above {where} through a quiet season of rain "
        "and rumour.",
    ],
    "driven": [
        "{who} was driven off the line above {where} and gave up a mile of "
        "{land} before the wall held (+insight).",
        "{who} lost the stretch they were given on the {edge} marches, and "
        "walked back through what was left of the villages (+insight).",
    ],
    "maul": [
        "{who} was carried off the {edge} marches half-dead, and the thing "
        "that did it went back over the line alive (+insight).",
        "{who} was broken on the line above {where} and lived; the Waste "
        "keeps what it takes off a body (+insight).",
        "{who} came back from the {edge} front with the marks of it and "
        "little else (+insight).",
    ],
    "death": [
        "was pulled down on the {edge} marches above {where}",
        "did not come back off the line in {land}",
        "was lost in the dark beyond {where}, on the {edge} front",
    ],
}
FRONT_DEFENDED = "the villages behind the {edge} marches"

# INCURSION (§7): while the pot is over the line, the year the Waste comes
# over. A one-year event and the front's only world-scale one: the marches
# pay in prosperity and conscripts, the defenders are drawn like an
# expedition, and the whole thing is resolved as one contest against the
# threat number. Defeat is rare and permanent — a settlement is SWALLOWED.
INCURSION_AT = 7.0              # threat at or over which it can happen
INCURSION_CHANCE = 0.35         # ... and the yearly roll once it can
INCURSION_DEFENDERS = (5, 10)
INCURSION_VETERAN_WEIGHT = 2.0  # the ones who know that ground
INCURSION_NATIVE_WEIGHT = 2.5   # ... and the ones whose ground it is
INCURSION_BASE_WEIGHT = 0.6     # everyone else the sects can reach
INCURSION_WALL_BASE = 45.0      # the marches' own walls, forts and watch:
                                # everything holding that line which is not
                                # an agent, and never was one
INCURSION_THREAT_SCORE = 4.0    # what a point of threat is worth against it
INCURSION_ARMY_SCORE = 0.45     # ... against the march polities' levies
INCURSION_CULTIVATOR_SCORE = 0.35   # ... and a cultivator's power, as in war
INCURSION_NOISE = 0.25
INCURSION_ODDS = (0.35, 0.97)   # the line usually holds
INCURSION_DEATH = 0.10          # of the drawn, when it does
INCURSION_DEATH_LOST = 0.30     # ... and when it does not
INCURSION_INSIGHT = 4
INCURSION_STANDING = 2
INCURSION_KARMA = KARMA_RESCUE  # §7: standing in front of other people
INCURSION_RESET = (2.0, 4.0)    # what a thrown-back host leaves behind
INCURSION_LOST_THREAT = 0.5     # ... and what a broken line adds to it
INCURSION_PROSPERITY = -1.5     # the land it came over
INCURSION_PROSPERITY_OTHER = -0.5   # ... and the rest of the marches
INCURSION_UNREST = 1
INCURSION_DEAD = (600, 15000)   # conscripts and villagers: chronicle colour
INCURSION_OPEN = [
    "The Waste came over the {edge} marches into {land} in force; the "
    "levies of {domain} were called out and {dead} of them and the villages "
    "behind them died in the first month.",
    "The {edge} front broke open into {land}: {dead} conscripts and "
    "villagers were dead before the sects had riders on the road.",
]
INCURSION_HELD = [
    "The line above {where} held; the host was broken on it and went back "
    "over into the Waste.",
    "{land} threw the incursion back at {where} and burned what was left of "
    "it on the field.",
]
INCURSION_LOST = [
    "The line above {where} broke. {where} is gone — the Waste holds the "
    "ground it stood on, and nothing has come back out of it.",
    "Nothing held in front of {where}. The village and everyone still in it "
    "were swallowed, and the {edge} front is a mile deeper into {land} than "
    "it was.",
]
# The front's own pleas: a march-land village below PETITION_AT begs the
# sects for relief through the ordinary petition machinery (§7 — no new
# diplomacy anywhere). The opposition is the Waste, not a magistrate, so
# answering one makes no enemy of the court and earns no grudge.
FRONT_PETITION_MISSIONS = [
    ("to send a sword to the wall above {where}",
     "stood the wall above {where} until the season turned and the raids "
     "stopped",
     "the wall"),
    ("to clear the things nesting in the fields of {where}",
     "burned out what had been nesting in the fields of {where}",
     "the nests"),
    ("to bring the people of {where} back through the line",
     "brought what was left of {where} back through the line alive",
     "the road out"),
]
FRONT_PETITION_OPPOSITION = 10.0    # the wall, before the pot is counted
FRONT_PETITION_PER_THREAT = 4.0     # ... and per point of the pot

# --- THE PLAYABLE LAYER: TRAINING, MASTERS AND THE HALL (VII §8) -----------
# ONE RANK MECHANIC, and this is it. Everything a played character can grind
# at — the three proficiencies below, the stance ranks P2 left for this
# session to EARN, and P6's three professions — is the same track: seasons of
# practice go in, and rank N costs `step` x N of them. A track is a SHAPE
# (here) and a STORE (a dict on `PlayerState`), and nothing else; adding
# alchemy is a row in this table and a store, not new code. `World.track_rank`
# is the only place a rank is ever computed.
RANK_SHAPES = {
    #  name          max rank, seasons that rank N costs
    "proficiency": {"max": 5, "step": 1.0},
    # A stance is dearer per rank than a drill: it is a way of fighting, not
    # a habit of the arms. P2 wrote the ranks; this is where they come from.
    "stance": {"max": STANCE_RANK_MAX, "step": 2.0},
    # P6: §8's three skins on the one mechanic — alchemy, forging, healing.
    # Three seasons for the first rank, six for the second, nine for the
    # third: a craft is the longest project a played life has, and nothing
    # else in this block had to change to carry it.
    "profession": {"max": 3, "step": 3.0},
}
# THE EFFECTS ARE DELIBERATELY SMALL (§8). A fifth-rank body is worth about
# what a light wound costs; a fifth-rank weapon is two and a half points
# inside a cap of four; a fifth-rank theory is five percentage points on a
# tribulation and a trickle of insight. They are texture and a PROJECT —
# something a played life is about between the years the world happens to it
# — and they are not a way through a realm.
PROFICIENCIES = {
    # key: (the activity's label, the one line the menu shows)
    "body": ("Body", "a harder body, and wounds that come off lighter"),
    "weapon": ("Weapon", "the blade, and the stance you fight in"),
    "theory": ("Theory", "the tribulation, and a slow trickle of insight"),
}
PROFICIENCY_SHAPE = "proficiency"
PROFICIENCY_WORDS = ("untrained", "drilled", "practised", "seasoned",
                     "hardened", "past teaching")
PROFICIENCY_BODY_HP = 1.0       # points of body a rank is worth. Small on
                                # purpose and MEASURED small: hp is the one
                                # thing the one roll never hears about (VII
                                # §5 — the reference geometry is two whole
                                # bodies), so a full Body track is worth
                                # about three points of win rate on an even
                                # duel, comfortably under what the whole +4
                                # power cap buys. --test-combat prints it.
PROFICIENCY_BODY_RESIST = 0.12  # ... and the chance per rank that what walks
                                # out of a fight walks out one level lighter
PROFICIENCY_WEAPON_POWER = 0.5  # power a rank is worth, INSIDE the §5 cap
PROFICIENCY_THEORY_TRIBULATION = 0.01   # per rank, on the breakthrough roll
PROFICIENCY_THEORY_INSIGHT = 0.4        # what a season of reading pays
TRAIN_STANCE_SEASONS = 1.0      # a weapon season also drills the stance you
                                # actually fight in (§3)
# A season of training is still a season AT THE SECT, and pays a fraction of
# what sitting in the hall cultivating pays. This is not generosity, it is
# §12's autopilot target: a random legal-choice hand has to come out of the
# menu at an ordinary cultivator's pace, and every activity added to the menu
# that pays no qi at all quietly makes the season layer a PENALTY for being
# played. The fraction is set where it restores the qi a uniform hand made
# before this session's five new activities widened the menu — measured, not
# guessed (see `autocmp.py` in the tuning scratch). Cultivating still pays
# two and a half times as much, so a rank is bought and not found.
TRAIN_QI_SHARE = 0.4
FIGHT_DRILL_SEASONS = 0.5       # ... and §4's other half: a stance carried
                                # through a real fight is worth half a season
                                # of drilling it. Ranks come from USE, and
                                # this is what "use" is worth.
TRAIN_LINES = {
    "body": [
        "{who} spent the season on the practice ground, and on the hill "
        "above it, and on the hill again.",
        "{who} carried stone up the mountain all season for no reason "
        "anybody could see.",
        "{who} drilled the forms until the forms stopped costing anything.",
    ],
    "weapon": [
        "{who} spent the season at the racks, working {stance} against "
        "whoever the hall would give them.",
        "{who} drilled {stance} all season against a post that never "
        "tired of it.",
        "{who} took the sword out every morning of the season and put it "
        "back every night a little better.",
    ],
    "theory": [
        "{who} spent the season in the reading room over the older "
        "commentaries (+insight).",
        "{who} read the tribulation records of four dead disciples all "
        "season and copied out what killed them (+insight).",
        "{who} argued the theory of the {realm} passage with the "
        "librarians until the librarians gave up (+insight).",
    ],
}
TRAIN_RANK_LINES = {
    "body": "{who}'s body has caught up with the drills ({word}: "
            "Body {rank}/{max}).",
    "weapon": "{who}'s hands have caught up with the sword ({word}: "
              "Weapon {rank}/{max}).",
    "theory": "{who} has read past what the sect bothers to teach ({word}: "
              "Theory {rank}/{max}).",
}
STANCE_RANK_LINE = ("{who} drilled {stance} until it stopped being a "
                    "decision (rank {rank}/{max}).")
STANCE_TAUGHT_LINE = "{who} was taught {stance} by {by} (rank {rank}/{max})."

# THE SECT TRAINING HALL (§3). The library and the practice hall are the
# sect's, not yours: they open for standing and they cost silver, and what
# they hold is FORMS — the stances everybody in the sect is supposed to know
# and nobody has bothered to teach you. The other half of the hall is P7's
# (techniques are cards, and the hall is where the sect sells them); the seam
# is `_hall_technique` and it is empty until then.
HALL_STANDING = 4               # the hall does not open for a nobody
HALL_COST = 3                   # silver a season in it costs
HALL_TEACHES = 0.60             # ... and the seasons that teach a form
HALL_STANCE_RANK = 1            # what the hall's teaching is worth: the form
HALL_THEORY = 0.5               # the reading that comes with it, in seasons
HALL_STANDING_GAIN = 0.25       # being seen at the right desks
HALL_LINES = {
    "taught": "{who} spent the season in the {sect} training hall and came "
              "out of it knowing {stance} (-silver).",
    "read": "{who} spent the season in the {sect} training hall, mostly "
            "reading; nothing in it was new.",
    "shut": "{who} was turned away from the {sect} training hall: the "
            "library opens for standing, and pays for its lamps in silver.",
}

# SEEK A MASTER (§8). A search season turns somebody up; their TRIAL is a
# scene, and the scene is a reading of the RECORD — what the karma ledger
# says, what adversity has taught, what name the epithets carry, and one bout
# at Sparring against somebody of the seeker's own height. A won master is a
# teaching multiplier, a grant of stances, and (P7) sometimes a technique;
# and it is a REAL relationship, bound through `_bind` like any other, which
# the world can kill, betray or avenge with no further help from this table.
MASTER_MIN_GAP = 1              # §8: realm >= PC + 1
MASTER_MIN_AGE_GAP = 8          # ... and long enough on the road to teach it
MASTER_FIND = 0.55              # a season of asking that turns somebody up
MASTER_POOL = 5                 # the candidates a season weighs
MASTER_WEIGHT_BASE = 1.0
MASTER_WEIGHT_TRAIT = 2.0       # a temper the seeker shares
MASTER_WEIGHT_SECT = 2.5        # their own sect first ...
MASTER_WEIGHT_LAND = 1.5        # ... then their own country
MASTER_WEIGHT_KNOWN = 3.0       # somebody who already knows their face
MASTER_WEIGHT_VICE = -1.5       # ... and what a black ledger costs a teacher
MASTER_TRIAL_KARMA = 0.20       # the ledger, read in the master's direction
MASTER_TRIAL_INSIGHT = 0.15
MASTER_TRIAL_EPITHET = 1.5      # a name is a kind of record
MASTER_TRIAL_STANDING = 0.25
MASTER_TRIAL_TALENT = 0.40
MASTER_TRIAL_WON = 3.0          # the bout at Sparring, taken ...
MASTER_TRIAL_LOST = 0.5         # ... and lost in front of them
MASTER_TRIAL_NOISE = 2.0        # what the day itself is worth
MASTER_TRIAL_NEED = 4.0         # what an ordinary teacher asks
MASTER_TRIAL_PER_REALM = 2.0    # ... and what each realm of reach adds
MASTER_INTENSITY = 3            # bound as close as a sworn brother
MASTER_TEACHING = 1.6           # what a training season is worth under one
MASTER_STANCE_CHANCE = 0.20     # ... and the seasons they simply teach you
MASTER_GIFT_RANK = 2            # §4: a parting gift can be Patience at 2
MASTER_KARMA = 1                # taking a disciple is a kindness
MASTER_INSIGHT = 2              # being taken is a lesson
MASTER_LINES = {
    "none": "{who} spent the season asking after teachers, and was passed "
            "from one closed door to the next.",
    "found": "{who} went to {master} and asked to be taught.",
    "spar": "a master's trial",
    "passed": "{master} took {who} as a disciple after the trial "
              "(+insight).",
    "failed": "{master} heard {who} out, watched them fight, and sent them "
              "back down the mountain.",
    "gift": " {master} taught them {stance} on the day of it.",
    "have": "{who} already has a master, and a second one is not a thing "
            "the sects would sit still for.",
}

# --- THE PLAYABLE LAYER: PROFESSIONS (VII §8) ------------------------------
# ONE RANK MECHANIC, THREE SKINS. A profession is a row in `RANK_SHAPES`
# (`{"max": 3, "step": 3.0}` — three seasons for the first rank, eighteen for
# the whole ladder) and a store on `PlayerState`, and that is the entire
# machinery: `World._practice` is the same dumb accumulator P5's drills go
# through, and `World.track_rank` is still the only place a rank is computed.
#
# What the three skins are FOR: a profession is the player's answer to a
# world that hands out nothing on request. Alchemy buys SPEED and charges
# for it at the ceiling; forging buys a point of power and silver; healing
# buys the one currency the kernel has never sold — other people's debt.
#
# NPCs DO NOT PRACTISE PROFESSIONS (v1, §8). Their single `resources` number
# is already the abstraction of every pill, blade and physician in the world,
# and nothing below is ever reached from an NPC path: no die is rolled here
# for anyone whose `play` is None, which is why the batch stream is
# bit-identical across this session.
PROFESSION_SHAPE = "profession"
PROFESSIONS = {
    # key: (the menu's label, the one line the menu shows)
    "alchemy": ("The furnace (alchemy)",
                "pills — qi, healing, clarity — and the poison they leave"),
    "forging": ("The forge",
                "gear worth a point or two of power, and sellable"),
    "healing": ("The infirmary (healing)",
                "your own wounds free, and other people's at a price"),
}
PROFESSION_WORDS = ("unlearned", "apprentice", "journeyman", "master")
# §8: rank 2+ NEEDS A TEACHER OR A MANUAL. The seasons still go in — a wall
# is not a hole in the floor — but the hands stop learning from them until
# somebody who knows the craft is standing there or has written it down.
PROFESSION_TEACHER_RANK = 2
PROFESSION_QI_SHARE = 0.4       # the furnace and the forge are AT THE SECT,
                                # and a season at them pays the same fraction
                                # of a cultivation season that P5's training
                                # does (TRAIN_QI_SHARE, and measured with it):
                                # every activity on the menu that pays no qi
                                # at all quietly makes being played a penalty.
CRAFT_SPOIL = {0: 1.0, 1: 0.35, 2: 0.15, 3: 0.0}    # the season's work,
                                                    # ruined, by rank
# A CRAFT IS NOT A SAFE ROOM. Furnaces go up, billets go through a hand, and
# the fever the patient was carried in with turns out to be catching. This
# is not decoration: without it, three whole activities on the season menu
# carried NO risk at all, and §12's autopilot — which picks by coin — quietly
# came out ahead of the sixty-four beside it purely by having safer places to
# spend a season in. Measured against P5's bot (2.32 deaths per 100 years) and
# set to put the hazard back where it was.
CRAFT_ACCIDENT = {"alchemy": 0.04, "forging": 0.03, "healing": 0.03}
CRAFT_ACCIDENT_DEATH = 0.10     # ... of which this many do not get up
CRAFT_ACCIDENT_SERIOUS = 0.25   # ... and this many of the rest are bad
                                # enough to leave a mark on the heart as
                                # well as the arm. Only the bad ones pay
                                # BURDEN: a ceiling eaten a point at a time
                                # is the PILL's signature in this session,
                                # and a trade should not quietly counterfeit
                                # it — what a craft costs is a season and a
                                # body.
CRAFT_ACCIDENT_LINES = {
    "alchemy": "{who}'s furnace went up in their face; they came out of the "
               "room on their hands and knees.",
    "forging": "{who} took a white billet across the forearm at the forge "
               "and lost the rest of the season to it.",
    "healing": "{who} took the fever off their own patient and spent the "
               "back half of the season on the infirmary floor.",
}
CRAFT_ACCIDENT_BAD = " They were a long time coming right again (+burden)."
CRAFT_DEATHS = {
    "alchemy": ["killed when a furnace went up in a sect workshop",
                "poisoned by their own batch, testing it on themselves"],
    "forging": ["killed at the forge when a quenching tank flashed over",
                "bled to death in a sect workshop after a slip at the anvil"],
    "healing": ["carried off by a fever taken from a patient in the "
                "infirmary",
                "dead of the plague they had spent the season treating"],
}
PROFESSION_LINES = {
    "practice": {
        "alchemy": ["{who} spent the season at the furnace, and mostly at "
                    "the scrubbing of it.",
                    "{who} spent the season grinding and weighing and "
                    "watching a pot that did not boil."],
        "forging": ["{who} spent the season at the forge, drawing out billets "
                    "that went back into the fire.",
                    "{who} spent the season on the bellows and the hammer and "
                    "very little else."],
        "healing": ["{who} spent the season in the infirmary, learning which "
                    "of the jars was which.",
                    "{who} spent the season setting bones that somebody else "
                    "had already set better."],
    },
    "rank": "{who} has come up to {word} at {craft} ({rank}/{max}).",
    "wall": "{who} has taken {craft} as far as copied notes go; past "
            "{word} it wants a teacher or a manual.",
    "spoiled": {
        "alchemy": "{who}'s batch came out of the furnace as slag and a "
                   "smell that stayed in the robes for a month.",
        "forging": "{who} drew the blade too thin and it went back into the "
                   "fire in two pieces.",
        "healing": "{who} spent the season in the infirmary and learned only "
                   "that they had learned nothing.",
    },
}
# THE MANUAL. §8's other door past rank 1, and the sect library is where it
# opens: a season in the hall (which already costs standing and silver) can
# turn up the written-down version of a craft the disciple has actually
# started. P7's technique manuals — including the flawed ones — are a
# different thing on the same shelf, and `_hall_technique` is their seam.
HALL_MANUAL = 0.30              # of a year in the hall, given a craft to
                                # look one up for
HALL_MANUAL_LINE = ("{who} came out of the {sect} library with a hand-copied "
                    "manual of {craft} under one arm.")

# ALCHEMY (§8). Pills are the fast lane and TOXICITY is the bill: every pill
# taken is a point of it, and above PILL_TOXICITY_FREE every further pill is
# a point of BURDEN — permanent, felt at every tribulation after, and exactly
# Part I §3's promise made mechanical. Six pills is a CAREER's worth of free
# shortcuts; the seventh starts eating the ceiling. Toxicity sheds one point
# a pill-free year, so a player who paces themselves never pays at all — and
# that pacing is the whole game the pill offers.
PILL_KINDS = {
    "qi": "qi in the dantian, where a season of sitting would have put it",
    "healing": "one level of a wound, closed on the spot",
    "clarity": "a clear head at the next tribulation, once",
}
PILL_YIELD = {1: (1, 1), 2: (1, 2), 3: (2, 3)}      # pills a season, by rank
PILL_QI = 18.0                  # what a qi pill puts in the dantian: two and
                                # a half years of sitting at the sect, and
                                # SIX OF THEM ARE A FULL DANTIAN — which is
                                # exactly the free toxicity budget above.
                                # That is the whole shape of the wall: one
                                # realm's qi can be bought outright and cost
                                # nothing, a second one bought in the same
                                # decade starts eating the ceiling, and a
                                # tribulation FAILED (qi back to 40, and the
                                # refill on top of a body already at the
                                # line) is what actually poisons a career.
PILL_CLARITY_PER_RANK = 0.03    # §8: +3% a rank, on ONE breakthrough attempt
PILL_TOXICITY_FREE = 6          # what a body carries before the pills cost
PILL_TOXICITY_BURDEN = 1        # ... and the burden every further one adds
PILL_DECAY = 1                  # toxicity shed in a pill-free year
PILL_VALUE = {"qi": 3, "healing": 4, "clarity": 5}  # silver, sold
PILL_LINES = {
    "brew": "{who} drew {n} {kind} pill{s} out of the furnace.",
    "qi": "{who} swallowed a qi pill and sat with it until it had gone "
          "where it was told (+qi).",
    "clarity": "{who} swallowed a clarity pill and kept the head it bought "
               "for the tribulation.",
    "none": "{who} has no {kind} pill to take.",
    "whole": "{who} is not hurt; the pill would be wasted on them.",
    "toxic": "{who} felt the last of the pills settle somewhere it will not "
             "come out of (+burden).",
}

# FORGING (§8). Gear at +1/+2 power — a real point, inside the §5 cap, which
# `World.player_power` and nothing else enforces. The rack is sellable: what
# a forge is FOR, in a world where silver buys the hall and the road.
FORGE_POWER = {1: 1, 2: 1, 3: 2}
FORGE_MASTERWORK = 0.25         # a rank-2 season that comes off the anvil a
                                # rank-3 piece anyway
FORGE_VALUE = {1: 5, 2: 5, 3: 12}       # silver a piece fetches, by grade
FORGE_NAMES = ["a straight sword", "a pair of bracers", "a hooked spear",
               "a riding sabre", "a set of scaled greaves", "a heavy glaive",
               "a short sword and its sheath", "a banded cuirass"]
FORGE_LINES = {
    "made": "{who} took {what} off the anvil — {grade}, worth +{power} in "
            "anybody's hands.",
    "sold": "{who} sold {what} to {buyer} for {silver} silver.",
    "market": "{who} sold {what} in the market for {silver} silver.",
    "empty": "{who} has nothing on the rack to sell.",
}
FORGE_GRADES = {1: "a serviceable piece", 2: "a serviceable piece",
                3: "a piece worth a name"}

# HEALING (§8). Your own wounds free — and other people's for the only coin
# this kernel has never minted. A patient carried in is a scene: they live or
# they do not, the ledger moves either way, and at rank 2+ somebody who WOULD
# HAVE DIED walks out owing you a LIFE-DEBT, which is the strongest rel in
# the social ledger and the one thing a grudge cannot be written over.
HEAL_SELF_RANK = 1              # from here your own wounds close in the season
HEAL_FULL_RANK = 2              # ... and from here they close entirely
HEAL_PATIENT = 0.50             # of a season: somebody is carried in
HEAL_DIRE = 0.35                # ... and would not have seen the month out
HEAL_SAVE_BASE = 0.45
HEAL_SAVE_PER_RANK = 0.20
HEAL_DIRE_PENALTY = 0.25
HEAL_SAVE_CLAMP = (0.05, 0.95)
HEAL_KARMA = 1                  # §7: deeds move the ledger, and this is one.
HEAL_KARMA_DIRE = 3             # Small on purpose: a season in the
                                # infirmary sees one or two through, and a
                                # career of them should reach "honoured" in
                                # a decade — not outrun an assassination
                                # (-30) in a single year.
HEAL_LOST_INSIGHT = 3           # adversity teaches, and losing one is that
HEAL_FEE = (1, 3)               # what a grateful house presses on you
HEAL_GRATITUDE = 1              # the rel a saved patient carries
LIFEDEBT_RANK = 2               # §8: the rank a life-debt starts at
LIFEDEBT_INTENSITY = 4          # ... and how heavy it sits
HEAL_POOL = 6                   # the faces a season's door brings up ...
HEAL_WEIGHT_SECT = 2.5          # ... their own sect first,
HEAL_WEIGHT_LAND = 1.5          # ... then their own country,
HEAL_WEIGHT_KNOWN = 2.0         # ... and anyone whose name they know
HEAL_TROUBLES = ["carried in off the road with a spear-hole in them",
                 "brought down from the practice ground with a crushed hand",
                 "found half-drowned under the mill at the ford",
                 "carried up the mountain burning with a fever",
                 "brought in from the wilds with a beast's teeth still in "
                 "the leg",
                 "dragged out of a collapsed gallery with the dust in both "
                 "lungs"]
HEAL_LINES = {
    "none": "{who} kept the infirmary all season and nobody worse than a "
            "sprain came through the door.",
    "saved": "{who} treated {patient}, {trouble}, and had them on their feet "
             "by the turn of the season (+karma).",
    "dire": "{who} kept {patient} alive — {trouble}, and by every reckoning "
            "already dead (+karma).",
    "debt": " {patient} owes {who} a life, and both of them know it.",
    "lost": "{who} worked over {patient} for a season, {trouble}, and lost "
            "them anyway (+insight).",
}

# THE PROFITEER (§3). The trade run's vice fork: grain into a starving land
# at famine prices pays DOUBLE and costs karma. It is offered only where it
# exists — a country with nothing left to eat — and it is the season layer's
# clearest statement of the kernel's oldest rule: VICE IS THE FAST LANE, and
# the ledger is what it is billed to.
PROFITEER_AT = 4.0              # a land poor enough for famine prices
PROFITEER_MULT = 2.0            # §3: pays double
PROFITEER_KARMA = -4
PROFITEER_PROSPERITY = -0.4     # what it takes out of the town it sold in
PROFITEER_LINES = {
    "ask": ("The {b} is starving, and grain there is worth what the last "
            "silver in a village can pay."),
    "took": "{who} ran {goods} into the starving {b} and sold it at famine "
            "prices (+resources, -karma).",
    "fair": "{who} ran {goods} into the starving {b} and sold it for what it "
            "had cost them.",
}

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
    ("body", "Train the body", PROFICIENCIES["body"][1]),
    ("weapon", "Train a weapon", PROFICIENCIES["weapon"][1]),
    ("theory", "Study theory", PROFICIENCIES["theory"][1]),
    ("hall", "Sect training hall",
     "the sect's forms, for standing and silver"),
    ("master", "Seek a master",
     "somebody above you, their trial, and what they teach"),
    ("alchemy", PROFESSIONS["alchemy"][0], PROFESSIONS["alchemy"][1]),
    ("forging", PROFESSIONS["forging"][0], PROFESSIONS["forging"][1]),
    ("healing", PROFESSIONS["healing"][0], PROFESSIONS["healing"][1]),
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
    ("front", "The demon front",
     "the deadliest season there is: cores, standing, and the Waste"),
]
PLAYER_ACTIVITY_KEYS = [k for k, _, _ in PLAYER_ACTIVITIES]

# --- THE AUTOPILOT (VII §12) -----------------------------------------------
# The played character, played by NOBODY: a bot that takes a legal activity
# at random every season and answers every question the kernel puts to it the
# same way. §12's target is that 32 seeded runs of this land inside Part
# III's funnel and die at ordinary rates — the player's edge is judgment, not
# existence, and if a random hand comes out ahead of the sim's own agents
# then the season menu is a cheat and not a game.
#
# It rolls on its OWN generator and never on `world.rng`, exactly like the
# human it stands in for (VII §1), so a bot run is a seeded world played by a
# seeded hand and reproduces exactly.
AUTOPILOT_SEED_OFFSET = 90001
AUTOPILOT_NAME = "Nobody"


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
    swallowed: bool = False                     # VII §7: the Waste holds it

    def settlements(self) -> list:
        """Every settlement at or beneath this place (sect seats excluded).

        A SWALLOWED settlement (VII §7) is not one of them: the Waste holds
        that ground, and it is not the country's any more — nobody is born
        there, nothing is grown there, and it is not counted in what the
        land is worth. What is left of it is the scar line in
        `state_of_the_lands`.
        """
        if self.kind in SETTLEMENT_KINDS:
            return [] if self.swallowed else [self]
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
    front: bool = False             # VII §7: a march-land begging for relief
                                    # from the Waste, not from its own court


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

    Techniques are P7; the field exists so that session has one place to put
    them, and so the shape of a played sheet stops changing underneath the
    save format.

    P6: `professions` is SEASONS OF PRACTICE like the rest of the tracks;
    `pills`, `gear`, `toxicity` and `clarity` are the only INVENTORY in the
    sim, and they exist on exactly one sheet — an NPC's `resources` is
    already the abstraction of all of it (VII §8).

    P5: `proficiencies` and `drills` are both SEASONS OF PRACTICE, not
    ranks — the one rank mechanic (`RANK_SHAPES`, `World.track_rank`) turns
    seasons into a rank wherever one is read, so a teaching multiplier can
    credit a season and a half without anything else in the sim knowing.
    `stances` stays what P2 made it, the authoritative stance RANK, because
    a rank can also be given (a master's gift, the training hall) and not
    only ground out.

    There is deliberately no hp here. VII §5: hp exists ONLY inside a fight,
    where `_bout` holds it on the stack; what a character carries between
    fights is a WOUND, and the body it leaves them is `World.max_hp`.
    """
    activity: str = "cultivate"     # the last chosen season activity
    seasons: int = 0                # seasons actually played
    wound: int = 0                  # P3: 0 none, 1 light, 2 serious
    proficiencies: dict = field(default_factory=dict)   # P5: Body/Weapon/
                                                        # Theory, in seasons
    drills: dict = field(default_factory=dict)          # P5: seasons drilled
                                                        # into each stance
    stances: dict = field(default_factory=dict)         # P2: stance ranks 0-3
    professions: dict = field(default_factory=dict)     # P6: alchemy/forging/
                                                        # healing, in seasons
    manuals: list = field(default_factory=list)         # P6: the crafts a
                                                        # book has unlocked
    techniques: list = field(default_factory=list)      # P7
    pills: dict = field(default_factory=dict)           # P6: kind -> how many
    brew: str = "qi"                                    # P6: what the
                                                        # furnace is set up
                                                        # for, until told
                                                        # otherwise
    gear: list = field(default_factory=list)            # P6: the rack, as
                                                        # {"what", "power",
                                                        #  "grade"} dicts
    toxicity: int = 0                                   # P6: pills the body
                                                        # is still carrying
    pill_year: int = -1                                 # ... and the last
                                                        # year one went down
    clarity: float = 0.0                                # P6: a clarity pill
                                                        # held for the next
                                                        # tribulation
    orders: dict = field(default_factory=dict)          # P3: standing orders
                                                        # (VII §6; seeded
                                                        # from ORDERS_DEFAULT)


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
    front_seasons: int = 0            # VII §7: seasons stood on the marches
    front_last: Optional[int] = None  # ... and the last year they stood one
    front_stands: int = 0             # incursions they were on the line for
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
        # VII §5: round combat. Fights stay one-roll off camera; a fight the
        # PLAYED character is in unfolds into exchanges. `narrate` is the
        # fight camera the front end hangs on the kernel (see `tell`), and
        # `_exchange_cache` memoises the race inversion that holds the
        # invariant, which is pure arithmetic and worth doing once.
        self.round_combat = True
        self.narrate: Optional[Callable] = None
        self._exchange_cache: dict = {}
        # VII §7: THE DEMON FRONT. One edge of the grid borders the Waste,
        # the lands along it are the marches, and `demon_threat` is the pot.
        # Demons are a field, not agents: this is the whole roster.
        self.demon_threat = DEMON_THREAT_START
        self.waste_edge = ""
        self.march_lands: list = []                # the 2-3 lands on that edge
        self.swallowed: list = []                  # (year, Place) — permanent
        self._front_relief = 0.0                   # relief spent this year
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

        self._build_marches()
        for land in self.lands.values():
            self._build_land_tree(land)

    def _build_marches(self):
        """VII §7: which outer edge of the grid the DEMON WASTE lies beyond.

        A seeded roll, once, at worldgen. The three lands along that edge are
        the marches — except that one of its corners is often sheltered, and
        then there are two. Nothing else about the Waste is ever generated:
        it holds no court, takes no tribute and signs nothing.
        """
        r = self.rng
        self.waste_edge = r.choice(DEMON_WASTE_EDGES)
        if self.waste_edge == "north":
            slots = [(0, 0), (0, 1), (0, 2)]
        elif self.waste_edge == "south":
            slots = [(2, 0), (2, 1), (2, 2)]
        elif self.waste_edge == "west":
            slots = [(0, 0), (1, 0), (2, 0)]
        else:
            slots = [(0, 2), (1, 2), (2, 2)]
        lands = [self.grid[row][col] for row, col in slots]
        if r.random() < MARCH_SHELTERED_CHANCE:
            lands.pop(r.choice([0, 2]))     # a sheltered corner of that edge
        self.march_lands = lands

    def _build_land_tree(self, land: Place):
        r = self.rng
        land.baseline = r.uniform(*PROSPERITY_BASELINE)
        if self.is_march(land):
            land.baseline = min(10.0, land.baseline + MARCH_BASELINE)
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
        return [p for p in self.places.values()
                if p.kind in SETTLEMENT_KINDS and not p.swallowed]

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
        if not homes:
            return land     # a land the Waste has taken whole (VII §7)
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
        if holder is target:
            return      # nobody keeps a score against themselves (a rare
                        # self-grudge used to send them to duel themselves)
        held = holder.rels.get(target.aid)
        if held is not None and held.kind == "life-debt":
            # VII §8: the strongest coin in the social ledger. You do not
            # open a score against the one who kept you alive, and a bad day
            # does not turn the debt into one.
            return
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
        self._front_relief = 0.0        # §7: what the pot will hear this year
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
            # §7: and the marches take whoever the marches take. The front
            # burns through NPC lives on the same table the player fights on.
            if self._take_front(a):
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
                self._duel(a, t, context="a long-nursed grudge",
                           edge="allout")
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
                self._duel(a, r.choice(peers), edge="allout",
                           context="a quarrel picked for its own sake")
                return
        if a.has_trait("Proud") and r.random() < 0.25 * share:
            peers = [o for o in self.cultivators() if o.sect == a.sect
                     and o.realm == a.realm and o.aid != a.aid]
            if peers:
                self._duel(a, r.choice(peers), edge="duelling",
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
        power = self.fight_power(a)     # P5: a trained weapon is worth its
                                        # half-points here too
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
        # §3: THE PROFITEER FORK, and VICE IS STILL THE FAST LANE. Offered
        # only where it exists — a country with nothing left to eat — and
        # never to an NPC, whose `_vice_spoils` above is already the whole
        # of what their appetite is worth on this road. Nothing here rolls
        # unless the player says the word.
        asked = famine = False
        if (self.playing and a is self.pc and other is not home
                and other.wealth() < PROFITEER_AT):
            asked = True
            famine = self.ask_player(
                "profiteer", PROFITEER_LINES["ask"].format(b=other.name),
                ["fair", "famine"], "fair") == "famine"
        if famine:
            take = int(round(take * PROFITEER_MULT))
            a.karma += PROFITEER_KARMA
            self._record_deed(a, "cruelty")     # §2: the record mutates you
            where = self._pick_home(other)
            where.prosperity = max(0.0, where.prosperity
                                   + PROFITEER_PROSPERITY)
        a.resources += take
        if r.random() < TRADE_STANDING_CHANCE * share:
            a.standing += 1
        if asked:
            self.log(PROFITEER_LINES["took" if famine else "fair"]
                     .format(**fields), [a],
                     place=where if famine else None)
            return
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

    # -- the demon front (VII §7) -------------------------------------------
    #
    # DEMONS ARE A FIELD, NOT AGENTS. Everything below fights a NUMBER: the
    # threat is the whole host, the scene tables are the whole roster, and
    # no part of it ever reaches `_bout`, which wants two agents and a
    # stance each. What the front is FOR is that a permanent war gives the
    # world a source of deathly fighting that never runs dry — for the
    # player and for the NPCs alike.

    def is_march(self, place: Optional[Place]) -> bool:
        """Does this place lie in one of the march-lands?"""
        if place is None or not self.march_lands:
            return False
        land = place if place.kind == "land" else place.land
        return any(land is m for m in self.march_lands)

    def threat_word(self) -> str:
        """The pot, in words. The reader never sees the number."""
        for ceiling, word in DEMON_THREAT_WORDS:
            if self.demon_threat < ceiling:
                return word
        return DEMON_THREAT_WORDS[-1][1]

    def waste_word(self) -> str:
        return WASTE_EDGE_WORDS.get(self.waste_edge, self.waste_edge)

    def _front_land(self, a: Optional[Agent] = None) -> Optional[Place]:
        """Which stretch of the marches somebody goes to: their own country
        if they were born on it, otherwise wherever the sects send them."""
        if not self.march_lands:
            return None
        if a is not None and a.home is not None and self.is_march(a.home):
            return a.home.land
        return self.rng.choice(self.march_lands)

    def front_volunteer_weight(self, a: Agent) -> float:
        """§7: how badly a cultivator wants a season on the line.

        The war-volunteer machinery's shape, with the front's own skew: the
        Righteous who think somebody has to, the Bloodthirsty who want the
        fighting, and march-land natives — whose own country it is —
        doubled.
        """
        w = sum(m for t, m in FRONT_VOLUNTEER_TRAITS.items() if a.has_trait(t))
        if self.is_march(a.home):
            w = (w + FRONT_VOLUNTEER_NATIVE) * FRONT_VOLUNTEER_NATIVE_MULT
        return w

    def _take_front(self, a: Agent, forced=False, share=1.0) -> bool:
        """Does this cultivator give the year to the marches?

        Rolls nothing at all for anybody the front has no hold on, which is
        why the batch stream only moves for the ones who would go.
        """
        if not self.march_lands or a.realm < FRONT_MIN_REALM \
                or a.age < FRONT_MIN_AGE:
            return False
        if not forced:
            eager = min(1.0, self.front_volunteer_weight(a)
                        / FRONT_VOLUNTEER_FULL)
            if eager <= 0:
                return False
            chance = eager * (FRONT_CHANCE
                              + FRONT_CHANCE_PER_THREAT * self.demon_threat)
            if a.front_last is not None and self.year - a.front_last <= 1:
                chance *= FRONT_RETURN
            if self.rng.random() >= chance:
                return False
        self._act_front(a, share=share)
        return True

    def _front_served(self, a: Agent, share: float):
        """§7: what standing on the line does to the pot.

        -0.1 a cultivator-season, and DEMON_RELIEF_CAP is all of it a single
        year can hold: the line is long, and the tenth sword on it buys the
        Waste's attention, not its absence.
        """
        seasons = max(1, int(round(share * len(SEASONS))))
        a.front_seasons += seasons
        a.front_last = self.year
        room = max(0.0, DEMON_RELIEF_CAP - self._front_relief)
        relief = min(room, seasons * DEMON_THREAT_PER_SEASON)
        self._front_relief += relief
        self.demon_threat = max(0.0, self.demon_threat - relief)

    def _front_drift(self):
        """CLOSE: the pot boils. §7's drift, read per season (see the tables)
        and paid once a year, after everything that stirred it."""
        if not self.march_lands:
            return
        self.demon_threat = min(
            DEMON_THREAT_MAX,
            self.demon_threat + DEMON_THREAT_DRIFT * len(SEASONS))

    def _take_wound(self, a: Agent, level: int):
        """A wound taken OUTSIDE a fight: off the line (P4 §7) or out of a
        furnace that went up (P6 §8). hp lives only inside a bout, and there
        is no bout here — but a body carried off is carried off the same
        way, and `_wound_resisted` is still the one door it comes through."""
        if a.play is None or not a.alive:
            return
        level = self._wound_resisted(a, level)
        if level <= a.play.wound:
            return
        a.play.wound = level
        self.log(WOUND_LINES[level].format(who=a.display()), [a])

    def _front_epithet(self, a: Agent, pool=FRONT_EPITHETS) -> str:
        free = [e for e in pool if e not in a.epithets]
        if not free or len(a.epithets) >= 3:
            return ""
        ep = self.rng.choice(free)
        a.epithets.append(ep)
        return f" [epithet: {ep}]"

    def _act_front(self, a: Agent, share=1.0):
        """A season on the marches: the deadliest lane there is (§7).

        A contest against the pot, on the expedition's kind of roll — there
        is no one to duel. Roughly twice as lethal as the harsh road at
        either resolution, because a season pays a quarter of the year's
        risk exactly as it pays a quarter of the year's gains.
        """
        r = self.rng
        land = self._front_land(a)
        if land is None:
            return
        where = self._pick_home(land)
        edge = self.waste_word()
        foe = (r.uniform(*FRONT_POWER)
               + FRONT_POWER_PER_REALM * (a.realm - 1)
               + FRONT_POWER_PER_THREAT * self.demon_threat)
        # P5: the front is a contest against a NUMBER (P4: it never enters
        # `_bout`), but it is still a season of fighting with your own hands,
        # so it reads the same clipped bonus a duel does. The §5 cap cannot
        # leak here: `player_power` is where it is enforced, and an NPC's is
        # zero without a die being rolled for it.
        power = self.fight_power(a)
        odds = max(FRONT_ODDS[0], min(FRONT_ODDS[1], power / (power + foe)))
        self._front_served(a, share)
        fields = dict(who=a.display(), land=land.name, where=where.name,
                      edge=edge)

        def line(key) -> str:
            return r.choice(FRONT_LINES[key]).format(**fields)

        if r.random() < odds:
            a.resources += self._share_int(r.randint(*FRONT_SPOILS)
                                           + self._vice_spoils(a), share)
            a.insight += FRONT_INSIGHT * share
            a.karma += self._share_int(FRONT_KARMA, share)
            if r.random() < FRONT_STANDING_CHANCE * share:
                a.standing += 1
            mark = ""
            if a.front_seasons >= FRONT_VETERAN_SEASONS \
                    and FRONT_VETERAN_EPITHET not in a.epithets:
                mark = self._front_epithet(a, (FRONT_VETERAN_EPITHET,))
            text = line("held") + mark
            if mark:
                self.log(text, [a], place=where)
            else:
                a.history.append((self.year, text))
            return
        if not self._fires(share):
            a.history.append((self.year, line("quiet")))
            return
        roll = r.random()
        if roll < FRONT_DEATH:
            # §7 prices this the way it prices any death in front of other
            # people: it buys the dead nothing but the obituary.
            self._fell_defending(a, FRONT_DEFENDED.format(edge=edge))
            self.kill(a, line("death"))
            return
        if roll < FRONT_DEATH + FRONT_MAUL:
            a.insight += FRONT_MAUL_INSIGHT
            a.burden += 1
            a.fortune = max(-FORTUNE_CAP, a.fortune - 1)
            text = line("maul") + self._front_epithet(a)
            self.log(text, [a], dramatic=True, place=where)
            self._take_wound(a, 2)      # ... and then what walks off the line
            self._mutate(a, "near_death")
            return
        a.insight += FRONT_DRIVEN_INSIGHT * share
        self._take_wound(a, 1)
        a.history.append((self.year, line("driven")))

    # -- the incursion (§7): the year the Waste comes over ------------------

    def _plan_incursion(self) -> Optional[dict]:
        """Rolled with the rest of the year, so that a timeskip can stop on
        its eve for the people it is coming for."""
        r = self.rng
        if not self.march_lands or self.demon_threat < INCURSION_AT:
            return None
        if r.random() >= INCURSION_CHANCE:
            return None
        land = r.choice(self.march_lands)
        pool, weights = [], []
        for a in self.cultivators():
            if a.realm < FRONT_MIN_REALM or a.age < FRONT_MIN_AGE:
                continue
            w = INCURSION_BASE_WEIGHT + self.front_volunteer_weight(a)
            if a.home is not None and a.home.land is land:
                w += INCURSION_NATIVE_WEIGHT
            if a.front_last is not None \
                    and self.year - a.front_last <= FRONT_VETERAN_YEARS:
                w += INCURSION_VETERAN_WEIGHT
            pool.append(a)
            weights.append(w)
        drawn, seen = [], set()
        if pool:
            k = min(len(pool), r.randint(*INCURSION_DEFENDERS))
            while len(drawn) < k:
                a = r.choices(pool, weights)[0]
                if a.aid not in seen:
                    seen.add(a.aid)
                    drawn.append(a)
        return {"land": land.pid, "defenders": [a.aid for a in drawn]}

    def _run_incursion(self, land: Place, defenders: list):
        """One year of it, resolved as one contest against the pot.

        The marches pay first and in full — prosperity, levies, villages —
        and then the line either holds or does not. Both endings are filed
        with `_remember`; only the second one is permanent.
        """
        r = self.rng
        edge = self.waste_word()
        polities = [p for p in self.polities.values()
                    if p.land is land and p.kind != "sect"]
        armies = sum(p.army for p in polities)
        domain = polities[0].domain if polities else land.name
        dead = r.randint(*INCURSION_DEAD)
        seat = self._capital(land)
        self.log(r.choice(INCURSION_OPEN).format(
            edge=edge, land=land.name, domain=domain, dead=f"{dead:,}"),
            defenders, world_event=True, place=seat)
        for p in land.settlements():
            p.prosperity = max(0.0, p.prosperity + INCURSION_PROSPERITY)
        for other in self.march_lands:
            if other is land:
                continue
            for p in other.settlements():
                p.prosperity = max(0.0, p.prosperity
                                   + INCURSION_PROSPERITY_OTHER)
        for p in polities:
            p.unrest = min(UNREST_MAX, p.unrest + INCURSION_UNREST)

        # VII §2: the kernel does not decide for a played character whether
        # they stand in it.
        standing = []
        for a in defenders:
            if not a.alive or a.is_ruler():
                continue
            if self.playing and a is self.pc:
                if self.ask_player(
                        "incursion",
                        f"The Waste is over the {edge} marches into "
                        f"{land.name}; the sects are calling out everyone "
                        f"who can stand on a wall.",
                        ["ride", "stay"], "ride") != "ride":
                    self.log(f"{a.display()} was called to the {edge} line "
                             f"when the Waste came over, and did not go.",
                             [a], place=seat)
                    continue
            standing.append(a)
        for a in standing:
            a.front_stands += 1
            self._front_served(a, 1.0)

        score = (INCURSION_WALL_BASE
                 + sum(INCURSION_CULTIVATOR_SCORE * a.power()
                       for a in standing)
                 + INCURSION_ARMY_SCORE * armies)
        score *= r.uniform(1.0 - INCURSION_NOISE, 1.0 + INCURSION_NOISE)
        wall = self.demon_threat * INCURSION_THREAT_SCORE
        odds = max(INCURSION_ODDS[0],
                   min(INCURSION_ODDS[1], score / (score + wall)))
        held = r.random() < odds
        killed = [a for a in standing
                  if r.random() < (INCURSION_DEATH if held
                                   else INCURSION_DEATH_LOST)]
        for a in killed:
            self._fell_defending(a, FRONT_DEFENDED.format(edge=edge))
            self.kill(a, f"killed on the {edge} line when the Waste came "
                         f"over into {land.name}")
        survivors = [a for a in standing if a.alive]
        for a in survivors:
            a.insight += INCURSION_INSIGHT + len(killed)
            a.standing += INCURSION_STANDING
            a.karma += INCURSION_KARMA
            self._record_deed(a, "mercy")

        if held:
            where = self._pick_home(land)
            self.demon_threat = r.uniform(*INCURSION_RESET)
            self.log(r.choice(INCURSION_HELD).format(
                land=land.name, where=where.name, edge=edge),
                survivors, world_event=True, place=where)
            self._remember(land, f"the Waste came over the {edge} marches "
                                 f"and was thrown back at {where.name}")
        else:
            where = self._swallow(land)
            self.demon_threat = min(DEMON_THREAT_MAX,
                                    self.demon_threat + INCURSION_LOST_THREAT)
            if where is None:
                # Everything on that stretch is already gone; there was
                # nothing left out there for the host to take.
                self.log(f"The {edge} line broke again into {land.name}, and "
                         f"there was nothing left on that stretch of it for "
                         f"the Waste to take.", survivors, world_event=True,
                         place=self._capital(land))
                self._remember(land, f"the {edge} line broke a second time "
                                     f"over ground already given up")
            else:
                self.log(r.choice(INCURSION_LOST).format(
                    land=land.name, where=where.name, edge=edge),
                    survivors, world_event=True, dramatic=True, place=where)
                self._remember(land, f"{where.name} was swallowed by the "
                                     f"Waste, and the {edge} front came a "
                                     f"mile inland")
        if killed:
            names = ", ".join(k.display() for k in killed)
            self.log(f"The {edge} line cost {len(killed)} of the sects' own: "
                     f"{names}.", survivors, world_event=True)

    def _swallow(self, land: Place) -> Optional[Place]:
        """A settlement the Waste keeps. Floored, and left floored: the
        baseline goes with it and it is off the map, so nothing ever drifts
        back. A capital is never taken — a country whose last town went
        under would be a country the sim can no longer talk about."""
        seats = {p.seat.pid for p in self.polities.values()
                 if p.seat is not None}
        options = [p for p in land.settlements()
                   if p.kind != "city" and p.pid not in seats]
        if not options:
            return None
        place = min(options, key=lambda p: p.prosperity)
        place.prosperity = 0.0
        place.baseline = 0.0
        place.swallowed = True
        self.swallowed.append((self.year, place))
        return place

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

    def _maim(self, winner: Agent, loser: Agent, where: str,
              meant=True) -> bool:
        """A victor who does not stop at winning — or a fight that did not
        stop when it should have (VII §4: the edge's own maim chance).

        The victim walks out of it with an epithet, a heavier burden and the
        insight that adversity pays — which is how the sim ends up full of
        walking evidence of somebody's character. Only a maiming that was
        MEANT is filed as a cruelty; an all-out fight that went too far is a
        thing that happened, not a thing somebody chose.
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
        if meant:
            self._record_deed(winner, "cruelty")   # VII §2: the ledger
        self.log(MAIM_LINES["meant" if meant else "accident"].format(
            winner=winner.display(), loser=loser.name, where=where, ep=ep),
            [winner, loser], dramatic=True)
        return True

    # -- stances: edge x manner (VII §4) ------------------------------------

    def stance_rank(self, a: Agent, key: str) -> int:
        """Rank 0-3 in one edge or one manner.

        The EARNING of ranks — use, masters, the training hall — is P5; this
        is the seam it writes through. A played character carries real ranks
        on `Agent.play`. An NPC is trained UP TO the edge their own character
        takes them to — a killer knows how to duel, a duellist has never
        learned to kill — and in the one manner their nature fights in; a
        stance the situation forces on them is untrained, which is what
        makes a forced edge expensive.
        """
        if a.play is not None:
            return max(0, min(STANCE_RANK_MAX, a.play.stances.get(key, 0)))
        edge, manner = self._native_stance(a)
        if key in STANCE_EDGES:
            return (STANCE_NPC_RANK
                    if EDGE_ORDER.index(key) <= EDGE_ORDER.index(edge) else 0)
        return STANCE_NPC_RANK if key == manner else 0

    def _native_stance(self, a: Agent) -> tuple:
        """The edge and manner this character's own nature fights in."""
        manner = None
        for trait, name in STANCE_TRAIT_MANNER:
            if a.has_trait(trait):
                manner = name
                break
        edge = "murderous" if a.has_trait("Bloodthirsty") else "duelling"
        return (edge, manner)

    def _pick_stance(self, a: Agent, context_edge: str) -> tuple:
        """(edge, manner) for one fighter (VII §4).

        The context sets the edge the fight was called at, and a fighter can
        only carry it FURTHER: a sect feud is not answered with a sparring
        bout. Traits pick the manner, and the manner is the one thing that
        can take the killing back out of a fight — a Righteous fighter's
        pledge either holds under a drawn blade or it does not.
        """
        r = self.rng
        base = context_edge if context_edge in STANCE_EDGES else "duelling"
        _, manner = self._native_stance(a)
        # VII §6: a played character's standing orders are exactly what an
        # NPC's nature is — read in the same place, for the same reason. The
        # ordered edge can only carry the fight FURTHER than the context
        # called it: nobody spars their way out of a sect feud.
        if a.play is not None:
            orders = self.orders_of(a)
            want = orders["edge"]
            if want in STANCE_EDGES:
                base = max((base, want), key=EDGE_ORDER.index)
            told = orders["manner"]
            if told in STANCE_MANNERS:
                manner = told
            elif told == "none":
                manner = None
        if base != "murderous":
            plain = not STANCE_EDGES[base]["lethal"]
            for trait, chance in STANCE_MURDEROUS_TRAITS.items():
                if not a.has_trait(trait):
                    continue
                if plain:
                    chance *= STANCE_MURDEROUS_PLAIN
                if r.random() < chance:
                    base = "murderous"
                    break
        if (manner == "merciful" and STANCE_EDGES[base]["lethal"]
                and r.random() >= STANCE_MERCIFUL_HOLDS):
            manner = None       # the pledge did not survive the drawn blade
        return (base, manner)

    def _stance_weight(self, a: Agent, mine: tuple, theirs: tuple,
                       foe: Optional[Agent] = None,
                       phase: Optional[int] = None) -> float:
        """What a stance is worth in the one exchange the kernel rolls.

        A bonus is HALVED and a malus DOUBLED at rank 0 (VII §4), which is
        what makes an edge somebody else chose expensive. The whole spread
        is a few percent of one roll: by VII §5 nothing here may bridge a
        realm, and a realm gap never reaches this function at all.

        `phase` is the round number, and only the round model passes one:
        patience is a SCHEDULE (give the opening away, take it back later)
        whose flat `weight` is what the schedule comes to over a whole
        fight, which is the number the one roll is entitled to read.
        """
        edge, manner = mine
        w = STANCE_EDGES[edge]["weight"]
        w *= self._rank_scale(w, self.stance_rank(a, edge))
        if manner:
            spec = STANCE_MANNERS[manner]
            m = spec["weight"]
            if manner == "patience" and phase is not None:
                m = spec["early" if phase <= ROUND_PATIENCE_ROUNDS else "late"]
            if manner == "harmonious":
                if theirs[1] == "rage":
                    m += spec["vs_rage"]
                if self._has_vice(foe):
                    m += spec["vs_vice"]
            m *= self._rank_scale(m, self.stance_rank(a, manner))
            w += m
        # Rage: what it hands out it also hands over.
        if theirs[1] == "rage":
            w += STANCE_MANNERS["rage"]["taken"]
        return w

    @staticmethod
    def _rank_scale(value: float, rank: int) -> float:
        bonus, malus = STANCE_PROFICIENCY.get(rank, (1.0, 1.0))
        return bonus if value >= 0 else malus

    @staticmethod
    def _has_vice(a: Optional[Agent]) -> bool:
        return a is not None and any(a.has_trait(t) for t in VICE_TRAITS)

    def player_power_terms(self, a: Agent) -> list:
        """Every point the player layer adds to a fighter, itemised.

        P5 filled in the first line of it: Weapon proficiency, half a point
        a rank, two and a half at the top of the track. P6 adds forged gear,
        +1 or +2. P7's techniques append here and NOWHERE ELSE — one list
        in, one clamp out.
        """
        if a is None or a.play is None:
            return []
        terms = []
        weapon = self.proficiency_rank(a, "weapon")
        if weapon:
            terms.append(("weapon", PROFICIENCY_WEAPON_POWER * weapon))
        # P6: what came off the anvil — the best piece on the rack, never a
        # stack of them. P7: ("technique", elemental arts +1).
        gear = self.gear_power(a)
        if gear:
            terms.append(("gear", gear))
        return terms

    def player_power(self, a: Agent) -> float:
        """What the PLAYER LAYER adds to a fighter, and THE ONE PLACE the
        VII §5 cap is enforced.

        Nothing this layer ever builds — proficiencies, gear, techniques,
        all of them stacked together on the same character — may add up to
        more than PLAYER_POWER_CAP, which is less than half a realm's ten
        points. That is not a guideline the individual tables are asked to
        respect; it is this `min`. Every table above is free to be generous
        because this line is not.
        """
        if a is None or a.play is None:
            return 0.0
        return min(PLAYER_POWER_CAP,
                   sum(v for _, v in self.player_power_terms(a)))

    def fight_power(self, a: Agent) -> float:
        """What a character is worth in a contest of arms they fight WITH
        THEIR OWN HANDS: a duel, a bout, a season in the wilds, a season on
        the line. Identical to `Agent.power` for everyone who is not played.

        Deliberately NOT read by the group contests — a war, an incursion,
        an expedition. Those are scored on realms and numbers because they
        are army arithmetic, and one player's sword-work is not what carries
        a wall. It is also why the front's own contest (`_act_front`) reads
        this and the incursion's does not.
        """
        return a.power() + self.player_power(a)

    def _stance_power(self, a: Agent, mine: tuple, theirs: tuple,
                      foe: Optional[Agent] = None,
                      phase: Optional[int] = None) -> float:
        """What a fighter is worth in this fight, in this stance."""
        return max(1.0, self.fight_power(a)
                   * (1.0 + self._stance_weight(a, mine, theirs, foe, phase)))

    def duel_odds(self, att: Agent, dfn: Agent, sa: tuple, sb: tuple,
                  phase: Optional[int] = None) -> float:
        """THE ONE-ROLL WIN PROBABILITY, and the only one in the sim.

        VII §5's invariant lives here: the round model's win rate must sit
        within three percentage points of this number, so that the funnel
        cannot tell which resolution ran. Stances tilt the exchange by a few
        percent; realms were settled before it was called.
        """
        pa = self._stance_power(att, sa, sb, dfn, phase)
        pb = self._stance_power(dfn, sb, sa, att, phase)
        return pa / (pa + pb)

    @staticmethod
    def _stance_phrase(st: tuple) -> str:
        """What a stance looks like from outside, with nobody's name on it."""
        edge, manner = st
        return MANNER_PHRASE[manner] if manner else EDGE_PHRASE[edge]

    def _stance_words(self, a: Agent, st: tuple) -> str:
        """How this one fought, in words — the vocabulary VII §4 asks the
        chronicle to speak."""
        return f"{a.display()} {self._stance_phrase(st)}"

    def _stance_tail(self, att: Agent, sa: tuple,
                     dfn: Agent, sb: tuple) -> str:
        return (f" — {self._stance_words(att, sa)}, "
                f"{self._stance_words(dfn, sb)}")

    def _execute_chance(self, winner: Agent, st: tuple,
                        theirs: tuple) -> float:
        """Whether a beaten foe who yields is finished (VII §4).

        The choice belongs to the VICTOR, and so does the number: it is
        their own edge that says how far they came to go, not the edge the
        fight reached. What the loser brought matters in exactly one way —
        a victor who has just been fought FOR THEIR LIFE finishes it far
        more readily than one who was only being fought.
        """
        if st[1] == "merciful":
            return 0.0
        chance = STANCE_EDGES[st[0]]["execute"]
        if st[0] != "murderous" and theirs[0] == "murderous":
            chance += STANCE_EXECUTE_ATTACKED
        for trait, step in STANCE_EXECUTE_TRAITS.items():
            if winner.has_trait(trait):
                chance += step
        return max(0.0, min(1.0, chance))

    @staticmethod
    def _killer_clause(came: list) -> str:
        """The tail that names who brought a killing edge to a fight."""
        if not came:
            return ""
        if len(came) > 1:
            return "; both of them had come to kill"
        return f"; {came[0].display()} had come to kill, not to win"

    def _stance_seen(self, a: Agent, st: tuple):
        """VII §4: a killing edge costs standing when it is witnessed.
        People remember who came to kill."""
        if st[0] != "murderous" or not a.alive:
            return
        if self.rng.random() < STANCE_SEEN:
            a.standing = max(0, a.standing - STANCE_SEEN_STANDING)

    # -- round combat: the fight the played character is IN (VII §5) --------

    def _rounds_wanted(self, att: Agent, dfn: Agent) -> bool:
        """Does this fight unfold, or is it settled with the one roll?

        Only a fight the PLAYED character is in. Everything else in the world
        — every feud, every score come due, every quarrel picked in a
        courtyard two lands away — is resolved exactly as it was, which is
        what keeps the funnel and the tuning targets where they were.
        """
        return self.round_combat and (att.play is not None
                                      or dfn.play is not None)

    def max_hp(self, a: Agent) -> float:
        """The body a fighter brings to a bout.

        A wound takes points off it and P5's Body proficiency puts them back
        on — at rank 5, half of what a light wound costs, and no more. That
        is a bonus the one roll never hears about, the mirror image of the
        wound it also never hears about (VII §5): the reference geometry is
        two WHOLE bodies, and the fight is run on the real ones.
        """
        if a.play is None:
            return ROUND_HP
        trained = PROFICIENCY_BODY_HP * self.proficiency_rank(a, "body")
        return max(ROUND_HP * 0.4,
                   ROUND_HP + trained - WOUND_MAX_HP.get(a.play.wound, 0.0))

    def orders_of(self, a: Agent) -> dict:
        """A played character's standing orders (VII §6), defaults filled."""
        out = dict(ORDERS_DEFAULT)
        if a.play is not None:
            out.update({k: v for k, v in a.play.orders.items() if k in out})
        return out

    def set_order(self, a: Agent, key: str, value: str) -> str:
        """Change one standing order. Returns what to tell the player."""
        if a is None or a.play is None:
            return "There is nobody to give orders to."
        key = key.strip().lower()
        if key not in ORDERS_DEFAULT:
            return f"No such order: {key}"
        value = value.strip().lower()
        if key == "yield":
            try:
                num = float(value.rstrip("%"))
            except ValueError:
                return ("The yield line is a fraction (0.25) or a percent "
                        "(25%).")
            if num > 1.0:
                num /= 100.0
            num = max(ORDERS_YIELD_CLAMP[0], min(ORDERS_YIELD_CLAMP[1], num))
            a.play.orders["yield"] = num
            return f"Standing order: yield at {num * 100:.0f}% of your own."
        choices = ORDERS_CHOICES[key]
        if not value:
            return f"{key} is one of: {', '.join(choices)}"
        for opt in choices:
            if opt.startswith(value):
                a.play.orders[key] = opt
                return f"Standing order: {key} = {opt}."
        return f"{key} is one of: {', '.join(choices)}"

    def orders_card(self, a: Agent) -> str:
        """VII §6: the small card of defaults a fight is fought off."""
        if a is None or a.play is None:
            return "Nothing to show."
        orders = self.orders_of(a)
        lines = ["Standing orders (`orders KEY VALUE` to change one):"]
        for key in ("edge", "manner", "yield", "execute", "escape", "pauses"):
            value = orders[key]
            if key == "yield":
                value = f"{float(value) * 100:.0f}%"
            lines.append(f"  {key:<8} {str(value):<10} {ORDERS_HELP[key]}")
        lines.append("  (a fight that never has to ask you anything prints "
                     "as one line, like anybody else's)")
        return "\n".join(lines)

    def _yield_line(self, a: Agent) -> float:
        """The hp fraction a fighter stops at.

        Orders for a played character; nature for everyone else, and the
        natures that cannot stop are the ones that get people killed.
        """
        if a.play is not None:
            try:
                want = float(self.orders_of(a)["yield"])
            except (TypeError, ValueError):
                want = ORDERS_DEFAULT["yield"]
            return max(ORDERS_YIELD_CLAMP[0], min(ORDERS_YIELD_CLAMP[1], want))
        line = NPC_YIELD_BASE
        for trait, step in NPC_YIELD_TRAITS.items():
            if a.has_trait(trait):
                line += step
        return max(NPC_YIELD_CLAMP[0], min(NPC_YIELD_CLAMP[1], line))

    @staticmethod
    def _race_odds(q: float, na: int, nb: int) -> float:
        """The chance of landing `na` exchanges before the other lands `nb`.

        A race to na and nb is decided inside na+nb-1 exchanges however it
        actually plays out, so it is a binomial tail and nothing more.
        """
        n = na + nb - 1
        return sum(math.comb(n, k) * (q ** k) * ((1.0 - q) ** (n - k))
                   for k in range(na, n + 1))

    def _exchange_chance(self, p: float, na: int, nb: int) -> float:
        """THE INVARIANT, solved instead of tuned (VII §5).

        Given the one roll's win probability and the geometry of the race,
        this is the per-exchange chance whose race comes out at exactly that
        number. Everything the rounds add moves na and nb; the inversion
        gives it all back.
        """
        key = (round(p, 4), na, nb)
        hit = self._exchange_cache.get(key)
        if hit is not None:
            return hit
        lo, hi = 0.0005, 0.9995
        for _ in range(32):
            mid = (lo + hi) / 2.0
            if self._race_odds(mid, na, nb) < p:
                lo = mid
            else:
                hi = mid
        out = (lo + hi) / 2.0
        self._exchange_cache[key] = out
        return out

    def _swing_of(self, a: Agent, foe: Agent, mine: tuple, theirs: tuple,
                  roll: float) -> float:
        """What one landed exchange takes off the other one.

        VII §5's 12-20%, tilted by the power ratio — the stronger fighter's
        blows tell — and by what each of them came to do: the harsh edges
        hit harder, and rage hands out and takes the same extra.
        """
        pa = self._stance_power(a, mine, theirs, foe)
        pb = self._stance_power(foe, theirs, mine, a)
        tilt = (pa / pb) ** ROUND_SWING_TILT
        tilt = max(ROUND_SWING_CLAMP[0], min(ROUND_SWING_CLAMP[1], tilt))
        swing = roll * tilt * STANCE_EDGES[mine[0]]["dmg"]
        if mine[1] == "rage":
            swing *= 1.0 + STANCE_MANNERS["rage"]["weight"]
        if theirs[1] == "rage":
            swing *= 1.0 + STANCE_MANNERS["rage"]["taken"]
        return max(1.0, swing)

    def _movement_rank(self, a: Agent) -> int:
        """P7's Movement school, read early. Techniques do not exist yet, so
        this is zero for everybody and the escape table already has its
        term."""
        if a.play is None:
            return 0
        return sum(1 for t in a.play.techniques if t == "movement")

    def _escape_chance(self, a: Agent, foe: Agent) -> float:
        """Breaking off a killing fight (VII §5)."""
        chance = ESCAPE_BASE
        if a.has_trait("Cautious"):
            chance += ESCAPE_CAUTIOUS
        chance += ESCAPE_MOVEMENT * self._movement_rank(a)
        gap = foe.realm - a.realm
        if gap > 0:
            chance -= ESCAPE_PER_REALM * gap
        return max(ESCAPE_CLAMP[0], min(ESCAPE_CLAMP[1], chance))

    def _pause_switch(self, a: Agent, which: str, mine: tuple) -> tuple:
        """The second half of a pause: which edge, or which manner."""
        if which == "edge":
            pick = self.ask_player(
                "edge", "Fight it at what edge?", list(EDGE_ORDER), mine[0])
            return ("stance", (pick, mine[1]))
        opts = ["none"] + list(STANCE_MANNERS)
        pick = self.ask_player("manner", "Fight it in what manner?", opts,
                               mine[1] or "none")
        return ("stance", (mine[0], None if pick == "none" else pick))

    def _pause_own(self, a: Agent, foe: Agent, mine: tuple, theirs: tuple,
                   own: float, other: float, lethal: bool) -> tuple:
        """A threshold crossed on your own body (VII §5).

        ONE prompt per crossing and then the fight flows again — this is the
        autocombat contract, not a round-by-round menu. A played character
        answers off their standing orders unless the orders say to ask; an
        NPC answers with its nature, which is the same machinery read the
        other way round.
        """
        if a.play is not None:
            orders = self.orders_of(a)
            if lethal and orders["escape"] == "always":
                return ("escape", None)
            if orders["pauses"] != "ask":
                return ("fight", None)
            opts = ["fight", "yield", "manner", "edge"]
            if lethal:
                opts.append("last")
                if orders["escape"] != "never":
                    opts.append("escape")
            answer = self.ask_player(
                "pause",
                f"You are down to {own * 100:.0f}% and {foe.display()} is at "
                f"{other * 100:.0f}% — you {self._stance_phrase(mine)}, "
                f"they "
                f"{self._stance_phrase(theirs)}.",
                opts, "fight")
            if answer in ("edge", "manner"):
                return self._pause_switch(a, answer, mine)
            return (answer, None)
        if lethal and any(a.has_trait(t) for t in NPC_ESCAPE_TRAITS) \
                and self.rng.random() < NPC_ESCAPE_CHANCE:
            return ("escape", None)
        for trait, manner in NPC_PAUSE_LOSING:
            if a.has_trait(trait) and mine[1] != manner:
                return ("stance", (mine[0], manner))
        return ("fight", None)

    def _pause_foe(self, a: Agent, foe: Agent, mine: tuple, theirs: tuple,
                   own: float, other: float, lethal: bool) -> tuple:
        """A threshold crossed on the OTHER one, while you are ahead: the
        moment to ease off, or to make a lesson of it (VII §5)."""
        if a.play is not None:
            orders = self.orders_of(a)
            if orders["pauses"] != "ask":
                return ("press", None)
            opts = ["press", "ease", "manner"]
            answer = self.ask_player(
                "advantage",
                f"{foe.display()} is down to {other * 100:.0f}% and you are "
                f"at {own * 100:.0f}%.", opts, "press")
            if answer == "manner":
                return self._pause_switch(a, "manner", mine)
            if answer == "ease":
                step = EDGE_ORDER.index(mine[0])
                if step > 0:
                    return ("stance", (EDGE_ORDER[step - 1], mine[1]))
            return ("press", None)
        for trait, manner in NPC_PAUSE_WINNING:
            if a.has_trait(trait) and mine[1] != manner:
                return ("stance", (mine[0], manner))
        return ("press", None)

    def _blow_line(self, n: int, w: Agent, l: Agent, left: float) -> str:
        """One line for one exchange. Chosen by the round number and the
        state of the man taking it — narration never touches `rng`, so
        watching a fight cannot move the world."""
        bucket = ("even" if left >= PAUSE_FOE[0]
                  else "hurt" if left >= PAUSE_FOE[1] else "failing")
        pool = ROUND_BLOW_LINES[bucket]
        return pool[n % len(pool)].format(w=w.display(), l=l.name)

    def _bout(self, att: Agent, dfn: Agent, sa: tuple, sb: tuple,
              edge: str, ctx: str) -> dict:
        """THE FIGHT, exchange by exchange (VII §5).

        Both sides enter at their whole body less what they are still
        carrying. Each round is one exchange, weighted by power x stance and
        calibrated so the race reproduces the one roll; the loser of it takes
        a swing. Crossings of the pause thresholds hand the decision back —
        to the player through their orders, to an NPC through its nature —
        and then the fight flows on. Nothing here kills anybody: the bout
        decides who is standing, and `_duel`'s own outcome chain does the
        rest, which is why a played fight and a rolled one are the same
        fight.
        """
        r = self.rng
        who = [att, dfn]
        st = [sa, sb]
        top = [self.max_hp(att), self.max_hp(dfn)]
        hp = [top[0], top[1]]
        # Each fighter's blow is rolled ONCE: it is the pair of whole numbers
        # of exchanges this makes the fight take that the calibration inverts.
        roll = [r.uniform(*ROUND_SWING), r.uniform(*ROUND_SWING)]
        line = [self._yield_line(att), self._yield_line(dfn)]
        crossed = [set(), set()]      # own-hp thresholds already answered
        watched = [set(), set()]      # ... and the other one's, while ahead
        marks = [list(PAUSE_OWN), list(PAUSE_OWN)]
        seen_marks = [list(PAUSE_FOE), list(PAUSE_FOE)]
        # What the bout hands back: who is standing, how it ended, the
        # stances it ended in (they can change mid-fight), and the two bodies
        # it ended with, which is where the wounds come from.
        bout = {"who": who, "winner": None, "loser": None, "how": "beaten",
                "rounds": 0, "fled": None, "edge": edge,
                "hp": hp, "top": top, "sa": sa, "sb": sb}
        swing = [0.0, 0.0]
        floor = [0.0, 0.0]
        na = nb = 1
        fight = edge
        lethal = STANCE_EDGES[fight]["lethal"]
        stale = True
        n = 0
        self.tell("open", ROUND_OPEN.format(
            a=att.display(), aw=self._stance_phrase(st[0]),
            b=dfn.display(), bw=self._stance_phrase(st[1]), ctx=ctx))

        def settle(hitter: int, how: str):
            bout.update(winner=who[hitter], loser=who[1 - hitter], how=how)

        def strike(hitter: int) -> bool:
            """One landed exchange. True if it ended the fight."""
            target = 1 - hitter
            hp[target] = max(0.0, hp[target] - swing[hitter])
            self.tell("round", ROUND_LINE.format(
                n=n, blow=self._blow_line(n, who[hitter], who[target],
                                          hp[target] / max(1.0, top[target])),
                a=att.name, ahp=hp[0], b=dfn.name, bhp=hp[1]))
            if hp[target] <= floor[target]:
                settle(hitter, "down" if hp[target] <= 0.0
                       else ("yielded" if lethal else "beaten"))
                return True
            return False

        while n < ROUND_CAP:
            if stale:
                fight = max((st[0][0], st[1][0]), key=EDGE_ORDER.index)
                spec = STANCE_EDGES[fight]
                lethal = spec["lethal"]
                swing[0] = self._swing_of(att, dfn, st[0], st[1], roll[0])
                swing[1] = self._swing_of(dfn, att, st[1], st[0], roll[1])
                # THE REFERENCE GEOMETRY: two whole bodies stopping at the
                # edge's own line. The fight is then run on the real one, so
                # a wound or a yield line somebody moved themselves costs
                # exactly what it should and the invariant still holds for
                # the fight the harness measures.
                stop = spec["stop"] or ORDERS_DEFAULT["yield"]
                room = ROUND_HP * (1.0 - stop)
                na = max(1, math.ceil(room / swing[0]))
                nb = max(1, math.ceil(room / swing[1]))
                for i in (0, 1):
                    floor[i] = max(spec["stop"], line[i]) * top[i]
                    # THE BRINK: one exchange above the line this one stops
                    # at, so the last pause always leaves exactly one
                    # decision (see PAUSE_OWN).
                    brink = (floor[i] + swing[1 - i]) / max(1.0, top[i])
                    for table, into in ((PAUSE_OWN, marks),
                                        (PAUSE_FOE, seen_marks)):
                        second = max(table[1], brink)
                        into[i] = [table[0]]
                        if second <= table[0] - PAUSE_BRINK_GAP:
                            into[i].append(second)
                stale = False
            n += 1
            q = self._exchange_chance(
                self.duel_odds(att, dfn, st[0], st[1], phase=n), na, nb)
            hitter = 0 if r.random() < q else 1
            if strike(hitter):
                break
            target = 1 - hitter
            done = False
            # The one who took it, first: it is their business.
            for step, mark in enumerate(marks[target]):
                if hp[target] > mark * top[target] or step in crossed[target]:
                    continue
                crossed[target].add(step)
                act, payload = self._pause_own(
                    who[target], who[hitter], st[target], st[hitter],
                    hp[target] / top[target], hp[hitter] / top[hitter], lethal)
                if act == "yield":
                    settle(hitter, "yielded" if lethal else "beaten")
                    done = True
                elif act == "last":
                    line[target] = 0.0
                    floor[target] = 0.0
                elif act == "escape":
                    if r.random() < self._escape_chance(who[target],
                                                        who[hitter]):
                        settle(hitter, "fled")
                        bout["fled"] = who[target]
                        done = True
                    else:
                        self.tell("round", f"   {n}. "
                                  f"{who[target].display()} broke and could "
                                  f"not get clear.")
                        done = strike(hitter)
                elif act == "stance":
                    st[target] = payload
                    stale = True
                break
            if done:
                break
            # ... and then the one who is ahead, easing off or leaning in.
            for step, mark in enumerate(seen_marks[target]):
                if hp[target] > mark * top[target] or step in watched[hitter]:
                    continue
                if hp[hitter] <= hp[target]:
                    continue
                watched[hitter].add(step)
                act, payload = self._pause_foe(
                    who[hitter], who[target], st[hitter], st[target],
                    hp[hitter] / top[hitter], hp[target] / top[target], lethal)
                if act == "stance":
                    st[hitter] = payload
                    stale = True
                break
        if bout["winner"] is None:
            # Nobody could finish it: the one still on their feet has it.
            hitter = 0 if hp[0] >= hp[1] else 1
            settle(hitter, "beaten")
        bout.update(rounds=n, edge=fight, sa=st[0], sb=st[1])
        self.tell("close", "")
        return bout

    def _wound_resisted(self, a: Agent, level: int) -> int:
        """P5, §8: a trained body carries it off one level lighter, some of
        the time. The one place wound resistance is read, and both wound
        doors — the bout's and the front's — go through it."""
        if level <= 0 or a is None or a.play is None:
            return level
        rank = self.proficiency_rank(a, "body")
        if rank and self.rng.random() < PROFICIENCY_BODY_RESIST * rank:
            return level - 1
        return level

    def _bout_wounds(self, bout: dict):
        """VII §5: hp is gone when the fight is. What walks out is a wound —
        and only a played character carries one, because an NPC's whole body
        is already abstracted into the one number the kernel fights with."""
        for i, a in enumerate(bout["who"]):
            if a.play is None or not a.alive:
                continue
            frac = bout["hp"][i] / max(1.0, bout["top"][i])
            level = (2 if frac < WOUND_SERIOUS_AT
                     else 1 if frac < WOUND_LIGHT_AT else 0)
            level = self._wound_resisted(a, level)
            if level <= a.play.wound:
                continue
            a.play.wound = level
            self.log(WOUND_LINES[level].format(who=a.display()), [a])

    def heal_wound(self, a: Agent, how="rest") -> bool:
        """One level closed, and THE ONLY PLACE a wound closes. A restful
        season does it; P6's infirmary season and healing pill come through
        the same door with `how` set, and only the line changes."""
        if a is None or a.play is None or a.play.wound <= 0:
            return False
        word = WOUND_WORD[a.play.wound]
        a.play.wound -= 1
        self.log(WOUND_HEALED.get(how, WOUND_HEALED["rest"]).format(
            who=a.display(), what=word), [a])
        return True

    def _duel(self, att: Agent, dfn: Agent, context="",
              edge="duelling") -> Optional[Agent]:
        """One formula, with the tyranny of realms — fought in stance.

        `edge` is what the CONTEXT called the fight at: a tournament bout is
        not a murder, and a sect feud or a score come due is not a sparring
        match. Each fighter brings their own stance to it (`_pick_stance`),
        and every death, maiming, yield, spare and execution below is read
        out of the stance tables instead of a ladder of trait checks.

        Returns WHO WAS LEFT STANDING (P5), or None if nobody was. Nothing
        in the kernel reads it; a scene that has to know how a fight went —
        a master's trial, and whatever P6 and P7 stage — does.
        """
        r = self.rng
        gap = att.realm - dfn.realm
        ctx = f" over {context}" if context else ""
        sa = self._pick_stance(att, edge)
        sb = self._pick_stance(dfn, edge)
        # The harsher edge is the fight: nobody spars with someone who came
        # to kill them.
        fight = max((sa[0], sb[0]), key=EDGE_ORDER.index)
        spec = STANCE_EDGES[fight]
        lethal = spec["lethal"]
        # Who brought the killing edge. Between equals the stance clause
        # already describes a fighter who carries no manner BY their edge,
        # so naming them twice is dropped there and kept across a gap,
        # where no stance clause is printed at all.
        killer_edge = self._killer_clause(
            [x for x, st in ((att, sa), (dfn, sb)) if st[0] == "murderous"])
        killer_named = self._killer_clause(
            [x for x, st in ((att, sa), (dfn, sb))
             if st[0] == "murderous" and st[1]])

        if abs(gap) >= 1:
            # VII §5: the realms settle it before a stance is worth anything.
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
                         f"contest{killer_edge}.", [strong, weak],
                         dramatic=True)
                self.kill(weak, f"killed by {strong.display()}", killer=strong)
                self._stance_seen(strong, sa if strong is att else sb)
            else:
                weak.insight += 3
                self._add_grudge(weak, strong, 2)
                self.log(f"{weak.display()} fled before {strong.display()}"
                         f"{ctx}; the humiliation cuts deep (+insight).",
                         [strong, weak])
                self._mutate(weak, "humiliated")
            return strong

        # VII §5: a fight the PLAYED character is in unfolds into exchanges;
        # every other fight in the world is still settled with the one roll,
        # and both come out of the same distribution. A bout decides who is
        # left standing and nothing else — the outcome chain below is the
        # same chain either resolution ends in, in the same order.
        bout = None
        if self._rounds_wanted(att, dfn):
            bout = self._bout(att, dfn, sa, sb, fight, ctx)
            sa, sb = bout["sa"], bout["sb"]   # a stance can change mid-fight
            fight = bout["edge"]
            spec = STANCE_EDGES[fight]
            lethal = spec["lethal"]
            killer_named = self._killer_clause(
                [x for x, st in ((att, sa), (dfn, sb))
                 if st[0] == "murderous" and st[1]])
            if bout["how"] == "fled":
                self._broke_off(bout, ctx)
                self._fight_drill(att, sa)
                self._fight_drill(dfn, sb)
                return bout["winner"]
            att_wins = bout["winner"] is att
        else:
            att_wins = r.random() < self.duel_odds(att, dfn, sa, sb)
        winner, loser = (att, dfn) if att_wins else (dfn, att)
        win_st, lose_st = (sa, sb) if att_wins else (sb, sa)
        winner.standing += 1
        winner.resources += self._vice_spoils(winner)   # §7: spoils to the bone
        tail = self._stance_tail(winner, win_st, loser, lose_st)
        # Studying pays win or lose; the gallery pays only a win.
        for who, st in ((att, sa), (dfn, sb)):
            if st[1] == "studying":
                who.insight += STANCE_MANNERS["studying"]["insight"]
        if win_st[1] == "showy":
            winner.standing += STANCE_MANNERS["showy"]["standing"]
        self._stance_seen(att, sa)
        self._stance_seen(dfn, sb)
        # §4: ranks come from USE. Whatever stance they actually carried
        # through it is a little more theirs afterwards.
        self._fight_drill(att, sa)
        self._fight_drill(dfn, sb)
        merciful = win_st[1] == "merciful"

        # 1. The accident: a death nobody in the ring intended.
        if not merciful and r.random() < spec["kill"]:
            self._record_deed(winner, "blood")
            self.log(f"{winner.display()} put {loser.display()} down{ctx}"
                     f"{tail}; the blow was not meant to kill, and killed.",
                     [winner, loser], dramatic=True)
            self.kill(loser, f"killed by mischance in a duel with "
                             f"{winner.display()}", killer=winner)
        # 2. The yield, and what the victor does with it.
        elif lethal and not merciful \
                and self._finishes(winner, win_st, lose_st, loser):
            # §7 prices the killing: across a realm gap it is a killing
            # and costs the ledger, between equals a duel is a duel and the
            # spare below is the whole moral asymmetry.
            self._karma_kill(winner, loser)
            self._record_deed(winner, "blood")
            self.log(f"{winner.display()} beat {loser.display()} down{ctx} "
                     f"and finished it where they lay{tail}{killer_named}.",
                     [winner, loser], dramatic=True)
            self.kill(loser, f"slain in a duel by {winner.display()}",
                      killer=winner)
        else:
            # 3. The beaten one lives: spared, shamed, or crippled anyway.
            loser.insight += 3
            humbling = win_st[1] == "humiliating"
            self._add_grudge(loser, winner, 2 + (
                STANCE_MANNERS["humiliating"]["grudge"] if humbling else 0))
            spared = ""
            if lethal:
                winner.karma += KARMA_SPARE     # §7: sparing a beaten foe
                self._record_deed(winner, "mercy")
                spared = ", spared where the next blow would have finished it"
            if humbling:
                loser.standing = max(0, loser.standing
                                     - STANCE_MANNERS["humiliating"]["shame"])
            self.log(f"{winner.display()} defeated {loser.display()}{ctx}"
                     f"{tail}; {loser.display()} survives, shamed{spared} "
                     f"(+insight).", [winner, loser])
            meant = humbling or winner.has_trait("Cruel")
            maim = spec["maim"] * (STANCE_MAIM_CRUEL if meant else 1.0)
            if not merciful and r.random() < maim:
                self._maim(winner, loser, "the duel", meant=meant)
            self._mutate(loser, "humiliated")
        # VII §5: hp was only ever inside the fight. What is carried out of
        # it is a wound, and only by whoever was played.
        if bout is not None:
            self._bout_wounds(bout)
        return winner

    def _finishes(self, winner: Agent, win_st: tuple, lose_st: tuple,
                  loser: Agent) -> bool:
        """Does the victor finish a beaten foe who yields (VII §4, §6)?

        The kernel's roll is made either way, so that watching a fight does
        not shift the world's own dice; for a PLAYED victor the answer then
        comes from their standing orders instead, because the whole point of
        a yield is that the choice belongs to the one still standing.
        """
        rolled = self.rng.random() < self._execute_chance(winner, win_st,
                                                          lose_st)
        if winner.play is None:
            return rolled
        policy = self.orders_of(winner)["execute"]
        if policy in ("kill", "spare"):
            return policy == "kill"
        if not self.playing or self.ask is None:
            return rolled       # nobody at the keyboard: their own appetite
        return self.ask_player(
            "execute", f"{loser.display()} is beaten, and yields.",
            ["spare", "kill"], "spare") == "kill"

    def _broke_off(self, bout: dict, ctx: str):
        """VII §5: somebody took the door out of a killing fight.

        Nobody won it. The one who ran keeps the wound, the grudge and the
        lesson adversity always pays, and is seen running — which is its own
        price in a world that remembers.
        """
        fled, foe = bout["fled"], bout["winner"]
        fled.insight += ESCAPE_INSIGHT
        fled.standing = max(0, fled.standing - ESCAPE_STANDING)
        foe.standing += 1
        self._add_grudge(fled, foe, 1)
        self.log(f"{fled.display()} broke off from {foe.display()}{ctx} and "
                 f"got clear of it, hurt and seen to run (+insight).",
                 [fled, foe])
        self._bout_wounds(bout)
        self._mutate(fled, "humiliated")

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

        incursion = self._plan_incursion()
        if incursion is not None:
            land = self.places.get(incursion["land"])
            add("incursion", incursion,
                {"edge": self.waste_word(),
                 "land": land.name if land else "the marches"})

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
        elif kind == "incursion":
            land = self.places.get(p["land"])
            drawn = [self.agents[aid] for aid in p["defenders"]
                     if self.agents[aid].alive
                     and not self.agents[aid].is_ruler()]
            if land is not None and self.demon_threat >= INCURSION_AT:
                self._run_incursion(land, drawn)
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
        if kind == "incursion":
            # §3: march-landers and anyone who stood that line inside three
            # years. Everyone else reads about it in the digest.
            return (pc.aid in p.get("defenders", ())
                    or self.is_march(pc.home)
                    or (pc.front_last is not None
                        and self.year - pc.front_last <= FRONT_VETERAN_YEARS))
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

    def tell(self, kind: str, text: str):
        """THE FIGHT CAMERA (VII §5, §11).

        `ask_player` is how the kernel puts a question to the human; this is
        how it shows them a fight, one exchange at a time. It is not the
        chronicle — nothing here is recorded, and with no front end attached
        (batch runs, `--test-combat`) it goes nowhere at all. The kernel
        still never prints: `Play` owns the screen and decides whether these
        lines reach it or the fight collapses into its one chronicle line.
        """
        if self.narrate is not None:
            self.narrate(kind, text)

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
        # §7: a march-land below the line begs for relief from the WASTE,
        # through this same machinery. No new diplomacy anywhere — the Waste
        # holds no court to send the riders to.
        front = self.is_march(place)
        plea, done, task = r.choice(FRONT_PETITION_MISSIONS if front
                                    else PETITION_MISSIONS)
        sect = self._petition_sect(place.land)
        self.petitions.append(Petition(
            place=place, sect=sect, year=self.year,
            polity=polity.pid if polity else None, plea=plea, done=done,
            task=task, front=front))
        self._petition_seen[place.pid] = self.year
        ruler = self.leader_of(polity) if polity else None
        under = (f" under {self.ruler_ref(ruler)}"
                 if ruler is not None and ruler.alive else "")
        if front:
            under = f" and a night's ride from the {self.waste_word()} Waste"
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
        if petition.front:
            ruler = None    # §7: the Waste holds no court to make an enemy of
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
        if petition.front:
            opposition = (FRONT_PETITION_OPPOSITION
                          + FRONT_PETITION_PER_THREAT * self.demon_threat)
            self._front_served(hero, 1.0)
        else:
            opposition = PETITION_OPPOSITION
            if ruler is not None:
                opposition += PETITION_OPPOSITION_PER_REALM * (ruler.realm - 1)
            if polity is not None:
                opposition += PETITION_OPPOSITION_PER_ARMY * polity.army
        power = hero.power()
        chance = max(PETITION_ODDS[0],
                     min(PETITION_ODDS[1], power / (power + opposition)))
        domain = polity.domain if polity is not None else place.land.name
        broke = (f"what came over the line at {where}" if petition.front
                 else f"the men of {domain}")

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
                f"was broken by {broke}")
        if lethal:
            # §7: dying in defence of others. It buys the dead nothing.
            self._fell_defending(hero, f"the villagers of {where}")
            self.log(text + f"; they did not walk out, and {where} is left "
                            f"worse than it was.",
                     [hero] + ([ruler] if ruler is not None else []),
                     dramatic=True, place=place)
            self.kill(hero, f"killed by {broke} answering the plea of "
                            f"{where}")
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
            # VII §4: a tournament bout is fought at the DUELLING edge —
            # a final is not a murder. What the runner-up carries out of it
            # is that edge's own risk, tripled when the champion meant it,
            # and nothing at all when they fought merciful.
            st = self._native_stance(champ)
            meant = st[1] == "humiliating"
            maim = 0.0 if st[1] == "merciful" else (
                STANCE_EDGES["duelling"]["maim"]
                * (STANCE_MAIM_CRUEL if meant else 1.0))
            if r.random() < maim:
                self._maim(champ, runner, "the final", meant=meant)
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
            self._duel(f1, f2, context="the sect feud", edge="allout")
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
        # A score come due is a killing matter to the people who keep
        # scores; to everyone else it is a duel (VII §4: the call site names
        # the edge, and the stances take it from there).
        edge = "allout" if any(
            foe.has_trait(t) for t in ("Vengeful", "Ruthless", "Bloodthirsty")
        ) else "duelling"
        self._duel(foe, pc, context="a score come due", edge=edge)

    # -- resolution phase ---------------------------------------------------

    def _resolution_phase(self):
        self._front_drift()
        self._drift_prosperity()
        self._stipends()
        self._karma_luck()
        self._pill_year()               # P6 §8: what a pill-free year sheds
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
        # §7: the marches live under raids that never stop, and settle one
        # to two points under the temper the rest of their land would have.
        march = {m.pid for m in self.march_lands}
        drag = min(MARCH_DRAG_CAP, MARCH_DRAG_PER_THREAT * self.demon_threat)
        for p in self.settlements():
            if march and p.land is not None and p.land.pid in march:
                p.prosperity = max(0.0, p.prosperity - drag)
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
        # §8: what the reading room is worth — a percentage point a rank, on
        # the one roll a cultivation career is actually decided by. Zero for
        # everybody who is not played, and rolled for nobody.
        chance += (PROFICIENCY_THEORY_TRIBULATION
                   * self.proficiency_rank(a, "theory"))
        # P6 §8: a clarity pill, spent HERE and nowhere else — on the
        # ATTEMPT, win or lose, which is what "one breakthrough attempt"
        # means. Nobody unplayed has one, and no die is rolled to find out.
        if a.play is not None and a.play.clarity:
            chance += a.play.clarity
            a.play.clarity = 0.0
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
        if a.front_seasons:
            stands = ("" if not a.front_stands else
                      (" and stood in the breaking of the line once."
                       if a.front_stands == 1 else
                       f" and stood in {a.front_stands} breakings of the "
                       f"line."))
            parts.append(f"Served {a.front_seasons} seasons on the "
                         f"{self.waste_word()} marches{stands or '.'}")
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
        self._seed_stances(a)       # VII §4: what their own nature taught
        self._seed_orders(a)        # VII §6: and what it does by default
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
            self._seed_stances(self.pc)
            self._seed_orders(self.pc)
        return self.pc

    def _seed_stances(self, a: Agent) -> None:
        """VII §4: a played character starts trained in the one stance their
        own character already fights in, exactly like an NPC, and untrained
        in everything else. Raising the rest is the drill, the training
        hall, and whatever a master is willing to teach (P5).
        """
        if a.play is None:
            return
        edge, manner = self._native_stance(a)
        keys = list(EDGE_ORDER[:EDGE_ORDER.index(edge) + 1])
        if manner:
            keys.append(manner)
        for key in keys:
            a.play.stances[key] = max(a.play.stances.get(key, 0),
                                      STANCE_NPC_RANK)
            # P5: what nature already taught is practice already done, so
            # the first drill goes toward the SECOND rank and not the first.
            a.play.drills[key] = max(a.play.drills.get(key, 0.0),
                                     self._stance_seasons(STANCE_NPC_RANK))

    def _seed_orders(self, a: Agent) -> None:
        """VII §6: a played character starts under the default orders, not a
        blank card, so that every question a fight can ask already has an
        answer and a bout can run without stopping at all."""
        if a.play is None:
            return
        for key, value in ORDERS_DEFAULT.items():
            a.play.orders.setdefault(key, value)

    # -- training, masters and the hall (VII §8) ----------------------------

    @staticmethod
    def track_rank(seasons: float, shape: str) -> int:
        """THE ONE RANK MECHANIC (§8). Seasons of practice in, rank out.

        Rank N costs `step` x N seasons, so the whole track costs a
        triangular number of them and the last rank costs as much as the
        first three. Every ranked thing the player layer has — the three
        proficiencies, the stances, P6's professions — is read here and
        nowhere else.
        """
        spec = RANK_SHAPES[shape]
        rank, need = 0, 0.0
        while rank < spec["max"]:
            need += spec["step"] * (rank + 1)
            if seasons + 1e-9 < need:
                break
            rank += 1
        return rank

    @staticmethod
    def track_progress(seasons: float, shape: str) -> tuple:
        """(rank, seasons done toward the next, seasons the next one costs).
        The card reads this; nothing in the simulation does."""
        spec = RANK_SHAPES[shape]
        rank = World.track_rank(seasons, shape)
        done = sum(spec["step"] * (i + 1) for i in range(rank))
        if rank >= spec["max"]:
            return (rank, 0.0, 0.0)
        return (rank, seasons - done, spec["step"] * (rank + 1))

    def proficiency_rank(self, a: Agent, key: str) -> int:
        """Body / Weapon / Theory, rank 0-5. Zero for everybody who is not
        played, and — this matters for the batch stream — WITHOUT a die."""
        if a is None or a.play is None:
            return 0
        return self.track_rank(a.play.proficiencies.get(key, 0.0),
                               PROFICIENCY_SHAPE)

    def master_of(self, a: Agent) -> Optional[Agent]:
        """The living teacher a character is bound to, if any."""
        if a is None:
            return None
        for aid, rel in a.rels.items():
            if rel.kind != "master":
                continue
            other = self.agents.get(aid)
            if other is not None and other.alive:
                return other
        return None

    def teaching(self, a: Agent) -> float:
        """§8: what a season of training is worth. A master multiplies it —
        that is the whole mechanical content of having one, and it is why a
        master is worth a season of asking and a trial."""
        return MASTER_TEACHING if self.master_of(a) is not None else 1.0

    def _practice(self, a: Agent, store: dict, key: str, shape: str,
                  seasons: float) -> tuple:
        """Put seasons into one track. Returns (old rank, new rank).

        The single door P6's professions write through as well: everything
        that can be ground at is ground at here, so a teaching multiplier, a
        manual or a pill only ever has to move the number going in.
        """
        was = self.track_rank(store.get(key, 0.0), shape)
        store[key] = store.get(key, 0.0) + seasons
        return (was, self.track_rank(store[key], shape))

    @staticmethod
    def _stance_seasons(rank: int) -> float:
        """The practice a granted stance rank is worth, so that a gift and a
        drill never pay for the same rank twice."""
        spec = RANK_SHAPES["stance"]
        return sum(spec["step"] * (i + 1)
                   for i in range(min(rank, spec["max"])))

    def _grant_stance(self, a: Agent, key: str, rank: int, by: str) -> bool:
        """A stance TAUGHT rather than drilled (§4: a master's parting gift
        can be Patience at rank 2). Returns whether it was worth anything."""
        if a.play is None or (key not in STANCE_EDGES
                              and key not in STANCE_MANNERS):
            return False
        rank = max(0, min(STANCE_RANK_MAX, rank))
        if a.play.stances.get(key, 0) >= rank:
            return False
        a.play.stances[key] = rank
        a.play.drills[key] = max(a.play.drills.get(key, 0.0),
                                 self._stance_seasons(rank))
        self.log(STANCE_TAUGHT_LINE.format(who=a.display(), stance=key,
                                           by=by, rank=rank,
                                           max=STANCE_RANK_MAX), [a])
        return True

    def _drill_target(self, a: Agent) -> str:
        """Which stance a weapon season drills (§3).

        You train what you fight in: the edge and the manner the standing
        orders put you in, or your own nature's when the orders leave it to
        you — and of those, whichever is the weaker. No die is rolled, so
        the player chooses this through `orders` and nothing else.
        """
        orders = self.orders_of(a)
        edge, manner = self._native_stance(a)
        want = [orders["edge"] if orders["edge"] in STANCE_EDGES else edge]
        told = orders["manner"]
        if told in STANCE_MANNERS:
            want.append(told)
        elif told != "none" and manner:
            want.append(manner)
        return min(want, key=lambda k: (self.stance_rank(a, k), want.index(k)))

    def _act_train(self, a: Agent, key: str, share=1.0):
        """A season on the practice ground, at the racks, or in the reading
        room (§3, §8). One quarter of a year like everything else — which is
        why a rank is a project and not a purchase."""
        r = self.rng
        seasons = share * len(SEASONS) * self.teaching(a)
        was, now = self._practice(a, a.play.proficiencies, key,
                                  PROFICIENCY_SHAPE, seasons)
        self._act_cultivate(a, share * TRAIN_QI_SHARE)   # still at the sect
        stance = self._drill_target(a) if key == "weapon" else ""
        text = r.choice(TRAIN_LINES[key]).format(
            who=a.display(), stance=stance, realm=a.realm_name)
        a.history.append((self.year, text))
        if key == "theory":
            a.insight += PROFICIENCY_THEORY_INSIGHT * share * len(SEASONS)
        if key == "weapon":
            self._drill_stance(a, stance, TRAIN_STANCE_SEASONS * share
                               * len(SEASONS) * self.teaching(a))
        if now > was:
            self.log(TRAIN_RANK_LINES[key].format(
                who=a.display(), word=PROFICIENCY_WORDS[now], rank=now,
                max=RANK_SHAPES[PROFICIENCY_SHAPE]["max"]), [a])
        # §8: what a teacher is FOR. Now and then they simply hand a form
        # over instead of watching the drill.
        master = self.master_of(a)
        if master is not None and r.random() < MASTER_STANCE_CHANCE * share:
            self._teach_stance(a, master)

    def _drill_stance(self, a: Agent, key: str, seasons: float):
        """Stance proficiency EARNED THROUGH USE (§4) — the drill half. The
        other half is `_fight_drill`, which is the same door from a fight."""
        if a.play is None or not key:
            return
        was, now = self._practice(a, a.play.drills, key, "stance", seasons)
        if now > was:
            a.play.stances[key] = max(a.play.stances.get(key, 0), now)
            self.log(STANCE_RANK_LINE.format(
                who=a.display(), stance=key, rank=now,
                max=STANCE_RANK_MAX), [a])

    def _fight_drill(self, a: Agent, st: tuple):
        """§4: ranks come from USE. A stance carried through a real fight is
        worth a fraction of a season drilling it — which is what makes a
        fighter good at the way they actually fight, and leaves the edge
        somebody else forced on them expensive."""
        if a is None or a.play is None:
            return
        for key in st:
            if key:
                self._drill_stance(a, key, FIGHT_DRILL_SEASONS)

    def _act_hall(self, a: Agent, share=1.0):
        """The sect training hall (§3): the forms, for standing and silver.

        The hall's other half — techniques off the library shelves — is P7's;
        `_hall_technique` is the seam and returns nothing until then.
        """
        r = self.rng
        if a.standing < HALL_STANDING or a.resources < HALL_COST:
            a.history.append((self.year, HALL_LINES["shut"].format(
                who=a.display(), sect=a.sect)))
            return
        a.resources -= HALL_COST
        self._practice(a, a.play.proficiencies, "theory", PROFICIENCY_SHAPE,
                       HALL_THEORY * share * len(SEASONS) * self.teaching(a))
        if r.random() < HALL_STANDING_GAIN * share * len(SEASONS):
            a.standing += 1
        self._hall_technique(a)         # P7
        self._hall_manual(a, share)     # P6 §8: the other door past rank 1
        taught = ""
        if r.random() < HALL_TEACHES * share * len(SEASONS):
            taught = self._hall_stance(a)
        if taught:
            self.log(HALL_LINES["taught"].format(
                who=a.display(), sect=a.sect, stance=taught), [a])
        else:
            a.history.append((self.year, HALL_LINES["read"].format(
                who=a.display(), sect=a.sect)))

    def _hall_stance(self, a: Agent) -> str:
        """What the hall can teach: a form nobody has shown this disciple
        yet. The hall gives the FORM (rank 1); the drill gives the rest."""
        unknown = [k for k in list(STANCE_MANNERS) + list(EDGE_ORDER)
                   if self.stance_rank(a, k) < HALL_STANCE_RANK]
        if not unknown:
            return ""
        key = self.rng.choice(unknown)
        a.play.stances[key] = max(a.play.stances.get(key, 0),
                                  HALL_STANCE_RANK)
        a.play.drills[key] = max(a.play.drills.get(key, 0.0),
                                 self._stance_seasons(HALL_STANCE_RANK))
        return key

    def _hall_manual(self, a: Agent, share=1.0) -> str:
        """§8's other door past a craft's first rank: the written-down
        version of it, off the sect's own shelves, for a craft this disciple
        has actually started. P7's technique manuals — the flawed ones
        included — are a different thing on the same shelf."""
        want = [k for k in PROFESSIONS
                if k not in a.play.manuals
                and self.track_rank(a.play.professions.get(k, 0.0),
                                    PROFESSION_SHAPE) >= 1]
        if not want or self.rng.random() >= HALL_MANUAL * share * len(SEASONS):
            return ""
        key = self.rng.choice(want)
        a.play.manuals.append(key)
        self.log(HALL_MANUAL_LINE.format(who=a.display(), sect=a.sect,
                                         craft=key), [a])
        return key

    def _hall_technique(self, a: Agent):
        """P7's seam: the sect library sells technique cards for standing and
        silver (VII §9). Nothing here yet, and deliberately nothing — a
        technique is a card with a school and a realm gate, and neither
        exists until P7 writes them."""
        return None

    def _master_technique(self, a: Agent, master: Agent):
        """P7's other seam: §8's "occasionally a technique". The master rel
        and the trial are P5's; what a teacher can hand over beyond a stance
        is P7's, and this is where it goes."""
        return None

    # -- professions: the furnace, the forge, the infirmary (VII §8) --------
    #
    # ONE RANK MECHANIC, THREE SKINS. Every rank below is read out of
    # `profession_rank`, which reads `World.track_rank`, which is where every
    # rank in the player layer comes from; the seasons go in through
    # `World._practice`, the same dumb accumulator P5's drills use. NOTHING
    # HERE ROLLS FOR AN NPC: every entry point returns before the first die
    # when `play` is None, which is what keeps the batch stream identical.

    def profession_rank(self, a: Agent, key: str) -> int:
        """Alchemy / forging / healing, rank 0-3 — and §8's WALL.

        Past `PROFESSION_TEACHER_RANK` the seasons still bank but the rank
        does not rise, until somebody who knows the craft is standing over it
        (a master) or has written it down (a manual). The practice is not
        lost: the day the teacher arrives, the hands already know it.
        """
        if a is None or a.play is None:
            return 0
        rank = self.track_rank(a.play.professions.get(key, 0.0),
                               PROFESSION_SHAPE)
        if (rank >= PROFESSION_TEACHER_RANK
                and not self.profession_taught(a, key)):
            return PROFESSION_TEACHER_RANK - 1
        return rank

    def profession_taught(self, a: Agent, key: str) -> bool:
        """§8's gate on rank 2 and up: a teacher, or a manual.

        Deliberately NOT folded into `_practice`, which must stay a dumb
        accumulator — a gate that ate seasons would make a manual found late
        worth nothing, and the whole point of the wall is that it is a wall
        and not a hole in the floor.
        """
        if a is None or a.play is None:
            return False
        return key in a.play.manuals or self.master_of(a) is not None

    def _act_profession(self, a: Agent, key: str, share=1.0):
        """A season at the furnace, the forge or the infirmary (§3, §8).

        One season, two things, exactly like a season at the racks: the
        practice goes into the track, and the craft does whatever the rank
        the practice has already bought is good for.
        """
        r = self.rng
        seasons = share * len(SEASONS) * self.teaching(a)
        was = self.profession_rank(a, key)
        banked = self.track_rank(a.play.professions.get(key, 0.0),
                                 PROFESSION_SHAPE)
        self._practice(a, a.play.professions, key, PROFESSION_SHAPE, seasons)
        now = self.profession_rank(a, key)
        earned = self.track_rank(a.play.professions.get(key, 0.0),
                                 PROFESSION_SHAPE)
        self._act_cultivate(a, share * PROFESSION_QI_SHARE)   # at the sect
        if now > was:
            self.log(PROFESSION_LINES["rank"].format(
                who=a.display(), word=PROFESSION_WORDS[now], craft=key,
                rank=now, max=RANK_SHAPES[PROFESSION_SHAPE]["max"]), [a])
        elif earned > banked and earned > now:
            # §8's wall, said the season the hands hit it and not again.
            a.history.append((self.year, PROFESSION_LINES["wall"].format(
                who=a.display(), craft=key, word=PROFESSION_WORDS[now])))
        if self._craft_accident(a, key, share):
            return                      # the season ended in the infirmary
        if now <= 0:
            a.history.append((self.year, r.choice(
                PROFESSION_LINES["practice"][key]).format(who=a.display())))
            return
        if r.random() < CRAFT_SPOIL.get(now, 0.0):
            a.history.append((self.year, PROFESSION_LINES["spoiled"][key]
                              .format(who=a.display())))
            return
        if key == "alchemy":
            self._brew(a, now, share)
        elif key == "forging":
            self._forge(a, now, share)
        else:
            self._infirmary(a, now, share)

    def _craft_accident(self, a: Agent, key: str, share=1.0) -> bool:
        """Did the season take a piece out of them? (§8, and §12's autopilot
        target — see CRAFT_ACCIDENT.) Returns True if the season ends here."""
        r = self.rng
        if r.random() >= CRAFT_ACCIDENT[key] * share * len(SEASONS):
            return False
        if r.random() < CRAFT_ACCIDENT_DEATH:
            self.kill(a, r.choice(CRAFT_DEATHS[key]))
            return True
        bad = r.random() < CRAFT_ACCIDENT_SERIOUS
        if bad:
            a.burden += 1
        self.log(CRAFT_ACCIDENT_LINES[key].format(who=a.display())
                 + (CRAFT_ACCIDENT_BAD if bad else ""), [a], dramatic=bad)
        self._take_wound(a, 2 if bad else 1)
        return True

    # -- alchemy: the pills, and the bill for them --------------------------

    def _brew(self, a: Agent, rank: int, share=1.0):
        """A batch out of the furnace.

        WHICH pill is the player's call, and it is a STANDING one (`brew
        KIND`, `PlayerState.brew`) rather than a question a season — a
        furnace is set up for a recipe and left that way, and a timeskip
        that stopped to ask four times a year would not be a timeskip.
        """
        r = self.rng
        kind = a.play.brew if a.play.brew in PILL_KINDS else "qi"
        lo, hi = PILL_YIELD[rank]
        n = self._share_int(r.randint(lo, hi), share * len(SEASONS))
        if n <= 0:
            a.history.append((self.year, PROFESSION_LINES["spoiled"]["alchemy"]
                              .format(who=a.display())))
            return
        a.play.pills[kind] = a.play.pills.get(kind, 0) + n
        self.log(PILL_LINES["brew"].format(who=a.display(), n=n, kind=kind,
                                           s="" if n == 1 else "s"), [a])

    def take_pill(self, kind: str, a: Optional[Agent] = None) -> str:
        """§8: swallow one, and pay TOXICITY for it.

        Every pill is a point; above `PILL_TOXICITY_FREE` every further one
        is a point of BURDEN, which is permanent and is felt at every
        tribulation after. Six pills is a career's worth of free shortcuts —
        the seventh starts eating the ceiling, and the ceiling is what a
        cultivator's whole life is about. Toxicity sheds a point a pill-free
        year (`_pill_year`), so a player who paces themselves never pays.

        §8 reads "+qi on a cultivation season"; the qi is paid HERE, where
        the pill goes down, because nothing in this layer carries a pending
        effect between one season and the next (VII §5 refused exactly that
        for hp). What "on a cultivation season" means in play is that the
        player chooses the season to swallow it in — and everything the pill
        is worth is on the table when they do.

        Returns what to tell the human; the chronicle gets the rest.
        """
        a = self.pc if a is None else a
        if a is None or a.play is None or not a.alive:
            return "There is nobody to take it."
        want = (kind or "").strip().lower()
        kind = next((k for k in PILL_KINDS if k.startswith(want)), "")
        if not kind:
            return f"Pills come in three kinds: {', '.join(PILL_KINDS)}."
        if a.play.pills.get(kind, 0) <= 0:
            return PILL_LINES["none"].format(who=a.display(), kind=kind)
        if kind == "healing" and not a.play.wound:
            return PILL_LINES["whole"].format(who=a.display())
        a.play.pills[kind] -= 1
        a.play.toxicity += 1
        a.play.pill_year = self.year
        if kind == "qi":
            a.qi = min(100, a.qi + PILL_QI)
            self.log(PILL_LINES["qi"].format(who=a.display()), [a])
        elif kind == "healing":
            self.heal_wound(a, how="pill")      # P3's one door, still
        else:
            # No pill market in v1: the alchemist and the one who swallows it
            # are the same hand, so the grade is read off the craft.
            a.play.clarity += PILL_CLARITY_PER_RANK * max(
                1, self.profession_rank(a, "alchemy"))
            self.log(PILL_LINES["clarity"].format(who=a.display()), [a])
        if a.play.toxicity > PILL_TOXICITY_FREE:
            a.burden += PILL_TOXICITY_BURDEN
            self.log(PILL_LINES["toxic"].format(who=a.display()), [a])
        return ""

    def set_brew(self, kind: str, a: Optional[Agent] = None) -> str:
        """What the furnace is set up for, until told otherwise."""
        a = self.pc if a is None else a
        if a is None or a.play is None:
            return "There is no furnace to set."
        want = (kind or "").strip().lower()
        match = next((k for k in PILL_KINDS
                      if want and k.startswith(want)), "")
        if not match:
            return ("The furnace takes one recipe at a time: "
                    + "; ".join(f"{k} ({v})" for k, v in PILL_KINDS.items()))
        a.play.brew = match
        return f"The furnace is set up for {match} pills: {PILL_KINDS[match]}."

    def _pill_year(self):
        """§8: toxicity decays a point per PILL-FREE year. No die, and no
        agent without a played sheet is touched."""
        for a in self.living():
            if a.play is None or a.play.toxicity <= 0:
                continue
            if a.play.pill_year == self.year:
                continue
            a.play.toxicity = max(0, a.play.toxicity - PILL_DECAY)

    # -- forging: the rack --------------------------------------------------

    def _forge(self, a: Agent, rank: int, share=1.0):
        """A piece off the anvil. Worth a point or two of power — inside the
        §5 cap, which `player_power` and nothing else enforces — and worth
        silver to somebody who would rather buy than make."""
        r = self.rng
        grade = rank
        if rank == 2 and r.random() < FORGE_MASTERWORK:
            grade = 3
        what = r.choice(FORGE_NAMES)
        a.play.gear.append({"what": what, "power": FORGE_POWER[grade],
                            "grade": grade})
        self.log(FORGE_LINES["made"].format(
            who=a.display(), what=what, grade=FORGE_GRADES[grade],
            power=FORGE_POWER[grade]), [a])

    def gear_power(self, a: Agent) -> float:
        """What the rack is worth in a fight: the best piece on it, and no
        stacking — you carry one sword."""
        if a is None or a.play is None or not a.play.gear:
            return 0.0
        return float(max(g["power"] for g in a.play.gear))

    def _market_buyer(self, a: Agent, price: int) -> Optional[Agent]:
        """Somebody with the silver for it. §8: what they buy MELTS INTO
        their `resources` — an NPC keeps no inventory, because their one
        number is already the abstraction of every blade and pill they own,
        and it does not move for a fair trade."""
        pool = [o for o in self.cultivators()
                if o.aid != a.aid and o.alive and o.resources >= price]
        if not pool:
            return None
        mine = [o for o in pool if o.sect == a.sect]
        return self.rng.choice(mine or pool)

    def sell_item(self, what: str, a: Optional[Agent] = None) -> str:
        """Sell a pill or a piece off the rack (§8). The gear sold is the
        WORST piece there — you do not sell the sword off your own hip until
        it is the only one left."""
        a = self.pc if a is None else a
        if a is None or a.play is None or not a.alive:
            return "There is nobody to sell anything."
        want = (what or "").strip().lower()
        kind = next((k for k in PILL_KINDS if want and k.startswith(want)), "")
        if not kind:
            if not want or not ("gear".startswith(want)
                                or want in ("rack", "piece")):
                return f"Sell 'gear' or one of: {', '.join(PILL_KINDS)}."
            if not a.play.gear:
                return FORGE_LINES["empty"].format(who=a.display())
            piece = min(a.play.gear, key=lambda g: g["power"])
            a.play.gear.remove(piece)
            price = FORGE_VALUE[piece["grade"]]
            self._sold(a, piece["what"], price)
            return ""
        if a.play.pills.get(kind, 0) <= 0:
            return PILL_LINES["none"].format(who=a.display(), kind=kind)
        a.play.pills[kind] -= 1
        self._sold(a, f"a {kind} pill", PILL_VALUE[kind])
        return ""

    def _sold(self, a: Agent, what: str, price: int):
        a.resources += price
        buyer = self._market_buyer(a, price)
        if buyer is None:
            self.log(FORGE_LINES["market"].format(
                who=a.display(), what=what, silver=price), [a])
            return
        self.log(FORGE_LINES["sold"].format(
            who=a.display(), what=what, buyer=buyer.display(),
            silver=price), [a, buyer])

    # -- healing: your own wounds, and other people's -----------------------

    def _patient(self, a: Agent) -> Optional[Agent]:
        """Who gets carried in. Sect first, then the country, then whoever
        the season brings; never a ruler, who has physicians of his own."""
        pool = [o for o in self.cultivators()
                if o.aid != a.aid and o.alive and o.age >= 14
                and not o.is_ruler()]
        if not pool:
            return None
        short = pool if len(pool) <= HEAL_POOL else self.rng.sample(pool,
                                                                   HEAL_POOL)
        weights = []
        for o in short:
            w = 1.0
            if o.sect == a.sect:
                w += HEAL_WEIGHT_SECT
            if (a.home is not None and o.home is not None
                    and o.home.land is a.home.land):
                w += HEAL_WEIGHT_LAND
            if o.aid in a.rels:
                w += HEAL_WEIGHT_KNOWN
            weights.append(w)
        return self.rng.choices(short, weights=weights)[0]

    def _infirmary(self, a: Agent, rank: int, share=1.0):
        """A season of it. Your own wounds close for nothing; somebody
        else's is a scene with a ledger attached (§8)."""
        r = self.rng
        if a.play.wound and rank >= HEAL_SELF_RANK:
            self.heal_wound(a, how="craft")
            while a.play.wound and rank >= HEAL_FULL_RANK:
                self.heal_wound(a, how="craft")
        if r.random() >= HEAL_PATIENT * share * len(SEASONS):
            a.history.append((self.year, HEAL_LINES["none"].format(
                who=a.display())))
            return
        patient = self._patient(a)
        if patient is None:
            a.history.append((self.year, HEAL_LINES["none"].format(
                who=a.display())))
            return
        trouble = r.choice(HEAL_TROUBLES)
        dire = r.random() < HEAL_DIRE
        chance = HEAL_SAVE_BASE + HEAL_SAVE_PER_RANK * rank
        if dire:
            chance -= HEAL_DIRE_PENALTY
        chance = max(HEAL_SAVE_CLAMP[0], min(HEAL_SAVE_CLAMP[1], chance))
        fields = dict(who=a.display(), patient=patient.display(),
                      trouble=trouble)
        if r.random() >= chance:
            a.insight += HEAL_LOST_INSIGHT
            self.log(HEAL_LINES["lost"].format(**fields), [a, patient],
                     dramatic=dire)
            if dire:
                self.kill(patient, "died of their injuries under a healer's "
                                   "hands")
            return
        a.karma += HEAL_KARMA_DIRE if dire else HEAL_KARMA
        a.resources += r.randint(*HEAL_FEE)
        text = HEAL_LINES["dire" if dire else "saved"].format(**fields)
        if dire and rank >= LIFEDEBT_RANK:
            # §8: the strongest coin in the social ledger. `_add_grudge` will
            # not write over it, and the holder grieves like a sworn brother.
            self._record_deed(a, "mercy")
            self._bind(a, patient, "life-debt", LIFEDEBT_INTENSITY)
            text += HEAL_LINES["debt"].format(**fields)
        else:
            back = patient.rels.get(a.aid)
            if back is None or back.kind not in FRIENDLY_KINDS:
                self._bind(a, patient, "friend", HEAL_GRATITUDE)
            else:
                back.intensity += HEAL_GRATITUDE
            if dire:
                self._record_deed(a, "mercy")
        self.log(text, [a, patient], dramatic=dire)

    # -- seek a master (VII §8) ---------------------------------------------

    def _master_weight(self, a: Agent, cand: Agent) -> float:
        """How likely this one is to be the one the season turns up."""
        w = MASTER_WEIGHT_BASE
        w += MASTER_WEIGHT_TRAIT * sum(1 for t in cand.traits
                                       if a.has_trait(t))
        if cand.sect == a.sect:
            w += MASTER_WEIGHT_SECT
        if (a.home is not None and cand.home is not None
                and cand.home.land is a.home.land):
            w += MASTER_WEIGHT_LAND
        if cand.aid in a.rels:
            w += MASTER_WEIGHT_KNOWN
        if self._has_vice(cand):
            w += MASTER_WEIGHT_VICE
        return max(0.1, w)

    def _master_candidate(self, a: Agent) -> Optional[Agent]:
        """§8: realm >= PC + 1, compatible traits weighted."""
        pool = [o for o in self.cultivators()
                if o.aid != a.aid and o.alive
                and o.realm >= a.realm + MASTER_MIN_GAP
                and o.age >= a.age + MASTER_MIN_AGE_GAP]
        if not pool:
            return None
        shortlist = pool if len(pool) <= MASTER_POOL else self.rng.sample(
            pool, MASTER_POOL)
        weights = [self._master_weight(a, o) for o in shortlist]
        return self.rng.choices(shortlist, weights=weights)[0]

    def _act_seek_master(self, a: Agent, share=1.0):
        """A season of asking, and if somebody answers, their trial (§8)."""
        r = self.rng
        if self.master_of(a) is not None:
            a.history.append((self.year, MASTER_LINES["have"].format(
                who=a.display())))
            return
        cand = None
        if r.random() < MASTER_FIND * share * len(SEASONS):
            cand = self._master_candidate(a)
        if cand is None:
            a.history.append((self.year, MASTER_LINES["none"].format(
                who=a.display())))
            return
        self.log(MASTER_LINES["found"].format(
            who=a.display(), master=cand.display()), [a, cand])
        self._master_trial(a, cand)

    def _trial_partner(self, a: Agent, cand: Agent) -> Optional[Agent]:
        """Who the trial is fought against.

        NOT the master: §5's tyranny of realms settles a fight across a realm
        before a stance is worth anything, and a candidate is a realm above
        by construction — a bout with them would be a flight, not a test. So
        the master sets somebody of the seeker's own height on them, which is
        what a trial has always been anyway.
        """
        peers = [o for o in self.cultivators()
                 if o.aid != a.aid and o.aid != cand.aid and o.alive
                 and o.realm == a.realm and o.age >= 14]
        if not peers:
            return None
        theirs = [o for o in peers if o.sect == cand.sect]
        return self.rng.choice(theirs or peers)

    def _master_trial(self, a: Agent, cand: Agent):
        """THE TRIAL (§8): a test of the RECORD, and one bout at Sparring.

        Karma is read in the candidate's own direction — a teacher who keeps
        a clean ledger wants one, and one who does not wants nerve — so the
        trial is a reading of the life the player has actually led, not a
        die dressed up as a scene.
        """
        r = self.rng
        score = (a.insight * MASTER_TRIAL_INSIGHT
                 + len(a.epithets) * MASTER_TRIAL_EPITHET
                 + a.standing * MASTER_TRIAL_STANDING
                 + a.talent * MASTER_TRIAL_TALENT)
        direction = -1.0 if self._has_vice(cand) else 1.0
        score += a.karma * MASTER_TRIAL_KARMA * direction
        partner = self._trial_partner(a, cand)
        if partner is not None:
            winner = self._duel(partner, a, context=MASTER_LINES["spar"],
                                edge="sparring")
            score += MASTER_TRIAL_WON if winner is a else MASTER_TRIAL_LOST
        if not a.alive:
            # Sparring kills nobody — but the edge a fight is CALLED at is
            # not the edge everybody brings to it, and a trial partner who
            # came to kill is a trial that ends differently (VII §4).
            return
        score += r.uniform(-MASTER_TRIAL_NOISE, MASTER_TRIAL_NOISE)
        need = MASTER_TRIAL_NEED + MASTER_TRIAL_PER_REALM * (cand.realm
                                                             - a.realm)
        if score < need:
            self.log(MASTER_LINES["failed"].format(
                who=a.display(), master=cand.display()), [a, cand])
            return
        self._bind(a, cand, "master", MASTER_INTENSITY)
        a.insight += MASTER_INSIGHT
        cand.karma += MASTER_KARMA
        gift = ""
        stance = self._teach_stance(a, cand, rank=MASTER_GIFT_RANK,
                                    quiet=True)
        if stance:
            gift = MASTER_LINES["gift"].format(master=cand.display(),
                                               stance=stance)
        self._master_technique(a, cand)         # P7
        self.log(MASTER_LINES["passed"].format(
            who=a.display(), master=cand.display()) + gift, [a, cand],
            dramatic=True)

    def _teach_stance(self, a: Agent, master: Agent, rank=0,
                      quiet=False) -> str:
        """What a master hands over.

        Only what they themselves fight in (§4): the manner their own nature
        takes, and the edges up to the one they are willing to take a fight
        to. A teacher who has never come to kill cannot teach you how, and
        breadth is what the training hall is for.
        """
        if a.play is None:
            return ""
        edge, manner = self._native_stance(master)
        want = [k for k in (manner,) if k]
        want += list(EDGE_ORDER[:EDGE_ORDER.index(edge) + 1])[::-1]
        for key in want:
            target = max(rank, self.stance_rank(a, key) + 1)
            target = min(STANCE_RANK_MAX, target)
            if self.stance_rank(a, key) >= target:
                continue
            if quiet:
                a.play.stances[key] = target
                a.play.drills[key] = max(a.play.drills.get(key, 0.0),
                                         self._stance_seasons(target))
            else:
                self._grant_stance(a, key, target, master.display())
            return key
        return ""

    # -- what the player layer is worth in a fight (VII §5) ------------------

    def activity_available(self, key: str) -> bool:
        """Is this season's activity even on the table? The kernel owns the
        answer so that the terminal front end and the autopilot (§12) read
        exactly one list of legal choices."""
        pc = self.pc
        if pc is None:
            return False
        if key == "muster":
            return any(i.kind == "muster" for i in self.agenda)
        if key == "front":
            return bool(self.march_lands) and pc.realm >= FRONT_MIN_REALM \
                and pc.age >= FRONT_MIN_AGE
        if key == "hall":
            return bool(pc.sect) and pc.standing >= HALL_STANDING \
                and pc.resources >= HALL_COST
        if key == "master":
            return self.master_of(pc) is None and pc.realm < MAX_REALM
        return True

    def activity_refusal(self, key: str) -> str:
        if key == "front":
            return ("The marches take neither children nor "
                    f"{REALM_NAMES[1]} disciples.")
        if key == "hall":
            return (f"The hall opens at standing {HALL_STANDING} and costs "
                    f"{HALL_COST} silver a season.")
        if key == "master":
            return "You have a master already."
        return "There is no muster to join this year."

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
        # VII §5: a serious wound halves what a season is worth — the
        # season is spent whether or not the body was up to it.
        share = SEASON_RATE * WOUND_PAYOUT.get(a.play.wound, 1.0)
        carried = a.play.wound      # what they walked INTO the season with
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
        elif activity in PROFICIENCIES:
            self._act_train(a, activity, share)
        elif activity in PROFESSIONS:
            self._act_profession(a, activity, share)
        elif activity == "hall":
            self._act_hall(a, share)
        elif activity == "master":
            self._act_seek_master(a, share)
        elif activity == "front":
            if not self._take_front(a, forced=True, share=share):
                self.log(f"{a.display()} went looking for a place on the "
                         f"line and was turned back off the road; the "
                         f"marches take neither children nor "
                         f"{REALM_NAMES[1]} disciples.", [a])
        elif activity == "muster":
            if not self._take_service(a, forced=True, share=share):
                self.log(f"{a.display()} went looking for a muster to join; "
                         f"the levies were stood down and the season went "
                         f"nowhere.", [a])
        else:
            self._act_cultivate(a, share)
        # ... and a season spent quietly closes one level of it (VII §5) —
        # but never one taken THIS season: a fight you walked out of an hour
        # ago is not something the same three months also mended.
        if activity in WOUND_REST and a.play.wound and a.play.wound <= carried:
            self.heal_wound(a)

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
            cost = (" — a season's work is worth half until it closes"
                    if a.play.wound >= 2 else "")
            lines.append(f"  wounded ({WOUND_WORD[a.play.wound]}, "
                         f"{self.max_hp(a):.0f} of {ROUND_HP:.0f}){cost}")
        if a.play is not None and a.play.toxicity:
            over = (" — every further pill is a point of burden"
                    if a.play.toxicity >= PILL_TOXICITY_FREE else "")
            lines.append(f"  pills in the blood: toxicity "
                         f"{a.play.toxicity} of {PILL_TOXICITY_FREE}{over}")
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
        if self.march_lands and (self.is_march(a.home) or a.front_seasons):
            lines.append(f"  the {self.waste_word()} marches: the Waste is "
                         f"{self.threat_word()}")
        for notice in self.agenda_notices(season):
            lines.append(f"  * {notice}")
        return "\n".join(lines)

    def player_bag(self) -> str:
        """VII §11: what the played character is carrying — the crafts, the
        shelf, the rack, the toxicity, and (P7) the techniques."""
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
        # P5: the three tracks, with what the next rank still costs.
        prof = []
        for key, (label, _) in PROFICIENCIES.items():
            rank, done, need = self.track_progress(
                st.proficiencies.get(key, 0.0), PROFICIENCY_SHAPE)
            toward = (f" ({done:.1f}/{need:.0f} toward {rank + 1})"
                      if need else "")
            prof.append(f"{label} {rank}/"
                        f"{RANK_SHAPES[PROFICIENCY_SHAPE]['max']}"
                        f" — {PROFICIENCY_WORDS[rank]}{toward}")
        lines.append("  training: " + "; ".join(prof))
        if st.stances:
            lines.append("  stances: " + ", ".join(
                f"{k} {v}/{STANCE_RANK_MAX}"
                for k, v in sorted(st.stances.items())))
        # P6: the three crafts, and §8's wall where it has been hit.
        crafts = []
        top = RANK_SHAPES[PROFESSION_SHAPE]["max"]
        for key in PROFESSIONS:
            banked, done, need = self.track_progress(
                st.professions.get(key, 0.0), PROFESSION_SHAPE)
            if not banked and not done:
                continue
            shown = self.profession_rank(a, key)
            wall = (" — WALLED: it wants a teacher or a manual"
                    if shown < banked else "")
            toward = (f" ({done:.1f}/{need:.0f} toward {banked + 1})"
                      if need and not wall else "")
            crafts.append(f"{key} {shown}/{top} — "
                          f"{PROFESSION_WORDS[shown]}{toward}{wall}")
        if crafts:
            lines.append("  crafts: " + "; ".join(crafts))
        if st.manuals:
            lines.append("  manuals: " + ", ".join(sorted(st.manuals)))
        held = [f"{k} x{n}" for k, n in sorted(st.pills.items()) if n > 0]
        over = (" — over the line: every further pill is a point of burden"
                if st.toxicity >= PILL_TOXICITY_FREE else "")
        lines.append(f"  pills: {', '.join(held) or 'none'} | toxicity "
                     f"{st.toxicity} of {PILL_TOXICITY_FREE}{over}")
        if self.profession_rank(a, "alchemy"):
            lines.append(f"  the furnace is set up for {st.brew} pills "
                         f"('brew KIND' to change it)")
        if st.clarity:
            lines.append(f"  a clarity pill is in them: "
                         f"{st.clarity * 100:+.0f}% on the next tribulation")
        if st.gear:
            best = max(st.gear, key=lambda g: g["power"])
            spare = len(st.gear) - 1
            lines.append(f"  rack: carrying {best['what']} "
                         f"(+{best['power']} power)"
                         + (f", and {spare} more piece"
                            f"{'s' if spare != 1 else ''} to sell"
                            if spare else ""))
        lines.append("  techniques: none — the schools arrive with the next "
                     "session")
        master = self.master_of(a)
        if master is not None:
            lines.append(f"  master: {master.display()} "
                         f"({master.realm_name}) — a training season is "
                         f"worth x{MASTER_TEACHING:.1f} under them")
        # VII §5: the whole player-layer combat bonus, and the one clamp.
        terms = self.player_power_terms(a)
        raw = sum(v for _, v in terms)
        capped = self.player_power(a)
        detail = ", ".join(f"{k} +{v:.1f}" for k, v in terms) or "nothing yet"
        clip = " (CAPPED)" if raw > capped + 1e-9 else ""
        lines.append(f"  in a fight: {detail} = +{capped:.1f} power "
                     f"of a possible +{PLAYER_POWER_CAP:.0f}{clip}")
        lines.append(f"  body: {self.max_hp(a):.0f} of {ROUND_HP:.0f} "
                     f"({WOUND_WORD[st.wound]})")
        if a.front_seasons:
            lines.append(f"  the marches: {a.front_seasons} seasons on the "
                         f"line, {a.front_stands} incursions stood")
        orders = self.orders_of(a)
        lines.append(f"  orders: {orders['edge']} / {orders['manner']}, "
                     f"yield at {float(orders['yield']) * 100:.0f}%, "
                     f"{orders['execute']} the beaten, escape "
                     f"{orders['escape']} ('orders' for the card)")
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
        if a.front_seasons:
            stands = (f", and stood on the line through {a.front_stands} "
                      f"incursions" if a.front_stands else "")
            lines.append(f"  the marches: {a.front_seasons} seasons served "
                         f"(last Y{a.front_last}){stands}")
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
        if self.march_lands:
            names = ", ".join(m.name for m in self.march_lands)
            lines.append(f"  The Waste lies beyond the {self.waste_edge} "
                         f"edge: {names} are the march-lands, and the front "
                         f"there is {self.threat_word()}.")
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
        if self.is_march(land):
            eaten = [pl.name for _, pl in self.swallowed if pl.land is land]
            held = f"; the Waste holds {', '.join(eaten)}" if eaten else ""
            lines.append(f"  A march of the {self.waste_word()} Waste, "
                         f"which is {self.threat_word()}{held}.")
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
                march = (f"march of the {self.waste_word()} Waste, "
                         if self.is_march(land) else "")
                lines.append("")
                lines.append(f"  {land.name.upper()} — {seat}{march}"
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
                # §7: the scars. A swallowed settlement is never given back
                # and never drifts back, so it is named for as long as the
                # chronicle runs.
                eaten = [(y, pl) for y, pl in self.swallowed
                         if pl.land is land]
                if eaten:
                    named = ", ".join(f"{pl.name} (Y{y})" for y, pl in eaten)
                    lines.append(f"    The Waste holds {named}; nothing has "
                                 f"come back out of them.")
        wars = []
        for war in self.wars:
            att = self.polities.get(war.attacker)
            dfn = self.polities.get(war.defender)
            if att is None or dfn is None:
                continue
            wars.append(f"the {att.name} is {self.years_phrase(war.fought)} "
                        f"into a war on {dfn.domain}")
        lines.append("")
        if self.march_lands:
            names = ", ".join(m.name for m in self.march_lands)
            lines.append(f"    Beyond the {self.waste_word()} marches — "
                         f"{names} — lies the Waste, {self.threat_word()} "
                         f"this year.")
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


# Which of the kernel's questions come from inside a fight, and so want the
# exchanges so far put on screen before they are asked (VII §5).
FIGHT_ASKS = ("pause", "advantage", "execute", "edge", "manner")
PLAY_HELP = """Commands (play mode):
  <enter>            repeat last season's activity
  1-%d or NAME       this season's activity
  menu               show the activity menu again
  skip N doing X     keep doing X for up to %d seasons; the engine wakes you
                     the season BEFORE anything that matters to you
  agenda             what this year is known to hold
  bag                what you are carrying
  brew KIND          what the furnace is set up for: qi, healing, clarity
  take KIND          swallow a pill: qi, healing or clarity
  sell KIND | gear   sell a pill, or the worst piece off the rack
  orders             the standing orders card; `orders KEY VALUE` sets one
  pc / sheet NAME    a character sheet
  log NAME           a character's whole private history
  map / courts       the nine lands; every ruler and how they rule
  land NAME          one land's polities, rulers, edicts, prosperity
  roster / famous / obits
  help / quit
""" % (len(PLAYER_ACTIVITIES), TIMESKIP_CAP)


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
        # VII §5: the fight camera. Rounds are buffered rather than printed,
        # so that a bout which never has to ask the player anything can
        # collapse into the one chronicle line every other fight in the
        # world gets (VII §6).
        self.fight_lines: list = []
        self.fight_shown = False
        world.narrate = self.tell

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

    def tell(self, kind: str, text: str):
        """The kernel's fight camera (World.tell), one line per exchange."""
        if kind == "open":
            self.fight_lines = [text]
            self.fight_shown = False
        elif kind == "round":
            if self.fight_shown:
                print(text)
            else:
                self.fight_lines.append(text)

    def show_fight(self):
        """Something in the fight is about to ask the player a question: put
        the exchanges that led to it on screen first."""
        if self.fight_shown:
            return
        for line in self.fight_lines:
            print(line)
        self.fight_lines = []
        self.fight_shown = True

    def ask(self, kind: str, prompt: str, options: list, default: str) -> str:
        """The kernel's question hook (World.ask_player)."""
        if kind in FIGHT_ASKS:
            self.show_fight()
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
            lines.append(f" {mark}{i:>2}. {label:<24} {pays}")
        lines.append("   (a season pays a quarter of a year's work; "
                     "'skip N doing X' runs several)")
        return "\n".join(lines)

    def _available(self, key: str) -> bool:
        # The kernel owns the list of legal choices, so that the terminal
        # and the autopilot (VII §12) can never disagree about it.
        return self.world.activity_available(key)

    def _refusal(self, key: str) -> str:
        return self.world.activity_refusal(key)

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
                    print(self._refusal(act))
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
        elif low == "brew" or low.startswith("brew "):
            print(w.set_brew(cmd[4:].strip()))
        elif low == "take" or low.startswith("take "):
            # P6: swallowing a pill and selling a blade are not seasons, and
            # what they log is flushed at once so the player sees the price.
            said = w.take_pill(cmd[4:].strip())
            if said:
                print(said)
            self.flush_private(self.flush())
        elif low == "sell" or low.startswith("sell "):
            said = w.sell_item(cmd[4:].strip())
            if said:
                print(said)
            self.flush_private(self.flush())
        elif low == "orders" or low.startswith("orders "):
            parts = cmd.split(None, 2)
            if len(parts) == 1:
                print(w.orders_card(w.pc))
            else:
                print(w.set_order(w.pc, parts[1],
                                  parts[2] if len(parts) > 2 else ""))
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
            print(self._refusal(activity))
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
        self.fight_lines, self.fight_shown = [], False
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
            if reason is None and not self._available(self.skip_activity):
                # P5: a skip whose activity has stopped being legal — the
                # hall shut for want of silver, the muster stood down — is a
                # skip spending seasons on nothing. Wake, and ask again.
                reason = self._refusal(self.skip_activity).rstrip(".")
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


# ---------------------------------------------------------------------------
# --test-combat: the round model against the one roll (VII §5)
# ---------------------------------------------------------------------------
# Everything in the round model is CALIBRATED here rather than guessed: the
# stop lines, the swing band, the pause thresholds and the patience schedule
# are all read back out of this harness. It answers four questions:
#   1. does a fought bout win as often as the one roll says it should
#      (the invariant, within COMBAT_TEST_BAND);
#   2. does an even fight take the 3-8 rounds VII §5 asks for;
#   3. do the two resolutions kill and cripple at the same rates;
#   4. is that killing and crippling still ordered by edge.
COMBAT_TEST_BAND = 3.0          # percentage points; VII §5 and §12
COMBAT_TEST_ROUNDS = (3, 8)     # what an even fight should take
COMBAT_NEUTRAL = ["Stubborn", "Charming"]   # traits no stance table reads
# label, then each side as (realm, talent, qi) — or with P5's weapon rank
# and P6's forged gear appended, (realm, talent, qi, weapon, gear), the two
# tenants of the §5 cap — then the two stances. The edge the fight is
# called at is the harsher of the two.
COMBAT_CELLS = [
    ("even, Qi Refining",        (1, 5, 40), (1, 5, 40),
     ("duelling", None), ("duelling", None)),
    ("even, Core Formation",     (3, 5, 40), (3, 5, 40),
     ("duelling", None), ("duelling", None)),
    ("talent 9 vs 3",            (2, 9, 40), (2, 3, 40),
     ("duelling", None), ("duelling", None)),
    ("qi 95 vs 5",               (2, 5, 95), (2, 5, 5),
     ("duelling", None), ("duelling", None)),
    ("widest inside one realm",  (1, 10, 95), (1, 1, 0),
     ("duelling", None), ("duelling", None)),
    ("even, sparring",           (2, 5, 40), (2, 5, 40),
     ("sparring", None), ("sparring", None)),
    ("even, all-out",            (2, 5, 40), (2, 5, 40),
     ("allout", None), ("allout", None)),
    ("even, murderous",          (2, 5, 40), (2, 5, 40),
     ("murderous", None), ("murderous", None)),
    ("rage vs plain",            (2, 5, 40), (2, 5, 40),
     ("allout", "rage"), ("allout", None)),
    ("patience vs plain",        (2, 5, 40), (2, 5, 40),
     ("duelling", "patience"), ("duelling", None)),
    ("harmonious vs rage",       (2, 5, 40), (2, 5, 40),
     ("allout", "harmonious"), ("allout", "rage")),
    ("showy vs studying",        (2, 5, 40), (2, 5, 40),
     ("duelling", "showy"), ("duelling", "studying")),
    ("all-out vs duelling",      (2, 5, 40), (2, 5, 40),
     ("allout", None), ("duelling", None)),
    ("murderous vs merciful",    (3, 6, 60), (3, 4, 30),
     ("murderous", None), ("duelling", "merciful")),
    ("rage vs patience, Nascent", (4, 7, 70), (4, 5, 20),
     ("allout", "rage"), ("allout", "patience")),
    # P5: the +4 cap's only tenant so far. Both resolutions read
    # `player_power`, so a trained weapon must move the fought bout by
    # exactly as much as it moves the one roll and no more.
    ("weapon 5 vs untrained",    (2, 5, 40, 5), (2, 5, 40),
     ("duelling", None), ("duelling", None)),
    ("weapon 5, murderous",      (2, 5, 40, 5), (2, 5, 40),
     ("murderous", None), ("murderous", None)),
    # P6: the cap's second tenant. A master-forged piece is +2 power, and it
    # has to move the fought bout by exactly what it moves the one roll.
    ("forged +2 vs bare",        (2, 5, 40, 0, 2), (2, 5, 40),
     ("duelling", None), ("duelling", None)),
    ("weapon 5 and forged +2",   (2, 5, 40, 5, 2), (2, 5, 40),
     ("duelling", None), ("duelling", None)),
]


def _test_fighter(world: World, aid: int, name: str, played: bool) -> Agent:
    a = Agent(aid=aid, name=name, sect="", age=30, talent=5,
              traits=list(COMBAT_NEUTRAL))
    a.realm = 2
    if played:
        a.play = PlayerState()
        world._seed_orders(a)
    world.agents[aid] = a
    return a


def _seasons_for_rank(rank: int, shape: str) -> float:
    """The practice a given rank costs, for the harness and for anything
    else that has to put a character at a rank rather than earn one."""
    spec = RANK_SHAPES[shape]
    return sum(spec["step"] * (i + 1)
               for i in range(min(rank, spec["max"])))


def _test_reset(a: Agent, realm: int, talent: int, qi: float, weapon=0,
                gear=0, stances=(), wound=0, body=0):
    a.realm, a.talent, a.qi = realm, talent, float(qi)
    a.traits = list(COMBAT_NEUTRAL)
    a.alive = True
    a.epithets, a.rels, a.history, a.deeds = [], {}, [], []
    a.insight, a.burden, a.standing, a.karma = 0.0, 0, 1, 0
    a.resources, a.fortune = 0, 0
    a.death_year = a.death_cause = None
    if a.play is not None:
        a.play.wound = wound
        # A played fighter knows the stance the cell puts them in; an
        # untrained stance is a different measurement (VII §4), not this one.
        a.play.stances = {k: STANCE_NPC_RANK for k in stances if k}
        # P5: the ranks the cell asks for, and NOTHING carried over from the
        # last ten thousand fights — a bout drills the stance it was fought
        # in, and the harness must measure a fixed fighter.
        a.play.drills = {k: _seasons_for_rank(STANCE_NPC_RANK, "stance")
                         for k in stances if k}
        a.play.proficiencies = {
            "weapon": _seasons_for_rank(weapon, PROFICIENCY_SHAPE),
            "body": _seasons_for_rank(body, PROFICIENCY_SHAPE)}
        # P6: the rack, which the one roll and the fought bout must both
        # read out of `player_power` and neither out of anywhere else.
        a.play.gear = ([{"what": "a forged blade", "power": gear, "grade": 3}]
                       if gear else [])


def test_combat(seed=1, fights=10000) -> bool:
    """VII §5's Monte Carlo. Prints the whole table and returns pass/fail."""
    world = World(seed=seed, intake_size=8)
    world.round_combat = True
    att = _test_fighter(world, 900001, "Attacker", True)
    dfn = _test_fighter(world, 900002, "Defender", False)
    band = COMBAT_TEST_BAND
    print("=" * 72)
    print("--test-combat: the round model against the one roll (VII §5)")
    print(f"seed {seed}, {fights} fights a cell, invariant band {band:.1f}pp")
    print("=" * 72)
    print()
    print("THE INVARIANT — a fought bout against pa/(pa+pb)")
    print(f"  {'matchup':<28}{'stances':<26}{'one roll':>9}"
          f"{'fought':>8}{'delta':>9}")
    worst = 0.0
    rounds_by_edge: dict = {}
    for label, side_a, side_b, sa, sb in COMBAT_CELLS:
        _test_reset(att, *side_a, stances=sa)
        _test_reset(dfn, *side_b)
        want = world.duel_odds(att, dfn, sa, sb)
        wins = 0
        counts: list = []
        for _ in range(fights):
            _test_reset(att, *side_a, stances=sa)
            _test_reset(dfn, *side_b)
            bout = world._bout(att, dfn, sa, sb,
                               max((sa[0], sb[0]), key=EDGE_ORDER.index), "")
            wins += 1 if bout["winner"] is att else 0
            counts.append(bout["rounds"])
            rounds_by_edge.setdefault(bout["edge"], []).extend(
                [bout["rounds"]] if side_a == side_b else [])
        got = wins / fights
        delta = (got - want) * 100.0
        worst = max(worst, abs(delta))
        stances = f"{sa[0]}/{sa[1] or '-'} vs {sb[0]}/{sb[1] or '-'}"
        print(f"  {label:<28}{stances:<26}{want * 100:>8.1f}%"
              f"{got * 100:>7.1f}%{delta:>+8.2f}pp")
    invariant_ok = worst <= band
    print(f"  worst |delta| {worst:.2f}pp over {len(COMBAT_CELLS)} cells "
          f"-> {'PASS' if invariant_ok else 'FAIL'}")
    print()
    print(f"ROUND COUNTS, even fights only (target "
          f"{COMBAT_TEST_ROUNDS[0]}-{COMBAT_TEST_ROUNDS[1]})")
    print(f"  {'edge':<12}{'mean':>7}{'median':>8}{'p10':>6}{'p90':>6}"
          f"{'in band':>10}")
    rounds_ok = True
    for edge in EDGE_ORDER:
        counts = sorted(rounds_by_edge.get(edge, []))
        if not counts:
            continue
        n = len(counts)
        mean = sum(counts) / n
        med = counts[n // 2]
        p10, p90 = counts[int(n * 0.10)], counts[int(n * 0.90)]
        inband = sum(1 for c in counts
                     if COMBAT_TEST_ROUNDS[0] <= c <= COMBAT_TEST_ROUNDS[1])
        ok = COMBAT_TEST_ROUNDS[0] <= med <= COMBAT_TEST_ROUNDS[1]
        rounds_ok = rounds_ok and ok
        print(f"  {edge:<12}{mean:>7.1f}{med:>8}{p10:>6}{p90:>6}"
              f"{100.0 * inband / n:>9.0f}%  {'ok' if ok else 'OUT'}")
    print(f"  -> {'PASS' if rounds_ok else 'FAIL'} (median inside the band "
          f"at every edge)")
    print()
    # What a wound costs: outside the invariant on purpose (VII §5 — the
    # calibration is computed for two whole bodies, and the fight is run on
    # the real ones).
    # P5's Body proficiency is the same axis read the other way: the one
    # roll never hears about either, and at rank 5 a trained body is worth
    # about what a light wound costs. Both are printed together because
    # they are the same measurement.
    print("WHAT A BODY IS WORTH (even fight at duelling, the played side "
          "hurt or trained)")
    for label, wound, body in (("serious", 2, 0), ("light", 1, 0),
                               ("whole", 0, 0), ("Body 3", 0, 3),
                               ("Body 5", 0, 5)):
        wins = 0
        for _ in range(fights):
            _test_reset(att, 2, 5, 40, stances=("duelling",), wound=wound,
                        body=body)
            _test_reset(dfn, 2, 5, 40)
            bout = world._bout(att, dfn, ("duelling", None),
                               ("duelling", None), "duelling", "")
            wins += 1 if bout["winner"] is att else 0
        _test_reset(att, 2, 5, 40, stances=("duelling",), wound=wound,
                    body=body)
        print(f"  {label:<10} win {100.0 * wins / fights:>5.1f}%"
              f"   body {world.max_hp(att):.0f}")
    print()
    # The outcome chain: the same duel, resolved both ways.
    print(f"DEATH AND MAIM PER EDGE ({fights} duels an edge, both "
          f"resolutions)")
    print(f"  {'edge':<12}{'death 1-roll':>14}{'death rounds':>14}"
          f"{'maim 1-roll':>13}{'maim rounds':>13}")
    deaths: dict = {}
    maims: dict = {}
    for edge in EDGE_ORDER:
        for mode in ("roll", "rounds"):
            world.round_combat = (mode == "rounds")
            played, plain = (att, dfn)
            dead = hurt = 0
            for i in range(fights):
                _test_reset(played, 2, 5, 40, stances=(edge,))
                _test_reset(plain, 2, 5, 40)
                world._duel(played, plain, context="", edge=edge)
                dead += sum(1 for x in (played, plain) if not x.alive)
                hurt += sum(len(x.epithets) for x in (played, plain))
                if i % 500 == 0:
                    world.chronicle.clear()
                    world.obituaries.clear()
            deaths[(edge, mode)] = 100.0 * dead / fights
            maims[(edge, mode)] = 100.0 * hurt / fights
        print(f"  {edge:<12}{deaths[(edge, 'roll')]:>13.2f}%"
              f"{deaths[(edge, 'rounds')]:>13.2f}%"
              f"{maims[(edge, 'roll')]:>12.2f}%"
              f"{maims[(edge, 'rounds')]:>12.2f}%")
    world.round_combat = True
    spar_ok = (deaths[("sparring", "roll")] == 0
               == deaths[("sparring", "rounds")])
    duel_ok = max(deaths[("duelling", "roll")],
                  deaths[("duelling", "rounds")]) < 3.0
    maim_ok = all(maims[("sparring", m)] < maims[("duelling", m)]
                  < maims[("allout", m)] for m in ("roll", "rounds"))
    print(f"  sparring kills nobody: {'PASS' if spar_ok else 'FAIL'}; "
          f"duel accidents < 3%: {'PASS' if duel_ok else 'FAIL'}; "
          f"maim ordered sparring < duelling < all-out: "
          f"{'PASS' if maim_ok else 'FAIL'}")
    print()
    ok = invariant_ok and rounds_ok and spar_ok and duel_ok and maim_ok
    print(f"--test-combat: {'PASS' if ok else 'FAIL'}")
    return ok


class Autopilot:
    """VII §12: a random legal-choice hand at the season menu.

    Not a strategy and deliberately not one — it does not read the agenda,
    does not save for the hall, does not train what it fights in. It is the
    control group for the whole playable layer: whatever the menu is worth,
    it is worth it to somebody who is paying attention, and this one is not.
    """

    def __init__(self, world: World, seed: int):
        self.world = world
        self.rng = random.Random(seed)      # NEVER world.rng

    def choose(self) -> str:
        legal = [k for k in PLAYER_ACTIVITY_KEYS
                 if self.world.activity_available(k)]
        return self.rng.choice(legal) if legal else "cultivate"

    def ask(self, kind: str, prompt: str, options: list, default: str) -> str:
        """Every question the kernel can put to a player, answered by coin."""
        return self.rng.choice(list(options)) if options else default


def autopilot_run(world: World, years: int, bot_seed: int) -> Optional[Agent]:
    """Play a whole world with the bot at the menu. Returns the FIRST played
    character — the clean sample §12's funnel is read off — while the bot
    goes on playing whoever the chronicle turns to after them."""
    bot = Autopilot(world, bot_seed)
    first = world.begin_play(AUTOPILOT_NAME, ask=bot.ask)
    for _ in range(years):
        world.begin_year()
        for season in SEASONS:
            pc = world.pc
            if (pc is not None and pc.alive and pc.play is not None
                    and not pc.is_ruler()):
                world.player_season(bot.choose())
            world.run_season(season)
        world.end_year()
        if world.pc is not None and world.pc.play is None:
            world.take_over_pc()        # the bot picks the story back up
    return first


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
    p.add_argument("--test-combat", action="store_true",
                   help="run VII §5's combat harness (the round model "
                        "against the one roll) and print the table")
    p.add_argument("--autopilot", action="store_true",
                   help="play the PC with VII §12's random legal-choice bot "
                        "(with --years) and print the report")
    p.add_argument("--play", action="store_true",
                   help="play agent 65 of the starting intake, one season "
                        "at a time (VII: the playable layer)")
    p.add_argument("--follow-pc", action="store_true",
                   help="run until the main character reaches the peak, dies "
                        "or leaves the path, then print their whole life "
                        "(--years, if given, caps the run)")
    args = p.parse_args()

    if args.test_combat:
        sys.exit(0 if test_combat(seed=args.seed if args.seed is not None
                                  else 1) else 1)

    world = World(seed=args.seed, intake_size=args.intake)

    if args.autopilot:
        years = args.years if args.years is not None else 200
        hero = autopilot_run(world, years,
                             (args.seed or 0) + AUTOPILOT_SEED_OFFSET)
        if hero is not None:
            print(world.life_report(hero))
            print()
        print(world.final_report())
    elif args.play:
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
