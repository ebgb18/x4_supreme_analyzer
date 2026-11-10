# ==============================================================================
# STREAMING SAVE PARSER
# ==============================================================================
import gzip
import os
import re
from collections import Counter, defaultdict, deque
from xml.parsers import expat

from .constants import (
    SIZE_BY_CLASS, DEPLOYABLE_REGEX, DEFAULT_FACTION_RELATIONS, HOSTILITY_RELATION_THRESHOLD,
    MODULE_CLASSES, GEAR_CLASSES, COMBAT_ENGAGEMENT_WINDOW, CODE_REGEX, HEX_ID_REGEX,
    ERLKING_VAULT_REGEX, VAULT_REGEX, BUILTIN_WARE_NAMES,
)
from .models import TradeTransaction, Ship, BuildStorage, Station
from .utils import prettify, gear_category, gear_parts

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
        self.market_offers = []

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

        # Real market offers: <trade id=... buyer|seller=... ware=... price=... amount=...>
        w_id = (a.get("ware") or "").lower()
        if not w_id:
            return
        try: price = float(a.get("price", 0.0) or 0.0)
        except ValueError: price = 0.0
        try: amt = int(float(a.get("amount", 0) or 0))
        except ValueError: amt = 0
        if price <= 0:
            return
        buyer = a.get("buyer")
        seller = a.get("seller")
        partner = a.get("partner")
        # Station production offers (no partner): the station itself is the counterparty
        if ofr and ofr.get("station") and not partner:
            st = ofr["station"]
            side = "buy" if buyer else ("sell" if seller else None)
            if side:
                st.offers.append({"ware": w_id, "side": side, "price": price, "amount": amt})
                self.market_offers.append({
                    "station_id": st.id, "sector": st.sector, "ware": w_id,
                    "side": side, "price": price, "amount": amt, "partner": None,
                })
            return
        # Active trade deals (with partner): record as market intelligence
        if partner:
            owner_id = buyer or seller
            self.market_offers.append({
                "station_id": None, "sector": ofr.get("sector") if ofr else None,
                "ware": w_id, "side": "buy" if buyer else "sell",
                "price": price, "amount": amt, "partner": partner, "owner": owner_id,
            })

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

        # 5. STATION REFERENCE PRICES (market price book, not trade config)
        if "reference" in self.tags[-3:] and "prices" in self.tags[-4:]:
            ofr = self.owner_frame()
            if ofr and ofr.get("station"):
                st = ofr["station"]
                try: buy_p = float(a.get("buy", 0.0) or 0.0)
                except ValueError: buy_p = 0.0
                try: sell_p = float(a.get("sell", 0.0) or 0.0)
                except ValueError: sell_p = 0.0
                st.reference_prices[w_id] = {"buy": buy_p, "sell": sell_p}
            return

        # 6. STATION LOGICAL OVERVIEW CONFIGURATIONS
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

