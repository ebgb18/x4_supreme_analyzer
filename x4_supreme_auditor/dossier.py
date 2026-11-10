# ==============================================================================
# UNIFIED STRATEGIC DOSSIER & MARKDOWN GENERATOR
# ==============================================================================
import datetime
from collections import Counter, defaultdict, deque

from .constants import (
    REF_REGEX, SOLID_WARES, LIQUID_WARES, SPECIES_DIET_RULES, COMBAT_ENGAGEMENT_WINDOW,
    AVERAGE_WARE_PRICES,
)
from .utils import esc, num, prettify, ammo_class
from .analytics import (
    process_trade_analytics, compute_trade_intelligence, compute_logistics_intelligence,
    compute_derelict_valuation, compute_empire_health, build_commander_briefing,
    compute_market_intelligence,
)

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

    # ---- SUPREME INTELLIGENCE ENGINE (V1.7.7) ----
    completed_trades_intel, ship_profits_intel, ware_profits_intel, inactive_traders = process_trade_analytics(P, N)
    trade_intel = compute_trade_intelligence(P, N, completed_trades_intel, ship_profits_intel, ware_profits_intel)
    logistics_intel = compute_logistics_intelligence(P, N)
    derelict_val = compute_derelict_valuation(P, N)
    market_intel = compute_market_intelligence(P, N)
    empire_health = compute_empire_health(P, N, trade_intel, logistics_intel, threat_hops)
    briefing = build_commander_briefing(P, N, trade_intel, logistics_intel, threat_hops, derelict_val)

    date_str = datetime.datetime.utcfromtimestamp(int(P.info["date"])).strftime("%Y-%m-%d %H:%M UTC") if P.info.get("date") else "Unknown"

    md.append("# SUPREME COMMAND UNIFIED STRATEGIC & INDUSTRIAL DOSSIER (V1.7.7 ENTERPRISE — SUPREME INTELLIGENCE EDITION)\n")
    md.append(f"> Savegame: **{P.info.get('save_name', 'Unknown')}** | Commander: **{P.info.get('player', 'Val Selton')}** | Engine: `X4 Build {P.info.get('build', 'Unknown')}` | Time: `{save_time:,.0f}s` ({date_str})\n")

    # 0. COMMANDER BRIEFING & EMPIRE HEALTH SCORE
    md.append("## 0. Commander Briefing & Empire Health Score")
    md.append(f"### **Empire Health: {empire_health['composite']:.1f}/100 — Grade {empire_health['grade']}**\n")
    health_rows = [
        ["Treasury Liquidity", f"{empire_health['treasury']:.1f}", "15%"],
        ["Fleet Readiness", f"{empire_health['fleet']:.1f}", "25%"],
        ["Industrial Health", f"{empire_health['industry']:.1f}", "20%"],
        ["Logistics & Storage", f"{empire_health['logistics']:.1f}", "15%"],
        ["Security Posture", f"{empire_health['security']:.1f}", "15%"],
        ["Personnel Readiness", f"{empire_health['personnel']:.1f}", "10%"],
    ]
    md += table(["Health Dimension", "Score /100", "Weight"], health_rows)
    md.append("")
    if briefing:
        md.append("### Priority Action Items")
        level_icon = {"CRITICAL": "🔴", "WARNING": "🟠", "INFO": "🔵"}
        for a in briefing:
            md.append(f"- {level_icon.get(a['level'], '•')} **[{a['level']}] {a['category']}:** {a['message']}")
        md.append("")
    else:
        md.append("- *No critical action items. Empire operating within nominal parameters.*\n")

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
            shield_str = ", ".join(f"{cnt}x {N.gear(m)}" for m, cnt in s.installed_shields.items())
        elif s.parts['shieldgenerator'] == 0:
            shield_str = "**NO SHIELDS INSTALLED (0 SLOTS)**"

        engine_str = ", ".join(f"{cnt}x {N.gear(m)}" for m, cnt in s.installed_engines.items()) if s.installed_engines else "Standard Engines"
        weap_summary = []
        if s.installed_weapons: weap_summary.append("Main: " + ", ".join(f"{cnt}x {N.gear(m)}" for m, cnt in s.installed_weapons.items()))
        if s.installed_turrets: weap_summary.append("Turrets: " + ", ".join(f"{cnt}x {N.gear(m)}" for m, cnt in s.installed_turrets.items()))
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
    completed_trades, ship_profits, ware_profits = completed_trades_intel, ship_profits_intel, ware_profits_intel
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

    # 18. TRADE ROUTE INTELLIGENCE (PROFIT/HOUR, ROI, ROUTE MATRIX)
    md.append("## 18. Trade Route Intelligence — Profit/Hour, ROI & Route Matrix")
    md.append(f"- **Fleet ROI:** **{trade_intel['fleet_roi_pct']:.1f}%** on **{num(trade_intel['total_cost'])} Cr** deployed capital")
    md.append(f"- **Fleet Profit Velocity:** **{num(trade_intel['fleet_profit_per_hour'])} Cr/hour** across all completed cycles\n")

    eff_rows = []
    for e in trade_intel["ship_efficiency"][:12]:
        s_obj = P.ships.get(e["ship_id"])
        s_title = ship_name(s_obj) if s_obj else f"Trader [{e['ship_id']}]"
        eff_rows.append([
            s_title, f"{num(e['profit_per_hour'])} Cr/h", f"{num(e['recent_profit_24h'])} Cr",
            f"{e['roi_pct']:.1f}%", f"{e['avg_margin']:.1f}%", f"{e['avg_util']:.1f}%", str(e["trades"])
        ])
    if eff_rows:
        md.append("### Fleet Efficiency Leaderboard (Profit/Hour)")
        md += table(["Vessel", "Profit / Hour", "Last 24h Profit", "ROI %", "Avg Margin", "Avg Hold Fill", "Trades"], eff_rows)
        md.append("")

    route_rows = []
    for r in trade_intel["route_matrix"][:15]:
        route_rows.append([
            sname(r["buy_sector"]), sname(r["sell_sector"]), N.ware(r["ware"]),
            str(r["trades"]), f"{num(r['profit'])} Cr", f"{num(r['profit_per_hour'])} Cr/h",
            f"{r['avg_margin']:.1f}%", f"{r['roi_pct']:.1f}%"
        ])
    if route_rows:
        md.append("### Route Profitability Matrix (Buy → Sell, by Ware)")
        md += table(["Buy Sector", "Sell Sector", "Ware", "Runs", "Net Profit", "Profit / Hour", "Avg Margin", "ROI %"], route_rows)
        md.append("")

    partner_rows = []
    for p_ in trade_intel["partner_intel"][:12]:
        partner_rows.append([
            p_["name"], p_["owner"], str(p_["trades"]), num(p_["volume"]),
            f"{num(p_['value'])} Cr", N.ware(p_["top_ware"]), f"{p_['buys']}B / {p_['sells']}S"
        ])
    if partner_rows:
        md.append("### External Partner Intelligence (Counterparties by Volume)")
        md += table(["Partner", "Faction", "Trades", "Units", "Total Value", "Top Ware", "Buy/Sell"], partner_rows)
        md.append("")

    velocity_rows = []
    for v in trade_intel["ware_velocity"][:10]:
        velocity_rows.append([
            N.ware(v["ware"]), num(v["volume"]), f"{num(v['profit'])} Cr",
            f"{num(v['profit_per_hour'])} Cr/h", f"{v['avg_price']:.2f} Cr", str(v["trades"])
        ])
    if velocity_rows:
        md.append("### Ware Velocity — Profit per Hour by Commodity")
        md += table(["Commodity", "Units Traded", "Net Profit", "Profit / Hour", "Avg Unit Price", "Transactions"], velocity_rows)
        md.append("")

    # 19. LOGISTICS AUTONOMY & TIME-TO-EMPTY
    md.append("## 19. Logistics Autonomy — Time-to-Empty per Production Input")
    autonomy_rows = []
    for row in logistics_intel["autonomy"]:
        if row["hours_to_empty"] > 24.0:
            continue
        st_obj = P.stations.get(row["station_id"])
        st_title = station_name(st_obj) if st_obj else row["station"]
        flag = "🔴 CRITICAL" if row["critical"] else ("🟠 WARNING" if row["warning"] else "🟢 OK")
        autonomy_rows.append([
            st_title, sname(row["sector"]), N.ware(row["ware"]),
            num(row["stock"]), f"{row['rate_hr']:.1f}/h", f"{row['hours_to_empty']:.1f}h", flag
        ])
    if autonomy_rows:
        md += table(["Station Complex", "Sector", "Input Ware", "Stock", "Burn Rate", "Time to Empty", "Status"], autonomy_rows[:40])
        if len(autonomy_rows) > 40: md.append(f"- *...and {len(autonomy_rows) - 40} more input lines audited.*")
    else:
        md.append("- *All production inputs have >24h autonomy. Supply chain healthy.*")
    md.append("")

    # 20. STORAGE COMPOSITION & ALLOCATION EFFICIENCY
    md.append("## 20. Storage Composition & Allocation Efficiency Audit")
    comp_rows = []
    for sc in logistics_intel["storage_composition"]:
        st_obj = P.stations.get(sc["station_id"])
        st_title = station_name(st_obj) if st_obj else sc["station"]
        top = ", ".join(f"{N.ware(t['ware'])} ({num(t['m3'])} m³)" for t in sc["top_wares"]) or "Empty"
        comp_rows.append([
            st_title, sname(sc["sector"]),
            f"{sc['container_pct']:.0f}%", f"{sc['solid_pct']:.0f}%", f"{sc['liquid_pct']:.0f}%", top
        ])
    if comp_rows:
        md += table(["Station Complex", "Sector", "Container", "Solid", "Liquid", "Top Stored Wares (by m³)"], comp_rows)
        md.append("")

    alloc_rows = []
    for a_ in logistics_intel["allocation_audit"]:
        if not (a_["over_allocated"] or a_["under_allocated"]):
            continue
        st_obj = P.stations.get(a_["station_id"])
        st_title = station_name(st_obj) if st_obj else a_["station"]
        flag = "Over-allocated" if a_["over_allocated"] else "Under-allocated"
        alloc_rows.append([
            st_title, sname(a_["sector"]), N.ware(a_["ware"]),
            f"{num(a_['allocated_m3'])} m³", f"{num(a_['used_m3'])} m³", f"{a_['efficiency_pct']:.0f}%", flag
        ])
    if alloc_rows:
        md.append("### Allocation Efficiency Flags (<20% or >95% utilized)")
        md += table(["Station Complex", "Sector", "Ware", "Allocated", "Used", "Efficiency", "Flag"], alloc_rows[:30])
        md.append("")

    # 21. PRICE ANOMALY AUDIT
    md.append("## 21. Price Anomaly Audit — Offers & Manual Prices vs Galactic Average")
    anomaly_rows = []
    for pa in logistics_intel["price_anomalies"][:30]:
        st_obj = P.stations.get(pa["station_id"])
        st_title = station_name(st_obj) if st_obj else pa["station"]
        anomaly_rows.append([
            st_title, sname(pa["sector"]), N.ware(pa["ware"]), pa["side"].upper(),
            f"{pa['price']:.2f} Cr", f"{pa['avg_price']:.2f} Cr", f"{pa['deviation_pct']:+.1f}%", pa["source"].upper()
        ])
    if anomaly_rows:
        md += table(["Station Complex", "Sector", "Ware", "Side", "Price", "Galactic Avg", "Deviation", "Source"], anomaly_rows)
    else:
        md.append("- *No prices deviate >25% from galactic averages. Market posture nominal.*")
    md.append("")

    # 22. PRODUCTION BURN COST & HOURLY INPUT SPEND
    md.append("## 22. Production Burn Cost — Hourly Input Spend per Complex")
    burn_rows = []
    for b in logistics_intel["burn_costs"][:20]:
        st_obj = P.stations.get(b["station_id"])
        st_title = station_name(st_obj) if st_obj else b["station"]
        burn_rows.append([
            st_title, sname(b["sector"]), str(b["modules"]), f"{num(b['input_cost_per_hour'])} Cr/h"
        ])
    if burn_rows:
        md += table(["Station Complex", "Sector", "Production Modules", "Input Cost / Hour"], burn_rows)
    else:
        md.append("- *No production modules detected.*")
    md.append("")

    # 23. DERELICT ASSET VALUATION
    md.append("## 23. Derelict Asset Valuation — Recoverable Fleet Capital")
    md.append(f"- **Total Derelict Hulls:** **{derelict_val['count']}** ({derelict_val['claimable']} claimable/known)")
    md.append(f"- **Estimated Recoverable Value:** **{num(derelict_val['total_value'])} Cr**")
    if derelict_val["by_size"]:
        size_str = ", ".join(f"{sz}: {cnt}" for sz, cnt in sorted(derelict_val["by_size"].items()))
        md.append(f"- **By Size Class:** {size_str}")
    md.append("")

    # 24. MARKET INTELLIGENCE — ARBITRAGE & PRICE POSITIONING
    md.append("## 24. Market Intelligence — Cross-Station Arbitrage & Price Positioning")
    md.append(f"- **Market Offers Parsed:** **{num(market_intel['total_offers'])}** total ({num(market_intel['station_offer_count'])} station production offers)\n")

    arb_rows = []
    for a_ in market_intel["arbitrage"][:20]:
        buy_st = P.stations.get(a_["buy_station_id"])
        sell_st = P.stations.get(a_["sell_station_id"])
        buy_title = station_name(buy_st) if buy_st else f"Station [{a_['buy_station_id']}]"
        sell_title = station_name(sell_st) if sell_st else f"Station [{a_['sell_station_id']}]"
        arb_rows.append([
            N.ware(a_["ware"]), buy_title, sname(a_["buy_sector"]), f"{a_['buy_price']:.2f} Cr",
            sell_title, sname(a_["sell_sector"]), f"{a_['sell_price']:.2f} Cr",
            f"{a_['spread']:.2f} Cr", f"{a_['margin_pct']:.1f}%"
        ])
    if arb_rows:
        md.append("### Cross-Station Arbitrage Opportunities (Buy Low → Sell High)")
        md += table(["Ware", "Buy At", "Buy Sector", "Buy Price", "Sell At", "Sell Sector", "Sell Price", "Spread", "Margin"], arb_rows)
        md.append("")
    else:
        md.append("- *No profitable cross-station arbitrage spreads detected in current offers.*\n")

    price_idx_rows = []
    for p_ in market_intel["station_price_index"]:
        st_obj = P.stations.get(p_["station_id"])
        st_title = station_name(st_obj) if st_obj else p_["station"]
        price_idx_rows.append([
            st_title, sname(p_["sector"]), f"{p_['avg_deviation_pct']:+.1f}%",
            str(p_["offer_count"]), str(p_["cheapest_count"]), str(p_["priciest_count"])
        ])
    if price_idx_rows:
        md.append("### Station Price Competitiveness Index (vs Galactic Average)")
        md += table(["Station Complex", "Sector", "Avg Price Deviation", "Offers", "Cheapest Wares", "Priciest Wares"], price_idx_rows)
        md.append("")

    return "\n".join(md), grand_total_net_worth, total_liquid, fleet_capital, real_estate, stockpile_val

