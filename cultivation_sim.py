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

Stdlib only. Python 3.9+.
"""

import argparse
import random
import sys
from dataclasses import dataclass, field
from typing import Optional

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

# Insight required to attempt the breakthrough OUT of each realm.
INSIGHT_REQ = {1: 10, 2: 22, 3: 38, 4: 58, 5: 85}

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
PROSPERITY_DRIFT = 0.2
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
HEIR_AGE = (20, 48)             # age of a courtier raised to a vacant seat
RULER_REALM2_CHANCE = 0.15      # a sovereign with a cultivator ancestor
RULER_RESOURCES = (6, 14)       # the treasury they sit on
RULER_STANDING = (5, 9)
# Court skew: thrones are not filled at random from the trait pool. The
# ambitious end up near seats, and so do the people willing to use one.
COURT_TRAIT_WEIGHTS = {"Power-Hungry": 3.0, "Proud": 2.5, "Righteous": 2.5,
                       "Cruel": 2.0, "Charming": 1.6, "Greedy": 1.5,
                       "Cold": 1.5, "Humble": 1.5, "Loyal": 1.5,
                       "Bully": 1.5, "Bloodthirsty": 1.5, "Ruthless": 1.3}

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
    "BENEVOLENT":   {"prosperity": 0.4,  "unrest": 0, "karma": 1,
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
NEGLECT_AGE_SCORE = 2           # absence (§5) — and a cultivator-king only
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
# A ruler doing the same thing for thirty years is not news every year: a
# facet writes a line when it is newly dominant, and only sometimes after.
RULE_LINE_REPEAT_CHANCE = 0.2
RULE_LINES = {
    "BENEVOLENT": [
        "{ruler} opened the granaries of {domain} through a hard winter.",
        "{ruler} cut the levies on {domain} and paid for the dikes out of "
        "the treasury.",
        "{ruler} heard petitions in person all year; the assessors of "
        "{domain} were whipped for false measures.",
        "{ruler} rebuilt the roads of {domain} and fed the work gangs at "
        "the crown's expense.",
    ],
    "EXTRACTIVE": [
        "{ruler} tripled the tax on herds and hearths; the villages of "
        "{domain} go hungry.",
        "{ruler} seized the salt trade of {domain} for the treasury.",
        "{ruler} sold the harvest of {domain} abroad and kept the silver.",
        "{ruler} set a new toll on every bridge and ford in {domain}.",
    ],
    "CRUEL": [
        "{ruler} answered the complaints of {domain} with the headsman.",
        "{ruler} burned a village of {domain} for a rumour of sedition.",
        "{ruler} hung the tax-defaulters of {domain} along the roads.",
        "{ruler} took hostages from every house of note in {domain}.",
    ],
    "NEGLECTFUL": [
        "{ruler} let the granaries of {domain} stand unrepaired another year.",
        "{ruler} read no petition out of {domain} all year.",
        "{ruler} kept to the inner court while the roads of {domain} washed "
        "out.",
    ],
    "CONSCRIPTION": [
        "{ruler} called up the levies of {domain}; the fields went unsown.",
        "{ruler} took one man in five from the villages of {domain} for the "
        "muster.",
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
]
RULE_MORTAL_LINES = [
    "{ruler} has held the seat of the {polity} for {years}.",
    "{ruler} completed {years} on the seat; {domain} has known no other "
    "hand for a generation.",
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
CLAIM_REALM_DAMP = 0.40         # per realm above the second: the higher a
                                # cultivator has climbed, the less a mortal
                                # seat is worth stepping off the path for
CLAIM_CHANCE_PER_POINT = 0.20
CLAIM_CHANCE_MAX = 0.8
CLAIM_CONTEST_CHANCE = 0.35     # two claims pressed at once
CLAIM_CONTEST_STANDING = 2
CLAIM_CONTEST_NOISE = 6.0

# INVITATION AND REFUSAL. A court left in disarray looks outside for a ruler
# and offers the seat to a famous or native cultivator — who is entirely free
# to refuse it, and often does. Refusals are remembered in the obituary.
INVITE_CHANCE = 0.18            # a heirless court looks outside at all
INVITE_UNREST = 4               # an unquiet one looks harder
INVITE_UNREST_BONUS = 0.18
INVITE_MIN_REALM = 2
INVITE_MIN_STANDING = 8
INVITE_NATIVE = 2.5
INVITE_FAMOUS = 2.0
INVITE_STANDING_WEIGHT = 0.4
INVITE_REFUSE_BASE = 0.45
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
ABDICATE_TRAIT_CHANCE = 0.004    # an Ascetic or Broken ruler
ABDICATE_TRAITS = ("Ascetic", "Broken")
ABDICATE_WEARY_AT = 0.80        # fraction of lifespan: old and weary
ABDICATE_WEARY_CHANCE = 0.014
ABDICATE_LONG_REIGN = 30
ABDICATE_LONG_CHANCE = 0.003
ABDICATE_CULTIVATOR_CHANCE = 0.002  # the mountain never stops calling
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
            "Walked the roads of the {land} for a year and came back with "
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
            "Spent the year at the fairs of {where} in the {land}; much "
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


# ---------------------------------------------------------------------------
# Places — the nested world tree
# ---------------------------------------------------------------------------

def prosperity_word(value: float) -> str:
    """Prosperity is reported in words, never numbers."""
    for ceiling, word in PROSPERITY_WORDS:
        if value < ceiling:
            return word
    return PROSPERITY_WORDS[-1][1]


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
# Agents
# ---------------------------------------------------------------------------

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
    past_reigns: list = field(default_factory=list)  # seats held and laid down
    thrones_refused: int = 0          # §4: offers turned down, for the obituary
    extraction_years: int = 0         # years of taking — the corruption clock
    karma: int = 0                    # §7: seeded from traits, moved by deeds
    defended: str = ""                # what they died in defence of, if any
    rels: dict = field(default_factory=dict)     # aid -> Rel
    epithets: list = field(default_factory=list)
    history: list = field(default_factory=list)  # private log: (year, text)
    fortune: int = 0                  # streaky luck, clamped small
    stipend_years: int = 0            # years the family at home has sent silver
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
        # Consequences (§9): the campaigns currently being fought.
        self.wars: list = []
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
                    dominant_land=None) -> Agent:
        r = self.rng
        sex = r.choice("mf")
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
        """Advance one year; return the chronicle lines it produced."""
        self._fresh_lines = []
        self.year += 1

        self._action_phase()
        self._event_phase()
        self._resolution_phase()

        if self.year % INTAKE_PERIOD == 0:
            self._recruit_intake()

        if self.pc is not None and not self.pc.alive:
            self._succeed_pc()

        return self._fresh_lines

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
        for a in list(self.living()):
            if a.age < 14 or not a.alive:
                continue
            if a.is_ruler():
                self._act_rule(a)       # §4: ruling replaces the action phase
                continue
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

    def _take_service(self, a: Agent) -> bool:
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
        if war is None and not ("CONSCRIPTION" in polity.last_facets
                                and a.has_trait("Bloodthirsty")):
            return False
        eager = min(1.0, self.war_volunteer_weight(a, polity)
                    / WAR_VOLUNTEER_FULL)
        if eager <= 0 or r.random() >= SERVICE_CHANCE * eager:
            return False
        pay = r.randint(*SERVICE_PAY)
        a.resources += pay + self._vice_spoils(a)
        a.standing += 1
        polity.army += 1
        leader = self.leader_of(polity)
        under = (f" under {self.ruler_ref(leader)}"
                 if leader is not None and leader.alive else "")
        if war is not None:
            other = self.polities.get(
                war.defender if war.attacker == polity.pid else war.attacker)
            war.enlisted.setdefault(polity.pid, []).append(a.aid)
            # No place= on this one, unlike the peacetime muster: a war
            # takes whole cohorts of natives at once, and a land's own
            # chronicle would be nothing else for three years running. The
            # muster is the country's news; who rode to it is each rider's.
            self.log(f"{a.display()} took the field with the armies of "
                     f"{polity.domain}{under} against "
                     f"{other.domain if other else 'the enemy'}.", [a])
            return True
        if r.random() < SERVICE_SKIRMISH:
            a.insight += SERVICE_INSIGHT
            self.log(f"{a.display()} rode with the levies of {polity.domain}"
                     f"{under} and spent the season killing along the border "
                     f"(+resources, +insight).", [a], place=a.home)
        else:
            self.log(f"{a.display()} took a captain's pay in the muster of "
                     f"{polity.domain}{under}; the levies drilled all year "
                     f"and marched nowhere (+resources).", [a], place=a.home)
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

    def _act_cultivate(self, a: Agent):
        a.qi = min(100, a.qi + (3 + a.talent * 0.9) * self.sects[a.sect])
        a.resources += 1

    def _act_seclude(self, a: Agent):
        a.qi = min(100, a.qi + 6 + a.talent * 1.2)
        # The world moves on: relationships decay.
        for rel in a.rels.values():
            if self.rng.random() < 0.3:
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

    def _act_adventure(self, a: Agent):
        r = self.rng
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
        if roll < 0.04 / a.realm:   # the wilds threaten the strong far less
            self.kill(a, scene("death"))
        elif roll < 0.12:
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
            a.resources += r.randint(2, 6) + self._vice_spoils(a)
            a.fortune = min(FORTUNE_CAP, a.fortune + 1)
            if condition == "rich" and r.random() < ADVENTURE_PATRON_CHANCE:
                a.standing += 1     # patrons and fairs make names
            a.history.append((self.year, scene("spoils")))
        elif roll < 0.82:
            a.insight += 3
            if condition == "harsh" and r.random() < ADVENTURE_RESCUE_CHANCE:
                # In a misruled land the insight is sometimes bought by a
                # deed, and a deed is worth writing down.
                a.karma += ADVENTURE_RESCUE_KARMA
                self.log(scene("rescue"), [a], place=where)
            else:
                a.history.append((self.year, scene("insight")))
        elif roll < 0.92:
            a.resources += 8 + self._vice_spoils(a)
            a.insight += 2
            a.fortune = min(FORTUNE_CAP, a.fortune + 2)
            self.log(scene("treasure"), [a], dramatic=(a.realm >= 3),
                     place=where)
        else:
            others = [o for o in self.cultivators()
                      if o.aid != a.aid and abs(o.realm - a.realm) <= 1]
            if others:
                o = r.choice(others)
                kind = "friend" if r.random() < 0.6 else "rival"
                self._bind(a, o, kind, 2)
                self.log(scene("meeting", other=o.display(), kind=kind),
                         [a, o], place=where)

    def _act_socialize(self, a: Agent):
        r = self.rng
        # A vengeful agent with a ripe grudge seeks the enemy. A grudge
        # against a RULER is not settled with a duel — that is a revolt or
        # an assassination (§9), and neither is settled with a duel.
        targets = [self.agents[i] for i, rel in a.rels.items()
                   if rel.kind in HOSTILE_KINDS and rel.intensity >= 3
                   and self.agents[i].alive and not self.agents[i].is_ruler()]
        if targets and (a.has_trait("Vengeful") or a.has_trait("Ruthless")):
            t = max(targets, key=lambda x: a.rels[x.aid].intensity)
            if a.power() >= t.power() - 3:
                self._duel(a, t, lethal=True, context="a long-nursed grudge")
                return
        # §7: a Bully fights only DOWNWARD — the tyranny of realms inverted.
        if a.has_trait("Bully") and r.random() < BULLY_CHANCE:
            if self._bully_shakedown(a):
                return
        # ... and Bloodthirsty goes looking for a fight with an equal, which
        # is the only kind that can actually kill them.
        if a.has_trait("Bloodthirsty") and r.random() < BLOODTHIRSTY_DUEL_CHANCE:
            peers = [o for o in self.cultivators()
                     if o.aid != a.aid and o.realm == a.realm and o.age >= 14]
            if peers:
                self._duel(a, r.choice(peers), lethal=True,
                           context="a quarrel picked for its own sake")
                return
        if a.has_trait("Proud") and r.random() < 0.25:
            peers = [o for o in self.cultivators() if o.sect == a.sect
                     and o.realm == a.realm and o.aid != a.aid]
            if peers:
                self._duel(a, r.choice(peers), lethal=False,
                           context="a matter of face")
                return
        # Default: mingle.
        a.standing += 1 if r.random() < 0.5 else 0
        if r.random() < 0.3:
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
                spared = ", spared where the next blow would have finished it"
            self.log(f"{winner.display()} defeated {loser.display()}{ctx}; "
                     f"{loser.display()} survives, shamed{spared} (+insight).",
                     [winner, loser])
            if winner.has_trait("Cruel") and r.random() < CRUEL_MAIM_CHANCE:
                self._maim(winner, loser, "the duel")
            self._mutate(loser, "humiliated")

    # -- event phase --------------------------------------------------------

    def _event_phase(self):
        self._politics_phase()
        self._war_phase()           # §9: campaigns first — they set at_war
        self._revolt_phase()
        self._maybe_assassinate()
        self._maybe_usurp()
        self._sect_year()           # §11: the head's character on the sect
        self._petition_phase()
        if self.year % TOURNAMENT_PERIOD == 0:
            self._tournament()
        if self.year >= self.next_expedition:
            self._expedition()
            self.next_expedition = self.year + self.rng.randint(4, 9)
        if self.feud_cooldown > 0:
            self.feud_cooldown -= 1
        else:
            self._maybe_feud()

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

    def _seat(self, polity: Polity, a: Agent):
        """Put a living agent on a throne.

        Everything else in the sim already routes around rulers — the action
        phase hands them the RULE action, and cultivators() keeps them out of
        tournaments, expeditions, petitions and the sect's own life — so this
        plus polity.leader is the whole transition.
        """
        a.ruling = polity.pid
        a.reign_start = self.year
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
                                  self.year, how))
        a.ruling = None
        a.reign_start = None

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

        rivals = [(a, w) for a, w in zip(pool, weights) if a is not claimant]
        if rivals and r.random() < CLAIM_CONTEST_CHANCE:
            other = r.choices([a for a, _ in rivals], [w for _, w in rivals])[0]

            def clout(x):
                return (x.realm * 8 + x.standing * CLAIM_CONTEST_STANDING
                        + r.uniform(0, CLAIM_CONTEST_NOISE)
                        + (4 if x.has_trait("Charming") else 0))

            winner, loser = ((claimant, other) if clout(claimant) >= clout(other)
                             else (other, claimant))
            self._seat(polity, winner)
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
        if r.random() < max(0.05, min(0.95, refuse)):
            guest.thrones_refused += 1
            self.log(f"The notables of {polity.domain} offered the seat of "
                     f"the {polity.name} to {guest.display()} of "
                     f"{guest.sect}, who refused it and went back to the "
                     f"mountain.", [guest], dramatic=True, place=polity.seat)
            return False
        self._seat(polity, guest)
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
        self._seat(polity, usurper)
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

    def _revolt_phase(self):
        """The valve unrest never had.

        Everything else in this layer pushes unrest up — cruelty, edicts,
        levies, a petition answered, a vassal's defiance — and until now only
        a funeral spent it, so bad courts simply pinned at the cap. Over the
        threshold, a country can rise in any year. Vassals rise as readily as
        sovereigns; only a sovereign's rising is world news (§12).
        """
        r = self.rng
        for polity in self.ruling_polities():
            if polity.unrest <= REVOLT_THRESHOLD:
                continue
            leader = self.leader_of(polity)
            if leader is None or not leader.alive:
                continue
            over = polity.unrest - REVOLT_THRESHOLD
            if r.random() < REVOLT_CHANCE_PER_UNREST * over:
                self._revolt(polity, leader)

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

    def _revolt(self, polity: Polity, leader: Agent):
        """One rising, settled by the tyranny of realms like everything else.

        A mortal tyrant falls to any Foundation Establishment champion. A
        cultivator-king does not fall at all — he turns the same rising into a
        massacre, and the country pays for having tried.
        """
        r = self.rng
        champion = self._revolt_champion(polity, leader)
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
                self._seat(polity, champion)
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

    def _war_phase(self):
        for war in list(self.wars):
            self._war_year(war)
        self._maybe_declare_war()

    def _maybe_declare_war(self):
        """§9: between edge-adjacent sovereigns, and rarely across a corner.

        Started by a restless ruler with an army to spend; a court left weak
        by a contested succession is what one of them looks at, and a vassal
        that has kept the tribute one year too many is the other.
        """
        r = self.rng
        if r.random() >= WAR_CHANCE:
            return
        busy = set()
        for war in self.wars:
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
            return
        attacker, defender, kind = r.choices(options, weights)[0]
        self._declare_war(attacker, defender, kind)

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

    def _petition_phase(self):
        """Starving villages beg the sects; the sects sometimes answer.

        This is the only door between the spiritual exemption and the secular
        world, so it is deliberately narrow: pleas lapse unheard, and at most
        one new one is sent a year.
        """
        self._lapse_petitions()
        for petition in list(self.petitions):
            self._maybe_answer_petition(petition)
        self._maybe_petition()

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

    def _maybe_answer_petition(self, petition: Petition):
        r = self.rng
        if r.random() >= PETITION_ANSWER_CHANCE:
            return
        polity = self.polities.get(petition.polity)
        ruler = self.leader_of(polity) if polity else None
        if ruler is not None and not ruler.alive:
            ruler = None
        agents, weights = self._petition_candidates(petition, ruler)
        if not agents:
            return
        hero = r.choices(agents, weights)[0]
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

    def _expedition(self):
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
            return
        k = min(len(pool), r.randint(6, 12))
        volunteers, seen = [], set()
        while len(volunteers) < k:
            a = r.choices(pool, weights)[0]
            if a.aid not in seen:
                seen.add(a.aid)
                volunteers.append(a)
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

    def _maybe_feud(self):
        r = self.rng
        totals: dict[tuple, int] = {}
        for a in self.cultivators():
            for i, rel in a.rels.items():
                o = self.agents.get(i)
                if (o and o.sect and rel.kind in HOSTILE_KINDS
                        and o.sect != a.sect):
                    key = tuple(sorted((a.sect, o.sect)))
                    totals[key] = totals.get(key, 0) + rel.intensity
        for (s1, s2), total in totals.items():
            if total < FEUD_THRESHOLD:
                continue
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
            break  # at most one feud per year

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
        """Left alone, a settlement returns to its land's temper. What drags
        it away from baseline is the rule style of whoever holds it."""
        for p in self.settlements():
            if p.prosperity < p.baseline:
                p.prosperity = min(p.baseline, p.prosperity + PROSPERITY_DRIFT)
            elif p.prosperity > p.baseline:
                p.prosperity = max(p.baseline, p.prosperity - PROSPERITY_DRIFT)

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
            parts = [f"OBITUARY: {self.ruler_ref(a)}, dead at {a.age} after "
                     f"{self.years_phrase(reign)} on the seat; "
                     f"{a.death_cause}."]
        else:
            of_sect = f" of {a.sect}" if a.sect else ""
            parts = [f"OBITUARY: {a.display()}{of_sect}, dead at {a.age} "
                     f"({a.realm_name}); {a.death_cause}."]
        if a.defended:
            parts.append(f"Died in defence of {a.defended}.")
        for name, domain, title, start, end, how in a.past_reigns:
            parts.append(f"Was {title} of {domain} for "
                         f"{self.years_phrase(end - start)}, and "
                         f"{how} the seat in Y{end}.")
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
            return True
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

    def _mutate(self, a: Agent, trigger: str, sure=False):
        """`sure` skips the usual gate: the caller has already rolled for it
        (POWER CORRUPTS carries its own, slower clock)."""
        r = self.rng
        if not a.alive or (not sure and r.random() > 0.35):
            return
        swap = None
        gain = None
        gained_by_the_seat = False
        if trigger == "power":
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
        if swap is not None:
            to = self._camera_filter(a, swap[1])
            if to in a.traits:
                return
            a.traits.remove(swap[0])
            a.traits.append(to)
            self.log(f"{self.ruler_ref(a)} is changed"
                     f"{' by the seat' if gained_by_the_seat else ''}: "
                     f"{swap[0]} -> {to}.", [a])
        elif gain is not None:
            to = self._camera_filter(a, gain)
            if to in a.traits:
                return
            a.traits.append(to)
            self.log(f"{self.ruler_ref(a)} is changed"
                     f"{' by the seat' if gained_by_the_seat else ''}: "
                     f"gained trait {to}.", [a])

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
                f"({self.years_phrase(self.reign_length(a))}), "
                f"{polity.style} rule, unrest {polity.unrest}, "
                f"{polity.domain} is {polity.word()} — no qi while it lasts")
        for name, domain, title, start, end, how in a.past_reigns:
            lines.append(f"  past reign: {title} of {domain} ({name}), "
                         f"Y{start}-Y{end} ({how} the seat)")
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

    def courts(self) -> str:
        """Every ruler: their polity, its type, this year's style, unrest."""
        lines = [f"THE COURTS — year {self.year}"]
        for sov in sorted(self.sovereigns(),
                          key=lambda p: (not p.land.is_center(), p.land.name)):
            lines.append(self._court_line(sov))
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
                 self.famous_list(), "", self.roster(), ""]
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


def main():
    p = argparse.ArgumentParser(
        description="Cultivation World Simulator (toy version)")
    p.add_argument("--years", type=int, default=None,
                   help="run N years non-interactively and print the report")
    p.add_argument("--seed", type=int, default=None,
                   help="RNG seed for a reproducible world")
    p.add_argument("--intake", type=int, default=INTAKE_SIZE,
                   help="students per intake cycle (default %(default)s)")
    p.add_argument("--follow-pc", action="store_true",
                   help="run until the main character reaches the peak, dies "
                        "or leaves the path, then print their whole life "
                        "(--years, if given, caps the run)")
    args = p.parse_args()

    world = World(seed=args.seed, intake_size=args.intake)

    if args.follow_pc:
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
