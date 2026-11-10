# ==============================================================================
# X4: Foundations (v8.0+) - Supreme Command & Empire Intelligence Terminal
# Version: V1.7.7 Enterprise - Supreme Intelligence Edition
# Zero external dependencies: 100% standard Python 3.8+ (expat, json, gzip, webbrowser)
# ==============================================================================

import re

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

# Galactic average ware prices (Cr). Calibrated to X4 v8.0 save medians (save_003, build 590967).
AVERAGE_WARE_PRICES = {
    "energycells": 1594.0, "ore": 5070.0, "silicon": 12900.0, "ice": 2624.0,
    "hydrogen": 6164.0, "helium": 3936.0, "methane": 4244.0, "nividium": 51491.0,
    "refinedmetals": 15528.0, "siliconwafers": 29360.0, "graphene": 16877.0, "hullparts": 24386.0,
    "claytronics": 208022.0, "antimattercells": 13569.0, "antimatterconverters": 35335.0,
    "advancedcomposites": 52654.0, "advancedelectronics": 120196.0, "computronicsubstrate": 846272.0,
    "metallicmicrolattice": 4900.0, "siliconcarbide": 141400.0, "terranmre": 4379.0,
    "foodrations": 1815.0, "medicalsupplies": 5949.0, "proteinpaste": 9500.0, "water": 4913.0,
    "spices": 2203.0, "nostropoil": 3366.0, "sojabeans": 8397.0, "sojahusk": 3614.0,
    "sunriseflowers": 8867.0, "microchips": 95508.0, "smartchips": 6300.0, "quantumtubes": 30963.0,
    "plasmaconductors": 101340.0, "shieldcomponents": 19652.0, "turretcomponents": 30913.0,
    "weaponcomponents": 32405.0, "dronecomponents": 102800.0, "fieldcoils": 41200.0,
    "engineparts": 18200.0, "missilecomponents": 855.0, "scanningarrays": 105300.0,
    "rawscrap": 15791.0, "scrapmetal": 37757.0, "scruffinfruits": 2179.0, "cheltmeat": 7200.0,
    "bofu": 10029.0, "boggas": 7480.0, "plankton": 1922.0, "meat": 5371.0, "wheat": 3472.0,
    "condensate": 2570571.0, "majadust": 40732.0, "majasnails": 6516.0, "spacefuel": 26091.0,
    "spaceweed": 32432.0, "stimulants": 67388.0, "superfluidcoolant": 13619.0,
    "swampplant": 9426.0, "teladianium": 24006.0
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

