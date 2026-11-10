# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================
import html
import re

from .constants import (
    SIZE_BY_CLASS, BASE_COMBAT_WEIGHT, DEPLOYABLE_REGEX,
)

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

