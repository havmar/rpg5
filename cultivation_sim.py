#!/usr/bin/env python3
"""Cultivation World Simulator — toy version.

First-pass implementation of Part III of cultivation_sim_design.txt:
a uniform agent model, a yearly three-phase loop (action / events /
resolution), traits that weight actions, mutate under pressure and modify
outcomes, epithets, tournaments, expeditions, feuds, successions,
breakthroughs with real failure states, voluntary exits, and generations
via 8-year intakes.

Plus the first course of the politics layer (Part VI, session 1): the nine
lands on a 3x3 grid, a nested tree of places carrying prosperity, and
recruitment reach measured in geography. Every agent is born in a real
settlement; `map` shows the grid.

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
]

# JOB 1 — traits weight the yearly action choice (multipliers on base weights).
TRAIT_ACTION = {
    "Proud":     {"socialize": 1.3},
    "Cautious":  {"adventure": 0.5, "cultivate": 1.3},
    "Reckless":  {"adventure": 2.2, "seclude": 0.6},
    "Ruthless":  {"socialize": 1.2},
    "Loyal":     {"socialize": 1.2},
    "Vengeful":  {"socialize": 1.4},
    "Scholarly": {"cultivate": 1.4, "teach": 1.8},
    "Charming":  {"socialize": 1.8},
    "Stubborn":  {"cultivate": 1.3},
    "Ascetic":   {"seclude": 2.2, "socialize": 0.5},
    "Greedy":    {"adventure": 1.6},
    "Humble":    {"cultivate": 1.2},
    "Righteous": {"socialize": 1.1},
    "Cold":      {"seclude": 1.4, "socialize": 0.6},
    "Broken":    {"seclude": 1.7, "adventure": 0.5},
}

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
    rels: dict = field(default_factory=dict)     # aid -> Rel
    epithets: list = field(default_factory=list)
    history: list = field(default_factory=list)  # private log: (year, text)
    fortune: int = 0                  # streaky luck, clamped small
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
        self.sects = {name: richness for name, richness in SECT_SPECS}
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

        # The random main character.
        self.pc = r.choice(cohort)
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
        rel = holder.rels.get(target.aid)
        if rel and rel.kind in HOSTILE_KINDS:
            rel.intensity += amount
        else:
            holder.rels[target.aid] = Rel("grudge", amount)

    # -- logging ------------------------------------------------------------

    def log(self, text, actors, dramatic=False, world_event=False):
        """Record an event. Always private to actors; printed selectively."""
        for a in actors:
            a.history.append((self.year, text))

        tag = None
        pc = self.pc
        if world_event:
            tag = "world"
        if pc is not None:
            if any(a.aid == pc.aid for a in actors):
                tag = "PC"
            else:
                for a in actors:
                    rel = pc.rels.get(a.aid)
                    if rel is not None:
                        tag = REL_DISPLAY.get(rel.kind, rel.kind)
                        break
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
            act = self._pick_action(a)
            getattr(self, f"_act_{act}")(a)

    def _act_cultivate(self, a: Agent):
        a.qi = min(100, a.qi + (3 + a.talent * 0.9) * self.sects[a.sect])
        a.resources += 1

    def _act_seclude(self, a: Agent):
        a.qi = min(100, a.qi + 6 + a.talent * 1.2)
        # The world moves on: relationships decay.
        for rel in a.rels.values():
            if self.rng.random() < 0.3:
                rel.intensity = max(0, rel.intensity - 1)

    def _act_adventure(self, a: Agent):
        r = self.rng
        roll = r.random() - a.fortune * 0.02   # streaky luck bias
        if roll < 0.04 / a.realm:   # the wilds threaten the strong far less
            self.kill(a, "died on an adventure in the wilds")
        elif roll < 0.12:
            a.insight += 4
            a.burden += 1
            a.fortune = max(-3, a.fortune - 1)
            text = f"{a.display()} barely survived a brush with death in the wilds (+insight)."
            if r.random() < 0.4 and len(a.epithets) < 3:
                ep = r.choice([e for e in MAIM_EPITHETS if e not in a.epithets])
                a.epithets.append(ep)
                text += f" [epithet: {ep}]"
            self.log(text, [a], dramatic=True)
            self._mutate(a, "near_death")
        elif roll < 0.42:
            pass  # nothing found
        elif roll < 0.67:
            a.resources += r.randint(2, 6)
            a.fortune = min(3, a.fortune + 1)
        elif roll < 0.82:
            a.insight += 3
            a.history.append((self.year, "An epiphany on the road (+insight)."))
        elif roll < 0.92:
            a.resources += 8
            a.insight += 2
            a.fortune = min(3, a.fortune + 2)
            self.log(f"{a.display()} found a fortuitous treasure in a ruined "
                     f"cave.", [a], dramatic=(a.realm >= 3))
        else:
            others = [o for o in self.living()
                      if o.aid != a.aid and abs(o.realm - a.realm) <= 1]
            if others:
                o = r.choice(others)
                kind = "friend" if r.random() < 0.6 else "rival"
                self._bind(a, o, kind, 2)
                self.log(f"{a.display()} crossed paths with {o.display()} on "
                         f"the road; they parted as {kind}s.", [a, o])

    def _act_socialize(self, a: Agent):
        r = self.rng
        # A vengeful agent with a ripe grudge seeks the enemy.
        targets = [self.agents[i] for i, rel in a.rels.items()
                   if rel.kind in HOSTILE_KINDS and rel.intensity >= 3
                   and self.agents[i].alive]
        if targets and (a.has_trait("Vengeful") or a.has_trait("Ruthless")):
            t = max(targets, key=lambda x: a.rels[x.aid].intensity)
            if a.power() >= t.power() - 3:
                self._duel(a, t, lethal=True, context="a long-nursed grudge")
                return
        if a.has_trait("Proud") and r.random() < 0.25:
            peers = [o for o in self.living() if o.sect == a.sect
                     and o.realm == a.realm and o.aid != a.aid]
            if peers:
                self._duel(a, r.choice(peers), lethal=False,
                           context="a matter of face")
                return
        # Default: mingle.
        a.standing += 1 if r.random() < 0.5 else 0
        if r.random() < 0.3:
            peers = [o for o in self.living()
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
            juniors = [o for o in self.living() if o.sect == a.sect
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

    def _duel(self, att: Agent, dfn: Agent, lethal=False, context=""):
        """One formula, with the tyranny of realms."""
        r = self.rng
        gap = att.realm - dfn.realm
        ctx = f" over {context}" if context else ""

        if abs(gap) >= 1:
            strong, weak = (att, dfn) if gap > 0 else (dfn, att)
            flee = 0.5 + (0.25 if weak.has_trait("Cautious") else 0)
            if abs(gap) >= 2:
                flee -= 0.25
            if lethal and r.random() > flee:
                self.log(f"{strong.display()} struck down {weak.display()}"
                         f"{ctx} — a full realm between them left no contest.",
                         [strong, weak], dramatic=True)
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

        kill_chance = 0.0
        if lethal:
            kill_chance = 0.55
            if winner.has_trait("Ruthless"):
                kill_chance = 0.85
            if winner.has_trait("Righteous"):
                kill_chance = 0.25
        if r.random() < kill_chance:
            self.log(f"{winner.display()} defeated and slew {loser.display()}"
                     f"{ctx}.", [winner, loser], dramatic=True)
            self.kill(loser, f"slain in a duel by {winner.display()}",
                      killer=winner)
        else:
            loser.insight += 3
            self._add_grudge(loser, winner, 2)
            self.log(f"{winner.display()} defeated {loser.display()}{ctx}; "
                     f"{loser.display()} survives, shamed (+insight).",
                     [winner, loser])
            self._mutate(loser, "humiliated")

    # -- event phase --------------------------------------------------------

    def _event_phase(self):
        if self.year % TOURNAMENT_PERIOD == 0:
            self._tournament()
        if self.year >= self.next_expedition:
            self._expedition()
            self.next_expedition = self.year + self.rng.randint(4, 9)
        if self.feud_cooldown > 0:
            self.feud_cooldown -= 1
        else:
            self._maybe_feud()

    def _tournament(self):
        r = self.rng
        for realm in range(1, 5):
            band = [a for a in self.living()
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
            champ.resources += 4
            self._bind(champ, runner, "rival", 2)
            self.log(f"{champ.display()} won the {REALM_NAMES[realm]} "
                     f"tournament, defeating {runner.display()} in the final; "
                     f"a rivalry is born before the assembled sects.",
                     [champ, runner], dramatic=(realm >= 3))
            self._mutate(runner, "humiliated")

    def _expedition(self):
        r = self.rng
        pool = [a for a in self.living() if 14 <= a.age and a.realm <= 4]
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
            roll = r.random() - a.fortune * 0.02
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
                a.resources += r.randint(4, 10)
                a.fortune = min(3, a.fortune + 1)
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
        for a in self.living():
            for i, rel in a.rels.items():
                o = self.agents.get(i)
                if (o and rel.kind in HOSTILE_KINDS and o.sect != a.sect):
                    key = tuple(sorted((a.sect, o.sect)))
                    totals[key] = totals.get(key, 0) + rel.intensity
        for (s1, s2), total in totals.items():
            if total < FEUD_THRESHOLD:
                continue
            self.feud_cooldown = FEUD_COOLDOWN
            self.log(f"Accumulated grudges ignite a feud between {s1} "
                     f"and {s2}.", [], world_event=True)
            side1 = [a for a in self.living() if a.sect == s1]
            side2 = [a for a in self.living() if a.sect == s2]
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
        for a in list(self.living()):
            self._try_breakthrough(a)
        for a in list(self.living()):
            a.age += 1
            if a.age > a.lifespan:
                self.kill(a, f"died of old age at {a.age}, "
                             f"{a.realm_name} to the last")
                continue
            self._maybe_voluntary_exit(a)

    def _drift_prosperity(self):
        """Left alone, a settlement returns to its land's temper. Nothing
        pushes prosperity away from baseline yet — that is the rulers' job."""
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
            self.log(f"{a.display()} broke through to {a.realm_name} "
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
                o.history.append((self.year,
                                  f"Grieved the loss of {back.kind} "
                                  f"{a.display()} (+insight)."))
                if killer is not None and killer.alive:
                    self._add_grudge(o, killer, 3)
                    self._mutate(o, "betrayed")

        violent = killer is not None or "old age" not in cause
        obit = self._obituary(a)
        self.obituaries.append(obit)
        self.log(obit, [a], dramatic=violent or a.realm >= FAME_REALM)

        if was_head:
            self._succession(a.sect, a)
        else:
            self._update_sect_heads()

    def _obituary(self, a: Agent) -> str:
        grievers = [self.agents[i].display() for i, rel in a.rels.items()
                    if rel.kind in FRIENDLY_KINDS
                    and self.agents[i].alive][:3]
        celebrants = [o.display() for o in self.living()
                      if o.rels.get(a.aid)
                      and o.rels[a.aid].kind in HOSTILE_KINDS][:3]
        parts = [f"OBITUARY: {a.display()} of {a.sect}, dead at {a.age} "
                 f"({a.realm_name}); {a.death_cause}."]
        if grievers:
            parts.append(f"Grieved by {', '.join(grievers)}.")
        if celebrants:
            parts.append(f"Quietly celebrated by {', '.join(celebrants)}.")
        return " ".join(parts)

    # -- sect politics ------------------------------------------------------

    def _update_sect_heads(self):
        for sect in self.sects:
            members = [a for a in self.living() if a.sect == sect]
            if members:
                head = max(members, key=lambda x: (x.realm, x.standing))
                self.sect_heads[sect] = head.aid

    def _succession(self, sect: str, dead_head: Agent):
        r = self.rng
        members = [a for a in self.living() if a.sect == sect]
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

    # -- trait mutation (JOB 3) ---------------------------------------------

    def _mutate(self, a: Agent, trigger: str):
        r = self.rng
        if not a.alive or r.random() > 0.35:
            return
        swap = None
        if trigger == "humiliated" and a.has_trait("Proud"):
            swap = ("Proud", r.choice(["Humble", "Vengeful", "Broken"]))
        elif trigger == "betrayed" and a.has_trait("Loyal"):
            swap = ("Loyal", "Vengeful")
        elif trigger == "near_death":
            if a.has_trait("Reckless"):
                swap = ("Reckless", r.choice(["Cautious", "Ascetic"]))
            elif r.random() < 0.5 and "Ascetic" not in a.traits:
                a.traits.append("Ascetic")
                self.log(f"{a.display()} emerged changed: gained trait "
                         f"Ascetic.", [a])
                return
        if swap and swap[1] not in a.traits:
            a.traits.remove(swap[0])
            a.traits.append(swap[1])
            self.log(f"{a.display()} is changed: {swap[0]} -> {swap[1]}.",
                     [a])

    # -- PC handling --------------------------------------------------------

    def _succeed_pc(self):
        old = self.pc
        # Dump the fallen protagonist's full life into the chronicle record.
        candidates = [a for a in self.living() if a.age <= 30]
        if not candidates:
            candidates = self.living()
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
        return "\n".join([
            f"{a.display()} — {a.sect} [{alive}]",
            f"  home: {self.origin_line(a)}"
            + (f", {a.home.word()}" if a.home is not None else ""),
            f"  age {a.age} | realm {a.realm} ({a.realm_name}) | "
            f"qi {a.qi:.0f}/100",
            f"  talent {a.talent}/10 | insight {a.insight:.0f} | "
            f"burden {a.burden} | resources {a.resources} | "
            f"standing {a.standing}",
            f"  traits: {', '.join(a.traits)}",
            f"  epithets: {', '.join(a.epithets) if a.epithets else '-'}",
            f"  relationships: {self.describe_rels(a) or '-'}",
        ])

    def personal_log(self, a: Agent) -> str:
        lines = [f"PRIVATE HISTORY of {a.display()} ({a.sect}):"]
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
        if a.realm >= MAX_REALM:
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


def run_until_pc_resolved(world: World, cap_year: int, echo=True):
    """Step until the current protagonist reaches the peak, dies or quits.

    Returns the agent that was followed (the world may pick a successor PC
    on their death; this is the one whose story just ended).
    """
    hero = world.pc
    if hero is None:
        return None
    while hero.alive and hero.realm < MAX_REALM and world.year < cap_year:
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
