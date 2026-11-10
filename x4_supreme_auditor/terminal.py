# ==============================================================================
# UNIFIED ALL-IN-ONE WEB TERMINAL (HTML + RADAR + FULL DOSSIER TABS)
# ==============================================================================
import json
from collections import Counter, defaultdict, deque

from .constants import (
    REF_REGEX, SOLID_WARES, LIQUID_WARES, COMBAT_ENGAGEMENT_WINDOW,
)
from .utils import num, prettify, ammo_class
from .analytics import (
    process_trade_analytics, compute_trade_intelligence, compute_logistics_intelligence,
    compute_derelict_valuation, compute_empire_health, build_commander_briefing,
    compute_market_intelligence,
)

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
    trade_intel = compute_trade_intelligence(P, N, completed_trades, ship_profits, ware_profits)
    logistics_intel = compute_logistics_intelligence(P, N)
    derelict_val = compute_derelict_valuation(P, N)
    market_intel = compute_market_intelligence(P, N)
    empire_health = compute_empire_health(P, N, trade_intel, logistics_intel, threat_hops)
    briefing = build_commander_briefing(P, N, trade_intel, logistics_intel, threat_hops, derelict_val)

    intelligence_payload = {
        "health": empire_health,
        "briefing": briefing,
        "fleet_roi_pct": round(trade_intel["fleet_roi_pct"], 1),
        "fleet_profit_per_hour": round(trade_intel["fleet_profit_per_hour"], 0),
        "total_cost": round(trade_intel["total_cost"], 0),
        "ship_efficiency": [
            {
                "name": (ship_name(P.ships[e["ship_id"]]) if e["ship_id"] in P.ships else e["ship_id"]),
                "profit_per_hour": round(e["profit_per_hour"], 0),
                "recent_profit_24h": round(e["recent_profit_24h"], 0),
                "roi_pct": round(e["roi_pct"], 1),
                "avg_margin": round(e["avg_margin"], 1),
                "avg_util": round(e["avg_util"], 1),
                "trades": e["trades"],
            }
            for e in trade_intel["ship_efficiency"][:12]
        ],
        "route_matrix": [
            {
                "buy_sec": sname(r["buy_sector"]), "sell_sec": sname(r["sell_sector"]),
                "ware": N.ware(r["ware"]), "trades": r["trades"],
                "profit": round(r["profit"], 0), "profit_per_hour": round(r["profit_per_hour"], 0),
                "avg_margin": round(r["avg_margin"], 1), "roi_pct": round(r["roi_pct"], 1),
            }
            for r in trade_intel["route_matrix"][:15]
        ],
        "partner_intel": [
            {
                "name": p_["name"], "owner": p_["owner"], "trades": p_["trades"],
                "volume": p_["volume"], "value": round(p_["value"], 0),
                "top_ware": N.ware(p_["top_ware"]), "buys": p_["buys"], "sells": p_["sells"],
            }
            for p_ in trade_intel["partner_intel"][:12]
        ],
        "ware_velocity": [
            {
                "ware": N.ware(v["ware"]), "volume": v["volume"], "profit": round(v["profit"], 0),
                "profit_per_hour": round(v["profit_per_hour"], 0), "avg_price": round(v["avg_price"], 2),
                "trades": v["trades"],
            }
            for v in trade_intel["ware_velocity"][:10]
        ],
        "autonomy": [
            {
                "station": (station_name(P.stations[a_["station_id"]]) if a_["station_id"] in P.stations else a_["station"]),
                "sector": sname(a_["sector"]), "ware": N.ware(a_["ware"]),
                "stock": a_["stock"], "rate_hr": round(a_["rate_hr"], 1),
                "hours_to_empty": round(a_["hours_to_empty"], 1),
                "critical": a_["critical"], "warning": a_["warning"],
            }
            for a_ in logistics_intel["autonomy"] if a_["hours_to_empty"] <= 24.0
        ][:40],
        "storage_composition": [
            {
                "station": (station_name(P.stations[sc["station_id"]]) if sc["station_id"] in P.stations else sc["station"]),
                "sector": sname(sc["sector"]),
                "container_pct": round(sc["container_pct"], 1), "solid_pct": round(sc["solid_pct"], 1), "liquid_pct": round(sc["liquid_pct"], 1),
                "top_wares": [{"ware": N.ware(t["ware"]), "m3": round(t["m3"], 0)} for t in sc["top_wares"]],
            }
            for sc in logistics_intel["storage_composition"]
        ],
        "allocation_audit": [
            {
                "station": (station_name(P.stations[a_["station_id"]]) if a_["station_id"] in P.stations else a_["station"]),
                "sector": sname(a_["sector"]), "ware": N.ware(a_["ware"]),
                "allocated_m3": round(a_["allocated_m3"], 0), "used_m3": round(a_["used_m3"], 0),
                "efficiency_pct": round(a_["efficiency_pct"], 1),
                "over_allocated": a_["over_allocated"], "under_allocated": a_["under_allocated"],
            }
            for a_ in logistics_intel["allocation_audit"] if (a_["over_allocated"] or a_["under_allocated"])
        ][:30],
        "price_anomalies": [
            {
                "station": (station_name(P.stations[pa["station_id"]]) if pa["station_id"] in P.stations else pa["station"]),
                "sector": sname(pa["sector"]), "ware": N.ware(pa["ware"]), "side": pa["side"],
                "price": round(pa["price"], 2), "avg_price": round(pa["avg_price"], 2),
                "deviation_pct": round(pa["deviation_pct"], 1), "source": pa["source"],
            }
            for pa in logistics_intel["price_anomalies"][:30]
        ],
        "burn_costs": [
            {
                "station": (station_name(P.stations[b["station_id"]]) if b["station_id"] in P.stations else b["station"]),
                "sector": sname(b["sector"]), "modules": b["modules"],
                "input_cost_per_hour": round(b["input_cost_per_hour"], 0),
            }
            for b in logistics_intel["burn_costs"][:20]
        ],
        "derelict_valuation": derelict_val,
        "market": {
            "total_offers": market_intel["total_offers"],
            "station_offer_count": market_intel["station_offer_count"],
            "arbitrage": [
                {
                    "ware": N.ware(a_["ware"]),
                    "buy_station": (station_name(P.stations[a_["buy_station_id"]]) if a_["buy_station_id"] in P.stations else f"Station [{a_['buy_station_id']}]"),
                    "buy_sector": sname(a_["buy_sector"]), "buy_price": round(a_["buy_price"], 2),
                    "sell_station": (station_name(P.stations[a_["sell_station_id"]]) if a_["sell_station_id"] in P.stations else f"Station [{a_['sell_station_id']}]"),
                    "sell_sector": sname(a_["sell_sector"]), "sell_price": round(a_["sell_price"], 2),
                    "spread": round(a_["spread"], 2), "margin_pct": round(a_["margin_pct"], 1),
                }
                for a_ in market_intel["arbitrage"][:20]
            ],
            "station_price_index": [
                {
                    "station": (station_name(P.stations[p_["station_id"]]) if p_["station_id"] in P.stations else p_["station"]),
                    "sector": sname(p_["sector"]),
                    "avg_deviation_pct": round(p_["avg_deviation_pct"], 1),
                    "offer_count": p_["offer_count"],
                    "cheapest_count": p_["cheapest_count"],
                    "priciest_count": p_["priciest_count"],
                }
                for p_ in market_intel["station_price_index"]
            ],
        },
    }

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
        sh_str = ", ".join(f"{cnt}x {N.gear(m)}" for m, cnt in s.installed_shields.items()) if s.installed_shields else (f"{s.parts['shieldgenerator']}x Shields" if s.parts['shieldgenerator'] > 0 else "NO SHIELDS (0 Slots)")
        eng_str = ", ".join(f"{cnt}x {N.gear(m)}" for m, cnt in s.installed_engines.items()) if s.installed_engines else "Standard Engines"
        weap_list = [f"{cnt}x {N.gear(m)}" for m, cnt in s.installed_weapons.items()]
        turr_list = [f"{cnt}x {N.gear(m)}" for m, cnt in s.installed_turrets.items()]
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
<title>X4: FOUNDATIONS — SUPREME COMMAND TERMINAL V1.7.7 ENTERPRISE — SUPREME INTELLIGENCE EDITION</title>
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
    <span class="logo-tag">V1.7.7 ENTERPRISE</span>
  </div>
  <nav>
    <button class="nav-btn active" onclick="switchTab('intel', event)">🧠 Supreme Intelligence</button>
    <button class="nav-btn" onclick="switchTab('radar', event)">🛰️ Tactical Radar</button>
    <button class="nav-btn" onclick="switchTab('war', event)">⚔️ War Room (30s Window)</button>
    <button class="nav-btn" onclick="switchTab('builds', event)">🏗️ Construction & Slipways</button>
    <button class="nav-btn" onclick="switchTab('trades', event)">💰 Trade Analyzer (Mod 1801)</button>
    <button class="nav-btn" onclick="switchTab('eco', event)">🏭 Economy & Industry</button>
    <button class="nav-btn" onclick="switchTab('fleet', event)">🚢 Fleet & Hierarchy</button>
    <button class="nav-btn" onclick="switchTab('recon', event)">🔍 Derelicts & Vaults</button>
  </nav>
</header>

<div class="content-area">
  <div class="tab-pane active" id="tab-intel">
    <div class="grid-cards">
      <div class="metric-card">
        <div class="metric-title">Empire Health Score</div>
        <div class="metric-val" style="color:var(--accent-cyan)">__HEALTH_COMPOSITE__<span style="font-size:0.9rem; color:var(--text-dim)">/100</span></div>
        <div class="metric-sub">Grade __HEALTH_GRADE__ — Weighted Composite</div>
      </div>
      <div class="metric-card">
        <div class="metric-title">Fleet Profit Velocity</div>
        <div class="metric-val" style="color:var(--accent-green)">__FLEET_PPH__ Cr/h</div>
        <div class="metric-sub">Fleet ROI: __FLEET_ROI__% on deployed capital</div>
      </div>
      <div class="metric-card">
        <div class="metric-title">Derelict Recoverable Value</div>
        <div class="metric-val" style="color:var(--accent-gold)">__DERELICT_VALUE__ Cr</div>
        <div class="metric-sub">__DERELICT_COUNT__ hulls (__DERELICT_CLAIMABLE__ claimable)</div>
      </div>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>EMPIRE HEALTH BREAKDOWN</span></div>
      <table>
        <thead><tr><th>Dimension</th><th>Score /100</th><th>Weight</th></tr></thead>
        <tbody id="healthTableBody"></tbody>
      </table>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>COMMANDER BRIEFING — PRIORITY ACTION ITEMS</span></div>
      <div id="briefingList"></div>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>FLEET EFFICIENCY LEADERBOARD (PROFIT / HOUR)</span></div>
      <table>
        <thead><tr><th>Vessel</th><th>Profit / Hour</th><th>Last 24h</th><th>ROI %</th><th>Avg Margin</th><th>Hold Fill</th><th>Trades</th></tr></thead>
        <tbody id="effTableBody"></tbody>
      </table>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>ROUTE PROFITABILITY MATRIX (BUY → SELL)</span></div>
      <table>
        <thead><tr><th>Buy Sector</th><th>Sell Sector</th><th>Ware</th><th>Runs</th><th>Net Profit</th><th>Profit / Hour</th><th>Margin</th><th>ROI</th></tr></thead>
        <tbody id="routeTableBody"></tbody>
      </table>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>EXTERNAL PARTNER INTELLIGENCE (BY TRADE VALUE)</span></div>
      <table>
        <thead><tr><th>Partner</th><th>Faction</th><th>Trades</th><th>Units</th><th>Total Value</th><th>Top Ware</th><th>Buy/Sell</th></tr></thead>
        <tbody id="partnerTableBody"></tbody>
      </table>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>WARE VELOCITY — PROFIT PER HOUR BY COMMODITY</span></div>
      <table>
        <thead><tr><th>Commodity</th><th>Units Traded</th><th>Net Profit</th><th>Profit / Hour</th><th>Avg Price</th><th>Transactions</th></tr></thead>
        <tbody id="velocityTableBody"></tbody>
      </table>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>LOGISTICS AUTONOMY — TIME TO EMPTY (&lt;24h)</span></div>
      <table>
        <thead><tr><th>Station</th><th>Sector</th><th>Input Ware</th><th>Stock</th><th>Burn /h</th><th>Time to Empty</th><th>Status</th></tr></thead>
        <tbody id="autonomyTableBody"></tbody>
      </table>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>STORAGE COMPOSITION & TOP STORED WARES</span></div>
      <table>
        <thead><tr><th>Station</th><th>Sector</th><th>Container</th><th>Solid</th><th>Liquid</th><th>Top Stored (m³)</th></tr></thead>
        <tbody id="compositionTableBody"></tbody>
      </table>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>ALLOCATION EFFICIENCY FLAGS (&lt;20% / &gt;95% UTILIZED)</span></div>
      <table>
        <thead><tr><th>Station</th><th>Sector</th><th>Ware</th><th>Allocated</th><th>Used</th><th>Efficiency</th><th>Flag</th></tr></thead>
        <tbody id="allocationTableBody"></tbody>
      </table>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>PRICE ANOMALY AUDIT (&gt;25% VS GALACTIC AVERAGE)</span></div>
      <table>
        <thead><tr><th>Station</th><th>Sector</th><th>Ware</th><th>Side</th><th>Price</th><th>Galactic Avg</th><th>Deviation</th><th>Source</th></tr></thead>
        <tbody id="anomalyTableBody"></tbody>
      </table>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>PRODUCTION BURN COST — HOURLY INPUT SPEND</span></div>
      <table>
        <thead><tr><th>Station</th><th>Sector</th><th>Modules</th><th>Input Cost / Hour</th></tr></thead>
        <tbody id="burnTableBody"></tbody>
      </table>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>CROSS-STATION ARBITRAGE (BUY LOW → SELL HIGH)</span></div>
      <table>
        <thead><tr><th>Ware</th><th>Buy At</th><th>Buy Sector</th><th>Buy Price</th><th>Sell At</th><th>Sell Sector</th><th>Sell Price</th><th>Spread</th><th>Margin</th></tr></thead>
        <tbody id="arbitrageTableBody"></tbody>
      </table>
    </div>

    <div class="panel-box">
      <div class="panel-title"><span>STATION PRICE COMPETITIVENESS INDEX (VS GALACTIC AVERAGE)</span></div>
      <table>
        <thead><tr><th>Station</th><th>Sector</th><th>Avg Deviation</th><th>Offers</th><th>Cheapest Wares</th><th>Priciest Wares</th></tr></thead>
        <tbody id="priceIndexTableBody"></tbody>
      </table>
    </div>
  </div>

  <div class="tab-pane" id="tab-radar">
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
  const INTEL = /*__INTEL_JSON__*/;

  function switchTab(tabId, ev) {
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-' + tabId).classList.add('active');
    if (ev && ev.target) ev.target.classList.add('active');
    if (tabId === 'radar') {
      const c = document.getElementById("radarCanvas");
      if (c && c.clientWidth > 0) { c.width = c.clientWidth; c.height = c.clientHeight; }
      draw();
    }
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

  // ---- SUPREME INTELLIGENCE TAB ----
  const healthBody = document.getElementById("healthTableBody");
  const healthDims = [
    ["Treasury Liquidity", INTEL.health.treasury, "15%"],
    ["Fleet Readiness", INTEL.health.fleet, "25%"],
    ["Industrial Health", INTEL.health.industry, "20%"],
    ["Logistics & Storage", INTEL.health.logistics, "15%"],
    ["Security Posture", INTEL.health.security, "15%"],
    ["Personnel Readiness", INTEL.health.personnel, "10%"]
  ];
  healthDims.forEach(([dim, score, weight]) => {
    let col = score >= 80 ? 'var(--accent-green)' : (score >= 55 ? 'var(--accent-gold)' : 'var(--accent-red)');
    healthBody.innerHTML += `<tr><td><strong>${dim}</strong></td><td style="color:${col}; font-weight:700;">${score.toFixed(1)}</td><td>${weight}</td></tr>`;
  });

  const briefingList = document.getElementById("briefingList");
  if (INTEL.briefing && INTEL.briefing.length > 0) {
    const levelColor = {CRITICAL: 'var(--accent-red)', WARNING: 'var(--accent-gold)', INFO: 'var(--accent-cyan)'};
    INTEL.briefing.forEach(a => {
      briefingList.innerHTML += `<div style="border-left:3px solid ${levelColor[a.level] || 'var(--text-dim)'}; padding:8px 12px; margin-bottom:8px; background:rgba(255,255,255,0.02); border-radius:4px;"><span class="badge ${a.level === 'CRITICAL' ? 'badge-crit' : (a.level === 'WARNING' ? 'badge-warn' : 'badge-ok')}">${a.level}</span> <strong style="color:var(--text-dim); font-size:0.75rem; text-transform:uppercase;">${a.category}</strong><div style="margin-top:4px; font-size:0.85rem;">${a.message}</div></div>`;
    });
  } else {
    briefingList.innerHTML = `<div style="color:var(--accent-green); padding:12px;">No critical action items. Empire operating within nominal parameters.</div>`;
  }

  const effBody = document.getElementById("effTableBody");
  if (INTEL.ship_efficiency && INTEL.ship_efficiency.length > 0) {
    INTEL.ship_efficiency.forEach(e => {
      effBody.innerHTML += `<tr><td><strong>${e.name}</strong></td><td style="color:var(--accent-green)">+${Math.round(e.profit_per_hour).toLocaleString()} Cr/h</td><td>${Math.round(e.recent_profit_24h).toLocaleString()} Cr</td><td>${e.roi_pct}%</td><td>${e.avg_margin}%</td><td>${e.avg_util}%</td><td>${e.trades}</td></tr>`;
    });
  } else {
    effBody.innerHTML = `<tr><td colspan="7" style="color:var(--text-dim); text-align:center;">No trade efficiency data logged yet.</td></tr>`;
  }

  const routeBody = document.getElementById("routeTableBody");
  if (INTEL.route_matrix && INTEL.route_matrix.length > 0) {
    INTEL.route_matrix.forEach(r => {
      routeBody.innerHTML += `<tr><td>${r.buy_sec}</td><td>${r.sell_sec}</td><td><strong>${r.ware}</strong></td><td>${r.trades}</td><td style="color:var(--accent-green)">+${Math.round(r.profit).toLocaleString()} Cr</td><td>${Math.round(r.profit_per_hour).toLocaleString()} Cr/h</td><td>${r.avg_margin}%</td><td>${r.roi_pct}%</td></tr>`;
    });
  } else {
    routeBody.innerHTML = `<tr><td colspan="8" style="color:var(--text-dim); text-align:center;">No completed route cycles recorded.</td></tr>`;
  }

  const partnerBody = document.getElementById("partnerTableBody");
  if (INTEL.partner_intel && INTEL.partner_intel.length > 0) {
    INTEL.partner_intel.forEach(p => {
      partnerBody.innerHTML += `<tr><td><strong>${p.name}</strong></td><td>${p.owner}</td><td>${p.trades}</td><td>${Math.round(p.volume).toLocaleString()}</td><td>${Math.round(p.value).toLocaleString()} Cr</td><td>${p.top_ware}</td><td>${p.buys}B / ${p.sells}S</td></tr>`;
    });
  } else {
    partnerBody.innerHTML = `<tr><td colspan="7" style="color:var(--text-dim); text-align:center;">No external partner transactions logged.</td></tr>`;
  }

  const velocityBody = document.getElementById("velocityTableBody");
  if (INTEL.ware_velocity && INTEL.ware_velocity.length > 0) {
    INTEL.ware_velocity.forEach(v => {
      velocityBody.innerHTML += `<tr><td><strong>${v.ware}</strong></td><td>${Math.round(v.volume).toLocaleString()}</td><td style="color:var(--accent-green)">+${Math.round(v.profit).toLocaleString()} Cr</td><td>${Math.round(v.profit_per_hour).toLocaleString()} Cr/h</td><td>${v.avg_price.toFixed(2)} Cr</td><td>${v.trades}</td></tr>`;
    });
  } else {
    velocityBody.innerHTML = `<tr><td colspan="6" style="color:var(--text-dim); text-align:center;">No ware velocity data available.</td></tr>`;
  }

  const autonomyBody = document.getElementById("autonomyTableBody");
  if (INTEL.autonomy && INTEL.autonomy.length > 0) {
    INTEL.autonomy.forEach(a => {
      let badge = a.critical ? '<span class="badge badge-crit">CRITICAL</span>' : (a.warning ? '<span class="badge badge-warn">WARNING</span>' : '<span class="badge badge-ok">OK</span>');
      autonomyBody.innerHTML += `<tr><td><strong>${a.station}</strong></td><td>${a.sector}</td><td>${a.ware}</td><td>${Math.round(a.stock).toLocaleString()}</td><td>${a.rate_hr}/h</td><td>${a.hours_to_empty}h</td><td>${badge}</td></tr>`;
    });
  } else {
    autonomyBody.innerHTML = `<tr><td colspan="7" style="color:var(--accent-green); text-align:center;">All production inputs have &gt;24h autonomy. Supply chain healthy.</td></tr>`;
  }

  const compositionBody = document.getElementById("compositionTableBody");
  if (INTEL.storage_composition && INTEL.storage_composition.length > 0) {
    INTEL.storage_composition.forEach(sc => {
      let top = (sc.top_wares || []).map(t => `${t.ware} (${Math.round(t.m3).toLocaleString()} m³)`).join(", ") || "Empty";
      compositionBody.innerHTML += `<tr><td><strong>${sc.station}</strong></td><td>${sc.sector}</td><td>${sc.container_pct}%</td><td>${sc.solid_pct}%</td><td>${sc.liquid_pct}%</td><td style="font-size:0.8rem;">${top}</td></tr>`;
    });
  } else {
    compositionBody.innerHTML = `<tr><td colspan="6" style="color:var(--text-dim); text-align:center;">No storage modules detected.</td></tr>`;
  }

  const allocationBody = document.getElementById("allocationTableBody");
  if (INTEL.allocation_audit && INTEL.allocation_audit.length > 0) {
    INTEL.allocation_audit.forEach(a => {
      let flag = a.over_allocated ? '<span class="badge badge-warn">OVER-ALLOCATED</span>' : '<span class="badge badge-crit">UNDER-ALLOCATED</span>';
      allocationBody.innerHTML += `<tr><td><strong>${a.station}</strong></td><td>${a.sector}</td><td>${a.ware}</td><td>${Math.round(a.allocated_m3).toLocaleString()} m³</td><td>${Math.round(a.used_m3).toLocaleString()} m³</td><td>${a.efficiency_pct}%</td><td>${flag}</td></tr>`;
    });
  } else {
    allocationBody.innerHTML = `<tr><td colspan="7" style="color:var(--accent-green); text-align:center;">All storage allocations within 20–95% efficiency band.</td></tr>`;
  }

  const anomalyBody = document.getElementById("anomalyTableBody");
  if (INTEL.price_anomalies && INTEL.price_anomalies.length > 0) {
    INTEL.price_anomalies.forEach(pa => {
      let col = pa.deviation_pct > 0 ? 'var(--accent-gold)' : 'var(--accent-cyan)';
      anomalyBody.innerHTML += `<tr><td><strong>${pa.station}</strong></td><td>${pa.sector}</td><td>${pa.ware}</td><td>${pa.side.toUpperCase()}</td><td>${pa.price.toFixed(2)} Cr</td><td>${pa.avg_price.toFixed(2)} Cr</td><td style="color:${col}; font-weight:700;">${pa.deviation_pct > 0 ? '+' : ''}${pa.deviation_pct}%</td><td>${pa.source.toUpperCase()}</td></tr>`;
    });
  } else {
    anomalyBody.innerHTML = `<tr><td colspan="8" style="color:var(--accent-green); text-align:center;">No prices deviate &gt;25% from galactic averages.</td></tr>`;
  }

  const burnBody = document.getElementById("burnTableBody");
  if (INTEL.burn_costs && INTEL.burn_costs.length > 0) {
    INTEL.burn_costs.forEach(b => {
      burnBody.innerHTML += `<tr><td><strong>${b.station}</strong></td><td>${b.sector}</td><td>${b.modules}</td><td style="color:var(--accent-gold)">${Math.round(b.input_cost_per_hour).toLocaleString()} Cr/h</td></tr>`;
    });
  } else {
    burnBody.innerHTML = `<tr><td colspan="4" style="color:var(--text-dim); text-align:center;">No production modules detected.</td></tr>`;
  }

  const arbitrageBody = document.getElementById("arbitrageTableBody");
  if (INTEL.market && INTEL.market.arbitrage && INTEL.market.arbitrage.length > 0) {
    INTEL.market.arbitrage.forEach(a => {
      arbitrageBody.innerHTML += `<tr><td><strong>${a.ware}</strong></td><td>${a.buy_station}</td><td>${a.buy_sector}</td><td>${a.buy_price.toFixed(2)} Cr</td><td>${a.sell_station}</td><td>${a.sell_sector}</td><td>${a.sell_price.toFixed(2)} Cr</td><td style="color:var(--accent-green)">+${a.spread.toFixed(2)} Cr</td><td>${a.margin_pct}%</td></tr>`;
    });
  } else {
    arbitrageBody.innerHTML = `<tr><td colspan="9" style="color:var(--text-dim); text-align:center;">No profitable cross-station arbitrage spreads detected in current offers.</td></tr>`;
  }

  const priceIndexBody = document.getElementById("priceIndexTableBody");
  if (INTEL.market && INTEL.market.station_price_index && INTEL.market.station_price_index.length > 0) {
    INTEL.market.station_price_index.forEach(p => {
      let col = p.avg_deviation_pct < 0 ? 'var(--accent-green)' : (p.avg_deviation_pct > 10 ? 'var(--accent-red)' : 'var(--text-main)');
      priceIndexBody.innerHTML += `<tr><td><strong>${p.station}</strong></td><td>${p.sector}</td><td style="color:${col}; font-weight:700;">${p.avg_deviation_pct > 0 ? '+' : ''}${p.avg_deviation_pct}%</td><td>${p.offer_count}</td><td>${p.cheapest_count}</td><td>${p.priciest_count}</td></tr>`;
    });
  } else {
    priceIndexBody.innerHTML = `<tr><td colspan="6" style="color:var(--text-dim); text-align:center;">No station price offers parsed.</td></tr>`;
  }

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
                                     .replace("/*__INTEL_JSON__*/", json.dumps(intelligence_payload))\
                                     .replace("__HEALTH_COMPOSITE__", f"{empire_health['composite']:.1f}")\
                                     .replace("__HEALTH_GRADE__", empire_health["grade"])\
                                     .replace("__FLEET_PPH__", num(trade_intel["fleet_profit_per_hour"]))\
                                     .replace("__FLEET_ROI__", f"{trade_intel['fleet_roi_pct']:.1f}")\
                                     .replace("__DERELICT_VALUE__", num(derelict_val["total_value"]))\
                                     .replace("__DERELICT_COUNT__", str(derelict_val["count"]))\
                                     .replace("__DERELICT_CLAIMABLE__", str(derelict_val["claimable"]))\
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

