# ==============================================================================
# DATA MODELS
# ==============================================================================
from collections import Counter

from .constants import (
    DEFAULT_CARGO_VOLUMES, ESTIMATED_HULL_VALUES, HABITATION_CAPACITIES,
)
from .utils import classify_ship

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
        self.reference_prices = {}
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

