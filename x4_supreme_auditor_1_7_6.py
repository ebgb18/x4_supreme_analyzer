# ==============================================================================
# X4: Foundations (v8.0+) — Supreme Command & Empire Intelligence Terminal
# Version: V1.7.6 Enterprise — Precision Fleet & Dynamic Logistics Engine
# Zero external dependencies: 100% standard Python 3.8+ (expat, json, gzip, webbrowser)
# ==============================================================================

import os
import sys
import glob
import gzip
import re
import json
import html
import math
import argparse
import datetime
import webbrowser
from collections import defaultdict, Counter, deque
from xml.parsers import expat

# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================
DEFAULT_GAME_DIR = r"C:\Users\Austin\Documents\x4_data"

# Tactical engagement window (seconds)
COMBAT_ENGAGEMENT_WINDOW = 30.0

# Dynamic diplomacy threshold: relation <= -0.20 (<= -10 rep) triggers combat hostility
HOSTILITY_RELATION_THRESHOLD = -0.20

SIZE_BY_CLASS = {
    "ship_xl": "XL", "ship_l": "L", "ship_m": "M", "ship_s": "S", "ship_xs": "XS"
}
SIZES = ("XL", "L", "M", "S")

DEFAULT_FACTION_RELATIONS = {
    "xenon": -1.0,
    "khaak": -1.0
}

DEPLOYABLE_REGEX = re.compile(
    r"(drone|lasertower|mine_0|navbeacon|nav_beacon|satellite|resourceprobe|spacebomb|police|lifeboat)",
    re.IGNORECASE
)
REF_REGEX = re.compile(r"\{\s*(\d+)\s*,\s*(\d+)\s*\}")
SECTOR_REGEX = re.compile(r"cluster_(\d+)_sector_?(\d+)_macro", re.IGNORECASE)
ERLKING_VAULT_REGEX = re.compile(r"^landmarks_erlking_vault_\d+_macro$", re.IGNORECASE)
VAULT_REGEX = re.compile(r"^landmarks_(erlking_)?vault_\d+_macro$", re.IGNORECASE)

MODULE_CLASSES = {
    "production", "defencemodule", "habitation", "storage",
    "dockarea", "pier", "buildmodule", "connectionmodule", "radar"
}
GEAR_CLASSES = {
    "weapon", "turret", "missilelauncher", "missileturret", "shieldgenerator", "engine"
}

SOLID_WARES = {"ore", "silicon", "ice", "nividium", "rawscrap"}
LIQUID_WARES = {"hydrogen", "helium", "methane"}

BASE_COMBAT_WEIGHT = {
    "XL_BATTLESHIP": 2200, "XL_CARRIER": 1200, "XL_BUILDER": 60, "XL_RESUPPLIER": 100,
    "L_DESTROYER": 600, "L_CARRIER": 450, "L_FREIGHTER": 15, "L_MINER": 20,
    "M_GUNBOAT": 65, "M_CORVETTE": 55, "M_FRIGATE": 50, "M_BOMBER": 45,
    "M_FREIGHTER": 8, "M_MINER": 10, "S_HEAVYFIGHTER": 15, "S_FIGHTER": 10,
    "S_SCOUT": 4, "S_RACER": 4
}

ESTIMATED_HULL_VALUES = {
    "XL_BATTLESHIP": 185_000_000, "XL_CARRIER": 95_000_000, "XL_BUILDER": 32_000_000,
    "XL_RESUPPLIER": 40_000_000, "L_DESTROYER": 24_000_000, "L_CARRIER": 20_000_000,
    "L_FREIGHTER": 10_000_000, "L_MINER": 9_500_000, "M_GUNBOAT": 4_800_000,
    "M_CORVETTE": 5_200_000, "M_FRIGATE": 4_200_000, "M_BOMBER": 3_800_000,
    "M_FREIGHTER": 1_600_000, "M_MINER": 1_500_000, "S_HEAVYFIGHTER": 950_000,
    "S_FIGHTER": 750_000, "S_SCOUT": 350_000, "S_RACER": 300_000
}

AVERAGE_WARE_PRICES = {
    "energycells": 16.0, "ore": 50.0, "silicon": 110.0, "ice": 45.0,
    "hydrogen": 58.0, "helium": 44.0, "methane": 48.0, "nividium": 500.0,
    "refinedmetals": 140.0, "siliconwafers": 280.0, "graphene": 160.0, "hullparts": 272.0,
    "claytronics": 2100.0, "antimattercells": 180.0, "antimatterconverters": 350.0,
    "advancedcomposites": 550.0, "advancedelectronics": 1100.0, "computronicsubstrate": 9200.0,
    "metallicmicrolattice": 115.0, "siliconcarbide": 1150.0, "terranmre": 85.0,
    "foodrations": 75.0, "medicalsupplies": 60.0, "proteinpaste": 45.0, "water": 65.0,
    "spices": 42.0, "nostropoil": 80.0, "sojabeans": 62.0, "sojahusk": 160.0,
    "sunriseflowers": 40.0, "microchips": 950.0, "smartchips": 60.0, "quantumtubes": 340.0,
    "plasmaconductors": 1320.0, "shieldcomponents": 240.0, "turretcomponents": 260.0,
    "weaponcomponents": 220.0, "dronecomponents": 900.0, "fieldcoils": 420.0,
    "engineparts": 180.0, "missilecomponents": 12.0, "scanningarrays": 1150.0,
    "rawscrap": 100.0, "scrapmetal": 1120.0, "scruffinfruits": 42.0, "cheltmeat": 95.0,
    "bofu": 245.0, "boggas": 160.0, "plankton": 45.0, "meat": 65.0, "wheat": 38.0
}

HABITATION_CAPACITIES = {
    ("terran", "l"): 500, ("terran", "m"): 250, ("terran", "s"): 125,
    ("argon", "l"): 1000, ("argon", "m"): 500, ("argon", "s"): 250,
    ("teladi", "l"): 1000, ("teladi", "m"): 500, ("teladi", "s"): 250,
    ("paranid", "l"): 999, ("paranid", "m"): 666, ("paranid", "s"): 333,
    ("split", "l"): 1000, ("split", "m"): 500, ("split", "s"): 250,
    ("boron", "l"): 1000, ("boron", "m"): 500, ("boron", "s"): 250
}

SPECIES_DIET_RULES = {
    "terran": {"food": ("terranmre", 250.0), "meds": ("medicalsupplies", 125.0)},
    "argon": {"food": ("foodrations", 280.0), "meds": ("medicalsupplies", 125.0)},
    "teladi": {"food": ("nostropoil", 230.0), "meds": ("medicalsupplies", 125.0)},
    "paranid": {"food": ("sojahusk", 260.0), "meds": ("medicalsupplies", 125.0)},
    "split": {"food": ("scruffinfruits", 250.0), "meds": ("medicalsupplies", 125.0)},
    "boron": {"food": ("bofu", 240.0), "meds": ("medicalsupplies", 125.0)}
}

DEFAULT_CARGO_VOLUMES = {
    "XL": 80_000.0, "L": 38_000.0, "M": 8_200.0, "S": 1_200.0, "XS": 100.0
}

FALLBACK_PROD_CONSUMPTION = {
    ("computronicsubstrate", "default"): {"ore": 7200.0, "silicon": 7200.0, "hydrogen": 9000.0, "energycells": 12000.0},
    ("metallicmicrolattice", "default"): {"ore": 9600.0, "helium": 3200.0, "energycells": 4000.0},
    ("siliconcarbide", "default"): {"silicon": 4320.0, "methane": 4320.0, "energycells": 7200.0},
    ("refinedmetals", "default"): {"ore": 2880.0, "energycells": 2160.0},
    ("siliconwafers", "default"): {"silicon": 2880.0, "energycells": 2160.0},
    ("graphene", "default"): {"methane": 2880.0, "energycells": 1440.0},
    ("antimattercells", "default"): {"hydrogen": 3200.0, "energycells": 1600.0},
    ("water", "default"): {"ice": 3200.0, "energycells": 1600.0},
    ("hullparts", "default"): {"refinedmetals": 1120.0, "graphene": 160.0, "energycells": 320.0},
    ("claytronics", "default"): {"antimattercells": 400.0, "microchips": 640.0, "quantumtubes": 400.0, "energycells": 560.0},
    ("microchips", "default"): {"siliconwafers": 800.0, "energycells": 200.0},
    ("smartchips", "default"): {"siliconwafers": 160.0, "energycells": 200.0},
    ("advancedelectronics", "default"): {"microchips": 800.0, "quantumtubes": 400.0, "energycells": 200.0},
    ("medicalsupplies", "terran"): {"proteinpaste": 1200.0, "ice": 600.0, "energycells": 600.0},
    ("medicalsupplies", "default"): {"spices": 800.0, "water": 1200.0, "wheat": 600.0, "energycells": 600.0},
    ("terranmre", "default"): {"proteinpaste": 1200.0, "ice": 600.0, "energycells": 600.0},
    ("proteinpaste", "default"): {"ice": 1600.0, "methane": 800.0, "energycells": 800.0},
    ("stimulants", "default"): {"spices": 400.0, "silicon": 400.0, "energycells": 800.0}
}

BUILTIN_SECTORS = {
    (1, 1): "Grand Exchange I", (1, 2): "Grand Exchange III", (1, 3): "Grand Exchange IV",
    (2, 1): "Black Hole Sun IV", (2, 2): "Black Hole Sun V",
    (3, 1): "Second Contact II Flashpoint", (3, 2): "Second Contact VII", (3, 3): "Second Contact XI",
    (4, 1): "Nopileos' Fortune II", (4, 2): "Nopileos' Fortune VI",
    (5, 1): "Hatikvah's Choice I", (5, 2): "Hatikvah's Choice III",
    (6, 1): "Silent Witness I", (6, 2): "Silent Witness XI", (6, 3): "Silent Witness XII",
    (7, 1): "Ianamus Zura IV", (7, 2): "Ianamus Zura VII", (8, 1): "Eighteen Billion",
    (9, 1): "Hewa's Twin I", (9, 2): "Hewa's Twin II", (9, 3): "Hewa's Twin III", (9, 4): "Hewa's Twin IV",
    (10, 1): "Trinity Sanctum III", (10, 2): "Trinity Sanctum VII",
    (11, 1): "Pontifex's Claim", (12, 1): "Holy Vision", (13, 1): "True Sight",
    (14, 1): "Pious Mists II", (14, 2): "Pious Mists IV", (14, 3): "Pious Mists XI",
    (15, 1): "Morning Star III", (15, 2): "Morning Star IV",
    (16, 1): "Argon Prime", (17, 1): "Antigone Memorial",
    (18, 1): "Faulty Logic I", (18, 2): "Faulty Logic VII",
    (19, 1): "Atiya's Misfortune I", (19, 2): "Atiya's Misfortune III",
    (20, 1): "Company Regard", (21, 1): "Scale Plate Green I", (21, 2): "Scale Plate Green VII",
    (23, 1): "Sacred Relic", (26, 1): "Tharka's Cascade XV", (26, 2): "Tharka's Cascade XVII",
    (27, 1): "The Void", (28, 1): "Frontier Edge", (29, 1): "Memory of Profit IX", (29, 2): "Memory of Profit X",
    (30, 1): "Profit Center Alpha", (31, 1): "Heretic's End",
    (32, 1): "Matrix #79B", (33, 1): "Matrix #451", (34, 1): "Matrix #598",
    (35, 1): "Turquoise Sea IX", (35, 2): "Turquoise Sea X",
    (48, 1): "Getsu Fune", (100, 1): "Asteroid Belt",
    (101, 1): "Mars", (102, 1): "Venus", (104, 1): "Jupiter", (106, 1): "Mercury",
    (107, 1): "Earth", (108, 1): "The Moon", (109, 1): "Titan",
    (110, 1): "Saturn I", (110, 2): "Saturn II", (111, 1): "Uranus",
    (112, 1): "Savage Spur I", (112, 2): "Savage Spur II", (113, 1): "Oort Cloud", (114, 1): "Pluto",
    (400, 1): "Zyarth's Dominion I", (400, 2): "Zyarth's Dominion X",
    (401, 1): "Family Zhin", (401, 2): "Family Kritt", (402, 1): "Heart of Acrimony II",
    (403, 1): "Family Nhuut", (403, 2): "Family Tkr",
    (404, 1): "Guiding Star V", (404, 2): "Guiding Star VII",
    (405, 1): "Wretched Skies IV", (405, 2): "Wretched Skies V", (405, 3): "Wretched Skies X",
    (406, 1): "Tharka's Ravine XVI", (406, 2): "Tharka's Ravine XXIV",
    (408, 1): "Family Valka", (409, 1): "Fires of Defeat",
    (410, 1): "Open Market", (411, 1): "Two Grand",
    (500, 1): "Avarice I", (500, 2): "Avarice V: Dead End", (500, 3): "Avarice IV",
    (501, 1): "Windfall I Union Summit", (502, 1): "Windfall III The Hoard",
    (503, 1): "Windfall IV Aurora's Dream", (504, 1): "Leap of Faith",
    (601, 1): "Kingdom End I", (602, 1): "Barren Shores",
    (603, 1): "Sanctuary of Darkness", (604, 1): "Great Reef",
    (605, 1): "Ocean of Fantasy", (606, 1): "Menelaus' Oasis",
    (607, 1): "Rolk's Demise", (608, 1): "Watchful Gaze", (609, 1): "Atreus' Clouds",
    (705, 1): "Savage Spur II", (705, 2): "Savage Spur I",
    (710, 1): "Hatikvah's Faith", (711, 1): "Nopileos' Memorial",
    (712, 1): "Matrix #101", (715, 1): "President's End",
    (724, 1): "Circle of Deceit", (724, 2): "Segaris",
    (725, 1): "Brennan's Triumph", (726, 1): "Gaian Prophecy"
}

BUILTIN_SHIP_NAMES = {
    "ship_atf_xl_battleship_01_a_macro": "Asgard", "ship_pir_xl_battleship_01_a_macro": "Erlking",
    "ship_spl_xl_battleship_01_a_macro": "Raptor", "ship_spl_xl_carrier_01_a_macro": "Raptor",
    "ship_arg_xl_carrier_01_a_macro": "Colossus Vanguard", "ship_arg_xl_carrier_01_b_macro": "Colossus Sentinel",
    "ship_arg_xl_carrier_02_a_macro": "Colossus E", "ship_par_xl_carrier_01_a_macro": "Zeus Vanguard",
    "ship_par_xl_carrier_01_b_macro": "Zeus Sentinel", "ship_par_xl_carrier_02_a_macro": "Zeus E",
    "ship_tel_xl_carrier_01_a_macro": "Condor Vanguard", "ship_tel_xl_carrier_01_b_macro": "Condor Sentinel",
    "ship_tel_xl_carrier_02_a_macro": "Condor E", "ship_ter_xl_carrier_01_a_macro": "Tokyo",
    "ship_bor_xl_carrier_01_a_macro": "Shark", "ship_bor_l_carrier_01_a_macro": "Guppy",
    "ship_par_xl_builder_01_a_macro": "Heracles Vanguard", "ship_par_xl_builder_01_b_macro": "Heracles Sentinel",
    "ship_arg_xl_builder_01_a_macro": "Mammoth Vanguard", "ship_arg_xl_builder_01_b_macro": "Mammoth Sentinel",
    "ship_tel_xl_builder_01_a_macro": "Albatross Vanguard", "ship_tel_xl_builder_01_b_macro": "Albatross Sentinel",
    "ship_ter_xl_builder_01_a_macro": "Kyushu", "ship_bor_xl_builder_01_a_macro": "Walrus",
    "ship_atf_l_destroyer_01_a_macro": "Syn", "ship_ter_l_destroyer_01_a_macro": "Osaka",
    "ship_arg_l_destroyer_01_a_macro": "Behemoth Vanguard", "ship_arg_l_destroyer_01_b_macro": "Behemoth Sentinel",
    "ship_arg_l_destroyer_02_a_macro": "Behemoth E", "ship_par_l_destroyer_01_a_macro": "Odysseus Vanguard",
    "ship_par_l_destroyer_01_b_macro": "Odysseus Sentinel", "ship_par_l_destroyer_02_a_macro": "Odysseus E",
    "ship_tel_l_destroyer_01_a_macro": "Phoenix Vanguard", "ship_tel_l_destroyer_01_b_macro": "Phoenix Sentinel",
    "ship_tel_l_destroyer_02_a_macro": "Phoenix E", "ship_bor_l_destroyer_01_a_macro": "Ray",
    "ship_spl_l_destroyer_01_a_macro": "Rattlesnake", "ship_ter_l_flag01_a_macro": "Sapporo",
    "ship_par_l_trans_container_03_a_macro": "Helios E", "ship_par_l_trans_container_01_a_macro": "Helios Vanguard",
    "ship_par_l_trans_container_01_b_macro": "Helios Sentinel", "ship_arg_l_trans_container_01_a_macro": "Shuyaku Vanguard",
    "ship_arg_l_trans_container_03_b_macro": "Incarcatura Sentinel", "ship_par_m_trans_container_01_a_macro": "Demeter Vanguard",
    "ship_spl_m_trans_container_01_a_macro": "Boa", "ship_ter_m_trans_container_01_a_macro": "Baldric",
    "ship_arg_m_trans_container_01_a_macro": "Mercury Vanguard", "ship_arg_l_miner_solid_01_a_macro": "Magnetar Vanguard (Mineral)",
    "ship_arg_l_miner_solid_01_b_macro": "Magnetar Sentinel (Mineral)", "ship_arg_l_miner_liquid_01_a_macro": "Magnetar Vanguard (Gas)",
    "ship_arg_l_miner_liquid_01_b_macro": "Magnetar Sentinel (Gas)", "ship_tel_l_miner_solid_02_a_macro": "Crane E (Mineral)",
    "ship_tel_l_miner_liquid_02_a_macro": "Crane E (Gas)", "ship_par_l_miner_solid_01_a_macro": "Chthonios Vanguard (Mineral)",
    "ship_par_l_miner_solid_01_b_macro": "Chthonios Sentinel (Mineral)", "ship_par_l_miner_liquid_01_a_macro": "Chthonios Vanguard (Gas)",
    "ship_ter_m_miner_solid_01_a_macro": "Bolo (Mineral)", "ship_ter_m_miner_liquid_01_a_macro": "Bolo (Gas)",
    "ship_arg_m_miner_solid_01_a_macro": "Drill Vanguard (Mineral)", "ship_bor_s_miner_solid_01_story_macro": "Plurima",
    "ship_ter_m_gunboat_01_a_macro": "Jian", "ship_bor_m_gunboat_01_a_macro": "Thresher",
    "ship_ter_m_corvette_01_a_macro": "Katana", "ship_ter_m_corvette_02_a_macro": "Odachi",
    "ship_par_m_corvette_01_a_macro": "Nemesis Vanguard", "ship_par_m_corvette_01_b_macro": "Nemesis Sentinel",
    "ship_spl_m_corvette_01_a_macro": "Dragon", "ship_spl_m_corvette_02_a_macro": "Dragon Raider",
    "ship_spl_m_frigate_01_a_macro": "Cobra", "ship_bor_m_corvette_01_a_macro": "Hydra",
    "ship_tel_m_bomber_01_a_macro": "Peregrine Vanguard", "ship_tel_m_bomber_01_b_macro": "Peregrine Sentinel",
    "ship_tel_m_frigate_01_a_macro": "Osprey Vanguard", "ship_par_s_heavyfighter_01_a_macro": "Ares",
    "ship_arg_s_fighter_01_a_macro": "Buster Vanguard", "ship_arg_s_fighter_02_a_macro": "Eclipse Vanguard",
    "ship_ter_s_fighter_01_a_macro": "Gladius", "ship_ter_s_fighter_02_a_macro": "Kukri",
    "ship_ter_s_fighter_04_a_macro": "Takoba", "ship_spl_s_fighter_01_a_macro": "Jaguar",
    "ship_spl_s_fighter_02_a_macro": "Asp", "ship_spl_s_heavyfighter_01_a_macro": "Chimera",
    "ship_spl_s_heavyfighter_02_a_macro": "Balaur", "ship_gen_s_racer_01_a_macro": "Dart",
    "ship_par_s_racer_01_a_macro": "Theseus Sport", "ship_arg_s_racer_01_a_macro": "Pleiades",
    "ship_tel_s_racer_01_a_macro": "Sparrow", "ship_xen_xl_carrier_01_a_macro": "Xenon I (Dreadnought)",
    "ship_xen_xl_destroyer_01_a_macro": "Xenon K (Destroyer)", "ship_xen_l_destroyer_01_a_macro": "Xenon H (Cruiser)",
    "ship_xen_l_terraformer_01_a_macro": "Xenon H (Terraformer)", "ship_xen_m_corvette_01_a_macro": "Xenon P (Corvette)",
    "ship_xen_m_corvette_02_a_macro": "Xenon PE (Heavy Corvette)", "ship_xen_s_heavyfighter_01_a_macro": "Xenon M (Heavy Fighter)",
    "ship_xen_s_fighter_01_a_macro": "Xenon F (Interceptor)", "ship_xen_s_scout_01_a_macro": "Xenon N (Scout)"
}

BUILTIN_WARE_NAMES = {
    "energycells": "Energy Cells", "ore": "Ore", "silicon": "Silicon", "ice": "Ice",
    "hydrogen": "Hydrogen", "helium": "Helium", "methane": "Methane", "nividium": "Nividium",
    "graphene": "Graphene", "refinedmetals": "Refined Metals", "hullparts": "Hull Parts",
    "claytronics": "Claytronics", "antimattercells": "Antimatter Cells",
    "antimatterconverters": "Antimatter Converters", "advancedcomposites": "Advanced Composites",
    "advancedelectronics": "Advanced Electronics", "computronicsubstrate": "Computronic Substrate",
    "dronecomponents": "Drone Components", "engineparts": "Engine Parts", "fieldcoils": "Field Coils",
    "microchips": "Microchips", "missilecomponents": "Missile Components",
    "plasmaconductors": "Plasma Conductors", "quantumtubes": "Quantum Tubes",
    "scanningarrays": "Scanning Arrays", "shieldcomponents": "Shield Components",
    "smartchips": "Smart Chips", "turretcomponents": "Turret Components",
    "weaponcomponents": "Weapon Components", "siliconwafers": "Silicon Wafers",
    "metallicmicrolattice": "Metallic Microlattice", "siliconcarbide": "Silicon Carbide",
    "terranmre": "Terran MRE", "foodrations": "Food Rations", "medicalsupplies": "Medical Supplies",
    "proteinpaste": "Protein Paste", "water": "Water", "spices": "Spices",
    "nostropoil": "Nostrop Oil", "sojabeans": "Soja Beans", "sojahusk": "Soja Husk",
    "sunriseflowers": "Sunrise Flowers", "majadust": "Maja Dust", "spacefuel": "Space Fuel",
    "spaceweed": "Space Weed", "stimulants": "Stimulants", "teladianium": "Teladianium",
    "rawscrap": "Raw Scrap", "scrapmetal": "Scrap Metal", "scruffinfruits": "Scruffin Fruits",
    "cheltmeat": "Chelt Meat", "bofu": "BoFu", "boggas": "BoGas"
}

BUILTIN_WARE_VOLUMES = {
    "energycells": 1.0, "ore": 10.0, "silicon": 18.0, "ice": 8.0,
    "hydrogen": 6.0, "helium": 6.0, "methane": 6.0, "nividium": 10.0,
    "rawscrap": 1.0, "scrapmetal": 2.0, "computronicsubstrate": 40.0,
    "metallicmicrolattice": 2.0, "siliconcarbide": 18.0, "terranmre": 1.0,
    "proteinpaste": 2.0, "stimulants": 1.0, "medicalsupplies": 2.0,
    "refinedmetals": 14.0, "graphene": 20.0, "hullparts": 12.0,
    "claytronics": 20.0, "antimattercells": 18.0, "antimatterconverters": 12.0,
    "advancedcomposites": 16.0, "advancedelectronics": 22.0, "dronecomponents": 14.0,
    "engineparts": 10.0, "fieldcoils": 12.0, "microchips": 22.0,
    "missilecomponents": 4.0, "plasmaconductors": 32.0, "quantumtubes": 22.0,
    "scanningarrays": 38.0, "shieldcomponents": 10.0, "smartchips": 2.0,
    "turretcomponents": 20.0, "weaponcomponents": 20.0, "siliconwafers": 18.0,
    "water": 6.0, "spices": 3.0, "nostropoil": 6.0, "sojabeans": 5.0,
    "sojahusk": 7.0, "sunriseflowers": 6.0, "majadust": 1.0, "spacefuel": 2.0,
    "spaceweed": 3.0, "scruffinfruits": 4.0, "cheltmeat": 6.0, "bofu": 12.0
}

CODE_REGEX = re.compile(r"\b([A-Z]{3}-\d{3})\b")
HEX_ID_REGEX = re.compile(r"\[(0x[0-9a-fA-F]+)\]")

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================
def prettify(token):
    return re.sub(r"[_]+", " ", str(token)).strip().title()

def esc(s):
    return html.escape(str(s).replace("|", "/").replace("\n", " ").strip())

def num(n):
    return f"{int(round(float(n))):,}"

def classify_ship(macro, cls):
    m = macro.lower()
    size = SIZE_BY_CLASS.get(cls, "?")
    if "builder" in m: return "Builder (Civilian)", "Civilian", "XL_BUILDER"
    if "resupplier" in m: return "Resupply Auxiliary", "Civilian", "XL_RESUPPLIER"
    if "miner" in m:
        t = "Gas" if "liquid" in m else "Mineral"
        w_key = f"{size}_MINER" if f"{size}_MINER" in BASE_COMBAT_WEIGHT else "M_MINER"
        return f"{t} Miner ({size})", "Miner", w_key
    if "trans" in m or "courier" in m:
        kind = "Container" if "container" in m else ("Solid" if "solid" in m else ("Liquid" if "liquid" in m else "Freight"))
        w_key = f"{size}_FREIGHTER" if f"{size}_FREIGHTER" in BASE_COMBAT_WEIGHT else "M_FREIGHTER"
        return f"Freighter ({kind}, {size})", "Trader", w_key
    if re.search(r"_tug_|_tug$", m): return "Salvage Tug", "Civilian", "M_FREIGHTER"
    if "scout" in m or "racer" in m: return "Scout / Courier", "Civilian", "S_SCOUT"

    for tok, name, weight in (
        ("battleship", "Battleship", "XL_BATTLESHIP"),
        ("carrier", "Carrier", f"{size}_CARRIER" if size in ("XL", "L") else "L_CARRIER"),
        ("destroyer", "Destroyer", "L_DESTROYER"),
        ("flag", "Flagship Cruiser", "L_DESTROYER"),
        ("gunboat", "Gunboat", "M_GUNBOAT"),
        ("corvette", "Corvette", "M_CORVETTE"),
        ("frigate", "Frigate", "M_FRIGATE"),
        ("bomber", "Bomber", "M_BOMBER"),
        ("heavyfighter", "Heavy Fighter", "S_HEAVYFIGHTER"),
        ("fighter", "Interceptor", "S_FIGHTER")
    ):
        if tok in m: return name, "Military", weight

    if size in ("XL", "L"):
        return f"Heavy Combatant ({size})", "Military", f"{size}_DESTROYER" if size == "L" else "XL_BATTLESHIP"
    return "Auxiliary Vessel", "Civilian", "M_FREIGHTER"

def gear_parts(macro):
    t = macro.lower().replace("_macro", "").split("_")
    size = t[2].upper() if len(t) > 2 and t[2].lower() in ("xs", "s", "m", "l", "xl") else "?"
    typ = t[3] if len(t) > 3 else (t[1] if len(t) > 1 else "?")
    return size, typ

def gear_category(macro):
    m = macro.lower()
    if "plasma" in m: return "Plasma Battery"
    if "beam" in m: return "Beam Emitter"
    if "pulse" in m: return "Pulse Laser"
    if "flak" in m: return "Flak Cannon"
    if "bolt" in m: return "Bolt Repeater"
    if "shard" in m: return "Shard Battery"
    if "torpedo" in m: return "Torpedo Launcher"
    if "missile" in m: return "Missile Turret"
    if "railgun" in m: return "Railgun"
    if "gatling" in m: return "Gatling Cannon"
    return "Standard Weapon"

def ammo_class(macro):
    m = macro.lower().replace("_macro", "")
    t = m.split("_")
    if m.startswith("missile_"): return "Missiles", f"{t[1].title()} ({t[2].title()})" if len(t) > 2 else t[1].title()
    if m.startswith("countermeasure"): return "Countermeasures", "Flares"
    if "mine" in m and m.startswith(("weapon_", "mine")): return "Mines", prettify(m)
    if "lasertower" in m: return "Laser Towers", "XS" if "_xs_" in m else "S"
    if "nav_beacon" in m or "navbeacon" in m: return "Nav Beacons", "Beacon"
    if "satellite" in m: return "Satellites", "Advanced" if m.endswith("_02") else "Basic"
    if "resourceprobe" in m: return "Resource Probes", "Probe"
    if "drone" in m: return "Drones", prettify(t[-3] if len(t) > 3 else m)
    if "police" in m: return "Police Craft", "Police"
    return "Other", prettify(m)

# ==============================================================================
# GAME DATA LOADER & NAMER
# ==============================================================================
class GameData:
    def __init__(self, game_dir):
        self.dir = game_dir
        self.index, self.sources, self.text = {}, [], {}
        self.wares, self.ware_volumes, self.ware_recipes, self.sector_name_tags = {}, {}, {}, {}
        self.macro_cache, self.ok = {}, False
        if game_dir and os.path.isdir(game_dir):
            self._build()

    def _index_folder(self, src, folder):
        if not os.path.isdir(folder): return
        self.sources.append((src, folder))
        try:
            cats = sorted(f for f in os.listdir(folder) if f.endswith(".cat") and "_sig" not in f)
        except OSError: return
        for c in cats:
            dat = os.path.join(folder, c[:-4] + ".dat")
            if not os.path.exists(dat): continue
            off = 0
            try:
                with open(os.path.join(folder, c), "r", encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        p = line.rstrip("\r\n").rsplit(" ", 3)
                        if len(p) != 4: continue
                        try: size = int(p[1])
                        except ValueError: continue
                        self.index.setdefault(p[0].lower(), {})[src] = (dat, off, size)
                        off += size
            except OSError: pass

    def read_all(self, rel):
        rel = rel.replace("\\", "/").lower()
        out = []
        for src, folder in self.sources:
            loose = os.path.join(folder, *rel.split("/"))
            if os.path.isfile(loose):
                try:
                    with open(loose, "rb") as fh: out.append(fh.read())
                except OSError: pass
                continue
            e = self.index.get(rel, {}).get(src)
            if e:
                try:
                    with open(e[0], "rb") as fh:
                        fh.seek(e[1])
                        out.append(fh.read(e[2]))
                except OSError: pass
        return [b.decode("utf-8", "replace") for b in out]

    def _build(self):
        self._index_folder("base", self.dir)
        ext = os.path.join(self.dir, "extensions")
        if os.path.isdir(ext):
            for d in sorted(os.listdir(ext)):
                sub = os.path.join(ext, d)
                if os.path.isdir(sub): self._index_folder(d, sub)

        for txt in self.read_all("t/0001-l044.xml"):
            for pm in re.finditer(r'<page\s+id="(\d+)"[^>]*>(.*?)</page>', txt, re.S):
                p_id = pm.group(1)
                for tm in re.finditer(r'<t\s+id="(\d+)"[^>]*>(.*?)</t>', pm.group(2), re.S):
                    self.text[(p_id, tm.group(1))] = html.unescape(tm.group(2))

        for txt in self.read_all("libraries/mapdefaults.xml"):
            for m in re.finditer(r'<dataset\s+macro="([a-zA-Z0-9_]+_sector[0-9_]*macro)"', txt):
                seg = txt[m.end():m.end() + 900]
                n = re.search(r'<identification[^>]*?\bname="([^"]+)"', seg)
                if n: self.sector_name_tags[m.group(1).lower()] = n.group(1)

        for txt in self.read_all("libraries/wares.xml"):
            for wm in re.finditer(r'<ware\b([^>]*)>(.*?)</ware>', txt, re.S):
                attrs, body = wm.group(1), wm.group(2)
                i = re.search(r'\bid="([^"]+)"', attrs)
                n = re.search(r'\bname="([^"]+)"', attrs)
                v = re.search(r'\bvolume="([^"]+)"', attrs)
                if not i: continue
                wid = i.group(1).lower()
                if n: self.wares[wid] = n.group(1)
                if v:
                    try: self.ware_volumes[wid] = float(v.group(1))
                    except ValueError: pass

                for prod in re.finditer(r'<production\b([^>]*)>(.*?)</production>', body, re.S):
                    p_attrs, p_body = prod.group(1), prod.group(2)
                    t_match = re.search(r'\btime="([^"]+)"', p_attrs)
                    if not t_match: continue
                    try: cycle_time = float(t_match.group(1))
                    except ValueError: continue
                    if cycle_time <= 0: continue
                    m_match = re.search(r'\bmethod="([^"]+)"', p_attrs)
                    method = m_match.group(1).lower() if m_match else "default"
                    cycles_per_hr = 3600.0 / cycle_time
                    inputs = {}
                    pri_match = re.search(r'<primary>(.*?)</primary>', p_body, re.S)
                    scan_body = pri_match.group(1) if pri_match else p_body
                    for in_ware in re.finditer(r'<ware\b([^>]*)>', scan_body):
                        iw_attrs = in_ware.group(1)
                        w_id = re.search(r'\bware="([^"]+)"', iw_attrs)
                        w_amt = re.search(r'\bamount="([^"]+)"', iw_attrs)
                        if w_id and w_amt:
                            try: inputs[w_id.group(1).lower()] = float(w_amt.group(1)) * cycles_per_hr
                            except ValueError: pass
                    if inputs:
                        self.ware_recipes[(wid, method)] = inputs
                        if wid not in self.ware_recipes: self.ware_recipes[wid] = inputs
        self.ok = bool(self.text)

    def resolve(self, raw, depth=0):
        if not raw: return ""
        def sub(m):
            t = self.text.get((m.group(1), m.group(2)))
            if t is None:
                if (m.group(1), m.group(2)) == ("20102", "1011"): t = "Trade Station"
                elif (m.group(1), m.group(2)) == ("20102", "2011"): t = "Defence Platform"
                elif (m.group(1), m.group(2)) == ("20102", "3001"): t = "Headquarters"
            if t is None: return m.group(0)
            return self.resolve(t, depth + 1) if depth < 8 else t

        s = REF_REGEX.sub(sub, raw)
        s = re.sub(r"\s*\\?\([^()]*\\?\)\s*", " ", s)
        parts = s.split()
        if len(parts) >= 2 and len(parts) % 2 == 0:
            half = len(parts) // 2
            if parts[:half] == parts[half:]: parts = parts[:half]
        return " ".join(parts).strip()

    def ship_macro_name(self, macro):
        if macro in self.macro_cache: return self.macro_cache[macro]
        res = None
        parts = macro.split("_")
        if self.ok and len(parts) > 3 and parts[2] in ("xs", "s", "m", "l", "xl"):
            for txt in reversed(self.read_all(f"assets/units/size_{parts[2]}/macros/{macro}.xml")):
                m = re.search(r'<identification[^>]*?\bname="([^"]+)"', txt)
                if m:
                    r = self.resolve(m.group(1))
                    if r and not REF_REGEX.search(r):
                        res = r
                        break
        self.macro_cache[macro] = res
        return res

class Namer:
    def __init__(self, gd=None, overrides=None):
        self.gd, self.ov = gd, overrides or {}

    def text(self, raw):
        if not raw: return ""
        return self.gd.resolve(raw) if (self.gd and self.gd.ok) else raw

    def sector(self, macro):
        if not macro: return "Unknown / Transit"
        m_lower = macro.lower()
        if m_lower in self.ov: return self.ov[m_lower]
        m = SECTOR_REGEX.search(m_lower)
        if self.gd and self.gd.ok:
            tag = self.gd.sector_name_tags.get(m_lower)
            if not tag and m: tag = "{20004,%d}" % (int(m.group(1)) * 10000 + int(m.group(2)) * 10 + 1)
            if tag:
                r = self.gd.resolve(tag)
                if r and not REF_REGEX.search(r): return r
        if m:
            key = (int(m.group(1)), int(m.group(2)))
            if key in BUILTIN_SECTORS: return BUILTIN_SECTORS[key]
            return f"Cluster {key[0]} / Sector {key[1]:02d}"
        return prettify(m_lower.replace("cluster_", "").replace("sector_", "").replace("_macro", ""))

    def ship(self, macro):
        m_lower = (macro or "").lower()
        if m_lower in self.ov: return self.ov[m_lower]
        if self.gd and self.gd.ok:
            r = self.gd.ship_macro_name(m_lower)
            if r: return r
        if m_lower in BUILTIN_SHIP_NAMES: return BUILTIN_SHIP_NAMES[m_lower]
        clean = re.sub(r"^ship_|_macro$", "", m_lower)
        parts = [p.capitalize() for p in clean.split("_") if p not in ["01", "02", "03", "a", "b", "c"]]
        return " ".join(parts) if parts else prettify(clean)

    def ware(self, wid):
        wid_lower = wid.lower()
        if self.gd and self.gd.ok and wid_lower in self.gd.wares:
            r = self.gd.resolve(self.gd.wares[wid_lower])
            if r and not REF_REGEX.search(r): return r
        if wid_lower in BUILTIN_WARE_NAMES: return BUILTIN_WARE_NAMES[wid_lower]
        return prettify(wid_lower)

    def volume(self, wid):
        wid_lower = wid.lower()
        if self.gd and self.gd.ok and wid_lower in self.gd.ware_volumes:
            return self.gd.ware_volumes[wid_lower]
        return BUILTIN_WARE_VOLUMES.get(wid_lower, 10.0)

    def price(self, wid):
        return AVERAGE_WARE_PRICES.get(wid.lower(), 150.0)

    def module_inputs(self, macro):
        m = macro.lower().replace("_macro", "")
        parts = m.split("_")
        race = parts[1] if len(parts) > 1 and parts[0] == "prod" else ""
        target_ware = parts[2] if len(parts) > 2 and parts[0] == "prod" else m
        race_to_method = {"ter": "terran", "tel": "teladi", "bor": "boron", "spl": "split", "arg": "default", "par": "default", "gen": "default"}
        method = race_to_method.get(race, "default")
        if self.gd and (target_ware, method) in self.gd.ware_recipes:
            return self.gd.ware_recipes[(target_ware, method)]
        if (target_ware, method) in FALLBACK_PROD_CONSUMPTION:
            return FALLBACK_PROD_CONSUMPTION[(target_ware, method)]
        if self.gd and target_ware in self.gd.ware_recipes:
            return self.gd.ware_recipes[target_ware]
        return FALLBACK_PROD_CONSUMPTION.get((target_ware, "default"), {})

# ==============================================================================
# DATA MODELS
# ==============================================================================
class TradeTransaction:
    def __init__(self, t, ship_id, partner_id, ware, amount, price, op, sector):
        self.time = float(t or 0.0)
        self.ship_id = ship_id
        self.partner_id = partner_id
        self.ware = ware.lower() if ware else "energycells"
        self.amount = int(amount)
        self.price = float(price)
        self.op = op.upper()
        self.sector = sector
        self.total_cr = round(self.amount * self.price, 2)
        self.is_internal = False

class CompletedTrade:
    def __init__(self, ship_id, ware, amount, buy_time, sell_time, buy_price, sell_price, buy_sec, sell_sec, is_internal, util_pct):
        self.ship_id = ship_id
        self.ware = ware
        self.amount = amount
        self.buy_time = buy_time
        self.sell_time = sell_time
        self.duration_s = max(0.0, sell_time - buy_time)
        self.buy_price = buy_price
        self.sell_price = sell_price
        self.cost = round(amount * buy_price, 2)
        self.revenue = round(amount * sell_price, 2)
        self.net_profit = round(self.revenue - self.cost, 2)
        self.margin_pct = round((self.net_profit / self.revenue * 100.0), 1) if self.revenue > 0 else 0.0
        self.buy_sector = buy_sec
        self.sell_sector = sell_sec
        self.is_internal = is_internal
        self.util_pct = util_pct

class Ship:
    def __init__(self, cid, a, size, sector, zone):
        self.id = cid
        self.macro = a.get("macro", "").lower()
        self.cls = a.get("class", "")
        self.size = size
        self.code = a.get("code", "")
        self.name = a.get("name", "")
        self.owner = a.get("owner", "player")
        self.sector = sector
        self.zone = zone
        self.pos = [0.0, 0.0, 0.0]
        self.role, self.category, self.weight_key = classify_ship(self.macro, self.cls)
        self.cargo_capacity_m3 = DEFAULT_CARGO_VOLUMES.get(size, 8_000.0)
        self.parts = Counter()
        self.gear = Counter()
        self.gear_types = Counter()
        self.installed_shields = Counter()
        self.installed_engines = Counter()
        self.installed_weapons = Counter()
        self.installed_turrets = Counter()
        self.software = set()
        self.marines = 0
        self.service = 0
        self.other_crew = Counter()
        self.marine_skills = []
        self.pilot_id = None
        self.pilot_name = ""
        self.pilot_skills = {}
        self.player_piloted = False
        self.orders = []
        self.sub_group = None
        self.commander_conn = None
        self.cmd_target = None
        self.commander = None
        self.assignment = "Unassigned"
        self.groups = {}
        self.ammo = Counter()
        self.cargo = Counter()
        self.shield_groups = []
        self.hull_pct = 100.0
        try:
            if a.get("hull"): self.hull_pct = float(a["hull"]) * 100.0
        except ValueError: pass
        self.attacktime = float(a["attacktime"]) if a.get("attacktime") else None
        self.attacker_id = a.get("attacker")
        self.kids = []
        self.transactions = []

    @property
    def shield_pct(self):
        if not self.shield_groups:
            return 100.0 if self.parts.get("shieldgenerator", 0) > 0 else 0.0
        return sum(self.shield_groups) / len(self.shield_groups)

    @property
    def elite_marines(self): return sum(1 for sk in self.marine_skills if sk >= 10)
    @property
    def veteran_marines(self): return sum(1 for sk in self.marine_skills if 5 <= sk < 10)
    @property
    def recruit_marines(self): return sum(1 for sk in self.marine_skills if sk < 5)

    @property
    def boarding_strength(self):
        total = 0.0
        for sk in self.marine_skills:
            pct = round(sk * 100.0 / 15.0)
            if pct >= 67: total += 110.0
            elif pct >= 34: total += 55.0
            else: total += 15.0
        return int(total)

    @property
    def estimated_value(self):
        base_val = ESTIMATED_HULL_VALUES.get(self.weight_key, 1_500_000)
        turret_count = self.parts.get("turret", 0) + self.parts.get("missileturret", 0)
        weapon_count = self.parts.get("weapon", 0) + self.parts.get("missilelauncher", 0)
        shield_count = self.parts.get("shieldgenerator", 0)
        eq_val = (turret_count * 120_000) + (weapon_count * 250_000) + (shield_count * 300_000)
        return int((base_val + eq_val) * (self.hull_pct / 100.0))

class BuildStorage:
    def __init__(self, cid, parent_station_id, sector=None):
        self.id = cid
        self.station_id = parent_station_id
        self.sector = sector
        self.cargo = Counter()
        self.needed = Counter()
        self.reservations = Counter()
        self.queue = []
        self.raw_construction_entries = []
        self.assigned_builder = None

class Station:
    def __init__(self, cid, a, sector, zone):
        self.id = cid
        self.macro = a.get("macro", "").lower()
        self.code = a.get("code", "")
        self.name = a.get("name", "") or a.get("basename", "")
        self.owner = a.get("owner", "player")
        self.sector = sector
        self.zone = zone
        self.pos = [0.0, 0.0, 0.0]
        self.role = "Station"
        self.modules = Counter()
        self.module_macros = Counter()
        self.raw_construction_entries = []
        self.fabrication_bays = []
        self.prod = []
        self.defence = Counter()
        self.gear = Counter()
        self.gear_types = Counter()
        self.docks = Counter()
        self.cargo = Counter()
        self.ammo = Counter()
        self.parts = Counter()
        self.offers = []
        self.reservations = []
        self.shortage = Counter()
        self.workforce = Counter()
        self.manager = None
        self.manager_id = None
        self.accounts = []
        self.groups = {}
        self.hull_pct = 100.0
        try:
            if a.get("hull"): self.hull_pct = float(a["hull"]) * 100.0
        except ValueError: pass
        self.attacktime = float(a["attacktime"]) if a.get("attacktime") else None
        self.attacker_id = a.get("attacker")
        self.kids = []
        self.build_storage = None
        self.default_trade_rule = None
        self.trade_wares = {}
        self.shipyard_queue = []
        self.construction_queue = []
        self.assigned_builder = None
        self.active_build_macro = None

    def storage_capacities(self):
        caps = {"container": 0.0, "solid": 0.0, "liquid": 0.0}
        for mac, cnt in self.module_macros.items():
            m = mac.lower()
            if "storage" not in m: continue
            sz = 1_000_000.0 if "_l_" in m or "_xl_" in m else (100_000.0 if "_m_" in m else 25_000.0)
            if "container" in m: caps["container"] += sz * cnt
            elif "solid" in m: caps["solid"] += sz * cnt
            elif "liquid" in m: caps["liquid"] += sz * cnt
            elif "condensate" in m or "scrap" in m: caps["solid"] += sz * cnt
        return caps

    def workforce_capacity(self):
        cap = 0
        for mac, cnt in self.module_macros.items():
            m = mac.lower()
            if not (m.startswith("hab_") or "habitation" in m or "living" in m):
                continue
            race = "argon"
            for r in ("terran", "paranid", "teladi", "split", "boron", "argon"):
                if f"_{r[:3]}_" in m or r in m:
                    race = r
                    break
            size = "l" if "_l_" in m else ("m" if "_m_" in m else "s")
            cap += HABITATION_CAPACITIES.get((race, size), 500) * cnt
        return cap

    @property
    def estimated_value(self):
        val = 15_000_000
        for m, cnt in self.module_macros.items():
            if "buildmodule" in m and "ships" in m: val += 120_000_000 * cnt
            elif "computronicsubstrate" in m or "claytronics" in m: val += 28_000_000 * cnt
            elif "prod_" in m: val += 6_000_000 * cnt
            elif "storage" in m: val += (2_500_000 if "_l_" in m else 800_000) * cnt
            elif "defence" in m: val += 3_000_000 * cnt
            elif m.startswith("hab_") or "habitation" in m: val += 2_000_000 * cnt
            else: val += 500_000 * cnt
        return int(val)

# ==============================================================================
# STREAMING SAVE PARSER
# ==============================================================================
class SaveParser:
    def __init__(self):
        self.tags = []
        self.comp_stack = []
        self.conns = []
        self.in_jobs = 0
        self.cur_faction = None
        self.order_stack = []
        self.cur_order = None
        self.info: dict = {"patches": []}
        self.ships = {}
        self.ship_by_code = {}
        self.stations = {}
        self.build_storages = {}
        self.all_units = {}
        self.xs_craft = 0
        self.derelicts = []
        self.datavaults = []
        self.hostile_units = []
        self.gates = []
        self.sectors = {}
        self.zones = {}
        self.sector_clusters = {}
        self.cluster_sectors = defaultdict(list)
        self.hostile = defaultdict(Counter)
        self.conn_comp = {}
        self.sub_links = []
        self.gate_conn = {}
        self.gate_links = []
        self.accounts = []
        self.player_account_id = None
        self.player_direct_money = None
        self.relations = dict(DEFAULT_FACTION_RELATIONS)
        self.counts = Counter()
        self.truncated = None
        self.adj = defaultdict(set)
        self.cur_marine = False
        self.recent_losses = []
        self.trade_rules = {}
        self.cur_trade_ware = None
        self.all_transactions = []
        self.trade_state_log_count = 0

    def is_hostile(self, fac):
        if not fac: return False
        fac_clean = fac.lower()
        if fac_clean in ("player", "ownerless", "none"): return False
        rel = self.relations.get(fac_clean, DEFAULT_FACTION_RELATIONS.get(fac_clean, 0.0))
        return rel <= HOSTILITY_RELATION_THRESHOLD

    def owner_frame(self):
        for fr in reversed(self.comp_stack):
            if fr.get("buildstorage"): return fr
            if fr.get("ship") or fr.get("station"): return fr
        return None

    def start(self, name, a):
        self.tags.append(name)
        self.counts["elements"] += 1
        if name == "component": return self._component(a)
        if name in ("jobs", "job", "waiting"):
            self.in_jobs += 1
            return
        if name == "connection":
            self.conns.append((a.get("connection", ""), a.get("id", "")))
            if not self.in_jobs: self._connection(a)
            return
        if self.in_jobs: return
        handler = getattr(self, f"_t_{name}", None)
        if handler: handler(a)

    def end(self, name):
        self.tags.pop()
        if name == "component":
            if self.comp_stack:
                fr = self.comp_stack.pop()
                if fr["cls"] == "npc": self._npc_end(fr)
                if any(fr.get(k) for k in ("derelict", "vault", "ship", "station", "hostile_unit", "gate")):
                    start = 0
                    for i, pfr in enumerate(self.comp_stack):
                        if pfr["cls"] in ("sector", "cluster"): start = i + 1
                    tot_x, tot_y, tot_z = fr["pos"]
                    for pfr in self.comp_stack[start:]:
                        tot_x += pfr["pos"][0]
                        tot_y += pfr["pos"][1]
                        tot_z += pfr["pos"][2]
                    final_pos = (tot_x, tot_y, tot_z)
                    if fr.get("derelict"): fr["derelict"]["pos"] = final_pos
                    if fr.get("vault"): fr["vault"]["pos"] = final_pos
                    if fr.get("ship"): fr["ship"].pos = final_pos
                    if fr.get("station"): fr["station"].pos = final_pos
                    if fr.get("hostile_unit"): fr["hostile_unit"]["pos"] = final_pos
                    if fr.get("gate"): fr["gate"]["pos"] = final_pos
        elif name in ("jobs", "job", "waiting"):
            self.in_jobs = max(0, self.in_jobs - 1)
        elif name == "connection":
            self.conns.pop()
        elif name == "order":
            if self.order_stack: self.order_stack.pop()
            self.cur_order = self.order_stack[-1] if self.order_stack else None
        elif name == "faction":
            self.cur_faction = None
        elif name == "person":
            self.cur_marine = False
        elif name == "ware":
            if self.cur_trade_ware and self.tags[-1:] == ["trade"]:
                self.cur_trade_ware = None

    def _component(self, a):
        cls = a.get("class", "")
        cid = a.get("id", "")
        macro = a.get("macro", "").lower()
        owner = a.get("owner", "")
        parent = self.comp_stack[-1] if self.comp_stack else None
        sector = parent["sector"] if parent else None
        zone = parent["zone"] if parent else None
        cluster = parent["cluster"] if parent else None

        fr = {
            "cls": cls, "cid": cid, "macro": macro, "owner": owner,
            "sector": sector, "zone": zone, "cluster": cluster,
            "pos": [0.0, 0.0, 0.0], "ship": None, "station": None, "derelict": None,
            "vault": None, "npc": None, "hostile_unit": None, "gate": None,
            "buildstorage": None
        }
        self.comp_stack.append(fr)
        if self.in_jobs: return

        if cid:
            self.all_units[cid] = {"id": cid, "name": a.get("name", "") or macro, "macro": macro, "owner": owner, "class": cls, "code": a.get("code", "")}

        if cls == "cluster": fr["cluster"] = cid
        elif cls == "sector":
            fr["sector"] = cid
            self.sectors[cid] = macro
            if fr["cluster"]:
                self.sector_clusters[cid] = fr["cluster"]
                self.cluster_sectors[fr["cluster"]].append(cid)
        elif cls == "zone": fr["zone"] = cid
        elif cls == "buildstorage":
            parent_station_id = a.get("station")
            parent_station = self.stations.get(parent_station_id) if parent_station_id else None
            if not parent_station:
                for pfr in reversed(self.comp_stack[:-1]):
                    if pfr.get("station"):
                        parent_station = pfr["station"]
                        parent_station_id = parent_station.id
                        break
            bs = BuildStorage(cid, parent_station_id, fr["sector"])
            self.build_storages[cid] = bs
            fr["buildstorage"] = bs
            if parent_station: parent_station.build_storage = bs
        elif cls.startswith("ship_"):
            size = SIZE_BY_CLASS.get(cls)
            deploy = bool(DEPLOYABLE_REGEX.search(macro))
            if owner == "player" and size and not deploy:
                if size == "XS": self.xs_craft += 1
                else:
                    s = Ship(cid, a, size, fr["sector"], fr["zone"])
                    self.ships[cid] = s
                    if s.code: self.ship_by_code[s.code] = s
                    fr["ship"] = s
                    self.counts["player_ships"] += 1
            is_wreck = a.get("state") == "wreck" or a.get("wreck") == "1" or cls == "wreck"
            if not is_wreck and owner in ("ownerless", "none") and size and size != "XS" and not deploy:
                d = {"id": cid, "macro": macro, "size": size, "sector": fr["sector"], "zone": fr["zone"], "known": a.get("knownto") == "player", "pos": (0.0, 0.0, 0.0)}
                self.derelicts.append(d)
                fr["derelict"] = d
            elif not is_wreck and self.is_hostile(owner) and size and size != "XS" and not deploy:
                self.hostile[fr["sector"] or ""][(owner, macro, size)] += 1
                if size in ("XL", "L"):
                    h_unit = {"id": cid, "macro": macro, "size": size, "owner": owner, "sector": fr["sector"], "pos": (0.0, 0.0, 0.0), "type": "ship"}
                    self.hostile_units.append(h_unit)
                    fr["hostile_unit"] = h_unit
        elif cls == "station":
            if owner == "player":
                st = Station(cid, a, fr["sector"], fr["zone"])
                self.stations[cid] = st
                fr["station"] = st
                self.counts["player_stations"] += 1
            elif self.is_hostile(owner):
                self.hostile[fr["sector"] or ""][(owner, macro, "STATION")] += 1
                h_st = {"id": cid, "macro": macro, "size": "STATION", "owner": owner, "sector": fr["sector"], "pos": (0.0, 0.0, 0.0), "type": "station"}
                self.hostile_units.append(h_st)
                fr["hostile_unit"] = h_st
        elif VAULT_REGEX.match(macro):
            v = {"id": cid, "macro": macro, "sector": fr["sector"], "erlking": bool(ERLKING_VAULT_REGEX.match(macro)), "unlocked": False, "blueprint": None, "pos": (0.0, 0.0, 0.0)}
            self.datavaults.append(v)
            fr["vault"] = v
        elif cls == "collectableblueprints":
            for pfr in reversed(self.comp_stack[:-1]):
                if pfr.get("vault"):
                    pfr["vault"]["blueprint"] = a.get("blueprints", "Unknown Blueprint")
                    break
        elif "gate" in cls:
            fr["is_gate"] = True
            g_rec = {"id": cid, "macro": macro, "sector": fr["sector"], "pos": (0.0, 0.0, 0.0)}
            self.gates.append(g_rec)
            fr["gate"] = g_rec
        elif cls == "npc": fr["npc"] = {"id": cid, "name": a.get("name", ""), "skills": {}}
        elif cls in GEAR_CLASSES:
            ofr = self.owner_frame()
            if ofr:
                tgt = ofr.get("ship") or ofr.get("station")
                if tgt:
                    tgt.parts[cls] += 1
                    tgt.gear_types[gear_category(macro)] += 1
                    tgt.gear[(cls,) + gear_parts(macro)] += 1
                    if isinstance(tgt, Ship):
                        if cls == "shieldgenerator": tgt.installed_shields[macro] += 1
                        elif cls == "engine": tgt.installed_engines[macro] += 1
                        elif cls in ("weapon", "missilelauncher"): tgt.installed_weapons[macro] += 1
                        elif cls in ("turret", "missileturret"): tgt.installed_turrets[macro] += 1
        elif cls in MODULE_CLASSES or macro.startswith("hab_") or "habitation" in cls:
            ofr = self.owner_frame()
            if ofr and ofr.get("station"):
                st = ofr["station"]
                st.modules[cls] += 1
                st.module_macros[macro] += 1
                t = macro.replace("_macro", "").split("_")
                if cls == "defencemodule" and len(t) > 2: st.defence[t[2]] += 1
                elif cls == "production": st.prod.append(macro)
                elif cls == "buildmodule" and "ships" in macro:
                    bay_sz = "S/M" if "_s_" in macro else ("L" if "_l_" in macro else "XL")
                    st.fabrication_bays.append({"macro": macro, "size": bay_sz, "role": f"{bay_sz} Fabrication Bay"})
                elif cls == "buildmodule" and "equip" in macro:
                    bay_sz = "S/M" if "_s_" in macro else "L"
                    st.fabrication_bays.append({"macro": macro, "size": bay_sz, "role": f"{bay_sz} Equipment Dock"})
        elif cls in ("dockingbay", "dockarea"):
            ofr = self.owner_frame()
            if ofr and ofr.get("station"):
                st = ofr["station"]
                m = macro.lower()
                sz = next((x for x in ("xl", "xs", "l", "m", "s") if f"_{x}_" in m), "?")
                kind = "launchtube" if "launchtube" in m else ("hangar" if "shipstorage" in m else "dock")
                if cls == "dockingbay": st.docks[(kind, sz.upper())] += 1

    def _npc_end(self, fr):
        n = fr.get("npc")
        if not n: return
        for p in reversed(self.comp_stack):
            if p.get("ship") and p["ship"].pilot_id == n["id"]:
                p["ship"].pilot_name, p["ship"].pilot_skills = n["name"], n["skills"]
                break
            if p.get("station") and p["station"].manager_id == n["id"]:
                p["station"].manager = {"name": n["name"], "skills": n["skills"]}
                break

    def _connection(self, a):
        name, cid = a.get("connection", ""), a.get("id", "")
        fr = self.comp_stack[-1] if self.comp_stack else None
        if not fr or not cid: return
        if fr.get("is_gate"): self.gate_conn[cid] = fr["sector"]
        elif name in ("commander", "subordinates") and (fr.get("ship") or fr.get("station")):
            c_obj = fr.get("ship") or fr.get("station")
            self.conn_comp[cid] = c_obj.id
            if name == "commander" and fr.get("ship"): fr["ship"].commander_conn = cid

    def _t_connected(self, a):
        if not self.conns or not self.comp_stack: return
        cname, cid = self.conns[-1]
        tgt = a.get("connection") or a.get("ref")
        if not tgt: return
        fr = self.comp_stack[-1]
        if fr.get("is_gate"): self.gate_links.append((cid, tgt))
        elif cname == "commander" and fr.get("ship"): fr["ship"].cmd_target = tgt
        elif cname == "subordinates" and (fr.get("ship") or fr.get("station")):
            c_obj = fr.get("ship") or fr.get("station")
            if c_obj: self.sub_links.append((c_obj.id, tgt))

    def _t_game(self, a):
        if self.tags[-2:-1] == ["info"]:
            self.info.update({"version": a.get("version"), "build": a.get("build"), "time": a.get("time"), "id": a.get("id")})

    def _t_save(self, a):
        if self.tags[-2:-1] == ["info"]: self.info["save_name"], self.info["date"] = a.get("name"), a.get("date")

    def _t_player(self, a):
        if self.tags[-2:-1] == ["info"]:
            self.info["player"] = a.get("name")
            if a.get("money"):
                try: self.player_direct_money = int(round(float(a["money"])))
                except ValueError: pass

    def _t_patch(self, a):
        if self.tags[-2:-1] == ["patches"]: self.info["patches"].append((a.get("name"), a.get("version")))

    def _t_faction(self, a):
        if self.tags[-2:-1] == ["factions"]: self.cur_faction = a.get("id")

    def _t_relation(self, a):
        if not self.cur_faction: return
        fac, rel = a.get("faction"), a.get("relation")
        if not fac or rel is None: return
        try:
            rel_val = float(rel)
            if self.cur_faction == "player": self.relations[fac.lower()] = rel_val
            elif fac.lower() == "player": self.relations[self.cur_faction.lower()] = rel_val
        except ValueError: pass

    def _t_rule(self, a):
        r_id = a.get("id") or a.get("rule")
        r_name = a.get("name")
        if r_id and r_name:
            self.trade_rules[str(r_id)] = r_name

    def _t_trade(self, a):
        ofr = self.owner_frame()
        if ofr and ofr.get("station"):
            st = ofr["station"]
            rule_id = a.get("rule") or a.get("defaultrule") or a.get("traderule")
            if rule_id: st.default_trade_rule = str(rule_id)

    def _t_log(self, a):
        if a.get("type") != "trade" or not a.get("ware"):
            return
        owner_id = a.get("owner")
        if owner_id not in self.ships and owner_id not in self.stations:
            return
        try:
            float(a.get("v", ""))
        except ValueError:
            return
        self.trade_state_log_count += 1

    def _t_tradeoffer(self, a):
        ofr = self.owner_frame()
        if not ofr: return
        w_id = a.get("ware", "").lower()
        if not w_id: return
        try: price = float(a.get("price", 0.0))
        except ValueError: price = 0.0
        try: amt = int(float(a.get("amount", 0)))
        except ValueError: amt = 0

        # Normal station trading
        if ofr.get("station") and not ofr.get("buildstorage"):
            ofr["station"].offers.append({
                "ware": w_id, "side": a.get("side", "sell"),
                "price": price, "amount": amt
            })

    def _t_account(self, a):
        aid, amt = a.get("id"), a.get("amount")
        if self.cur_faction == "player" and aid and amt is None:
            self.player_account_id = aid
            return
        if amt is None: return
        try: amt = int(round(float(amt)))
        except ValueError: return
        rec = {"id": aid, "amount": amt}
        self.accounts.append(rec)
        ofr = self.owner_frame()
        if ofr and ofr.get("station"): ofr["station"].accounts.append(rec)

    def _t_post(self, a):
        if self.tags[-2:-1] != ["control"] or not self.comp_stack: return
        comp, pid = a.get("component"), a.get("id")
        fr = self.comp_stack[-1]
        if fr.get("ship"):
            if pid == "aipilot" and comp: fr["ship"].pilot_id = comp
            elif pid == "playerpilot": fr["ship"].player_piloted = True
        elif fr.get("station") and pid == "manager" and comp: fr["station"].manager_id = comp

    def _t_order(self, a):
        fr = self.comp_stack[-1] if self.comp_stack else None
        if fr and fr.get("ship"):
            o = {"order": a.get("order", ""), "default": a.get("default") == "1", "temp": a.get("temp") == "1", "state": a.get("state", ""), "params": {}}
            fr["ship"].orders.append(o)
            self.order_stack.append(o)
            self.cur_order = o

    def _t_param(self, a):
        if self.cur_order is not None and self.tags[-2:-1] == ["order"]:
            n = a.get("name")
            if n in ("target", "destination", "space", "anchorspace", "tradeware", "supplier", "range", "radius", "commander", "attacker", "primarytarget", "station"):
                self.cur_order["params"][n] = a.get("value", "")
            elif n == "builder" and a.get("value"):
                ofr = self.owner_frame()
                if ofr and ofr.get("station"):
                    ofr["station"].assigned_builder = a.get("value")

    def _t_group(self, a):
        fr = self.comp_stack[-1] if self.comp_stack else None
        p = self.tags[-2:-1]
        if p == ["subordinates"] and fr and (fr.get("ship") or fr.get("station")):
            assign = a.get("assignment") or a.get("assignmment") or ""
            c_obj = fr.get("ship") or fr.get("station")
            c_obj.groups[a.get("index")] = assign.replace("assignment.", "").strip().capitalize()
        elif "value" in a and (p in (["shields"], ["shield"]) or (fr and fr.get("cls") == "shieldgenerator")):
            ofr = self.owner_frame()
            if ofr and ofr.get("ship"):
                try:
                    val = float(a["value"])
                    mx = float(a.get("max", 0))
                    if mx > 0: ofr["ship"].shield_groups.append((val / mx) * 100.0)
                    elif val <= 1.0: ofr["ship"].shield_groups.append(val * 100.0)
                    elif val <= 100.0: ofr["ship"].shield_groups.append(val)
                except ValueError: pass

    _t_shield = _t_group
    _t_shields = _t_group

    def _t_attacker(self, a):
        cid = a.get("component") or a.get("id") or a.get("ref")
        if cid:
            ofr = self.owner_frame()
            if ofr and ofr.get("ship") and not ofr["ship"].attacker_id:
                ofr["ship"].attacker_id = cid
            elif ofr and ofr.get("station") and not ofr["station"].attacker_id:
                ofr["station"].attacker_id = cid

    def _t_subordinate(self, a):
        fr = self.comp_stack[-1] if self.comp_stack else None
        if fr and fr.get("ship") and "group" in a: fr["ship"].sub_group = a["group"]

    def _t_person(self, a):
        fr = self.comp_stack[-1] if self.comp_stack else None
        if fr and fr.get("ship") and self.tags[-2:-1] == ["people"]:
            role = a.get("role", "")
            if role == "marine":
                fr["ship"].marines += 1
                fr["ship"].marine_skills.append(0)
                self.cur_marine = True
            elif role == "service":
                fr["ship"].service += 1
                self.cur_marine = False
            else:
                fr["ship"].other_crew[role] += 1
                self.cur_marine = False

    def _t_skills(self, a):
        fr = self.comp_stack[-1] if self.comp_stack else None
        if not fr: return
        if self.tags[-2:-1] == ["person"] and fr.get("ship") and self.cur_marine:
            try:
                if fr["ship"].marine_skills: fr["ship"].marine_skills[-1] = int(a.get("boarding", 0) or 0)
                else: fr["ship"].marine_skills.append(int(a.get("boarding", 0) or 0))
            except ValueError: pass
        elif self.tags[-2:-1] == ["traits"] and fr.get("npc"):
            fr["npc"]["skills"] = {k: int(v) for k, v in a.items() if v.isdigit()}

    def _t_item(self, a):
        p_up = self.tags[-2:-1]
        ofr = self.owner_frame()
        if not ofr: return
        if p_up == ["available"] and self.tags[-3:-2] == ["ammunition"]:
            tgt = ofr.get("ship") or ofr.get("station")
            if tgt:
                try: tgt.ammo[a.get("macro", "").lower()] += int(a.get("amount", 1))
                except ValueError: pass
        elif p_up in (["software"], ["upgrades"]):
            tgt = ofr.get("ship")
            if tgt and a.get("ware"): tgt.software.add(a["ware"])

    def _t_reservation(self, a):
        w_id = a.get("ware", "").lower()
        if not w_id: return
        amt_str = a.get("amount") or a.get("exact")
        try: amt = int(float(amt_str)) if amt_str else 0
        except ValueError: amt = 0
        if amt <= 0: return

        ofr = self.owner_frame()
        if not ofr: return
        bs = ofr.get("buildstorage")
        if not bs and ofr.get("station"):
            bs = ofr["station"].build_storage
        if bs:
            bs.reservations[w_id] += amt

    def _t_ware(self, a):
        w_id = a.get("ware", "").lower()
        if not w_id: return
        amt_str = a.get("amount") or a.get("exact") or a.get("value") or a.get("planned")
        try: amt = int(float(amt_str)) if amt_str else 0
        except ValueError: amt = 0
        ofr = self.owner_frame()
        if not ofr: return

        # 1. PHYSICAL CARGO INVENTORY (Catches both direct and nested inside <wares>)
        if "cargo" in self.tags[-4:]:
            tgt = ofr.get("buildstorage") or ofr.get("ship") or ofr.get("station")
            if tgt and amt > 0:
                tgt.cargo[w_id] += amt
            return

        # 2. INCOMING TRADE RESERVATIONS (En route to build storage)
        if any(tag in ("reservations", "reservation") for tag in self.tags[-4:]):
            bs = ofr.get("buildstorage")
            if not bs and ofr.get("station"): bs = ofr["station"].build_storage
            if bs and amt > 0:
                bs.reservations[w_id] += amt
            return

        # 3. STATION SHORTAGES
        if "shortage" in self.tags[-3:] and ofr.get("station") and amt > 0:
            ofr["station"].shortage[w_id] += amt
            return

        # 4. CONSTRUCTION PLANNED / NEEDED WARES (Strictly from construction sequence/entry/resources)
        in_construction_plan = any(tag in ("sequence", "construction", "resources", "needed") for tag in self.tags[-4:])
        if in_construction_plan and amt > 0:
            bs = ofr.get("buildstorage")
            if not bs and ofr.get("station"): bs = ofr["station"].build_storage
            if bs:
                bs.needed[w_id] = max(bs.needed.get(w_id, 0), amt)
            return

        # 5. STATION LOGICAL OVERVIEW CONFIGURATIONS
        if ofr.get("station") and not ofr.get("buildstorage"):
            st = ofr["station"]
            raw_limit = a.get("limit") or a.get("capacity") or a.get("amount")
            raw_sell = a.get("sell") or a.get("sellmin")
            raw_buy = a.get("buy") or a.get("buymax")
            rule_ref = a.get("rule") or a.get("traderule")

            trade_info = st.trade_wares.get(w_id, {
                "ware": w_id, "allocated_m3": None, "sell_threshold": None, "buy_threshold": None,
                "sell_mode": "auto", "buy_mode": "auto", "manual_price": None, "price_mode": "auto",
                "trade_rule_id": None
            })

            if raw_limit:
                try: trade_info["allocated_m3"] = float(raw_limit)
                except ValueError: pass
            if raw_sell is not None:
                try: trade_info["sell_threshold"] = int(float(raw_sell))
                except ValueError: pass
            if raw_buy is not None:
                try: trade_info["buy_threshold"] = int(float(raw_buy))
                except ValueError: pass
            if a.get("sellmode"): trade_info["sell_mode"] = a["sellmode"]
            if a.get("buymode"): trade_info["buy_mode"] = a["buymode"]
            if a.get("price"):
                try: trade_info["manual_price"] = float(a["price"])
                except ValueError: pass
            if a.get("manual") == "1": trade_info["price_mode"] = "manual"
            if rule_ref: trade_info["trade_rule_id"] = str(rule_ref)

            st.trade_wares[w_id] = trade_info
            self.cur_trade_ware = trade_info

    def _t_buy(self, a):
        if self.cur_trade_ware:
            amt = a.get("amount") or a.get("limit") or a.get("max")
            if amt:
                try: self.cur_trade_ware["buy_threshold"] = int(float(amt))
                except ValueError: pass
            if a.get("manual") == "1": self.cur_trade_ware["buy_mode"] = "manual"
            if a.get("rule"): self.cur_trade_ware["trade_rule_id"] = str(a.get("rule"))

    def _t_sell(self, a):
        if self.cur_trade_ware:
            amt = a.get("amount") or a.get("limit") or a.get("min")
            if amt:
                try: self.cur_trade_ware["sell_threshold"] = int(float(amt))
                except ValueError: pass
            if a.get("manual") == "1": self.cur_trade_ware["sell_mode"] = "manual"
            if a.get("rule"): self.cur_trade_ware["trade_rule_id"] = str(a.get("rule"))

    def _t_price(self, a):
        if self.cur_trade_ware:
            val = a.get("value") or a.get("price")
            if val:
                try:
                    self.cur_trade_ware["manual_price"] = round(float(val), 2)
                    self.cur_trade_ware["price_mode"] = "manual"
                except ValueError: pass

    def _t_limit(self, a):
        if self.cur_trade_ware:
            val = a.get("amount") or a.get("value")
            if val:
                try: self.cur_trade_ware["allocated_m3"] = float(val)
                except ValueError: pass

    _t_limits = _t_limit

    def _t_builder(self, a):
        b_id = a.get("component") or a.get("id") or a.get("ref") or a.get("builder")
        if b_id:
            ofr = self.owner_frame()
            if ofr:
                if ofr.get("station"): ofr["station"].assigned_builder = b_id
                if ofr.get("buildstorage"): ofr["buildstorage"].assigned_builder = b_id

    def _t_construction(self, a):
        b_id = a.get("builder") or a.get("builderid")
        if b_id:
            ofr = self.owner_frame()
            if ofr:
                if ofr.get("station"): ofr["station"].assigned_builder = b_id
                if ofr.get("buildstorage"): ofr["buildstorage"].assigned_builder = b_id

    def _t_entry(self, a):
        p = self.tags[-2:-1]
        macro = (a.get("macro") or a.get("module") or a.get("building") or "").lower()

        # Station construction layout sequence
        if macro and any(tag in ("sequence", "queue", "construction", "entries", "plans", "plan", "stage") for tag in self.tags[-4:]):
            ofr = self.owner_frame()
            if not ofr: return

            st = ofr.get("station")
            bs = ofr.get("buildstorage")
            if not st and bs and bs.station_id and bs.station_id in self.stations:
                st = self.stations[bs.station_id]

            entry_id = a.get("id") or a.get("construction")
            state = (a.get("state") or "").lower()
            raw_prog = a.get("progress") or a.get("completion")
            prog = 0.0
            if raw_prog:
                try:
                    v = float(raw_prog)
                    prog = (v * 100.0) if 0.0 < v <= 1.0 else (v if v <= 100.0 else 100.0)
                except ValueError: prog = 0.0

            entry_data = {
                "id": entry_id,
                "macro": macro,
                "state": state,
                "progress": prog
            }

            if st: st.raw_construction_entries.append(entry_data)
            if bs: bs.raw_construction_entries.append(entry_data)

        # Logbook ingestion
        elif p == ["log"]:
            title, text = a.get("title", ""), a.get("text", "")
            combined = (title + " " + text).lower()

            buy_match = re.search(r"\b(?:buy|bought|purchased)\b", combined)
            sell_match = re.search(r"\b(?:sell|sold)\b", combined)
            if bool(buy_match) == bool(sell_match):
                is_trade_log = False
            else:
                is_trade_log = True

            if is_trade_log:
                code_match = CODE_REGEX.search(title + " " + text)
                hex_match = HEX_ID_REGEX.search(title + " " + text)
                ship = self.ship_by_code.get(code_match.group(1)) if code_match else None
                s_id = ship.id if ship else (hex_match.group(1) if hex_match else None)
                if not s_id or s_id not in self.ships:
                    return

                ware_match = None
                for wid, display_name in sorted(
                    BUILTIN_WARE_NAMES.items(),
                    key=lambda item: max(len(item[0]), len(item[1])),
                    reverse=True
                ):
                    for alias in (wid, display_name):
                        alias_pattern = re.escape(alias)
                        if re.search(rf"(?<!\w){alias_pattern}(?!\w)", combined, re.IGNORECASE):
                            ware_match = (wid, alias_pattern)
                            break
                    if ware_match:
                        break
                if not ware_match:
                    return

                trade_ware, ware_pattern = ware_match
                amount_match = re.search(
                    rf"(?<!\w)(\d[\d,]*)\s*(?:x\s*)?{ware_pattern}(?!\w)",
                    combined,
                    re.IGNORECASE
                )
                if not amount_match:
                    return
                amount = int(amount_match.group(1).replace(",", ""))
                if amount <= 0:
                    return

                money_raw = a.get("money")
                try:
                    if money_raw is not None:
                        total_cr = abs(float(money_raw))
                    else:
                        credit_match = re.search(r"(?<!\w)(\d[\d,]*(?:\.\d+)?)\s*(?:cr|credits)\b", combined)
                        if not credit_match:
                            return
                        total_cr = float(credit_match.group(1).replace(",", ""))
                except ValueError:
                    return

                try: t_val = float(a.get("time", 0.0))
                except ValueError: return

                tx = TradeTransaction(
                    t=t_val,
                    ship_id=s_id,
                    partner_id=a.get("partner", "unknown"),
                    ware=trade_ware,
                    amount=amount,
                    price=round(total_cr / amount, 2),
                    op="BUY" if buy_match else "SELL",
                    sector=None
                )
                self.all_transactions.append(tx)
                self.ships[s_id].transactions.append(tx)

            elif ("destroyed" in combined or "under attack" in combined or "flee" in combined or "forced pilot" in combined):
                try:
                    t_val = float(a.get("time", 0))
                    self.recent_losses.append((t_val, re.sub(r"(\\012|\[\\012\])", " | ", title).strip(), re.sub(r"(\\012|\[\\012\])", " | ", text).strip()))
                except ValueError: pass

    def _t_build(self, a):
        ofr = self.owner_frame()
        if not ofr: return

        st = ofr.get("station")
        bs = ofr.get("buildstorage")
        if not st and bs and bs.station_id and bs.station_id in self.stations:
            st = self.stations[bs.station_id]
        if not bs and st and st.build_storage:
            bs = st.build_storage

        b_type = a.get("type", "")
        macro = (a.get("macro") or a.get("hull") or "").lower()
        b_id = a.get("builder")
        if b_id:
            if st: st.assigned_builder = b_id
            if bs: bs.assigned_builder = b_id

        save_time = float(self.info.get("time") or 0.0)
        t_start = float(a["start"]) if a.get("start") else None
        t_total = float(a["time"]) if a.get("time") else None
        t_rem = float(a["remaining"]) if a.get("remaining") else None

        if t_start is not None and t_total and t_total > 0 and save_time >= t_start:
            prog = ((save_time - t_start) / t_total) * 100.0
        elif t_total and t_rem is not None and t_total > 0:
            prog = (1.0 - (t_rem / t_total)) * 100.0
        else:
            raw_c = a.get("completion") or a.get("progress")
            try:
                v = float(raw_c) if raw_c else 0.0
                prog = (v * 100.0) if 0.0 < v <= 1.0 else (v if v <= 100.0 else 100.0)
            except ValueError: prog = 0.0

        prog = max(0.0, min(100.0, prog))
        time_left = t_rem if t_rem is not None else (max(0.0, t_total - (prog / 100.0 * t_total)) if t_total else 0.0)

        if b_type == "buildmodule" or (macro and not macro.startswith("ship_")):
            if macro:
                if st: st.active_build_macro = macro
                entry = {"macro": macro, "state": "building", "progress": round(prog, 1)}
                if st:
                    st.construction_queue = [e for e in st.construction_queue if e["macro"] != macro]
                    st.construction_queue.insert(0, entry)
                if bs:
                    bs.queue = [e for e in bs.queue if e["macro"] != macro]
                    bs.queue.insert(0, entry)
        else:
            if macro and st:
                st.shipyard_queue.append({
                    "hull": macro,
                    "client": a.get("faction") or a.get("customer") or "player",
                    "progress": round(prog, 1),
                    "time_left_s": int(time_left)
                })

    def _t_workforce(self, a):
        ofr = self.owner_frame()
        if ofr and ofr.get("station"):
            try: ofr["station"].workforce[a.get("race", "?").lower()] += int(a.get("amount", 0))
            except ValueError: pass

    def _t_unlock(self, a):
        fr = self.comp_stack[-1] if self.comp_stack else None
        if fr and fr.get("vault") and a.get("state") == "unlocked": fr["vault"]["unlocked"] = True

    def _t_position(self, a):
        if not self.comp_stack: return
        p_up = self.tags[-2:]
        if p_up == ["offset", "position"] or p_up == ["movement", "position"]:
            try:
                x = float(a.get("x", 0))
                y = float(a.get("y", 0))
                z = float(a.get("z", 0))
                self.comp_stack[-1]["pos"] = [x, y, z]
            except ValueError: pass

    def _t_transaction(self, a):
        ofr = self.owner_frame()
        tgt_ship = ofr.get("ship") if ofr else None
        tgt_st = ofr.get("station") if ofr else None
        s_id = tgt_ship.id if tgt_ship else (tgt_st.id if tgt_st else a.get("ship"))
        if not s_id: return

        w_id = a.get("ware", "").lower()
        if not w_id: return
        try: amt = int(float(a.get("amount", 0)))
        except ValueError: amt = 0
        if amt <= 0: return

        try: price = float(a.get("price", 0.0))
        except ValueError: price = 0.0

        op = a.get("event") or a.get("operation") or a.get("type") or "SELL"
        tx = TradeTransaction(
            t=a.get("time", 0.0),
            ship_id=s_id,
            partner_id=a.get("partner") or a.get("station") or "unknown",
            ware=w_id,
            amount=amt,
            price=price,
            op=op,
            sector=ofr.get("sector") if ofr else None
        )
        self.all_transactions.append(tx)
        if tgt_ship: tgt_ship.transactions.append(tx)

    def parse(self, path):
        xp = expat.ParserCreate()
        xp.StartElementHandler, xp.EndElementHandler = self.start, self.end
        size = os.path.getsize(path)
        opener = gzip.open if path.endswith(".gz") else open
        done, nxt = 0, 0
        with opener(path, "rb") as fh:
            raw = getattr(fh, "fileobj", fh)
            try:
                while True:
                    chunk = fh.read(1 << 20)
                    if not chunk: break
                    xp.Parse(chunk, False)
                    done = raw.tell()
                    if done >= nxt:
                        pct = (100.0 * done / max(size, 1))
                        print(f"    ... Auditing {pct:5.1f}% | {self.counts['elements']:,} XML elements", end="\r")
                        nxt = done + (32 << 20)
                xp.Parse(b"", True)
            except expat.ExpatError as e: self.truncated = str(e)
        print(" " * 80, end="\r")

    def finalize(self):
        for a, b in self.gate_links:
            sa, sb = self.gate_conn.get(a), self.gate_conn.get(b)
            if sa and sb and sa != sb:
                self.adj[sa].add(sb)
                self.adj[sb].add(sa)
        for cl, secs in self.cluster_sectors.items():
            for i, sa in enumerate(secs):
                for sb in secs[i + 1:]:
                    self.adj[sa].add(sb)
                    self.adj[sb].add(sa)

        all_comps = {**self.ships, **self.stations}
        rev_sub_links = {tgt: cmd for cmd, tgt in self.sub_links}

        for s in self.ships.values():
            cmd_id = self.conn_comp.get(s.cmd_target) if s.cmd_target else None
            if cmd_id is None and s.commander_conn: cmd_id = rev_sub_links.get(s.commander_conn)
            if cmd_id in all_comps and cmd_id != s.id:
                s.commander = cmd_id
                all_comps[cmd_id].kids.append(s.id)
                cmd_obj = all_comps[cmd_id]
                if s.sub_group and s.sub_group in cmd_obj.groups: s.assignment = cmd_obj.groups[s.sub_group]
                else:
                    d_ord = (self.primary_order(s) or {}).get("order", "").lower()
                    if s.category == "Miner": s.assignment = "Mining"
                    elif s.category == "Trader": s.assignment = "Trade"
                    elif s.category == "Military":
                        if "intercept" in d_ord: s.assignment = "Intercept"
                        elif "bombard" in d_ord: s.assignment = "Bombard"
                        elif "attack" in d_ord: s.assignment = "Attack"
                        else: s.assignment = "Defence"
                    else: s.assignment = "Support"

        for st in self.stations.values():
            if "headquarters" in st.macro: st.role = "Headquarters"
            elif any("buildmodule" in m and "ships" in m for m in st.module_macros): st.role = "Shipyard / Wharf"
            elif any("buildmodule" in m and "equip" in m for m in st.module_macros): st.role = "Equipment Dock"
            elif st.modules["production"] > 0: st.role = "Production Complex"
            elif st.modules["storage"] > 0: st.role = "Trade Station"
            elif st.modules["defencemodule"] > 0: st.role = "Defence Platform"
            else: st.role = "Installation"

        # Explicit Build Storage linking
        for bs in self.build_storages.values():
            if bs.station_id and bs.station_id in self.stations:
                st = self.stations[bs.station_id]
                st.build_storage = bs

        # Fallback linkage by sector proximity if unlinked
        for st in self.stations.values():
            if not st.build_storage and st.sector:
                for bs in self.build_storages.values():
                    if bs.sector == st.sector and not bs.station_id:
                        st.build_storage = bs
                        bs.station_id = st.id
                        break

        # Builder detection
        for s in self.ships.values():
            if s.role == "Builder (Civilian)" or "builder" in s.macro:
                for o in s.orders:
                    o_name = o.get("order", "").lower()
                    if o_name in ("deploytostation", "build", "buildstation", "assigntostation", "waitforbuild"):
                        target_id = o["params"].get("target") or o["params"].get("station") or o["params"].get("destination")
                        if target_id:
                            target_st = None
                            if target_id in self.stations: target_st = self.stations[target_id]
                            elif target_id in self.build_storages:
                                bs = self.build_storages[target_id]
                                if bs.station_id and bs.station_id in self.stations:
                                    target_st = self.stations[bs.station_id]
                            if target_st:
                                if not target_st.assigned_builder: target_st.assigned_builder = s.id
                                if target_st.build_storage and not target_st.build_storage.assigned_builder:
                                    target_st.build_storage.assigned_builder = s.id

        # Construction queue sync
        for st in self.stations.values():
            bs = st.build_storage
            if bs and bs.raw_construction_entries:
                st.raw_construction_entries.extend(bs.raw_construction_entries)

            if st.raw_construction_entries:
                built_pool = Counter(st.module_macros)
                real_pending = []

                for entry in st.raw_construction_entries:
                    emac = entry.get("macro")
                    prog = entry.get("progress", 0.0)
                    estate = entry.get("state", "")

                    if estate in ("complete", "built", "finished", "done") or prog >= 100.0:
                        continue

                    if built_pool[emac] > 0 and estate != "building":
                        built_pool[emac] -= 1
                        continue

                    if estate == "building" or prog > 0.0 or emac == st.active_build_macro:
                        real_pending.insert(0, {"macro": emac, "state": "building", "progress": round(prog, 1)})
                    else:
                        real_pending.append({"macro": emac, "state": "planned", "progress": round(prog, 1)})

                st.construction_queue = real_pending

            if bs:
                if not bs.queue and st.construction_queue: bs.queue = list(st.construction_queue)
                elif not st.construction_queue and bs.queue: st.construction_queue = list(bs.queue)
                if not bs.assigned_builder and st.assigned_builder: bs.assigned_builder = st.assigned_builder
                elif not st.assigned_builder and bs.assigned_builder: st.assigned_builder = bs.assigned_builder

        player_unit_ids = set(self.ships.keys()) | set(self.stations.keys()) | set(self.build_storages.keys())
        for tx in self.all_transactions:
            if tx.partner_id in player_unit_ids: tx.is_internal = True

    def descendants(self, cid):
        out, seen, queue = [], {cid}, deque([cid])
        all_comps = {**self.ships, **self.stations}
        while queue:
            curr = queue.popleft()
            if curr in all_comps:
                for k in all_comps[curr].kids:
                    if k not in seen:
                        seen.add(k)
                        out.append(k)
                        queue.append(k)
        return out

    def primary_order(self, s):
        real = [o for o in s.orders if not o["temp"]]
        non_def = [o for o in real if not o["default"]]
        return (non_def or real or [None])[0]

    def activity(self, s):
        for o in s.orders:
            if o["state"] in ("started", "critical"): return o["order"]
        p = self.primary_order(s)
        return p["order"] if p else "Idle"

    def resolve_combat_target(self, s, namer=None):
        save_time = float(self.info.get("time") or 0.0)
        attacker = None
        if s.attacktime and (save_time - s.attacktime) < COMBAT_ENGAGEMENT_WINDOW:
            if s.attacker_id and s.attacker_id in self.all_units:
                u = self.all_units[s.attacker_id]
                u_owner = (u["owner"] or "").lower()
                if self.is_hostile(u_owner):
                    nm = namer.ship(u["macro"]) if namer else prettify(u["macro"].replace("_macro", ""))
                    attacker = f"Under attack by: [{u['id']}] {nm} ({u_owner.upper()})"

        target = None
        for o in s.orders:
            ord_name = o["order"].lower()
            if ord_name in ("attack", "combat", "flee", "protectship", "patrol"):
                p_tgt = o["params"].get("target") or o["params"].get("primarytarget") or o["params"].get("attacker")
                if p_tgt and p_tgt in self.all_units:
                    u = self.all_units[p_tgt]
                    u_owner = (u["owner"] or "").lower()
                    if self.is_hostile(u_owner):
                        nm = namer.ship(u["macro"]) if namer else prettify(u["macro"].replace("_macro", ""))
                        target = f"{o['order']} -> [{u['id']}] {nm} ({u_owner.upper()})"
                        break

        if attacker and target: return f"{attacker} | {target}"
        return attacker or target or "Standby / Clear"

# ==============================================================================
# TRADE ANALYZER ENGINE (MOD 1801 PARITY & LOG NORMALIZATION)
# ==============================================================================
def process_trade_analytics(P, N):
    save_time = float(P.info.get("time") or 0.0)
    tx_by_ship = defaultdict(list)
    for tx in P.all_transactions:
        tx_by_ship[tx.ship_id].append(tx)

    completed_trades = []
    for s_id, tx_list in tx_by_ship.items():
        sorted_tx = sorted(tx_list, key=lambda x: x.time)
        open_buys = defaultdict(deque)
        ship_obj = P.ships.get(s_id)
        cap = ship_obj.cargo_capacity_m3 if ship_obj else 8_000.0

        for tx in sorted_tx:
            w = tx.ware
            if tx.op in ("BUY", "MINE"):
                open_buys[w].append((tx, tx.amount))
            elif tx.op == "SELL":
                remaining_to_sell = tx.amount
                while remaining_to_sell > 0 and open_buys[w]:
                    buy_tx, remaining_in_lot = open_buys[w][0]
                    matched_amount = min(remaining_to_sell, remaining_in_lot)
                    vol = N.volume(w) * matched_amount
                    util_pct = min(100.0, round((vol / cap * 100.0), 1)) if cap > 0 else 50.0
                    tr = CompletedTrade(
                        ship_id=s_id, ware=w, amount=matched_amount,
                        buy_time=buy_tx.time, sell_time=tx.time,
                        buy_price=buy_tx.price, sell_price=tx.price,
                        buy_sec=buy_tx.sector, sell_sec=tx.sector,
                        is_internal=(buy_tx.is_internal or tx.is_internal),
                        util_pct=util_pct
                    )
                    completed_trades.append(tr)
                    remaining_to_sell -= matched_amount
                    remaining_in_lot -= matched_amount
                    if remaining_in_lot:
                        open_buys[w][0] = (buy_tx, remaining_in_lot)
                    else:
                        open_buys[w].popleft()

    ship_profits = defaultdict(lambda: {"profit": 0.0, "trades": 0, "volume": 0, "rev": 0.0, "ext_profit": 0.0, "util_acc": []})
    for tr in completed_trades:
        st = ship_profits[tr.ship_id]
        st["profit"] += tr.net_profit
        if not tr.is_internal: st["ext_profit"] += tr.net_profit
        st["trades"] += 1
        st["volume"] += tr.amount
        st["rev"] += tr.revenue
        st["util_acc"].append(tr.util_pct)

    ware_profits = defaultdict(lambda: {"profit": 0.0, "volume": 0, "revenue": 0.0, "trades": 0})
    for tr in completed_trades:
        wt = ware_profits[tr.ware]
        wt["profit"] += tr.net_profit
        wt["volume"] += tr.amount
        wt["revenue"] += tr.revenue
        wt["trades"] += 1

    inactive_traders = []
    for s in P.ships.values():
        if s.category in ("Trader", "Miner") and (s.commander or s.assignment in ("Trade", "Mining")):
            last_tx_time = max([tx.time for tx in s.transactions], default=0.0)
            idle_hrs = (save_time - last_tx_time) / 3600.0 if last_tx_time > 0 else 999.0
            if idle_hrs > 2.0:
                inactive_traders.append((s, idle_hrs))

    return completed_trades, ship_profits, ware_profits, inactive_traders

# ==============================================================================
# UNIFIED STRATEGIC DOSSIER & MARKDOWN GENERATOR
# ==============================================================================
def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows]
    return out

def build_dossier(P, N, game_dir, gd_ok):
    md = []
    save_time = float(P.info.get("time") or 0)

    def sname(sid): return N.sector(P.sectors.get(sid)) if sid else "Unknown / Transit"
    def ship_name(s):
        nm = N.text(s.name) if s.name else ""
        base = nm if nm and not REF_REGEX.search(nm) else N.ship(s.macro)
        return f"{base} ({s.code})" if s.code and s.code not in base else base
    def station_name(st):
        nm = N.text(st.name) if st.name else ""
        base = nm if nm and not REF_REGEX.search(nm) else st.role
        return f"{base} ({st.code})" if st.code and st.code not in base else base

    ships = list(P.ships.values())
    stations = list(P.stations.values())
    warships = [s for s in ships if s.category == "Military"]
    traders = [s for s in ships if s.category == "Trader"]
    miners = [s for s in ships if s.category == "Miner"]
    auxiliary = [s for s in ships if s.category == "Civilian"]

    acct_by_id = {a["id"]: a["amount"] for a in P.accounts if a.get("id")}
    purse = P.player_direct_money if P.player_direct_money is not None else acct_by_id.get(P.player_account_id, 0)
    station_cash = sum(sum(a["amount"] for a in st.accounts) for st in stations)
    total_liquid = purse + station_cash
    fleet_capital = sum(s.estimated_value for s in ships)
    real_estate = sum(st.estimated_value for st in stations)

    stockpile_val = 0
    for st in stations:
        for w, amt in st.cargo.items(): stockpile_val += int(amt * N.price(w))
    for s in ships:
        for w, amt in s.cargo.items(): stockpile_val += int(amt * N.price(w))

    grand_total_net_worth = total_liquid + fleet_capital + real_estate + stockpile_val
    total_skimmable = 0
    station_skim_data = []
    for st in stations:
        st_c = sum(a["amount"] for a in st.accounts)
        rec_reserve = 50_000_000 if "Shipyard" in st.role else (20_000_000 if st.prod else 10_000_000)
        skimmable = max(0, st_c - rec_reserve)
        total_skimmable += skimmable
        if skimmable > 5_000_000:
            station_skim_data.append([station_name(st), sname(st.sector), f"{num(st_c)} Cr", f"{num(rec_reserve)} Cr", f"{num(skimmable)} Cr"])

    total_marines = sum(s.marines for s in ships)
    total_service = sum(s.service for s in ships)
    total_crew = total_marines + total_service + sum(sum(s.other_crew.values()) for s in ships)
    veteran_marines = sum(s.veteran_marines for s in ships)
    elite_marines = sum(s.elite_marines for s in ships)
    empire_boarding_power = sum(s.boarding_strength for s in ships)

    unarmed = [s for s in warships if not (s.parts["weapon"] + s.parts["turret"] + s.parts["missilelauncher"] + s.parts["missileturret"])]
    unshielded = [s for s in warships if not s.parts["shieldgenerator"]]
    unpiloted = [s for s in warships if not (s.pilot_id or s.player_piloted)]
    damaged_ships = [
        s for s in ships 
        if s.hull_pct < 98.0 
        or (s.parts.get("shieldgenerator", 0) > 0 and s.shield_pct < 90.0) 
        or (s.attacktime and (save_time - s.attacktime) < COMBAT_ENGAGEMENT_WINDOW)
    ]

    ammo_total = defaultdict(int)
    for obj in ships + stations:
        for m, count in obj.ammo.items():
            cat, _ = ammo_class(m)
            ammo_total[cat] += count

    threat_hops = {}
    hostile_sids = {sid for sid, cnt in P.hostile.items() if sid and any(k[2] in ("XL", "L", "STATION") for k in cnt)}
    queue = deque()
    for f in hostile_sids: threat_hops[f] = 0; queue.append(f)
    while queue:
        curr = queue.popleft()
        for neighbor in P.adj.get(curr, ()):
            if neighbor not in threat_hops: threat_hops[neighbor] = threat_hops[curr] + 1; queue.append(neighbor)

    date_str = datetime.datetime.utcfromtimestamp(int(P.info["date"])).strftime("%Y-%m-%d %H:%M UTC") if P.info.get("date") else "Unknown"

    md.append("# SUPREME COMMAND UNIFIED STRATEGIC & INDUSTRIAL DOSSIER (V1.7.6 ENTERPRISE)\n")
    md.append(f"> Savegame: **{P.info.get('save_name', 'Unknown')}** | Commander: **{P.info.get('player', 'Val Selton')}** | Engine: `X4 Build {P.info.get('build', 'Unknown')}` | Time: `{save_time:,.0f}s` ({date_str})\n")

    # 1. EMPIRE VALUATION
    md.append("## 1. Empire Balance Sheet & Total Net Worth")
    md.append(f"### **Total Empire Net Worth: {num(grand_total_net_worth)} Credits**\n")
    net_rows = [
        ["Commander Wallet (Personal Purse)", f"{num(purse)} Cr", f"{purse*100.0/grand_total_net_worth:.1f}%"],
        ["Station Operating Capital Reserves", f"{num(station_cash)} Cr", f"{station_cash*100.0/grand_total_net_worth:.1f}%"],
        ["Active Naval Fleet Valuation (Ships + Gear)", f"{num(fleet_capital)} Cr", f"{fleet_capital*100.0/grand_total_net_worth:.1f}%"],
        ["Station Industrial Real Estate (Modules & Docks)", f"{num(real_estate)} Cr", f"{real_estate*100.0/grand_total_net_worth:.1f}%"],
        ["Warehouse & Fleet Commodity Stockpiles", f"{num(stockpile_val)} Cr", f"{stockpile_val*100.0/grand_total_net_worth:.1f}%"],
        ["**Grand Total Empire Assets**", f"**{num(grand_total_net_worth)} Cr**", "100.0%"]
    ]
    md += table(["Asset Category", "Estimated Valuation", "Share of Wealth"], net_rows)
    md.append("")

    # 2. EXECUTIVE OVERVIEW
    md.append("## 2. Executive Empire & Personnel Overview")
    md.append(f"- **Total Active Fleet:** **{len(ships)} hulls** (+ {P.xs_craft} XS utility/dock craft)")
    md.append(f"  - Warships: **{len(warships)} hulls** (XL: {sum(1 for s in warships if s.size=='XL')}, L: {sum(1 for s in warships if s.size=='L')}, M: {sum(1 for s in warships if s.size=='M')}, S: {sum(1 for s in warships if s.size=='S')})")
    md.append(f"  - Commercial Freighters: **{len(traders)} hulls** (Assigned: {len([t for t in traders if t.commander])} | Independent: {len([t for t in traders if not t.commander])})")
    md.append(f"  - Raw Resource Miners: **{len(miners)} hulls** (Assigned: {len([m for m in miners if m.commander])} | Independent: {len([m for m in miners if not m.commander])})")
    md.append(f"  - Auxiliary / Construction / Scouts: **{len(auxiliary)} hulls**")
    md.append(f"- **Station Infrastructure:** **{len(stations)} corporate installations**")
    md.append(f"- **Treasury Liquidity:** **{num(total_liquid)} Cr** (Safe to Skim from Stations: **{num(total_skimmable)} Cr**)")
    md.append(f"- **Marine Assault & Boarding Readiness:**")
    md.append(f"  - Total Personnel: **{num(total_crew)} crew** (Technicians: {num(total_service)})")
    md.append(f"  - Marine Force: **{num(total_marines)} troops** ({num(elite_marines)} Elite | {num(veteran_marines)} Veteran | {num(sum(s.recruit_marines for s in ships))} Recruit)")
    md.append(f"  - **Total Marine Assault Strength:** **{num(empire_boarding_power)} attack points** (Exact 0-15 skill rating scaling)")
    md.append(f"- **Tactical Deployables & Ordnance:** {ammo_total.get('Laser Towers', 0)} Laser Towers | {ammo_total.get('Satellites', 0)} Satellites | {ammo_total.get('Resource Probes', 0)} Probes | {ammo_total.get('Drones', 0)} Drones | {ammo_total.get('Missiles', 0)} Missiles")
    md.append(f"- **Fleet Exceptions:** {len(unarmed)} unarmed warships | {len(unshielded)} unshielded | {len(unpiloted)} unpiloted | {len(damaged_ships)} damaged or combat-stressed hulls\n")

    # 3. STATION EXPANSION QUEUES & BUILD STORAGE
    md.append("## 3. Station Expansion Queues & Build Storage Logistics")
    bs_rows = []
    for st in stations:
        bs = st.build_storage
        queue = (bs.queue if bs and bs.queue else st.construction_queue)
        builder_id = (bs.assigned_builder if bs and bs.assigned_builder else st.assigned_builder)
        needed = (bs.needed if bs else Counter())
        cargo = (bs.cargo if bs else Counter())
        resv = (bs.reservations if bs else Counter())

        active = next((e for e in queue if e.get("state") == "building"), None)
        pending = [e for e in queue if e.get("state") == "planned"]
        q_len = len(pending)

        builder = "Unassigned"
        if builder_id:
            if builder_id in P.ships:
                b_ship = P.ships[builder_id]
                builder = f"{ship_name(b_ship)} ({b_ship.code or b_ship.id})"
            elif builder_id in P.all_units:
                b_u = P.all_units[builder_id]
                builder = f"{b_u['name']} ({b_u['id']})"
            else: builder = f"Builder [{builder_id}]"

        shortages = []
        for w, need_amt in sorted(needed.items()):
            cur = cargo.get(w, 0)
            incoming = resv.get(w, 0)
            inbound_str = f" (+{num(incoming)})" if incoming > 0 else ""
            if (cur + incoming) < need_amt:
                shortages.append(f"{N.ware(w)}: {num(cur)}{inbound_str}/{num(need_amt)}")
            elif need_amt > 0:
                shortages.append(f"{N.ware(w)}: {num(cur)}{inbound_str}/{num(need_amt)} (OK)")

        unfilled = [s for s in shortages if "(OK)" not in s]
        shortage_str = ", ".join(unfilled) if unfilled else ("All Supplied" if shortages else "None Required")

        building_str = "None"
        if active:
            prog = active.get("progress", 0.0)
            building_str = f"{prettify(active['macro'])} ({prog:.1f}%) [Building]"
        elif pending:
            building_str = f"Standby ({prettify(pending[0]['macro'])}) [Queued]"

        if active or q_len > 0 or unfilled or (builder != "Unassigned" and (needed or queue)):
            bs_rows.append([station_name(st), sname(st.sector), builder, building_str, f"{q_len} planned", shortage_str])

    if bs_rows: md += table(["Station Complex", "Sector", "Assigned Builder", "Active Construction", "Queue Size", "Missing Construction Wares"], bs_rows)
    else: md.append("- *No active station module expansions or construction bottlenecks detected (all existing stations fully completed).*")
    md.append("")

    # 4. STORAGE SATURATION & CHOKE DIAGNOSTICS
    md.append("## 4. Station Storage Saturation & Choke Diagnostics")
    storage_table = []
    for st in sorted(stations, key=lambda x: sname(x.sector)):
        caps = st.storage_capacities()
        if sum(caps.values()) == 0: continue
        c_m3, s_m3, l_m3 = 0.0, 0.0, 0.0
        for w, amt in st.cargo.items():
            vol = N.volume(w) * amt
            if w in SOLID_WARES: s_m3 += vol
            elif w in LIQUID_WARES: l_m3 += vol
            else: c_m3 += vol

        c_pct = (c_m3 / caps["container"] * 100.0) if caps["container"] > 0 else 0.0
        s_pct = (s_m3 / caps["solid"] * 100.0) if caps["solid"] > 0 else 0.0
        l_pct = (l_m3 / caps["liquid"] * 100.0) if caps["liquid"] > 0 else 0.0

        status = "Optimal"
        if c_pct > 92.0 or s_pct > 92.0 or l_pct > 92.0: status = "**CRITICAL CHOKE**"
        elif c_pct > 80.0 or s_pct > 80.0 or l_pct > 80.0: status = "High Saturation"

        storage_table.append([
            station_name(st), sname(st.sector),
            f"{c_pct:4.1f}% ({num(c_m3/1000)}k/{num(caps['container']/1000)}k m³)" if caps['container'] else "-",
            f"{s_pct:4.1f}% ({num(s_m3/1000)}k/{num(caps['solid']/1000)}k m³)" if caps['solid'] else "-",
            f"{l_pct:4.1f}% ({num(l_m3/1000)}k/{num(caps['liquid']/1000)}k m³)" if caps['liquid'] else "-",
            status
        ])
    if storage_table: md += table(["Station Complex", "Sector", "Container Saturation", "Solid Saturation", "Liquid Saturation", "Storage State"], storage_table)
    md.append("")

    # 5. PRODUCTION STARVATION AUDIT
    md.append("## 5. End-to-End Production Starvation & Input Bottlenecks")
    prod_health_table = []
    for st in sorted(stations, key=lambda x: sname(x.sector)):
        if not st.prod: continue
        demands = defaultdict(float)
        for pm in st.prod:
            inputs = N.module_inputs(pm)
            for w, rate in inputs.items(): demands[w] += rate

        starved_inputs, low_inputs = [], []
        for w, rate_hr in demands.items():
            stock = st.cargo.get(w, 0)
            if stock == 0: starved_inputs.append(N.ware(w))
            elif (stock / rate_hr) < 0.5: low_inputs.append(N.ware(w))

        if starved_inputs: state, bottleneck = "**HALTED / STARVING**", "Empty: " + ", ".join(starved_inputs)
        elif low_inputs: state, bottleneck = "At Risk", "Depleting: " + ", ".join(low_inputs)
        else: state, bottleneck = "Self-Sufficient", "All inputs stocked"
        prod_health_table.append([station_name(st), sname(st.sector), len(st.prod), state, bottleneck])

    if prod_health_table: md += table(["Station Complex", "Sector", "Production Modules", "Operational Health", "Diagnostic Bottleneck"], prod_health_table)
    md.append("")

    # 6. LOGICAL OVERVIEW SLIDERS & TRADE RULES
    md.append("## 6. Logical Overview Sliders, Trade Rules & Storage Allocations")
    trade_rows = []
    for st in sorted(stations, key=lambda x: sname(x.sector)):
        offer_prices = {(off["ware"], off["side"]): off["price"] for off in st.offers}
        scan_wares = set(st.trade_wares.keys()) | set(st.cargo.keys())

        for wid in sorted(scan_wares, key=lambda x: N.ware(x)):
            if wid.startswith(("ship_", "inv_")): continue
            tw = st.trade_wares.get(wid, {})
            stock = st.cargo.get(wid, 0)

            sell_t = tw.get("sell_threshold")
            sell_m = tw.get("sell_mode", "auto")
            if sell_t is None or sell_t == -1 or (sell_t == 1 and sell_m == "auto"):
                sell_str = "Auto (Sell Surplus)" if sell_m == "auto" else "Disabled"
            elif sell_t == 0:
                sell_str = "0 (Sell All)"
            else:
                sell_str = f"{num(sell_t)} ({sell_m})"

            buy_t = tw.get("buy_threshold")
            buy_m = tw.get("buy_mode", "auto")
            if buy_t is None or buy_t == -1 or (buy_t == 1 and buy_m == "auto"):
                buy_str = "Max Storage (Auto)" if buy_m == "auto" else "Disabled"
            elif buy_t == 0:
                buy_str = "0 (No Buy)"
            else:
                buy_str = f"{num(buy_t)} ({buy_m})"

            if tw.get("price_mode") == "manual" and tw.get("manual_price"):
                price_str = f"{tw['manual_price']:.2f} Cr (Manual)"
            elif (wid, "sell") in offer_prices:
                price_str = f"{offer_prices[(wid, 'sell')]:.2f} Cr (Sell Auto)"
            elif (wid, "buy") in offer_prices:
                price_str = f"{offer_prices[(wid, 'buy')]:.2f} Cr (Buy Auto)"
            else:
                price_str = f"{N.price(wid):.2f} Cr (Avg Market)"

            rule_id = tw.get("trade_rule_id") or st.default_trade_rule
            rule_name = P.trade_rules.get(rule_id, "Galaxy Open (Default)") if rule_id else "Galaxy Open"
            cap_str = f"{num(tw['allocated_m3'])} m³" if tw.get("allocated_m3") else "Auto Allocation"

            trade_rows.append([
                station_name(st), sname(st.sector), N.ware(wid), num(stock),
                cap_str, sell_str, buy_str, price_str, rule_name
            ])

    if trade_rows:
        md += table(["Station Complex", "Sector", "Ware", "Current Stock", "Allocated Capacity", "Sell All But", "Buy Up To", "Unit Price", "Trade Rule"], trade_rows[:40])
        if len(trade_rows) > 40: md.append(f"- *...and {len(trade_rows) - 40} more ware configuration entries audited.*")
    else: md.append("- *No custom logical overview trade parameters configured.*")
    md.append("")

    # 7. SHIPYARD & WHARF PRODUCTION QUEUES
    md.append("## 7. Shipyard & Wharf Production Slipways")
    sy_rows = []
    for st in sorted(stations, key=lambda x: sname(x.sector)):
        if not st.fabrication_bays and not st.shipyard_queue: continue
        bays_summary = ", ".join(f"{b['size']} Bay" for b in st.fabrication_bays) or "Standard Slipways"

        if st.shipyard_queue:
            for b in st.shipyard_queue:
                sy_rows.append([
                    station_name(st), sname(st.sector), bays_summary, N.ship(b["hull"]),
                    b["client"].upper(), f"{b['progress']:.1f}%", f"{b['time_left_s']}s"
                ])
        else:
            sy_rows.append([station_name(st), sname(st.sector), bays_summary, "Slipways Idle", "Internal / Civilian", "100.0%", "Ready for Orders"])

    if sy_rows: md += table(["Shipyard Facility", "Sector", "Fabrication Bays", "Active Hull / State", "Client Faction", "Assembly Progress", "Time Remaining"], sy_rows)
    else: md.append("- *No shipyard or wharf fabrication bays detected.*")
    md.append("")

    # 8. WORKFORCE CEILINGS & LIFE SUPPORT
    md.append("## 8. Workforce Ceilings, Life Support Timers & Industrial Efficiency")
    wf_rows = []
    for st in sorted(stations, key=lambda x: sname(x.sector)):
        cap = st.workforce_capacity()
        total_wf = sum(st.workforce.values())
        if cap == 0 and total_wf == 0: continue

        sat_pct = (total_wf / cap * 100.0) if cap > 0 else 0.0
        eff_bonus = f"+{sat_pct * 0.25:.1f}%" if total_wf > 0 else "0.0%"

        food_autonomy_list = []
        tot_med_burn = 0.0

        for race, count in st.workforce.items():
            if count <= 0: continue
            diet = SPECIES_DIET_RULES.get(race, SPECIES_DIET_RULES["argon"])
            f_ware, f_burn_1k = diet["food"]
            m_ware, m_burn_1k = diet["meds"]

            food_burn = (count / 1000.0) * f_burn_1k
            tot_med_burn += (count / 1000.0) * m_burn_1k
            f_hrs = (st.cargo.get(f_ware, 0) / food_burn) if food_burn > 0 else 999.0
            food_autonomy_list.append(f"{N.ware(f_ware)}: {f_hrs:.1f}h")

        med_hrs = (st.cargo.get("medicalsupplies", 0) / tot_med_burn) if tot_med_burn > 0 else 999.0
        food_str = ", ".join(food_autonomy_list) if food_autonomy_list else "Self-Sustaining"

        wf_rows.append([
            station_name(st), sname(st.sector), f"{num(total_wf)} / {num(cap)}",
            f"{sat_pct:.1f}%", eff_bonus, food_str, f"{med_hrs:.1f}h"
        ])

    if wf_rows: md += table(["Station Complex", "Sector", "Workforce / Habitat Capacity", "Saturation", "Productivity Bonus", "Species Food Autonomy", "Medical Supplies Autonomy"], wf_rows)
    md.append("")

    # 9. GALACTIC THREAT MATRIX & BALANCE OF POWER (DYNAMIC DIPLOMACY)
    md.append("## 9. Galactic Threat Matrix & Balance of Power")
    total_hostile_stations = sum(sum(v for k, v in cnt.items() if k[2] == "STATION") for cnt in P.hostile.values())
    total_hostile_capitals = sum(sum(v for k, v in cnt.items() if k[2] in ("XL", "L")) for cnt in P.hostile.values())
    total_hostile_strikecraft = sum(sum(v for k, v in cnt.items() if k[2] in ("M", "S")) for cnt in P.hostile.values())

    hostile_capitals_by_faction = defaultdict(int)
    for cnt in P.hostile.values():
        for (owner, macro, sz), count in cnt.items():
            if sz in ("XL", "L"):
                hostile_capitals_by_faction[owner.upper()] += count

    our_battleships = sum(1 for s in warships if s.weight_key == "XL_BATTLESHIP")
    our_carriers = sum(1 for s in warships if "CARRIER" in s.weight_key)
    our_destroyers = sum(1 for s in warships if s.weight_key == "L_DESTROYER")

    hostile_faction_breakdown = ", ".join(f"{count} {fac}" for fac, count in sorted(hostile_capitals_by_faction.items(), key=lambda x: -x[1])) or "None Detected"
    carrier_str = f" | **{our_carriers} Carriers**" if our_carriers else ""

    md.append(f"- **Detected Galactic Threat:** {total_hostile_capitals} Hostile Capital Ships (XL/L) | {total_hostile_strikecraft} Strike Craft | {total_hostile_stations} Fortresses/Stations")
    md.append(f"- **Capital Balance of Power:**")
    md.append(f"  - Player Fleet: **{our_battleships} Battleships**{carrier_str} | **{our_destroyers} Destroyers**")
    md.append(f"  - Hostile Capital Distribution: **{hostile_faction_breakdown}**")
    md.append("\nGate proximity from player installations to nearest hostile frontline:\n")

    occupied_sids = sorted(
        {s.sector for s in ships if s.sector} | {st.sector for st in stations if st.sector},
        key=lambda x: threat_hops.get(x, 99)
    )

    threat_table = []
    for sid in occupied_sids:
        hops = threat_hops.get(sid, 999)
        h_cnt = P.hostile.get(sid, Counter())
        h_caps = [f"{cnt}x {N.ship(macro)} ({owner.upper()})" for (owner, macro, sz), cnt in h_cnt.items() if sz in ("XL", "L")]
        h_stn = sum(cnt for (owner, macro, sz), cnt in h_cnt.items() if sz == "STATION")

        if hops == 0 or h_caps or h_stn: status, posture = "`CRITICAL FRONT`", "Active Incursion / Hot War Zone"
        elif hops == 1: status, posture = "`HIGH RISK`", "Direct Gate Connection to Frontline"
        elif hops <= 3: status, posture = "`GUARDED`", "Buffer Perimeter Patrol"
        else: status, posture = "`SECURE`", "Deep Sovereign Interior"

        our_mil = sum(1 for s in warships if s.sector == sid)
        our_civ = sum(1 for s in ships if s.sector == sid and s.category != "Military")
        our_stn = sum(1 for st in stations if st.sector == sid)
        force_summary = f"{our_mil} Warships / {our_stn} Bases"
        if our_mil == 0 and our_civ > 0: force_summary += f" ({our_civ} Civilian Vessels)"

        threat_table.append([
            sname(sid), status, f"**{hops} Hops**" if hops < 999 else "Isolated",
            ", ".join(h_caps) if h_caps else ("Base Threat" if h_stn else "Clear"),
            force_summary, posture
        ])
    md += table(["Sector", "Threat Level", "Front Distance", "Detected Hostiles", "Our Defense Force", "Defense Posture"], threat_table)
    md.append("")

    # 10. ACTIVE COMBAT TRIAGE & VECTORS
    md.append(f"## 10. Active Combat Vectors & Engagement Triage ({int(COMBAT_ENGAGEMENT_WINDOW)}s Live Window)")
    combat_rows = []
    for s in ships:
        is_combat = (s.attacktime and (save_time - s.attacktime) < COMBAT_ENGAGEMENT_WINDOW)
        target_info = P.resolve_combat_target(s, N)
        if is_combat or target_info != "Standby / Clear" or s.hull_pct < 98.0:
            status = "**UNDER FIRE**" if is_combat else ("Damaged" if s.hull_pct < 98.0 else "Engaged")
            combat_rows.append([
                ship_name(s), s.code, sname(s.sector), f"{s.hull_pct:.1f}%", f"{s.shield_pct:.0f}%",
                status, P.activity(s), target_info
            ])

    if combat_rows:
        md += table(["Ship Name", "Code", "Sector", "Hull", "Shield", "Combat State", "Current Order", "Engagement Vector"], combat_rows)
    else: md.append("- *All naval assets are currently out of hostile contact and reporting green status.*")
    md.append("")

    # 11. COMBAT CASUALTIES & LOGBOOK
    md.append("## 11. Combat Casualties & Logbook Destruction Feed")
    if P.recent_losses:
        loss_table = []
        for t_val, title, text in reversed(P.recent_losses[-15:]):
            hrs_ago = (save_time - t_val) / 3600.0 if save_time >= t_val else 0.0
            loss_table.append([f"{hrs_ago:.1f}h ago", N.text(title), N.text(text)])
        md += table(["Time", "Incident", "Log Details"], loss_table)
    md.append("")

    # 12. SHIP EQUIPMENT & LOADOUT AUDIT
    md.append("## 12. Warship Loadout & Equipment Audit")
    eq_rows = []
    for s in sorted(warships, key=lambda x: (x.size != "XL", x.size != "L", ship_name(x))):
        shield_str = f"{s.parts['shieldgenerator']}x Shields"
        if s.installed_shields:
            shield_str = ", ".join(f"{cnt}x {prettify(m)}" for m, cnt in s.installed_shields.items())
        elif s.parts['shieldgenerator'] == 0:
            shield_str = "**NO SHIELDS INSTALLED (0 SLOTS)**"

        engine_str = ", ".join(f"{cnt}x {prettify(m)}" for m, cnt in s.installed_engines.items()) if s.installed_engines else "Standard Engines"
        weap_summary = []
        if s.installed_weapons: weap_summary.append("Main: " + ", ".join(f"{cnt}x {prettify(m)}" for m, cnt in s.installed_weapons.items()))
        if s.installed_turrets: weap_summary.append("Turrets: " + ", ".join(f"{cnt}x {prettify(m)}" for m, cnt in s.installed_turrets.items()))
        full_weap = " | ".join(weap_summary) if weap_summary else "Unarmed"

        eq_rows.append([ship_name(s), s.size, s.role, shield_str, f"{s.shield_pct:.0f}%", engine_str, full_weap])

    if eq_rows: md += table(["Warship", "Size", "Role", "Shield Loadout", "Shield State", "Engines", "Weapons & Turret Battery"], eq_rows[:25])
    md.append("")

    # 13. TOP FLEET ACES
    md.append("## 13. Personnel Excellence: Top Pilots & Fleet Aces")
    pilots = []
    for s in ships:
        if s.pilot_id and s.pilot_skills:
            pilots.append((s.pilot_skills.get("piloting", 0), s.pilot_skills.get("morale", 0), s.pilot_name, ship_name(s), sname(s.sector)))
    pilots.sort(key=lambda x: (-x[0], -x[1]))

    pilot_rows = [[name, f"{p_sk}/15", f"{m_sk}/15", s_nm, sec] for p_sk, m_sk, name, s_nm, sec in pilots[:10]]
    if pilot_rows: md += table(["Pilot Name", "Piloting Skill", "Morale", "Assigned Vessel", "Current Sector"], pilot_rows)
    md.append("")

    # 14. STATIONS & ASSIGNED SUBORDINATES
    md.append("## 14. Stations & Assigned Subordinate Wings (In-Game Menu Parity)")
    for st in sorted(stations, key=lambda x: (sname(x.sector), station_name(x))):
        st_treasury = sum(a["amount"] for a in st.accounts)
        md.append(f"\n### {station_name(st)} — [{sname(st.sector)}] ({st.role})")
        md.append(f"- **Operating Balance:** {num(st_treasury)} Cr | Hull Integrity: `{st.hull_pct:.1f}%`")
        if st.manager:
            mgmt_skill = st.manager["skills"].get("management", 0)
            md.append(f"- **Station Director:** {st.manager['name']} (Management: {mgmt_skill}/15)")

        weapons = [f"{cnt}x {k}" for k, cnt in st.gear_types.most_common() if cnt > 0]
        sh_count = sum(v for k, v in st.gear.items() if k[0] == "shieldgenerator")
        tu_count = sum(v for k, v in st.gear.items() if k[0] in ("turret", "missileturret"))
        def_str = f"{sum(st.defence.values())} defence modules" if st.defence else "0 defence modules"
        md.append(f"- **Fortifications:** {def_str} | {sh_count} shields | {tu_count} turrets (Battery: {', '.join(weapons) if weapons else 'Standard'})")

        sub_ids = P.descendants(st.id)
        if sub_ids:
            md.append(f"- **Assigned Subordinates ({len(sub_ids)} vessels total):**")
            grouped_subs = defaultdict(lambda: defaultdict(int))
            for sub_id in sub_ids:
                if sub_id in P.ships:
                    sub = P.ships[sub_id]
                    grouped_subs[sub.assignment][(N.ship(sub.macro), sub.role, sub.size)] += 1

            for wing, models in sorted(grouped_subs.items()):
                md.append(f"  - **Wing: {wing} ({sum(models.values())} craft):**")
                for (m_name, r_name, sz), count in sorted(models.items(), key=lambda x: -x[1]):
                    md.append(f"    - {count}x **{m_name}** ({r_name}, {sz})")
        else:
            md.append("- **Assigned Subordinates:** None")

        if st.cargo:
            stock = [(N.ware(w), cnt) for w, cnt in st.cargo.items() if not w.startswith(("ship_", "inv_"))]
            top_stock = sorted(stock, key=lambda x: -x[1])[:10]
            md.append("- **Stockpile:** " + ", ".join(f"{w} {num(n)}" for w, n in top_stock))
    md.append("")

    # 15. DERELICT & DATA VAULT RECONNAISSANCE
    md.append("## 15. High-Value Derelict & Data Vault Reconnaissance")
    recon_rows = []
    for d in sorted(P.derelicts, key=lambda x: (sname(x['sector']), N.ship(x['macro']))):
        recon_rows.append([sname(d['sector']), N.ship(d['macro']), d['size'], "Derelict Hull", f"({d['pos'][0]/1000.0:.1f}km, {d['pos'][1]/1000.0:.1f}km, {d['pos'][2]/1000.0:.1f}km)", "Claimable" if d['known'] else "Unsurveyed", d['id']])
    for v in sorted(P.datavaults, key=lambda x: sname(x['sector'])):
        kind = "Erlking Vault" if v["erlking"] else "Standard Data Vault"
        payload = f"Blueprint: {prettify(v['blueprint'])}" if v["blueprint"] else ("Erlking Blueprint" if v["erlking"] else "Data / Loot")
        recon_rows.append([sname(v['sector']), kind, "Vault", payload, f"({v['pos'][0]/1000.0:.1f}km, {v['pos'][1]/1000.0:.1f}km, {v['pos'][2]/1000.0:.1f}km)", "Unlocked" if v["unlocked"] else "Sealed", v['id']])
    md += table(["Sector", "Target Object", "Class", "Payload", "Coordinates (Sector-Relative)", "Intel Status", "Component ID"], recon_rows)
    md.append("")

    # 16. TRADE ANALYZER & COMMERCIAL EFFICIENCY (MOD 1801 PARITY)
    completed_trades, ship_profits, ware_profits, inactive_traders = process_trade_analytics(P, N)
    md.append("## 16. Commercial Trade Performance & Profit Analyzer (Nexus Mod 1801 Parity)")
    total_trade_profit = sum(t.net_profit for t in completed_trades)
    external_trade_profit = sum(t.net_profit for t in completed_trades if not t.is_internal)
    md.append(f"- **Total Realized Net Profit:** **{num(total_trade_profit)} Cr** (External NPC Profit: **{num(external_trade_profit)} Cr**)")
    md.append(f"- **Completed Trade Cycles Logged:** **{len(completed_trades)} cycles** | **{len(P.all_transactions)} priceable transaction records**")
    if P.trade_state_log_count:
        md.append(f"- **Unpriced Trade-State Events:** **{num(P.trade_state_log_count)} player-owned events** (stock-state records contain no transaction price or buy/sell direction, so they are excluded from profit totals).\n")
    else:
        md.append("")

    top_ships_table = []
    for s_id, data in sorted(ship_profits.items(), key=lambda x: -x[1]["profit"])[:12]:
        s_obj = P.ships.get(s_id)
        s_title = ship_name(s_obj) if s_obj else f"Trader [{s_id}]"
        s_role = s_obj.role if s_obj else "Commercial Vessel"
        s_cmd = sname(s_obj.sector) if s_obj else "Galaxy Transit"
        avg_util = sum(data["util_acc"]) / len(data["util_acc"]) if data["util_acc"] else 0.0
        top_ships_table.append([
            s_title, s_role, s_cmd, f"{num(data['profit'])} Cr",
            f"{num(data['ext_profit'])} Cr", str(data["trades"]), f"{avg_util:.1f}%"
        ])

    if top_ships_table:
        md.append("### Top Earning Trade & Mining Ships")
        md += table(["Ship Name", "Role", "Operating Sector", "Total Net Profit", "External NPC Margin", "Trades Run", "Avg Cargo Utilization"], top_ships_table)
        md.append("")

    top_wares_table = []
    for wid, data in sorted(ware_profits.items(), key=lambda x: -x[1]["profit"])[:10]:
        top_wares_table.append([
            N.ware(wid), num(data["volume"]), f"{num(data['revenue'])} Cr",
            f"{num(data['profit'])} Cr", str(data["trades"])
        ])

    if top_wares_table:
        md.append("### High-Value Commercial Commodities (Empire Cash Cows)")
        md += table(["Commodity Ware", "Units Sold", "Gross Revenue", "Realized Net Profit", "Transactions"], top_wares_table)
        md.append("")

    if inactive_traders:
        md.append("### Inactive / Stalled Trade Fleet Warning (> 2h without Trades)")
        inact_rows = [[ship_name(s), s.role, sname(s.sector), P.activity(s), f"{hrs:.1f} hours" if hrs < 990 else "No Logged Trades"] for s, hrs in inactive_traders[:10]]
        md += table(["Ship Name", "Role", "Sector", "Current Activity", "Idle Time"], inact_rows)
        md.append("")

    # 17. TREASURY SKIMMING
    md.append("## 17. Corporate Treasury Skimming & War Chest Transfer")
    md.append(f"Commander Wallet: **{num(purse)} Cr** | Empire Liquid Surplus: **{num(total_skimmable)} Cr**\n")
    if station_skim_data: md += table(["Station Complex", "Sector", "Current Account", "Recommended Operating Reserve", "Surplus Capital Available"], station_skim_data)
    md.append("")

    return "\n".join(md), grand_total_net_worth, total_liquid, fleet_capital, real_estate, stockpile_val

# ==============================================================================
# UNIFIED ALL-IN-ONE WEB TERMINAL (HTML + RADAR + FULL DOSSIER TABS)
# ==============================================================================
def generate_command_terminal_html(P, N, output_html, net_worth, liquid, fleet_val, st_val, stock_val):
    save_time = float(P.info.get("time") or 0)
    def sname(sid): return N.sector(P.sectors.get(sid)) if sid else "Unknown / Transit"
    def ship_name(s):
        nm = N.text(s.name) if s.name else ""
        return nm if nm and not REF_REGEX.search(nm) else N.ship(s.macro)
    def station_name(st):
        nm = N.text(st.name) if st.name else ""
        return nm if nm and not REF_REGEX.search(nm) else st.role

    entities = []
    for st in P.stations.values():
        subs_cnt = len(P.descendants(st.id))
        entities.append({
            "id": st.id, "name": station_name(st), "code": st.code, "type": "station", "role": st.role,
            "sector": sname(st.sector), "sector_id": st.sector, "x": round(st.pos[0] / 1000.0, 1),
            "y": round(st.pos[1] / 1000.0, 1), "z": round(st.pos[2] / 1000.0, 1), "hull": round(st.hull_pct, 1),
            "shield": 100.0, "subordinates": subs_cnt, "details": f"{st.role} | Subordinates: {subs_cnt} hulls"
        })

    for s in P.ships.values():
        is_combat = (s.attacktime and (save_time - s.attacktime) < COMBAT_ENGAGEMENT_WINDOW)
        entities.append({
            "id": s.id, "name": ship_name(s), "code": s.code, "type": "player_ship", "category": s.category,
            "size": s.size, "role": s.role, "sector": sname(s.sector), "sector_id": s.sector,
            "x": round(s.pos[0] / 1000.0, 1), "y": round(s.pos[1] / 1000.0, 1), "z": round(s.pos[2] / 1000.0, 1),
            "hull": round(s.hull_pct, 1), "shield": round(s.shield_pct, 1), "assignment": s.assignment,
            "order": P.activity(s), "under_fire": bool(is_combat), "details": f"{s.role} ({s.size}) | Vector: {P.resolve_combat_target(s, N)}"
        })

    for h in P.hostile_units:
        entities.append({
            "id": h["id"], "name": N.ship(h["macro"]), "code": f"{h['owner'].upper()}-THREAT", "type": "hostile", "size": h["size"],
            "role": "Hostile Warship" if h["type"]=="ship" else "Hostile Platform", "sector": sname(h["sector"]),
            "sector_id": h["sector"], "x": round(h["pos"][0] / 1000.0, 1), "y": round(h["pos"][1] / 1000.0, 1),
            "z": round(h["pos"][2] / 1000.0, 1), "hull": 100.0, "shield": 100.0, "details": f"THREAT: {h['owner'].upper()} {h['size']}"
        })

    for d in P.derelicts:
        entities.append({
            "id": d["id"], "name": f"Derelict {N.ship(d['macro'])}", "code": d["id"], "type": "derelict", "size": d["size"],
            "role": "Abandoned Derelict", "sector": sname(d["sector"]), "sector_id": d["sector"], "claimable": d["known"],
            "x": round(d["pos"][0] / 1000.0, 1), "y": round(d["pos"][1] / 1000.0, 1), "z": round(d["pos"][2] / 1000.0, 1),
            "details": f"Unclaimed Hull ({d['size']}) | Status: {'Claimable' if d['known'] else 'Unsurveyed'}"
        })

    for v in P.datavaults:
        entities.append({
            "id": v["id"], "name": "Erlking Vault" if v["erlking"] else "Data Vault", "code": v["id"], "type": "vault",
            "erlking": v["erlking"], "role": "Data Vault", "sector": sname(v["sector"]), "sector_id": v["sector"],
            "blueprint": prettify(v["blueprint"]) if v["blueprint"] else None,
            "x": round(v["pos"][0] / 1000.0, 1), "y": round(v["pos"][1] / 1000.0, 1), "z": round(v["pos"][2] / 1000.0, 1),
            "details": f"Blueprint: {prettify(v['blueprint'])}" if v['blueprint'] else "Data Vault Beacon"
        })

    for g in P.gates:
        entities.append({
            "id": g["id"], "name": "Jump Gate / Accelerator", "code": g["id"], "type": "gate", "role": "Navigation Gate",
            "sector": sname(g["sector"]), "sector_id": g["sector"], "x": round(g["pos"][0] / 1000.0, 1),
            "y": round(g["pos"][1] / 1000.0, 1), "z": round(g["pos"][2] / 1000.0, 1), "details": "Hyperlane Jump Gate"
        })

    sectors_list = sorted({e["sector"] for e in entities if e["sector"] and "Unknown" not in e["sector"]})

    hostile_sids = {sid for sid, cnt in P.hostile.items() if sid and any(k[2] in ("XL", "L", "STATION") for k in cnt)}
    threat_hops = {}
    q = deque()
    for f in hostile_sids: threat_hops[f] = 0; q.append(f)
    while q:
        curr = q.popleft()
        for neighbor in P.adj.get(curr, ()):
            if neighbor not in threat_hops: threat_hops[neighbor] = threat_hops[curr] + 1; q.append(neighbor)

    occupied_sids = sorted({s.sector for s in P.ships.values() if s.sector} | {st.sector for st in P.stations.values() if st.sector}, key=lambda x: threat_hops.get(x, 99))
    threat_rows = []
    for sid in occupied_sids:
        hops = threat_hops.get(sid, 999)
        h_cnt = P.hostile.get(sid, Counter())
        h_caps = [f"{cnt}x {N.ship(m)} ({o.upper()})" for (o, m, sz), cnt in h_cnt.items() if sz in ("XL", "L")]
        threat_rows.append({
            "sector": sname(sid), "hops": hops if hops < 999 else "Isolated",
            "threat": "CRITICAL" if (hops==0 or h_caps) else ("HIGH RISK" if hops==1 else ("GUARDED" if hops<=3 else "SECURE")),
            "hostiles": ", ".join(h_caps) if h_caps else "Clear",
            "forces": f"{sum(1 for s in P.ships.values() if s.sector==sid and s.category=='Military')} Warships | {sum(1 for st in P.stations.values() if st.sector==sid)} Bases"
        })

    combat_triage = [
        {
            "name": ship_name(s), "code": s.code, "sector": sname(s.sector),
            "hull": round(s.hull_pct, 1), "shield": round(s.shield_pct, 1),
            "combat": bool(s.attacktime and (save_time - s.attacktime) < COMBAT_ENGAGEMENT_WINDOW),
            "order": P.activity(s), "vector": P.resolve_combat_target(s, N)
        }
        for s in P.ships.values()
        if (s.attacktime and (save_time - s.attacktime) < COMBAT_ENGAGEMENT_WINDOW) or s.hull_pct < 98.0 or P.resolve_combat_target(s, N) != "Standby / Clear"
    ]

    losses = [
        {"time": f"{(save_time - t)/3600.0:.1f}h ago", "title": N.text(ti), "text": N.text(tx)}
        for t, ti, tx in reversed(P.recent_losses[-20:])
    ]

    construction_diag = []
    for st in P.stations.values():
        bs = st.build_storage
        queue = (bs.queue if bs and bs.queue else st.construction_queue)
        builder_id = (bs.assigned_builder if bs and bs.assigned_builder else st.assigned_builder)
        needed = (bs.needed if bs else Counter())
        cargo = (bs.cargo if bs else Counter())
        resv = (bs.reservations if bs else Counter())

        active = next((e for e in queue if e.get("state") == "building"), None)
        pending = [e for e in queue if e.get("state") == "planned"]
        q_len = len(pending)

        builder = "Unassigned"
        if builder_id:
            if builder_id in P.ships:
                b_ship = P.ships[builder_id]
                builder = f"{ship_name(b_ship)} ({b_ship.code or b_ship.id})"
            elif builder_id in P.all_units:
                b_u = P.all_units[builder_id]
                builder = f"{b_u['name']} ({b_u['id']})"
            else: builder = f"Builder [{builder_id}]"

        shortages = []
        for w, need_amt in sorted(needed.items()):
            cur = cargo.get(w, 0)
            incoming = resv.get(w, 0)
            inbound_str = f" (+{num(incoming)})" if incoming > 0 else ""
            if (cur + incoming) < need_amt:
                shortages.append(f"{N.ware(w)}: {num(cur)}{inbound_str}/{num(need_amt)}")
            elif need_amt > 0:
                shortages.append(f"{N.ware(w)}: {num(cur)}{inbound_str}/{num(need_amt)} (OK)")

        unfilled = [s for s in shortages if "(OK)" not in s]
        shortage_str = ", ".join(unfilled) if unfilled else ("All Supplied" if shortages else "None Required")

        building_str = "None"
        if active:
            building_str = f"{prettify(active['macro'])} ({active.get('progress', 0.0):.1f}%) [Building]"
        elif pending:
            building_str = f"Standby ({prettify(pending[0]['macro'])}) [Queued]"

        if active or q_len > 0 or unfilled or (builder != "Unassigned" and (needed or queue)):
            construction_diag.append({
                "station": station_name(st), "sector": sname(st.sector),
                "builder": builder, "building": building_str,
                "queue": f"{q_len} planned", "shortages": shortage_str
            })

    if not construction_diag:
        construction_diag.append({
            "station": "All Corporate Platforms", "sector": "Empire Wide",
            "builder": "None Needed", "building": "All Stations Completed",
            "queue": "0 planned", "shortages": "None Required"
        })

    shipyard_diag = []
    for st in sorted(P.stations.values(), key=lambda x: sname(x.sector)):
        if not st.fabrication_bays and not st.shipyard_queue: continue
        bays_str = ", ".join(f"{b['size']} Bay" for b in st.fabrication_bays) or "Standard Slipways"
        if st.shipyard_queue:
            for b in st.shipyard_queue:
                shipyard_diag.append({
                    "station": station_name(st), "sector": sname(st.sector), "bays": bays_str,
                    "hull": N.ship(b["hull"]), "client": b["client"].upper(),
                    "progress": b["progress"], "time": b["time_left_s"]
                })
        else:
            shipyard_diag.append({
                "station": station_name(st), "sector": sname(st.sector), "bays": bays_str,
                "hull": "Slipways Idle", "client": "Internal / Civilian",
                "progress": 100.0, "time": 0
            })

    skimming_diag = []
    total_skimmable = 0
    for st in P.stations.values():
        bal = sum(a["amount"] for a in st.accounts)
        reserve = 50_000_000 if "Shipyard" in st.role else (20_000_000 if st.prod else 10_000_000)
        surplus = max(0, bal - reserve)
        total_skimmable += surplus
        if surplus > 5_000_000:
            skimming_diag.append({"station": station_name(st), "sector": sname(st.sector), "balance": num(bal), "reserve": num(reserve), "surplus": num(surplus)})

    storage_diag = []
    for st in sorted(P.stations.values(), key=lambda x: sname(x.sector)):
        caps = st.storage_capacities()
        if sum(caps.values()) == 0: continue
        c_m3 = sum(N.volume(w)*a for w, a in st.cargo.items() if w not in SOLID_WARES and w not in LIQUID_WARES)
        s_m3 = sum(N.volume(w)*a for w, a in st.cargo.items() if w in SOLID_WARES)
        l_m3 = sum(N.volume(w)*a for w, a in st.cargo.items() if w in LIQUID_WARES)
        storage_diag.append({
            "station": station_name(st), "sector": sname(st.sector),
            "cPct": round(c_m3 / caps["container"] * 100.0, 1) if caps["container"] else 0,
            "sPct": round(s_m3 / caps["solid"] * 100.0, 1) if caps["solid"] else 0,
            "lPct": round(l_m3 / caps["liquid"] * 100.0, 1) if caps["liquid"] else 0
        })

    prod_diag = []
    for st in sorted(P.stations.values(), key=lambda x: sname(x.sector)):
        if not st.prod: continue
        demands = defaultdict(float)
        for pm in st.prod:
            for w, rate in N.module_inputs(pm).items(): demands[w] += rate
        starved, low = [], []
        for w, r_hr in demands.items():
            stock = st.cargo.get(w, 0)
            if stock == 0: starved.append(N.ware(w))
            elif (stock / r_hr) < 0.5: low.append(N.ware(w))
        status = "HALTED" if starved else ("AT RISK" if low else "OPTIMAL")
        prod_diag.append({"station": station_name(st), "sector": sname(st.sector), "status": status, "bottleneck": ", ".join(starved or low) or "Fully Stocked"})

    trade_diag = []
    for st in sorted(P.stations.values(), key=lambda x: sname(x.sector)):
        offer_prices = {(off["ware"], off["side"]): off["price"] for off in st.offers}
        scan_wares = set(st.trade_wares.keys()) | set(st.cargo.keys())
        for wid in sorted(scan_wares, key=lambda x: N.ware(x)):
            if wid.startswith(("ship_", "inv_")): continue
            tw = st.trade_wares.get(wid, {})
            sell_t = tw.get("sell_threshold")
            sell_m = tw.get("sell_mode", "auto")
            if sell_t is None or sell_t == -1 or (sell_t == 1 and sell_m == "auto"):
                sell_str = "Auto (Sell Surplus)" if sell_m == "auto" else "Disabled"
            elif sell_t == 0:
                sell_str = "0 (Sell All)"
            else:
                sell_str = f"{num(sell_t)} ({sell_m})"

            buy_t = tw.get("buy_threshold")
            buy_m = tw.get("buy_mode", "auto")
            if buy_t is None or buy_t == -1 or (buy_t == 1 and buy_m == "auto"):
                buy_str = "Max Storage (Auto)" if buy_m == "auto" else "Disabled"
            elif buy_t == 0:
                buy_str = "0 (No Buy)"
            else:
                buy_str = f"{num(buy_t)} ({buy_m})"

            if tw.get("price_mode") == "manual" and tw.get("manual_price"):
                price_str = f"{tw['manual_price']:.2f} Cr (Manual)"
            elif (wid, "sell") in offer_prices:
                price_str = f"{offer_prices[(wid, 'sell')]:.2f} Cr (Sell Auto)"
            elif (wid, "buy") in offer_prices:
                price_str = f"{offer_prices[(wid, 'buy')]:.2f} Cr (Buy Auto)"
            else:
                price_str = f"{N.price(wid):.2f} Cr (Avg Market)"

            rule_id = tw.get("trade_rule_id") or st.default_trade_rule
            rule_name = P.trade_rules.get(rule_id, "Galaxy Open (Default)") if rule_id else "Galaxy Open"

            trade_diag.append({
                "station": station_name(st), "sector": sname(st.sector), "ware": N.ware(wid),
                "stock": num(st.cargo.get(wid, 0)), "capacity": f"{num(tw['allocated_m3'])} m³" if tw.get('allocated_m3') else "Auto Allocation",
                "sell": sell_str, "buy": buy_str, "price": price_str, "rule": rule_name
            })

    completed_trades, ship_profits, ware_profits, inactive_traders = process_trade_analytics(P, N)
    trade_analytics_payload = {
        "trades": [
            {
                "ship": ship_name(P.ships[t.ship_id]) if t.ship_id in P.ships else t.ship_id,
                "ware": N.ware(t.ware),
                "amount": t.amount,
                "profit": t.net_profit,
                "margin": t.margin_pct,
                "internal": t.is_internal,
                "buy_sec": sname(t.buy_sector),
                "sell_sec": sname(t.sell_sector),
                "util": t.util_pct
            }
            for t in completed_trades[:80]
        ],
        "top_ships": [
            {
                "name": ship_name(P.ships[s_id]) if s_id in P.ships else s_id,
                "profit": d["profit"],
                "ext_profit": d["ext_profit"],
                "trades": d["trades"],
                "avg_util": round(sum(d["util_acc"]) / len(d["util_acc"]), 1) if d["util_acc"] else 0.0
            }
            for s_id, d in sorted(ship_profits.items(), key=lambda x: -x[1]["profit"])[:12]
        ],
        "top_wares": [
            {
                "ware": N.ware(wid),
                "profit": d["profit"],
                "revenue": d["revenue"],
                "volume": d["volume"]
            }
            for wid, d in sorted(ware_profits.items(), key=lambda x: -x[1]["profit"])[:10]
        ]
    }

    loadout_diag = []
    for s in sorted(P.ships.values(), key=lambda x: (x.category != "Military", x.size != "XL", x.size != "L", ship_name(x))):
        if s.category != "Military" and s.size not in ("XL", "L"): continue
        sh_str = ", ".join(f"{cnt}x {prettify(m)}" for m, cnt in s.installed_shields.items()) if s.installed_shields else (f"{s.parts['shieldgenerator']}x Shields" if s.parts['shieldgenerator'] > 0 else "NO SHIELDS (0 Slots)")
        eng_str = ", ".join(f"{cnt}x {prettify(m)}" for m, cnt in s.installed_engines.items()) if s.installed_engines else "Standard Engines"
        weap_list = [f"{cnt}x {prettify(m)}" for m, cnt in s.installed_weapons.items()]
        turr_list = [f"{cnt}x {prettify(m)}" for m, cnt in s.installed_turrets.items()]
        w_str = ", ".join(weap_list) if weap_list else ("Unarmed" if not turr_list else "Turrets Only")
        t_str = ", ".join(turr_list) if turr_list else "None"
        loadout_diag.append({
            "name": ship_name(s), "code": s.code, "size": s.size, "role": s.role, "sector": sname(s.sector),
            "shields": sh_str, "shieldPct": round(s.shield_pct, 1), "engines": eng_str, "weapons": w_str, "turrets": t_str
        })

    hierarchy_diag = []
    for st in sorted(P.stations.values(), key=lambda x: (sname(x.sector), station_name(x))):
        sub_ids = P.descendants(st.id)
        grouped_subs = defaultdict(lambda: defaultdict(int))
        for sub_id in sub_ids:
            if sub_id in P.ships:
                sub = P.ships[sub_id]
                grouped_subs[sub.assignment][(N.ship(sub.macro), sub.role, sub.size)] += 1
        wings = []
        for w_name, models in sorted(grouped_subs.items()):
            ships_in_wing = [{"name": m_name, "role": r_name, "size": sz, "count": count} for (m_name, r_name, sz), count in sorted(models.items(), key=lambda x: -x[1])]
            wings.append({"wing": w_name, "total": sum(models.values()), "ships": ships_in_wing})
        dir_str = f"{st.manager['name']} (Mgmt: {st.manager['skills'].get('management', 0)}/15)" if st.manager else "None"
        sh_count = sum(v for k, v in st.gear.items() if k[0] == "shieldgenerator")
        tu_count = sum(v for k, v in st.gear.items() if k[0] in ("turret", "missileturret"))
        fort_str = f"{sum(st.defence.values())} def modules, {sh_count} shields, {tu_count} turrets"
        hierarchy_diag.append({
            "name": station_name(st), "sector": sname(st.sector), "role": st.role, "hull": round(st.hull_pct, 1),
            "balance": num(sum(a["amount"] for a in st.accounts)), "director": dir_str, "fortifications": fort_str,
            "subCount": len(sub_ids), "wings": wings
        })

    aces_diag = []
    pilots = []
    for s in P.ships.values():
        if s.pilot_id and s.pilot_skills:
            pilots.append((s.pilot_skills.get("piloting", 0), s.pilot_skills.get("morale", 0), s.pilot_name, ship_name(s), sname(s.sector)))
    pilots.sort(key=lambda x: (-x[0], -x[1]))
    for p_sk, m_sk, p_nm, s_nm, sec in pilots[:15]:
        aces_diag.append({"name": p_nm, "piloting": f"{p_sk}/15", "morale": f"{m_sk}/15", "ship": s_nm, "sector": sec})

    terminal_template = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>X4: FOUNDATIONS — SUPREME COMMAND TERMINAL V1.7.6 ENTERPRISE</title>
<style>
  :root {
    --bg-dark: #070b12; --panel-bg: rgba(13, 20, 32, 0.95); --border-color: #1a2f47;
    --accent-cyan: #00f0ff; --accent-blue: #0088ff; --accent-red: #ff3344;
    --accent-gold: #ffbe3b; --accent-purple: #c359ff; --accent-green: #00ff88;
    --text-main: #d2e4f5; --text-dim: #6c8ca8;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', system-ui, sans-serif; }
  body { background: var(--bg-dark); color: var(--text-main); height: 100vh; overflow: hidden; display: flex; flex-direction: column; }
  header { background: #05080e; border-bottom: 1px solid var(--border-color); padding: 10px 20px; display: flex; align-items: center; justify-content: space-between; }
  .logo { font-size: 1.1rem; font-weight: 800; letter-spacing: 2px; color: var(--accent-cyan); display: flex; align-items: center; gap: 10px; }
  .logo-tag { font-size: 0.65rem; background: rgba(0,240,255,0.15); border: 1px solid var(--accent-cyan); padding: 2px 6px; border-radius: 4px; }
  
  nav { display: flex; gap: 6px; }
  .nav-btn { background: #0c1524; border: 1px solid var(--border-color); color: var(--text-dim); padding: 7px 16px; border-radius: 4px; cursor: pointer; font-size: 0.82rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; transition: 0.2s; }
  .nav-btn:hover { border-color: var(--accent-cyan); color: #fff; }
  .nav-btn.active { background: rgba(0,240,255,0.15); border-color: var(--accent-cyan); color: var(--accent-cyan); }

  .content-area { flex: 1; position: relative; overflow: hidden; }
  .tab-pane { display: none; width: 100%; height: 100%; overflow-y: auto; padding: 24px; }
  .tab-pane.active { display: block; }
  #tab-radar { padding: 0; overflow: hidden; }

  .grid-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
  .metric-card { background: var(--panel-bg); border: 1px solid var(--border-color); border-radius: 6px; padding: 18px; }
  .metric-title { font-size: 0.75rem; text-transform: uppercase; color: var(--text-dim); letter-spacing: 1px; }
  .metric-val { font-size: 1.5rem; font-weight: 800; color: #fff; margin-top: 6px; }
  .metric-sub { font-size: 0.8rem; color: var(--accent-cyan); margin-top: 4px; }

  .panel-box { background: var(--panel-bg); border: 1px solid var(--border-color); border-radius: 6px; padding: 20px; margin-bottom: 24px; }
  .panel-title { font-size: 0.95rem; font-weight: 700; letter-spacing: 1px; color: var(--accent-cyan); border-bottom: 1px solid var(--border-color); padding-bottom: 10px; margin-bottom: 16px; display: flex; justify-content: space-between; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-bottom: 12px; }
  th { text-align: left; padding: 10px; border-bottom: 1px solid var(--border-color); color: var(--text-dim); text-transform: uppercase; font-size: 0.75rem; }
  td { padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); }
  tr:hover td { background: rgba(0,240,255,0.04); }

  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700; }
  .badge-crit { background: rgba(255,51,68,0.2); color: var(--accent-red); border: 1px solid var(--accent-red); }
  .badge-warn { background: rgba(255,190,59,0.2); color: var(--accent-gold); border: 1px solid var(--accent-gold); }
  .badge-ok { background: rgba(0,255,136,0.15); color: var(--accent-green); border: 1px solid var(--accent-green); }

  #viewport { width: 100%; height: 100%; position: relative; background: radial-gradient(circle at center, #091322 0%, #05080e 100%); cursor: crosshair; }
  canvas { display: block; width: 100%; height: 100%; }
  .hud-float { position: absolute; background: var(--panel-bg); backdrop-filter: blur(10px); border: 1px solid var(--border-color); border-radius: 6px; padding: 14px; z-index: 10; }
  #radar-controls { top: 20px; left: 20px; width: 280px; display: flex; flex-direction: column; gap: 10px; }
  #radar-inspector { top: 20px; right: 20px; width: 330px; display: none; }
  #radar-tools { bottom: 20px; left: 20px; display: flex; gap: 10px; }
  select, input { width: 100%; background: #09111c; border: 1px solid var(--border-color); color: #fff; padding: 8px; border-radius: 4px; font-size: 0.85rem; }
  .filter-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 6px; }
  .f-btn { background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); color: var(--text-dim); padding: 5px; border-radius: 4px; cursor: pointer; font-size: 0.75rem; text-align: center; }
  .f-btn.active { border-color: var(--accent-cyan); color: #fff; background: rgba(0,240,255,0.1); }
</style>
</head>
<body>

<header>
  <div class="logo">
    <span>X4 SUPREME TERMINAL</span>
    <span class="logo-tag">V1.7.6 ENTERPRISE</span>
  </div>
  <nav>
    <button class="nav-btn active" onclick="switchTab('radar', event)">🛰️ Tactical Radar</button>
    <button class="nav-btn" onclick="switchTab('war', event)">⚔️ War Room (30s Window)</button>
    <button class="nav-btn" onclick="switchTab('builds', event)">🏗️ Construction & Slipways</button>
    <button class="nav-btn" onclick="switchTab('trades', event)">💰 Trade Analyzer (Mod 1801)</button>
    <button class="nav-btn" onclick="switchTab('eco', event)">🏭 Economy & Industry</button>
    <button class="nav-btn" onclick="switchTab('fleet', event)">🚢 Fleet & Hierarchy</button>
    <button class="nav-btn" onclick="switchTab('recon', event)">🔍 Derelicts & Vaults</button>
  </nav>
</header>

<div class="content-area">
  <div class="tab-pane active" id="tab-radar">
    <div id="viewport">
      <canvas id="radarCanvas"></canvas>
      <div class="hud-float" id="radar-controls">
        <span style="font-size:0.75rem; color:var(--accent-cyan); font-weight:700;">SECTOR SELECTION</span>
        <select id="sectorSelect"><option value="ALL">All Sectors (Galaxy View)</option></select>
        <span style="font-size:0.75rem; color:var(--accent-cyan); font-weight:700; margin-top:4px;">RADAR FILTERS</span>
        <div class="filter-grid">
          <div class="f-btn active" data-type="station">Stations</div>
          <div class="f-btn active" data-type="military">Warships</div>
          <div class="f-btn active" data-type="civilian">Civilian</div>
          <div class="f-btn active" data-type="hostile">Hostiles</div>
          <div class="f-btn active" data-type="derelict">Derelicts</div>
          <div class="f-btn active" data-type="gate">Gates</div>
        </div>
      </div>
      <div class="hud-float" id="radar-tools">
        <button class="nav-btn" id="btnZoomIn">Zoom +</button>
        <button class="nav-btn" id="btnZoomOut">Zoom -</button>
        <button class="nav-btn" id="btnRecenter">Center</button>
      </div>
      <div class="hud-float" id="radar-inspector">
        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border-color); padding-bottom:8px; margin-bottom:10px;">
          <strong id="inspName" style="color:var(--accent-cyan)">Target Details</strong>
          <span style="cursor:pointer; color:var(--text-dim);" onclick="document.getElementById('radar-inspector').style.display='none'">&times;</span>
        </div>
        <div id="inspBody" style="font-size:0.8rem; line-height:1.6;"></div>
      </div>
    </div>
  </div>

  <div class="tab-pane" id="tab-war">
    <div class="grid-cards">
      <div class="metric-card">
        <div class="metric-title">Active Combat Engagements</div>
        <div class="metric-val" style="color:var(--accent-red)">__COMBAT_COUNT__</div>
        <div class="metric-sub">Live 30-Second Window</div>
      </div>
      <div class="metric-card">
        <div class="metric-title">Galactic Incursions</div>
        <div class="metric-val" style="color:var(--accent-gold)">__ACTIVE_INC__</div>
        <div class="metric-sub">Hostile Capitals Detected</div>
      </div>
      <div class="metric-card">
        <div class="metric-title">Empire Boarding Power</div>
        <div class="metric-val" style="color:var(--accent-cyan)">__BOARDING_POWER__</div>
        <div class="metric-sub">__ELITE_MARINES__ Elite Shock Troops</div>
      </div>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>ACTIVE COMBAT TRIAGE (LIVE 30-SECOND WINDOW)</span></div>
      <table>
        <thead><tr><th>Vessel</th><th>Code</th><th>Sector</th><th>Hull</th><th>Shield</th><th>Status</th><th>Order</th><th>Engagement Vector</th></tr></thead>
        <tbody id="combatTableBody"></tbody>
      </table>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>GALACTIC THREAT MATRIX & GATE HOP PROXIMITY</span></div>
      <table>
        <thead><tr><th>Sector</th><th>Front Distance</th><th>Threat Level</th><th>Detected Hostiles</th><th>Defense Fleet</th></tr></thead>
        <tbody id="threatTableBody"></tbody>
      </table>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>COMBAT LOGBOOK INCIDENTS</span></div>
      <table>
        <thead><tr><th>Time</th><th>Incident</th><th>Log Details</th></tr></thead>
        <tbody id="lossTableBody"></tbody>
      </table>
    </div>
  </div>

  <div class="tab-pane" id="tab-builds">
    <div class="panel-box">
      <div class="panel-title"><span>STATION EXPANSION QUEUES & BUILD STORAGE BOTTLENECKS</span></div>
      <table>
        <thead><tr><th>Station Complex</th><th>Sector</th><th>Assigned Builder</th><th>Active Construction</th><th>Queue Size</th><th>Material Shortages</th></tr></thead>
        <tbody id="buildTableBody"></tbody>
      </table>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>SHIPYARD & WHARF ASSEMBLY SLIPWAYS</span></div>
      <table>
        <thead><tr><th>Shipyard Facility</th><th>Sector</th><th>Fabrication Bays</th><th>Hull / State</th><th>Client Faction</th><th>Progress</th><th>Time Remaining</th></tr></thead>
        <tbody id="shipyardTableBody"></tbody>
      </table>
    </div>
  </div>

  <div class="tab-pane" id="tab-trades">
    <div class="grid-cards">
      <div class="metric-card">
        <div class="metric-title">Total Trade Profit</div>
        <div class="metric-val" style="color:var(--accent-green)">__TRADE_PROFIT__ Cr</div>
        <div class="metric-sub">__TRADE_DATA_COVERAGE__</div>
      </div>
      <div class="metric-card">
        <div class="metric-title">Commercial Trade Fleet</div>
        <div class="metric-val" style="color:var(--accent-cyan)">__ACTIVE_TRADERS__ Hulls</div>
        <div class="metric-sub">Dedicated Freighters & Miners</div>
      </div>
      <div class="metric-card">
        <div class="metric-title">Fleet Hold Utilization</div>
        <div class="metric-val" style="color:var(--accent-gold)">__AVG_UTIL__%</div>
        <div class="metric-sub">Average Freight Capacity Used</div>
      </div>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>TOP EARNING TRADE & MINING SHIPS (NET PROFIT LEADERBOARD)</span></div>
      <table>
        <thead><tr><th>Vessel</th><th>Total Net Profit</th><th>External NPC Margin</th><th>Trades Run</th><th>Avg Hold Fill %</th></tr></thead>
        <tbody id="tradeShipsBody"></tbody>
      </table>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>COMMODITY PROFIT BREAKDOWN (EMPIRE CASH COWS)</span></div>
      <table>
        <thead><tr><th>Commodity</th><th>Gross Revenue</th><th>Realized Net Profit</th><th>Volume Traded</th></tr></thead>
        <tbody id="tradeWaresBody"></tbody>
      </table>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>COMPLETED TRADE CYCLES & TRANSACTION LEDGER</span></div>
      <table>
        <thead><tr><th>Vessel</th><th>Ware</th><th>Amount</th><th>Net Profit</th><th>Margin %</th><th>Buy Sector</th><th>Sell Sector</th><th>Hold %</th></tr></thead>
        <tbody id="tradeLedgerBody"></tbody>
      </table>
    </div>
  </div>

  <div class="tab-pane" id="tab-eco">
    <div class="grid-cards">
      <div class="metric-card">
        <div class="metric-title">Total Empire Net Worth</div>
        <div class="metric-val">__NET_WORTH__ Cr</div>
        <div class="metric-sub">Grand Total Balance Sheet</div>
      </div>
      <div class="metric-card">
        <div class="metric-title">Treasury Liquidity</div>
        <div class="metric-val">__LIQUID_CASH__ Cr</div>
        <div class="metric-sub">Safe to Skim: __SKIM_CASH__ Cr</div>
      </div>
      <div class="metric-card">
        <div class="metric-title">Industrial Real Estate</div>
        <div class="metric-val">__STATION_VAL__ Cr</div>
        <div class="metric-sub">Modules, Factories & Docks</div>
      </div>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>CORPORATE TREASURY SKIMMING MANIFEST</span></div>
      <table>
        <thead><tr><th>Station Complex</th><th>Sector</th><th>Account Balance</th><th>Required Reserve</th><th>Safe Surplus to Skim</th></tr></thead>
        <tbody id="skimTableBody"></tbody>
      </table>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>PRODUCTION STARVATION & BOTTLENECK AUDIT</span></div>
      <table>
        <thead><tr><th>Installation</th><th>Sector</th><th>Operational Health</th><th>Diagnostic Bottleneck</th></tr></thead>
        <tbody id="prodTableBody"></tbody>
      </table>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>STORAGE CHOKE & SATURATION DIAGNOSTICS</span></div>
      <table>
        <thead><tr><th>Station Complex</th><th>Sector</th><th>Container</th><th>Solid</th><th>Liquid</th></tr></thead>
        <tbody id="storageTableBody"></tbody>
      </table>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>LOGICAL OVERVIEW SLIDERS & TRADE CONFIGURATIONS</span></div>
      <table>
        <thead><tr><th>Station</th><th>Sector</th><th>Ware</th><th>Stock</th><th>Capacity</th><th>Sell All But</th><th>Buy Up To</th><th>Price</th><th>Trade Rule</th></tr></thead>
        <tbody id="tradeTableBody"></tbody>
      </table>
    </div>
  </div>

  <div class="tab-pane" id="tab-fleet">
    <div class="panel-box">
      <div class="panel-title"><span>STATION & FLEET HIERARCHY TREE</span></div>
      <div id="stationHierarchyList"></div>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>WARSHIP LOADOUT & GEAR AUDIT</span></div>
      <table>
        <thead><tr><th>Warship</th><th>Code</th><th>Size</th><th>Role</th><th>Shields</th><th>Engines</th><th>Weapons</th><th>Turrets</th></tr></thead>
        <tbody id="loadoutTableBody"></tbody>
      </table>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>PERSONNEL EXCELLENCE: TOP PILOT ACES</span></div>
      <table>
        <thead><tr><th>Pilot Name</th><th>Piloting</th><th>Morale</th><th>Assigned Vessel</th><th>Current Sector</th></tr></thead>
        <tbody id="acesTableBody"></tbody>
      </table>
    </div>
  </div>

  <div class="tab-pane" id="tab-recon">
    <div class="panel-box">
      <div class="panel-title"><span>ABANDONED DERELICTS & ERLKING DATA VAULTS</span></div>
      <table>
        <thead><tr><th>Target Name</th><th>Classification</th><th>Sector</th><th>Coordinates</th><th>Payload / Intel</th><th>Action</th></tr></thead>
        <tbody id="reconTableBody"></tbody>
      </table>
    </div>
  </div>
</div>

<script>
  const ENTITIES = /*__ENTITIES_JSON__*/;
  const SECTORS = /*__SECTORS_JSON__*/;
  const COMBAT_DATA = /*__COMBAT_JSON__*/;
  const THREAT_DATA = /*__THREAT_JSON__*/;
  const LOSS_DATA = /*__LOSS_JSON__*/;
  const BUILD_DATA = /*__BUILD_JSON__*/;
  const SHIPYARD_DATA = /*__SHIPYARD_JSON__*/;
  const SKIM_DATA = /*__SKIM_JSON__*/;
  const PROD_DATA = /*__PROD_JSON__*/;
  const STORAGE_DATA = /*__STORAGE_JSON__*/;
  const TRADE_DATA = /*__TRADE_JSON__*/;
  const TRADE_ANALYTICS = /*__TRADE_ANALYTICS_JSON__*/;
  const LOADOUT_DATA = /*__LOADOUT_JSON__*/;
  const HIERARCHY_DATA = /*__HIERARCHY_JSON__*/;
  const ACES_DATA = /*__ACES_JSON__*/;

  function switchTab(tabId, ev) {
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-' + tabId).classList.add('active');
    if (ev && ev.target) ev.target.classList.add('active');
    if (tabId === 'radar') draw();
  }

  const cBody = document.getElementById("combatTableBody");
  COMBAT_DATA.forEach(d => {
    cBody.innerHTML += `<tr><td><strong>${d.name}</strong></td><td>${d.code}</td><td>${d.sector}</td><td style="color:var(--accent-gold)">${d.hull}%</td><td>${d.shield}%</td><td><span class="badge ${d.combat?'badge-crit':'badge-warn'}">${d.combat?'UNDER FIRE':'DAMAGED'}</span></td><td>${d.order}</td><td style="color:var(--accent-red); font-weight:600;">${d.vector}</td></tr>`;
  });

  const tBody = document.getElementById("threatTableBody");
  THREAT_DATA.forEach(t => {
    let bClass = t.threat === 'CRITICAL' ? 'badge-crit' : (t.threat === 'HIGH RISK' ? 'badge-warn' : 'badge-ok');
    tBody.innerHTML += `<tr><td><strong>${t.sector}</strong></td><td>${t.hops}</td><td><span class="badge ${bClass}">${t.threat}</span></td><td>${t.hostiles}</td><td>${t.forces}</td></tr>`;
  });

  const lBody = document.getElementById("lossTableBody");
  LOSS_DATA.forEach(l => {
    lBody.innerHTML += `<tr><td>${l.time}</td><td style="color:var(--accent-red)">${l.title}</td><td>${l.text}</td></tr>`;
  });

  const bBody = document.getElementById("buildTableBody");
  BUILD_DATA.forEach(b => {
    bBody.innerHTML += `<tr><td><strong>${b.station}</strong></td><td>${b.sector}</td><td>${b.builder}</td><td style="color:var(--accent-cyan)">${b.building}</td><td>${b.queue}</td><td style="color:var(--accent-gold)">${b.shortages}</td></tr>`;
  });

  const syBody = document.getElementById("shipyardTableBody");
  SHIPYARD_DATA.forEach(s => {
    syBody.innerHTML += `<tr><td><strong>${s.station}</strong></td><td>${s.sector}</td><td>${s.bays || 'Standard'}</td><td><strong>${s.hull}</strong></td><td>${s.client}</td><td>${s.progress}%</td><td>${s.time}s</td></tr>`;
  });

  const tsBody = document.getElementById("tradeShipsBody");
  if (TRADE_ANALYTICS.top_ships && TRADE_ANALYTICS.top_ships.length > 0) {
    TRADE_ANALYTICS.top_ships.forEach(s => {
      tsBody.innerHTML += `<tr><td><strong>${s.name}</strong></td><td style="color:var(--accent-green)">+${Math.round(s.profit).toLocaleString()} Cr</td><td>${Math.round(s.ext_profit).toLocaleString()} Cr</td><td>${s.trades}</td><td>${s.avg_util}%</td></tr>`;
    });
  } else {
    tsBody.innerHTML = `<tr><td colspan="5" style="color:var(--text-dim); text-align:center;">No trade transactions logged yet in save history.</td></tr>`;
  }

  const twBody = document.getElementById("tradeWaresBody");
  if (TRADE_ANALYTICS.top_wares && TRADE_ANALYTICS.top_wares.length > 0) {
    TRADE_ANALYTICS.top_wares.forEach(w => {
      twBody.innerHTML += `<tr><td><strong>${w.ware}</strong></td><td>${Math.round(w.revenue).toLocaleString()} Cr</td><td style="color:var(--accent-green)">+${Math.round(w.profit).toLocaleString()} Cr</td><td>${Math.round(w.volume).toLocaleString()}</td></tr>`;
    });
  } else {
    twBody.innerHTML = `<tr><td colspan="4" style="color:var(--text-dim); text-align:center;">No commercial commodity profits logged yet.</td></tr>`;
  }

  const tlBody = document.getElementById("tradeLedgerBody");
  if (TRADE_ANALYTICS.trades && TRADE_ANALYTICS.trades.length > 0) {
    TRADE_ANALYTICS.trades.forEach(t => {
      tlBody.innerHTML += `<tr><td><strong>${t.ship}</strong></td><td>${t.ware}</td><td>${Math.round(t.amount).toLocaleString()}</td><td style="color:var(--accent-green)">+${Math.round(t.profit).toLocaleString()} Cr</td><td>${t.margin}%</td><td>${t.buy_sec || 'Trade Hub'}</td><td>${t.sell_sec || 'Client'}</td><td>${t.util}%</td></tr>`;
    });
  } else {
    tlBody.innerHTML = `<tr><td colspan="8" style="color:var(--text-dim); text-align:center;">No individual trade cycles recorded.</td></tr>`;
  }

  const skimBody = document.getElementById("skimTableBody");
  SKIM_DATA.forEach(s => {
    skimBody.innerHTML += `<tr><td><strong>${s.station}</strong></td><td>${s.sector}</td><td>${s.balance} Cr</td><td>${s.reserve} Cr</td><td style="color:var(--accent-green); font-weight:700;">+${s.surplus} Cr</td></tr>`;
  });

  const prodBody = document.getElementById("prodTableBody");
  PROD_DATA.forEach(p => {
    let bClass = p.status === 'HALTED' ? 'badge-crit' : (p.status === 'AT RISK' ? 'badge-warn' : 'badge-ok');
    prodBody.innerHTML += `<tr><td><strong>${p.station}</strong></td><td>${p.sector}</td><td><span class="badge ${bClass}">${p.status}</span></td><td>${p.bottleneck}</td></tr>`;
  });

  const storageBody = document.getElementById("storageTableBody");
  STORAGE_DATA.forEach(s => {
    storageBody.innerHTML += `<tr><td><strong>${s.station}</strong></td><td>${s.sector}</td><td>${s.cPct}%</td><td>${s.sPct}%</td><td>${s.lPct}%</td></tr>`;
  });

  const tradeBody = document.getElementById("tradeTableBody");
  TRADE_DATA.forEach(t => {
    tradeBody.innerHTML += `<tr><td><strong>${t.station}</strong></td><td>${t.sector}</td><td>${t.ware}</td><td>${t.stock}</td><td>${t.capacity}</td><td>${t.sell}</td><td>${t.buy}</td><td>${t.price}</td><td>${t.rule}</td></tr>`;
  });

  const hierList = document.getElementById("stationHierarchyList");
  HIERARCHY_DATA.forEach(st => {
    let subHtml = "";
    if (st.wings && st.wings.length > 0) {
      st.wings.forEach(w => {
        let shipsList = w.ships.map(s => `${s.count}x <strong>${s.name}</strong> (${s.role}, ${s.size})`).join(", ");
        subHtml += `<div style="margin-left:16px; margin-top:4px;"><span style="color:var(--accent-cyan); font-weight:600;">Wing: ${w.wing} (${w.total} craft):</span> ${shipsList}</div>`;
      });
    } else {
      subHtml = `<div style="margin-left:16px; color:var(--text-dim); margin-top:4px;">No subordinate vessels assigned.</div>`;
    }
    hierList.innerHTML += `
      <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:6px; padding:14px; margin-bottom:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="color:var(--accent-cyan); font-size:1rem;">${st.name} — [${st.sector}] (${st.role})</strong>
          <span class="badge ${st.hull > 90 ? 'badge-ok' : 'badge-warn'}">Hull: ${st.hull}%</span>
        </div>
        <div style="color:var(--text-dim); font-size:0.8rem; margin:6px 0;">
          Balance: <span style="color:#fff">${st.balance} Cr</span> | Director: <span style="color:#fff">${st.director}</span> | Fortifications: <span style="color:#fff">${st.fortifications}</span>
        </div>
        <div style="font-size:0.82rem; margin-top:8px;">
          <strong>Assigned Subordinates (${st.subCount} total):</strong>
          ${subHtml}
        </div>
      </div>
    `;
  });

  const loadoutBody = document.getElementById("loadoutTableBody");
  LOADOUT_DATA.forEach(l => {
    loadoutBody.innerHTML += `<tr><td><strong>${l.name}</strong></td><td>${l.code}</td><td>${l.size}</td><td>${l.role}</td><td>${l.shields} (${l.shieldPct}%)</td><td>${l.engines}</td><td>${l.weapons}</td><td>${l.turrets}</td></tr>`;
  });

  const acesBody = document.getElementById("acesTableBody");
  ACES_DATA.forEach(a => {
    acesBody.innerHTML += `<tr><td><strong>${a.name}</strong></td><td>${a.piloting}</td><td>${a.morale}</td><td>${a.ship}</td><td>${a.sector}</td></tr>`;
  });

  const reconBody = document.getElementById("reconTableBody");
  ENTITIES.filter(e => e.type === 'derelict' || e.type === 'vault').forEach(r => {
    reconBody.innerHTML += `<tr><td><strong>${r.name}</strong></td><td>${r.role}</td><td>${r.sector}</td><td>${r.x}km, ${r.z}km</td><td>${r.details}</td><td><button class="nav-btn" style="padding:4px 8px; font-size:0.75rem;" onclick="locateOnRadar('${r.sector}', ${r.x}, ${r.z}, '${r.id}')">Locate</button></td></tr>`;
  });

  function locateOnRadar(sec, x, z, id) {
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-radar').classList.add('active');
    document.querySelector("button[onclick*='radar']").classList.add('active');
    currentSector = sec;
    document.getElementById("sectorSelect").value = sec;
    panX = -x * zoom; panY = -z * zoom;
    selectedEntity = ENTITIES.find(e => e.id === id);
    if (selectedEntity) showInspector(selectedEntity);
    draw();
  }

  const canvas = document.getElementById("radarCanvas");
  const ctx = canvas.getContext("2d");
  let width = canvas.width = canvas.clientWidth;
  let height = canvas.height = canvas.clientHeight;
  let panX = 0, panY = 0, zoom = 1.6, isDragging = false, lastMouse = { x: 0, y: 0 };
  let selectedEntity = null, hoveredEntity = null, currentSector = "ALL";
  const filters = { station: true, military: true, civilian: true, hostile: true, derelict: true, gate: true };

  const sSelect = document.getElementById("sectorSelect");
  SECTORS.forEach(sec => {
    const opt = document.createElement("option"); opt.value = sec; opt.textContent = sec;
    sSelect.appendChild(opt);
  });
  sSelect.addEventListener("change", (e) => { currentSector = e.target.value; panX = 0; panY = 0; draw(); });

  document.querySelectorAll(".f-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      filters[btn.dataset.type] = !filters[btn.dataset.type];
      btn.classList.toggle("active", filters[btn.dataset.type]);
      draw();
    });
  });

  window.addEventListener('resize', () => { width = canvas.width = canvas.clientWidth; height = canvas.height = canvas.clientHeight; draw(); });
  canvas.addEventListener("mousedown", (e) => { isDragging = true; lastMouse = { x: e.clientX, y: e.clientY }; });
  window.addEventListener("mouseup", () => isDragging = false);
  canvas.addEventListener("mousemove", (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left; const my = e.clientY - rect.top;
    if (isDragging) {
      panX += (e.clientX - lastMouse.x); panY += (e.clientY - lastMouse.y);
      lastMouse = { x: e.clientX, y: e.clientY }; draw();
    } else {
      const cx = width / 2 + panX; const cy = height / 2 + panY;
      const visible = ENTITIES.filter(ent => currentSector === "ALL" || ent.sector === currentSector);
      hoveredEntity = null;
      for (let ent of visible) {
        const sx = cx + (ent.x * zoom); const sy = cy + (ent.z * zoom);
        if (Math.hypot(mx - sx, my - sy) <= 8) { hoveredEntity = ent; break; }
      }
      canvas.style.cursor = hoveredEntity ? 'pointer' : (isDragging ? 'grabbing' : 'crosshair');
    }
  });
  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    zoom = Math.min(Math.max(0.1, zoom * (e.deltaY < 0 ? 1.15 : 0.85)), 15.0);
    draw();
  });
  canvas.addEventListener("click", () => { if (hoveredEntity) { selectedEntity = hoveredEntity; showInspector(hoveredEntity); draw(); } });
  document.getElementById("btnRecenter").addEventListener("click", () => { panX = 0; panY = 0; zoom = 1.6; draw(); });
  document.getElementById("btnZoomIn").addEventListener("click", () => { zoom *= 1.25; draw(); });
  document.getElementById("btnZoomOut").addEventListener("click", () => { zoom *= 0.8; draw(); });

  function showInspector(e) {
    const insp = document.getElementById("radar-inspector");
    insp.style.display = "block";
    document.getElementById("inspName").textContent = e.name;
    document.getElementById("inspBody").innerHTML = `
      <div><strong>Role:</strong> ${e.role || e.type}</div>
      <div><strong>Sector:</strong> ${e.sector}</div>
      <div><strong>Coordinates:</strong> ${e.x}km, ${e.z}km</div>
      ${e.hull !== undefined ? `<div><strong>Hull:</strong> ${e.hull}% | <strong>Shield:</strong> ${e.shield}%</div>` : ''}
      ${e.order ? `<div><strong>Current Order:</strong> ${e.order}</div>` : ''}
      <div><strong>Details:</strong> ${e.details}</div>
    `;
  }

  function draw() {
    ctx.clearRect(0, 0, width, height);
    const cx = width / 2 + panX; const cy = height / 2 + panY;

    ctx.strokeStyle = "rgba(26, 47, 71, 0.5)"; ctx.lineWidth = 1;
    [25, 50, 100, 200, 300].forEach(r => {
      ctx.beginPath(); ctx.arc(cx, cy, r * zoom, 0, Math.PI * 2); ctx.stroke();
    });

    const visible = ENTITIES.filter(e => currentSector === "ALL" || e.sector === currentSector);
    visible.forEach(ent => {
      if (ent.type === "station" && !filters.station) return;
      if (ent.type === "player_ship" && ent.category === "Military" && !filters.military) return;
      if (ent.type === "player_ship" && ent.category !== "Military" && !filters.civilian) return;
      if (ent.type === "hostile" && !filters.hostile) return;
      if (ent.type === "derelict" && !filters.derelict) return;
      if (ent.type === "gate" && !filters.gate) return;

      const sx = cx + (ent.x * zoom); const sy = cy + (ent.z * zoom);
      if (sx < 0 || sx > width || sy < 0 || sy > height) return;

      if (ent.type === "station") { ctx.fillStyle = "#00f0ff"; ctx.fillRect(sx - 5, sy - 5, 10, 10); }
      else if (ent.type === "hostile") { ctx.fillStyle = "#ff3344"; ctx.beginPath(); ctx.arc(sx, sy, 5, 0, Math.PI * 2); ctx.fill(); }
      else if (ent.type === "derelict") { ctx.fillStyle = "#ffbe3b"; ctx.fillRect(sx - 3, sy - 3, 6, 6); }
      else if (ent.type === "gate") { ctx.strokeStyle = "#00ff88"; ctx.beginPath(); ctx.arc(sx, sy, 8, 0, Math.PI * 2); ctx.stroke(); }
      else { ctx.fillStyle = ent.category === "Military" ? "#0088ff" : "#00ff88"; ctx.beginPath(); ctx.arc(sx, sy, 4, 0, Math.PI * 2); ctx.fill(); }

      if (ent.under_fire) {
        ctx.strokeStyle = "#ff3344"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(sx, sy, 12, 0, Math.PI * 2); ctx.stroke();
      }
      if (zoom >= 0.8) {
        ctx.fillStyle = "#a8c7e2"; ctx.font = "10px monospace"; ctx.fillText(ent.name, sx + 8, sy + 3);
      }
    });
  }

  draw();
</script>
</body>
</html>"""

    terminal_html = terminal_template.replace("/*__ENTITIES_JSON__*/", json.dumps(entities))\
                                     .replace("/*__SECTORS_JSON__*/", json.dumps(sectors_list))\
                                     .replace("/*__COMBAT_JSON__*/", json.dumps(combat_triage))\
                                     .replace("/*__THREAT_JSON__*/", json.dumps(threat_rows))\
                                     .replace("/*__LOSS_JSON__*/", json.dumps(losses))\
                                     .replace("/*__BUILD_JSON__*/", json.dumps(construction_diag))\
                                     .replace("/*__SHIPYARD_JSON__*/", json.dumps(shipyard_diag))\
                                     .replace("/*__SKIM_JSON__*/", json.dumps(skimming_diag))\
                                     .replace("/*__PROD_JSON__*/", json.dumps(prod_diag))\
                                     .replace("/*__STORAGE_JSON__*/", json.dumps(storage_diag))\
                                     .replace("/*__TRADE_JSON__*/", json.dumps(trade_diag))\
                                     .replace("/*__TRADE_ANALYTICS_JSON__*/", json.dumps(trade_analytics_payload))\
                                     .replace("/*__LOADOUT_JSON__*/", json.dumps(loadout_diag))\
                                     .replace("/*__HIERARCHY_JSON__*/", json.dumps(hierarchy_diag))\
                                     .replace("/*__ACES_JSON__*/", json.dumps(aces_diag))\
                                     .replace("__COMBAT_COUNT__", str(len(combat_triage)))\
                                     .replace("__ACTIVE_INC__", str(sum(1 for e in entities if e["type"]=="hostile" and e.get("size") in ("XL", "L"))))\
                                     .replace("__BOARDING_POWER__", num(sum(s.boarding_strength for s in P.ships.values())))\
                                     .replace("__ELITE_MARINES__", num(sum(s.elite_marines for s in P.ships.values())))\
                                     .replace("__TRADE_PROFIT__", num(sum(t.net_profit for t in completed_trades)))\
                                     .replace("__TRADE_DATA_COVERAGE__", f"{num(P.trade_state_log_count)} unpriced stock-state events; excluded from profit")\
                                     .replace("__ACTIVE_TRADERS__", str(sum(1 for s in P.ships.values() if s.category in ("Trader", "Miner"))))\
                                     .replace("__AVG_UTIL__", f"{(sum(t.util_pct for t in completed_trades)/max(1, len(completed_trades))):.1f}")\
                                     .replace("__NET_WORTH__", num(net_worth))\
                                     .replace("__LIQUID_CASH__", num(liquid))\
                                     .replace("__SKIM_CASH__", num(total_skimmable))\
                                     .replace("__FLEET_VAL__", num(fleet_val))\
                                     .replace("__STATION_VAL__", num(st_val))

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(terminal_html)
    print(f"[+] Complete Supreme Command Terminal HTML generated -> {output_html}")

# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================
def find_game_dir(user_arg):
    candidates = [
        user_arg, DEFAULT_GAME_DIR, os.environ.get("X4_GAME_DIR"),
        r"C:\Program Files (x86)\Steam\steamapps\common\X4 Foundations",
        r"D:\SteamLibrary\steamapps\common\X4 Foundations",
        r"F:\genisis\X4.Foundations-SteamRIP.com\X4 Foundations Envoy Pack"
    ]
    for c in candidates:
        if c and os.path.isdir(c): return c
    return None

def find_default_save():
    for f in sorted(os.listdir("."), reverse=True):
        if (f.endswith(".xml.gz") or f.endswith(".xml")) and not f.startswith("x4_"):
            return f
    docs = os.path.expanduser(r"~\Documents\Egosoft\X4")
    if os.path.isdir(docs):
        saves = glob.glob(os.path.join(docs, "*", "save", "*.xml.gz"))
        if saves:
            return max(saves, key=os.path.getmtime)
    return None

def main():
    parser = argparse.ArgumentParser(description="X4: Foundations Supreme Command & Empire Intelligence Terminal (V1.7.6 Enterprise)")
    parser.add_argument("save", nargs="?", help="Path to save file (.xml or .xml.gz)")
    parser.add_argument("--game-dir", default=DEFAULT_GAME_DIR, help="Path to unpacked X4 game data directory")
    parser.add_argument("--out", default="x4_master_empire_dossier.md", help="Output Markdown report path")
    parser.add_argument("--html", default="x4_command_terminal.html", help="Interactive tactical terminal HTML path")
    parser.add_argument("--names", default="x4_sector_names.json", help="Optional sector name override JSON")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch web browser terminal")
    args = parser.parse_args()

    save_path = args.save or find_default_save()
    if not save_path or not os.path.isfile(save_path):
        sys.exit("[-] Error: No valid savegame found. Provide a .xml or .xml.gz save file.")

    gdir = find_game_dir(args.game_dir)
    print(f"[*] Initializing Game Data Engine from: {gdir}")
    gd = GameData(gdir) if gdir else None

    overrides = {}
    if os.path.isfile(args.names):
        try:
            with open(args.names, encoding="utf-8") as fh:
                overrides = {k.lower(): v for k, v in json.load(fh).items() if not k.startswith("_")}
        except Exception as e: print(f"[-] Warning reading {args.names}: {e}")

    namer = Namer(gd if (gd and gd.ok) else None, overrides)

    print(f"[*] Parsing savegame: {save_path}")
    P = SaveParser()
    P.parse(save_path)
    if P.truncated:
        sys.exit(f"[-] Error: Savegame XML is malformed or truncated ({P.truncated}). No reports generated.")
    P.finalize()

    report, net_worth, liquid, fleet_val, st_val, stock_val = build_dossier(P, namer, gdir, bool(gd and gd.ok))
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(report)
    print(f"[+] Markdown dossier compiled -> {args.out}")

    generate_command_terminal_html(P, namer, args.html, net_worth, liquid, fleet_val, st_val, stock_val)

    if not args.no_browser:
        full_html_path = os.path.abspath(args.html)
        print(f"[*] Launching Supreme Command Terminal -> {full_html_path}")
        webbrowser.open(f"file://{full_html_path}")

    print(f"[+] Terminal deployment complete. Empire Net Worth: {num(net_worth)} Credits.")

if __name__ == "__main__":
    main()