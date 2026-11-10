# ==============================================================================
# TRADE ANALYZER ENGINE (MOD 1801 PARITY & LOG NORMALIZATION)
# ==============================================================================
from collections import Counter, defaultdict, deque

from .constants import (
    AVERAGE_WARE_PRICES, ESTIMATED_HULL_VALUES, SOLID_WARES, LIQUID_WARES,
    SPECIES_DIET_RULES, COMBAT_ENGAGEMENT_WINDOW,
)
from .models import CompletedTrade
from .utils import classify_ship

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
# SUPREME INTELLIGENCE ENGINE (V1.7.7)
# Profit/hour, ROI, route matrix, partner & ware velocity analytics,
# logistics autonomy, storage composition, allocation efficiency,
# price anomaly audit, empire health score and commander briefing.
# ==============================================================================

def _clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))


def compute_trade_intelligence(P, N, completed_trades, ship_profits, ware_profits):
    """Deep commercial analytics: profit/hour, ROI, route matrix, partners, ware velocity."""
    save_time = float(P.info.get("time") or 0.0)

    # ---- Per-ship efficiency (profit/hour, ROI, recent 24h) ----
    tx_by_ship = defaultdict(list)
    for tx in P.all_transactions:
        tx_by_ship[tx.ship_id].append(tx)

    ship_efficiency = []
    for s_id, data in ship_profits.items():
        txs = tx_by_ship.get(s_id, [])
        first_t = min((t.time for t in txs), default=save_time)
        hours = max((save_time - first_t) / 3600.0, 1.0)
        total_cost = sum(t.cost for t in completed_trades if t.ship_id == s_id)
        total_rev = data["rev"]
        roi = (data["profit"] / total_cost * 100.0) if total_cost > 0 else 0.0
        recent_cutoff = save_time - 86400.0
        recent_profit = sum(t.net_profit for t in completed_trades if t.ship_id == s_id and t.sell_time >= recent_cutoff)
        ship_obj = P.ships.get(s_id)
        ship_efficiency.append({
            "ship_id": s_id,
            "name": ship_obj.role if ship_obj else s_id,
            "profit": data["profit"],
            "ext_profit": data["ext_profit"],
            "trades": data["trades"],
            "profit_per_hour": data["profit"] / hours,
            "recent_profit_24h": recent_profit,
            "roi_pct": roi,
            "avg_margin": (data["profit"] / total_rev * 100.0) if total_rev > 0 else 0.0,
            "avg_util": (sum(data["util_acc"]) / len(data["util_acc"])) if data["util_acc"] else 0.0,
            "hours_active": hours,
        })
    ship_efficiency.sort(key=lambda x: -x["profit_per_hour"])

    # ---- Route profitability matrix (buy sector -> sell sector, per ware) ----
    route_acc = defaultdict(lambda: {"trades": 0, "profit": 0.0, "revenue": 0.0, "cost": 0.0,
                                     "volume": 0, "duration_h": 0.0, "margins": []})
    for t in completed_trades:
        key = (t.buy_sector or "?", t.sell_sector or "?", t.ware)
        r = route_acc[key]
        r["trades"] += 1
        r["profit"] += t.net_profit
        r["revenue"] += t.revenue
        r["cost"] += t.cost
        r["volume"] += t.amount
        r["duration_h"] += t.duration_s / 3600.0
        r["margins"].append(t.margin_pct)
    route_matrix = []
    for (buy_sec, sell_sec, ware), r in route_acc.items():
        route_matrix.append({
            "buy_sector": buy_sec, "sell_sector": sell_sec, "ware": ware,
            "trades": r["trades"], "profit": r["profit"], "revenue": r["revenue"],
            "volume": r["volume"],
            "profit_per_hour": (r["profit"] / r["duration_h"]) if r["duration_h"] > 0.01 else 0.0,
            "avg_margin": (sum(r["margins"]) / len(r["margins"])) if r["margins"] else 0.0,
            "roi_pct": (r["profit"] / r["cost"] * 100.0) if r["cost"] > 0 else 0.0,
        })
    route_matrix.sort(key=lambda x: -x["profit"])

    # ---- Partner intelligence (external trade counterparties) ----
    player_ids = set(P.ships) | set(P.stations) | set(P.build_storages)
    partner_acc = defaultdict(lambda: {"trades": 0, "volume": 0, "value": 0.0, "wares": Counter(), "buys": 0, "sells": 0})
    for tx in P.all_transactions:
        pid = tx.partner_id
        if not pid or pid in player_ids or pid == "unknown":
            continue
        pa = partner_acc[pid]
        pa["trades"] += 1
        pa["volume"] += tx.amount
        pa["value"] += tx.total_cr
        pa["wares"][tx.ware] += tx.amount
        if tx.op == "BUY": pa["buys"] += 1
        elif tx.op == "SELL": pa["sells"] += 1
    partner_intel = []
    for pid, pa in partner_acc.items():
        unit = P.all_units.get(pid, {})
        nm = unit.get("name") or f"Partner [{pid}]"
        top_ware = pa["wares"].most_common(1)[0][0] if pa["wares"] else "?"
        partner_intel.append({
            "partner_id": pid, "name": nm, "owner": (unit.get("owner") or "?").upper(),
            "trades": pa["trades"], "volume": pa["volume"], "value": pa["value"],
            "top_ware": top_ware, "buys": pa["buys"], "sells": pa["sells"],
        })
    partner_intel.sort(key=lambda x: -x["value"])

    # ---- Ware velocity (units/hour and profit/hour per commodity) ----
    ware_time = defaultdict(float)
    for t in completed_trades:
        ware_time[t.ware] += t.duration_s / 3600.0
    ware_velocity = []
    for wid, data in ware_profits.items():
        hrs = ware_time.get(wid, 0.0)
        ware_velocity.append({
            "ware": wid, "volume": data["volume"], "profit": data["profit"],
            "revenue": data["revenue"], "trades": data["trades"],
            "profit_per_hour": (data["profit"] / hrs) if hrs > 0.01 else 0.0,
            "avg_price": (data["revenue"] / data["volume"]) if data["volume"] else 0.0,
        })
    ware_velocity.sort(key=lambda x: -x["profit_per_hour"])

    total_cost = sum(t.cost for t in completed_trades)
    total_profit = sum(t.net_profit for t in completed_trades)
    fleet_roi = (total_profit / total_cost * 100.0) if total_cost > 0 else 0.0
    total_duration_h = sum(t.duration_s for t in completed_trades) / 3600.0
    fleet_profit_per_hour = (total_profit / total_duration_h) if total_duration_h > 0.01 else 0.0

    return {
        "ship_efficiency": ship_efficiency,
        "route_matrix": route_matrix,
        "partner_intel": partner_intel,
        "ware_velocity": ware_velocity,
        "fleet_roi_pct": fleet_roi,
        "fleet_profit_per_hour": fleet_profit_per_hour,
        "total_cost": total_cost,
        "total_profit": total_profit,
    }


def compute_logistics_intelligence(P, N):
    """Autonomy timers, storage composition, allocation efficiency, price anomalies."""
    # ---- Production input autonomy (time-to-empty per input ware) ----
    autonomy_rows = []
    for st in P.stations.values():
        if not st.prod:
            continue
        demands = defaultdict(float)
        for pm in st.prod:
            for w, rate in N.module_inputs(pm).items():
                demands[w] += rate
        for w, rate_hr in sorted(demands.items(), key=lambda kv: kv[0]):
            if rate_hr <= 0:
                continue
            stock = st.cargo.get(w, 0)
            hrs = stock / rate_hr
            autonomy_rows.append({
                "station_id": st.id, "station": st.name or st.role, "sector": st.sector,
                "ware": w, "stock": stock, "rate_hr": rate_hr, "hours_to_empty": hrs,
                "critical": hrs < 2.0, "warning": 2.0 <= hrs < 6.0,
            })
    autonomy_rows.sort(key=lambda r: r["hours_to_empty"])

    # ---- Storage composition per station ----
    storage_composition = []
    for st in P.stations.values():
        caps = st.storage_capacities()
        if sum(caps.values()) <= 0:
            continue
        used = {"container": 0.0, "solid": 0.0, "liquid": 0.0}
        ware_vol = []
        for w, amt in st.cargo.items():
            vol = N.volume(w) * amt
            ware_vol.append((w, vol))
            if w in SOLID_WARES: used["solid"] += vol
            elif w in LIQUID_WARES: used["liquid"] += vol
            else: used["container"] += vol
        ware_vol.sort(key=lambda x: -x[1])
        top_wares = [{"ware": w, "m3": v} for w, v in ware_vol[:3]]
        storage_composition.append({
            "station_id": st.id, "station": st.name or st.role, "sector": st.sector,
            "container_pct": (used["container"] / caps["container"] * 100.0) if caps["container"] else 0.0,
            "solid_pct": (used["solid"] / caps["solid"] * 100.0) if caps["solid"] else 0.0,
            "liquid_pct": (used["liquid"] / caps["liquid"] * 100.0) if caps["liquid"] else 0.0,
            "container_m3": used["container"], "solid_m3": used["solid"], "liquid_m3": used["liquid"],
            "caps": caps, "top_wares": top_wares,
        })

    # ---- Allocation efficiency (allocated m3 vs actually used) ----
    allocation_audit = []
    for st in P.stations.values():
        for wid, tw in st.trade_wares.items():
            alloc = tw.get("allocated_m3")
            if not alloc or alloc <= 0:
                continue
            stock = st.cargo.get(wid, 0)
            used_m3 = N.volume(wid) * stock
            eff = used_m3 / alloc * 100.0
            allocation_audit.append({
                "station_id": st.id, "station": st.name or st.role, "sector": st.sector,
                "ware": wid, "allocated_m3": alloc, "used_m3": used_m3, "efficiency_pct": eff,
                "over_allocated": eff < 20.0, "under_allocated": eff > 95.0,
            })
    allocation_audit.sort(key=lambda r: r["efficiency_pct"])

    # ---- Price anomaly audit (offers & manual prices vs galactic average) ----
    price_anomalies = []
    for st in P.stations.values():
        for off in st.offers:
            wid = off["ware"]
            avg = AVERAGE_WARE_PRICES.get(wid)
            price = off.get("price", 0.0)
            if not avg or price <= 0:
                continue
            dev = (price - avg) / avg * 100.0
            if abs(dev) > 25.0:
                price_anomalies.append({
                    "station_id": st.id, "station": st.name or st.role, "sector": st.sector,
                    "ware": wid, "side": off.get("side", "sell"), "price": price,
                    "avg_price": avg, "deviation_pct": dev, "source": "offer",
                })
        for wid, tw in st.trade_wares.items():
            if tw.get("price_mode") == "manual" and tw.get("manual_price"):
                avg = AVERAGE_WARE_PRICES.get(wid)
                if not avg:
                    continue
                dev = (tw["manual_price"] - avg) / avg * 100.0
                if abs(dev) > 25.0:
                    price_anomalies.append({
                        "station_id": st.id, "station": st.name or st.role, "sector": st.sector,
                        "ware": wid, "side": "manual", "price": tw["manual_price"],
                        "avg_price": avg, "deviation_pct": dev, "source": "manual",
                    })
    price_anomalies.sort(key=lambda r: -abs(r["deviation_pct"]))

    # ---- Hourly input burn cost per production station ----
    burn_costs = []
    for st in P.stations.values():
        if not st.prod:
            continue
        demands = defaultdict(float)
        for pm in st.prod:
            for w, rate in N.module_inputs(pm).items():
                demands[w] += rate
        cost_hr = sum(rate * AVERAGE_WARE_PRICES.get(w, 150.0) for w, rate in demands.items())
        burn_costs.append({
            "station_id": st.id, "station": st.name or st.role, "sector": st.sector,
            "input_cost_per_hour": cost_hr, "modules": len(st.prod),
        })
    burn_costs.sort(key=lambda r: -r["input_cost_per_hour"])

    return {
        "autonomy": autonomy_rows,
        "storage_composition": storage_composition,
        "allocation_audit": allocation_audit,
        "price_anomalies": price_anomalies,
        "burn_costs": burn_costs,
    }


def compute_market_intelligence(P, N):
    """Real market intelligence from parsed <trade> offers and <prices><reference> books.

    Returns best buy/sell per ware, cross-station arbitrage spreads, and
    per-station price competitiveness vs galactic averages.
    """
    offers = getattr(P, "market_offers", [])

    # ---- Best buy / best sell per ware (station production offers only) ----
    station_offers = [o for o in offers if o.get("station_id")]
    best_buy = {}
    best_sell = {}
    for o in station_offers:
        w = o["ware"]
        if o["side"] == "buy":
            cur = best_buy.get(w)
            if cur is None or o["price"] < cur["price"]:
                best_buy[w] = o
        elif o["side"] == "sell":
            cur = best_sell.get(w)
            if cur is None or o["price"] > cur["price"]:
                best_sell[w] = o

    # ---- Arbitrage spreads: buy at lowest station, sell at highest ----
    arbitrage = []
    all_wares = set(best_buy) | set(best_sell)
    for w in all_wares:
        buy_o = best_buy.get(w)
        sell_o = best_sell.get(w)
        if not buy_o or not sell_o:
            continue
        if buy_o["station_id"] == sell_o["station_id"]:
            continue
        spread = sell_o["price"] - buy_o["price"]
        if spread <= 0:
            continue
        margin_pct = spread / sell_o["price"] * 100.0
        arbitrage.append({
            "ware": w,
            "buy_station_id": buy_o["station_id"], "buy_sector": buy_o["sector"], "buy_price": buy_o["price"],
            "sell_station_id": sell_o["station_id"], "sell_sector": sell_o["sector"], "sell_price": sell_o["price"],
            "spread": spread, "margin_pct": margin_pct,
            "buy_amount": buy_o["amount"], "sell_amount": sell_o["amount"],
        })
    arbitrage.sort(key=lambda r: -r["spread"])

    # ---- Per-station price competitiveness vs galactic average ----
    station_price_index = []
    for st in P.stations.values():
        if not st.offers:
            continue
        devs = []
        for off in st.offers:
            avg = AVERAGE_WARE_PRICES.get(off["ware"])
            if not avg or off["price"] <= 0:
                continue
            devs.append((off["price"] - avg) / avg * 100.0)
        if not devs:
            continue
        station_price_index.append({
            "station_id": st.id, "station": st.name or st.role, "sector": st.sector,
            "avg_deviation_pct": sum(devs) / len(devs),
            "offer_count": len(st.offers),
            "cheapest_count": sum(1 for d in devs if d < -10.0),
            "priciest_count": sum(1 for d in devs if d > 10.0),
        })
    station_price_index.sort(key=lambda r: r["avg_deviation_pct"])

    # ---- Reference price book analysis (station's internal price view) ----
    reference_analysis = []
    for st in P.stations.values():
        refs = getattr(st, "reference_prices", {})
        if not refs:
            continue
        devs = []
        for w, rp in refs.items():
            avg = AVERAGE_WARE_PRICES.get(w)
            if not avg:
                continue
            if rp.get("buy", 0) > 0:
                devs.append((rp["buy"] - avg) / avg * 100.0)
        if devs:
            reference_analysis.append({
                "station_id": st.id, "station": st.name or st.role, "sector": st.sector,
                "avg_buy_deviation_pct": sum(devs) / len(devs),
                "referenced_wares": len(refs),
            })

    return {
        "best_buy": best_buy,
        "best_sell": best_sell,
        "arbitrage": arbitrage,
        "station_price_index": station_price_index,
        "reference_analysis": reference_analysis,
        "total_offers": len(offers),
        "station_offer_count": len(station_offers),
    }


def compute_derelict_valuation(P, N):
    """Estimate total recoverable value of abandoned hulls."""
    total = 0
    by_size = Counter()
    claimable = 0
    for d in P.derelicts:
        _, _, w_key = classify_ship(d["macro"], f"ship_{d['size'].lower()}")
        val = ESTIMATED_HULL_VALUES.get(w_key, 1_500_000)
        total += val
        by_size[d["size"]] += 1
        if d.get("known"):
            claimable += 1
    return {"total_value": total, "count": len(P.derelicts), "by_size": dict(by_size), "claimable": claimable}


def compute_empire_health(P, N, trade_intel, logistics_intel, threat_hops):
    """Composite 0-100 empire health score with weighted sub-scores and grade."""
    save_time = float(P.info.get("time") or 0.0)
    ships = list(P.ships.values())
    stations = list(P.stations.values())
    warships = [s for s in ships if s.category == "Military"]

    # Treasury (15%): 1B Cr liquidity benchmark
    acct_by_id = {a["id"]: a["amount"] for a in P.accounts if a.get("id")}
    purse = P.player_direct_money if P.player_direct_money is not None else acct_by_id.get(P.player_account_id, 0)
    station_cash = sum(sum(a["amount"] for a in st.accounts) for st in stations)
    liquid = purse + station_cash
    treasury_score = _clamp(liquid / 1_000_000_000.0 * 100.0)

    # Fleet readiness (25%): armed / shielded / piloted / hull integrity
    if warships:
        armed = sum(1 for s in warships if (s.parts["weapon"] + s.parts["turret"] + s.parts["missilelauncher"] + s.parts["missileturret"]) > 0)
        shielded = sum(1 for s in warships if s.parts["shieldgenerator"] > 0)
        piloted = sum(1 for s in warships if s.pilot_id or s.player_piloted)
        avg_hull = sum(s.hull_pct for s in warships) / len(warships)
        fleet_score = (armed / len(warships) * 100.0 + shielded / len(warships) * 100.0 +
                       piloted / len(warships) * 100.0 + avg_hull) / 4.0
    else:
        fleet_score = 100.0

    # Industry (20%): production stations free of starved inputs
    prod_stations = [st for st in stations if st.prod]
    if prod_stations:
        healthy = 0
        for st in prod_stations:
            demands = defaultdict(float)
            for pm in st.prod:
                for w, rate in N.module_inputs(pm).items():
                    demands[w] += rate
            if all(st.cargo.get(w, 0) > 0 for w in demands):
                healthy += 1
        industry_score = healthy / len(prod_stations) * 100.0
    else:
        industry_score = 100.0

    # Logistics (15%): stations below critical storage choke
    capped = [sc for sc in logistics_intel["storage_composition"]]
    if capped:
        ok = sum(1 for sc in capped if max(sc["container_pct"], sc["solid_pct"], sc["liquid_pct"]) <= 92.0)
        logistics_score = ok / len(capped) * 100.0
    else:
        logistics_score = 100.0

    # Security (15%): threat posture of occupied sectors
    occupied = {s.sector for s in ships if s.sector} | {st.sector for st in stations if st.sector}
    crit = sum(1 for sid in occupied if threat_hops.get(sid, 999) == 0)
    high = sum(1 for sid in occupied if threat_hops.get(sid, 999) == 1)
    guarded = sum(1 for sid in occupied if 2 <= threat_hops.get(sid, 999) <= 3)
    security_score = _clamp(100.0 - 30.0 * crit - 15.0 * high - 5.0 * guarded)

    # Personnel (10%): marine readiness weighting
    total_marines = sum(s.marines for s in ships)
    if total_marines > 0:
        elite = sum(s.elite_marines for s in ships)
        veteran = sum(s.veteran_marines for s in ships)
        recruit = sum(s.recruit_marines for s in ships)
        personnel_score = _clamp((elite * 1.0 + veteran * 0.6 + recruit * 0.25) / total_marines * 100.0)
    else:
        personnel_score = 50.0

    composite = (treasury_score * 0.15 + fleet_score * 0.25 + industry_score * 0.20 +
                 logistics_score * 0.15 + security_score * 0.15 + personnel_score * 0.10)
    if composite >= 90: grade = "S"
    elif composite >= 80: grade = "A"
    elif composite >= 70: grade = "B"
    elif composite >= 55: grade = "C"
    elif composite >= 40: grade = "D"
    else: grade = "F"

    return {
        "composite": round(composite, 1), "grade": grade,
        "treasury": round(treasury_score, 1), "fleet": round(fleet_score, 1),
        "industry": round(industry_score, 1), "logistics": round(logistics_score, 1),
        "security": round(security_score, 1), "personnel": round(personnel_score, 1),
        "liquid": liquid,
    }


def build_commander_briefing(P, N, trade_intel, logistics_intel, threat_hops, derelict_val):
    """Prioritized alert feed for the commander. Each alert: level, category, message."""
    save_time = float(P.info.get("time") or 0.0)
    alerts = []

    def add(level, category, message):
        alerts.append({"level": level, "category": category, "message": message})

    def sec_name(sid):
        if not sid:
            return "Unknown"
        return N.sector(P.sectors.get(sid)) if P.sectors.get(sid) else str(sid)

    # Production starvation / autonomy
    for row in logistics_intel["autonomy"]:
        sec = sec_name(row["sector"])
        if row["critical"]:
            add("CRITICAL", "Industry", f"{row['station']} ({sec}): {row['ware']} depletes in {row['hours_to_empty']:.1f}h — production will stall")
        elif row["warning"]:
            add("WARNING", "Industry", f"{row['station']} ({sec}): {row['ware']} autonomy only {row['hours_to_empty']:.1f}h")

    # Storage chokes
    for sc in logistics_intel["storage_composition"]:
        sec = sec_name(sc["sector"])
        worst = max(sc["container_pct"], sc["solid_pct"], sc["liquid_pct"])
        if worst > 92.0:
            add("CRITICAL", "Logistics", f"{sc['station']} ({sec}): storage at {worst:.0f}% — output blocked")
        elif worst > 80.0:
            add("WARNING", "Logistics", f"{sc['station']} ({sec}): storage at {worst:.0f}% — approaching choke")

    # Fleet readiness
    for s in P.ships.values():
        if s.category != "Military":
            continue
        nm = s.name or s.role
        if not (s.pilot_id or s.player_piloted):
            add("WARNING", "Fleet", f"{nm} ({s.code or s.id}): no pilot assigned")
        if not (s.parts["weapon"] + s.parts["turret"] + s.parts["missilelauncher"] + s.parts["missileturret"]):
            add("WARNING", "Fleet", f"{nm} ({s.code or s.id}): unarmed warship")
        if s.hull_pct < 70.0:
            add("WARNING", "Fleet", f"{nm} ({s.code or s.id}): hull at {s.hull_pct:.0f}% — needs repair")

    # Combat stress
    for s in P.ships.values():
        if s.attacktime and (save_time - s.attacktime) < COMBAT_ENGAGEMENT_WINDOW:
            add("CRITICAL", "Combat", f"{s.name or s.role} ({s.code or s.id}): under fire right now")

    # Security posture
    occupied = {s.sector for s in P.ships.values() if s.sector} | {st.sector for st in P.stations.values() if st.sector}
    for sid in occupied:
        if threat_hops.get(sid, 999) == 0:
            add("CRITICAL", "Security", f"{sec_name(sid)}: hostile capital presence — front line")

    # Inactive traders (only ships that have traded before but stopped)
    for s in P.ships.values():
        if s.category in ("Trader", "Miner") and (s.commander or s.assignment in ("Trade", "Mining")):
            last_tx = max((tx.time for tx in s.transactions), default=0.0)
            if last_tx <= 0.0:
                continue
            idle_h = (save_time - last_tx) / 3600.0
            if idle_h > 6.0:
                add("WARNING", "Trade", f"{s.name or s.role} ({s.code or s.id}): idle {idle_h:.1f}h — check orders/blacklist")

    # Price anomalies (severe only)
    for pa in logistics_intel["price_anomalies"]:
        if abs(pa["deviation_pct"]) > 40.0:
            sec = sec_name(pa["sector"])
            add("INFO", "Market", f"{pa['station']} ({sec}): {pa['ware']} priced {pa['deviation_pct']:+.0f}% vs galactic average")

    # Treasury surplus
    skimmable = 0
    for st in P.stations.values():
        bal = sum(a["amount"] for a in st.accounts)
        reserve = 50_000_000 if "Shipyard" in st.role else (20_000_000 if st.prod else 10_000_000)
        skimmable += max(0, bal - reserve)
    if skimmable > 50_000_000:
        add("INFO", "Treasury", f"{skimmable:,.0f} Cr safe to skim from station accounts")

    # Derelicts
    if derelict_val["claimable"] > 0:
        add("INFO", "Recon", f"{derelict_val['claimable']} claimable derelict hulls worth ~{derelict_val['total_value']:,.0f} Cr")

    order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    alerts.sort(key=lambda a: order.get(a["level"], 3))
    return alerts[:30]
